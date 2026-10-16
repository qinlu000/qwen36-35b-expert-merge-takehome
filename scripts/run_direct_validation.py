"""Generate held-out HLE-proxy or SAB answers without sending gold to the solver."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx

from prepare_sab_sft import SYSTEM as ASI_SYSTEM


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def inputs(project, tasks, kind):
    system = ((project / 'configs/eval/prompts/hle_system.txt').read_text().rstrip('\n')
              if kind == 'hle' else ASI_SYSTEM)
    rows = [json.loads(line) for line in tasks.read_text().splitlines() if line.strip()]
    return [{'id': str(row['id']) if kind == 'hle' else 'sab-' + str(row['task_id']),
             'category': row.get('category', row.get('repo')),
             'messages': [{'role': 'system', 'content': system},
                          {'role': 'user', 'content': row['question' if kind == 'hle' else 'prompt']}]}
            for row in rows]


async def run(args):
    project, output = args.project.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    questions = inputs(project, args.tasks.resolve(), args.kind)
    assert len({q['id'] for q in questions}) == len(questions)
    # This file is the solver input. References/checkers are kept in the source task file only.
    input_path = output / 'solver_inputs.jsonl'
    input_text = ''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in questions)
    if input_path.exists():
        assert input_path.read_text() == input_text
    else:
        input_path.write_text(input_text)
    protocol = json.loads((project / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    generation = {k: v for k, v in protocol['generation_default'].items()
                  if k not in ('sampling_seed', 'scope')}
    deadline_seconds = 300 if args.kind == 'hle' else 1200
    config = {'kind': args.kind, 'checkpoint': args.model, 'endpoint': args.endpoint,
              'tasks': str(args.tasks.resolve()), 'count': len(questions),
              'context_tokens': 65536, 'generation': generation, 'seed': 0,
              'thinking': False, 'preserve_thinking': False,
              'walltime_seconds': deadline_seconds, 'parallel': args.parallel,
              'scoring': 'separate; no reference or checker in model request'}
    if (output / 'run_config.json').exists():
        assert json.loads((output / 'run_config.json').read_text()) == config
    save(output / 'run_config.json', config)
    result_dir = output / 'questions'
    result_dir.mkdir(exist_ok=True)
    if args.prepare_only:
        print(json.dumps({'prepared': len(questions), 'network_calls': 0}))
        return
    header = {'Authorization': 'Bearer ' + args.key_file.read_text().strip()}
    template = {'enable_thinking': False, 'preserve_thinking': False}
    semaphore = asyncio.Semaphore(args.parallel)
    async with httpx.AsyncClient(base_url=args.endpoint.rstrip('/'), headers=header,
                                trust_env=False,
                                limits=httpx.Limits(max_connections=args.parallel)) as client:
        async def solve(row):
            path = result_dir / (row['id'] + '.json')
            if path.exists():
                return
            async with semaphore:
                started = time.monotonic()
                record = {'id': row['id'], 'category': row['category'], 'model': args.model,
                          'started_at_utc': datetime.now(timezone.utc).isoformat(),
                          'status': 'infrastructure_invalid'}
                # Admission is persisted before any call. A resumed process does not regenerate
                # an ambiguous interrupted response under the same experiment name.
                started_path = result_dir / (row['id'] + '.started')
                if started_path.exists():
                    record['error'] = 'interrupted_previous_attempt; retained without regeneration'
                    save(path, record)
                    return
                started_path.write_text(record['started_at_utc'])
                try:
                    async with asyncio.timeout(deadline_seconds):
                        count = await client.post('/tokenize', json={
                            'model': args.model, 'messages': row['messages'],
                            'chat_template_kwargs': template}, timeout=deadline_seconds)
                        count.raise_for_status()
                        count = count.json()
                        assert count['max_model_len'] == 65536
                        record['prompt_tokens_exact'] = count['count']
                        if count['count'] + 8192 > 65536:
                            record['status'] = 'context_overflow'
                        else:
                            payload = dict(generation, model=args.model, messages=row['messages'],
                                           seed=0, chat_template_kwargs=template)
                            response = await client.post('/v1/chat/completions', json=payload,
                                timeout=max(.1, deadline_seconds - (time.monotonic() - started)))
                            response.raise_for_status()
                            response = response.json()
                            record['raw_response'] = response
                            choice = response['choices'][0]
                            message = choice['message']
                            assert not message.get('reasoning') and not message.get('reasoning_content')
                            assert isinstance(message.get('content'), str)
                            assert response['usage']['prompt_tokens'] == count['count']
                            assert response['usage']['completion_tokens'] <= 8192
                            record.update(status='completed', response=message['content'],
                                          usage=response['usage'], finish_reason=choice['finish_reason'])
                except (httpx.ConnectTimeout, httpx.PoolTimeout) as error:
                    record.update(error_type=type(error).__name__)
                except (TimeoutError, httpx.ReadTimeout, httpx.WriteTimeout) as error:
                    record.update(status='solver_budget_exhausted', error_type=type(error).__name__)
                except Exception as error:
                    record.update(error_type=type(error).__name__, error=str(error)[:300])
                record['elapsed_seconds'] = round(time.monotonic() - started, 3)
                record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
                save(path, record)
                print(json.dumps({k: record[k] for k in ('id', 'status', 'elapsed_seconds')}), flush=True)
        await asyncio.gather(*(solve(row) for row in questions))
    results = [json.loads((result_dir / (row['id'] + '.json')).read_text()) for row in questions]
    save(output / 'summary.json', {'count': len(questions), 'saved': len(results),
         'status_counts': dict(Counter(r['status'] for r in results)),
         'completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) for r in results),
         'scoring': 'not run', 'finished_at_utc': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--kind', choices=['hle', 'asi'], required=True)
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parallel', type=int, default=20)
    parser.add_argument('--prepare-only', action='store_true')
    asyncio.run(run(parser.parse_args()))
