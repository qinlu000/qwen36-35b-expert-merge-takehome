"""One synthetic native command check in a cached official task environment."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import shutil

import httpx

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from release_validation_cpus import base_scopes


async def main(args):
    output = args.output.resolve()
    config = json.loads((output / 'config.json').read_text())
    manifest = json.loads((output / 'manifest.json').read_text())
    root = Path('/data/caoqinlu/projects/apex-takehome')
    target = output / 'acceptance'
    cpu_offset = config.get('acceptance_cpu_offset', 120)
    cpu_ids = list(range(cpu_offset, cpu_offset + 4))
    headers = {'Authorization': 'Bearer ' + (root / config['key_file']).read_text().strip()}
    async with httpx.AsyncClient(base_url=config['endpoint'], headers=headers, trust_env=False, timeout=10) as client:
        for _ in range(120):
            try:
                (await client.get('/health')).raise_for_status()
                break
            except httpx.HTTPError:
                await asyncio.sleep(10)
        else:
            raise TimeoutError('Terminal service did not become healthy within20minutes')
        response = await client.get('/v1/models')
        response.raise_for_status()
        models = response.json()
        assert {row['id'] for row in models['data']} == {config.get('base_alias', 'apex-terminal-base'), config['model']}
    target.mkdir(exist_ok=False)
    assert not base_scopes(set(cpu_ids)), 'Acceptance CPUs temporarily occupied'
    original = next(row for row in manifest['entries'] if row['task_id'] == 'bn-fit-modify' and row['seed'] == 0)
    source = Path(original['trial_config']['task']['path'])
    fixture = target / 'tasks/apex-terminal-command-acceptance'
    fixture.mkdir(parents=True)
    shutil.copytree(source / 'environment', fixture / 'environment')
    (fixture / 'task.toml').write_text((source / 'task.toml').read_text())
    (fixture / 'instruction.md').write_text(
        'Synthetic command plumbing check. Execute printf "APEX_TERMINAL250_READY\\n" '
        '> /app/apex-terminal250-ready.txt, read that file back, and mark the task complete. '
        'Use the required native terminal JSON format.\n')
    (fixture / 'tests').mkdir()
    resource_code = ('import json,os,pathlib; '
        'pathlib.Path("/logs/verifier/resource-affinity.json").write_text('
        'json.dumps({"cpus":sorted(os.sched_getaffinity(0))}))')
    (fixture / 'tests/test.sh').write_text(
        '#!/bin/bash\nmkdir -p /logs/verifier\n'
        + '/opt/harbor-server/bin/python3 -c ' + shlex.quote(resource_code) + '\n'
        'if test "$(cat /app/apex-terminal250-ready.txt 2>/dev/null)" = APEX_TERMINAL250_READY; then\n'
        ' echo 1 > /logs/verifier/reward.txt\nelse\n echo 0 > /logs/verifier/reward.txt\nfi\n')
    trial_config = TrialConfig.model_validate(original['trial_config'])
    trial_config.task.path = fixture
    trial_config.task.source = 'synthetic acceptance fixture using the official cached bn-fit-modify environment'
    trial_config.trials_dir = target / 'trials'
    trial_config.trial_name = 'native-command'
    trial_config.environment.kwargs['baseline_cpu_offset'] = cpu_offset
    trial = await Trial.create(trial_config)
    await trial.run()
    directory = trial_config.trials_dir / trial_config.trial_name
    result = json.loads((directory / 'result.json').read_text())
    records = [json.loads(path.read_text()) for path in sorted((directory / 'agent/v2_requests').glob('*.json'))]
    assert records and all(row['request']['model'] == config['model'] for row in records)
    assert not result.get('exception_info'), result.get('exception_info')
    assert result['verifier_result']['rewards']['reward'] == 1
    affinity = json.loads((directory / 'verifier/resource-affinity.json').read_text())
    assert affinity['cpus'] == cpu_ids, affinity
    state = json.loads((directory / 'artifacts/logs/artifacts/final-task-state.json').read_text())
    assert state['captured_before_verifier'] is True and state['return_code'] == 0
    receipt = {'at': datetime.now(timezone.utc).isoformat(), 'ready': True,
        'scope': 'One synthetic echo/read native Terminus2 command fixture; no benchmark questions or scores',
        'cached_official_environment': str(source), 'original_official_task_unchanged': True,
        'model': config['model'], 'model_requests': len(records), 'base_generations': 0,
        'fixture_reward': 1, 'actual_cpu_affinity': affinity['cpus'], 'memory_limit_bytes': 8192 * 1024**2,
        'memory_enforcement': 'Unchanged Base launcher verifies systemd MemoryMax before launching the namespace',
        'final_state_saved_before_verifier': True, 'models': models,
        'context_tokens': 65536, 'output_tokens': 8192,
        'sampling': {'temperature': 1, 'top_p': 0.95, 'top_k': 20, 'thinking': False}}
    (target / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
