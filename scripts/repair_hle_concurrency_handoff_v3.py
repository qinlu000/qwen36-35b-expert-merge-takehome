"""HLE concurrency handoff leaf; preserve all terminal answers and native budgets."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import time

import httpx

from run_hle_v2 import save


async def bounded_queue(entries, execute, healthy, checkpoint, concurrency=8, interval=1, stop_admission_file=None):
    """Health before admission and while all active requests are waiting."""
    pending = iter(entries)
    active = {}
    admitted, completed = [], []
    exhausted, reason, draining = False, None, False
    try:
        while active or not exhausted:
            if not await healthy():
                reason = 'endpoint_health_failed'
                break
            draining = stop_admission_file is not None and stop_admission_file.exists()
            while len(active) < concurrency and not exhausted and not draining:
                if not await healthy():
                    reason = 'endpoint_health_failed_before_admission'
                    break
                try:
                    entry = next(pending)
                except StopIteration:
                    exhausted = True
                    break
                active[asyncio.create_task(execute(entry))] = entry
                admitted.append(entry['id'])
                checkpoint({'state': 'running', 'admitted': admitted, 'completed': completed,
                            'active': [e['id'] for e in active.values()]})
            if reason or not active:
                break
            done, _ = await asyncio.wait(active, timeout=interval, return_when=asyncio.FIRST_COMPLETED)
            # Inspect every result before admitting any replacements.
            for task in done:
                entry = active.pop(task)
                result = await task
                completed.append(entry['id'])
                if result.get('infrastructure_failure'):
                    reason = 'transport_failure_requires_audit'
            if reason:
                break
    finally:
        for task in active:
            if not task.done():
                task.cancel()
        await asyncio.gather(*active, return_exceptions=True)
    final = {'state': 'paused_infrastructure' if reason else ('drained' if draining and not exhausted else 'completed'), 'reason': reason,
             'admitted': admitted, 'completed': completed,
             'cancelled_or_unwinding': [e['id'] for e in active.values()],
             'not_admitted': len(entries) - len(admitted)}
    checkpoint(final)
    return final


async def run(args):
    root, out = args.project.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (out / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Same HLE block lock as the original owner: never overlap two HLE controllers.
    block = (root / 'artifacts/runs/base_model_block.lock').open('a')
    fcntl.flock(block, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (out / 'questions').mkdir(exist_ok=True)
    protocol_path = root / 'configs/eval/protocol_v2_unified64k8k.json'
    protocol = json.loads(protocol_path.read_text())
    cfg, generation = protocol['benchmarks']['hle'], protocol['generation_default']
    assert cfg['question_walltime_seconds'] == 300 and generation['max_tokens'] == 8192
    system = (root / cfg['system_prompt']).read_text().rstrip('\n')
    original_config = json.loads((args.source / 'run_config.json').read_text())
    manifest = json.loads((out / 'manual_retry_manifest.json').read_text())
    route = json.loads(args.route_file.read_text())
    endpoint = route['endpoint']
    concurrency = route.get('solver_concurrency', 8)
    assert concurrency == 8  # Only engine max_num_seqs changes in this handoff.
    import pyarrow.parquet as pq
    data = root / 'artifacts/benchmarks/hle' / cfg['dataset_revision'] / 'test-00000-of-00001.parquet'
    rows = pq.read_table(data, columns=['id', 'question', 'image']).to_pylist()
    questions = {r['id']: r for r in rows}
    assert len(questions) == 2500
    order = json.loads((root / cfg['task_manifest']).read_text())['task_ids']
    by_id = {e['id']: e for e in manifest['selected']}
    entries = [by_id[i] for i in order if i in by_id]
    metadata = {'pid': os.getpid(), 'endpoint': endpoint, 'protocol_sha256': original_config['protocol_sha256'],
                'runner': str(Path(__file__).resolve()), 'selected': len(entries),
                'original_retained': len(manifest['retained']), 'concurrency': concurrency, 'question_walltime_seconds': 300,
                'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'network': 'Direct80-to-HPC forwarding; no local laptop dependency when provisioned.'}
    save(out / 'repair_config.json', metadata)
    if args.prepare_only:
        print(json.dumps({'prepared': len(entries), 'retained': len(manifest['retained']), 'model_requests': 0}))
        return
    entries = [e for e in entries if not (out / 'questions' / (e['id'] + '.json')).exists()]
    # A journal without a terminal record may have generated: never silently resume it.
    for entry in entries:
        if (out / 'questions' / (entry['id'] + '.started.json')).exists():
            raise RuntimeError('Interrupted manual trial requires audit: ' + entry['id'])
    headers = {'Authorization': 'Bearer ' + args.key_file.read_text().strip()}
    async with httpx.AsyncClient(base_url=endpoint.rstrip('/'), headers=headers, trust_env=False,
                                transport=httpx.AsyncHTTPTransport(retries=0),
                                limits=httpx.Limits(max_connections=10)) as client:
        async def healthy():
            try:
                return (await client.get('/health', timeout=3)).status_code == 200
            except httpx.HTTPError:
                return False

        async def request(path, payload, deadline, attempts):
            for number in (1, 2):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('shared300s solver deadline')
                receipt = {'path': path, 'attempt': number}
                attempts.append(receipt)
                try:
                    response = await client.post(path, json=payload, timeout=remaining)
                    receipt['http_status'] = response.status_code
                    if (response.status_code == 429 and number == 1 and
                            response.headers.get('x-apex-generation-started') == 'false'):
                        continue
                    response.raise_for_status()
                    return response.json()
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    receipt['connection_failure'] = type(exc).__name__
                    if number == 2:
                        raise

        async def solve(entry):
            question = questions[entry['id']]
            started = time.monotonic()
            record = {'id': entry['id'], 'is_image': bool(question['image']), 'mode': 'formal',
                      'manual_retry_index': entry['manual_retry_index'], 'original_result': entry['original_result'],
                      'prior_retry_result': entry.get('prior_retry_result'),
                      'infrastructure_retry_reason': entry.get('infrastructure_retry_reason'),
                      'status': 'failed', 'attempts': [],
                      'started_at_utc': datetime.now(timezone.utc).isoformat()}
            result_path = out / 'questions' / (entry['id'] + '.json')
            save(result_path.with_suffix('.started.json'), {'id': entry['id'], 'pid': os.getpid(),
                 'started_at_utc': record['started_at_utc'], 'manual_retry_index': entry['manual_retry_index']})
            try:
                async with asyncio.timeout(300):
                    content = [{'type': 'text', 'text': question['question']}]
                    if question['image']:
                        content.append({'type': 'image_url', 'image_url': {'url': question['image']}})
                    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}]
                    template = {'enable_thinking': False, 'preserve_thinking': False}
                    deadline = started + 300
                    count = await request('/tokenize', {'model': 'apex-qwen', 'messages': messages,
                                          'chat_template_kwargs': template}, deadline, record['attempts'])
                    record['prompt_tokens_exact'] = count['count']
                    assert count['max_model_len'] == 65536
                    if count['count'] + 8192 > 65536:
                        record['status'] = 'context_overflow'
                    else:
                        payload = {k: v for k, v in generation.items() if k not in {'sampling_seed', 'scope'}}
                        payload.update(model='apex-qwen', messages=messages,
                                       seed=generation['sampling_seed'], chat_template_kwargs=template)
                        response = await request('/v1/chat/completions', payload, deadline, record['attempts'])
                        record['raw_response'] = response
                        save(result_path, record)  # Freeze a received answer before validation/cleanup.
                        choice = response['choices'][0]
                        message = choice['message']
                        record.update(response=message.get('content'), usage=response['usage'],
                                      finish_reason=choice['finish_reason'])
                        assert response['usage']['prompt_tokens'] == count['count']
                        assert response['usage']['completion_tokens'] <= 8192
                        assert not message.get('reasoning') and not message.get('reasoning_content')
                        assert isinstance(record['response'], str)
                        record['status'] = 'completed'
            except asyncio.CancelledError:
                record.update(error_type='CancelledError', infrastructure_failure=True,
                              error='Cancelled after block infrastructure failure; explicit audit before retry.')
                raise
            except Exception as exc:
                record.update(error_type=type(exc).__name__, error=str(exc)[:300])
                if isinstance(exc, httpx.TransportError) and time.monotonic() - started < 299:
                    record['infrastructure_failure'] = True
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
                    record['infrastructure_failure'] = True
            finally:
                record.update(elapsed_seconds=round(time.monotonic() - started, 4),
                              finished_at_utc=datetime.now(timezone.utc).isoformat())
                save(result_path, record)
            return record

        def checkpoint(state):
            state['at_utc'] = datetime.now(timezone.utc).isoformat()
            save(out / 'checkpoint.json', state)
            selected = []
            for item in manifest['retained'] + manifest['selected']:
                path = out / 'questions' / (item['id'] + '.json')
                chosen = path if item.get('generate') and path.exists() else Path(item['original_result'])
                selected.append({'id': item['id'], 'path': str(chosen),
                    'manual_retry_index': item['manual_retry_index'],
                    'manual_result_pending': bool(item.get('generate') and chosen != path)})
            selection = {'expected': 2500, 'selection_rule': manifest['selection_rule'], 'entries': selected}
            save(out / 'first_valid_selection.json', selection)
            save(args.canonical_retry / 'first_valid_selection.json', selection)

        summary = await bounded_queue(entries, solve, healthy, checkpoint, concurrency=concurrency,
                                      stop_admission_file=out / "STOP_ADMISSION")
    save(out / 'summary.json', {**summary, 'expected_questions': 2500,
         'original_retained': len(manifest['retained']), 'selected_for_generation': len(manifest['selected']), 'grading': 'not run'})
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in summary.items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--route-file', type=Path, required=True)
    parser.add_argument('--canonical-retry', type=Path, required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    os.umask(0o077)
    asyncio.run(run(parser.parse_args()))
