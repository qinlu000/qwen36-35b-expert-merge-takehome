"""Wait for the new HLE service, drain the old leaf, then admit fifty new tasks."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import httpx

from run_hle_v2 import save

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
SOURCE = ROOT / 'artifacts/runs/base_hle_v2_724196'
CANONICAL = ROOT / 'artifacts/runs/base_hle_v2_724196_infra1'
PREVIOUS = ROOT / 'artifacts/runs/base_hle_v2_724196_seq20'
OUTPUT = ROOT / 'artifacts/runs/base_hle_v2_724196_seq50'


def load(path):
    return json.loads(path.read_text())


def running(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().rsplit(')', 1)[1].split()[0] != 'Z'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-pid', type=int, default=2880402)
    parser.add_argument('--route-file', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    owner = (OUTPUT / 'handoff-controller.lock').open('a')
    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def state(stage, **fields):
        save(OUTPUT / 'handoff-controller-state.json', {
            'at_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
            'stage': stage, 'old_pid': args.old_pid, 'new_model_calls': 0, **fields})

    # The backend fills this route only after the actual seq50 model and tunnel are ready.
    with httpx.Client(trust_env=False) as client:
        while True:
            route = load(args.route_file)
            assert route['solver_concurrency'] == 50 and route['engine_max_num_seqs'] == 50
            healthy = False
            if route.get('ready') and route.get('endpoint') and route.get('job_id'):
                try:
                    healthy = client.get(route['endpoint'].rstrip('/') + '/health', timeout=3).status_code == 200
                except httpx.HTTPError:
                    pass
            if healthy:
                break
            state('waiting_for_seq50_service', route=route)
            time.sleep(5)

    stopped_at = datetime.now(timezone.utc).isoformat()
    save(PREVIOUS / 'STOP_ADMISSION', {'at_utc': stopped_at, 'reason': 'user_authorized_50_concurrency_handoff',
                                      'new_endpoint': route['endpoint']})
    state('draining_seq20_without_cancellation', route=route)
    while running(args.old_pid):
        checkpoint = load(PREVIOUS / 'checkpoint.json')
        state('draining_seq20_without_cancellation', route=route,
              active_count=len(checkpoint.get('active', [])),
              completed_count=len(checkpoint.get('completed', [])))
        time.sleep(1)

    with (PREVIOUS / 'controller.lock').open('a') as old_lock, (ROOT / 'artifacts/runs/base_model_block.lock').open('a') as block:
        fcntl.flock(old_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(block, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous_summary = load(PREVIOUS / 'summary.json')
        assert previous_summary['state'] in ('drained', 'completed')
        assert not previous_summary['cancelled_or_unwinding']
        prior = OUTPUT / 'prior_seq20'
        prior.mkdir(exist_ok=True)
        (OUTPUT / 'questions').mkdir(exist_ok=True)
        for name in ('checkpoint.json', 'repair_config.json', 'first_valid_selection.json', 'summary.json'):
            if (PREVIOUS / name).exists():
                shutil.copy2(PREVIOUS / name, prior / name)
        manifest = load(PREVIOUS / 'manual_retry_manifest.json')
        retained = [dict(item, generate=False) for item in manifest['retained']]
        selected, retained_invalid = [], []
        for item in manifest['selected']:
            path = PREVIOUS / 'questions' / (item['id'] + '.json')
            if path.exists():
                record = load(path)
                assert record.get('finished_at_utc')
                retained.append(dict(item, original_result=str(path.resolve()), generate=False,
                                     classification='existing_seq20_terminal_result_retained'))
                if record.get('infrastructure_failure'):
                    retained_invalid.append(item['id'])
                continue
            if path.with_suffix('.started.json').exists():
                raise RuntimeError('Original started task lacks its terminal record: ' + item['id'])
            # Keep the original manual retry index and earlier cost/error paths unchanged.
            selected.append(dict(item, generate=True))
        assert len(retained) + len(selected) == 2500
        assert all(item['manual_retry_index'] in (1, 2) for item in selected)
        next_manifest = {**manifest, 'retained': retained, 'selected': selected,
                         'selection_rule': manifest['selection_rule'] + '; seq50 natural handoff transfers only never-started entries; no new retry index',
                         'seq50_handoff': {'at_utc': stopped_at, 'previous_output': str(PREVIOUS),
                                          'new_endpoint': route['endpoint'], 'retained_invalid_ids': retained_invalid,
                                          'new_infrastructure_retries': 0}}
        save(OUTPUT / 'manual_retry_manifest.json', next_manifest)
        for item in selected:
            path = CANONICAL / 'questions' / (item['id'] + '.json')
            link = path.with_suffix('.seq50-link')
            link.symlink_to(OUTPUT / 'questions' / path.name)
            link.replace(path)

    argv = [str(ROOT / 'artifacts/envs/hle/bin/python'), '-u',
            str(ROOT / 'scripts/repair_hle_concurrency50_v4.py'),
            '--source', str(SOURCE), '--output', str(OUTPUT),
            '--canonical-retry', str(CANONICAL), '--route-file', str(args.route_file),
            '--key-file', str(ROOT / 'artifacts/private/base_smoke_api_key')]
    with (OUTPUT / 'controller.log').open('ab', buffering=0) as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    # A real new-leaf admission confirms successful startup; no synthetic request is made.
    while True:
        if child.poll() is not None:
            raise RuntimeError('New HLE leaf exited during startup; keep the old model role reserved')
        checkpoint_path = OUTPUT / 'checkpoint.json'
        if checkpoint_path.exists() and load(checkpoint_path).get('admitted'):
            break
        time.sleep(0.2)
    targets_path = ROOT / 'artifacts/runs/base-terminal-recovery-v2-20261016/model-route-targets.json'
    with targets_path.with_suffix('.lock').open('a') as target_lock:
        fcntl.flock(target_lock, fcntl.LOCK_EX)
        targets = load(targets_path)
        target = {'url': 'http://127.0.0.1:28085', 'job_id': 726629,
                  'allocation_end_time': '2026-10-18T07:02:51+08:00', 'max_num_seqs': 20}
        if not any(item['url'] == target['url'] for item in targets['new_targets']):
            targets['new_targets'].append(target)
            save(targets_path, targets)
    receipt = {'at_utc': datetime.now(timezone.utc).isoformat(), 'pid': child.pid, 'old_pid': args.old_pid,
               'old_process_exited': True, 'old_locks_released': True, 'stop_admission_at_utc': stopped_at,
               'route': route, 'argv': argv, 'retained': len(retained), 'selected': len(selected),
               'selected_retry_indices': {str(index): sum(item['manual_retry_index'] == index for item in selected)
                                          for index in (1, 2)},
               'new_infrastructure_retries': 0, 'retained_invalid_ids': retained_invalid,
               'canonical_retry': str(CANONICAL), 'new_completion': str(OUTPUT / 'summary.json'),
               'judge_budget_restarted': False, 'old_service_transferred_to_terminal': target}
    save(OUTPUT / 'handoff-receipt.json', receipt)
    save(PREVIOUS / 'model-consumer-finished.json', {'state': 'completed', 'at_utc': receipt['at_utc'],
         'old_pid': args.old_pid, 'all_solver_consumers_finished': True,
         'natural_drain_without_cancellation': True, 'new_pid': child.pid,
         'role_finished': 'hle', 'role_transferred_to_terminal': True,
         'receipt': str(OUTPUT / 'handoff-receipt.json')})
    state('launched_seq50', new_pid=child.pid, retained=len(retained), selected=len(selected),
          new_infrastructure_retries=0)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
