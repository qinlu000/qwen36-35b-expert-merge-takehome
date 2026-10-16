"""CPU materialization/audit of the bounded new HLE candidate mixture.

Keeps quality holds; exports no final training release and runs no model.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer

from audit_new_academic_cpu import clean, normalize, pq
from candidate_selection import text_hash
from prepare_night_hle_proxy import HLE_REV, ngrams


def read_rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    root = args.repo
    base = root / 'artifacts/data/candidates/night_hle_20261016'
    selected = read_rows(base / 'existing_new_train_candidate_metadata.jsonl')
    teacher = read_rows(base / 'new_teacher_accepted.jsonl')
    val = read_rows(base / 'proxy_val_100.jsonl')
    val_hash = {text_hash(r['question']) for r in val}
    val_grams = set().union(*(ngrams(r['question']) for r in val))
    formal = pq.read_table(root / 'artifacts/benchmarks/hle' / HLE_REV /
                           'test-00000-of-00001.parquet', columns=['question']).to_pylist()
    formal_hash = {text_hash(r['question']) for r in formal}
    formal_grams = set().union(*(ngrams(r['question']) for r in formal))
    groups = defaultdict(list)
    for row in selected:
        groups[row['source_file']].append(row)
    restored = []
    for source, metas in groups.items():
        indices = {r['row_index_within_range_or_shard']: r for r in metas}
        path = root / source
        if path.suffix == '.parquet':
            pos = 0
            for batch in pq.ParquetFile(path).iter_batches(batch_size=256, use_threads=False,
                    columns=['problem', 'messages', 'tools', 'expected_answer']):
                for offset, row in enumerate(batch.to_pylist()):
                    if pos + offset in indices:
                        restored.append((indices[pos + offset], row))
                pos += len(batch)
                if pos > max(indices):
                    break
        else:
            lines = path.read_bytes().split(b'\n')[:-1]
            if '.range' in path.name:
                lines = lines[1:]
            for index, meta in indices.items():
                restored.append((meta, json.loads(lines[index])))
    assert len(restored) == len(selected)
    rows = []
    for meta, row in restored:
        messages, tools = normalize(row)
        assert not tools and not any(m.get('tool_calls') or m['role'] == 'tool' for m in messages)
        messages, _ = clean(messages)
        question = row.get('problem') or next(m['content'] for m in messages if m['role'] == 'user')
        assert text_hash(question) == meta['prompt_sha256']
        rows.append((meta, messages, question))
    rows.extend((r, r['messages'], r['question']) for r in teacher)
    tokenizer = AutoTokenizer.from_pretrained(root / 'artifacts/models/base_metadata/' /
        '995ad96eacd98c81ed38be0c5b274b04031597b0', local_files_only=True, trust_remote_code=False)
    records, rejected, seen = [], [], set()
    full_lengths, assistant_lengths = [], []
    for meta, messages, question in rows:
        phash, grams = text_hash(question), ngrams(question)
        reject = None
        if phash in seen:
            reject = 'duplicate_training_prompt'
        elif phash in val_hash or grams & val_grams:
            reject = 'validation_exact_or_13gram_overlap'
        elif phash in formal_hash or grams & formal_grams:
            reject = 'formal_HLE_exact_or_13gram_overlap'
        else:
            seen.add(phash)
        if reject:
            rejected.append({'family_key': meta['family_key'], 'reason': reject})
            continue
        messages, _ = clean(messages)
        rendered = tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)
        full = len(tokenizer.encode(rendered, add_special_tokens=False))
        body = max(len(tokenizer.encode(m['content'], add_special_tokens=False))
                   for m in messages if m['role'] == 'assistant')
        if full > 65536 or body > 8192:
            rejected.append({'family_key': meta['family_key'], 'reason': 'fixed_protocol_length_limit',
                             'complete_sequence_tokens': full, 'max_assistant_body_tokens': body})
            continue
        readiness = meta.get('train_readiness', 'candidate_teacher_matches_publisher_gold')
        records.append({'id': meta['family_key'], 'messages': messages,
                        'metadata': {k: v for k, v in meta.items() if k not in {
                            'messages', 'question', 'prompt', 'options', 'gold_answer', 'gold_option'}},
                        'train_readiness': readiness, 'training_released': False,
                        'complete_sequence_tokens': full, 'max_assistant_body_tokens_proxy': body})
        full_lengths.append(full)
        assistant_lengths.append(body)
    path = base / 'train.cleaned_candidates.jsonl'
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    result = {'rows_before_checks': len(rows), 'rows_after_checks': len(records),
              'category_counts': dict(Counter(r['metadata']['hle_category'] for r in records)),
              'readiness_counts': dict(Counter(r['train_readiness'] for r in records)),
              'rejection_counts': dict(Counter(r['reason'] for r in rejected)),
              'rejected': rejected, 'complete_sequence_tokens': {'sum': sum(full_lengths),
                  'max': max(full_lengths, default=0), 'mean': sum(full_lengths)/len(full_lengths) if full_lengths else 0},
              'max_assistant_body_tokens_proxy': max(assistant_lengths, default=0),
              'fixed_tokenizer_revision': '995ad96eacd98c81ed38be0c5b274b04031597b0',
              'chat_template_sha256': hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
              'template_flags': {'enable_thinking': False, 'preserve_thinking': False},
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'training_released': False,
              'limitations': ['Sequence token counts are exact for the fixed rendered candidate file, not final Swift labels or processed window budget.',
                              '13-gram exclusion does not prove semantic or paper/exam-family independence.',
                              'Science no-independent-gold holds remain; nothing was trained.']}
    (base / 'materialization_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
