#!/usr/bin/env python3
"""Keep complete SWE trajectories by existing HF-template token metadata."""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
from itertools import zip_longest
import json
from pathlib import Path
import shutil

SUBMIT = 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'


def check_complete(row):
    pending = deque()
    calls = observations = 0
    for message in row['messages']:
        if message['role'] == 'assistant':
            assert not pending, 'unanswered calls before another assistant'
            for call in message.get('tool_calls', []):
                arguments = call['function']['arguments']
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                assert call['function']['name'] == 'bash'
                assert set(arguments) == {'command'}
                pending.append((call['id'], arguments['command']))
                calls += 1
        elif message['role'] == 'tool':
            assert pending and message['tool_call_id'] == pending.popleft()[0]
            observations += 1
    assert row['messages'][-1]['role'] == 'assistant'
    assert len(pending) == 1 and pending[0][1] == SUBMIT
    assert len(row['messages'][-1]['tool_calls']) == 1
    return {'messages': len(row['messages']), 'bash_calls': calls,
            'tool_observations': observations, 'complete_final_submissions': 1}


def statistics(metadata):
    lengths = sorted(row['full_sequence_tokens'] for row in metadata)
    return {'rows': len(metadata),
            'full_sequence_tokens': sum(lengths),
            'min_full_sequence_tokens': min(lengths) if lengths else None,
            'median_full_sequence_tokens': lengths[len(lengths) // 2] if lengths else None,
            'max_full_sequence_tokens': max(lengths) if lengths else None,
            'assistant_output_tokens': sum(row.get('assistant_output_tokens', 0) for row in metadata),
            'max_assistant_output_tokens': max((row.get('max_assistant_output_tokens', 0)
                                                for row in metadata), default=None),
            'languages': dict(Counter(row.get('language', 'unknown') for row in metadata)),
            'sources': dict(Counter(row.get('source', 'unknown') for row in metadata))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-tokens', type=int, default=32768)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source_summary = json.loads((args.source / 'summary.json').read_text())
    all_metadata, kept_metadata, excluded_metadata = [], [], []
    structure = Counter()
    kept_lines, excluded_lines = [], []
    with (args.source / 'train.messages.jsonl').open('rb') as messages, \
            (args.source / 'train.manifest.jsonl').open('rb') as manifest, \
            (args.output / 'train.messages.jsonl').open('wb') as selected_messages, \
            (args.output / 'train.manifest.jsonl').open('wb') as selected_manifest, \
            (args.output / 'train.excluded_over_limit.manifest.jsonl').open('wb') as excluded_manifest, \
            (args.output / 'train.row_mapping.jsonl').open('w') as mapping:
        for line, (message_bytes, manifest_bytes) in enumerate(zip_longest(messages, manifest), 1):
            assert message_bytes is not None and manifest_bytes is not None, 'row-count mismatch'
            row, metadata = json.loads(message_bytes), json.loads(manifest_bytes)
            complete = check_complete(row)
            assert metadata.get('message_count', complete['messages']) == complete['messages']
            assert metadata['full_sequence_tokens'] > 0
            all_metadata.append(metadata)
            keep = metadata['full_sequence_tokens'] <= args.max_tokens
            if keep:
                selected_messages.write(message_bytes)
                selected_manifest.write(manifest_bytes)
                kept_metadata.append(metadata)
                kept_lines.append(line)
                structure.update(complete)
            else:
                excluded_manifest.write(manifest_bytes)
                excluded_metadata.append(metadata)
                excluded_lines.append(line)
            mapping.write(json.dumps({'source_line_1based': line,
                'selected_line_1based': len(kept_metadata) if keep else None,
                'excluded_line_1based': None if keep else len(excluded_metadata),
                'full_sequence_tokens': metadata['full_sequence_tokens'],
                'instance_id': metadata.get('instance_id'),
                'family_key': metadata.get('family_key')}, ensure_ascii=False) + '\n')
    val_metadata = []
    with (args.source / 'val.messages.jsonl').open('rb') as messages, \
            (args.source / 'val.manifest.jsonl').open('rb') as manifest:
        for message_bytes, manifest_bytes in zip_longest(messages, manifest):
            assert message_bytes is not None and manifest_bytes is not None, 'val row-count mismatch'
            check_complete(json.loads(message_bytes))
            val_metadata.append(json.loads(manifest_bytes))
    for name in ('val.messages.jsonl', 'val.manifest.jsonl'):
        shutil.copyfile(args.source / name, args.output / name)
        assert (args.source / name).read_bytes() == (args.output / name).read_bytes()
    inputs = {name: {'path': str((args.source / name).resolve()),
                     'bytes': (args.source / name).stat().st_size}
              for name in ('summary.json', 'train.messages.jsonl', 'train.manifest.jsonl',
                           'val.messages.jsonl', 'val.manifest.jsonl')}
    summary = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_directory': str(args.source.resolve()), 'output_directory': str(args.output.resolve()),
        'source_dataset': source_summary['source'], 'source_revision': source_summary['revision'],
        'teacher': source_summary['teacher'], 'max_complete_sequence_tokens': args.max_tokens,
        'token_count_scope': 'Existing full_sequence_tokens from pinned original HF Qwen chat template; '
                             'not newly tokenized native Swift lengths or supervised-token counts.',
        'filter_rule': 'Train complete sequence <= limit; preserve selected messages/manifest original '
                       'line bytes and source order. No truncation, resampling or model execution.',
        'inputs': inputs, 'original_train': statistics(all_metadata),
        'kept_train': statistics(kept_metadata), 'excluded_train': statistics(excluded_metadata),
        'original_train_thresholds': {str(limit): statistics([row for row in all_metadata
             if row['full_sequence_tokens'] <= limit]) for limit in (32768, 49152, 65536)},
        'kept_structure': dict(structure), 'source_lines_kept_1based': kept_lines,
        'source_lines_excluded_1based': excluded_lines,
        'val': {'rows': len(val_metadata), 'byte_identical_messages_and_manifest': True,
                'length_filter_applied': False,
                'purpose': 'Historical teacher-forced training diagnostic only; no task-level validation.'}}
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: summary[key] for key in ('output_directory', 'kept_train', 'excluded_train',
                                                   'original_train_thresholds', 'val')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
