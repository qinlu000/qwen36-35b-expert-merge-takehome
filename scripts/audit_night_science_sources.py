"""Bounded, CPU-only provenance audit of new NatureBench science traces.

Downloads only task metadata, selected trace sidecars, and <= 64 MiB of traces.
Does not execute task code, call models, or release training/evaluation data.
"""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess


STRONG_MODELS = {'deepseek-v4-pro', 'glm-5.2', 'glm-5.3',
                 'kimi-k3', 'minimax-m3', 'qwen-3.8-max'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.metadata_dir
    sources = {r['repo']: r for r in json.loads((root / 'index.json').read_text())}
    traces = sources['FrontisAI/NatureBench-traces']
    tasks_api = json.loads((root / 'FrontisAI--NatureBench.api.json').read_text())
    trace_files = {f['path']: f for f in traces['files']}
    task_files = {f['rfilename']: f for f in tasks_api['siblings']}
    receipts = []

    def fetch(repo, revision, path, info):
        target = root / 'bounded_files' / repo.replace('/', '--') / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size != info['size']:
            partial = target.with_suffix(target.suffix + '.part')
            subprocess.run(['/usr/bin/curl', '-fLsS', '--retry', '2', '--retry-all-errors', '--max-time', '60',
                            '-o', str(partial), 'https://huggingface.co/datasets/' + repo +
                            '/resolve/' + revision + '/' + path], check=True)
            partial.replace(target)
        data = target.read_bytes()
        assert len(data) == info['size'], path
        digest = sha(data)
        if info.get('lfs'):
            assert digest == info['lfs']['sha256'], path
        elif info.get('blobId'):
            blob = b'blob ' + str(len(data)).encode() + b'\0' + data
            assert hashlib.sha1(blob).hexdigest() == info['blobId'], path
        receipt = {'repo': repo, 'revision': revision, 'path': path, 'bytes': len(data),
                   'sha256': digest, 'source_identity_verified': True,
                   'local_path': str(target)}
        return data, receipt

    tasks = read_jsonl(root / 'nature_task_manifest.jsonl')
    task_map = {r['case_id']: r for r in tasks}
    index = json.loads((root / 'nature_index.json').read_text())
    valid = [r for r in index if r['model'] in STRONG_MODELS and
             r['judge_valid'] is True and r['effective_improvement'] is not None and
             all(r[k] for k in ('has_transcript', 'has_submissions', 'has_judge', 'has_result'))]
    positive = [r for r in valid if r['effective_improvement'] >= 0]
    grouped = defaultdict(list)
    for row in positive:
        grouped[row['case_id']].append(row)
    # Select one demonstrated strong run per independent source-paper family.
    representatives = [max(rows, key=lambda r: (r['effective_improvement'], r['model']))
                       for rows in grouped.values()]
    representatives.sort(key=lambda r: r['case_id'])

    def audit_rep(row):
        base = 'trajectories/' + row['harness'] + '__' + row['model'] + '/' + row['case_id'] + '/'
        files, bodies = [], {}
        for name in ('judge_verdict_v2.json', 'submissions.jsonl', 'result.json'):
            path = base + name
            data, receipt = fetch(traces['repo'], traces['revision'], path, trace_files[path])
            bodies[name] = data
            files.append(receipt)
        verdict = json.loads(bodies['judge_verdict_v2.json'])
        submissions = [json.loads(line) for line in bodies['submissions.jsonl'].splitlines() if line]
        scores = [s['aggregate_improvement'] for s in submissions
                  if isinstance(s.get('aggregate_improvement'), (int, float))]
        assert verdict['is_valid'] is True
        assert scores and abs(max(scores) - row['best_aggregate_improvement']) < 1e-9
        info_path = 'tasks/' + row['case_id'] + '/metadata.json'
        data, receipt = fetch('FrontisAI/NatureBench', tasks_api['sha'], info_path,
                              task_files[info_path])
        files.append(receipt)
        metadata = json.loads(data)
        record = {**row, 'source_paper': task_map[row['case_id']]['paper_doi'],
                  'published_domain': task_map[row['case_id']]['domain'],
                  'task_name': task_map[row['case_id']]['task_name'],
                  'family_key': 'doi:' + task_map[row['case_id']]['paper_doi'].casefold(),
                  'source_revision': traces['revision'], 'task_revision': tasks_api['sha'],
                  'validity_judge_model': verdict.get('model'),
                  'sidecar_verified': True, 'metadata_keys': sorted(metadata),
                  'task_metadata': metadata,
                  'readiness': 'candidate_hold', 'training_released': False,
                  'hold_reasons': ['ASI formal source-lineage exclusion incomplete',
                                   'per-task licenses not yet admitted',
                                   'native Claude Code differs from ASI direct_llm',
                                   'task input environment not restored or replayed']}
        return record, files, base

    with ThreadPoolExecutor(max_workers=4) as pool:
        audited = list(pool.map(audit_rep, representatives))
    records = [x[0] for x in audited]
    for _, files, _ in audited:
        receipts.extend(files)
    selected = {}
    for record, _, base in audited:
        selected.setdefault(record['published_domain'], (record, base))
    for record, _, base in audited:
        if record['compute'] == 'cpu':
            selected['cpu:' + record['case_id']] = record, base
    trace_bytes, trace_stats = 0, []
    for record, base in selected.values():
        path = base + 'transcript.jsonl'
        info = trace_files[path]
        if trace_bytes + info['size'] > 64 * 1024 * 1024:
            continue
        data, receipt = fetch(traces['repo'], traces['revision'], path, info)
        receipts.append(receipt)
        trace_bytes += len(data)
        parsed, failures = [], 0
        for line in data.splitlines():
            try:
                parsed.append(json.loads(line))
            except (ValueError, UnicodeError):
                failures += 1
        serialized = data.decode(errors='replace')
        nested = [obj for record in parsed for obj in objects(record)]
        trace_stats.append({'case_id': record['case_id'], 'model': record['model'],
                            'domain': record['published_domain'], 'bytes': len(data),
                            'records_parsed': len(parsed), 'malformed_records': failures,
                            'top_level_type_counts': dict(Counter(str(x.get('type')) for x in parsed)),
                            'nested_content_type_counts': dict(Counter(str(x['type']) for x in nested if 'type' in x)),
                            'native_tool_name_counts': dict(Counter(str(x.get('name')) for x in nested
                                                                   if x.get('type') == 'tool_use')),
                            'nonempty_thinking_field_objects': sum(bool(x.get('thinking')) for x in nested),
                            'think_tag_occurrences': serialized.count('<think>'),
                            'reasoning_content_key_occurrences': serialized.count('"reasoning_content"'),
                            'tool_use_marker_occurrences': serialized.count('"tool_use"'),
                            'has_run_py_reference': 'run.py' in serialized,
                            'code_executed_by_this_audit': False})
    hold = root / 'nature_candidate_hold.jsonl'
    hold.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    (root / 'download_receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    report = {'source': traces['repo'], 'revision': traces['revision'],
              'task_source_revision': tasks_api['sha'], 'index_rows': len(index),
              'index_unique_papers': len(task_map), 'strong_models': sorted(STRONG_MODELS),
              'valid_scored_complete_strong_rows': len(valid),
              'valid_scored_complete_strong_families': len({r['case_id'] for r in valid}),
              'nonnegative_effective_improvement_rows': len(positive),
              'nonnegative_effective_improvement_families': len(records),
              'sidecar_verified_representatives': len(records),
              'representative_models': dict(Counter(r['model'] for r in records)),
              'representative_domains': dict(Counter(r['published_domain'] for r in records)),
              'representative_compute': dict(Counter(r['compute'] for r in records)),
              'sample_trace_stats': trace_stats, 'downloaded_bytes': sum(r['bytes'] for r in receipts),
              'candidate_hold_path': str(hold), 'candidate_hold_sha256': sha(hold.read_bytes()),
              'training_released': 0, 'executable_task_dev_released': 0,
              'model_calls': 0, 'task_code_executed': False,
              'limitations': ['Nonnegative score is a conservative source-quality choice, not proof all other valid runs are failures.',
                              'One DOI is a conservative paper family; related papers/repositories may still overlap.',
                              'No ASI answer, reference or formal score was used.',
                              'No train/val split; only 45 high-quality candidate families, before further exclusions.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
