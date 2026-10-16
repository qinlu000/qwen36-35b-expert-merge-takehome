"""Freeze all 89 x 5 Terminal trials with the repaired Base runtime."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from harbor.job_plan import JobPlan
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import TaskConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    config = json.loads(args.config.read_text())
    output = root / config['output']
    runtime = output / 'runtime'
    runtime.mkdir(parents=True, exist_ok=False)
    (runtime / 'artifacts').symlink_to(root / 'artifacts', target_is_directory=True)
    origins = {}
    for relative in reversed(config['base_runtime_script_layers']):
        source = root / relative
        shutil.copytree(source, runtime / 'scripts', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in source.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                origins[str(path.relative_to(source))] = str(path)
    for name in ('run_terminal_expert_benchmark.py', 'accept_terminal_expert.py',
                 'release_validation_cpus.py'):
        source = root / 'scripts' / name
        shutil.copy2(source, runtime / 'scripts' / name)
        origins[name] = str(source)
    manifest_path = root / config['base_full_manifest']
    source = json.loads(manifest_path.read_text())
    ids = source['task_ids']
    assert len(ids) == len(set(ids)) == 89
    seed_configs = {int(seed): JobConfig.model_validate_json(Path(item['path']).read_text())
                    for seed, item in source['seed_job_configs'].items()}
    entries = []
    for row in source['entries']:
        trial = JobPlan.build_trial_configs(seed_configs[row['seed']],
            [TaskConfig.model_validate(row['task_config'])], job_id=None)[0]
        trial.trials_dir = output / 'trials'
        trial.trial_name = row['task_id'] + '__seed' + str(row['seed'])
        trial.job_id = None
        trial.environment.import_path = 'terminal_repair_environment_v2:TerminalRepairEnvironment'
        trial.environment.override_cpus = 4
        trial.environment.override_memory_mb = 8192
        trial.environment.kwargs.update(baseline_cpu_offset=0, baseline_cpu_slots=1)
        trial.agent.import_path = 'terminal_repair_agent_v2:TerminalRepairAgent'
        trial.agent.model_name = config['model']
        trial.agent.kwargs.update(api_base=config['endpoint'], api_key_path=str(root / config['key_file']))
        trial.agent.override_timeout_sec = 1800
        trial.verifier.override_timeout_sec = 900
        assert trial.agent.kwargs['seed'] == row['seed']
        entries.append({key: row[key] for key in ('key', 'task_id', 'seed', 'task_checksum')}
                       | {'trial_config': trial.model_dump(mode='json')})
    assert len(entries) == 445
    assert {row['key'] for row in entries} == {f'{task}/seed{seed}' for seed in range(5) for task in ids}
    frozen = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'task_ids': ids,
        'entries': entries, 'expected': 445, 'selection': 'Every fixed task and seed, independent of all rewards',
        'base_full_manifest': str(manifest_path),
        'base_full_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    (output / 'manifest.json').write_text(json.dumps(frozen, indent=2) + '\n')
    (output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    inventory = [{'relative_path': relative, 'source': source,
        'sha256': hashlib.sha256((runtime / 'scripts' / relative).read_bytes()).hexdigest()}
        for relative, source in sorted(origins.items())]
    (runtime / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps({'prepared': True, 'expected': 445, 'tasks': 89, 'seeds': list(range(5)),
                      'output': str(output), 'runtime_source_files': len(inventory), 'model_requests': 0}))


if __name__ == '__main__':
    main()
