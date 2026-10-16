#!/usr/bin/env python3
"""CPU-only, bounded audit of fixed Math-v4 and Science-v2 training candidates.

Never executes sample code, creates training splits, or prints sample bodies.
"""

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
    os.environ[key] = '2'
if hasattr(os, 'sched_getaffinity'):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])

import pyarrow as pa
import pyarrow.parquet as pq
from transformers import AutoTokenizer

pa.set_cpu_count(2)
pa.set_io_thread_count(2)
THINK = re.compile(r'^\s*<think>(.*?)</think>\s*', re.S)
REVISIONS = {
    'Math-v4': '84d42ad0cb960f07f951b9baa9ed2b46a5a18c66',
    'Science-v2': '6536a5021222a94126968e8c92f29ee47fc8a7df',
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def summary(values):
    values = sorted(values)
    if not values:
        return {'n': 0}
    def q(frac):
        position = (len(values) - 1) * frac
        lo, hi = math.floor(position), math.ceil(position)
        return round(values[lo] + (values[hi] - values[lo]) * (position - lo), 2)
    return {'n': len(values), 'mean': round(sum(values) / len(values), 2),
            'p50': q(.5), 'p95': q(.95), 'max': values[-1],
            'fit_counts': {str(b): sum(v <= b for v in values)
                           for b in (128, 512, 1024, 4096, 8192, 16384, 32768, 65536)}}


def normalize(row):
    """Decode documented JSON strings without changing tool names or actions."""
    messages = copy.deepcopy(row['messages'])
    tools = copy.deepcopy(row.get('tools') or [])
    if isinstance(tools, str):
        tools = json.loads(tools) if tools.strip() else []
    for tool in tools:
        function = tool.get('function', tool)
        if isinstance(function.get('parameters'), str):
            function['parameters'] = json.loads(function['parameters'])
    for message in messages:
        if message.get('role') not in {'system', 'user', 'assistant', 'tool'}:
            raise ValueError('unexpected_message_role')
        message['content'] = message.get('content') or ''
        if not isinstance(message['content'], str):
            raise ValueError('non_text_content')
        for call in message.get('tool_calls') or []:
            function = call.get('function', call)
            if isinstance(function.get('arguments'), str):
                function['arguments'] = json.loads(function['arguments'])
            if not isinstance(function.get('arguments', {}), dict):
                raise ValueError('non_object_tool_arguments')
    return messages, tools


def clean(messages):
    cleaned = copy.deepcopy(messages)
    counts = Counter()
    for message in cleaned:
        if message['role'] != 'assistant':
            continue
        text = message['content']
        for field in ('reasoning_content', 'reason_content'):
            counts[field + '_nonempty'] += bool(message.get(field))
            message.pop(field, None)
        if text.count('<think>') != text.count('</think>'):
            raise ValueError('unbalanced_think')
        if '<think>' in text or '</think>' in text:
            match = THINK.match(text)
            if not match or '<think>' in match.group(1):
                raise ValueError('nonleading_or_nested_think')
            text = text[match.end():]
            if '<think>' in text or '</think>' in text:
                raise ValueError('multiple_or_nonleading_think')
            counts['leading_think_removed'] += 1
        message['content'] = text
        if not text.strip() and not message.get('tool_calls'):
            counts['empty_clean_assistant_without_action'] += 1
    # Cleaning must preserve every role, action, and observation.
    assert [m['role'] for m in cleaned] == [m['role'] for m in messages]
    assert [m.get('tool_calls') for m in cleaned] == [m.get('tool_calls') for m in messages]
    assert [m['content'] for m in cleaned if m['role'] == 'tool'] == [m['content'] for m in messages if m['role'] == 'tool']
    return cleaned, counts


def synthetic_checks(tokenizer):
    fixtures = [
        {'messages': [{'role': 'user', 'content': 'Compute 1+1.'},
                      {'role': 'assistant', 'content': '<think>private</think>2',
                       'reasoning_content': 'private', 'reason_content': 'private'}]},
        {'messages': [{'role': 'user', 'content': 'Use a tool.'},
                      {'role': 'assistant', 'content': '', 'reasoning_content': 'private',
                       'tool_calls': [{'id': 'a', 'function': {'name': 'python', 'arguments': '{"code":"print(1+1)"}'}}]},
                      {'role': 'tool', 'content': '2', 'tool_call_id': 'a'},
                      {'role': 'assistant', 'content': 'The answer is 2.'}]},
    ]
    lengths = []
    for fixture in fixtures:
        messages, tools = normalize(fixture)
        cleaned, _ = clean(messages)
        rendered = tokenizer.apply_chat_template(cleaned, tools=tools or None, tokenize=False,
                                                add_generation_prompt=False, enable_thinking=False,
                                                preserve_thinking=False)
        assert 'private' not in rendered
        assert len(cleaned) == len(messages)
        if any(m['role'] == 'tool' for m in messages):
            assert '<function=python>' in rendered and 'print(1+1)' in rendered
        lengths.append(len(tokenizer.encode(rendered, add_special_tokens=False)))
    for text in ('<think>unfinished', 'answer <think>hidden</think>', '<think>one</think><think>two</think>'):
        try:
            clean([{'role': 'assistant', 'content': text}])
        except ValueError:
            continue
        raise AssertionError('Malformed thought fixture was not quarantined')
    return {'passed': True, 'valid_fixtures': 2, 'quarantine_fixtures': 3,
            'clean_rendered_fixture_lengths': lengths,
            'empty_think_wrapper_retained': '<think>\n\n</think>' in tokenizer.apply_chat_template(
                [{'role': 'user', 'content': 'x'}, {'role': 'assistant', 'content': 'y'}],
                tokenize=False, add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)}


def method_group(row):
    calls = [c.get('function', c).get('name', '') for m in row['messages'] for c in m.get('tool_calls') or []]
    names = '|'.join(calls).lower()
    has_tools = bool(calls or any(m['role'] == 'tool' for m in row['messages']))
    if 'tavily' in names or 'search' in names or 'browse' in names:
        return 'search_tool'
    if 'python' in names or 'code' in names or row.get('subset', '').upper() == 'TIR':
        return 'python_or_TIR'
    return 'other_tool' if has_tools else 'CoT_no_tool'


def meta_key(row, source):
    metadata = row.get('metadata') or {}
    metadata = metadata if isinstance(metadata, dict) else {}
    return (source, str(metadata.get('generation_model') or 'publisher_DeepSeek-V4-Pro_High'),
            method_group(row), str(metadata.get('topic') or 'Mathematics'),
            str(metadata.get('subtopic') or '<not_provided>'), str(row.get('source') or source),
            str(row.get('license') or '<missing>'))


def provenance(row):
    metadata = row.get('metadata') or {}
    metadata = metadata if isinstance(metadata, dict) else {}
    question = row.get('problem') or '\n'.join(m.get('content') or '' for m in row['messages'] if m['role'] == 'user')
    normalized = ' '.join(question.split())
    return {'uuid': row.get('uuid'), 'url': row.get('url') or metadata.get('QuestionLink'),
            'prompt_normalized_sha256': sha(normalized.encode()),
            'messages_sha256': sha(json.dumps(row['messages'], sort_keys=True, ensure_ascii=False).encode())}


def audit_sample(items, tokenizer, output, row_records):
    metrics = defaultdict(list)
    groups = defaultdict(lambda: defaultdict(list))
    counts, quarantines = Counter(), Counter()
    for source, index, row in items:
        group = meta_key(row, source)
        record = {'source': source, 'row_index': index, 'group': group, **provenance(row)}
        try:
            raw, tools = normalize(row)
            cleaned, row_counts = clean(raw)
            row_metrics = {}
            for label, messages, preserve in [('raw', raw, True), ('clean', cleaned, False)]:
                rendered = tokenizer.apply_chat_template(messages, tools=tools or None, tokenize=False,
                                                        add_generation_prompt=False,
                                                        enable_thinking=preserve, preserve_thinking=preserve)
                row_metrics[label + '_rendered_complete_sequence'] = len(tokenizer.encode(rendered, add_special_tokens=False))
                body_lengths = [len(tokenizer.encode(m['content'], add_special_tokens=False))
                                for m in messages if m['role'] == 'assistant']
                row_metrics[label + '_assistant_content_body_proxy'] = sum(body_lengths)
                if label == 'clean':
                    row_metrics['clean_final_assistant_content_tokens'] = body_lengths[-1] if body_lengths else 0
                    row_metrics['clean_assistant_tool_call_count'] = sum(len(m.get('tool_calls') or []) for m in messages if m['role'] == 'assistant')
                    if row_metrics['clean_assistant_content_body_proxy'] <= 128:
                        counts['clean_body_le128_tokens_form_only'] += 1
                    if row_metrics['clean_assistant_content_body_proxy'] >= 512:
                        counts['clean_body_ge512_tokens_form_only'] += 1
            counts.update(row_counts)
            counts['accepted_rows'] += 1
            for key, value in row_metrics.items():
                metrics[key].append(value)
                groups[group][key].append(value)
            record['metrics'] = row_metrics
            record['status'] = 'structurally_renderable_not_quality_approved'
        except (ValueError, TypeError, KeyError) as error:
            reason = str(error) if str(error) in {
                'unbalanced_think', 'nonleading_or_nested_think', 'multiple_or_nonleading_think',
                'non_text_content', 'non_object_tool_arguments', 'unexpected_message_role'} else type(error).__name__
            quarantines[reason] += 1
            record['status'] = 'quarantined'
            record['reason'] = reason
        row_records.write(json.dumps(record, ensure_ascii=False) + '\n')
    return {'sample_rows': len(items), 'counts': dict(counts), 'quarantine_counts': dict(quarantines),
            'metrics': {key: summary(values) for key, values in metrics.items()},
            'groups': [{'key': key, 'metrics': {k: summary(v) for k, v in metrics.items()}}
                       for key, metrics in sorted(groups.items())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--model-metadata', type=Path, required=True)
    parser.add_argument('--range-science', action='store_true', help='Also audit bounded, separately downloaded Science ranges')
    parser.add_argument('--science-per-group', type=int, default=8)
    args = parser.parse_args()
    started = time.monotonic()
    base = args.repo / 'artifacts/data/audits/new_academic_20261016'
    tokenizer = AutoTokenizer.from_pretrained(args.model_metadata, local_files_only=True, trust_remote_code=False)
    report = {
        'scope': 'CPU audit only; no sample code execution, teacher API, GPU, train/val selection or training export.',
        'revisions': REVISIONS,
        'tokenizer': {'model': 'Qwen/Qwen3.6-35B-A3B', 'revision': args.model_metadata.name,
                      'transformers': importlib.metadata.version('transformers'),
                      'tokenizers': importlib.metadata.version('tokenizers'),
                      'chat_template_sha256': sha(tokenizer.chat_template.encode())},
        'method': {'raw_template': 'enable_thinking=true,preserve_thinking=true,add_generation_prompt=false',
                   'clean_template': 'enable_thinking=false,preserve_thinking=false,add_generation_prompt=false',
                   'clean_policy': 'Remove assistant reasoning_content/reason_content and one balanced leading think block; quarantine malformed/nonleading/multiple blocks. Preserve visible explanation, tool calls, observations and all roles.',
                   'tool_normalization': 'Decode documented JSON-string function arguments/parameters, retaining their original fields/actions.',
                   'length_units': 'Qwen tokenizer tokens; 1K=1024',
                   'supervision_proxy': 'Assistant content bodies only, excludes thought fields, wrappers and tool call serialization. NOT final ms-swift labels; no train windows/packing defined.',
                   'processed_proxy': 'One complete rendered sequence, before training repetition/window duplication/padding. NOT final training cost.',
                   'short_answer_proxy': '<=128 clean assistant-content tokens per record is only a formal shortness flag, not proof of final-answer-only or correctness.',
                   'cpu_affinity': sorted(os.sched_getaffinity(0)), 'seed': 20261016},
        'synthetic_checks': synthetic_checks(tokenizer),
        'download_receipts': json.loads((base / 'download_receipts.json').read_text()),
        'sources': {},
    }
    math_file = args.repo / 'artifacts/data/raw/nemotron_sft_math_v4' / REVISIONS['Math-v4'] / 'train-00000-of-00012.parquet'
    source = pq.ParquetFile(math_file)
    metadata_columns = ['uuid', 'source', 'license', 'url', 'dataset', 'subset']
    meta = source.read(columns=metadata_columns, use_threads=False).to_pylist()
    counters = {key: dict(Counter(str(row.get(key)) for row in meta))
                for key in ('source', 'license', 'dataset', 'subset')}
    indices = sorted(random.Random(20261016).sample(range(len(meta)), min(128, len(meta))))
    table = source.read(columns=['messages', 'tools', 'metadata', 'problem'] + metadata_columns, use_threads=False)
    sampled = table.take(pa.array(indices, type=pa.int64())).to_pylist()
    with (base / 'row_measurements.jsonl').open('w') as row_records:
        report['sources']['Math-v4'] = {
            'selection': {'file': str(math_file.relative_to(args.repo)), 'downloaded_shards': 1, 'total_shards': 12,
                          'file_rows': len(meta), 'metadata_census_columns': metadata_columns,
                          'method': '128 uniform random row indices within first shard only; NOT a random sample of the full dataset',
                          'sample_index_sha256': sha(json.dumps(indices).encode()),
                          'downloaded_shard_schema': str(source.schema_arrow)},
            'metadata_counts_in_downloaded_shard': counters,
            'metadata_missing_url_rows': sum(not r.get('url') for r in meta),
            'metadata_unique_uuid_rows': len({r['uuid'] for r in meta}),
            **audit_sample([('Math-v4', i, row) for i, row in zip(indices, sampled)], tokenizer, base, row_records),
        }
        science_receipts = list(report['download_receipts'])
        if args.range_science:
            science_receipts += json.loads((base / 'range_download_receipts.json').read_text())
        grouped_rows = defaultdict(list)
        for receipt in science_receipts:
            if receipt['source'] != 'Science-v2' or receipt.get('skipped'):
                continue
            path = args.repo / receipt['local_path']
            data = path.read_bytes()
            assert sha(data) == receipt['sha256']
            lines = data.split(b'\n')[:-1]
            if '.range' in path.name:
                lines = lines[1:]
            grouped_rows[receipt['path']].extend([(path.name + ':' + str(i), json.loads(line))
                                                  for i, line in enumerate(lines) if line])
        for source_path, indexed_rows in grouped_rows.items():
            parsed = [r for _, r in indexed_rows]
            by_group = defaultdict(list)
            group_counts = Counter()
            for index, row in indexed_rows:
                key = meta_key(row, source_path)
                group_counts[key] += 1
                by_group[key].append((source_path, index, row))
            chosen = []
            rng = random.Random(20261016)
            for key, candidates in sorted(by_group.items()):
                chosen.extend(rng.sample(candidates, min(args.science_per_group, len(candidates))))
            report['sources']['Science-v2/' + source_path] = {
                'selection': {'method': 'Bounded <=8MiB prefix plus optional 7 separated <=8MiB ranges/file; complete inner lines only; equal capped random rows per observed teacher/method/topic/subtopic/source/license group. NOT population-representative.',
                              'per_group_cap': args.science_per_group,
                              'complete_parsed_rows': len(parsed), 'observed_groups': len(by_group),
                              'prefix_group_counts': [{'key': key, 'rows': n} for key, n in sorted(group_counts.items())]},
                'missing_source_url_rows': sum(not provenance(r)['url'] for r in parsed),
                'unique_uuid_rows': len({r['uuid'] for r in parsed}),
                **audit_sample(chosen, tokenizer, base, row_records),
            }
    report['row_measurements_path'] = str((base / 'row_measurements.jsonl').relative_to(args.repo))
    if args.range_science:
        report['range_download_receipts'] = json.loads((base / 'range_download_receipts.json').read_text())
    report['elapsed_seconds'] = round(time.monotonic() - started, 2)
    dump(base / 'aggregate.json', report)
    print(json.dumps({'output': str(base / 'aggregate.json'), 'elapsed_seconds': report['elapsed_seconds'],
                      'accepted_rows': {k: v['counts'].get('accepted_rows', 0) for k, v in report['sources'].items()}}), flush=True)


if __name__ == '__main__':
    main()
