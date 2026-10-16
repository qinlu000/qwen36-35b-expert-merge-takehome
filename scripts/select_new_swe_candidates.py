"""Create grouped candidate manifests from pinned FlashNext metadata; no SFT export."""
import argparse
import json
import os
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

for name in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[name] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from audit_new_swe_cpu import REV, family, normalize, chain_issues, sha, observation_features
from candidate_selection import SPLIT_SEED as SEED, family_rank, family_partition


def stable_rank(key):
    return family_rank(key)


def holdout(key):
    return family_partition(key)


def native_fixture(root):
    code = '''import json
from types import SimpleNamespace as N
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions, format_toolcall_observation_messages
calls=[N(id="synthetic-a",function=N(name="bash",arguments=json.dumps({"command":"SYNTHETIC_A"}))),N(id="synthetic-b",function=N(name="bash",arguments=json.dumps({"command":"SYNTHETIC_B"})))]
actions=parse_toolcall_actions(calls,format_error_template="{{error}}")
assert [a["tool_call_id"] for a in actions]==["synthetic-a","synthetic-b"]
observations=format_toolcall_observation_messages(actions=actions,outputs=[{"output":"OBS_A","returncode":0},{"output":"OBS_B","returncode":0}],observation_template="{{output.output}}")
assert [(o["tool_call_id"],o["content"]) for o in observations]==[("synthetic-a","OBS_A"),("synthetic-b","OBS_B")]
print(json.dumps({"passed":True,"calls":2,"parsed_in_input_order":True,"observation_ids_in_input_order":True,"shell_execution":False}))
'''
    env = os.environ.copy()
    env['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
    completed = subprocess.run([str(root / 'artifacts/envs/mini-swe/bin/python'), '-c', code],
                               capture_output=True, text=True, check=True, env=env)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--allow-partial', action='store_true')
    args = ap.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    root = args.root
    rawroot = root / 'artifacts/data/raw/open_swe' / REV
    outdir = root / 'artifacts/data/candidates/new_swe_20261016'
    outdir.mkdir(parents=True, exist_ok=True)
    receipts = json.loads((root / 'artifacts/data/audits/new_swe_20261016/download_receipts_all16.json').read_text())
    files = sorted(receipts, key=lambda r: r['file'])
    if not args.allow_partial:
        assert len(files) == 16, 'All 16 verified FlashNext shards are required'
    blocked = {r.lower() for r in json.loads((root / 'configs/data_exclusions.json').read_text())['swe_pro_repositories']}
    start = time.monotonic()
    oldfamilies, old_rows, old_files = set(), 0, 0
    for path in sorted((rawroot / 'data/minisweagent/qwen36_27b').rglob('*.parquet')):
        old_files += 1
        for batch in pq.ParquetFile(path).iter_batches(batch_size=512, columns=['repo', 'instance_id'], use_threads=False):
            for r in batch.to_pylist():
                oldfamilies.add(family(r['repo'], r['instance_id'])); old_rows += 1
    meta_counts = defaultdict(Counter)
    all_families, metadata_rows, candidates, quarantined = set(), [], [], []
    stats = Counter()
    for receipt in files:
        path = root / receipt['local_path']
        assert path.exists() and path.stat().st_size == receipt['bytes']
        assert receipt['sha256'] == receipt['upstream_sha256']
        pf = pq.ParquetFile(path)
        source = 'scale-swe' if '/scale-swe/' in receipt['file'] else 'swe-rebench-v2'
        byrow = {}
        offset = 0
        for batch in pf.iter_batches(batch_size=256, columns=['repo', 'instance_id', 'trajectory_id',
            'language', 'license', 'resolved', 'metadata.category', 'metadata.teacher_model'], use_threads=False):
            for j, row in enumerate(batch.to_pylist()):
                repo = (row['repo'] or '').strip().lower()
                key = family(repo, row['instance_id'])
                category = (row.get('metadata') or {}).get('category') or '<missing>'
                language = row.get('language') or '<missing>'
                excluded = repo in blocked
                teacher = (row.get('metadata') or {}).get('teacher_model') or {}
                record = {'source': source, 'file': receipt['file'], 'row': offset+j,
                    'repo': repo, 'instance_id': row['instance_id'], 'trajectory_id': row['trajectory_id'],
                    'family_sha256': key, 'family_key': key, 'language': language, 'category': category,
                    'resolved': row['resolved'], 'license': row['license'], 'teacher': teacher,
                    'exact_repo_excluded': excluded, 'also_in_old_qwen36_pool': key in oldfamilies}
                byrow[offset+j] = record
                metadata_rows.append(record); all_families.add(key); stats['rows'] += 1
                stats['exact_repo_excluded_rows'] += excluded
                stats['source_success_rows'] += row['resolved'] == 1
                stats['bugfix_source_success_after_exact_exclusion'] += category == 'bug-fix' and row['resolved'] == 1 and not excluded
                for name, value in [('source', source), ('category', category), ('language', language),
                    ('teacher', teacher.get('name')), ('thinking', teacher.get('enable_thinking')),
                    ('source_language_category', '|'.join([source, language, category]))]:
                    meta_counts[name][str(value)] += 1
            offset += len(batch)
        offset = 0
        # Read only trace messages/tools for source-success bug-fix candidates, never patch metadata.
        for batch in pf.iter_batches(batch_size=8, columns=['messages', 'tools'], use_threads=False):
            for j in range(len(batch)):
                rec = byrow[offset+j]
                if rec['category'] != 'bug-fix' or rec['resolved'] != 1 or rec['exact_repo_excluded']:
                    continue
                row = batch.slice(j, 1).to_pylist()[0]
                try:
                    tools = [json.loads(t) if isinstance(t, str) else t for t in row['tools']]
                    messages, cleaning = normalize(row['messages'], True)
                    issues = chain_issues(messages, tools)
                    if issues:
                        raise ValueError('action_chain')
                    if any(m['role'] == 'assistant' and not m.get('tool_calls') for m in messages):
                        raise ValueError('assistant_without_tool_calls')
                    for m in messages:
                        for call in m.get('tool_calls', []):
                            f = call['function']
                            if f['name'] != 'bash' or not isinstance(f['arguments'].get('command'), str):
                                raise ValueError('invalid_bash_signature')
                            if set(f['arguments']) != {'command'}:
                                raise ValueError('noncanonical_bash_argument_keys')
                    multi = sum(len(m.get('tool_calls', [])) > 1 for m in messages)
                    observation_counts = observation_features(messages)
                    if observation_counts['non_json'] == 0 and observation_counts['json_object']:
                        observation_format = 'json_only'
                    elif observation_counts['xml_returncode'] == observation_counts['non_json'] and not observation_counts['json_object']:
                        observation_format = 'xml_only'
                    else:
                        observation_format = 'mixed_or_unknown'
                    candidates.append({**rec, 'split': holdout(rec['family_sha256']),
                        'rank_key': stable_rank(rec['family_sha256']),
                        'stratum': '|'.join([source, rec['language'], 'bug-fix']),
                        'multi_call_assistant_turns': multi, 'message_count': len(messages),
                        'observation_format': observation_format, 'observation_counts': dict(observation_counts),
                        'structural_check': 'passed_role_count_and_argument_checks',
                        'protocol_status': 'multi_call_source_order_unverified' if multi else 'single_call_pairing_observed',
                        'fork_rename_lineage_status': 'pending',
                        'execution_status': 'not_replayed', 'val_use': 'teacher_forced_candidate_only',
                        'cleaning_counts': dict(cleaning)})
                except (ValueError, TypeError, KeyError) as e:
                    quarantined.append({**rec, 'quarantine_reason': str(e)})
            offset += len(batch)
        print(json.dumps({'event': 'candidate_shard_scanned', 'files_done': files.index(receipt)+1,
            'metadata_rows': stats['rows'], 'candidate_rows': len(candidates), 'quarantined_rows': len(quarantined)}), flush=True)
    # Keep one complete representative per known family; all teacher variants inherit family split.
    byfamily = defaultdict(list)
    for row in candidates:
        byfamily[row['family_sha256']].append(row)
    ranked = []
    for key, rows in byfamily.items():
        rows.sort(key=lambda r: (r['multi_call_assistant_turns'] > 0, r['file'], r['row']))
        selected = rows[0]
        selected['available_valid_variants'] = len(rows)
        ranked.append(selected)
    ranked.sort(key=lambda r: (r['stratum'], r['rank_key']))
    counters = defaultdict(int)
    for row in ranked:
        counters[(row['split'], row['stratum'])] += 1
        row['rank_in_split_stratum'] = counters[(row['split'], row['stratum'])]
    assert len({r['family_sha256'] for r in ranked}) == len(ranked)
    assert not ({r['family_sha256'] for r in ranked if r['split']=='train'} &
                {r['family_sha256'] for r in ranked if r['split']=='val'})
    for filename, records in [('metadata_rows.jsonl', metadata_rows), ('ranked_candidates.jsonl', ranked),
        ('quarantined_rows.jsonl', quarantined), ('family_split_index.jsonl', [
            {'family_sha256':key, 'family_key':key, 'split':holdout(key), 'also_in_old_qwen36_pool':key in oldfamilies}
            for key in sorted(all_families)])]:
        (outdir / filename).write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in records))
    joint_counts = Counter('|'.join([r['split'],r['source'],r['language']]) for r in ranked)
    report = {'recorded_at_utc':datetime.now(timezone.utc).isoformat(), 'source_repo':'nvidia/Open-SWE-Traces',
        'revision':REV, 'partition':'minisweagent/qwen38_flash_next', 'files_scanned':len(files),
        'verified_files':[{k:r[k] for k in ['file','bytes','sha256','upstream_sha256']} for r in files],
        'expected_files':16, 'bytes_verified':sum(r['bytes'] for r in files), 'metadata':dict(stats),
        'metadata_counts':{k:dict(v) for k,v in meta_counts.items()}, 'unique_new_families':len(all_families),
        'old_pool_join':{'files':old_files,'rows':old_rows,'unique_families':len(oldfamilies),
            'shared_new_families':len(all_families & oldfamilies), 'purpose':'cross-teacher family grouping only; old source is not selected'},
        'candidate_valid_rows':len(candidates), 'candidate_unique_families':len(ranked),
        'candidate_split_counts':dict(Counter(r['split'] for r in ranked)),
        'candidate_source_language_split_counts':dict(joint_counts),
        'candidate_source_counts':dict(Counter(r['source'] for r in ranked)),
        'candidate_language_counts':dict(Counter(r['language'] for r in ranked)),
        'candidate_protocol_status_counts':dict(Counter(r['protocol_status'] for r in ranked)),
        'candidate_observation_format_counts':dict(Counter(r['observation_format'] for r in ranked)),
        'candidate_source_observation_format_counts':dict(Counter(r['source']+'|'+r['observation_format'] for r in ranked)),
        'candidate_shared_old_families':sum(r['also_in_old_qwen36_pool'] for r in ranked),
        'quarantined_rows':len(quarantined), 'quarantine_counts':dict(Counter(r['quarantine_reason'] for r in quarantined)),
        'split_design':{'seed':SEED,'val_hash_bins':1,'total_hash_bins':10,
            'family_key':'sha256(lowercase owner/repo + NUL + instance_id)',
            'method':'shared helper family_rank=sha256(seed+NUL+family_key); int(rank[:16],16)%10==0 val; stable rank within source×language×bug-fix',
            'benchmark_ratio':'SWE fixed51 source category is uniformly debugging. Select source bug-fix only. No validated benchmark language frequency; no invented numeric language weights.',
            'budget':'ranked reservoir only; final train/val quotas and token budget not frozen'},
        'native_multi_call_fixture':native_fixture(root),
        'native_source_sha256':{str(p.relative_to(root)):sha(p) for p in [
            root/'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/models/utils/actions_toolcall.py',
            root/'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/agents/default.py']},
        'seconds':time.monotonic()-start,
        'scope':'Candidate split/ranking only, no ms-swift body export, no training/API/GPU or task execution. Candidate resolved=1 is publisher label. Source exact agent/container revisions and tool result ordering are unverified; local native fixture proves target supports ordered multiple calls but cannot prove source ordering. Source messages lack tool_call_id. Exact official11 repositories excluded; forks/renames and semantic/PR lineage beyond exact repository+instance remain pending. val is a grouped teacher-forced holdout candidate, execution environment restoration and final quota pending.'}
    (outdir/'summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'event':'complete','files':len(files),'rows':stats['rows'],
        'candidate_families':len(ranked),'splits':report['candidate_split_counts'],
        'seconds':report['seconds'],'summary':str(outdir/'summary.json')}),flush=True)


if __name__=='__main__':
    main()
