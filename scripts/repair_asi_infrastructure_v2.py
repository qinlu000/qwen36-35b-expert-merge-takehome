#!/usr/bin/env python3
"""Explicit manual ASI infrastructure retry with bounded admission and a breaker.

The original240 results are immutable. This separate attempt is authorized for
229 pre-generation failures and8 ambiguous disconnects, with the latter clearly
labelled a manual full-trial retry rather than a safe same-request HTTP retry.
The3 original received answers are always retained; there is no score selection.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import time

import httpx
from ai4sci_bench.runner.orchestrator import BenchmarkOrchestrator, RunConfig
from run_asi_baseline_v2 import BaselineDirectLLM, condition_worker, worker_init, write_json


def bounded_admission(entries, submit, healthy, is_infrastructure, checkpoint, concurrency=8, interval=.25):
    """Submit at most8 futures; a health/transport failure pauses the whole block."""
    pending = iter(entries)
    active = {}
    completed = []
    admitted = []
    exhausted = False
    reason = None
    while active or not exhausted:
        if not healthy():
            reason = 'endpoint_health_failed'
            break
        while len(active) < concurrency and not exhausted:
            if not healthy():
                reason = 'endpoint_health_failed_before_admission'
                break
            try:
                entry = next(pending)
            except StopIteration:
                exhausted = True
                break
            future = submit(entry)
            active[future] = entry
            admitted.append(entry['condition'])
            checkpoint({'state': 'running', 'admitted_this_session': admitted,
                        'completed_this_session': completed, 'active': [e['condition'] for e in active.values()]})
        if reason:
            break
        if not active:
            break
        done, _ = wait(active, timeout=interval, return_when=FIRST_COMPLETED)
        for future in done:
            entry = active.pop(future)
            try:
                value = future.result()
            except Exception as error:
                reason = 'worker_error:' + type(error).__name__
                break
            completed.append(entry['condition'])
            decision = is_infrastructure(entry, value)
            if decision:
                reason = 'pause_requires_audit:' + str(decision) + ':' + entry['condition']
                break
        if reason:
            break
    state = {'state': 'paused_infrastructure' if reason else 'completed', 'reason': reason,
             'admitted_this_session': admitted, 'completed_this_session': completed,
             'active': [entry['condition'] for entry in active.values()],
             'unsubmitted_this_session': len(entries) - len(admitted)}
    checkpoint(state)
    return state, active


def create_manifest(source, attempt):
    source_metadata = json.loads((source / 'asi_v2_run.json').read_text())
    audit = json.loads((source / 'infrastructure_audit_20261016.json').read_text())
    selected, frozen = [], []
    for entry in audit['conditions']:
        condition = entry['condition']
        task, level = condition.rsplit('__seed31415__', 1)
        item = {'condition': condition, 'task_id': task, 'level': level,
                'classification': entry['classification'], 'original_run': str(source),
                'original_result': str(source / task / (condition + '.json')),
                'original_response': str(source / 'audit' / (condition + '.response.json')),
                'dataset_seed': 31415, 'inference_seed': 0, 'manual_retry_index': 1,
                'attempt_dir': str(attempt), 'selection': 'first_received_valid_answer_chronologically'}
        if entry['classification'] in ('no_generation_attempt_tokenizer_or_admission_failure',
                                       'generation_attempted_transport_outcome_ambiguous'):
            assert not Path(item['original_response']).exists()
            item['manual_ambiguous_full_trial_retry'] = entry['classification'].endswith('ambiguous')
            selected.append(item)
        else:
            assert Path(item['original_response']).exists()
            item['manual_retry_index'] = 0
            frozen.append(item)
    assert len(selected) == 237 and len(frozen) == 3
    return {'schema_version': 1, 'repair_id': 'asi-v2-manual-infrastructure-attempt1-20261016',
        'source_run': str(source), 'attempt_dir': str(attempt),
        'source_run_metadata_sha256': hashlib.sha256((source / 'asi_v2_run.json').read_bytes()).hexdigest(),
        'source_protocol_sha256': source_metadata['protocol_sha256'],
        'source_runner_sha256': source_metadata['runner_sha256'],
        'manual_retry_index': 1, 'maximum_manual_full_trial_retries': 2,
        'authorization': 'Root explicitly authorized237 same-ID/seed/budget manual infrastructure retries;3 received answers remain frozen',
        'ambiguous_retry_disclosure': '8 requests were sent but disconnected. Their manual whole-trial retry is distinct from safe HTTP retry; original costs/artifacts retained.',
        'selection_rule': 'First received valid answer in chronological attempt order, including failed executions; no score-based selection',
        'selected_conditions': selected, 'frozen_original_answers': frozen}


def condition_infrastructure(attempt, entry):
    response = attempt / 'audit' / (entry['condition'] + '.response.json')
    if response.is_file():
        return False  # Any received answer is frozen, including parse/exec failures.
    result_path = attempt / entry['task_id'] / (entry['condition'] + '.json')
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    if result.get('execution_time_seconds', 0) >= 1199:
        return False  # The genuine fixed1200s solver budget is not retryable infra.
    path = attempt / 'audit' / (entry['condition'] + '.request.json')
    if not path.exists():
        return 'unknown_missing_audit_not_retry_authorization'
    audit = json.loads(path.read_text())
    events = audit['events']
    if any(event['event'] == 'generation_complete' for event in events):
        return False
    guards = [event for event in events if event['event'] == 'guard']
    if guards and guards[0]['prompt_tokens'] > 57344:
        return False  # Fixed-context domain failure, not endpoint unavailability.
    if any(event['event'] in ('ambiguous_transport_failure_no_retry', 'transport_failed_before_send') for event in events):
        return 'transport_failure_review_required'
    return 'unknown_before_answer_review_required'


def stop_inflight(pool, active, attempt):
    """Close controller sockets and kill only scopes owned by this repair run."""
    scopes = set()
    processes = list((pool._processes or {}).values())
    for process in processes:
        if process.is_alive():
            os.kill(process.pid, signal.SIGSTOP)
    parent_ids = {process.pid for process in processes}
    parents = {}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            try:
                fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
                parents[int(path.name)] = int(fields[1])
            except (OSError, IndexError, ValueError):
                pass
    owned = set(parent_ids)
    while True:
        expanded = owned | {pid for pid, parent in parents.items() if parent in owned}
        if expanded == owned:
            break
        owned = expanded
    for pid in owned:
        try:
            os.kill(pid, signal.SIGSTOP)
            group = Path(f'/proc/{pid}/cgroup').read_text().strip().split('::', 1)[1]
            unit = Path(group).name
            if unit.startswith('apex-asi-') and unit.endswith('.scope'):
                scopes.add(unit)
        except (ProcessLookupError, FileNotFoundError):
            pass
    for entry in active.values():
        path = attempt / 'audit' / (entry['condition'] + '.limits.json')
        if path.exists():
            unit = Path(json.loads(path.read_text())['cgroup']).name
            if not unit.startswith('apex-asi-') or not unit.endswith('.scope'):
                raise RuntimeError('Unexpected owned ASI scope name')
            scopes.add(unit)
    for unit in scopes:
        subprocess.run(['systemctl', '--user', 'kill', '--signal=KILL', unit],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        subprocess.run(['systemctl', '--user', 'stop', unit],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    for pid in owned:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    for future in active:
        future.cancel()
    pool.shutdown(wait=True, cancel_futures=True)
    remaining = []
    for unit in scopes:
        result = subprocess.run(['systemctl', '--user', 'is-active', unit], capture_output=True, text=True)
        if result.returncode == 0:
            remaining.append(unit)
    return {'stopped_worker_pids': [process.pid for process in processes],
            'owned_scopes': sorted(scopes), 'remaining_active_scopes': remaining,
            'worker_alive': [process.pid for process in processes if process.is_alive()]}


def save_selection(attempt, manifest):
    entries = []
    for entry in manifest['frozen_original_answers'] + manifest['selected_conditions']:
        condition = entry['condition']
        if entry['manual_retry_index'] == 0:
            chosen_run = Path(entry['original_run'])
            status = 'original_answer_frozen'
        else:
            chosen_run = attempt
            audit_path = attempt / 'audit' / (condition + '.request.json')
            audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
            # The frozen runner persists a full response before execution, but
            # writes its lifecycle audit in finally. Cancellation can therefore
            # leave a received answer with no final audit/result yet. Freeze it.
            valid = (attempt / 'audit' / (condition + '.response.json')).is_file()
            status = 'first_received_retry_answer' if valid else 'no_valid_received_retry_answer'
        entries.append({'condition': condition, 'status': status, 'run': str(chosen_run),
            'result': str(chosen_run / entry['task_id'] / (condition + '.json')),
            'response': str(chosen_run / 'audit' / (condition + '.response.json')),
            'original_result_retained': entry['original_result']})
    write_json(attempt / 'first_valid_selection.json', {'expected_conditions': 240,
        'selection_rule': manifest['selection_rule'], 'entries': entries})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--attempt-dir', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--parallel', type=int, default=8, choices=range(1, 9))
    parser.add_argument('--cpu-offset', type=int, default=0)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    root, source, attempt = args.project.resolve(), args.source_run.resolve(), args.attempt_dir.resolve()
    if source == attempt:
        raise ValueError('Infrastructure retry must use a separate attempt directory')
    attempt.mkdir(parents=True, exist_ok=True)
    lock_stream = (attempt / '.repair-controller.lock').open('a')
    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    snapshot = {}
    for journal in (source / 'audit').glob('*.started.json'):
        workspace = Path(json.loads(journal.read_text())['workspace'])
        stat = workspace.stat()
        snapshot[journal.name] = {'workspace': str(workspace), 'device': stat.st_dev, 'inode': stat.st_ino}
    assert len(snapshot) == 240
    symlinks = {}
    for path in (source / 'instances/_workspaces').rglob('*'):
        if path.is_symlink():
            stat = path.lstat()
            symlinks[str(path.relative_to(source))] = {'target': os.readlink(path),
                'device': stat.st_dev, 'inode': stat.st_ino}
    snapshot = {'physical_workspaces': snapshot, 'workspace_symlinks': symlinks}
    snapshot_path = attempt / 'source_workspace_snapshot.json'
    if snapshot_path.exists() and json.loads(snapshot_path.read_text()) != snapshot:
        raise ValueError('An original physical workspace changed; preserve and audit before repair')
    write_json(snapshot_path, snapshot)
    manifest = create_manifest(source, attempt)
    manifest_path = attempt / 'manual_retry_manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError('Refuse to change the explicit manual retry manifest')
    write_json(manifest_path, manifest)
    original = json.loads((source / 'asi_v2_run.json').read_text())
    if hashlib.sha256((root / 'scripts/run_asi_baseline_v2.py').read_bytes()).hexdigest() != original['runner_sha256']:
        raise ValueError('Frozen original ASI runner changed')
    if hashlib.sha256((root / 'scripts/asi_baseline_limits.py').read_bytes()).hexdigest() != original['limits_sha256']:
        raise ValueError('Frozen original ASI limits changed')
    cpu_list = sorted(os.sched_getaffinity(0))
    cpu_sets = [cpu_list[args.cpu_offset + i * 4:args.cpu_offset + (i + 1) * 4] for i in range(args.parallel)]
    if any(len(group) != 4 for group in cpu_sets):
        raise ValueError('Insufficient CPU sets for the fixed trial resources')
    write_json(attempt / 'repair_metadata.json', {'source_run_metadata_sha256': manifest['source_run_metadata_sha256'],
        'endpoint': args.endpoint, 'parallel': args.parallel, 'cpu_sets': cpu_sets,
        'repair_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'policy': 'same frozen ASI source/parameters/resources; no same-request transport retry changes'})
    save_selection(attempt, manifest)
    if args.prepare_only:
        print(json.dumps({'selected': 237, 'frozen_original_answers': 3, 'model_requests': 0}))
        return
    write_json(attempt / 'repair_controller.json', {'pid': os.getpid(),
        'started_at': datetime.now(timezone.utc).isoformat(), 'flock': str(attempt / '.repair-controller.lock'),
        'source_physical_workspaces_preserved': 240,
        'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    key = args.key_file.read_text().strip()
    def healthy():
        try:
            with httpx.Client(trust_env=False, timeout=2, headers={'Authorization': 'Bearer ' + key}) as client:
                response = client.get(args.endpoint.rstrip('/') + '/health')
            return response.status_code == 200
        except httpx.HTTPError:
            return False
    if not healthy():
        write_json(attempt / 'infrastructure_checkpoint.json', {'state': 'paused_infrastructure',
            'reason': 'initial_health_failed', 'admitted_this_session': [], 'unsubmitted_this_session': 237})
        return
    protocol = json.loads((root / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    if hashlib.sha256((root / 'configs/eval/protocol_v2_unified64k8k.json').read_bytes()).hexdigest() != original['protocol_sha256']:
        raise ValueError('Frozen ASI protocol changed; manual repair requires the original protocol')
    adapter = BaselineDirectLLM(endpoint=args.endpoint, key_file=args.key_file, protocol=protocol,
        ngspice_root=root / 'artifacts/tools/ngspice', audit_dir=attempt / 'audit')
    config = RunConfig(agent=adapter, sandbox='task', tasks_dir=str(root / 'artifacts/benchmarks/asi/tasks'),
                       output_dir=str(attempt), score=False, analyze=False)
    orchestrator = BenchmarkOrchestrator(config)
    task_ids = list(dict.fromkeys(entry['task_id'] for entry in manifest['selected_conditions']))
    tasks = {task['id']: task for task in orchestrator._load_tasks(task_ids)}
    entries = []
    for entry in manifest['selected_conditions']:
        if (attempt / entry['task_id'] / (entry['condition'] + '.json')).exists():
            continue
        entry = dict(entry)
        entry['resume_interrupted_without_generation'] = (attempt / 'audit' / (entry['condition'] + '.started.json')).exists()
        entries.append(entry)
    context = multiprocessing.get_context('spawn')
    cpu_queue = context.Queue()
    for group in cpu_sets:
        cpu_queue.put(group)
    pool = ProcessPoolExecutor(max_workers=args.parallel, mp_context=context,
                               initializer=worker_init, initargs=(cpu_queue,))
    def submit(entry):
        return pool.submit(condition_worker, str(root), args.endpoint, str(args.key_file.resolve()),
            protocol, str(attempt), tasks[entry['task_id']], entry['level'])
    def checkpoint(state):
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_json(attempt / 'infrastructure_checkpoint.json', state)
        save_selection(attempt, manifest)
    try:
        state, active = bounded_admission(entries, submit, healthy,
            lambda entry, value: not entry['resume_interrupted_without_generation'] and condition_infrastructure(attempt, entry),
            checkpoint, args.parallel)
        if state['state'] == 'paused_infrastructure':
            state['cleanup'] = stop_inflight(pool, active, attempt)
            checkpoint(state)
        else:
            pool.shutdown(wait=True)
    except BaseException:
        stop_inflight(pool, {}, attempt)
        raise


if __name__ == '__main__':
    main()
