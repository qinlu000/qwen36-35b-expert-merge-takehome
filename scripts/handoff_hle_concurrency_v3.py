"""Explicit HLE service handoff; preserve terminal answers and classify cancelled infra2."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from run_hle_v2 import save

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
SOURCE = ROOT / 'artifacts/runs/base_hle_v2_724196'
CANONICAL = ROOT / 'artifacts/runs/base_hle_v2_724196_infra1'
OUTPUT = ROOT / 'artifacts/runs/base_hle_v2_724196_seq20'


def load(path):
    return json.loads(path.read_text())


def running(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().rsplit(')', 1)[1].split()[0] != 'Z'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-pid', type=int, default=3887939)
    parser.add_argument('--route-file', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    route = load(args.route_file)
    assert route['solver_concurrency'] == 8 and route['engine_max_num_seqs'] == 20
    plan = {'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'old_pid': args.old_pid,
            'old_retry': str(CANONICAL), 'output': str(OUTPUT), 'route': route,
            'completion': str(OUTPUT / 'summary.json'), 'new_model_calls_during_preparation': 0,
            'policy': 'Retain every raw answer and normal budget end. Only <=8 explicitly cancelled unfinished retry1 records become infra2; never-started remain retry1.'}
    if not args.execute:
        save(OUTPUT / 'handoff-plan.json', plan)
        print(json.dumps(plan))
        return

    command = (Path('/proc') / str(args.old_pid) / 'cmdline').read_bytes().replace(b'\0', b' ')
    assert b'repair_hle_infrastructure_v2.py' in command and str(CANONICAL).encode() in command
    active_before = load(CANONICAL / 'checkpoint.json').get('active', [])
    assert len(active_before) <= 8
    stopped_at = datetime.now(timezone.utc).isoformat()
    os.kill(args.old_pid, signal.SIGINT)
    deadline = time.monotonic() + 90
    while running(args.old_pid):
        if time.monotonic() > deadline:
            raise RuntimeError('Original HLE process did not exit after SIGINT; do not launch another owner')
        time.sleep(0.2)

    # Prove that the original solver owner released both locks before changing routes.
    with (CANONICAL / 'controller.lock').open('a') as old_lock, (ROOT / 'artifacts/runs/base_model_block.lock').open('a') as block:
        fcntl.flock(old_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(block, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = OUTPUT / 'prior_retry1'
        prior.mkdir(exist_ok=True)
        (OUTPUT / 'questions').mkdir(exist_ok=True)
        for name in ('checkpoint.json', 'repair_config.json', 'first_valid_selection.json'):
            shutil.copy2(CANONICAL / name, prior / name)
        original = load(CANONICAL / 'manual_retry_manifest.json')
        retained = [dict(item, generate=False) for item in original['retained']]
        selected, cancelled = [], []
        for item in original['selected']:
            path = CANONICAL / 'questions' / (item['id'] + '.json')
            entry = dict(item, generate=True)
            if path.exists():
                record = load(path)
                normal_timeout = (record.get('error_type') == 'TimeoutError' and
                                  record.get('elapsed_seconds', 0) >= 299 and
                                  not record.get('infrastructure_failure'))
                if record.get('raw_response') or normal_timeout or record.get('status') == 'context_overflow':
                    retained.append(dict(item, original_result=str(path.resolve()), generate=False,
                                         classification='existing_retry1_terminal_result_retained'))
                    continue
                if not (record.get('infrastructure_failure') and record.get('error_type') == 'CancelledError'
                        and record.get('manual_retry_index') == 1
                        and record.get('finished_at_utc', '') >= stopped_at):
                    raise RuntimeError('Unclassified existing HLE record requires audit: ' + item['id'])
                preserved = prior / (item['id'] + '.json')
                shutil.copy2(path, preserved)
                started = path.with_suffix('.started.json')
                if started.exists():
                    shutil.copy2(started, prior / started.name)
                entry.update(manual_retry_index=2, prior_retry_result=str(preserved),
                             infrastructure_retry_reason='explicit_user_authorized_seq20_service_handoff')
                cancelled.append(item['id'])
            elif path.with_suffix('.started.json').exists():
                raise RuntimeError('Started HLE journal has no terminal cancellation record: ' + item['id'])
            selected.append(entry)
        assert len(cancelled) <= 8 and len(retained) + len(selected) == 2500
        manifest = {**original, 'retained': retained, 'selected': selected,
                    'selection_rule': original['selection_rule'] + '; controlled seq20 handoff preserves all complete retry1/raw/normal-timeout records; only explicit unfinished cancellation may use infra2',
                    'migration': {'at_utc': stopped_at, 'previous_retry': str(CANONICAL),
                                  'cancelled_retry1_ids': cancelled, 'new_endpoint': route['endpoint']}}
        save(OUTPUT / 'manual_retry_manifest.json', manifest)
        # The running Judge has loaded the canonical manifest and polls these paths.
        # Atomic per-question links expose new results without changing its budget or inputs.
        for entry in selected:
            path = CANONICAL / 'questions' / (entry['id'] + '.json')
            link = path.with_suffix('.handoff-link')
            link.symlink_to(OUTPUT / 'questions' / path.name)
            link.replace(path)

    argv = [str(ROOT / 'artifacts/envs/hle/bin/python'), '-u',
            str(ROOT / 'scripts/repair_hle_concurrency_handoff_v3.py'),
            '--source', str(SOURCE), '--output', str(OUTPUT),
            '--canonical-retry', str(CANONICAL), '--route-file', str(args.route_file),
            '--key-file', str(ROOT / 'artifacts/private/base_smoke_api_key')]
    with (OUTPUT / 'controller.log').open('ab', buffering=0) as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    receipt = {**plan, 'sigint_at_utc': stopped_at, 'old_process_exited': True,
               'old_locks_released': True, 'pid': child.pid, 'argv': argv,
               'retained': len(retained), 'selected': len(selected), 'active_ids_before_sigint': active_before,
               'infra2_ids': cancelled,
               'judge_compatibility': 'Canonical question symlinks; existing Judge inputs/results/budget stay intact. Its loaded entry metadata remains retry1; new solver records and this manifest identify actual infra2.'}
    save(OUTPUT / 'handoff-receipt.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
