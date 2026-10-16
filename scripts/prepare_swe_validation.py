"""Materialize the existing 100 repository-disjoint dev tasks, keeping gold private."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def main(args):
    root, output = args.project.resolve(), args.output.resolve()
    data = root / 'artifacts/data/candidates/new_swe_20261016'
    val = [json.loads(line) for line in (data / 'night_v2/val.manifest.jsonl').read_text().splitlines()]
    train = [json.loads(line) for line in (data / 'expanded_2k/swift_ready64k/train.manifest.jsonl').read_text().splitlines()]
    assert len(val) == len({row['instance_id'] for row in val}) == 100
    assert not {r['repo'].lower() for r in val} & {r['repo'].lower() for r in train}
    assert not {r['instance_id'] for r in val} & {r['instance_id'] for r in train}
    columns = ['repo', 'instance_id', 'base_commit', 'image_name', 'language',
               'problem_statement', 'interface', 'install_config', 'test_patch',
               'patch', 'FAIL_TO_PASS', 'PASS_TO_PASS']
    table = pq.read_table(root / 'artifacts/data/_metadata/night_swe_20261016/rebench_tasks.parquet',
                          columns=columns)
    wanted = {row['instance_id'] for row in val}
    selected = table.filter(pc.is_in(table['instance_id'], value_set=pa.array(sorted(wanted))))
    specs = {row['instance_id']: row for row in selected.to_pylist()}
    assert len(specs) == 100
    (output / 'gold_patches').mkdir(parents=True, exist_ok=True)
    records = []
    for manifest in val:
        row = specs[manifest['instance_id']]
        name = 'instance_' + row['instance_id']
        task = output / 'tasks' / name
        tests = task / 'tests'
        env = task / 'environment'
        tests.mkdir(parents=True, exist_ok=True)
        (env / 'files').mkdir(parents=True, exist_ok=True)
        workdir = '/' + row['repo'].split('/')[1]
        sif = output / 'images' / (row['instance_id'] + '.sif')
        instruction = row['problem_statement']
        if row['interface']:
            interface = row['interface'] if isinstance(row['interface'], str) else json.dumps(row['interface'])
            instruction += '\n\n' + interface
        (task / 'instruction.md').write_text(instruction + '\n')
        (env / 'Dockerfile').write_text('FROM ' + row['image_name'] + '\nWORKDIR ' + workdir + '\n')
        (env / 'files/setup.sh').write_text(
            'test "$(git -C ' + workdir + ' rev-parse HEAD)" = ' + row['base_commit'] + '\n'
            'if [ ! -e /testbed ]; then ln -s ' + workdir + ' /testbed; fi\n')
        (task / 'task.toml').write_text(f'''schema_version = "1.4"
artifacts = []
[task]
name = "swe-rebench-dev/{name}"
version = "1.0.0"
description = "Existing independent source-dev task"
authors = []
keywords = []
[metadata]
author_name = "SWE-rebench"
author_email = "unknown"
difficulty = "medium"
category = "debugging"
tags = ["independent-dev", "swe-rebench-v2"]
[verifier]
network_mode = "public"
timeout_sec = 3000.0
collect = []
[agent]
network_mode = "no-network"
timeout_sec = 1800.0
[environment]
network_mode = "public"
build_timeout_sec = 1800.0
docker_image = {json.dumps(str(sif))}
os = "linux"
cpus = 1
memory_mb = 4096
storage_mb = 10240
mcp_servers = []
''')
        (tests / 'spec.json').write_text(json.dumps({
            k: row[k] for k in ['instance_id', 'install_config', 'FAIL_TO_PASS', 'PASS_TO_PASS']
        } | {'workdir': workdir}, indent=2) + '\n')
        (tests / 'test_patch.diff').write_text(row['test_patch'])
        (tests / 'test.sh').write_text('#!/bin/bash\nset -e\n/opt/harbor-server/bin/python3 /tests/grade.py\n')
        shutil.copyfile(root / 'scripts/grade_swe_rebench_validation.py', tests / 'grade.py')
        shutil.copytree(args.source, tests / 'source', dirs_exist_ok=True)
        (output / 'gold_patches' / (name + '.patch')).write_text(row['patch'])
        records.append({k: row[k] for k in ['instance_id', 'repo', 'base_commit', 'image_name', 'language']} |
                       {'task_name': name, 'sif': str(sif), 'workdir': workdir})
    # Existing click image is first so conversion of the other 99 does not block execution.
    records.sort(key=lambda row: (row['instance_id'] != 'pallets__click-1852', row['instance_id']))
    (output / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    summary = {'tasks': len(records), 'languages': dict(Counter(row['language'] for row in records)),
               'train_tasks': len(train), 'repo_overlap': 0, 'instance_overlap': 0,
               'source_revision': '10483de0f50fe5da545942705a76c6150171af7f',
               'grader_revision': 'c71902a8cf8d2b725f63d51f199f4d3e56f68d2d',
               'scope': 'Held-out source validation, not official SWE Pro51; no teacher messages/gold patch in solver input'}
    (output / 'preparation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    main(parser.parse_args())
