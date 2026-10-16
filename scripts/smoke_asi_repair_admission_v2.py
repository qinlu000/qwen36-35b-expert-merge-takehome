#!/usr/bin/env python3
"""Independent HTTP outage/recovery fixture for bounded ASI repair admission."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading

import httpx
from repair_asi_infrastructure_v2 import bounded_admission, condition_infrastructure
from run_asi_baseline_v2 import write_json


class Server(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        raw = b'healthy' if self.server.healthy else b'offline'
        self.send_response(200 if self.server.healthy else 503)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with self.server.lock:
            self.server.calls.append(body['condition'])
        if self.server.outage:
            self.server.barrier.wait(timeout=10)
            self.server.healthy = False
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        raw = b'{"received":true}'
        self.send_response(200)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    root = Path(__file__).resolve().parents[1]
    parent = root / 'artifacts/preflight/asi'
    run = Path(tempfile.mkdtemp(prefix='repair-admission-', dir=parent))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Server)
    server.healthy, server.outage = True, True
    server.calls, server.lock, server.barrier = [], threading.Lock(), threading.Barrier(8)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    entries = [{'condition': f'self-authored-{index:03d}'} for index in range(237)]
    snapshots = []
    try:
        with httpx.Client(trust_env=False, timeout=2) as health_client:
            def healthy():
                try:
                    return health_client.get(endpoint + '/health').status_code == 200
                except httpx.HTTPError:
                    return False
            def worker(entry):
                try:
                    with httpx.Client(trust_env=False, timeout=12) as client:
                        client.post(endpoint + '/generate', json=entry).raise_for_status()
                    return 'received'
                except httpx.HTTPError:
                    return 'transport_failure'
            def checkpoint(state):
                snapshots.append(dict(state))
                write_json(run / 'checkpoint.json', state)
            with ThreadPoolExecutor(max_workers=8) as pool:
                state, active = bounded_admission(entries, lambda entry: pool.submit(worker, entry), healthy,
                    lambda entry, result: result == 'transport_failure', checkpoint, concurrency=8, interval=.05)
                for future in active:
                    future.cancel()
            outage_passed = (state['state'] == 'paused_infrastructure'
                and len(state['admitted_this_session']) == len(server.calls) == 8
                and state['unsubmitted_this_session'] == 229)
            failed_admitted = set(state['admitted_this_session'])
            remaining = [entry for entry in entries if entry['condition'] not in failed_admitted]
            server.healthy, server.outage = True, False
            with ThreadPoolExecutor(max_workers=8) as pool:
                recovered, active = bounded_admission(remaining, lambda entry: pool.submit(worker, entry), healthy,
                    lambda entry, result: result == 'transport_failure', checkpoint, concurrency=8, interval=.05)
            recovered_calls = server.calls[8:]
            recovery_passed = (recovered['state'] == 'completed' and len(recovered_calls) == 229
                and len(set(server.calls)) == 237 and not (set(recovered_calls) & failed_admitted))
            server.healthy = False
            with ThreadPoolExecutor(max_workers=8) as pool:
                offline, active = bounded_admission(entries, lambda entry: pool.submit(worker, entry), healthy,
                    lambda entry, result: True, checkpoint, concurrency=8)
            offline_passed = len(offline['admitted_this_session']) == 0 and offline['unsubmitted_this_session'] == 237
        edge = run / 'classification'
        (edge / 'audit').mkdir(parents=True)
        (edge / 'task').mkdir()
        classifications = []
        for name, response, elapsed, events, expected_pause in [
                ('received_parse_failure', True, 1, [], False),
                ('received_program_failure', True, 12, [], False),
                ('genuine_budget_timeout', False, 1200, [], False),
                ('context_budget_failure', False, 1, [{'event': 'guard', 'prompt_tokens': 57345}], False),
                ('transport_failure', False, 1, [{'event': 'ambiguous_transport_failure_no_retry'}], True),
                ('unknown_failure', False, 1, [], True)]:
            entry = {'condition': name, 'task_id': 'task'}
            if response:
                write_json(edge / 'audit' / (name + '.response.json'), {'self_authored_response': True})
            write_json(edge / 'task' / (name + '.json'), {'execution_time_seconds': elapsed})
            write_json(edge / 'audit' / (name + '.request.json'), {'events': events})
            reason = condition_infrastructure(edge, entry)
            classifications.append({'name': name, 'passed': bool(reason) == expected_pause,
                'pause_reason': reason, 'pause_does_not_authorize_retry': bool(reason)})
        summary = {'passed': outage_passed and recovery_passed and offline_passed and all(case['passed'] for case in classifications),
            'run_dir': str(run), 'real_model_calls': 0, 'benchmark_conditions_executed': 0,
            'outage': {'passed': outage_passed, 'admitted': 8, 'untouched': state['unsubmitted_this_session'], 'checkpoint': state['state']},
            'recovery': {'passed': recovery_passed, 'remaining_completed': len(recovered_calls),
                         'failed_attempts_regenerated': len(set(recovered_calls) & failed_admitted)},
            'initial_offline': {'passed': offline_passed, 'admitted': len(offline['admitted_this_session'])},
            'max_outstanding_futures': max(len(snapshot['active']) for snapshot in snapshots),
            'classification_cases': classifications}
        write_json(run / 'summary.json', summary)
        print(json.dumps(summary, indent=2))
        if not summary['passed']:
            raise SystemExit(1)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
