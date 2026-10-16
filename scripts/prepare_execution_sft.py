#!/usr/bin/env python3
"""Select complete Terminal episodes from cached lengths, then append all SAB references."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


def read_jsonl(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def write_jsonl(path, rows):
    with path.open('w') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    base = args.root / 'artifacts/data/candidates/new_terminal_horizon_20261016'
    sab = args.root / 'artifacts/data/candidates/scienceagentbench_verified_9c6e96c9/swift_ready'
    out = args.root / 'artifacts/data/candidates/execution_sft_20261016'
    out.mkdir(parents=True, exist_ok=True)

    original = read_jsonl(base / 'messages_v3/train.messages.jsonl')
    old_val = read_jsonl(base / 'messages_v3/val.messages.jsonl')
    pool = {row['task_id']: row for row in read_jsonl(base / 'proportional_candidates/train_pool.provisional.jsonl')}
    val_families = {row['family_key'] for row in read_jsonl(base / 'proportional_candidates/val_tasks.provisional.jsonl')}
    supply = read_jsonl(base / 'complete_history_64k_audit/task_supply.jsonl')
    census = {row['row_index']: row for row in read_jsonl(base / 'complete_history_64k_audit/trace_length_census.jsonl')}
    valid = {}
    for task in supply:
        assert task['task_id'] in pool and task['family_key'] not in val_families
        candidates = [row for row in task['valid_source_episodes']
                      if row['full_sequence_tokens'] <= 65536 and row['assistant_outputs_over8192'] == 0
                      and row['strict_json_errors'] == 0 and row['residual_think_tag_messages'] == 0]
        if candidates:
            valid[task['task_id']] = candidates

    quotas = Counter(row['category'] for row in original)
    selected, replacements, unresolved = [], [], defaultdict(list)
    selected_families = set()
    for old in original:
        choices = valid.get(old['task_id'], [])
        if not choices:
            unresolved[old['category']].append(old)
            continue
        chosen = next((row for row in choices if row['row_index'] == old['source_row_index']), None)
        reason = 'keep_original_episode'
        if chosen is None:
            chosen = max(choices, key=lambda row: (row['full_sequence_tokens'], -row['row_index']))
            reason = 'same_task_alternate_complete_episode'
        selected.append(chosen)
        selected_families.add(pool[old['task_id']]['family_key'])
        replacements.append({'original_task_id': old['task_id'], 'selected_task_id': old['task_id'],
                             'category': old['category'], 'source_row_index': chosen['row_index'], 'reason': reason})

    for category, slots in unresolved.items():
        spares = sorted((pool[task_id] for task_id in valid if pool[task_id]['category'] == category
                         and pool[task_id]['family_key'] not in selected_families), key=lambda row: row['family_rank'])
        for slot, spare in zip(slots, spares):
            choices = valid[spare['task_id']]
            chosen = max(choices, key=lambda row: (row['full_sequence_tokens'], -row['row_index']))
            selected.append(chosen)
            selected_families.add(spare['family_key'])
            replacements.append({'original_task_id': slot['task_id'], 'selected_task_id': spare['task_id'],
                                 'category': category, 'source_row_index': chosen['row_index'],
                                 'reason': 'same_category_train_spare_complete_episode'})

    selected_by_index = {row['row_index']: row for row in selected}
    assert len(selected_by_index) == len(selected) == len(selected_families)
    counts = Counter(pool[row['task_id']]['category'] for row in selected)
    assert all(counts[category] <= quota for category, quota in quotas.items())
    assert not selected_families & val_families

    terminal_train = []
    source = base / 'traces/data/TerminalHorizon-3K-SFT.jsonl'
    for index, line in enumerate(source.open()):
        if index not in selected_by_index:
            continue
        chosen = selected_by_index[index]
        task = pool[chosen['task_id']]
        raw = json.loads(line)['conversations']
        messages = []
        for message in raw:
            content = message['content']
            if message['role'] == 'assistant' and content.lstrip().startswith('<think>'):
                match = re.match(r'\A\s*<think>.*?</think>\s*', content, re.S)
                assert match
                content = content[match.end():]
            if message['role'] == 'assistant':
                json.loads(content)
                assert '<think>' not in content and '</think>' not in content
            messages.append({'role': message['role'], 'content': content})
        assert [m for m in raw if m['role'] == 'user'] == [m for m in messages if m['role'] == 'user']
        terminal_train.append({
            'id': 'terminal_horizon:' + task['task_id'], 'domain': 'terminal', 'messages': messages,
            'tools': [], 'task_id': task['task_id'], 'family_key': task['family_key'],
            'category': task['category'], 'source_row_index': index,
            'source': 'shunzou05/TerminalHorizon-3K',
            'source_revision': '45f1e98e317d3639437f0eb02f4e8bc5825732f3',
            'teacher': 'DeepSeek-V4-Pro-0813 (publisher declared)',
            'source_quality': 'publisher_process_filtered; native_parse_valid; final_completion_proxy_true',
            'success_verified': False, 'native_environment_validated_locally': False,
            'harness': 'Terminus2 (publisher declared; frozen native JSON protocol compatible)',
            'full_sequence_tokens': chosen['full_sequence_tokens'],
            'assistant_outputs_over8192': 0, 'final_task_complete_proxy': True,
            'training_window_status': 'complete_full_history; no_truncation_or_independent_later_windows',
        })
    assert len(terminal_train) == len(selected)

    val_lengths = {row['source_row_index']: row for row in read_jsonl(base / 'messages_v3/length_rows.jsonl')
                   if row['split'] == 'val'}
    terminal_val, val_dropped = [], []
    for row in old_val:
        length = val_lengths[row['source_row_index']]
        if length['full_sequence_tokens'] > 65536 or max(length['assistant_message_lengths']) > 8192:
            val_dropped.append({'task_id': row['task_id'], 'source_row_index': row['source_row_index'],
                                'full_sequence_tokens': length['full_sequence_tokens'],
                                'max_assistant_tokens': max(length['assistant_message_lengths'])})
            continue
        row = dict(row)
        row['full_sequence_tokens'] = length['full_sequence_tokens']
        row['assistant_outputs_over8192'] = 0
        row['training_window_status'] = 'complete_full_history; no_truncation_or_independent_later_windows'
        terminal_val.append(row)

    sab_rows = {split: read_jsonl(sab / (split + '.messages.jsonl')) for split in ('train', 'val')}
    assert len(sab_rows['train']) == 82 and len(sab_rows['val']) == 20
    combined = {'train': terminal_train + sab_rows['train'], 'val': terminal_val + sab_rows['val']}
    for split, rows in combined.items():
        write_jsonl(out / (split + '.messages.jsonl'), rows)
    write_jsonl(out / 'terminal_selection.provenance.jsonl', replacements)
    write_jsonl(out / 'terminal_val_excluded_by_length.jsonl', val_dropped)
    sab_manifest = json.load((sab / 'candidate_manifest.json').open())
    sab_provenance = []
    for split in ('train', 'val'):
        records = [row for row in sab_manifest['records'] if row['split'] == split]
        assert len(records) == len(sab_rows[split])
        for offset, record in enumerate(records):
            sab_provenance.append({'combined_split': split, 'combined_row_index':
                                   (len(terminal_train) if split == 'train' else len(terminal_val)) + offset,
                                   'sab_split_row_index': offset, **record})
    write_jsonl(out / 'sab.provenance.jsonl', sab_provenance)
    provenance = {
        'terminal_source': str(source), 'cached_train_lengths': str(base / 'complete_history_64k_audit/trace_length_census.jsonl'),
        'cached_train_supply': str(base / 'complete_history_64k_audit/task_supply.jsonl'),
        'cached_val_lengths': str(base / 'messages_v3/length_rows.jsonl'),
        'frozen_val99_manifest': str(base / 'proportional_candidates/val_tasks.provisional.jsonl'),
        'SAB_source': str(sab), 'SAB_manifest': str(sab / 'candidate_manifest.json'),
        'terminal_train_selection': str(out / 'terminal_selection.provenance.jsonl'),
        'sab_combined_row_mapping': str(out / 'sab.provenance.jsonl'),
        'source_hashes_recomputed': False, 'new_task_execution': False, 'API_calls': 0,
        'original_messages_v3_and_val99_modified': False,
    }
    (out / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    terminal_tokens = {split: sum(row['full_sequence_tokens'] for row in rows)
                       for split, rows in [('train', terminal_train), ('val', terminal_val)]}
    summary = {
        'counts': {'terminal_train': len(terminal_train), 'terminal_val': len(terminal_val),
                   'sab_train': len(sab_rows['train']), 'sab_val': len(sab_rows['val']),
                   'train': len(combined['train']), 'val': len(combined['val'])},
        'terminal_original_train_counts': dict(quotas), 'terminal_selected_train_counts': dict(counts),
        'terminal_category_gaps': {category: quotas[category] - counts[category] for category in quotas},
        'terminal_replacement_counts': dict(Counter(row['reason'] for row in replacements)),
        'terminal_cached_full_sequence_tokens': terminal_tokens,
        'terminal_max_full_sequence_tokens': max(row['full_sequence_tokens'] for row in terminal_train + terminal_val),
        'terminal_context_limit': 65536, 'terminal_max_assistant_output': 8192,
        'terminal_family_train_val_overlap': 0, 'frozen_terminal_task_val_count': len(val_families),
        'terminal_val_excluded_by_length': len(val_dropped),
        'terminal_quality': 'Complete source episodes, native parse valid and completion proxy true; publisher process filtering; independent grader success not verified.',
        'terminal_history_policy': 'Entire cleaned conversation retained; only leading balanced hidden think removed; visible JSON analysis/plan/commands and all user observations retained.',
        'terminal_replacement_policy': 'Keep original fitting episode; then same-task alternate; then same-category spare by existing family_rank. Alternate/spare episode chosen closest to 64K from below to avoid unnecessary shortest-episode bias.',
        'terminal_val_scope': 'Held-out teacher trace loss only; native task-success val readiness is separate.',
        'SAB_policy': 'Keep all authorized publisher-verified human gold, 82 train / 20 repo-held-out val; no environment, dependency, image or GPU filtering.',
        'SAB_local_runtime_passed_ids': sab_manifest.get('local_passed_ids', []),
        'SAB_length_filter_applied': False, 'SAB_canary_and_licenses_preserved': True,
        'SAB_note': 'Publisher verification is distinct from local runtime readiness; native checker reruns are not required for training export.',
        'loss_contract': 'Assistant content only supervised; system/user/observations masked. No fabricated tool traces or hidden reasoning.',
        'files': {split: {'path': str(out / (split + '.messages.jsonl')),
                          'bytes': (out / (split + '.messages.jsonl')).stat().st_size} for split in combined},
        'provenance': str(out / 'provenance.json'),
    }
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
