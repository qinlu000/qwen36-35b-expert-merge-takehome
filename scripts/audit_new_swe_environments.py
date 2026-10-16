"""Join new SWE candidates to pinned upstream task environment metadata on CPU."""
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
from audit_new_swe_cpu import sha

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/data/candidates/new_swe_20261016/night_v2'
source = root / 'artifacts/data/_metadata/night_swe_20261016/rebench_tasks.parquet'
expected = '0e0bf9355f892ad74ae98d4e1c404f39fd6654a8e351ee3e6ab162e4a64cd3ad'
assert sha(source) == expected and source.stat().st_size == 428839266
columns = ['repo', 'instance_id', 'base_commit', 'image_name', 'language', 'license', 'install_config']
rows = pq.read_table(source, columns=columns).to_pylist()
index = {x['instance_id']: x for x in rows}
assert len(index) == len(rows)
results, unmatched = [], []
for split in ['train', 'val']:
    for line in (out / f'{split}.manifest.jsonl').read_text().splitlines():
        candidate = json.loads(line)
        if candidate['source'] != 'swe-rebench-v2':
            unmatched.append({'family_key': candidate['family_key'], 'split': split, 'reason': 'Scale-SWE upstream metadata not downloaded; source trace remains candidate only'})
            continue
        task = index.get(candidate['instance_id'])
        if task is None:
            unmatched.append({'family_key': candidate['family_key'], 'split': split, 'reason': 'instance missing in pinned upstream'})
            continue
        assert task['repo'].lower() == candidate['repo']
        assert task['language'] == candidate['language']
        assert len(task['base_commit']) == 40 and task['image_name']
        config = task.get('install_config') or {}
        results.append({'family_key': candidate['family_key'], 'split': split, **task,
            'upstream_dataset': 'nebius/SWE-rebench-V2', 'upstream_revision': '10483de0f50fe5da545942705a76c6150171af7f',
            'upstream_revision_limit': 'Pinned current task snapshot; NVIDIA collector did not publish its exact task revision.',
            'runtime_status': 'not_restored', 'grader_status': 'not_executed',
            'native_collector_status': 'source mini collector not published in trajectory tree',
            'training_released': False, 'val_use': 'heldout_loss_until_runtime_and_independent_grader_verified'})
(out / 'environment_manifest.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in results))
(out / 'environment_unmatched.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in unmatched))
summary = {'source': {'dataset': 'nebius/SWE-rebench-V2', 'revision': '10483de0f50fe5da545942705a76c6150171af7f',
    'file': 'data/train-00000-of-00001.parquet', 'bytes': source.stat().st_size, 'sha256': expected, 'rows': len(rows), 'columns_read': columns},
    'matched': len(results), 'matched_by_split': dict(Counter(x['split'] for x in results)),
    'unmatched': len(unmatched), 'unmatched_by_reason': dict(Counter(x['reason'] for x in unmatched)),
    'published_images': sum(bool(x['image_name']) for x in results), 'published_base_commits': sum(bool(x['base_commit']) for x in results),
    'install_config_fields': dict(Counter(k for x in results for k,v in (x['install_config'] or {}).items() if v is not None)),
    'val_examples': [{k:x[k] for k in ['repo','instance_id','base_commit','image_name','language']} for x in results if x['split'] == 'val'][:8],
    'manifest_sha256': sha(out / 'environment_manifest.jsonl'),
    'scope': 'Environment-only upstream join. No source patch, test_patch, problem_statement, hidden tests or formal outcomes read. No container or task commands executed. Matching a published image/base is not runtime, dependency or verifier validation. NVIDIA source collector task snapshot and /testbed remapping remain unknown.'}
(out / 'environment_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, indent=2))
