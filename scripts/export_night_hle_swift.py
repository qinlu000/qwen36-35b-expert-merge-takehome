"""Export bounded, fully audited HLE SFT messages and independent proxy dev.

Validation loss uses original references, without invented teacher explanations.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer

from candidate_selection import text_hash


def read_rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def write_rows(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    return {'path': str(path), 'rows': len(rows), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo
    base = root / 'artifacts/data/candidates/night_hle_20261016'
    out = base / 'swift_ready'
    out.mkdir(exist_ok=True)
    training = read_rows(base / 'train.cleaned_candidates.jsonl')
    validation = read_rows(base / 'proxy_val_100.jsonl')
    materialization = json.loads((base / 'materialization_summary.json').read_text())
    generation = json.loads((base / 'teacher_generation_summary.json').read_text())
    assert len(training) == 500 and len(validation) == 100
    assert generation['stop_reason'] == 'quotas_satisfied' and sum(generation['accepted'].values()) == 296
    assert not materialization['rejection_counts']
    assert all(r['train_readiness'] != 'candidate_needs_answer_verification' for r in training)
    train_hash = {text_hash(r['messages'][0]['content']) for r in training}
    val_hash = {text_hash(r['prompt']) for r in validation}
    assert not train_hash & val_hash
    train_messages, provenance = [], []
    for index, row in enumerate(training):
        messages = row['messages']
        assert [m['role'] for m in messages] == ['user', 'assistant']
        assert all(m['content'].strip() for m in messages)
        assert not any(m.get('tool_calls') or m.get('reasoning_content') or m.get('reason_content') for m in messages)
        messages = [{'role': m['role'], 'content': m['content']} for m in messages]
        assert all('<think>' not in m['content'] and '</think>' not in m['content'] for m in messages)
        train_messages.append({'messages': messages})
        provenance.append({'row': index, 'family_key': row['id'], **row['metadata'],
                           'complete_sequence_tokens': row['complete_sequence_tokens'],
                           'max_assistant_body_tokens_proxy': row['max_assistant_body_tokens_proxy'],
                           'answer_evidence': row['metadata']['answer_evidence']})
    val_messages, val_tasks, val_provenance = [], [], []
    for index, row in enumerate(validation):
        assert isinstance(row['gold_answer'], str) and row['gold_answer'].strip()
        val_messages.append({'messages': [{'role': 'user', 'content': row['prompt']},
                                          {'role': 'assistant', 'content': row['gold_answer']}]})
        val_tasks.append({'id': row['family_key'], 'question': row['prompt'],
                          'answer': row['gold_answer'], 'answer_type': row['reference_type'],
                          'category': row['hle_category'], 'image': '', 'image_path': ''})
        val_provenance.append({'row': index, **{k: v for k, v in row.items() if k not in {
            'messages', 'question', 'prompt', 'options', 'gold_answer', 'gold_option'}}})
    tokenizer = AutoTokenizer.from_pretrained(root / 'artifacts/models/base_metadata/' /
        '995ad96eacd98c81ed38be0c5b274b04031597b0', local_files_only=True, trust_remote_code=False)
    def sequence_tokens(messages):
        rendered = tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)
        return len(tokenizer.encode(rendered, add_special_tokens=False))
    export_train_lengths = [sequence_tokens(r['messages']) for r in train_messages]
    assert export_train_lengths == [r['complete_sequence_tokens'] for r in training]
    val_lengths = [sequence_tokens(r['messages']) for r in val_messages]
    files = {
        'train': write_rows(out / 'train.messages.jsonl', train_messages),
        'train_provenance': write_rows(out / 'train.provenance.jsonl', provenance),
        'val_loss': write_rows(out / 'val.messages.jsonl', val_messages),
        'val_tasks': write_rows(out / 'val.tasks.jsonl', val_tasks),
        'val_provenance': write_rows(out / 'val.provenance.jsonl', val_provenance)}
    summary = {'data_ready': True, 'files': files,
               'train_categories': dict(Counter(r['metadata']['hle_category'] for r in training)),
               'train_sources': dict(Counter(r['metadata']['source'] for r in training)),
               'train_teacher_models': dict(Counter(r['metadata'].get('teacher_model') or
                    r['metadata'].get('teacher') for r in training)),
               'training_role_pattern': ['user', 'assistant'],
               'training_hidden_reasoning_fields': 0, 'training_think_tags_in_messages': 0,
               'train_lengths': materialization['complete_sequence_tokens'],
               'maximum_assistant_body_tokens_proxy': materialization['max_assistant_body_tokens_proxy'],
               'val_lengths': {'sum': sum(val_lengths), 'max': max(val_lengths)},
               'train_val_exact_prompt_overlap': 0,
               'formal_and_val_13gram_check': 'passed in materialization_summary.json',
               'swift_loss_mask_validated': False,
               'swift_loss_mask_required': 'All user tokens masked; supervise only assistant answer. Verify with actual Swift template before GPU training.',
               'validation_reference_policy': 'Original expected_answer or option letter only; no fabricated explanation or teacher call.',
               'science_publisher_only_135_policy': 'Held separately; replaced by fresh independently-gold-matched teacher answers.',
               'branch_api_budget_cny_conservative': generation['conservative_budget_cny'],
               'training_started_by_this_script': False,
               'limitations': ['100-task dev is a coarse-category proxy: no images, 59 MCQ, different difficulty and Other subdomains.',
                               'Teacher gold match verifies the selected answer, not every explanatory claim.',
                               'Question/13-gram grouping does not guarantee semantic or source-exam-family independence.',
                               'Sequence token counts are fixed-template counts, not Swift processed training token counts.']}
    (out / 'ready_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
