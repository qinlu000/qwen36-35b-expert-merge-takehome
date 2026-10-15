"""Read only fixed benchmark environment metadata, never instructions or tests."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = args.root / 'artifacts/preflight/swe_tb/task_image_manifest.json'
    groups = {}
    for task in json.loads(manifest.read_text()):
        group = groups.setdefault(task['benchmark'], {
            'tasks': 0, 'dockerfiles': 0, 'from_declarations': Counter(),
            'workdir_declarations': Counter(), 'user_declarations': Counter(),
            'explicit_network_settings': Counter(), 'task_file_resources_before_overrides': Counter(),
        })
        group['tasks'] += 1
        path = args.root / task['task_path'] / 'environment/Dockerfile'
        if path.exists():
            group['dockerfiles'] += 1
            lines = [line.strip() for line in path.read_text().splitlines()]
            for directive, name in [('FROM', 'from_declarations'),
                                    ('WORKDIR', 'workdir_declarations'),
                                    ('USER', 'user_declarations')]:
                values = [line.split(None, 1)[1] for line in lines
                          if line.upper().startswith(directive + ' ')]
                group[name].update(values or ['<not set here; inspect base image>'])
        env = task['environment']
        group['task_file_resources_before_overrides'][json.dumps({key: env.get(key) for key in
            ('cpus', 'memory_mb', 'memory', 'gpus')}, sort_keys=True)] += 1
        network = {key: value for key, value in {**env, **task['agent']}.items()
                   if 'network' in key or 'internet' in key}
        group['explicit_network_settings'][json.dumps(network, sort_keys=True)] += 1
    protocol = json.loads((args.root / 'configs/eval/protocol_v1.json').read_text())
    report = {
        'scope': 'Only the existing task image manifest and environment/Dockerfile directives; no task text, solution, tests, image pulls, containers or model requests.',
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'groups': groups,
        'declared_eval_resources_not_runtime_verified': {
            name: {key: protocol['benchmarks'][name][key] for key in
                   ('cpus', 'memory_mib', 'agent_timeout_seconds')}
            for name in ('swe', 'terminal')},
        'interpretation': 'Dockerfile FROM/USER/WORKDIR are build metadata, not proof of the final image OS, inherited user, mounts or runtime network/resource enforcement.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'tasks': {name: group['tasks'] for name, group in groups.items()},
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
