"""Prepare new-teacher QA candidates and a gold-reference HLE proxy dev.

The proxy matches eight coarse categories, not HLE difficulty or modalities.
Only public MMLU-Pro and new Math-v4/Science-v2 candidates are used.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import pyarrow.parquet as pq

from candidate_selection import family_partition, family_rank, normalized_text, proportional_quotas, text_hash


MMLU_REV = 'b189ec765aa7ed75c8acfea42df31fdae71f97be'
HLE_REV = '5a81a4c7271a2a2a312b9a690f0c2fde837e4c29'
COUNTS = {'Math': 1021, 'Biology/Medicine': 280, 'Computer Science/AI': 241,
          'Other': 233, 'Physics': 230, 'Humanities/Social Science': 219,
          'Chemistry': 165, 'Engineering': 111}
ALIASES = {'Mathematics': 'Math', 'Biology': 'Biology/Medicine'}
OTHER_SOURCES = {'ori_mmlu-miscellaneous', 'ori_mmlu-high_school_geography',
                 'ori_mmlu-formal_logic', 'ori_mmlu-logical_fallacies'}
HUM_SOURCES = {'history', 'law', 'philosophy', 'economics', 'psychology', 'business'}


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def write_rows(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))


def ngrams(text, n=13):
    words = re.findall(r'\w+', normalized_text(text))
    return {hashlib.sha256(' '.join(words[i:i+n]).encode()).hexdigest()
            for i in range(len(words) - n + 1)}


def category(row):
    label = row['category']
    direct = {'math': 'Math', 'physics': 'Physics', 'chemistry': 'Chemistry',
              'biology': 'Biology/Medicine', 'health': 'Biology/Medicine',
              'computer science': 'Computer Science/AI', 'engineering': 'Engineering'}
    if label in direct:
        return direct[label]
    if row['src'] in OTHER_SOURCES:
        return 'Other'
    if label in HUM_SOURCES:
        return 'Humanities/Social Science'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--replace-science-with-gold', action='store_true',
                        help='Hold publisher-only Science; use new teacher answers on referenced MMLU science tasks.')
    args = parser.parse_args()
    root = args.repo
    out = root / 'artifacts/data/candidates/night_hle_20261016'
    out.mkdir(parents=True, exist_ok=True)
    formal = pq.read_table(root / 'artifacts/benchmarks/hle' / HLE_REV /
                           'test-00000-of-00001.parquet', columns=['question']).to_pylist()
    formal_hashes = {text_hash(r['question']) for r in formal}
    formal_ngrams = set().union(*(ngrams(r['question']) for r in formal))
    source = root / 'artifacts/data/raw/mmlu_pro' / MMLU_REV
    source_rows = []
    for file in sorted(source.glob('*.parquet')):
        for row in pq.read_table(file).to_pylist():
            row['source_file'] = str(file.relative_to(root))
            source_rows.append(row)
    candidates, rejected, seen = [], Counter(), set()
    for row in source_rows:
        cat = category(row)
        if cat is None:
            rejected['unmapped_subject'] += 1
            continue
        prompt_hash = text_hash(row['question'])
        if prompt_hash in seen:
            rejected['duplicate_question_stem'] += 1
            continue
        seen.add(prompt_hash)
        if prompt_hash in formal_hashes or ngrams(row['question']) & formal_ngrams:
            rejected['formal_HLE_exact_or_13gram_overlap'] += 1
            continue
        if re.search(r'(?:following|above|below|given)\s+(?:figure|diagram|image|graph)|shown\s+in',
                     row['question'], re.I):
            rejected['potential_missing_visual_or_external_context'] += 1
            continue
        letter = row['answer'].strip()
        if not (0 <= row['answer_index'] < len(row['options']) and
                letter == chr(65 + row['answer_index'])):
            rejected['inconsistent_gold_index'] += 1
            continue
        family = 'qa:' + prompt_hash
        prompt = row['question'] + '\n\n' + '\n'.join(
            chr(65+i) + '. ' + option for i, option in enumerate(row['options']))
        candidates.append({'source': 'TIGER-Lab/MMLU-Pro', 'revision': MMLU_REV,
                           'source_file': row['source_file'], 'question_id': row['question_id'],
                           'question': row['question'], 'prompt': prompt, 'options': row['options'],
                           'gold_answer': letter, 'gold_option': row['options'][row['answer_index']],
                           'hle_category': cat, 'source_category': row['category'],
                           'ori_source': row['src'], 'family_key': family,
                           'prompt_sha256': prompt_hash, 'stable_rank_key': family_rank(family),
                           'candidate_partition': family_partition(family), 'modality': 'text_only',
                           'source_license': 'MIT dataset card; preserve source attribution',
                           'answer_evidence': 'publisher_expert_reviewed_reference',
                           'reference_type': 'multipleChoice', 'source_family_limit':
                           'No original exam/paper identity: conservative normalized question stem only.'})
    train_quota, val_quota = proportional_quotas(500, COUNTS), proportional_quotas(100, COUNTS)
    academic_path = root / 'artifacts/data/candidates/new_academic_20261016/ranked_candidates.jsonl'
    academic = [json.loads(line) for line in academic_path.open()]
    academic = [r for r in academic if 'v4-pro' in r['teacher'].casefold()]
    groups = defaultdict(list)
    for row in academic:
        row['hle_category'] = ALIASES.get(row['hle_category'], row['hle_category'])
        groups[row['candidate_partition'], row['hle_category']].append(row)
    for values in groups.values():
        values.sort(key=lambda r: r['stable_rank_key'])
    selected_train = []
    existing_cats = ('Math',) if args.replace_science_with_gold else ('Math', 'Biology/Medicine', 'Physics', 'Chemistry')
    for cat in existing_cats:
        selected_train.extend(groups['train', cat][:train_quota[cat]])
    # The existing global family reserve is retained; no old raw is accessed.
    math_val = groups['val', 'Math'][:val_quota['Math']]
    assert len(math_val) == val_quota['Math']
    missing_cats = [c for c in COUNTS if c not in existing_cats]
    mmlu_group = defaultdict(list)
    for row in candidates:
        mmlu_group[row['candidate_partition'], row['hle_category']].append(row)
    for values in mmlu_group.values():
        values.sort(key=lambda r: r['stable_rank_key'])
    # Gold-only validation tasks never receive teacher generations.
    validation = list(math_val)
    for cat in COUNTS:
        if cat != 'Math':
            validation.extend(mmlu_group['val', cat][:val_quota[cat]])
    assert len(validation) == 100
    val_hashes = {r['prompt_sha256'] for r in validation}
    val_ngram = set().union(*(ngrams(r['question']) for r in validation if r.get('question')))
    teacher_pool = []
    for cat in missing_cats:
        rows = [r for r in mmlu_group['train', cat] if r['prompt_sha256'] not in val_hashes and
                not ngrams(r['question']) & val_ngram]
        # One reserve per desired example; successful generations are admitted in rank order.
        teacher_pool.extend(rows[:2 * train_quota[cat]])
    assert not {r['family_key'] for r in selected_train + teacher_pool} & {r['family_key'] for r in validation}
    write_rows(out / 'existing_new_train_candidate_metadata.jsonl', selected_train)
    write_rows(out / 'teacher_reservoir.jsonl', teacher_pool)
    write_rows(out / 'proxy_val_metadata.jsonl', validation)
    # Materialize only the 41 independently held-out Math reference questions.
    math_file = root / next(r['source_file'] for r in math_val)
    math_rows = pq.read_table(math_file).to_pylist()
    proxy = []
    for row in validation:
        if row.get('source') == 'Math-v4':
            source_row = math_rows[row['row_index_within_range_or_shard']]
            assert text_hash(source_row['problem']) == row['prompt_sha256']
            proxy.append({**row, 'question': source_row['problem'], 'prompt': source_row['problem'],
                          'gold_answer': source_row['expected_answer'], 'reference_type': 'exactMatch',
                          'validation_readiness': 'reference_available_scorer_pending'})
        else:
            proxy.append(row)
    write_rows(out / 'proxy_val_100.jsonl', proxy)
    summary = {'training_target': train_quota, 'validation_target': val_quota,
               'mmlu_revision': MMLU_REV, 'mmlu_rows_scanned': len(source_rows),
               'mmlu_rejection_counts': dict(rejected),
               'mmlu_candidate_partition_category_counts': dict(Counter(
                   r['candidate_partition'] + ':' + r['hle_category'] for r in candidates)),
               'existing_new_train_candidates': len(selected_train),
               'existing_new_train_readiness': dict(Counter(r['train_readiness'] for r in selected_train)),
               'new_teacher_target': {c: train_quota[c] for c in missing_cats},
               'replace_science_with_gold_tasks': args.replace_science_with_gold,
               'new_teacher_reservoir': len(teacher_pool), 'validation_rows': len(proxy),
               'validation_categories': dict(Counter(r['hle_category'] for r in proxy)),
               'validation_reference_types': dict(Counter(r['reference_type'] for r in proxy)),
               'validation_mmlu_original_sources': dict(Counter(r['ori_source'] for r in proxy if 'ori_source' in r)),
               'validation_image_tasks': 0, 'training_released': False,
               'formal_HLE_columns_read': ['question'],
               'formal_overlap_check': 'normalized question exact SHA256 + normalized word 13-gram SHA256; no answers read',
               'train_val_exclusion': 'normalized question stem family + 13-gram between new teacher reservoir and MMLU val',
               'limitations': ['This is a proxy dev; HLE difficulty is not reproduced.',
                               '0 images and 59 MCQ versus HLE 342/2500 images and 591/2500 MCQ.',
                               'Other covers trivia, geography, and logic; music/art/ballet/games are largely absent.',
                               'Source exam/paper family and semantic paraphrase exclusion incomplete.',
                               'Publisher-only Science answers remain a separate unverified hold pool when replaced.',
                               'Final 41 Math gold scoring still requires a validated answer matcher.']}
    dump(out / 'selection_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
