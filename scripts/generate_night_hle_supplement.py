"""Bounded, resumable new DeepSeek teacher answers for independently split QA.

Gold answers are used only after generation. Validation is never sent to teacher.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import requests


SYSTEM = ('Solve the multiple-choice problem independently. Return a JSON object with '
          'two fields: "solution", a concise worked explanation suitable for the reader, '
          'and "answer", exactly one uppercase option letter. Do not include private '
          'thinking, think tags, or any text outside the JSON object. If uncertain, '
          'choose the best-supported option; do not invent missing information.')
MODEL = 'deepseek-v4-pro'
# Official peak USD rates checked 2026-10-16. All prompt tokens are charged at cache-miss
# rate conservatively. 8 CNY/USD is an internal budget safety factor, not an FX quote.
INPUT_USD_M, OUTPUT_USD_M, BUDGET_FACTOR = 1.32, 3.96, 8.0


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []


def append(path, record):
    with path.open('a') as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--max-attempts', type=int, default=240)
    parser.add_argument('--budget-cny', type=float, default=20.0)
    args = parser.parse_args()
    assert 1 <= args.max_attempts <= 480 and 0 < args.budget_cny <= 20
    root = args.candidate_dir
    env = {}
    for line in args.credentials.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key in {'DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL'}:
                env[key] = value.strip().strip('\"\'')
    base = env.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    assert base in {'https://api.deepseek.com', 'https://api.deepseek.com/v1'}
    summary = json.loads((root / 'selection_summary.json').read_text())
    target = summary['new_teacher_target']
    grouped = defaultdict(list)
    for row in rows(root / 'teacher_reservoir.jsonl'):
        grouped[row['hle_category']].append(row)
    schedule = []
    for index in range(max(map(len, grouped.values()))):
        for category in target:
            if index < len(grouped[category]):
                schedule.append(grouped[category][index])
    ledger_path = root / 'teacher_api_ledger.jsonl'
    accepted_path = root / 'new_teacher_accepted.jsonl'
    ledger, accepted = rows(ledger_path), rows(accepted_path)
    attempted = {r['family_key'] for r in ledger}
    success = Counter(r['hle_category'] for r in accepted)
    spent = sum(r['conservative_cost_usd'] for r in ledger)
    quality_review_cost = sum(r['conservative_cost_usd'] for r in rows(root / 'science_quality_review.jsonl'))
    spent += quality_review_cost
    budget_usd = args.budget_cny / BUDGET_FACTOR
    stop = 'reservoir_exhausted'
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + env['DEEPSEEK_API_KEY']
    for row in schedule:
        if row['family_key'] in attempted or success[row['hle_category']] >= target[row['hle_category']]:
            continue
        if len(ledger) >= args.max_attempts:
            stop = 'attempt_cap'
            break
        if all(success[key] >= value for key, value in target.items()):
            stop = 'quotas_satisfied'
            break
        reserve = ((len((SYSTEM + row['prompt']).encode()) + 1024) * INPUT_USD_M +
                   8192 * OUTPUT_USD_M) / 1e6
        if spent + reserve > budget_usd:
            stop = 'budget_guard'
            break
        started = time.time()
        receipt = {'family_key': row['family_key'], 'hle_category': row['hle_category'],
                   'source_question_id': row['question_id'], 'requested_model': MODEL,
                   'thinking': 'disabled', 'max_tokens': 8192,
                   'requested_at': datetime.now(timezone.utc).isoformat(),
                   'pricing_url': 'https://api-docs.deepseek.com/quick_start/pricing/',
                   'peak_usd_per_million': {'input_cache_miss': INPUT_USD_M, 'output': OUTPUT_USD_M},
                   'budget_conversion_safety_factor': BUDGET_FACTOR,
                   'gold_was_sent_to_teacher': False}
        response_data = None
        try:
            response = session.post(base + '/chat/completions', json={
                'model': MODEL, 'messages': [{'role': 'system', 'content': SYSTEM},
                                            {'role': 'user', 'content': row['prompt']}],
                'thinking': {'type': 'disabled'}, 'max_tokens': 8192, 'temperature': 0,
                'response_format': {'type': 'json_object'}, 'stream': False}, timeout=180)
            receipt['http_status'] = response.status_code
            response.raise_for_status()
            response_data = response.json()
            usage = response_data['usage']
            receipt.update({'usage': usage, 'returned_model': response_data.get('model'),
                            'response_id': response_data.get('id')})
            cost = (usage['prompt_tokens'] * INPUT_USD_M + usage['completion_tokens'] * OUTPUT_USD_M) / 1e6
            receipt['conservative_cost_usd'] = cost
            choice = response_data['choices'][0]
            message = choice['message']
            receipt['finish_reason'] = choice['finish_reason']
            assert choice['finish_reason'] == 'stop', 'incomplete_response'
            assert not message.get('reasoning_content'), 'unexpected_reasoning_content'
            result = json.loads(message['content'])
            answer = result['answer'].strip()
            solution = result['solution'].strip()
            assert isinstance(solution, str) and solution, 'empty_visible_solution'
            assert len(answer) == 1 and 'A' <= answer < chr(65 + len(row['options'])), 'invalid_option_letter'
            assert '<think>' not in solution and '</think>' not in solution, 'unexpected_think_tags'
            receipt['teacher_answer'] = answer
            receipt['gold_match'] = answer == row['gold_answer']
            receipt['status'] = 'accepted' if receipt['gold_match'] else 'gold_mismatch'
            if receipt['gold_match']:
                content = solution + '\n\nAnswer: ' + answer + '. ' + row['gold_option']
                record = {**row, 'teacher_model': response_data.get('model'),
                          'teacher_requested_model': MODEL, 'enable_thinking': False,
                          'messages': [{'role': 'user', 'content': row['prompt']},
                                       {'role': 'assistant', 'content': content}],
                          'answer_evidence': 'independent_teacher_choice_matches_publisher_gold',
                          'teacher_usage': usage, 'training_released': False,
                          'hold_reasons': ['fixed Qwen template/tokenization and final data audit pending']}
                append(accepted_path, record)
                accepted.append(record)
                success[row['hle_category']] += 1
        except (requests.RequestException, ValueError, KeyError, TypeError, AssertionError) as error:
            receipt['status'] = 'request_or_protocol_error'
            receipt['error_class'] = type(error).__name__
            if isinstance(error, AssertionError):
                receipt['protocol_failure'] = str(error)
            # If no usage was delivered, reserve the full maximum potential charge.
            receipt.setdefault('conservative_cost_usd', reserve)
        receipt['elapsed_seconds'] = round(time.time() - started, 3)
        spent += receipt['conservative_cost_usd']
        receipt['cumulative_conservative_usd'] = spent
        receipt['cumulative_budget_cny'] = spent * BUDGET_FACTOR
        append(ledger_path, receipt)
        ledger.append(receipt)
        attempted.add(row['family_key'])
        if response_data is not None:
            append(root / 'teacher_raw_responses.jsonl', {'family_key': row['family_key'], 'response': response_data})
        print(json.dumps({'attempts': len(ledger), 'accepted': dict(success),
                          'status': receipt['status'], 'budget_cny': round(spent * BUDGET_FACTOR, 5)}), flush=True)
    if all(success[key] >= value for key, value in target.items()):
        stop = 'quotas_satisfied'
    final = {'model_requested': MODEL, 'thinking': False, 'max_tokens': 8192,
             'target': target, 'accepted': dict(success), 'attempts': len(ledger),
             'status_counts': dict(Counter(r['status'] for r in ledger)),
             'missing': {key: max(0, value - success[key]) for key, value in target.items()},
             'conservative_cost_usd': spent, 'conservative_budget_cny': spent * BUDGET_FACTOR,
             'science_quality_review_cost_included_usd': quality_review_cost,
             'budget_cny_hard_cap': args.budget_cny, 'stop_reason': stop,
             'total_prompt_tokens': sum(r.get('usage', {}).get('prompt_tokens', 0) for r in ledger),
             'total_completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) for r in ledger),
             'maximum_completion_tokens': max((r.get('usage', {}).get('completion_tokens', 0) for r in ledger), default=0),
             'gold_not_sent_to_teacher': True, 'validation_teacher_calls': 0,
             'training_released': False}
    (root / 'teacher_generation_summary.json').write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(final, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
