#!/usr/bin/env python3
"""Rank metadata-only new academic candidates; never exports training bodies."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit

from audit_new_academic_cpu import (
    REVISIONS, clean, dump, method_group, normalize, pa, pq, Path,
)
from candidate_selection import SPLIT_SEED, family_partition, family_rank, text_hash

SEED = SPLIT_SEED
HLE_COUNTS = {'Mathematics': 1021, 'Biology': 280, 'Computer Science': 241,
              'Other': 233, 'Physics': 230, 'Humanities': 219,
              'Chemistry': 165, 'Engineering': 111}
TOPIC_MAP = {'mathematics': 'Mathematics', 'math': 'Mathematics',
             'biology': 'Biology', 'physics': 'Physics', 'chemistry': 'Chemistry'}


def canonical_url(value):
    if not value:
        return None
    parsed = urlsplit(value)
    match = re.search(r'/(?:questions|q)/(\d+)', parsed.path)
    path = '/questions/' + match.group(1) if match else parsed.path.rstrip('/')
    return urlunsplit(('https', parsed.netloc.casefold(), path, '', ''))


def science_rows(root, audit):
    receipts = json.loads((audit / 'download_receipts.json').read_text())
    receipts += json.loads((audit / 'range_download_receipts.json').read_text())
    for receipt in receipts:
        if receipt['source'] != 'Science-v2' or receipt.get('skipped'):
            continue
        path = root / receipt['local_path']
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == receipt['sha256']
        lines = data.split(b'\n')[:-1]
        if '.range' in path.name:
            lines = lines[1:]  # discard an initial partial record at arbitrary byte offset
        for index, line in enumerate(lines):
            if line:
                yield receipt['path'], str(path.relative_to(root)), index, json.loads(line)


def old_math_index(root):
    """Read problem/uuid columns only, strictly for cross-teacher grouping."""
    prompt_hashes, uuids = defaultdict(set), {}
    files = sorted((root / 'artifacts/data/raw/openr1_math').rglob('*.parquet'))
    rows = 0
    for path in files:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=512, columns=['problem', 'uuid'], use_threads=False):
            for row in batch.to_pylist():
                phash = text_hash(row['problem'])
                prompt_hashes[phash].add(row['uuid'])
                uuids[row['uuid']] = phash
                rows += 1
    return prompt_hashes, uuids, {'files': len(files), 'rows': rows,
        'columns': ['problem', 'uuid'], 'purpose': 'cross-teacher family linkage only, no old rows added or auto-excluded',
        'limits': 'OpenScience 1.6M old input rows not scanned; no semantic or paraphrase matching.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    args = parser.parse_args()
    root = args.repo
    audit = root / 'artifacts/data/audits/new_academic_20261016'
    out = root / 'artifacts/data/candidates/new_academic_20261016'
    out.mkdir(parents=True, exist_ok=True)
    formal_file = root / 'artifacts/data/audits/formal_input_fingerprints_20261016/index.json'
    formal = json.loads(formal_file.read_text())['hle_question_sha256']
    old_hashes, old_uuids, old_scope = old_math_index(root)
    counts, reasons, observed_topics, teachers, contract_counts = Counter(), Counter(), Counter(), Counter(), Counter()
    records, quarantine = [], []
    parents, token_to_index = [], {}
    blocked_aliases = set()

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def add(source, file, row_index, row):
        counts[source + '_scanned'] += 1
        metadata = row.get('metadata') or {}
        metadata = metadata if isinstance(metadata, dict) else {}
        topic = 'Mathematics' if source == 'Math-v4' else str(metadata.get('topic') or '<missing>')
        observed_topics[(source, topic)] += 1
        category = TOPIC_MAP.get(topic.casefold())
        teacher = 'publisher_DeepSeek-V4-Pro_High' if source == 'Math-v4' else str(metadata.get('generation_model') or '<missing>')
        teachers[(source, teacher)] += 1
        method = method_group(row)
        contract_counts[(source, method)] += 1
        users = [m.get('content') or '' for m in row['messages'] if m['role'] == 'user']
        question = row.get('problem') or (users[0] if users else '')
        phash = text_hash(question)
        url = canonical_url(row.get('url') or metadata.get('QuestionLink'))
        uuid = row.get('uuid')
        aliases = ['prompt:' + phash]
        if uuid:
            aliases.append('uuid:' + uuid)
        if url:
            aliases.append('url:' + url)
        old_ids = sorted(old_hashes.get(phash, set()) | ({uuid} if uuid in old_uuids else set()))
        for old_id in old_ids:
            aliases.append('uuid:' + old_id)
            aliases.append('prompt:' + old_uuids[old_id])
        record = {'source': source, 'source_file': file, 'row_index_within_range_or_shard': row_index,
                  'revision': REVISIONS['Math-v4' if source == 'Math-v4' else 'Science-v2'],
                  'uuid': uuid, 'source_url': url, 'prompt_sha256': phash,
                  'teacher': teacher, 'method': method, 'published_topic': topic,
                  'published_subtopic': metadata.get('subtopic'), 'hle_category': category,
                  'source_label': row.get('source') or source, 'license': row.get('license'),
                  'old_source_overlap': bool(old_ids), 'old_OpenR1_uuids': old_ids,
                  'modality': 'text_only', 'length_status': 'not_tokenized_for_candidate_ranking'}
        reject = None
        if phash in formal:
            reject = 'formal_HLE_exact_input_match'
            record['formal_ids'] = formal[phash]
        elif not category:
            reject = 'unmapped_topic_no_forced_HLE_category'
        elif method != 'CoT_no_tool':
            reject = 'tool_contract_not_HLE_no_tools'
        else:
            try:
                messages, tools = normalize(row)
                cleaned, _ = clean(messages)
                if tools:
                    reject = 'tools_declared_under_no_tool_label'
                elif not any(m['role'] == 'assistant' and m['content'].strip() for m in cleaned):
                    reject = 'no_visible_clean_assistant_content'
                elif any(m.get('tool_calls') for m in messages) or any(m['role'] == 'tool' for m in messages):
                    reject = 'tool_action_under_no_tool_label'
                elif not record['license']:
                    reject = 'missing_license'
            except (ValueError, TypeError, KeyError) as error:
                reject = 'structural_or_cleaning_' + type(error).__name__
        if reject:
            if reject == 'formal_HLE_exact_input_match':
                blocked_aliases.update(aliases)
            record['reason'] = reject
            reasons[(source, reject)] += 1
            quarantine.append(record)
            return
        # Math reference is publisher-verified; Science teacher output has no independent gold field.
        has_reference = source == 'Math-v4' and bool(row.get('expected_answer'))
        record['answer_evidence'] = 'publisher_reference_match' if has_reference else 'published_teacher_solution_no_independent_gold'
        record['train_readiness'] = 'candidate_with_publisher_reference' if has_reference else 'candidate_needs_answer_verification'
        record['validation_readiness'] = 'publisher_reference_available_needs_scorer_validation' if has_reference else 'validation_needs_gold'
        record['exact_lineage_status'] = 'source_url_available' if url else 'no_source_URL_prompt_hash_only'
        record['reference_sha256'] = text_hash(row['expected_answer']) if has_reference else None
        index = len(records)
        records.append(record)
        parents.append(index)
        record['family_aliases'] = aliases
        for alias in aliases:
            if alias in token_to_index:
                parents[find(index)] = find(token_to_index[alias])
            token_to_index[alias] = index

    math_path = root / 'artifacts/data/raw/nemotron_sft_math_v4' / REVISIONS['Math-v4'] / 'train-00000-of-00012.parquet'
    columns = ['uuid', 'problem', 'expected_answer', 'messages', 'tools', 'source', 'url', 'subset', 'license']
    position = 0
    for batch in pq.ParquetFile(math_path).iter_batches(batch_size=256, columns=columns, use_threads=False):
        for index, row in enumerate(batch.to_pylist()):
            add('Math-v4', str(math_path.relative_to(root)), position + index, row)
        position += len(batch)
    for source, file, row_index, row in science_rows(root, audit):
        add('Science-v2/' + source, file, row_index, row)

    families = defaultdict(list)
    for index, record in enumerate(records):
        families[find(index)].append(record)
    selected = []
    for members in families.values():
        aliases = sorted({alias for record in members for alias in record['family_aliases']})
        if blocked_aliases.intersection(aliases):
            for record in members:
                record['reason'] = 'family_alias_of_isolated_formal_task'
                quarantine.append(record)
                reasons[(record['source'], record['reason'])] += 1
            continue
        family = hashlib.sha256('\n'.join(aliases).encode()).hexdigest()
        categories = {r['hle_category'] for r in members}
        if len(categories) != 1:
            for record in members:
                record['reason'] = 'conflicting_category_within_exact_family'
                quarantine.append(record)
                reasons[(record['source'], record['reason'])] += 1
            continue
        members.sort(key=lambda r: (r['answer_evidence'] != 'publisher_reference_match',
                                    'V4-Pro' not in r['teacher'],
                                    hashlib.sha256((SEED + r['source_file'] + str(r['row_index_within_range_or_shard'])).encode()).hexdigest()))
        representative = members[0]
        representative['family_aliases'] = aliases
        representative['family_sha256'] = family
        representative['family_key'] = 'academic:' + family
        representative['observed_family_rows'] = len(members)
        representative['observed_family_teachers'] = sorted({r['teacher'] for r in members})
        representative['old_source_overlap'] = any(r['old_source_overlap'] for r in members)
        representative['old_OpenR1_uuids'] = sorted({u for r in members for u in r['old_OpenR1_uuids']})
        representative['candidate_partition'] = family_partition(representative['family_key'])
        representative['stable_rank_key'] = family_rank(representative['family_key'])
        representative['target_category_fraction'] = HLE_COUNTS[representative['hle_category']] / 2500
        selected.append(representative)
    selected.sort(key=lambda r: (r['candidate_partition'], r['hle_category'], r['stable_rank_key']))
    rank_counts = Counter()
    with (out / 'ranked_candidates.jsonl').open('w') as output:
        for record in selected:
            key = (record['candidate_partition'], record['hle_category'])
            rank_counts[key] += 1
            record['rank_within_partition_category'] = rank_counts[key]
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
    with (out / 'quarantined_metadata.jsonl').open('w') as output:
        for record in quarantine:
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
    receipts = json.loads((audit / 'download_receipts.json').read_text()) + json.loads((audit / 'range_download_receipts.json').read_text())
    report = {
        'status': 'ranked_candidate_partitions_only_NOT_final_training_export_or_frozen_taskdev',
        'seed': SEED, 'source_revisions': REVISIONS,
        'target': {'benchmark': 'HLE', 'class_counts': HLE_COUNTS,
                   'image_marginal': {'target': '342/2500', 'available_new_pool': 0},
                   'allocation_policy': 'Keep all 8 category shares explicit; do not renormalize missing classes into Math. Per-category rankings support later token/time quota selection.'},
        'holdout_rule': "Shared candidate_selection.py: rank=sha256((SPLIT_SEED+'\\0'+family_key).encode()); int(rank[:16],16)%10==0 holds out ~10%; no fixed task count; one representative per observed exact family. Independent of HLE class fractions.",
        'grouping': 'Transitive union by normalized prompt hash, canonical source URL, or published UUID; no semantic deduplication. Family aliases/row indices remain in ignored remote metadata.',
        'normalization': 'NFKC -> collapse Unicode whitespace -> strip -> casefold -> SHA256 UTF8',
        'scope': 'Math first verified shard; Science 8x8MiB byte ranges/file, first+7 evenly distributed offsets. Byte-stratified convenience scan, not uniform row sampling or full population estimate.',
        'scanned_row_counts': dict(counts),
        'observed_topics': [{'source': k[0], 'topic': k[1], 'rows': v} for k, v in sorted(observed_topics.items())],
        'teacher_counts_in_scanned_bytes_only': [{'source': k[0], 'teacher': k[1], 'rows': v} for k, v in sorted(teachers.items())],
        'method_counts_in_scanned_bytes_only': [{'source': k[0], 'method': k[1], 'rows': v} for k, v in sorted(contract_counts.items())],
        'isolation_counts': [{'source': k[0], 'reason': k[1], 'rows': v} for k, v in sorted(reasons.items())],
        'qualified_rows_before_family_collapse': len(records), 'observed_exact_families': len(selected),
        'partition_category_counts': [{'partition': k[0], 'category': k[1], 'families': v} for k, v in sorted(rank_counts.items())],
        'readiness_counts': dict(Counter(r['validation_readiness'] for r in selected)),
        'readiness_by_partition': [{'partition': k[0], 'readiness': k[1], 'families': v}
                                   for k, v in sorted(Counter((r['candidate_partition'], r['validation_readiness'])
                                                             for r in selected).items())],
        'candidate_teacher_category_counts': [{'partition': k[0], 'teacher': k[1], 'category': k[2], 'families': v}
                                              for k, v in sorted(Counter((r['candidate_partition'], r['teacher'], r['hle_category'])
                                                                        for r in selected).items())],
        'old_source_overlap_families': sum(r['old_source_overlap'] for r in selected),
        'old_source_overlap_policy': 'Retain newer teacher representative; link known old UUID/prompt aliases to same family/partition. Old source overlap is not a formal benchmark hit and is not auto-excluded. No prior final old val exists.',
        'formal_HLE_fingerprint_index_sha256': hashlib.sha256(formal_file.read_bytes()).hexdigest(),
        'formal_HLE_exact_hit_rows': sum(v for (source, reason), v in reasons.items() if reason == 'formal_HLE_exact_input_match'),
        'old_teacher_isolation_scope': old_scope,
        'downloaded_science_bytes': sum(r['bytes_received'] for r in receipts if r['source'] == 'Science-v2'),
        'missing_HLE_classes': [k for k in HLE_COUNTS if not any(r['hle_category'] == k for r in selected)],
        'limits': ['Zero exact HLE hits does not prove no contamination: paraphrases, embedded prompts, image content and lineage aliases remain pending.',
                   'Science has no independent gold/verification field; val needs_gold never counted as runnable taskdev. New teacher name does not establish correctness.',
                   'AoPS source URL absent; prompt hashes and publisher UUIDs cannot fully isolate modified versions of the same original problem.',
                   'Cross-source matching spans current new scan and old OpenR1 problem/uuid metadata only; known old aliases are retained in the same candidate family/partition; old OpenScience and unscanned new records remain pending.',
                   'No fixed training quota, train window, ms-swift labels, GPU throughput or final dataset chosen. Candidate partitions may change if new family aliases are discovered.'],
        'artifacts': {'ranked_candidates': str((out / 'ranked_candidates.jsonl').relative_to(root)),
                      'ranked_candidates_sha256': hashlib.sha256((out / 'ranked_candidates.jsonl').read_bytes()).hexdigest(),
                      'quarantine': str((out / 'quarantined_metadata.jsonl').relative_to(root))},
    }
    dump(out / 'aggregate.json', report)
    print(json.dumps({'output': str(out / 'aggregate.json'), 'families': len(selected), 'scanned': dict(counts)}))


if __name__ == '__main__':
    main()
