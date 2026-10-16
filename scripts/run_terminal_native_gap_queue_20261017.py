#!/usr/bin/env python3
"""Grade six retained answers once, sharing CPU92-95 with the ASI grader."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from terminal_verifier_evidence import verifier_infra_reason

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
REPAIR = ROOT / 'artifacts/recovery/terminal-v2/native-gaps-20261017'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def busy_scopes():
    busy = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            scope = (process / 'cgroup').read_text()
            if (any(prefix in scope for prefix in ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and set(range(92, 96)).intersection(os.sched_getaffinity(int(process.name)))):
                busy.add(scope.strip().split('/')[-1])
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return sorted(busy)


def grade(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    reward = ((data.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (data.get('exception_info') or {}).get('exception_type')
    reason = verifier_infra_reason(data)
    valid = reward in (0, 1) and exception is None and not reason
    return {'path': str(path), 'reward': reward if valid else None,
            'valid': valid, 'exception': exception, 'verifier_issue': reason, 'new_model_calls': 0}


def label(row):
    return row['key'].replace('/seed', '__seed') + row.get('attempt_tag', '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'logs').mkdir(exist_ok=True)
    control = (output / '.controller.lock').open('a+')
    fcntl.flock(control, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lease = (ROOT / 'artifacts/eval/direct_asi_grader_cpu92_95.lock').open('a+')
    plan = json.loads((REPAIR / 'plan.json').read_text())
    terminal, active = {}, {}
    state = 'waiting_shared_cpu_lease'

    def checkpoint():
        pending = [row['key'] for row in plan['entries'] if row['key'] not in terminal and row['key'] not in active]
        value = {'updated_at_utc': now(), 'pid': os.getpid(), 'expected': 6, 'state': state,
                 'active': active, 'pending': pending, 'terminal': terminal,
                 'valid_scored': sum(bool(v and v['valid']) for v in terminal.values()),
                 'new_model_calls': 0, 'cpu_ids': [92, 93, 94, 95], 'memory_mb': 8192,
                 'native_verifier_seconds': 900, 'shared_lease_lock': str(lease.name)}
        save(output / 'checkpoint.json', value)
        source = json.loads(Path(plan['source_summary']).read_text())
        accepted = dict(source.get('accepted_first_valid') or source['accepted'])
        accepted.update({k: v for k, v in terminal.items() if v and v['valid']})
        valid = len(accepted)
        summary = {'updated_at_utc': now(), 'expected': 445, 'expected_trials': 445,
                   'valid_scored': valid, 'valid_covered': valid, 'active_trials': len(active),
                   'pending_not_admitted': len(pending), 'infrastructure_unscored': 445 - valid - len(active) - len(pending),
                   'complete': valid == 445, 'accepted': accepted, 'accepted_first_valid': accepted,
                   'original_summary': plan['source_summary'], 'new_model_calls': 0,
                   'primary_mean_percent': None, 'mean_percent': None, 'sample_sd_percent_ddof1': None,
                   'selection': 'Retain 436 original valid results and accept only native grades of the six frozen archived answers.'}
        save(output / 'corrected445_summary.json', summary)
        return pending

    for row in plan['entries']:
        result = output / 'trials' / label(row) / 'result.json'
        if result.parent.exists():
            terminal[row['key']] = grade(result) or {'valid': False, 'reward': None,
                'path': str(result), 'verifier_issue': 'Existing incomplete attempt retained; no automatic retry'}
    while checkpoint():
        ready = [row for row in plan['entries'] if row['key'] not in terminal and
                 (not row['cache_receipt'] or (Path(row['cache_receipt']).exists() and
                    json.loads(Path(row['cache_receipt']).read_text()).get('ready')))]
        if not ready:
            state = 'waiting_exact_dependency_cache'
            time.sleep(5)
            continue
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            state = 'waiting_shared_cpu_lease'
            time.sleep(5)
            continue
        busy = busy_scopes()
        if busy:
            fcntl.flock(lease, fcntl.LOCK_UN)
            state = 'waiting_cpu_scope_drain'
            save(output / 'lease-gate.json', {'updated_at_utc': now(), 'busy_scopes': busy})
            time.sleep(5)
            continue
        row = ready[0]
        key = row['key']
        trial_name = label(row)
        directory = output / 'trials' / trial_name
        command = [sys.executable, str(Path(__file__).with_name('run_terminal_native_gap_grade_20261017.py')),
                   '--original-result', row['original_result'], '--restore-manifest', row['restore_manifest'],
                   '--output', str(directory), '--cpu-offset', '92']
        active[key] = {'started_at_utc': now(), 'cpu_ids': [92, 93, 94, 95], 'child_pid': None}
        state = 'native_grading'
        checkpoint()
        with (output / 'logs' / (trial_name + '.log')).open('a') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, pass_fds=(lease.fileno(),))
            active[key]['child_pid'] = child.pid
            checkpoint()
            print(json.dumps({'event': 'native_start', 'key': key, 'pid': child.pid, 'at_utc': now()}), flush=True)
            while child.poll() is None:
                time.sleep(5)
                checkpoint()
        # Hold the shared lock until container cleanup has actually drained.
        while busy_scopes():
            state = 'waiting_owned_scope_cleanup'
            checkpoint()
            time.sleep(5)
        terminal[key] = grade(directory / 'result.json') or {'valid': False, 'reward': None,
            'path': str(directory / 'result.json'), 'verifier_issue': 'Child exited without native result'}
        terminal[key]['child_returncode'] = child.returncode
        active.pop(key)
        fcntl.flock(lease, fcntl.LOCK_UN)
        state = 'yielding_shared_cpu_lease'
        checkpoint()
        print(json.dumps({'event': 'native_done', 'key': key, **terminal[key], 'at_utc': now()}), flush=True)
        if not terminal[key]['valid'] and not (directory / 'verifier/test-stdout.txt').exists():
            state = 'paused_setup_failure'
            checkpoint()
            return
        time.sleep(10)
    state = 'finished'
    checkpoint()
    save(output / 'all_cpu_consumers_finished.json', {'updated_at_utc': now(), 'cpu_consumers_finished': True,
        'active_scopes': busy_scopes(), 'new_model_calls': 0, 'native_attempts_finished': len(terminal),
        'valid_scored': sum(bool(v and v['valid']) for v in terminal.values())})


if __name__ == '__main__':
    main()
