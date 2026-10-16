#!/usr/bin/env python3
"""Recover actual final Pivot episodes, then supplement the frozen Horizon prefix."""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pyarrow.parquet as pq
from sklearn.feature_extraction.text import TfidfVectorizer

from audit_terminal_horizon_complete_history import initialize, measure, dist
from candidate_selection import normalized_text
from expand_terminal_sft import clean_messages, read_rows, signature


def instruction(messages):
    return messages[0]['content'].split('Task Description:\n', 1)[-1].rsplit('\n\nCurrent terminal state:\n', 1)[0].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--include-fp8', action='store_true', help='Include the official GLM-5.1-FP8 teacher variant.')
    args = parser.parse_args()
    root = args.root
    base = root / 'artifacts/data/candidates/nemotron_terminal_pivot_20261016'
    horizon = root / 'artifacts/data/candidates/new_terminal_horizon_20261016'
    old = root / 'artifacts/data/candidates/terminal_sft_expanded_20261016'
    out = root / 'artifacts/data/candidates/terminal_sft_2k_20261016'
    out.mkdir(parents=True, exist_ok=True)
    finals, actions, starts, totals, uid_tasks = {}, defaultdict(dict), {}, {}, {}
    metadata_final_rows = 0
    source_rows = 0
    for path in sorted((base / 'raw').glob('*.parquet')):
        for batch in pq.ParquetFile(path).iter_batches(batch_size=64):
            for row in batch.to_pylist():
                source_rows += 1
                meta = row['metadata']
                assert meta['teacher_model'] in ('zai-org/GLM-5.1', 'zai-org/GLM-5.1-FP8') and meta['harness'] == 'terminus_2'
                uid = meta['source_trajectory_uid']
                turn, total = meta['pivot_agent_turn_index'], meta['total_source_agent_turns']
                assert uid not in totals or totals[uid] == total
                assert uid not in uid_tasks or uid_tasks[uid] == row['task_name']
                totals[uid] = total
                uid_tasks[uid] = row['task_name']
                prompt = row['responses_create_params']['input']
                starts.setdefault(uid, prompt[0])
                assert starts[uid] == prompt[0]
                actions[uid][turn] = row['expected_answer']
                metadata_final_rows += turn == total - 1
                if uid not in finals or turn > finals[uid]['metadata']['pivot_agent_turn_index']:
                    finals[uid] = row
    assert source_rows == 31111
    print(json.dumps({'decision_points': source_rows, 'unique_trajectories': len(totals),
                      'metadata_last_source_turn_released': metadata_final_rows,
                      'last_published_action_complete': sum(bool(json.loads(r['expected_answer']).get('task_complete')) for r in finals.values())}), flush=True)
    envs = read_rows(horizon / 'environment_metadata.jsonl')
    val_ids = {task for row in read_rows(horizon / 'proportional_candidates/val_tasks.provisional.jsonl')
               for task in row['family_task_ids']}
    formal = [{'task_id': path.parent.name, 'instruction': path.read_text()}
              for path in sorted((root / 'artifacts/benchmarks/terminal-bench-2').glob('*/instruction.md'))]
    assert len(formal) == 89
    task_inputs = {}
    for uid, row in finals.items():
        text = instruction(row['responses_create_params']['input'])
        task_inputs[uid] = text
    task_names = sorted(task_inputs)
    protected = [row for row in envs if row['task_id'] in val_ids] + formal
    corpus = [task_inputs[task] for task in task_names] + [row['instruction'] for row in envs + formal]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2,
                                 max_df=.9, stop_words='english', dtype=np.float32)
    vectorizer.fit(corpus)
    similarities = (vectorizer.transform([task_inputs[t] for t in task_names]) @
                    vectorizer.transform([r['instruction'] for r in protected]).T).toarray()
    exact_protected = {normalized_text(row['instruction']): row['task_id'] for row in protected}
    task_holds, review = {}, []
    for index, uid in enumerate(task_names):
        task = uid_tasks[uid]
        closest = int(np.argmax(similarities[index]))
        score = float(similarities[index, closest])
        exact = exact_protected.get(normalized_text(task_inputs[uid]))
        if exact or task in val_ids or task in {r['task_id'] for r in formal} or score >= .35:
            task_holds[task] = 'protected_task_exact_or_near_match'
            review.append({'task_name': task, 'source_trajectory_uid': uid,
                           'protected_task_id': exact or protected[closest]['task_id'],
                           'tfidf_similarity': score, 'exact_normalized_instruction': bool(exact)})
    (base / 'protected_task_holds.json').write_text(json.dumps(review, indent=2) + '\n')
    parser_file = root / 'artifacts/benchmarks/harbor/src/harbor/agents/terminus_2/terminus_json_plain_parser.py'
    spec = importlib.util.spec_from_file_location('pivot_native_parser', parser_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    native_parser = module.TerminusJSONPlainParser()
    initialize(root)
    reasons = Counter()
    post_completion_execution_uids = []
    for uid, published in actions.items():
        complete = [i for i, action in published.items() if json.loads(action).get('task_complete')]
        if complete and any(i > max(complete) and any(c.get('keystrokes', '').strip() for c in json.loads(action).get('commands', []))
                            for i, action in published.items()):
            post_completion_execution_uids.append(uid)
    metrics_path = base / 'episode_lengths.jsonl'
    metrics = {r['source_trajectory_uid']: r for r in read_rows(metrics_path)} if metrics_path.exists() else {}
    qualified = []
    for number, (uid, row) in enumerate(sorted(finals.items())):
        task, meta = row['task_name'], row['metadata']
        raw = row['responses_create_params']['input'] + [{'role': 'assistant', 'content': row['expected_answer']}]
        reason = task_holds.get(task)
        total = meta['total_source_agent_turns']
        completed_turns = meta['pivot_agent_turn_index'] + 1
        if not json.loads(row['expected_answer']).get('task_complete'):
            reasons['last_published_action_not_complete'] += 1
            continue
        if len(raw) != 2 * completed_turns or any(m['role'] != ('user' if i % 2 == 0 else 'assistant') for i, m in enumerate(raw)):
            reason = 'history_turn_count_or_role_mismatch'
        elif any(raw[2 * turn + 1]['content'] != action for turn, action in actions[uid].items()):
            reason = 'released_action_history_inconsistent'
        elif 'Task Description:\n' not in raw[0]['content'] or 'Current terminal state:\n' not in raw[0]['content']:
            reason = 'missing_initial_task_or_terminal_state'
        if reason:
            reasons[reason] += 1
            continue
        try:
            messages = clean_messages(raw)
        except AttributeError:
            reasons['malformed_think'] += 1
            continue
        parsed = [native_parser.parse_response(m['content']) for m in messages if m['role'] == 'assistant']
        if any(p.error for p in parsed): reason = 'native_parse_error'
        elif not parsed[-1].is_task_complete: reason = 'last_published_action_not_complete'
        if reason:
            reasons[reason] += 1
            continue
        if uid not in metrics:
            metric = measure(number, messages)
            metric['source_trajectory_uid'] = uid
            metrics[uid] = metric
            with metrics_path.open('a') as stream: stream.write(json.dumps(metric) + '\n')
        metric = metrics[uid]
        if metric['full_sequence_tokens'] > 65536: reason = 'complete_sequence_over64k'
        elif metric['assistant_outputs_over8192']: reason = 'assistant_reply_over8k'
        elif metric['strict_json_errors']: reason = 'strict_json_error'
        elif metric['residual_think_tag_messages']: reason = 'residual_think_tags'
        if reason:
            reasons[reason] += 1
            continue
        qualified.append({'uid': uid, 'task': task, 'messages': messages, 'metric': metric,
                          'teacher': meta['teacher_model'],
                          'total_source_agent_turns': total,
                          'final_pivot_index': meta['pivot_agent_turn_index'],
                          'unreleased_tail_turn_count': total - completed_turns})
        reasons['qualified_before_content_dedup'] += 1
        if number % 100 == 0: print(json.dumps({'final_episodes_checked': number + 1, 'qualified': len(qualified)}), flush=True)
    original = read_rows(old / 'train.messages.jsonl')
    provenance = [r for r in read_rows(old / 'provenance.jsonl') if r['split'] == 'train']
    assert len(original) == len(provenance) == 1107
    horizon_exact = {normalized_text(row['instruction']): row['task_id'] for row in envs}
    horizon_task_families = {row['task_id']: row['family_key'] for row in provenance}
    seen = {signature(row['messages']) for row in original}
    by_task = defaultdict(list)
    for row in qualified:
        if row['teacher'] == 'zai-org/GLM-5.1-FP8' and not args.include_fp8: continue
        by_task[row['task']].append(row)
    for group in by_task.values(): group.sort(key=lambda r: (r['teacher'].endswith('-FP8'), r['uid']))
    selected, duplicates = [], 0
    depth = 0
    while len(selected) < 2000 - len(original):
        candidates = [by_task[task][depth] for task in sorted(by_task) if len(by_task[task]) > depth]
        if not candidates: break
        for row in candidates:
            key = signature(row['messages'])
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            selected.append(row)
            if len(selected) == 2000 - len(original): break
        depth += 1
    with (out / 'train.messages.jsonl').open('w') as stream:
        for row in original: stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        for row in selected:
            stream.write(json.dumps({'messages': row['messages'], 'tools': []}, ensure_ascii=False) + '\n')
            key = normalized_text(task_inputs[row['uid']])
            horizon_match = horizon_exact.get(key)
            provenance.append({'split': 'train', 'row_index': len(provenance), 'domain': 'terminal',
                               'source': 'nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1',
                               'source_revision': 'eaef26944643644c8a3dbbf361ce6128142f5976',
                               'source_trajectory_uid': row['uid'], 'task_id': 'atcb:' + row['task'],
                               'family_key': horizon_task_families.get(horizon_match, 'atcb:' + row['task']),
                               'horizon_exact_instruction_task_id': horizon_match,
                               'category': 'unclassified', 'teacher': row['teacher'], 'harness': 'Terminus2 v2.0.0 / Harbor (publisher)',
                               'teacher_precision_variant': 'FP8' if row['teacher'].endswith('-FP8') else 'unsuffixed; serving precision not specified in source',
                               'source_quality': 'publisher_automated_verifier_passed_source_trajectory',
                               'success_verified_by_publisher': True, 'native_environment_validated_locally': False,
                               'full_sequence_tokens': row['metric']['full_sequence_tokens'],
                               'assistant_outputs_over8192': 0, 'final_task_complete_proxy': True,
                               'source_total_agent_turns': row['total_source_agent_turns'],
                               'last_published_completion_pivot_index': row['final_pivot_index'],
                               'unreleased_tail_turn_count': row['unreleased_tail_turn_count'],
                               'completion_semantics': 'Complete history through last published task_complete action; publisher filters post-completion confirmations.',
                               'released_action_history_consistent': True,
                               'training_window_status': 'complete_initial_to_last_published_completion; no_truncation_or_independent_later_windows'})
    shutil.copyfile(old / 'val.messages.jsonl', out / 'val.messages.jsonl')
    assert (old / 'val.messages.jsonl').read_bytes() == (out / 'val.messages.jsonl').read_bytes()
    training = list(provenance)
    provenance.extend(r for r in read_rows(old / 'provenance.jsonl') if r['split'] == 'val')
    with (out / 'provenance.jsonl').open('w') as stream:
        for row in provenance: stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    summary = {'target_train_episodes': 2000, 'train_episodes': len(training), 'val_episodes': 42,
               'horizon_prefix_episodes': 1107, 'pivot_added_episodes': len(selected),
               'pivot_added_unique_task_names': len({r['task'] for r in selected}),
               'train_unique_source_task_ids': len({r['task_id'] for r in training}),
               'train_unique_family_keys': len({r['family_key'] for r in training}),
               'gap_to_2000': max(0, 2000 - len(training)),
               'full_sequence_tokens': dist([r['full_sequence_tokens'] for r in training]),
               'pivot_source_decision_points': source_rows, 'pivot_source_trajectory_uids': len(totals),
               'pivot_source_task_names': len(set(uid_tasks.values())),
               'metadata_last_source_turn_released': metadata_final_rows,
               'last_published_action_complete': sum(bool(json.loads(r['expected_answer']).get('task_complete')) for r in finals.values()),
               'uids_with_nonempty_published_action_after_last_completion': len(post_completion_execution_uids),
               'selected_unreleased_tail_turn_count_distribution': dict(Counter(r['unreleased_tail_turn_count'] for r in selected)),
               'completion_semantics': 'Use highest released point only when task_complete=true, preserving its entire initial-to-completion history. Publisher filters post-completion confirmations; unreleased tail contents are unavailable.',
               'pivot_trajectory_waterfall': dict(reasons), 'pivot_qualified_episodes': len(qualified),
               'pivot_qualified_unique_tasks': len({r['task'] for r in qualified}),
               'pivot_qualified_teacher_counts': dict(Counter(r['teacher'] for r in qualified)),
               'pivot_selected_teacher_counts': dict(Counter(r['teacher'] for r in selected)),
               'fp8_teacher_enabled': args.include_fp8,
               'exact_content_duplicates_encountered_while_selecting': duplicates,
               'protected_task_holds': len(task_holds), 'protected_tfidf_threshold': .35,
               'formal_task_inputs_checked': len(formal), 'frozen_task_val_inputs_checked': len(val_ids),
               'val42_byte_identical': True, 'frozen_task_val99_unchanged': True,
               'context_limit': 65536, 'assistant_output_limit': 8192,
               'selection': 'Keep all Horizon1107; round-robin real distinct Pivot trajectories across publisher seed-task groups; prefer original-precision teacher within task.',
               'pivot_category_annotation': 'Not inferred; unclassified. Category distribution is an open limitation.',
               'source_success_limit': 'NVIDIA publisher verifier-pass claim; no local task replay.',
               'source_licenses': {'shunzou05/TerminalHorizon-3K': 'Apache-2.0',
                                   'nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1': 'CC-BY-4.0, NVIDIA Corporation'},
               'output': str(out)}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (base / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
