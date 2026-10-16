#!/usr/bin/env python3
"""After the current cohort finishes, recover only proven pre-model setup errors."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from swe_baseline_v2 import ROOT, save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--prior-pid', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--key-path', type=Path, required=True)
    parser.add_argument('--acceptance-receipt', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    command = Path(f'/proc/{args.prior_pid}/cmdline')
    while command.exists() and str(args.prior).encode() in command.read_bytes():
        time.sleep(30)
    checkpoint = json.loads((args.prior / 'admission_checkpoint.json').read_text())
    if checkpoint['state'] != 'finished_available_images':
        save_json(args.output / 'recovery_wait.json', {'state': 'needs_audit', 'prior': str(args.prior),
            'reason': 'Prior controller did not finish normally; no automatic model request'})
        return
    ids = json.loads((ROOT / 'analysis/source_snapshots/protocol/swe_hard_task_ids.json').read_text())['task_ids']
    recover = []
    for name in ids:
        result = args.prior / 'generation' / name / 'result.json'
        if not result.is_file():
            continue
        data = json.loads(result.read_text())
        error = (data.get('exception_info') or {}).get('exception_message', '')
        if 'Container mini runtime differs from fixed constraints:' not in error:
            continue
        if any((args.prior / 'requests' / name).glob('*.json')):
            continue
        if (args.prior / 'generation' / name / 'agent/mini-swe-agent.trajectory.json').exists():
            continue
        recover.append(name)
    manifest = args.output / 'admit_setup_recovery.json'
    save_json(manifest, recover)
    save_json(args.output / 'setup_repair_manifest.json', {'prior': str(args.prior),
        'reason': 'The repository egg-info was incorrectly included in the mini venv fingerprint',
        'selected_task_ids': recover, 'previous_model_requests': 0, 'previous_complete_responses': 0,
        'generation_attempt': 1, 'all_previous_artifacts_retained': True})
    if not recover:
        return
    snapshot = args.output / 'source_snapshot'
    snapshot.mkdir(exist_ok=True)
    for name in ['run_swe_baseline_v2_setup_recovery.py', 'swe_baseline_sitepackages_v2.py',
                 'swe_baseline_v2.py', 'swe_runtime_environment.py', 'swe_runtime_bootstrap.sh',
                 'swe_runtime_rootmap.sh']:
        shutil.copyfile(ROOT / 'scripts' / name, snapshot / name)
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts'))
    env['PATH'] = (str(ROOT / 'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin') + ':' +
        str(ROOT / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin') + ':' + env['PATH'])
    command = [str(ROOT / 'artifacts/envs/harbor/bin/python'), '-u',
        str(ROOT / 'scripts/run_swe_baseline_v2_setup_recovery.py'), '--output', str(args.output),
        '--endpoint', args.endpoint, '--key-path', str(args.key_path),
        '--admit-task-ids', str(manifest), '--acceptance-receipt', str(args.acceptance_receipt),
        '--concurrency', '8', '--cpu-offset', '64']
    with (args.output / 'controller.log').open('ab') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, env=env, start_new_session=True)
    (args.output / 'controller.pid').write_text(str(process.pid) + '\n')
    save_json(args.output / 'recovery_wait.json', {'state': 'launched', 'pid': process.pid,
        'selected': len(recover), 'scope': 51, 'prior': str(args.prior)})


if __name__ == '__main__':
    main()
