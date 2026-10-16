#!/usr/bin/env python3
"""Export all complete, non-val TerminalHorizon episodes within the fixed limits."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil

from audit_terminal_horizon_complete_history import initialize, measure, dist


def read_rows(path):
    return [json.loads(line) for line in path.open()]


def clean_messages(raw):
    messages = []
    for item in raw:
        content = item['content']
        if item['role'] == 'assistant' and content.lstrip().startswith('<think>'):
            content = content[re.match(r'\A\s*<think>.*?</think>\s*', content, re.S).end():]
        messages.append({'role': item['role'], 'content': content})
    return messages


def signature(messages):
    return tuple((item['role'], item['content']) for item in messages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    base = args.root / 'artifacts/data/candidates/new_terminal_horizon_20261016'
    old = args.root / 'artifacts/data/candidates/terminal_sft_20261016'
    out = args.root / 'artifacts/data/candidates/terminal_sft_expanded_20261016'
    out.mkdir(parents=True, exist_ok=True)
    checks = {row['row_index']: row for row in read_rows(base / 'inspection/row_index.jsonl')}
    tasks = {row['task_id']: row for row in read_rows(base / 'environment_metadata.jsonl')}
    labels = {row['id']: row for row in read_rows(base / 'annotations/labels.jsonl')}
    old_pool = {row['task_id'] for row in read_rows(base / 'proportional_candidates/train_pool.provisional.jsonl')}
    val = read_rows(base / 'proportional_candidates/val_tasks.provisional.jsonl')
    val_tasks = {task for row in val for task in row['family_task_ids']}
    near_val = {row['task_id'] for row in read_rows(base / 'proportional_candidates/near_val_train_holds.jsonl')}
    metrics = {row['row_index']: row for row in read_rows(base / 'complete_history_64k_audit/trace_length_census.jsonl')}
    additions = out / 'additional_length_census.jsonl'
    if additions.exists():
        metrics.update({row['row_index']: row for row in read_rows(additions)})
    old_provenance = read_rows(old / 'provenance.jsonl')
    provenance = [row for row in old_provenance if row['split'] == 'train']
    originals = read_rows(old / 'train.messages.jsonl')
    assert len(originals) == len(provenance) == 374
    selected = {row['source_row_index'] for row in provenance}
    seen = {signature(row['messages']) for row in originals}
    reasons, flags = Counter(), Counter()
    measured = 0
    initialized = False

    def native_reason(check):
        ids = check['task_ids']
        if len(ids) != 1 or ids[0] not in tasks: return 'unmatched_or_ambiguous_environment'
        if ids[0] in val_tasks: return 'frozen_val_family'
        if not check['role_chain_valid']: return 'invalid_role_chain'
        if check['malformed_think_turns']: return 'malformed_think'
        if check['native_parser_error_turns']: return 'native_parse_error'
        if not check['final_task_complete_proxy']: return 'final_task_complete_false'
        if check['formal_exact_hits']: return 'formal_task_exact_match'
        return None

    with (out / 'train.messages.jsonl').open('w') as train, additions.open('a') as cache:
        for row in originals:
            train.write(json.dumps(row, ensure_ascii=False) + '\n')
        for index, line in enumerate((base / 'traces/data/TerminalHorizon-3K-SFT.jsonl').open()):
            check = checks[index]
            for name, value in [('native_parse_error', check['native_parser_error_turns']),
                                ('malformed_think', check['malformed_think_turns']),
                                ('invalid_role_chain', not check['role_chain_valid']),
                                ('final_task_complete_false', not check['final_task_complete_proxy']),
                                ('formal_task_exact_match', check['formal_exact_hits'])]:
                if value: flags[name] += 1
            reason = native_reason(check)
            if reason:
                reasons[reason] += 1
                continue
            task_id = check['task_ids'][0]
            messages = None
            if index not in metrics:
                if not initialized:
                    initialize(args.root)
                    initialized = True
                messages = clean_messages(json.loads(line)['conversations'])
                metrics[index] = measure(index, messages)
                cache.write(json.dumps(metrics[index]) + '\n')
                cache.flush()
                measured += 1
                if measured % 10 == 0: print(json.dumps({'new_length_rows': measured}), flush=True)
            metric = metrics[index]
            if metric['full_sequence_tokens'] > 65536: flags['complete_sequence_over64k'] += 1
            if metric['assistant_outputs_over8192']: flags['assistant_reply_over8k'] += 1
            if task_id in near_val: reason = 'conservative_near_val_hold'
            elif metric['full_sequence_tokens'] > 65536: reason = 'complete_sequence_over64k'
            elif metric['assistant_outputs_over8192']: reason = 'assistant_reply_over8k'
            elif metric['strict_json_errors']: reason = 'strict_json_error'
            elif metric['residual_think_tag_messages']: reason = 'residual_think_tags'
            if reason:
                reasons[reason] += 1
                continue
            if index in selected:
                reasons['selected'] += 1
                continue
            if messages is None: messages = clean_messages(json.loads(line)['conversations'])
            key = signature(messages)
            if key in seen:
                reasons['exact_duplicate_cleaned_messages'] += 1
                continue
            seen.add(key)
            provenance.append({'split': 'train', 'row_index': len(provenance),
                               'id': 'terminal_horizon:row:%d' % index, 'domain': 'terminal',
                               'task_id': task_id, 'family_key': 'horizon-family:' + task_id,
                               'category': labels[task_id]['category'],
                               'category_confidence': labels[task_id]['confidence'],
                               'source_row_index': index, 'source': 'shunzou05/TerminalHorizon-3K',
                               'source_revision': '45f1e98e317d3639437f0eb02f4e8bc5825732f3',
                               'teacher': 'DeepSeek-V4-Pro-0813 (publisher declared)',
                               'harness': 'Terminus2 (native JSON protocol compatible)',
                               'source_quality': 'publisher_process_filtered; native_parse_valid; final_completion_proxy_true',
                               'success_verified': False, 'native_environment_validated_locally': False,
                               'full_sequence_tokens': metric['full_sequence_tokens'],
                               'assistant_outputs_over8192': 0, 'final_task_complete_proxy': True,
                               'training_window_status': 'complete_full_history; no_truncation_or_independent_later_windows',
                               'previous_train_pool_member': task_id in old_pool})
            train.write(json.dumps({'messages': messages, 'tools': []}, ensure_ascii=False) + '\n')
            selected.add(index)
            reasons['selected'] += 1
    assert sum(reasons.values()) == len(checks)
    assert len(provenance) == reasons['selected']
    assert not ({row['task_id'] for row in provenance} & val_tasks)
    shutil.copyfile(old / 'val.messages.jsonl', out / 'val.messages.jsonl')
    assert (old / 'val.messages.jsonl').read_bytes() == (out / 'val.messages.jsonl').read_bytes()
    provenance.extend(row for row in old_provenance if row['split'] == 'val')
    with (out / 'provenance.jsonl').open('w') as stream:
        for row in provenance: stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    training = [row for row in provenance if row['split'] == 'train']
    summary = {'source_episodes': len(checks), 'source_task_environments': len(tasks),
               'target_train_episodes': 2000, 'train_episodes': len(training), 'val_episodes': 42,
               'train_unique_tasks': len({row['task_id'] for row in training}),
               'train_unique_families': len({row['family_key'] for row in training}),
               'gap_to_2000': max(0, 2000 - len(training)),
               'full_sequence_tokens': dist([row['full_sequence_tokens'] for row in training]),
               'train_category_counts': dict(Counter(row['category'] for row in training)),
               'train_category_confidence_counts': dict(Counter(labels[row['task_id']]['confidence'] for row in training)),
               'formerly_outside_train_pool_selected_episodes': sum(row['task_id'] not in old_pool for row in training),
               'formerly_outside_train_pool_selected_tasks': len({row['task_id'] for row in training if row['task_id'] not in old_pool}),
               'mutually_exclusive_source_waterfall': dict(reasons), 'overlapping_flags': dict(flags),
               'additional_length_rows_measured_this_run': measured,
               'original_374_preserved_as_prefix': True, 'val42_byte_identical': True,
               'frozen_task_val_count': len(val), 'val_task_overlap': 0,
               'context_limit': 65536, 'assistant_output_limit': 8192,
               'truncation': False, 'exact_cleaned_message_deduplication': True,
               'category_low_confidence_is_not_quality_rejection': True,
               'conservative_near_val_hold_task_ids': sorted(near_val),
               'quality_limit': 'Publisher process review, native parser compatibility and final task_complete proxy; no independent per-row verifier reward.',
               'output': str(out)}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
