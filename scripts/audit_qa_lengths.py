#!/usr/bin/env python3
"""Count downloaded static training QA/program tokens; emit aggregates only."""

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import re
import time

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '4'
if hasattr(os, 'sched_getaffinity'):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])

import pyarrow as pa
import pyarrow.parquet as pq
from transformers import AutoTokenizer

pa.set_cpu_count(4)
pa.set_io_thread_count(4)
BUDGETS = (4096, 8192, 16384, 32768, 65536, 131072)
THINK = re.compile(r'^\s*<think>.*?</think>\s*', re.S)
PYTHON_FENCE = re.compile(r'```(?:python|py)\s*\n(.*?)```', re.S | re.I)


def summary(values):
    values = sorted(values)
    n = len(values)
    if not n:
        return {'n': 0}
    def quantile(q):
        pos = (n - 1) * q
        lo, hi = math.floor(pos), math.ceil(pos)
        return round(values[lo] + (values[hi] - values[lo]) * (pos - lo), 2)
    return {'n': n, 'mean': round(sum(values) / n, 2),
            **{f'p{int(q * 100)}': quantile(q) for q in (.5, .9, .95, .99)},
            'max': values[-1],
            'coverage': {str(b): {'fit_n': sum(v <= b for v in values),
                                  'fit_pct': round(100 * sum(v <= b for v in values) / n, 4),
                                  'over_n': sum(v > b for v in values)} for b in BUDGETS}}


def sampled_parquet(path, columns, sample_n, seed):
    """Uniform row-index sampling; decode batches but tokenize only selected rows."""
    source = pq.ParquetFile(path)
    selected = sorted(random.Random(seed).sample(range(source.metadata.num_rows),
                                                 min(sample_n, source.metadata.num_rows)))
    rows, position, target = [], 0, 0
    for batch in source.iter_batches(batch_size=512, columns=columns, use_threads=False):
        end = position + len(batch)
        indices = []
        while target < len(selected) and selected[target] < end:
            indices.append(selected[target] - position)
            target += 1
        if indices:
            rows.extend(batch.take(pa.array(indices, type=pa.int64())).to_pylist())
        position = end
        if target == len(selected):
            break
    metadata = {'path': str(path), 'population_rows': source.metadata.num_rows,
                'sample_rows': len(rows), 'seed': seed,
                'method': 'simple random sample without replacement of row indices',
                'selected_row_indices_sha256': hashlib.sha256(json.dumps(selected).encode()).hexdigest(),
                'decoded_rows_until_last_sample': position,
                'columns_read': columns, 'schema_has_token_length': False}
    return rows, metadata


def audit(rows, source_name, tokenizer):
    lengths = defaultdict(list)
    counters = Counter()
    for row in rows:
        if source_name == 'd3_gym_32b':
            raw = [{'role': 'system', 'content': row['instruction']},
                   {'role': 'user', 'content': row['input']},
                   {'role': 'assistant', 'content': row['output']}]
        elif source_name == 'open_science':
            raw = [{'role': 'user', 'content': row['input']},
                   {'role': 'assistant', 'content': row['output']}]
        else:
            raw = row['messages']
        cleaned = copy.deepcopy(raw)
        removed = []
        for message in cleaned:
            if message['role'] != 'assistant':
                continue
            text = message.get('content') or ''
            blocks = THINK.findall(text)
            removed.extend(blocks)
            counters['leading_balanced_think_prefixes'] += len(blocks)
            if text.count('<think>') != text.count('</think>'):
                counters['assistant_messages_unbalanced_think_tags'] += 1
            if message.get('reasoning_content'):
                removed.append(message['reasoning_content'])
            message.pop('reasoning_content', None)
            message['content'] = THINK.sub('', text, count=1).lstrip('\n')
        if removed:
            counters['rows_with_explicit_reasoning_removed'] += 1
        counters['rows'] += 1
        for label, messages, preserve in [('raw', raw, True), ('clean', cleaned, False)]:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False,
                enable_thinking=preserve, preserve_thinking=preserve)
            lengths[f'{label}_rendered_total'].append(len(tokenizer.encode(rendered, add_special_tokens=False)))
            assistant_lengths = [len(tokenizer.encode(m.get('content') or '', add_special_tokens=False))
                                 for m in messages if m['role'] == 'assistant']
            lengths[f'{label}_assistant_per_message'].extend(assistant_lengths)
            lengths[f'{label}_assistant_per_record'].append(sum(assistant_lengths))
        lengths['question_user_content'].append(sum(
            len(tokenizer.encode(m.get('content') or '', add_special_tokens=False))
            for m in raw if m['role'] == 'user'))
        lengths['system_instruction_content'].append(sum(
            len(tokenizer.encode(m.get('content') or '', add_special_tokens=False))
            for m in raw if m['role'] == 'system'))
        lengths['removed_published_reasoning_with_tags'].append(sum(
            len(tokenizer.encode(t, add_special_tokens=False)) for t in removed))
        if source_name == 'd3_gym_32b':
            code = PYTHON_FENCE.findall(cleaned[-1]['content'])
            counters['rows_with_python_fence'] += bool(code)
            lengths['python_fenced_code_combined'].append(sum(
                len(tokenizer.encode(t, add_special_tokens=False)) for t in code))
        if counters['rows'] % 250 == 0:
            print(json.dumps({'source': source_name, 'rows_counted': counters['rows']}), flush=True)
    return {'structure_counts': dict(counters), 'metrics': {k: summary(v) for k, v in lengths.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--model-metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--openr1-per-file', type=int, default=200)
    parser.add_argument('--open-science-sample', type=int, default=0)
    args = parser.parse_args()
    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(args.model_metadata, local_files_only=True, trust_remote_code=False)
    report = {
        'scope': 'Downloaded training candidates only; no formal benchmark rows, model weights, API, sample execution or training export.',
        'tokenizer': {'model': 'Qwen/Qwen3.6-35B-A3B',
                      'revision': args.model_metadata.name,
                      'class': type(tokenizer).__name__,
                      'transformers': importlib.metadata.version('transformers'),
                      'tokenizers': importlib.metadata.version('tokenizers'),
                      'chat_template_sha256': hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()},
        'method': {'raw': 'enable_thinking=true, preserve_thinking=true, add_generation_prompt=false',
                   'clean': 'explicitly remove only one leading balanced assistant <think> prefix and reasoning_content; false/false, no generation prompt',
                   'tag_policy': 'nonprefix and unbalanced tags retained; visible explanation outside leading <think> retained',
                   'percentile': 'linear interpolation at (n-1)*q',
                   'coverage': 'length <= budget, binary K=1024; assistant content excludes message wrappers',
                   'cpu_affinity': sorted(os.sched_getaffinity(0)),
                   'tokenizers_parallelism': False},
        'sources': {}}
    def save():
        report['elapsed_seconds'] = round(time.monotonic() - started, 2)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    path = next((args.repo / 'artifacts/data/raw/d3_gym_32b').rglob('Qwen3_32B_trajectories.json'))
    rows = json.loads(path.read_text())
    result = audit(rows, 'd3_gym_32b', tokenizer)
    result['selection'] = {'path': str(path), 'population_rows': len(rows), 'sample_rows': len(rows),
                           'method': 'full census', 'revision': path.parent.name,
                           'mapping': 'instruction -> system; input -> user; output -> assistant (temporary measurement mapping)',
                           'schema_has_token_length': False}
    report['sources']['d3_gym_32b'] = result
    save()
    print(json.dumps({'completed': 'd3_gym_32b', 'rows': len(rows), 'elapsed_seconds': report['elapsed_seconds']}), flush=True)
    if args.openr1_per_file:
        rows, manifests = [], []
        for i, path in enumerate(sorted((args.repo / 'artifacts/data/raw/openr1_math').rglob('*.parquet'))):
            subset, manifest = sampled_parquet(path, ['messages'], args.openr1_per_file, 20261016 + i)
            rows.extend(subset)
            manifests.append(manifest)
        result = audit(rows, 'openr1_math', tokenizer)
        result['selection'] = {'method': 'stratify by all downloaded parquet files; equal per-file simple random sample; unweighted sample statistics, not population estimates',
                               'files': manifests, 'sample_rows': len(rows),
                               'revision': path.parent.parent.name,
                               'excluded_columns': ['answer', 'solution', 'generations', 'correctness metadata']}
        report['sources']['openr1_math'] = result
        save()
        print(json.dumps({'completed': 'openr1_math', 'rows': len(rows), 'elapsed_seconds': report['elapsed_seconds']}), flush=True)
    if args.open_science_sample:
        path = next((args.repo / 'artifacts/data/raw/open_science').rglob('*.parquet'))
        rows, manifest = sampled_parquet(path, ['input', 'output'], args.open_science_sample, 20261016)
        result = audit(rows, 'open_science', tokenizer)
        result['selection'] = {**manifest, 'revision': path.parent.parent.name,
                               'excluded_columns': ['expected_answer']}
        report['sources']['open_science'] = result
        save()
        print(json.dumps({'completed': 'open_science', 'rows': len(rows), 'elapsed_seconds': report['elapsed_seconds']}), flush=True)
    else:
        report['open_science_not_tokenized'] = 'Optional audit deferred: 15.7GB parquet with nine large row groups; no length column.'
        save()


if __name__ == '__main__':
    main()
