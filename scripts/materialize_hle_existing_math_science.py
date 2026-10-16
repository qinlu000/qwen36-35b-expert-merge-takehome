"""Reuse published strong-teacher final answers; no teacher inference."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import urllib.request

import pyarrow.parquet as pq

from candidate_selection import normalized_text
from prepare_night_hle_proxy import HLE_REV

SCIENCE_REV = '6536a5021222a94126968e8c92f29ee47fc8a7df'


def rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def grams(text):
    words = re.findall(r'\w+', normalized_text(text))
    return {' '.join(words[i:i + 13]) for i in range(len(words) - 12)}


def write(path, values):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--extra-rqa-blocks', type=int, default=0)
    args = parser.parse_args()
    root = args.repo
    out = root / 'artifacts/data/candidates/hle_existing_2k_20261016/math_science'
    out.mkdir(parents=True, exist_ok=True)
    raw = root / 'artifacts/data/raw/nemotron_sft_science_v2' / SCIENCE_REV
    receipts = []
    # Adjacent to an existing V4-rich rqa range; at most two small blocks.
    assert 0 <= args.extra_rqa_blocks <= 2
    for i in range(args.extra_rqa_blocks):
        start = 2391983511 + i * 8388608
        end = start + 8388607
        path = raw / f'rqa.jsonl.extra_existing2k_{i + 1}.8MiB'
        if not path.exists():
            url = (f'https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/'
                   f'resolve/{SCIENCE_REV}/rqa.jsonl?existing2k_range={start}')
            request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(request, timeout=90) as response:
                content_range = response.headers.get('Content-Range', '')
                assert response.status == 206 and content_range.startswith(f'bytes {start}-{end}/')
                data = response.read(8388609)
            assert len(data) == 8388608
            path.write_bytes(data)
        receipts.append({'path': str(path.relative_to(root)), 'requested_range': [start, end],
                         'bytes': path.stat().st_size, 'purpose': 'bounded chemistry supply'})

    base = root / 'artifacts/data/candidates/night_hle_20261016'
    val = rows(base / 'proxy_val_100.jsonl')
    formal = pq.read_table(root / 'artifacts/benchmarks/hle' / HLE_REV /
                           'test-00000-of-00001.parquet', columns=['question']).to_pylist()
    blocked = {normalized_text(r['question']) for r in formal + val}
    blocked_grams = set().union(*(grams(r['question']) for r in formal + val))
    prior = rows(root / 'artifacts/data/candidates/new_academic_20261016/ranked_candidates.jsonl')
    prior_by_uuid = {r['uuid']: r for r in prior if r.get('uuid')}
    prior_val_uuids = {r['uuid'] for r in prior if r.get('candidate_partition') == 'val'}
    seen, science, rejected, scanned = set(), [], Counter(), Counter()
    for path in sorted(raw.iterdir()):
        if not path.is_file():
            continue
        lines = path.read_bytes().split(b'\n')[:-1]
        if '.range' in path.name or '.extra_' in path.name:
            lines = lines[1:]
        for line_number, line in enumerate(lines):
            if not line:
                continue
            row = json.loads(line)
            metadata = row.get('metadata') or {}
            if metadata.get('generation_model') != 'DeepSeek-V4-Pro':
                continue
            topic = metadata.get('topic')
            scanned[topic] += 1
            if topic not in {'Physics', 'Chemistry', 'Biology'}:
                continue
            uuid = row['uuid']
            messages = row['messages']
            if row.get('tools') or any(m.get('tool_calls') for m in messages):
                rejected['tool_protocol'] += 1
                continue
            if [m['role'] for m in messages] != ['user', 'assistant']:
                rejected['message_roles'] += 1
                continue
            question = messages[0]['content']
            prompt = normalized_text(question)
            if uuid in prior_val_uuids:
                rejected['prior_candidate_holdout'] += 1
                continue
            if prompt in blocked or grams(question) & blocked_grams:
                rejected['formal_or_frozen_val_question_overlap'] += 1
                continue
            if prompt in seen:
                rejected['duplicate_exact_question'] += 1
                continue
            cleaned = []
            for message in messages:
                content = message.get('content') or ''
                if message['role'] == 'assistant':
                    content = re.sub(r'^\s*<think>.*?</think>\s*', '', content, count=1, flags=re.S)
                assert content.strip() and '<think>' not in content and '</think>' not in content
                cleaned.append({'role': message['role'], 'content': content})
            seen.add(prompt)
            old = prior_by_uuid.get(uuid, {})
            science.append({'task_id': 'science-v2:' + uuid,
                'domain': 'Biology/Medicine' if topic == 'Biology' else topic,
                'source_id': 'nvidia/Nemotron-SFT-Science-v2:' + uuid,
                'teacher': 'DeepSeek-V4-Pro', 'messages': cleaned,
                'source_meta': {'dataset': 'nvidia/Nemotron-SFT-Science-v2', 'revision': SCIENCE_REV,
                    'uuid': uuid, 'source_file': str(path.relative_to(root)), 'source_line': line_number,
                    'source_url': old.get('source_url'), 'license': row.get('license'),
                    'published_subtopic': metadata.get('subtopic'),
                    'question_format': metadata.get('question_format'),
                    'teacher_mode': 'not_recorded_by_publisher',
                    'quality': 'published_teacher_answer_no_independent_gold',
                    'family_key': old.get('family_key'),
                    'candidate_partition': old.get('candidate_partition', 'new_train_candidate'),
                    'hidden_reasoning_removed': True, 'visible_answer_preserved': True,
                    'token_status': 'root_final_export_applies_64k_8k_without_truncation'}})
    math = []
    for row in rows(base / 'expanded_2k/math.ready.jsonl'):
        meta = row['metadata']
        math.append({'task_id': 'math-v4:' + meta['uuid'], 'domain': 'Math',
            'source_id': 'nvidia/Nemotron-SFT-Math-v4:' + meta['uuid'],
            'teacher': 'DeepSeek-V4-Pro High', 'messages': row['messages'],
            'source_meta': dict(meta, complete_sequence_tokens=row['complete_sequence_tokens'],
                                assistant_tokens=row['assistant_tokens'],
                                teacher_mode='high', quality='publisher_reference_match')})
    write(out / 'science.candidates.jsonl', [r for r in science if r['domain'] != 'Biology/Medicine'])
    write(out / 'science.reserve_bio.jsonl', [r for r in science if r['domain'] == 'Biology/Medicine'])
    write(out / 'math.ready.jsonl', math)
    write(out / 'candidates.jsonl', math + science)
    summary = {'math_reused_ready': len(math), 'science_candidates_by_domain': dict(Counter(r['domain'] for r in science)),
        'science_v4_scanned_by_topic': dict(scanned), 'rejected': dict(rejected),
        'extra_range_receipts': receipts, 'formal_columns_read': ['question'],
        'frozen_validation_rows': len(val), 'validation_unchanged': True,
        'new_teacher_calls': 0, 'hidden_reasoning_in_output': False, 'visible_answer_truncation': False,
        'length_checks': '817 math already checked; root final export token-checks science at 64k/8k',
        'science_quality': 'publisher model answer; no independent gold; teacher effort not recorded'}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
