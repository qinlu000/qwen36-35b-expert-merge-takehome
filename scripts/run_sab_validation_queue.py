"""Execute saved SAB validation programs after the dedicated four-CPU gate opens."""
import argparse
import ast
import base64
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import types

import httpx

from ai4sci_bench.adapters.direct_llm import DirectLLMAdapter
from asi_score_transport import DeepSeekJudgeTransport, input_token_bound, write_json


def vision_grade(args, task, workspace, condition):
    source = args.project / 'artifacts/data/_metadata/sab_validation_source_20261016/gpt4_visual_judge.py'
    prompt = next(ast.literal_eval(node.value) for node in ast.parse(source.read_text()).body
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROMPT_ORIGIN'
                                                           for t in node.targets))
    settings = {'mode': 'real', 'credentials': str(args.credentials), 'output': str(args.output),
                'max_generation_calls': 144, 'max_cny': 10}
    transport = DeepSeekJudgeTransport(settings, condition)
    directory = args.output / 'vision_calls'
    directory.mkdir(exist_ok=True)

    def encode_image(filename):
        filename = str(filename)
        path = (Path(task['benchmark_root']).parent / filename
                if filename.startswith('benchmark/eval_programs/gold_results/') else workspace / filename)
        return base64.b64encode(path.read_bytes()).decode()

    def score_figure(pred, gold):
        content = [{'type': 'text', 'text': prompt},
                   {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + pred}},
                   {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + gold}}]
        body = {'model': 'deepseek-flash', 'messages': [{'role': 'user', 'content': content}],
                'temperature': .2, 'max_tokens': 1000, 'n': 1, 'top_p': .95,
                'frequency_penalty': 0, 'presence_penalty': 0, 'thinking': {'type': 'disabled'}}
        texts = []
        bound = input_token_bound(body['messages'])
        reservation = (bound * .3 + 1000 * 1.2) * 8 / 1e6
        for sample in range(3):
            completed = directory / (condition + '.' + str(sample) + '.json')
            if completed.exists():
                data = json.loads(completed.read_text())
            else:
                data = None
                for attempt in range(2):
                    identifier = condition + '.' + str(sample) + '.' + str(attempt)
                    started_file = directory / (identifier + '.started.json')
                    if started_file.exists():
                        continue
                    transport.journal({'event': 'started', 'id': identifier, 'condition': condition,
                        'reserved_cny': reservation, 'max_tokens': 1000, 'at_unix': time.time()}, reserve=True)
                    write_json(started_file, {'at_unix': time.time(), 'body': body})
                    try:
                        with httpx.Client(trust_env=False, timeout=300) as client:
                            response = client.post('https://api.deepseek.com/chat/completions', json=body,
                                headers={'Authorization': 'Bearer ' + transport.key})
                            response.raise_for_status()
                            data = response.json()
                        assert len(data['choices']) == 1
                        assert isinstance(data['choices'][0]['message']['content'], str)
                        write_json(completed, data)
                        transport.journal({'event': 'completed', 'id': identifier, 'condition': condition,
                                           'usage': data.get('usage'), 'model': data.get('model')})
                        break
                    except Exception as error:
                        transport.journal({'event': 'failed', 'id': identifier, 'condition': condition,
                                           'error_type': type(error).__name__})
                if data is None:
                    raise RuntimeError('Two allowed visual Judge attempts failed')
            texts.append(data['choices'][0]['message']['content'])
        matches = [re.search(r'\[FINAL SCORE\]: (\d{1,3})', text, re.DOTALL) for text in texts]
        values = [int(match.group(1).strip()) if match else 0 for match in matches]
        return texts, sum(values) / len(values)

    # Keep the publisher's checker and its threshold unchanged; replace only image API transport.
    shim = types.ModuleType('gpt4_visual_judge')
    shim.encode_image, shim.score_figure = encode_image, score_figure
    sys.modules['gpt4_visual_judge'] = shim
    spec = importlib.util.spec_from_file_location('sab_checker', task['checker'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.eval()


def sandbox(args, workspace, code, seconds, *, gold=False):
    unit = 'apex-sab-val-' + workspace.name.replace('.', '-') + '-' + str(time.time_ns())
    command = ['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit, '-p', 'MemoryMax=8G',
               '-p', 'MemorySwapMax=0', sys.executable, str(args.project / 'scripts/sab_validation_sandbox.py'),
               '--workspace=' + str(workspace), '--env-dir=' + str(args.env_dir),
               '--datasets=' + str(args.benchmark / 'datasets'), '--code=' + code,
               '--receipt=' + str(workspace / 'limits.json'), '--cpu-list=112,113,114,115']
    if gold:
        command.append('--gold-results=' + str(args.benchmark / 'eval_programs/gold_results'))
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=max(.1, seconds))
        status = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'timeout': False}
    except subprocess.TimeoutExpired as error:
        subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=all', unit + '.scope'],
                       capture_output=True)
        status = {'returncode': None, 'stdout': (error.stdout or b'').decode(errors='replace'),
                  'stderr': (error.stderr or b'').decode(errors='replace'), 'timeout': True}
    status['elapsed_seconds'] = time.monotonic() - started
    write_json(workspace / ('checker_execution.json' if gold else 'execution.json'), status)
    return status


def main(args):
    args.project, args.output, args.env_dir = args.project.resolve(), args.output.resolve(), args.env_dir.resolve()
    args.benchmark = args.project / 'artifacts/data/raw/scienceagentbench/verified_asset/benchmark'
    args.output.mkdir(parents=True, exist_ok=True)
    results = args.output / 'results'
    results.mkdir(exist_ok=True)
    while not (args.ready_file.is_file() and args.env_ready_file.is_file()):
        print('Waiting for SAB exclusive four-CPU and dependency readiness', flush=True)
        time.sleep(30)
    gate = json.loads(args.ready_file.read_text())
    assert gate['ready'] is True and gate['cpus'] == [112, 113, 114, 115]
    os.sched_setaffinity(0, gate['cpus'])
    tasks = [json.loads(line) for line in args.tasks.read_text().splitlines() if line.strip()]
    adapter = DirectLLMAdapter()
    runs = {'base': args.generations / 'base_asi', 'asi128': args.generations / 'asi128'}
    while True:
        for model, directory in runs.items():
            for task in tasks:
                label = model + '.sab-' + str(task['task_id'])
                source, target = directory / 'questions' / ('sab-' + str(task['task_id']) + '.json'), results / (label + '.json')
                if target.exists() or not source.exists():
                    continue
                answer = json.loads(source.read_text())
                result = {'model': model, 'task_id': task['task_id'], 'source_result': str(source),
                          'generation_seconds': answer.get('elapsed_seconds', 0), 'correct': None,
                          'protocol': 'SAB independent segmented generation/execution proxy, not official ASI walltime'}
                workspace = args.output / 'workspaces' / label
                if workspace.exists():
                    write_json(target, dict(result, status='execution_interrupted_invalid'))
                    continue
                workspace.mkdir(parents=True)
                if answer['status'] != 'completed':
                    timeout = answer['status'] == 'solver_budget_exhausted'
                    write_json(target, dict(result, status=answer['status'], correct=False if timeout else None))
                    continue
                remaining = max(0, 1200 - result['generation_seconds'])
                result['execution_budget_seconds'] = remaining
                result['offline_queue_seconds'] = max(0, time.time() - source.stat().st_mtime)
                code = adapter._extract_code(answer['response'], code_file='solution.py',
                                              expected_output_files=[task['expected_output']])
                (workspace / 'solution.py').write_text(code)
                (workspace / 'pred_results').mkdir()
                (workspace / 'benchmark/datasets').mkdir(parents=True)
                execution = sandbox(args, workspace, 'solution.py', remaining)
                result['execution_seconds'] = execution['elapsed_seconds']
                text = execution['stdout'] + execution['stderr']
                if not (workspace / task['expected_output']).exists():
                    missing_env = 'ModuleNotFoundError' in text or 'ImportError' in text or 'bwrap:' in text
                    write_json(target, dict(result, status='environment_invalid' if missing_env else 'missing_output',
                                             correct=None if missing_env else False, execution=execution))
                    continue
                try:
                    if 'gpt4_visual_judge' in Path(task['checker']).read_text():
                        score, details = vision_grade(args, task, workspace, label)
                    else:
                        grader = args.output / 'graders' / label
                        (grader / 'benchmark/eval_programs/gold_results').mkdir(parents=True)
                        (grader / 'benchmark/datasets').mkdir()
                        shutil.copytree(workspace / 'pred_results', grader / 'pred_results')
                        shutil.copyfile(task['checker'], grader / 'checker.py')
                        checked = sandbox(args, grader, 'checker.py', 300, gold=True)
                        assert checked['returncode'] == 0
                        score, details = ast.literal_eval(checked['stdout'].splitlines()[-1])
                    write_json(target, dict(result, status='scored', correct=bool(score), details=details))
                except Exception as error:
                    write_json(target, dict(result, status='scoring_invalid', error_type=type(error).__name__))
        rows = [json.loads(path.read_text()) for path in results.glob('*.json')]
        summary = {'expected': 40, 'saved': len(rows), 'models': {}}
        for model in runs:
            chosen = [row for row in rows if row['model'] == model]
            valid = [row for row in chosen if row['correct'] is not None]
            summary['models'][model] = {'expected': 20, 'saved': len(chosen), 'scored': len(valid),
                'correct': sum(row['correct'] for row in valid),
                'accuracy_percent': 5 * sum(row['correct'] for row in valid) if len(valid) == 20 else None,
                'status_counts': dict(Counter(row['status'] for row in chosen))}
        write_json(args.output / 'summary.json', summary)
        print(json.dumps(summary), flush=True)
        if len(rows) == 40:
            break
        time.sleep(30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--generations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--env-dir', type=Path, required=True)
    parser.add_argument('--ready-file', type=Path, required=True)
    parser.add_argument('--env-ready-file', type=Path, required=True)
    parser.add_argument('--credentials', type=Path,
                        default=Path('/data/caoqinlu/projects/apex-takehome/artifacts/private/deepseek.env'))
    main(parser.parse_args())
