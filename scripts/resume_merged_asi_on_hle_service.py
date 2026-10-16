"""Reuse the existing normal-queue AVG64 HLE replica after its generation drains."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import time

import httpx

from run_direct_formal_pipeline import acceptance, launch, save


def now():
    return datetime.now(timezone.utc)


def live(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().rsplit(')', 1)[1].split()[0] != 'Z'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    output = root / 'artifacts/eval/merged_asi_existing_hle_service_20261017'
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (output / 'launch.json').exists(), 'Retain existing launch; never start a duplicate coordinator'
    cutoff = datetime.fromisoformat('2026-10-17T18:20:00+00:00')
    hle = root / 'artifacts/eval/avg64_hle2500_20261017'
    asi = root / 'artifacts/eval/avg64_asi240_20261017'
    source = root / 'artifacts/eval/asi128_asi240_20261017/generation_cpu_finished.json'
    endpoint = 'http://127.0.0.1:28095'
    while now() < cutoff:
        gate = json.loads(source.read_text()) if source.exists() else {}
        path = hle / 'summary.json'
        summary = json.loads(path.read_text()) if path.exists() else {}
        launch_path = hle / 'controller/launch.json'
        hle_launch = json.loads(launch_path.read_text()) if launch_path.exists() else {}
        marker_path = hle / 'model-consumer-finished.json'
        marker = json.loads(marker_path.read_text()) if marker_path.exists() else {}
        migration = root / 'artifacts/eval/hle_normal_migration_20261017/state.json'
        migration_state = json.loads(migration.read_text()) if migration.exists() else {}
        # The dedicated HLE migration writes a native verified normal-service receipt.
        config = json.loads((root / 'configs/eval/hle_dedicated_formal_20261017.json').read_text())['merged']
        ready = (gate.get('state') == 'finished' and gate.get('completed_conditions') == 240
            and gate.get('worker_pool_shutdown') is True and gate.get('active_owned_scopes') == []
            and summary.get('saved_results') == 2500 and summary.get('controller_state') == 'completed'
            and hle_launch.get('generation_pid') and not live(hle_launch['generation_pid'])
            and marker.get('model_consumer_finished') is True and marker.get('saved_results') == 2500
            and marker.get('generation_pid') == hle_launch['generation_pid']
            and not (hle / 'STOP_ADMISSION').exists()
            and config.get('endpoint') == endpoint and config.get('partition') == 'acd_u'
            and config.get('service_job_id') != 727822)
        save(output / 'state.json', {'state': 'waiting_existing_replica_and_cpu',
            'at_utc': now().isoformat(), 'pid': os.getpid(), 'endpoint': endpoint,
            'expert_generation_cpu_ready': gate.get('state') == 'finished',
            'hle_saved_results': summary.get('saved_results', 0),
            'hle_generation_pid': hle_launch.get('generation_pid'),
            'normal_service_job': config.get('service_job_id'),
            'migration_state': migration_state.get('state'), 'new_gpu_allocations': 0})
        if not ready:
            time.sleep(15)
            continue
        # The original merged ASI was never admitted. Preserve the user's release
        # receipt; do not recreate its old endpoint or allocate replacement GPUs.
        assert not asi.exists(), 'Existing ASI generation requires audit, not another launch'
        key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
        with httpx.Client(trust_env=False, timeout=5, headers={'Authorization': 'Bearer ' + key}) as client:
            try:
                if client.get(endpoint + '/health').status_code != 200:
                    time.sleep(15)
                    continue
                response = client.get(endpoint + '/metrics')
                response.raise_for_status()
                counts = re.findall(r'^vllm:num_requests_(?:running|waiting)(?:\{[^\n]*\})?\s+([0-9.eE+-]+)', response.text, re.M)
                if len(counts) < 2 or any(float(value) != 0 for value in counts):
                    time.sleep(15)
                    continue
            except httpx.HTTPError:
                time.sleep(15)
                continue
        acceptance(root, endpoint, {'asi': 'apex-avg64', 'hle': 'apex-avg64'}, output)
        command = [str(root / 'artifacts/envs/asi-py312/bin/python'),
            str(root / 'scripts/run_direct_formal_pipeline.py'), '--project', str(root),
            '--profile', 'merged', '--endpoint', endpoint]
        process = launch(command, output / 'pipeline.log', root)
        save(output / 'launch.json', {'at_utc': now().isoformat(), 'pid': process.pid,
            'command': command, 'endpoint': endpoint, 'reused_service_job': config['service_job_id'],
            'expert_generation_cpu_marker': str(source), 'hle_generation_summary': str(path),
            'new_gpu_allocations': 0, 'original_727654_remains_released': True})
        save(output / 'state.json', {'state': 'merged_asi_coordinator_started',
            'at_utc': now().isoformat(), 'pid': process.pid, 'new_gpu_allocations': 0})
        return
    save(output / 'state.json', {'state': 'core_cutoff_no_new_launch',
        'at_utc': now().isoformat(), 'new_gpu_allocations': 0})


if __name__ == '__main__':
    os.umask(0o077)
    main()
