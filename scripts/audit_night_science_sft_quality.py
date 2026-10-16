"""Twelve-case cross-subject critique of publisher-only science SFT answers.

This is an independent model quality signal, never gold correctness evidence.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

import requests


SYSTEM = ('Critically review a candidate science question and its proposed training answer. '
          'The answer may be wrong. Check self-containment, internal consistency, missing '
          'figures/context, and scientific correctness as far as the given information permits. '
          'Return JSON only: {"verdict":"accept|needs_review|reject", '
          '"reason":"brief specific explanation", "concerns":["..."]}. '
          'Use reject for a clear error or broken question, needs_review when uncertain. '
          'Agreement is not independent ground truth. Do not reveal hidden thinking.')


def read_rows(path):
    return [json.loads(line) for line in path.open() if line.strip()] if path.exists() else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    args = parser.parse_args()
    root = args.candidate_dir
    rows = read_rows(root / 'train.cleaned_candidates.jsonl')
    grouped = defaultdict(list)
    for row in rows:
        if row['train_readiness'] == 'candidate_needs_answer_verification':
            grouped[row['metadata']['hle_category']].append(row)
    selected = []
    for key, values in sorted(grouped.items()):
        selected.extend(sorted(values, key=lambda r: r['metadata']['stable_rank_key'])[:4])
    assert len(selected) == 12
    env = {}
    for line in args.credentials.read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            key, value = line.split('=', 1)
            if key in {'DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL'}:
                env[key] = value.strip().strip('\"\'')
    base = env.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    assert base in {'https://api.deepseek.com', 'https://api.deepseek.com/v1'}
    out = root / 'science_quality_review.jsonl'
    previous = read_rows(out)
    spent_usd = sum(r['conservative_cost_usd'] for r in read_rows(root / 'teacher_api_ledger.jsonl'))
    spent_usd += sum(r['conservative_cost_usd'] for r in previous)
    done = {r['family_key'] for r in previous}
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + env['DEEPSEEK_API_KEY']
    results = list(previous)
    for row in selected:
        if row['id'] in done:
            continue
        text = 'QUESTION:\n' + row['messages'][0]['content'] + '\n\nPROPOSED ANSWER:\n' + row['messages'][1]['content']
        reserve = ((len((SYSTEM + text).encode()) + 1024) * .30 + 8192 * 1.20) / 1e6
        assert (spent_usd + reserve) * 8 <= 20, 'shared branch budget exhausted'
        response = session.post(base + '/chat/completions', json={
            'model': 'deepseek-flash', 'messages': [{'role': 'system', 'content': SYSTEM},
                                                  {'role': 'user', 'content': text}],
            'thinking': {'type': 'disabled'}, 'max_tokens': 8192,
            'temperature': 0, 'response_format': {'type': 'json_object'}}, timeout=120)
        response.raise_for_status()
        data = response.json()
        choice = data['choices'][0]
        usage = data['usage']
        cost = (usage['prompt_tokens'] * .30 + usage['completion_tokens'] * 1.20) / 1e6
        spent_usd += cost
        assert choice['finish_reason'] == 'stop'
        assert not choice['message'].get('reasoning_content')
        result = json.loads(choice['message']['content'])
        assert result['verdict'] in {'accept', 'needs_review', 'reject'}
        record = {'family_key': row['id'], 'hle_category': row['metadata']['hle_category'],
                  'source_uuid': row['metadata']['uuid'], 'reviewer_model': data.get('model'),
                  'review_kind': 'independent_model_critique_conditioned_on_candidate_answer',
                  'independent_gold': False, 'result': result, 'usage': usage,
                  'conservative_cost_usd': cost, 'cumulative_branch_budget_cny': spent_usd * 8,
                  'requested_at': datetime.now(timezone.utc).isoformat(),
                  'pricing': {'input_usd_per_million_peak_uncached': .30,
                              'output_usd_per_million_peak': 1.20, 'cny_budget_safety_factor': 8}}
        with out.open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        results.append(record)
        print(json.dumps({'completed': len(results), 'verdict': result['verdict'],
                          'cumulative_branch_budget_cny': spent_usd * 8}), flush=True)
    summary = {'selected': len(selected), 'reviewed': len(results),
               'category_counts': dict(Counter(r['hle_category'] for r in results)),
               'verdict_counts': dict(Counter(r['result']['verdict'] for r in results)),
               'review_cost_usd': sum(r['conservative_cost_usd'] for r in results),
               'cumulative_branch_budget_cny': spent_usd * 8,
               'evidence_type': 'critic-model quality signal; no human or executable gold',
               'training_policy': 'Publisher-only answers remain unverified distillation supervision; no correctness claim or formal-score-based filtering.'}
    (root / 'science_quality_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
