#!/usr/bin/env python3
"""Stop new admission, drain existing trials, then use seq8 for untouched IDs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from swe_baseline_v2 import ROOT, save_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--endpoint', default='http://127.0.0.1:28084')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.prior / 'STOP_ADMISSION').touch()
    additional_path = args.prior / 'additional_children.json'
    additional = json.loads(additional_path.read_text()) if additional_path.exists() else []
    for child in additional:
        (Path(child['output']) / 'STOP_ADMISSION').touch()
    def additional_running():
        return any(Path(f"/proc/{c['pid']}/cmdline").exists() and
                   c['output'].encode() in Path(f"/proc/{c['pid']}/cmdline").read_bytes() for c in additional)
    while not (args.prior / 'cohort-finished.json').exists() or additional_running():
        time.sleep(5)
    ids = json.loads((ROOT / 'analysis/source_snapshots/protocol/swe_hard_task_ids.json').read_text())['task_ids']
    pending = set(json.loads((args.prior / 'checkpoint.json').read_text()).get('pending', []))
    for child in additional:
        data = json.loads((Path(child['output']) / 'admission_checkpoint.json').read_text())
        pending.update(data.get('pending', []))
    selected = [n for n in ids if n in pending]
    # Only tasks without a started journal may move to the new endpoint.
    # An additional child explicitly repairs a proven zero-model setup error;
    # its own queue/journals supersede the earlier setup-only journal.
    repair_ids = {n for c in additional for n in c['task_ids']}
    for child in json.loads((args.prior / 'controller.json').read_text())['children']:
        audit = Path(child['output']) / 'audit'
        selected = [n for n in selected if n in repair_ids or not (audit / (n + '.generation.started.json')).exists()]
    for child in additional:
        audit = Path(child['output']) / 'audit'
        selected = [n for n in selected if not (audit / (n + '.generation.started.json')).exists()]
    manifest = args.output / 'handoff-pending-ids.json'
    save_json(manifest, selected)
    save_json(ROOT / 'artifacts/runs/swe-base-725561/model-consumer-finished.json', {
        'model_consumer_finished': True, 'active': 0, 'moved_pending': selected,
        'prior': str(args.prior), 'old_answers_preserved': True})
    if not selected:
        save_json(args.output / 'cohort-finished.json', {'state': 'nothing_pending', 'scope': 51})
        return
    command = [str(ROOT / 'artifacts/envs/harbor/bin/python'), '-u',
        str(ROOT / 'scripts/run_swe_full_cohort_root.py'), '--output', str(args.output),
        '--admit-task-ids', str(manifest), '--endpoint', args.endpoint, '--engine-max-seqs', '8']
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts'))
    raise SystemExit(subprocess.call(command, env=env))


if __name__ == '__main__':
    main()
