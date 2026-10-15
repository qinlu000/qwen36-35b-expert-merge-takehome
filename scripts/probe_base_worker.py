"""Synthetic HTTP acceptance of an existing TP2 replica, without formal benchmark inputs."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import httpx


TEMPLATE = {'enable_thinking': False, 'preserve_thinking': False}


async def run(args):
    key = args.key_file.read_text().strip()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'endpoint': args.endpoint, 'worker': args.worker, 'passed': False,
              'purpose': 'synthetic eight-admitted-request queue/profile acceptance',
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'context_tokens': 65536, 'output_cap': 8192, 'requests': []}
    async with httpx.AsyncClient(base_url=args.endpoint, trust_env=False,
            headers={'Authorization': 'Bearer ' + key}, timeout=300,
            limits=httpx.Limits(max_connections=12)) as client:
        async def post(path, body):
            response = await client.post(path, json=body)
            response.raise_for_status()
            return response.json()

        try:
            ready_deadline = time.monotonic() + args.wait_seconds
            while True:
                try:
                    response = await client.get('/health', timeout=3)
                    if response.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if time.monotonic() >= ready_deadline:
                    raise TimeoutError('worker did not become ready within the startup window')
                await asyncio.sleep(2)
            response = await client.get('/v1/models')
            response.raise_for_status()
            assert any(x['id'] == 'apex-qwen' for x in response.json()['data'])
            async with httpx.AsyncClient(trust_env=False) as unauthenticated:
                response = await unauthenticated.get(args.endpoint + '/v1/models', timeout=10)
                assert response.status_code == 401
            report['authentication_enforced'] = True

            def messages(repeats):
                return [{'role': 'user', 'content':
                    'Synthetic context probe.\n' + ' filler' * repeats +
                    '\nIgnore the filler. Reply exactly SYNTHETIC_REPLICA_OK.'}]

            async def count(msgs):
                result = await post('/tokenize', {'model': 'apex-qwen', 'messages': msgs,
                                                  'chat_template_kwargs': TEMPLATE})
                assert result['max_model_len'] == 65536
                return result['count']

            low, high = 0, 57344
            while low < high:
                middle = (low + high + 1) // 2
                if await count(messages(middle)) <= 57344:
                    low = middle
                else:
                    high = middle - 1
            long_messages = messages(low)
            long_tokens = await count(long_messages)
            assert 57336 <= long_tokens <= 57344
            report['long_prompt_tokens'] = long_tokens
            short_messages = [{'role': 'user', 'content':
                               'Reply exactly SYNTHETIC_REPLICA_OK.'}]
            short_tokens = await count(short_messages)
            report['guard_over_budget_tokens'] = await count(messages(low + 64))
            assert report['guard_over_budget_tokens'] + 8192 > 65536
            report['over_budget_generations'] = 0
            metrics = []
            stop_metrics = asyncio.Event()

            async def sample_metrics():
                while not stop_metrics.is_set():
                    response = await client.get('/metrics', timeout=10)
                    if response.status_code == 200:
                        row = {'t': time.monotonic()}
                        for name in ['num_requests_running', 'num_requests_waiting', 'kv_cache_usage_perc']:
                            values = re.findall(r'^vllm:' + name + r'(?:\{[^\n]*\})? ([0-9.eE+-]+)',
                                                response.text, flags=re.M)
                            if values:
                                row[name] = sum(map(float, values))
                        metrics.append(row)
                    await asyncio.sleep(0.1)

            start = asyncio.Event()

            async def solve(index):
                msgs, tokens = ((long_messages, long_tokens) if index < 4 else
                                (short_messages, short_tokens))
                payload = {'model': 'apex-qwen', 'messages': msgs,
                           'temperature': 1 if args.worker == 'terminal' else 0.7,
                           'top_p': 0.95 if args.worker == 'terminal' else 0.8,
                           'top_k': 20, 'min_p': 0, 'presence_penalty': 0,
                           'repetition_penalty': 1, 'seed': 0, 'max_tokens': 8192,
                           'chat_template_kwargs': TEMPLATE}
                assert tokens + 8192 <= 65536
                await start.wait()
                began = time.monotonic()
                response = await post('/v1/chat/completions', payload)
                choice = response['choices'][0]
                message = choice['message']
                assert not message.get('reasoning') and not message.get('reasoning_content')
                assert response['usage']['prompt_tokens'] == tokens
                assert 'SYNTHETIC_REPLICA_OK' in (message.get('content') or '')
                assert choice['finish_reason'] == 'stop'
                assert 0 < response['usage']['completion_tokens'] <= 8192
                return {'index': index, 'long_input': index < 4,
                        'latency_seconds': time.monotonic() - began,
                        'usage': response['usage'], 'finish_reason': choice['finish_reason']}

            sampler = asyncio.create_task(sample_metrics())
            tasks = [asyncio.create_task(solve(i)) for i in range(8)]
            began = time.monotonic()
            start.set()
            try:
                report['requests'] = await asyncio.gather(*tasks)
            finally:
                stop_metrics.set()
                await sampler
            report['concurrent_batch_seconds'] = time.monotonic() - began
            report['metric_samples'] = len(metrics)
            report['metrics_peak'] = {name: max(row[name] for row in metrics if name in row)
                for name in ['num_requests_running', 'num_requests_waiting', 'kv_cache_usage_perc']
                if any(name in row for row in metrics)}
            assert report['metrics_peak'].get('num_requests_running', 0) <= 4
            report['limitations'] = ['Synthetic requests only; native benchmark acceptance remains separate.',
                'Short actual completions; full8192 decode not exercised.',
                'Prometheus snapshots are not continuous GPU peak-memory measurements.']
            report['passed'] = True
        finally:
            report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
            (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps({'worker': args.worker, 'passed': report['passed'],
                              'completed': len(report['requests']), 'output': str(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--worker', choices=['asi', 'terminal'], required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wait-seconds', type=int, default=1200)
    asyncio.run(run(parser.parse_args()))


if __name__ == '__main__':
    main()
