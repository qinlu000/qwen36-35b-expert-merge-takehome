#!/usr/bin/env python3
"""Prepare by default; stop only future admissions at the fixed01:10CST cutoff."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

CUTOFF = datetime.fromisoformat('2026-10-18T01:10:00+08:00')
PINS = {
  "terminal250_full445_20261017": {
    "model": "apex-terminal250",
    "checkpoint": "artifacts/runs/terminal-retry-sft-r16-726665/training/checkpoint-250",
    "service_job": "727912",
    "service_ends": "2026-10-18T02:01:28+08:00",
    "config_sha256": "24fb4d5200001279ddde81898690f8c1b5b4add99f75b8e6db7da3a140dc22a1",
    "manifest_sha256": "78dd5cda85a782f72f3b995b463bd65eb49b3c0653c98cd81a73250d68176fd3"
  },
  "avg64_terminal_full445_20261017": {
    "model": "apex-avg64",
    "checkpoint": "artifacts/merges/four-experts-avg-v1-20261017/avg-r64",
    "service_job": "727913",
    "service_ends": "2026-10-18T02:09:28+08:00",
    "config_sha256": "9642b90d128f3c9febae58115b4c20d967618f0785d8c859993a59653dd915cb",
    "manifest_sha256": "bb214b58f8aac849d129c04f6233610b2165aa978181f056c7966676db1acb49"
  }
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root):
    rows = []
    for name, expected in PINS.items():
        output = root / 'artifacts/eval' / name
        config = json.loads((output / 'config.json').read_text())
        assert digest(output / 'config.json') == expected['config_sha256'], name
        assert digest(output / 'manifest.json') == expected['manifest_sha256'], name
        assert all(config[k] == expected[k] for k in ['model', 'checkpoint', 'service_job', 'service_ends'])
        rows.append({'output': str(output), **expected,
                     'existing_stop_gate': (output / 'STOP_ADMISSION').exists()})
    return rows


def decision(at, states):
    if all(len(s['terminal']) == 445 and not s['active'] and not s['pending'] for s in states):
        return 'finished_no_consumers'
    return 'stop_future_admissions' if at >= CUTOFF else 'waiting_cutoff'


def execute(root, rows):
    owned = root / 'artifacts/eval/terminal-core-admission-guard-20261017'
    owned.mkdir(exist_ok=False)
    start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
    claim = {'pid': os.getpid(), 'starttime_ticks': start, 'cutoff': CUTOFF.isoformat(),
             'created_at_utc': datetime.now(timezone.utc).isoformat(), 'selection': rows,
             'script_sha256': digest(Path(__file__)), 'policy': 'No kill; admitted native budgets unchanged'}
    (owned / 'claim.json').write_text(json.dumps(claim, indent=2) + '\n')
    previous = None
    while True:
        at = datetime.now(timezone.utc)
        states = [json.loads((Path(row['output']) / 'checkpoint.json').read_text()) for row in rows]
        state = decision(at, states)
        value = {'at_utc': at.isoformat(), 'state': state, 'pid': os.getpid(),
                 'terminal_counts': [len(s['terminal']) for s in states],
                 'active_counts': [len(s['active']) for s in states],
                 'pending_counts': [len(s['pending']) for s in states]}
        if state == 'stop_future_admissions':
            prepare(root)  # Recheck the exact frozen queues before writing their existing gate.
            gates = []
            for row in rows:
                path = Path(row['output']) / 'STOP_ADMISSION'
                try:
                    with path.open('x') as stream:
                        json.dump({'reason': 'fixed_core_runway_cutoff', 'at_utc': at.isoformat(),
                                   'cutoff': CUTOFF.isoformat(), 'guard_claim': str(owned / 'claim.json'),
                                   'inflight_budgets_unchanged': True}, stream, indent=2)
                    action = 'created'
                except FileExistsError:
                    action = 'preserved_existing'
                gates.append({'path': str(path), 'action': action, 'sha256': digest(path)})
            value['gates'] = gates
        temporary = owned / 'state.tmp'
        temporary.write_text(json.dumps(value, indent=2) + '\n')
        temporary.replace(owned / 'state.json')
        if state != previous:
            with (owned / 'log.jsonl').open('a') as stream:
                stream.write(json.dumps(value) + '\n')
            previous = state
        if state != 'waiting_cutoff':
            return
        time.sleep(min(30, max(.1, (CUTOFF - at).total_seconds())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve()
    rows = prepare(root)
    if args.execute:
        os.umask(0o077)
        execute(root, rows)
    else:
        print(json.dumps({'mode': 'prepare_only', 'cutoff': CUTOFF.isoformat(),
                          'selection': rows, 'gates_written': 0, 'new_native_runs': 0}, indent=2))
