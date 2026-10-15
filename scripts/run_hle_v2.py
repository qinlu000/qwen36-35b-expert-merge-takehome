"""Fixed HLE v2 generation: exact server token guard, one frozen answer per ID.

Synthetic calibration is separate from the 2500-question formal run. No answers,
rationales or grading API are read here. Existing terminal results are never retried.
"""
import argparse
import asyncio
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time

import httpx


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def synthetic_questions():
    from PIL import Image
    rows = []
    for n in range(8):
        row = {'id': f'synthetic-{n}', 'question': 'What is 17 + 25?',
               'image': '', 'expected': '42'}
        if n % 2:
            color = 'red' if n < 4 else 'blue'
            size = (32, 32) if n < 4 else (640, 480)
            stream = io.BytesIO()
            Image.new('RGB', size, color).save(stream, format='PNG')
            row.update(question='Name the dominant color in this image.',
                       image='data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode(),
                       expected=color)
        rows.append(row)
    return rows


async def run(args):
    root = args.project.resolve()
    protocol_path = root / 'configs/eval/protocol_v2_unified64k8k.json'
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    cfg = protocol['benchmarks']['hle']
    gen = protocol['generation_default']
    assert protocol['model']['context_tokens'] == 65536 and gen['max_tokens'] == 8192
    assert not protocol['model']['enable_thinking']
    assert not protocol['model']['preserve_thinking']
    assert cfg['question_walltime_seconds'] == 300
    assert protocol['scheduling']['max_admitted_solver_tasks'] == 8
    manifest_bytes = (root / cfg['task_manifest']).read_bytes()
    manifest = json.loads(manifest_bytes)
    system = (root / cfg['system_prompt']).read_text().rstrip('\n')
    source = root / 'artifacts/benchmarks/hle/source/hle_eval/run_model_predictions.py'
    # Validate the selected prompt against the actual fixed official implementation.
    import ast
    official_system = next(ast.literal_eval(n.value) for n in ast.parse(source.read_text()).body
                           if isinstance(n, ast.Assign) and any(
                               isinstance(t, ast.Name) and t.id == 'SYSTEM_PROMPT' for t in n.targets))
    assert system == official_system
    if args.mode == 'calibration':
        questions = synthetic_questions()
        input_sha = digest(json.dumps(questions, sort_keys=True).encode())
    else:
        import pyarrow.parquet as pq
        data = root / 'artifacts/benchmarks/hle' / cfg['dataset_revision'] / 'test-00000-of-00001.parquet'
        input_sha = digest(data.read_bytes())
        assert input_sha == manifest['source_file_sha256']
        questions = pq.read_table(data, columns=['id', 'question', 'image']).to_pylist()
        assert len(questions) == len({q['id'] for q in questions}) == 2500
        assert {q['id'] for q in questions} == set(manifest['task_ids'])
        assert {q['id'] for q in questions if q['image']} == set(manifest['image_task_ids'])
        order = {task_id: i for i, task_id in enumerate(manifest['task_ids'])}
        questions.sort(key=lambda q: order[q['id']])
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    result_dir = out / 'questions'
    result_dir.mkdir(exist_ok=True)
    run_config = {'mode': args.mode, 'protocol_sha256': digest(protocol_bytes),
                  'task_manifest_sha256': digest(manifest_bytes), 'input_sha256': input_sha,
                  'official_source_sha256': digest(source.read_bytes()),
                  'runner_sha256': digest(Path(__file__).read_bytes()),
                  'system_prompt_sha256': digest(system.encode()),
                  'model_revision': protocol['model']['revision'], 'served_model': 'apex-qwen',
                  'endpoint': args.endpoint, 'solver_concurrency': 8, 'generation': gen,
                  'thinking': False, 'preserve_thinking': False,
                  'question_walltime_seconds': 300, 'total_questions': len(questions),
                  'read_columns': ['id', 'question', 'image'],
                  'grading': 'separate; no gold or grading service accessed'}
    config_path = out / 'run_config.json'
    if config_path.exists():
        assert json.loads(config_path.read_text()) == run_config, 'Refuse mixed run configuration'
    else:
        save(config_path, run_config)
    if args.prepare_only:
        print(json.dumps({'mode': args.mode, 'validated_inputs': len(questions),
                          'input_sha256': input_sha, 'network_calls': 0}))
        return
    key = args.key_file.read_text().strip()
    header = {'Authorization': 'Bearer ' + key}
    semaphore = asyncio.Semaphore(8)

    async with httpx.AsyncClient(base_url=args.endpoint.rstrip('/'), headers=header,
                                trust_env=False, limits=httpx.Limits(max_connections=8)) as client:
        async def request(path, payload, deadline, attempts):
            for number in range(1, 3):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('shared solver deadline')
                started = time.monotonic()
                receipt = {'path': path, 'attempt': number}
                attempts.append(receipt)
                try:
                    response = await client.post(path, json=payload, timeout=remaining)
                    receipt.update(http_status=response.status_code,
                                   elapsed_seconds=round(time.monotonic() - started, 4))
                    # A server 429 rejects admission. Never retry a read timeout,
                    # disconnect,500 or partial generation with an ambiguous outcome.
                    if response.status_code == 429 and number == 1:
                        await asyncio.sleep(min(1, max(0, deadline - time.monotonic())))
                        continue
                    response.raise_for_status()
                    return response.json()
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    receipt.update(connection_failure=type(exc).__name__,
                                   elapsed_seconds=round(time.monotonic() - started, 4))
                    if number == 2:
                        raise

        async def solve(question):
            task_id = question['id']
            assert '/' not in task_id and '\\' not in task_id
            result_path = result_dir / (task_id + '.json')
            if result_path.exists():
                return
            async with semaphore:
                started = time.monotonic()
                record = {'id': task_id, 'mode': args.mode, 'is_image': bool(question['image']),
                          'started_at_utc': datetime.now(timezone.utc).isoformat(),
                          'attempts': [], 'status': 'failed'}
                try:
                    async with asyncio.timeout(300):
                        content = [{'type': 'text', 'text': question['question']}]
                        if question['image']:
                            content.append({'type': 'image_url', 'image_url': {'url': question['image']}})
                        messages = [{'role': 'system', 'content': system},
                                    {'role': 'user', 'content': content}]
                        template = {'enable_thinking': False, 'preserve_thinking': False}
                        deadline = started + 300
                        count = await request('/tokenize', {'model': 'apex-qwen',
                                              'messages': messages, 'chat_template_kwargs': template},
                                              deadline, record['attempts'])
                        prompt_tokens = count['count']
                        record['prompt_tokens_exact'] = prompt_tokens
                        assert count['max_model_len'] == 65536
                        if prompt_tokens + 8192 > 65536:
                            record['status'] = 'context_overflow'
                        else:
                            payload = {k: v for k, v in gen.items()
                                       if k not in {'sampling_seed', 'scope'}}
                            payload.update(model='apex-qwen', messages=messages,
                                           seed=gen['sampling_seed'], chat_template_kwargs=template)
                            record['request_sha256'] = digest(json.dumps(payload, sort_keys=True).encode())
                            response = await request('/v1/chat/completions', payload,
                                                     deadline, record['attempts'])
                            record['raw_response'] = response
                            choice = response['choices'][0]
                            message = choice['message']
                            record['response'] = message.get('content')
                            record['usage'] = response['usage']
                            record['finish_reason'] = choice['finish_reason']
                            assert response['usage']['prompt_tokens'] == prompt_tokens, 'token guard mismatch'
                            assert response['usage']['completion_tokens'] <= 8192
                            assert not message.get('reasoning') and not message.get('reasoning_content')
                            assert isinstance(record['response'], str)
                            record['status'] = 'completed'
                            if args.mode == 'calibration':
                                record['semantic_check'] = question['expected'].casefold() in record['response'].casefold()
                except Exception as exc:
                    record['error_type'] = type(exc).__name__
                    record['error'] = str(exc)[:300]
                finally:
                    record['elapsed_seconds'] = round(time.monotonic() - started, 4)
                    record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
                    save(result_path, record)
                    print(json.dumps({'id': task_id, 'status': record['status'],
                                      'elapsed_seconds': record['elapsed_seconds']}), flush=True)

        await asyncio.gather(*(solve(question) for question in questions))
    results = [json.loads(p.read_text()) for p in result_dir.glob('*.json')]
    summary = {'mode': args.mode, 'denominator': len(questions), 'saved_results': len(results),
               'status_counts': dict(Counter(r['status'] for r in results)),
               'image_results': sum(r['is_image'] for r in results),
               'prompt_tokens': sum(r.get('usage', {}).get('prompt_tokens', 0) for r in results),
               'completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) for r in results),
               'grading': 'not run', 'finished_at_utc': datetime.now(timezone.utc).isoformat()}
    if args.mode == 'calibration':
        summary['passed'] = len(results) == 8 and all(
            r['status'] == 'completed' and r.get('semantic_check') for r in results)
    save(out / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--mode', choices=['calibration', 'formal'], default='calibration')
    parser.add_argument('--endpoint', default='http://127.0.0.1:18061')
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    arguments = parser.parse_args()
    os.umask(0o077)
    if arguments.mode == 'formal' and not arguments.prepare_only:
        import fcntl
        block = arguments.project / 'artifacts/runs/base_model_block.lock'
        block.parent.mkdir(parents=True, exist_ok=True)
        with block.open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            owner = block.with_suffix('.owner.json')
            save(owner, {'benchmark': 'hle', 'pid': os.getpid(), 'state': 'running',
                         'output': str(arguments.output),
                         'started_at_utc': datetime.now(timezone.utc).isoformat()})
            try:
                asyncio.run(run(arguments))
            finally:
                save(owner, {'benchmark': 'hle', 'pid': os.getpid(), 'state': 'finished',
                             'output': str(arguments.output),
                             'finished_at_utc': datetime.now(timezone.utc).isoformat()})
    else:
        asyncio.run(run(arguments))
