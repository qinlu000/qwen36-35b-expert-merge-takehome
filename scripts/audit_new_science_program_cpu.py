"""Audit new EcoCoder program candidates without executing code or training."""

import os
for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import argparse
import ast
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re

from transformers import AutoTokenizer

from candidate_selection import family_partition, family_rank, text_hash


REVISION = '09591b2b7b261aeb37d7db464f2af31eaa24baa0'
MODEL_REVISION = '995ad96eacd98c81ed38be0c5b274b04031597b0'
THINK = re.compile(r'\A\s*<think>.*?</think>\s*', re.S)
PYTHON = re.compile(r'```(?:python|py)\s*\n(.*?)```', re.S | re.I)


def clean_messages(messages):
    result = copy.deepcopy(messages)
    for msg in result:
        if msg['role'] != 'assistant':
            continue
        msg.pop('reasoning_content', None)
        content = msg.get('content') or ''
        if content.count('<think>') != content.count('</think>'):
            raise ValueError('unbalanced_think')
        msg['content'] = THINK.sub('', content, count=1)
    return result


def distribution(values):
    values = sorted(values)
    return {'n': len(values), 'mean': sum(values) / len(values),
            'median': values[(len(values) - 1) // 2],
            'p95': values[int((len(values) - 1) * .95)], 'max': max(values)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    source = root / 'artifacts/data/raw/ecocoder' / REVISION
    records = []
    for path in sorted((source / 'data/ecology').glob('*.jsonl')):
        for line_number, line in enumerate(path.open(), 1):
            row = json.loads(line)
            records.append((path.stem, line_number, row))

    # Join both method/template and paper lineage across every published split.
    parents = list(range(len(records)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    seen = {}
    for i, (_, _, row) in enumerate(records):
        metadata = row['metadata']
        prompt = '\n'.join(m['content'] for m in row['messages'] if m['role'] == 'user')
        keys = ['question:' + text_hash(prompt)]
        if row.get('method'):
            keys.append('method:' + row['method'].strip().casefold())
        keys += [key + ':' + str(metadata[key]).strip().casefold()
                 for key in ('doi', 'paper_id') if metadata.get(key)]
        for key in keys:
            if key in seen:
                parents[find(i)] = find(seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i in range(len(records)):
        groups[find(i)].append(i)
    family_keys = {i: 'ecocoder-family:' + hashlib.sha256(
        '\n'.join(sorted(records[j][2]['id'] for j in members)).encode()).hexdigest()
        for i, members in groups.items()}

    manifests, quarantine = [], Counter()
    for component, members in groups.items():
        candidates = []
        for i in members:
            source_split, line_number, row = records[i]
            if (row['metadata'].get('language') or '').casefold() != 'python':
                continue
            try:
                cleaned = clean_messages(row['messages'])
            except ValueError as error:
                quarantine[str(error)] += 1
                continue
            assistant = '\n'.join(m['content'] for m in cleaned if m['role'] == 'assistant')
            snippets = PYTHON.findall(assistant)
            if not snippets:
                quarantine['no_python_fence'] += 1
                continue
            try:
                for code in snippets:
                    ast.parse(code)
            except SyntaxError:
                quarantine['python_syntax_error'] += 1
                continue
            candidates.append((family_rank(row['id']), i, len(snippets)))
        if not candidates:
            continue
        _, selected, snippet_count = min(candidates)
        source_split, line_number, row = records[selected]
        family_key = family_keys[component]
        manifests.append({
            'source_repo': 'alrobles/ecocoder-scientific-reasoning',
            'revision': REVISION, 'source_file': f'data/ecology/{source_split}.jsonl',
            'line': line_number, 'row_id': row['id'], 'family_key': family_key,
            'family_rows': len(members), 'partition': family_partition(family_key),
            'rank': family_rank(family_key), 'target': 'asi', 'category': 'biology',
            'source_domain': row['domain'], 'method_category': row['method_category'],
            'language': 'Python', 'python_fences_syntax_valid': snippet_count,
            'status': 'needs_execution_and_source_overlap_verification',
            'val_status': 'needs_inputs_environment_and_independent_verifier',
            'license': 'Apache-2.0 dataset card; source-paper obligations need review',
        })
    manifests.sort(key=lambda row: row['rank'])
    train = [r for r in manifests if r['partition'] == 'train']
    val = [r for r in manifests if r['partition'] == 'val']
    assert not ({r['family_key'] for r in train} & {r['family_key'] for r in val})

    tokenizer = AutoTokenizer.from_pretrained(root / 'artifacts/models/base_metadata' / MODEL_REVISION,
                                              local_files_only=True, trust_remote_code=False)
    fixture = [{'role': 'user', 'content': 'Synthetic input.'},
               {'role': 'assistant', 'content': '<think>PRIVATE_FIXTURE</think>\n```python\nx = 1\n```'}]
    fixture_clean = clean_messages(fixture)
    assert 'PRIVATE_FIXTURE' not in fixture_clean[1]['content']
    assert 'x = 1' in fixture_clean[1]['content']
    sample = random.Random(20261016).sample(range(len(records)), min(128, len(records)))
    metrics = defaultdict(list)
    sample_quarantine = Counter()
    for i in sample:
        messages = records[i][2]['messages']
        try:
            cleaned = clean_messages(messages)
        except ValueError as error:
            sample_quarantine[str(error)] += 1
            continue
        for mode, conversation in [('raw', messages), ('clean', cleaned)]:
            rendered = tokenizer.apply_chat_template(conversation, tokenize=False,
                add_generation_prompt=False, enable_thinking=False, preserve_thinking=(mode == 'raw'))
            metrics[mode + '_full_sequence'].append(len(tokenizer.encode(rendered, add_special_tokens=False)))
            metrics[mode + '_assistant_content_proxy'].append(sum(len(tokenizer.encode(
                m['content'], add_special_tokens=False)) for m in conversation if m['role'] == 'assistant'))

    candidate_metrics = defaultdict(list)
    by_id = {row['id']: row for _, _, row in records}
    for candidate in manifests:
        messages = clean_messages(by_id[candidate['row_id']]['messages'])
        rendered = tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)
        candidate['clean_full_sequence_tokens'] = len(tokenizer.encode(rendered, add_special_tokens=False))
        candidate['assistant_content_token_proxy'] = sum(len(tokenizer.encode(
            m['content'], add_special_tokens=False)) for m in messages if m['role'] == 'assistant')
        candidate_metrics['clean_full_sequence'].append(candidate['clean_full_sequence_tokens'])
        candidate_metrics['assistant_content_proxy'].append(candidate['assistant_content_token_proxy'])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for partition, rows in [('train', train), ('val', val)]:
        (args.output_dir / f'{partition}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    summary = {
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'repo': 'alrobles/ecocoder-scientific-reasoning', 'revision': REVISION,
        'source_rows': len(records), 'source_split_counts': dict(Counter(s for s, _, r in records)),
        'language_counts': dict(Counter(r['metadata']['language'] for _, _, r in records)),
        'source_model_counts': dict(Counter(r['metadata'].get('source') for _, _, r in records)),
        'doi_present': sum(bool(r['metadata'].get('doi')) for _, _, r in records),
        'paper_id_present': sum(bool(r['metadata'].get('paper_id')) for _, _, r in records),
        'method_count': len({r['method'] for _, _, r in records}),
        'conservative_joined_families': len(groups), 'python_candidate_families': len(manifests),
        'candidate_partitions': {'train': len(train), 'val': len(val)},
        'python_rows_quarantined': dict(quarantine), 'family_overlap_train_val': 0,
        'sample_records': len(sample), 'sample_quarantine': dict(sample_quarantine),
        'token_statistics': {key: distribution(values) for key, values in metrics.items()},
        'all_python_candidate_token_statistics': {key: distribution(values) for key, values in candidate_metrics.items()},
        'supervision_measure': 'assistant content token proxy only, not final Swift labels or windowed processed tokens',
        'candidate_target_category': 'ASI biology only; ecology/R/Python source is not an 11-domain replacement',
        'source_verification': 'publisher quality score is not execution success; code AST parsed only, never executed',
        'split_policy': 'all published synthetic source splits jointly grouped by method, DOI/paper_id and question hash; global candidate family hash reserve; no source test score used',
        'training_or_model_calls': False,
        'limitations': ['No independent verifier or runtime environment yet; no executable task-dev claimed.',
                        'ASI source-lineage exclusion pending; candidates are not approved training data.',
                        'Target HLE/ASI image, other science disciplines, and terminal skills are not supplied.'],
    }
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
