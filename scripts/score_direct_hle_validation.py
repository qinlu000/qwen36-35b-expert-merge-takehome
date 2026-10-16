"""Score the frozen 100-question HLE proxy using the existing HLE Judge protocol."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from score_hle_baseline_v2 import (Budget, BudgetExhausted, HOST, MODEL, SchoolTLS,
                                    now, parse_judge, save)


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ('results', 'requests', 'responses'):
        (output / name).mkdir(exist_ok=True)
    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    assert len(tasks) == 100
    generations = dict(value.split('=', 1) for value in args.runs)
    criteria = (args.project / 'configs/eval/prompts/hle_judge_criteria.txt').read_text().rstrip('\n')
    system = (args.project / 'configs/eval/prompts/hle_judge_json_system.txt').read_text().rstrip('\n')
    # Existing fixed transport reads the authorized secret without printing or copying it.
    credentials = dict(line.split('=', 1) for line in args.credentials.read_text().splitlines()
                       if line.strip() and not line.lstrip().startswith('#') and '=' in line)
    key = credentials['OPENAI_API_KEY'].strip().strip("\"'")
    assert credentials['OPENAI_BASE_URL'].strip().strip("\"'").rstrip('/') == 'https://' + HOST + '/v1'
    budget = Budget(output, args.max_cny, 2 * 100 * len(generations))

    def score(item):
        name, task, answer = item
        identifier = name + '.' + task['id']
        destination = output / 'results' / (identifier + '.json')
        base = {'id': task['id'], 'model': name, 'category': task['category'],
                'answer_type': task['answer_type'], 'source_status': answer['status']}
        if answer['status'] != 'completed':
            native_timeout = answer['status'] == 'solver_budget_exhausted'
            save(destination, dict(base, evaluation_status='native_no_answer' if native_timeout else 'evaluation_invalid',
                                   correct=False if native_timeout else None))
            return
        prompt = criteria.format(question=task['question'], correct_answer=task['answer'], response=answer['response'])
        payload = {'model': MODEL, 'messages': [{'role': 'system', 'content': system},
                    {'role': 'user', 'content': prompt}], 'temperature': 0, 'seed': 0,
                   'max_tokens': 4096, 'thinking': {'type': 'disabled'},
                   'chat_template_kwargs': {'enable_thinking': False},
                   'response_format': {'type': 'json_object'}}
        bound = len(system.encode()) + len(prompt.encode()) + 1024
        attempted = [call for call in budget.transaction()['calls'] if call.startswith(identifier + '.')]
        for attempt in range(len(attempted) + 1, 3):
            call = identifier + '.' + str(attempt)
            try:
                budget.reserve(call, bound)
            except BudgetExhausted:
                save(output / 'stop.json', {'reason': 'validation_judge_budget_exhausted'})
                return
            save(output / 'requests' / (call + '.json'), payload)
            connection, usage, success = SchoolTLS(args.tls_tunnel_port), None, False
            try:
                connection.request('POST', '/v1/chat/completions', json.dumps(payload, ensure_ascii=False).encode(),
                    {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
                response = connection.getresponse()
                raw = response.read().decode()
                save(output / 'responses' / (call + '.json'), {'http_status': response.status, 'body': raw})
                assert response.status == 200
                data = json.loads(raw)
                usage = data.get('usage')
                message = data['choices'][0]['message']
                assert not message.get('reasoning_content') and not message.get('reasoning')
                parsed = parse_judge(message['content'])
                save(destination, dict(base, evaluation_status='judged', correct=parsed['correct'] == 'yes',
                                       judge_response=parsed, usage=usage,
                                       reported_model=data.get('model'), system_fingerprint=data.get('system_fingerprint')))
                success = True
                return
            except Exception as error:
                save(output / 'responses' / (call + '.error.json'), {'error_type': type(error).__name__})
            finally:
                connection.close()
                budget.finish(call, success, usage)
        save(destination, dict(base, evaluation_status='evaluation_invalid', correct=None,
                               reason='two allowed Judge attempts failed; original answer retained'))

    def summary():
        results = [json.loads(path.read_text()) for path in (output / 'results').glob('*.json')]
        models = {}
        for name in generations:
            rows = [r for r in results if r['model'] == name]
            valid = [r for r in rows if r['correct'] is not None]
            groups = {}
            for group in sorted({t['answer_type'] for t in tasks}):
                selected = [r for r in valid if r['answer_type'] == group]
                denominator = sum(t['answer_type'] == group for t in tasks)
                groups[group] = {'expected': denominator, 'scored': len(selected),
                    'correct': sum(r['correct'] for r in selected),
                    'accuracy_percent': 100 * sum(r['correct'] for r in selected) / denominator
                                        if len(selected) == denominator else None}
            models[name] = {'expected': 100, 'saved': len(rows), 'scored': len(valid),
                'correct': sum(r['correct'] for r in valid),
                'accuracy_percent': sum(r['correct'] for r in valid) if len(valid) == 100 else None,
                'status_counts': dict(Counter(r['evaluation_status'] for r in rows)), 'subgroups': groups}
        ledger = budget.transaction()
        result = {'metric': 'held-out proxy accuracy; not official HLE2500', 'models': models,
                  'judge': MODEL, 'judge_calls': len(ledger['calls']),
                  'accounted_cny': sum(r['charged_cny'] for r in ledger['calls'].values()),
                  'max_cny': args.max_cny, 'updated_at_utc': now()}
        save(output / 'summary.json', result)
        print(json.dumps(result), flush=True)
        return all(model['saved'] == 100 for model in models.values())

    while True:
        todo = []
        for name, directory in generations.items():
            for task in tasks:
                source = Path(directory) / 'questions' / (task['id'] + '.json')
                result = output / 'results' / (name + '.' + task['id'] + '.json')
                if source.exists() and not result.exists():
                    todo.append((name, task, json.loads(source.read_text())))
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(score, todo))
        complete = summary()
        if complete or (output / 'stop.json').exists() or not args.follow:
            break
        time.sleep(args.poll_seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--runs', nargs='+', required=True, help='model_label=generation_directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, default=Path('/data/caoqinlu/projects/data-perception/.env'))
    parser.add_argument('--tls-tunnel-port', type=int, default=28443)
    parser.add_argument('--max-cny', type=float, default=10)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--follow', action='store_true')
    parser.add_argument('--poll-seconds', type=float, default=15)
    run(parser.parse_args())
