#!/usr/bin/env python3
"""Real frozen ASI workers/scopes, self-authored HTTP outage and cleanup only."""
from concurrent.futures import ProcessPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing
import os
from pathlib import Path
import socket
import tempfile
import threading
import time

import httpx
from repair_asi_infrastructure_v2 import bounded_admission, stop_inflight, condition_infrastructure
from run_asi_baseline_v2 import condition_worker, worker_init, write_json


PROGRAM = '''import os,pathlib,subprocess,sys,time
subprocess.Popen([sys.executable,"-c","import time; time.sleep(300)"],start_new_session=True)
pathlib.Path("pid_namespace").write_text(os.readlink("/proc/self/ns/pid"))
while True:
 pathlib.Path("heartbeat").write_text(str(time.time_ns()))
 time.sleep(.05)
'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200 if self.server.healthy else 503)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/tokenize':
            payload = {'count': 123, 'max_model_len': 65536}
        elif 'case1' in body['messages'][1]['content']:
            # Ensure another worker has actually launched a detached process
            # before simulating the shared transport failure.
            deadline = time.monotonic() + 20
            journal = self.server.output / 'audit/synthetic-case0__seed31415__b1.started.json'
            while time.monotonic() < deadline:
                if journal.exists():
                    workspace = Path(json.loads(journal.read_text())['workspace'])
                    if (workspace / 'heartbeat').exists():
                        self.server.workspace = workspace
                        break
                time.sleep(.05)
            self.server.healthy = False
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        else:
            payload = {'id': 'synthetic-cleanup', 'object': 'chat.completion', 'created': 0,
                'model': 'apex-qwen', 'choices': [{'index': 0, 'finish_reason': 'stop',
                    'message': {'role': 'assistant', 'content': '```python\n' + PROGRAM + '\n```'}}],
                'usage': {'prompt_tokens': 123, 'completion_tokens': 40, 'total_tokens': 163}}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    root = Path(__file__).resolve().parents[1]
    run = Path(tempfile.mkdtemp(prefix='repair-cleanup-', dir=root / 'artifacts/preflight/asi'))
    project = run / 'project'
    (project / 'artifacts/benchmarks').mkdir(parents=True)
    (project / 'artifacts/tools').mkdir()
    inputs = project / 'artifacts/asi/instances_seed31415'
    inputs.mkdir(parents=True)
    (project / 'artifacts/benchmarks/asi').symlink_to(root / 'artifacts/benchmarks/asi', target_is_directory=True)
    (project / 'artifacts/tools/ngspice').symlink_to(root / 'artifacts/tools/ngspice', target_is_directory=True)
    runtime = next(group['runtime'] for group in json.loads((root / 'configs/asi/task_requirements.json').read_text())['runtime_groups'] if group['group'] == 24)
    tasks, entries = {}, []
    for index in range(2):
        name = f'synthetic-case{index}'
        directory = inputs / (name + '__seed31415')
        directory.mkdir()
        (directory / 'prompt_b1.md').write_text(f'Self-authored case{index} cleanup fixture.\n')
        tasks[name] = {'id': name, '_task_dir': run, '_runtime_python': runtime.get('python'),
            '_runtime_packages': runtime['packages'], 'output': {'files': [{'name': 'generated.py', 'type': 'code'}]}}
        entries.append({'condition': name + '__seed31415__b1', 'task_id': name, 'level': 'b1'})
    output = run / 'attempt'
    key = run / 'synthetic.key'
    key.write_text('self-authored-cleanup-key')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.healthy, server.output, server.workspace = True, output, None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    context = multiprocessing.get_context('spawn')
    cpu_queue = context.Queue()
    available = sorted(os.sched_getaffinity(0))
    cpu_queue.put(available[:4]); cpu_queue.put(available[4:8])
    pool = ProcessPoolExecutor(max_workers=2, mp_context=context, initializer=worker_init, initargs=(cpu_queue,))
    try:
        with httpx.Client(trust_env=False, timeout=2) as client:
            def healthy():
                try:
                    return client.get(endpoint + '/health').status_code == 200
                except httpx.HTTPError:
                    return False
            def submit(entry):
                return pool.submit(condition_worker, str(project), endpoint, str(key), {}, str(output), tasks[entry['task_id']], 'b1')
            state, active = bounded_admission(entries, submit, healthy,
                lambda entry, value: condition_infrastructure(output, entry),
                lambda state: write_json(run / 'checkpoint.json', state), concurrency=2)
        cleanup = stop_inflight(pool, active, output)
        workspace = server.workspace
        before = (workspace / 'heartbeat').read_text() if workspace else None
        namespace = (workspace / 'pid_namespace').read_text() if workspace else None
        time.sleep(.5)
        stopped = workspace is not None and (workspace / 'heartbeat').read_text() == before
        remaining = []
        for path in Path('/proc').glob('[0-9]*/ns/pid'):
            try:
                if namespace and os.readlink(path) == namespace:
                    remaining.append(str(path))
            except OSError:
                pass
        summary = {'passed': state['state'] == 'paused_infrastructure' and stopped and not remaining
                   and not cleanup['remaining_active_scopes'] and not cleanup['worker_alive'],
            'run_dir': str(run), 'benchmark_conditions_executed': 0, 'real_model_calls': 0,
            'state': state, 'cleanup': cleanup, 'heartbeat_stopped': stopped,
            'remaining_namespace_processes': remaining, 'frozen_old_worker_reused': True}
        write_json(run / 'summary.json', summary)
        print(json.dumps(summary, indent=2))
        if not summary['passed']:
            raise SystemExit(1)
    finally:
        if any(process.is_alive() for process in (pool._processes or {}).values()):
            stop_inflight(pool, {}, output)
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
