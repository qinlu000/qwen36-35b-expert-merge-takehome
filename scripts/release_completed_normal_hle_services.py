"""Release ordinary HLE replicas after their exact model consumers finish."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

import httpx

from run_direct_formal_pipeline import save


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    output = root / 'artifacts/eval/normal_hle_service_release_20261017'
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'ConnectTimeout=8', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
        '-o', 'UserKnownHostsFile=' + str(root / 'artifacts/private/baseline_hpc_known_hosts'),
        '-i', '/home/caoqinlu/.ssh/id_ed25519_hpc3_hkustgz', 'qinlucao@10.120.81.30']
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    released = read(output / 'state.json').get('released', {})
    sources = {
        'expert': ('hle250_hle2500_20261017', 28094),
        'controls': ('hle_task_controls_20261017', 28096),
        'merged': ('avg64_asi240_20261017', 28095),
    }
    while len(released) != 3:
        migration = read(root / 'artifacts/eval/hle_normal_migration_20261017/state.json')
        for profile, (folder, port) in sources.items():
            if profile in released:
                continue
            replica = migration.get('profiles', {}).get(profile, {})
            if replica.get('phase') != 'resumed':
                continue
            dest = root / 'artifacts/eval' / folder
            filename = 'generation_cpu_finished.json' if profile == 'merged' else 'model-consumer-finished.json'
            marker = read(dest / filename)
            if profile == 'controls':
                ready = marker.get('model_consumer_finished') is True and marker.get('total_saved_results') == 5000
            elif profile == 'merged':
                reuse = read(root / 'artifacts/eval/merged_asi_existing_hle_service_20261017/launch.json')
                ready = (marker.get('state') == 'finished' and marker.get('completed_conditions') == 240
                    and marker.get('worker_pool_shutdown') is True and marker.get('active_owned_scopes') == []
                    and reuse.get('reused_service_job') == replica['new_job'])
            else:
                ready = marker.get('model_consumer_finished') is True and marker.get('saved_results') == 2500
            if not ready:
                continue
            try:
                with httpx.Client(trust_env=False, timeout=5, headers={'Authorization': 'Bearer ' + key}) as client:
                    text = client.get('http://127.0.0.1:' + str(port) + '/metrics')
                    text.raise_for_status()
                    values = re.findall(r'^vllm:num_requests_(?:running|waiting)(?:\{[^\n]*\})?\s+([0-9.eE+-]+)', text.text, re.M)
                    if len(values) < 2 or any(float(v) != 0 for v in values):
                        continue
            except httpx.HTTPError:
                continue
            job = str(replica['new_job'])
            raw = subprocess.check_output(ssh + [shlex.join(['scontrol', 'show', 'job', '-o', job])], text=True)
            fields = dict(re.findall(r'(\w+)=([^ ]*)', raw))
            assert fields['Partition'] == 'acd_u' and fields['UserId'].startswith('qinlucao(')
            assert fields['WorkDir'] == '/data/user/qinlucao/projects/apex-takehome'
            assert fields['JobState'] == 'RUNNING'
            subprocess.run(ssh + [shlex.join(['scancel', job])], check=True)
            released[profile] = {'job_id': int(job), 'gpus': 2,
                'at_utc': datetime.now(timezone.utc).isoformat(), 'marker': str(dest / filename),
                'marker_observed': marker, 'running_and_waiting_requests': 0,
                'external_judges_continue': True}
            save(output / 'state.json', {'released': released, 'pid': os.getpid(),
                'at_utc': datetime.now(timezone.utc).isoformat()})
        save(output / 'state.json', {'released': released, 'pid': os.getpid(),
            'at_utc': datetime.now(timezone.utc).isoformat()})
        time.sleep(15)


if __name__ == '__main__':
    os.umask(0o077)
    main()
