#!/usr/bin/env python3
"""Collect fixed HARD51 first-valid fresh-replay scores without inventing zeros."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re
import time

from swe_baseline_v2 import ROOT, save_json

BASE = ROOT / 'artifacts/eval'
OUTPUT = BASE / 'base_swe_v2_20261016_final'


def score(path):
    result = json.loads(path.read_text())
    verifier = path.parent / 'verifier'
    text = '\n'.join(p.read_text(errors='replace') for p in
        [verifier / 'run-script-stdout.txt', verifier / 'run-script-stderr.txt'] if p.exists())
    parsed = verifier / 'output.json'
    tests = json.loads(parsed.read_text()).get('tests', []) if parsed.exists() else []
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    invalid = None
    if 'No module named pytest' in text:
        invalid = 'verifier_missing_pytest'
    elif 'pip is unavailable' in text or "No module named 'pip'" in text:
        invalid = 'verifier_missing_pip'
    elif 'proxy.golang.org' in text and 'i/o timeout' in text:
        invalid = 'verifier_public_go_dependency_timeout'
    elif result.get('exception_info'):
        invalid = 'harbor_replay_exception:' + result['exception_info']['exception_type']
    elif reward not in (0, 1):
        invalid = 'reward_missing'
    elif not tests and not re.search(
            r'imported .*not used|unknown directive|syntax error|assignment mismatch|undefined:|build failed|cannot import name', text):
        invalid = 'empty_tests_requires_audit'
    return {'task_id': path.parent.name, 'result': str(path), 'reward': reward,
        'invalid_reason': invalid, 'finished_at': result.get('finished_at', ''),
        'test_count': len(tests)}


def collect():
    ids = json.loads((ROOT / 'analysis/source_snapshots/protocol/swe_hard_task_ids.json').read_text())['task_ids']
    roots = [BASE / 'base_swe_v2_20261016_full/glibc',
        BASE / 'base_swe_v2_20261016_full/musl_root_repair',
        BASE / 'base_swe_v2_20261016_budget_replay',
        BASE / 'base_swe_v2_20261016_manual_infra1']
    roots += list((BASE / 'base_swe_v2_20261016_full_x2').glob('group*'))
    roots += list(BASE.glob('base_swe_v2_20261016_score_*'))
    candidates = [score(p) for root in roots for p in root.glob('replay/*/result.json')]
    candidates.sort(key=lambda row: row['finished_at'])
    rows = []
    retry_manifest = BASE / 'base_swe_v2_20261016_manual_infra1/manual_retry_manifest.json'
    retries = {r['task_id']: r for r in json.loads(retry_manifest.read_text())['tasks']} if retry_manifest.exists() else {}
    for name in ids:
        history = [r for r in candidates if r['task_id'] == name]
        valid = next((r for r in history if not r['invalid_reason']), None)
        rows.append({'task_id': name, 'status': 'valid_scored' if valid else
            'invalid_requires_replay' if history else 'awaiting_generation_or_replay',
            'reward': valid['reward'] if valid else None,
            'accepted_result': valid['result'] if valid else None,
            'invalid_attempts': [r for r in history if r['invalid_reason']],
            'manual_infrastructure_retries': int((BASE / 'base_swe_v2_20261016_manual_infra1/audit' /
                (name + '.generation.started.json')).exists()),
            'manual_infrastructure_retry_planned': name in retries,
            'original_incomplete_trial': retries.get(name),
            'all_score_attempts': history})
    valid = [r for r in rows if r['status'] == 'valid_scored']
    resolved = sum(r['reward'] == 1 for r in valid)
    complete = len(valid) == 51
    summary = {'as_of': datetime.now(timezone.utc).isoformat(), 'expected': 51,
        'valid_scored': len(valid), 'resolved': resolved, 'unscored': 51 - len(valid),
        'invalid_pending': sum(r['status'] == 'invalid_requires_replay' for r in rows),
        'awaiting_generation_or_replay': sum(r['status'] == 'awaiting_generation_or_replay' for r in rows),
        'primary_score_percent': 100 * resolved / 51 if complete else None,
        'conservative_resolved_percent': 100 * resolved / 51, 'complete': complete,
        'selection_policy': 'Earliest environment-valid fresh replay, regardless of reward; old invalid scores retained; no zero for unscored',
        'manual_retry_task_count': sum(r['manual_infrastructure_retries'] for r in rows),
        'manual_retry_planned_task_count': len(retries), 'tasks': rows}
    save_json(OUTPUT / 'final_summary.json', summary)
    with (OUTPUT / 'task_scores.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['task_id', 'status', 'reward',
            'accepted_result', 'manual_infrastructure_retries', 'invalid_score_attempts'])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in writer.fieldnames if k != 'invalid_score_attempts'} |
                            {'invalid_score_attempts': len(r['invalid_attempts'])})
    return {k: v for k, v in summary.items() if k != 'tasks'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--watch', action='store_true')
    args = p.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    lock = (OUTPUT / '.collector.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    previous = None
    while True:
        summary = collect()
        change = tuple(summary[k] for k in ['valid_scored', 'resolved', 'invalid_pending', 'awaiting_generation_or_replay'])
        if change != previous:
            print(json.dumps(summary), flush=True)
            previous = change
        if summary['complete'] or not args.watch:
            return
        time.sleep(15)


if __name__ == '__main__':
    main()
