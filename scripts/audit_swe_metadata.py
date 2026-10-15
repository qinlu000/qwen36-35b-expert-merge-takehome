"""Audit Open-SWE metadata only; this does not create an approved training split."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / 'data_sources.json').read_text())['open_swe']
exclusions = json.loads((ROOT / 'configs/data_exclusions.json').read_text())
blocked = {repo.lower() for repo in exclusions['swe_pro_repositories']}
files = []
for item in source['files']:
    path = ROOT / 'artifacts/data/raw/open_swe' / source['revision'] / item['path']
    if path.suffix == '.parquet' and path.exists() and path.stat().st_size == item['size']:
        files.append(path)
repos, licenses, resolved = Counter(), Counter(), Counter()
seen, duplicates, rows, exact_excluded = set(), 0, 0, 0
for path in files:
    table = pq.read_table(path, columns=['repo', 'license', 'instance_id', 'resolved'])
    for row in table.to_pylist():
        repo = (row['repo'] or '').strip().lower()
        repos[repo] += 1
        licenses[row['license'] or '<missing>'] += 1
        resolved[str(row['resolved'])] += 1
        key = (repo, row['instance_id'])
        duplicates += key in seen
        seen.add(key)
        exact_excluded += repo in blocked
        rows += 1
report = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'source_revision': source['revision'],
    'complete_shards': len(files),
    'expected_shards': sum(item['path'].endswith('.parquet') for item in source['files']),
    'rows': rows,
    'unique_repository_instance_pairs': len(seen),
    'repeated_repository_instance_pairs': duplicates,
    'exact_swe_pro_repository_rows': exact_excluded,
    'matching_swe_pro_repositories': {repo: count for repo, count in repos.items() if repo in blocked},
    'missing_repository_rows': repos[''],
    'license_counts': dict(licenses),
    'resolved_counts': dict(resolved),
    'files': [str(path.relative_to(ROOT)) for path in files],
    'scope': 'Metadata audit only. No messages, patches, tests or code read or executed. Exact repository exclusion is not a full contamination audit; forks, renamed repos, PR lineage and cross-source duplicates remain pending.',
}
out = ROOT / 'artifacts/data/audits/swe_metadata.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'files'}))
