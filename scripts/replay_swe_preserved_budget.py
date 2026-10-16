#!/usr/bin/env python3
"""Fresh official replay of preserved normal-budget patches; never call a model."""
import asyncio
import json
from pathlib import Path

from harbor.trial.trial import Trial
from run_swe_baseline_v2_next import trial_config
from swe_baseline_v2 import ROOT, save_json


async def main():
    source = ROOT / 'artifacts/eval/base_swe_v2_20261016_glibc_setup1'
    output = ROOT / 'artifacts/eval/base_swe_v2_20261016_budget_replay'
    output.mkdir(parents=True, exist_ok=True)
    selected = []
    for path in (source / 'generation').glob('*/result.json'):
        data = json.loads(path.read_text())
        error = (data.get('exception_info') or {}).get('exception_message', '')
        if 'exit 124' in error and 'timeout' in error:
            selected.append(path.parent.name)
    save_json(output / 'preserved_manifest.json', {'source': str(source), 'task_ids': selected,
        'reason': 'Normal1740s solver budget, preserve existing patch/trajectory',
        'model_calls': 0, 'generation_repeated': False, 'scope': 51})
    async def replay(name):
        journal = output / 'audit' / (name + '.started.json')
        if journal.exists():
            return
        save_json(journal, {'task_id': name, 'phase': 'fresh_replay_only', 'source': str(source)})
        cfg = trial_config(source / 'tasks' / name, output, 'replay', 2, cpu_offset=84)
        cfg.agent.kwargs['source_job'] = str(source / 'generation')
        trial = await Trial.create(cfg)
        await trial.run()
    await asyncio.gather(*(replay(name) for name in selected))
    save_json(output / 'finished.json', {'task_ids': selected, 'model_calls': 0})


if __name__ == '__main__':
    asyncio.run(main())
