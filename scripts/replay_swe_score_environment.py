#!/usr/bin/env python3
"""Re-score frozen model patches in a separate native runtime attempt."""
import argparse
import asyncio
import fcntl
import json
from pathlib import Path

from harbor.trial.trial import Trial
from run_swe_baseline_v2_next import trial_config
from swe_baseline_v2 import ROOT, save_json


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--category', default='python')
    parser.add_argument('--environment', default='swe_score_runtime:SweScoreRuntimeEnvironment')
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--cpu-offset', type=int, default=124)
    parser.add_argument('--task-id', action='append')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / '.controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    audit = json.loads(args.audit.read_text())
    selected = [row for row in audit['tasks'] if row['invalid_reason'] and
                (args.category == 'all' or (('missing_pytest' in row['invalid_reason'] or 'missing_pip' in row['invalid_reason'])
                 if args.category == 'python' else 'download_timeout' in row['invalid_reason']))]
    if args.task_id:
        selected = [row for row in selected if row['task_id'] in args.task_id]
    manifest = []
    for row in selected:
        prior = ROOT / row['result']
        config = json.loads((prior.parent / 'config.json').read_text())
        manifest.append({'task_id': row['task_id'], 'prior_result': str(prior),
            'prior_invalid_reason': row['invalid_reason'], 'task': config['task']['path'],
            'source_generation': config['agent']['kwargs']['source_job'],
            'model_generation_repeated': False})
    save_json(args.output / 'preserved_manifest.json', {'scope': 51, 'tasks': manifest,
        'model_calls': 0, 'patches_unchanged': True, 'environment': args.environment})
    gate = asyncio.Semaphore(args.concurrency)
    active, finished = set(), []
    def checkpoint():
        save_json(args.output / 'checkpoint.json', {'active': sorted(active), 'finished': finished,
            'pending': [r['task_id'] for r in manifest if r['task_id'] not in active and r['task_id'] not in finished],
            'model_calls': 0, 'scope': 51})
    async def replay(row):
        async with gate:
            name = row['task_id']
            directory = args.output / 'replay' / name
            journal = args.output / 'audit' / (name + '.started.json')
            if (directory / 'result.json').exists():
                finished.append(name)
                checkpoint()
                return
            if directory.exists() or journal.exists():
                raise RuntimeError('Interrupted replay retained for manual audit: ' + name)
            active.add(name)
            checkpoint()
            save_json(journal, row)
            config = trial_config(Path(row['task']), args.output, 'replay', args.concurrency,
                                  cpu_offset=args.cpu_offset)
            config.agent.kwargs['source_job'] = row['source_generation']
            config.environment.import_path = args.environment
            trial = await Trial.create(config)
            await trial.run()
            active.remove(name)
            finished.append(name)
            checkpoint()
    checkpoint()
    await asyncio.gather(*(replay(row) for row in manifest))
    save_json(args.output / 'finished.json', {'task_ids': finished, 'model_calls': 0})


if __name__ == '__main__':
    asyncio.run(main())
