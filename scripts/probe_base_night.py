"""Synthetic acceptance of the live Base service, before any formal HLE generation."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from types import SimpleNamespace

import httpx
import run_hle_v2


async def main(args):
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'purpose': 'synthetic only; no benchmark question or grading API',
              'passed': False, 'cases': []}
    key = args.key_file.read_text().strip()
    generation = json.loads((args.project / 'configs/eval/protocol_v2_unified64k8k.json').read_text())['generation_default']
    template = {'enable_thinking': False, 'preserve_thinking': False}
    async with httpx.AsyncClient(base_url=args.endpoint, trust_env=False,
                                headers={'Authorization': 'Bearer ' + key},
                                limits=httpx.Limits(max_connections=8)) as client:
        async def post(path, payload, timeout=300):
            result = await client.post(path, json=payload, timeout=timeout)
            result.raise_for_status()
            return result.json()

        def payload(messages, **extra):
            data = {k: v for k, v in generation.items() if k not in {'sampling_seed', 'scope'}}
            return dict(data, model='apex-qwen', seed=0, messages=messages,
                        chat_template_kwargs=template, **extra)

        def messages(n):
            return [{'role': 'system', 'content': 'Read the input and follow the final instruction.'},
                    {'role': 'user', 'content': 'Padding:' + ' x' * n + '\nReply with the number 42 only.'}]

        async def count(msg):
            return (await post('/tokenize', {'model': 'apex-qwen', 'messages': msg,
                                            'chat_template_kwargs': template}))['count']

        try:
            ready_deadline = time.monotonic() + 1200
            while True:
                try:
                    health = await client.get('/health', timeout=3)
                    if health.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= ready_deadline:
                    raise TimeoutError('service not healthy in1200s')
                await asyncio.sleep(5)
            unauth = await client.get('/v1/models', headers={'Authorization': ''})
            assert unauth.status_code == 401
            models = await client.get('/v1/models')
            models.raise_for_status()
            assert any(x['id'] == 'apex-qwen' for x in models.json()['data'])
            report['cases'].append({'case': 'authentication', 'passed': True})

            calibration = SimpleNamespace(project=args.project, mode='calibration', endpoint=args.endpoint,
                                          key_file=args.key_file, output=args.output / 'hle_calibration',
                                          prepare_only=False)
            await run_hle_v2.run(calibration)
            native = json.loads((calibration.output / 'summary.json').read_text())
            assert native['passed'], 'Native HLE synthetic acceptance failed'
            report['cases'].append({'case': 'native_hle_8_admitted_text_and_image', 'result': native})

            padding = 57344 - await count(messages(0))
            for _ in range(8):
                actual = await count(messages(padding))
                if actual == 57344:
                    break
                padding += 57344 - actual
            assert actual == 57344
            boundary_messages = messages(padding)
            started = time.monotonic()
            boundary = await post('/v1/chat/completions', payload(boundary_messages))
            assert boundary['usage']['prompt_tokens'] == 57344
            assert '42' in boundary['choices'][0]['message']['content']
            run_hle_v2.save(args.output / 'boundary_response.json', boundary)
            report['cases'].append({'case': 'exact57344_input_plus8192_cap',
                                    'usage': boundary['usage'], 'elapsed_seconds': time.monotonic() - started})
            over = messages(padding + 1)
            assert await count(over) == 57345
            rejected = await client.post('/v1/chat/completions', json=payload(over), timeout=30)
            assert rejected.status_code == 400
            report['cases'].append({'case': '57345_plus8192_rejected', 'http_status': 400})

            async def long_input(n):
                # Eight admitted solvers, engine max_num_seqs=4; log queue-inclusive time.
                msg = messages(padding - n)
                started = time.monotonic()
                result = await post('/v1/chat/completions', payload(msg))
                assert result['usage']['prompt_tokens'] == 57344 - n
                assert '42' in result['choices'][0]['message']['content']
                return {'index': n, 'usage': result['usage'],
                        'elapsed_seconds': time.monotonic() - started}
            concurrent = await asyncio.gather(*(long_input(n) for n in range(8)))
            report['cases'].append({'case': '8_admitted_long_inputs', 'results': concurrent})

            started = time.monotonic()
            full_output = await post('/v1/chat/completions', payload(
                [{'role': 'user', 'content': 'Write a very long list of distinct positive integers, one per line. Continue until the token budget is exhausted.'}],
                min_tokens=8192))
            assert full_output['usage']['completion_tokens'] == 8192
            assert full_output['choices'][0]['finish_reason'] == 'length'
            run_hle_v2.save(args.output / 'full8192_response.json', full_output)
            report['cases'].append({'case': 'full8192_decode_synthetic_min_tokens',
                                    'usage': full_output['usage'],
                                    'elapsed_seconds': time.monotonic() - started,
                                    'note': 'min_tokens is a synthetic stress setting only; never used in formal requests'})
            report['passed'] = True
        except Exception as exc:
            report['error_type'] = type(exc).__name__
            report['error'] = str(exc)[:400]
        finally:
            report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
            run_hle_v2.save(args.output / 'acceptance.json', report)
            print(json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--endpoint', default='http://127.0.0.1:18061')
    p.add_argument('--key-file', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    asyncio.run(main(p.parse_args()))
