"""Summarize saved direct-validation results without issuing model/Judge requests."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def summarize(args):
    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    hle = {}
    for label, folder in [('base', 'base_hle'), ('hle16', 'hle16'), ('hle250', 'hle250')]:
        generations = {p.stem: json.loads(p.read_text())
                       for p in (args.output / folder / 'questions').glob('*.json')}
        scores = {}
        for task in tasks:
            path = args.output / 'hle_scores/results' / (label + '.' + task['id'] + '.json')
            if path.exists():
                scores[task['id']] = json.loads(path.read_text())

        def group(selected):
            generated = [generations[t['id']] for t in selected if t['id'] in generations]
            scored = [scores[t['id']] for t in selected if t['id'] in scores]
            valid = [row for row in scored if row['correct'] is not None]
            judged = [row for row in scored if row['evaluation_status'] == 'judged']
            answered = [row for row in generated if row['status'] == 'completed']
            usage = [row['usage']['completion_tokens'] for row in answered]
            deadline = sum(row['status'] == 'solver_budget_exhausted' for row in generated)
            correct = sum(row['correct'] for row in valid)
            complete = len(valid) == len(selected)
            return {'expected': len(selected), 'generated_terminal': len(generated),
                    'complete': complete, 'completed_answers': len(answered),
                    'answers_judged': len(judged), 'deadline_no_answer': deadline,
                    'generation_infrastructure_or_protocol_invalid': len(generated) - len(answered) - deadline,
                    'judge_invalid': sum(row['evaluation_status'] == 'evaluation_invalid' for row in scored),
                    'correct': correct,
                    'answered_accuracy_percent': 100 * sum(row['correct'] for row in judged) / len(judged)
                                                if judged else None,
                    'answered_accuracy_scope': 'only scored completed answers; selected by answering before deadline',
                    'budget_limited_success_percent': 100 * correct / len(selected) if complete else None,
                    'score_statuses': dict(Counter(row['evaluation_status'] for row in scored)),
                    'answer_finish_reasons': dict(Counter(row.get('finish_reason') for row in answered)),
                    'completion_tokens': {'sum': sum(usage), 'median': statistics.median(usage) if usage else None,
                                          'max': max(usage) if usage else None}}
        value = group(tasks)
        value['answer_type'] = {kind: group([t for t in tasks if t['answer_type'] == kind])
                                for kind in sorted({t['answer_type'] for t in tasks})}
        value['category'] = {category: group([t for t in tasks if t['category'] == category])
                             for category in sorted({t['category'] for t in tasks})}
        hle[label] = value
    sab = {}
    for model, folder in [('base', 'base_asi'), ('asi128', 'asi128')]:
        rows = [json.loads(path.read_text()) for path in (args.output / folder / 'questions').glob('*.json')]
        sab[model] = {'expected': 20, 'generated_terminal': len(rows),
                      'generation_statuses': dict(Counter(row['status'] for row in rows))}
    sab_scores = args.output / 'sab_scores/summary.json'
    result = {'updated_at_utc': datetime.now(timezone.utc).isoformat(),
              'metric_scope': 'independent held-out proxies, not official HLE or ASI benchmark scores',
              'timeout_policy': '300s deadline without full response counted only in budget-limited success; not Judge-marked wrong',
              'hle': hle, 'sab_generation': sab,
              'sab_cpu_ready': (args.output / 'sab_cpu_ready.json').exists(),
              'sab_environment_ready': (args.output / 'sab_env_ready.json').exists(),
              'sab_scores': json.loads(sab_scores.read_text()) if sab_scores.exists() else None}
    save(args.output / 'progress_summary.json', result)
    if hle['base']['complete'] and not (args.output / 'base_hle_first_complete.json').exists():
        save(args.output / 'base_hle_first_complete.json', {
            'recorded_at_utc': result['updated_at_utc'], 'scope': result['metric_scope'],
            'model': 'Qwen/Qwen3.6-35B-A3B', 'variant': 'untrained fixed Base',
            'context_tokens': 65536, 'output_cap': 8192, 'nonthinking': True,
            'per_question_walltime_seconds': 300, 'parallel': 8, 'results': hle['base']})
    print(json.dumps({'updated_at_utc': result['updated_at_utc'],
          'hle': {name: {k: value[k] for k in ['generated_terminal', 'completed_answers', 'deadline_no_answer',
                        'answers_judged', 'correct', 'budget_limited_success_percent']} for name, value in hle.items()},
          'sab_generation': sab, 'sab_cpu_ready': result['sab_cpu_ready']}), flush=True)
    return all(value['complete'] for value in hle.values()) and result['sab_scores'] is not None and result['sab_scores']['saved'] == 40


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--follow', action='store_true')
    args = parser.parse_args()
    while True:
        complete = summarize(args)
        if not args.follow or complete:
            break
        time.sleep(30)
