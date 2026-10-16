#!/usr/bin/env python3
"""Independent fixed-cohort clean regeneration; retain the historical 5/51."""
import argparse
import asyncio
from collections import deque
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys

import httpx

import run_swe_baseline_v2_native as native
from collect_swe_final import score
from swe_baseline_v2 import ROOT, save_json


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--key-path', type=Path, required=True)
    parser.add_argument('--cpu-ids', type=int, nargs='+', default=[124, 126, 127])
    parser.add_argument('--endpoints', nargs='+', required=True)
    parser.add_argument('--single-task')
    parser.add_argument('--single-cpu', type=int)
    parser.add_argument('--single-endpoint')
    args = parser.parse_args()
    assert len(args.cpu_ids) == len(args.endpoints)
    plan = json.loads(args.plan.read_text())
    ids = plan['task_ids']
    assert len(ids) == len(set(ids)) == 28
    musl = {row['task_id'] for row in plan['entries']
            if 'MuslRootRuntimeEnvironment' in row['original_generation_environment']}
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'audit').mkdir(exist_ok=True)
    original_config = native.trial_config

    def trial_config(task, *pos, **kwargs):
        config = original_config(task, *pos, **kwargs)
        phase = pos[1] if len(pos) > 1 else kwargs['phase']
        if task.name in musl:
            config.environment.import_path = ('swe_clean_musl_runtime:SweCleanMuslScoreEnvironment'
                if phase == 'replay' else 'swe_clean_musl_runtime:SweCleanMuslRuntimeEnvironment')
        else:
            config.environment.import_path = 'swe_clean_glibc_runtime:SweCleanGlibcRuntimeEnvironment'
            if phase == 'replay' and task.name.startswith(('instance_flipt-io__', 'instance_future-architect__')):
                config.environment.import_path = 'swe_clean_glibc_runtime:SweCleanGlibcGoRuntimeEnvironment'
        return config

    native.trial_config = trial_config
    if args.single_task:
        task = output / 'tasks' / args.single_task
        result = await native.run_phase(task, output, 'generation', 1,
            endpoint=args.single_endpoint, key_path=args.key_path, cpu_offset=args.single_cpu)
        status = 'generation_infrastructure_requires_audit'
        if result is not None and result.agent_execution is not None and result.agent_execution.started_at is not None:
            await native.run_phase(task, output, 'replay', 1, cpu_offset=args.single_cpu)
            status = 'generation_and_replay_finished'
        save_json(output / 'audit' / (args.single_task + '.clean-outcome.json'), {'status': status})
        return

    lock = (output / '.controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    metadata = {'experiment_id': plan['experiment_id'], 'task_ids': ids,
        'kind': 'Independent clean repetition of all legacy-environment tasks',
        'historical_score_retained': plan['old_score_unchanged'],
        'cpu_ids': args.cpu_ids, 'endpoints': args.endpoints,
        'serving': 'Shared warm TP2 BF16 maxseq20 services with Terminal; three SWE tasks maximum',
        'seed': 0, 'solver_seconds': 1800, 'cpus_per_task': 1, 'memory_gib': 4,
        'context_tokens': 65536, 'max_output_tokens_per_call': 8192,
        'selection': 'All predetermined 28, including both old successes; no old/new score selection',
        'native_23_retained': True, 'agent': 'LockedMiniSwe / mini-swe-agent2.4.6'}
    frozen = output / 'experiment.json'
    if frozen.exists():
        assert json.loads(frozen.read_text()) == metadata
    else:
        save_json(frozen, metadata)
    save_json(output / 'controller.json', {'pid': os.getpid(),
        'started_at': datetime.now(timezone.utc).isoformat()})
    native.stage_tasks(output, ROOT / 'artifacts/benchmarks/swe-hard51', ids, ids)
    glibc_queue = deque(name for name in ids if name not in musl)
    musl_queue = deque(name for name in ids if name in musl)
    order = []
    while glibc_queue or musl_queue:
        for queue in (glibc_queue, glibc_queue, musl_queue):
            if queue:
                order.append(queue.popleft())
    previous = json.loads((output / 'checkpoint.json').read_text()) if (output / 'checkpoint.json').exists() else {}
    active = previous.get('active', {})
    terminal = previous.get('terminal', {})
    pending = deque(name for name in order if name not in active and name not in terminal)

    def checkpoint(state='running'):
        rows = []
        for name in ids:
            path = output / 'replay' / name / 'result.json'
            rows.append(score(path) if path.exists() else
                        {'task_id': name, 'reward': None, 'invalid_reason': 'not_scored'})
        valid = [row for row in rows if not row['invalid_reason']]
        resolved = sum(row['reward'] == 1 for row in valid)
        summary = {'as_of': datetime.now(timezone.utc).isoformat(), 'state': state,
            'expected': 28, 'valid_scored': len(valid), 'resolved': resolved,
            'complete': len(valid) == 28, 'pending': list(pending),
            'active': active, 'terminal': terminal, 'tasks': rows,
            'primary_score_percent': 100 * resolved / 28 if len(valid) == 28 else None,
            'historical_51_score_unchanged': plan['old_score_unchanged']}
        save_json(output / 'checkpoint.json', summary)
        save_json(output / 'clean28_summary.json', summary)
        original = json.loads((ROOT / 'artifacts/eval/base_swe_v2_20261016_final/final_summary.json').read_text())
        retained = [row for row in original['tasks'] if row['task_id'] not in ids]
        corrected = retained + rows
        corrected_complete = len(valid) == 28 and all(row['status'] == 'valid_scored' for row in retained)
        corrected_resolved = sum(row['reward'] == 1 for row in corrected)
        save_json(output / 'corrected51_summary.json', {
            'as_of': summary['as_of'], 'expected': 51, 'complete': corrected_complete,
            'clean28_valid_scored': len(valid), 'retained_native23': len(retained),
            'resolved': corrected_resolved,
            'primary_score_percent': 100 * corrected_resolved / 51 if corrected_complete else None,
            'selection': 'Replace all fixed legacy28, retain all native23, no reward selection',
            'historical_51_score_unchanged': plan['old_score_unchanged'], 'tasks': corrected})
        generated = sum((output / 'generation' / name / 'result.json').exists() for name in ids)
        no_future_models = not pending and all((output / 'generation' / name / 'result.json').exists()
            or name in terminal for name in ids)
        if no_future_models and not any(row['phase'] == 'generation' for row in active.values()):
            save_json(output / 'model-consumer-finished.json', {
                'model_consumer_finished': True, 'generation_results': generated,
                'output': str(output), 'scoring_may_still_be_running': True})

    async def worker(cpu, endpoint):
        def finish(name):
            outcome = output / 'audit' / (name + '.clean-outcome.json')
            terminal[name] = json.loads(outcome.read_text())['status'] if outcome.exists() else 'worker_infrastructure_requires_audit'
            active.pop(name)
            checkpoint()
            print(json.dumps({'event': 'finished', 'task': name, 'status': terminal[name]}), flush=True)

        inherited = next((name for name, row in active.items() if row['cpu'] == cpu), None)
        if inherited:
            pid = active[inherited]['pid']
            while Path('/proc/' + str(pid)).exists():
                stat = Path('/proc/' + str(pid) + '/stat')
                try:
                    if stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                        break
                except FileNotFoundError:
                    break
                if (output / 'generation' / inherited / 'result.json').exists():
                    active[inherited]['phase'] = 'replay'
                checkpoint()
                await asyncio.sleep(5)
            finish(inherited)
        async with httpx.AsyncClient(trust_env=False, timeout=3) as client:
            while pending:
                try:
                    response = await client.get(endpoint.rstrip('/') + '/health')
                    response.raise_for_status()
                except httpx.HTTPError:
                    checkpoint('waiting_for_endpoint')
                    await asyncio.sleep(10)
                    continue
                if not pending:
                    return
                ready = next((name for name in pending if name not in musl or
                              (output / 'musl-runtime-ready.json').exists()), None)
                if ready is None or (output / 'STOP_ADMISSION').exists():
                    checkpoint('waiting_for_musl_runtime' if ready is None else 'stopping_admission')
                    if (output / 'STOP_ADMISSION').exists():
                        return
                    await asyncio.sleep(5)
                    continue
                pending.remove(ready)
                active[ready] = {'cpu': cpu, 'endpoint': endpoint, 'phase': 'generation'}
                checkpoint()
                print(json.dumps({'event': 'admitted', 'task': ready, 'cpu': cpu, 'endpoint': endpoint}), flush=True)
                environment = dict(os.environ)
                if ready in musl:
                    environment['PATH'] = str(ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim') + ':' + environment['PATH']
                log = (output / 'audit' / (ready + '.controller.log')).open('ab')
                process = await asyncio.create_subprocess_exec(sys.executable, str(Path(__file__).resolve()),
                    *sys.argv[1:], '--single-task', ready, '--single-cpu', str(cpu),
                    '--single-endpoint', endpoint, env=environment, stdout=log, stderr=log)
                active[ready]['pid'] = process.pid
                while process.returncode is None:
                    if (output / 'generation' / ready / 'result.json').exists():
                        active[ready]['phase'] = 'replay'
                    checkpoint()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        pass
                log.close()
                finish(ready)

    checkpoint('starting')
    await asyncio.gather(*(worker(cpu, endpoint) for cpu, endpoint in zip(args.cpu_ids, args.endpoints)))
    checkpoint('finished_selected_cohort')


if __name__ == '__main__':
    asyncio.run(main())
