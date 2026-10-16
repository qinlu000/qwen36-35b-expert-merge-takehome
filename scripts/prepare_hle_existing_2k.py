"""Combine existing strong-teacher answers; never generate or truncate answers."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import shutil

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['OMP_NUM_THREADS'] = '2'

from transformers import AutoTokenizer

from candidate_selection import normalized_text, proportional_quotas
from expand_hle_sft_2k import clean_messages, lengths, MODEL_REV
from prepare_night_hle_proxy import COUNTS


def read(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def write(path, values):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--candidates', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.repo, args.output_dir
    old = root / 'artifacts/data/candidates/night_hle_20261016'
    expanded = old / 'expanded_2k'
    tokenizer = AutoTokenizer.from_pretrained(root / 'artifacts/models/base_metadata' / MODEL_REV,
        local_files_only=True, trust_remote_code=False)
    target = proportional_quotas(2000, COUNTS)
    seen, families, rejected = set(), set(), Counter()
    fixed, pool = [], defaultdict(list)
    val_questions = {normalized_text(row['question']) for row in read(old / 'proxy_val_100.jsonl')}

    def convert(row, origin):
        meta = dict(row.get('metadata') or row.get('source_meta') or {})
        for key in ('task_id', 'source_id', 'teacher', 'source_url', 'question', 'domain'):
            if key in row:
                meta[key] = row[key]
        if 'hle_category' in row:
            meta.update({key: value for key, value in row.items() if key not in {
                'messages', 'question', 'prompt', 'options', 'gold_answer', 'gold_option'}})
        domain = meta.get('hle_category') or row.get('domain')
        if domain not in target:
            rejected['unmapped_domain'] += 1
            return None
        messages = clean_messages(row['messages'])
        prompt = normalized_text(messages[0]['content'])
        question = normalized_text(row.get('question') or meta.get('question') or messages[0]['content'])
        family = meta.get('family_key') or meta.get('source_id') or row.get('source_id')
        if prompt in seen or question in seen or (family and family in families):
            rejected['duplicate_question_or_family'] += 1
            return None
        if question in val_questions:
            rejected['frozen_val_question_overlap'] += 1
            return None
        full, body = lengths(tokenizer, messages)
        if full > 65536 or body > 8192:
            rejected['complete_sequence_or_answer_limit'] += 1
            return None
        seen.update((prompt, question))
        if family:
            families.add(family)
        meta.update(hle_category=domain, selection_input=origin,
            hidden_reasoning_removed=meta.get('hidden_reasoning_removed', True),
            complete_sequence_tokens=full, assistant_tokens=body)
        return {'messages': messages, 'metadata': meta}

    for filename in ('math.ready.jsonl', 'new_teacher_accepted.jsonl'):
        for row in read(expanded / filename):
            item = convert(row, str((expanded / filename).relative_to(root)))
            assert item is not None, 'Previously prepared answer failed export: ' + filename
            fixed.append(item)
    assert len(fixed) == 1539
    for filename in args.candidates:
        for row in read(filename):
            item = convert(row, str(filename.relative_to(root)))
            if item:
                pool[item['metadata']['hle_category']].append(item)
    # Humanities final-answer supply is limited. Use the already separated,
    # publisher-referenced questions rather than inventing teacher explanations.
    # These are short-answer supervision, explicitly not reasoning trajectories.
    fixed_humanities = sum(item['metadata']['hle_category'] == 'Humanities/Social Science'
        for item in fixed)
    for row in read(expanded / 'teacher_reservoir.jsonl'):
        if len(pool['Humanities/Social Science']) >= target['Humanities/Social Science'] - fixed_humanities:
            break
        if row['hle_category'] != 'Humanities/Social Science':
            continue
        reference = {'messages': [{'role': 'user', 'content': row['prompt']},
            {'role': 'assistant', 'content': 'The answer is (' + row['gold_answer']
                + '): ' + row['gold_option']}],
            'metadata': dict(row, teacher='publisher_reference_not_model_generated',
                teacher_mode='not_applicable', answer_style='reference_short_answer',
                answer_evidence='publisher_reference_answer', hidden_reasoning_removed=False)}
        item = convert(reference, str((expanded / 'teacher_reservoir.jsonl').relative_to(root)))
        if item:
            pool['Humanities/Social Science'].append(item)
    supply = {key: len(value) for key, value in pool.items()}
    selected = list(fixed)
    counts = Counter(row['metadata']['hle_category'] for row in selected)
    for domain in target:
        wanted = max(0, target[domain] - counts[domain])
        chosen, pool[domain] = pool[domain][:wanted], pool[domain][wanted:]
        selected.extend(chosen)
        counts[domain] += len(chosen)
    initial_deficit = {key: target[key] - counts[key] for key in target if counts[key] < target[key]}
    assert not initial_deficit, initial_deficit
    assert len(selected) == 2000
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'train.messages.jsonl', [{'messages': row['messages']} for row in selected])
    write(out / 'train.provenance.jsonl', [dict(row['metadata'], row=i) for i, row in enumerate(selected)])
    for name in ('val.messages.jsonl', 'val.tasks.jsonl', 'val.provenance.jsonl'):
        shutil.copyfile(old / 'swift_ready' / name, out / name)
        assert (out / name).read_bytes() == (old / 'swift_ready' / name).read_bytes()
    full = [row['metadata']['complete_sequence_tokens'] for row in selected]
    body = [row['metadata']['assistant_tokens'] for row in selected]
    summary = {'data_ready': True, 'train_rows': len(selected), 'val_rows': 100,
        'categories': dict(counts), 'target_categories': target, 'quota_delta': {
            key: counts[key] - target[key] for key in target},
        'unavailable_strata_before_redistribution': initial_deficit,
        'candidate_supply_after_dedup_and_length_check': supply,
        'sources': dict(Counter(row['metadata'].get('source') or row['metadata'].get('dataset')
            or row['metadata']['selection_input'] for row in selected)),
        'teachers': dict(Counter(row['metadata'].get('teacher_model') or row['metadata'].get('teacher')
            or 'publisher_unspecified_effort' for row in selected)),
        'fixed_existing_math': 817, 'fixed_existing_accepted_high': 722,
        'reference_short_answer_rows': sum(row['metadata'].get('answer_style') == 'reference_short_answer'
            for row in selected),
        'new_api_calls': 0, 'validation_bytes_unchanged': True, 'truncated_samples': 0,
        'hidden_reasoning_fields_in_training': 0, 'rejections': dict(rejected),
        'full_sequence_tokens': {'sum': sum(full), 'max': max(full), 'mean': sum(full) / len(full)},
        'assistant_tokens': {'sum': sum(body), 'max': max(body)},
        'hard_sequence_limit': 65536, 'hard_assistant_limit': 8192,
        'limits': ['Academic domain proxy; difficulty and subject supply differ from HLE.',
            'Teacher mode and answer evidence are recorded per source; unknown effort is not relabeled High.',
            'Public source and question overlap exclusions do not prove semantic independence.']}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
