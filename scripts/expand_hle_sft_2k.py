"""Expand HLE QA data without changing the historical 500/100 exports."""

import argparse
from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path
import re
import shutil

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['OMP_NUM_THREADS'] = '2'

import pyarrow.parquet as pq
from transformers import AutoTokenizer

from candidate_selection import family_partition, family_rank, proportional_quotas, text_hash
from prepare_night_hle_proxy import COUNTS, HLE_REV, MMLU_REV, category, ngrams

MODEL_REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'
REL = 'artifacts/data/candidates/night_hle_20261016'


def rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def write(path, values):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in values))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def clean_messages(raw):
    result = []
    for m in raw:
        assert m['role'] in {'user', 'assistant'} and not m.get('tool_calls')
        content = m.get('content') or ''
        assert isinstance(content, str)
        if m['role'] == 'assistant':
            content = re.sub(r'^\s*<think>.*?</think>\s*', '', content, count=1, flags=re.S)
        assert content.strip() and '<think>' not in content and '</think>' not in content
        result.append({'role': m['role'], 'content': content})
    assert [m['role'] for m in result] == ['user', 'assistant']
    return result


def lengths(tokenizer, messages):
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False,
                                        enable_thinking=False, preserve_thinking=False)
    return len(tokenizer.encode(text, add_special_tokens=False)), len(tokenizer.encode(
        messages[-1]['content'], add_special_tokens=False))


def prepare(root, base, out, tokenizer):
    target = proportional_quotas(2000, COUNTS)
    old_meta = rows(base / 'swift_ready/train.provenance.jsonl')
    old_messages = rows(base / 'swift_ready/train.messages.jsonl')
    assert len(old_meta) == len(old_messages) == 500
    val = rows(base / 'proxy_val_100.jsonl')
    val_families = {r['family_key'] for r in val}
    val_hashes = {text_hash(r['question']) for r in val}
    val_grams = set().union(*(ngrams(r['question']) for r in val))
    formal = pq.read_table(root / 'artifacts/benchmarks/hle' / HLE_REV /
                           'test-00000-of-00001.parquet', columns=['question']).to_pylist()
    formal_hashes = {text_hash(r['question']) for r in formal}
    formal_grams = set().union(*(ngrams(r['question']) for r in formal))
    banned_grams = val_grams | formal_grams

    def excluded(question):
        h = text_hash(question)
        return h in val_hashes or h in formal_hashes or bool(ngrams(question) & banned_grams)

    math = []
    for meta, old in zip(old_meta, old_messages):
        if meta['hle_category'] == 'Math':
            full, body = lengths(tokenizer, old['messages'])
            math.append({'messages': old['messages'], 'metadata': meta,
                         'complete_sequence_tokens': full, 'assistant_tokens': body})
    old_families = {r['family_key'] for r in old_meta}
    ranked = rows(root / 'artifacts/data/candidates/new_academic_20261016/ranked_candidates.jsonl')
    candidates = [r for r in ranked if r['source'] == 'Math-v4' and r['candidate_partition'] == 'train'
                  and r['method'] == 'CoT_no_tool' and 'v4-pro' in r['teacher'].lower()
                  and r['family_key'] not in old_families | val_families]
    candidates.sort(key=lambda r: r['stable_rank_key'])
    wanted = candidates[:3 * (target['Math'] - len(math))]
    groups = defaultdict(dict)
    for r in wanted:
        groups[r['source_file']][r['row_index_within_range_or_shard']] = r
    restored, rejection = {}, Counter()
    for filename, indices in groups.items():
        offset = 0
        for batch in pq.ParquetFile(root / filename).iter_batches(batch_size=128, use_threads=False,
                columns=['problem', 'messages', 'tools', 'expected_answer']):
            for i, raw in enumerate(batch.to_pylist()):
                meta = indices.get(offset + i)
                if meta is None:
                    continue
                if excluded(raw['problem']):
                    rejection['formal_or_frozen_val_overlap'] += 1
                    continue
                assert text_hash(raw['problem']) == meta['prompt_sha256']
                try:
                    assert not raw.get('tools')
                    messages = clean_messages(raw['messages'])
                except (AssertionError, TypeError):
                    rejection['message_or_thinking_structure'] += 1
                    continue
                full, body = lengths(tokenizer, messages)
                if full > 65536 or body > 8192:
                    rejection['complete_64k_or_assistant_8k_limit'] += 1
                    continue
                restored[meta['family_key']] = {'messages': messages,
                    'metadata': dict(meta, hle_category='Math', teacher_mode='high',
                        answer_evidence='publisher_reference_match', hidden_reasoning_removed=True),
                    'complete_sequence_tokens': full, 'assistant_tokens': body}
            offset += len(batch)
    for meta in wanted:
        if len(math) >= target['Math']:
            break
        if meta['family_key'] in restored:
            math.append(restored[meta['family_key']])
    assert len(math) == target['Math'], (len(math), target['Math'])
    write(out / 'math.ready.jsonl', math)

    pool, seen, reject = [], set(), Counter()
    for filename in sorted((root / 'artifacts/data/raw/mmlu_pro' / MMLU_REV).glob('*.parquet')):
        for r in pq.read_table(filename).to_pylist():
            cat = category(r)
            h = text_hash(r['question'])
            if cat is None or cat == 'Math' or h in seen:
                continue
            seen.add(h)
            if family_partition('qa:' + h) != 'train' or excluded(r['question']):
                reject['partition_or_overlap'] += 1
                continue
            if re.search(r'(?:following|above|below|given)\s+(?:figure|diagram|image|graph)|shown\s+in',
                         r['question'], re.I):
                reject['missing_visual_context'] += 1
                continue
            letter = r['answer'].strip()
            assert letter == chr(65 + r['answer_index'])
            prompt = r['question'] + '\n\n' + '\n'.join(
                chr(65+i) + '. ' + option for i, option in enumerate(r['options']))
            family = 'qa:' + h
            pool.append({'source': 'TIGER-Lab/MMLU-Pro', 'revision': MMLU_REV,
                'source_file': str(filename.relative_to(root)), 'question_id': r['question_id'],
                'question': r['question'], 'prompt': prompt, 'options': r['options'],
                'gold_answer': letter, 'gold_option': r['options'][r['answer_index']],
                'hle_category': cat, 'source_category': r['category'], 'ori_source': r['src'],
                'family_key': family, 'prompt_sha256': h, 'stable_rank_key': family_rank(family),
                'candidate_partition': 'train', 'source_license': 'MIT dataset card',
                'historical_500_question': family in old_families})
    pool.sort(key=lambda r: (not r['historical_500_question'], r['stable_rank_key']))
    write(out / 'teacher_reservoir.jsonl', pool)
    for filename in ['val.messages.jsonl', 'val.tasks.jsonl', 'val.provenance.jsonl']:
        shutil.copyfile(base / 'swift_ready' / filename, out / filename)
    summary = {'training_target': target, 'new_teacher_target': {k:v for k,v in target.items() if k!='Math'},
        'math_ready': len(math), 'math_original_retained': 204, 'math_new': len(math)-204,
        'math_scan_rejections': dict(rejection), 'teacher_reservoir_counts': dict(Counter(r['hle_category'] for r in pool)),
        'teacher_historical_questions_available': sum(r['historical_500_question'] for r in pool),
        'teacher_reservoir_rejections': dict(reject), 'validation_byte_copy': True,
        'historical_500_files_untouched': True, 'formal_columns_read': ['question'],
        'science_publisher_only_135_hold_unchanged': True, 'length_limits': {'sequence':65536,'assistant':8192},
        'teacher_mode': 'high', 'historical_non_thinking_answers_policy': 'Regenerate questions with High; do not reuse old answer text.'}
    dump(out / 'selection_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))


def export(root, base, out, tokenizer):
    selection = json.loads((out / 'selection_summary.json').read_text())
    math_rows = rows(out / 'math.ready.jsonl')
    teacher = rows(out / 'new_teacher_accepted.jsonl')
    assert Counter(r['hle_category'] for r in teacher) == Counter(selection['new_teacher_target'])
    records = list(math_rows)
    for r in teacher:
        full, body = lengths(tokenizer, r['messages'])
        records.append({'messages': r['messages'], 'metadata': {k:v for k,v in r.items()
            if k not in {'messages','question','prompt','options','gold_answer','gold_option'}},
            'complete_sequence_tokens': full, 'assistant_tokens': body})
    assert len(records) == 2000
    assert len({r['metadata']['family_key'] for r in records}) == 2000
    assert all(r['complete_sequence_tokens']<=65536 and r['assistant_tokens']<=8192 for r in records)
    for r in records:
        assert clean_messages(r['messages']) == r['messages']
    write(out / 'train.messages.jsonl', [{'messages':r['messages']} for r in records])
    write(out / 'train.provenance.jsonl', [dict(r['metadata'], row=i,
        complete_sequence_tokens=r['complete_sequence_tokens'], assistant_tokens=r['assistant_tokens'])
        for i,r in enumerate(records)])
    for filename in ['val.messages.jsonl','val.tasks.jsonl','val.provenance.jsonl']:
        assert (out/filename).read_bytes() == (base/'swift_ready'/filename).read_bytes()
    full = [r['complete_sequence_tokens'] for r in records]
    body = [r['assistant_tokens'] for r in records]
    generation = json.loads((out/'teacher_generation_summary.json').read_text())
    summary = {'data_ready':True, 'train_rows':2000, 'validation_rows':100,
        'categories':dict(Counter(r['metadata']['hle_category'] for r in records)),
        'sources':dict(Counter(r['metadata']['source'] for r in records)),
        'teacher_mode':'DeepSeek-V4-Pro High (published Math / fresh API)',
        'full_sequence_tokens':{'sum':sum(full),'max':max(full),'mean':sum(full)/len(full)},
        'assistant_content_tokens':{'sum':sum(body),'max':max(body)},
        'suggested_max_length':2 ** math.ceil(math.log2(max(full))),
        'hard_sequence_limit':65536, 'hard_assistant_content_limit':8192,
        'truncated_samples':0,'hidden_reasoning_fields_in_training':0,
        'validation_bytes_unchanged':True,'original_500_files_untouched':True,
        'high_regenerated_historical_questions':sum(r['historical_500_question'] for r in teacher),
        'budget':generation, 'native_swift_labels_checked':False,
        'limits':['Category proxy only; no training images and difficulty differs from HLE.',
                  'Reference-matched answers do not prove every sentence of explanation.',
                  'Family/13-gram exclusions do not prove complete semantic independence.']}
    dump(out/'ready_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--phase',choices=['prepare','export'],required=True)
    a=p.parse_args()
    base=a.repo/REL
    out=base/'expanded_2k'
    out.mkdir(exist_ok=True)
    tokenizer=AutoTokenizer.from_pretrained(a.repo/'artifacts/models/base_metadata'/MODEL_REV,
        local_files_only=True,trust_remote_code=False)
    (prepare if a.phase=='prepare' else export)(a.repo,base,out,tokenizer)


if __name__=='__main__':
    main()
