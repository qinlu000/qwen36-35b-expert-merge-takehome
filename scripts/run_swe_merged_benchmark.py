"""Run fixed AVG64 HARD51 as individual SWE-expert CPU slots permanently drain."""
import argparse
import asyncio
from collections import deque
import fcntl
import json
import os
from pathlib import Path
import sys

import httpx

import run_swe_baseline_v2_native as native
from collect_swe_final import score
from swe_baseline_v2 import ROOT, save_json


from run_swe_expert_benchmark import configure_native, observe_serving, now, service_safe


def base_scopes(cpus):
    busy = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            group = (process / 'cgroup').read_text()
            if (any(prefix in group for prefix in
                    ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and cpus.intersection(os.sched_getaffinity(int(process.name)))):
                busy.add(group.strip().split('/')[-1])
        except (OSError, ProcessLookupError):
            pass
    return sorted(busy)


def expert_release_state(config, ids):
    output = ROOT / config['wait_for_swe_output']
    checkpoint_path = output / 'checkpoint.json'
    model_path = output / 'model-consumer-finished.json'
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {}
    model = json.loads(model_path.read_text()) if model_path.exists() else {}
    active, terminal = checkpoint.get('active', {}), checkpoint.get('terminal', {})
    accounted = (checkpoint.get('model') == 'apex-val-swe249'
                 and checkpoint.get('pending') == []
                 and not set(active).intersection(terminal)
                 and set(active).union(terminal) == set(ids)
                 and all(row.get('cpu') in config['cpu_ids'] for row in active.values()))
    return {
        'permanent_slot_release_possible': accounted,
        'all_source_consumers_finished': (accounted and not active and len(terminal) == 51
            and model.get('model_consumer_finished') is True
            and model.get('model') == 'apex-val-swe249' and model.get('expected') == 51
            and model.get('scoring_may_still_be_running') is False),
        'source': config['wait_for_swe_output'],
        'pending': len(checkpoint.get('pending', [])),
        'active': len(active), 'terminal': len(terminal),
        'active_cpu_ids': sorted({row['cpu'] for row in active.values()}),
        'model_consumer_finished': model.get('model_consumer_finished') is True,
        'scoring_may_still_be_running': model.get('scoring_may_still_be_running'),
        'source_as_of': checkpoint.get('as_of'),
        'source_checkpoint': checkpoint, 'source_model_marker': model,
    }


def claim_released_cpus(config, output, prior, handoffs, candidates, label):
    if not prior['permanent_slot_release_possible']:
        return []
    claimed = []
    snapshot = output / 'source-cpu-release-checkpoints' / (label + '.json')
    for cpu in candidates:
        if cpu in handoffs or cpu in prior['active_cpu_ids'] or base_scopes({cpu}):
            continue
        if not claimed:
            save_json(snapshot, prior['source_checkpoint'])
        handoffs[cpu] = {'cpu': cpu, 'scope_empty_at': now(),
            'source_pending': prior['pending'], 'source_active': prior['active'],
            'source_terminal': prior['terminal'], 'source_active_cpu_ids': prior['active_cpu_ids'],
            'source_checkpoint_as_of': prior['source_as_of'],
            'source_checkpoint_snapshot': str(snapshot.relative_to(ROOT)),
            'actual_scopes_before_avg_admission': [], 'permanent_release': True}
        claimed.append(cpu)
    if claimed:
        save_json(output / 'cpu-handoffs.json', {'schema': 'swe_per_cpu_release_v1',
            'source': config['wait_for_swe_output'],
            'handoffs': [handoffs[cpu] for cpu in sorted(handoffs)]})
    return claimed


def record_source_handoff(config, output, prior, handoffs):
    if not prior['all_source_consumers_finished'] or set(handoffs) != set(config['cpu_ids']):
        return
    busy = base_scopes(set(config['cpu_ids']))
    receipt = output / 'source-expert-consumers-finished.json'
    if not receipt.exists():
        snapshot = output / 'source-cpu-release-checkpoints/full-source-finished.json'
        save_json(snapshot, prior['source_checkpoint'])
        save_json(receipt, {'schema': 'swe_source_cpu_handoff_v1', 'at': now(),
            'source': config['wait_for_swe_output'],
            'source_checkpoint_snapshot': str(snapshot.relative_to(ROOT)),
            'source_terminal': 51, 'source_active': {}, 'source_pending': [],
            'source_model_marker': prior['source_model_marker'],
            'source_all_cpu_and_model_consumers_finished': True,
            'cpu_ids': config['cpu_ids'],
            'per_cpu_release_before_avg_admission': [handoffs[cpu] for cpu in sorted(handoffs)],
            'current_avg_scopes_on_released_cpus': busy,
            'whole_pool_empty_at_this_time': not busy,
            'note': 'Every source CPU was actually scope-empty after permanent release, before AVG use; current AVG scopes are separate.'})
    # This legacy proof is used by the audited collector. Never claim a flat
    # empty pool while the newly admitted AVG consumers are using these CPUs.
    legacy = output / 'admission-opened.json'
    if not legacy.exists() and not busy:
        save_json(legacy, {'at': now(), 'cpu_ids': config['cpu_ids'],
            'permanent_marker': config['cpu_release_marker'],
            'independent_task_validation_required': False,
            'base_scopes_on_target_cpus': [],
            'swe_expert_all_cpu_and_model_consumers_finished': True,
            'source_handoff': str(receipt.relative_to(ROOT)),
            'max_parallel': len(config['cpu_ids'])})


async def main(args):
    config = json.loads(args.config.read_text())
    assert config['model'] == 'apex-avg64'
    output = ROOT / config['output']
    output.mkdir(parents=True, exist_ok=True)
    (output / 'audit').mkdir(exist_ok=True)
    ids = json.loads((ROOT / config['task_manifest']).read_text())['task_ids']
    assert len(ids) == len(set(ids)) == 51
    musl = set(json.loads((ROOT / config['musl_manifest']).read_text()))
    assert len(musl) == 10 and musl.issubset(ids)
    configure_native(config['model'], musl)
    if args.single_task:
        assert args.single_task in ids and args.single_cpu in config['cpu_ids']
        task = output / 'tasks' / args.single_task
        result = await native.run_phase(task, output, 'generation', 1,
            endpoint=config['endpoint'], key_path=ROOT / config['key_file'], cpu_offset=args.single_cpu)
        state = 'generation_infrastructure_requires_audit'
        if result is not None and result.agent_execution is not None and result.agent_execution.started_at:
            await native.run_phase(task, output, 'replay', 1, cpu_offset=args.single_cpu)
            state = 'generation_and_replay_finished'
        save_json(output / 'audit' / (task.name + '.merged-outcome.json'), {'state': state, 'at': now()})
        return

    lock = (output / '.controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    readiness = native.stage_tasks(output, ROOT / 'artifacts/benchmarks/swe-hard51', ids, ids)
    assert all(row['ready'] for row in readiness.values())
    save_json(output / 'experiment.json', dict(config, task_ids=ids, expected=51,
        base_generation_tasks=0, agent_request_model='openai/' + config['model'],
        bridge_allowed_model=config['model'], cached_images_ready=len(readiness),
        task_inputs='Copies of all fixed official HARD51 tasks; only image field points to its pinned cached SIF'))
    save_json(output / 'controller.json', {'pid': os.getpid(), 'started_at': now(),
        'script': str(Path(__file__).resolve()), 'config': str(args.config.resolve())})
    if args.prepare_only:
        return
    previous = json.loads((output / 'checkpoint.json').read_text()) if (output / 'checkpoint.json').exists() else {}
    assert not previous.get('active'), 'Previous active tasks retained; inspect before restarting'
    terminal = previous.get('terminal', {})
    pending = deque(name for name in ids if name not in terminal)
    active = {}
    handoffs = {}

    def checkpoint(state):
        rows = []
        for name in ids:
            path = output / 'replay' / name / 'result.json'
            rows.append(score(path) if path.exists() else
                        {'task_id': name, 'reward': None, 'invalid_reason': 'not_scored'})
        valid = [row for row in rows if not row['invalid_reason']]
        resolved = sum(row['reward'] == 1 for row in valid)
        value = {'as_of': now(), 'state': state, 'model': config['model'],
            'expected': 51, 'valid_scored': len(valid), 'resolved': resolved,
            'complete': len(valid) == 51, 'primary_score_percent': 100 * resolved / 51 if len(valid) == 51 else None,
            'pending': list(pending), 'active': active, 'terminal': terminal, 'tasks': rows,
            'base_generation_tasks': 0, 'checkpoint': config['checkpoint'],
            'leased_cpu_ids': sorted(handoffs), 'max_parallel_tasks': len(handoffs)}
        save_json(output / 'checkpoint.json', value)
        save_json(output / 'summary.json', value)
        if not pending and not any(row['phase'] == 'generation' for row in active.values()):
            save_json(output / 'model-consumer-finished.json', {'at': now(), 'model_consumer_finished': True,
                'model': config['model'], 'expected': 51, 'scoring_may_still_be_running': bool(active)})

    checkpoint('waiting_permanently_released_swe_cpu_slots')
    while True:
        if (output / 'STOP_ADMISSION').exists():
            checkpoint('stopped_admission')
            return
        if not service_safe(config):
            checkpoint('service_expiring')
            return
        marker = ROOT / config['cpu_release_marker']
        released = json.loads(marker.read_text()) if marker.is_file() else {}
        prior = expert_release_state(config, ids)
        acceptance = output / 'service-acceptance.json'
        accepted = acceptance.exists() and json.loads(acceptance.read_text()).get('ready') is True
        if (released.get('ready') is True
                and released.get('cpu_consumers_finished') is True
                and prior['permanent_slot_release_possible'] and accepted):
            initial = claim_released_cpus(config, output, prior, handoffs,
                                          config['cpu_ids'], 'initial')
            if initial:
                save_json(output / 'initial-admission-opened.json', {'at': now(),
                    'cpu_ids': initial, 'initial_max_parallel': len(initial),
                    'source_pending': prior['pending'], 'source_active': prior['active'],
                    'source_terminal': prior['terminal'],
                    'source_active_cpu_ids': prior['active_cpu_ids'],
                    'source_all_consumers_finished': prior['all_source_consumers_finished'],
                    'permanent_marker': config['cpu_release_marker'],
                    'handoffs': str((output / 'cpu-handoffs.json').relative_to(ROOT)),
                    'whole_pool_drain_proof': False})
                record_source_handoff(config, output, prior, handoffs)
                break
        save_json(output / 'resource_gate.json', {'at': now(),
            'source_pending': prior['pending'], 'source_active': prior['active'],
            'source_terminal': prior['terminal'], 'source_active_cpu_ids': prior['active_cpu_ids'],
            'permanent_slot_release_possible': prior['permanent_slot_release_possible'],
            'endpoint_accepted': accepted})
        await asyncio.sleep(15)

    async def worker(cpu):
        async with httpx.AsyncClient(trust_env=False, timeout=3) as client:
            while pending:
                if (output / 'STOP_ADMISSION').exists() or not service_safe(config):
                    return
                if cpu not in handoffs:
                    prior = expert_release_state(config, ids)
                    claim_released_cpus(config, output, prior, handoffs, [cpu], 'cpu-' + str(cpu))
                    record_source_handoff(config, output, prior, handoffs)
                    if cpu not in handoffs:
                        await asyncio.sleep(10)
                        continue
                if base_scopes({cpu}):
                    await asyncio.sleep(10)
                    continue
                try:
                    response = await client.get(config['endpoint'].rstrip('/') + '/health')
                    response.raise_for_status()
                except httpx.HTTPError:
                    checkpoint('waiting_for_model_endpoint')
                    await asyncio.sleep(10)
                    continue
                if not pending:
                    return
                name = pending.popleft()
                active[name] = {'cpu': cpu, 'phase': 'generation', 'started_at': now()}
                checkpoint('running')
                environment = dict(os.environ)
                if name in musl:
                    environment['PATH'] = str(ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim') + ':' + environment['PATH']
                with (output / 'audit' / (name + '.controller.log')).open('ab') as log:
                    child = await asyncio.create_subprocess_exec(sys.executable, str(Path(__file__).resolve()),
                        '--config=' + str(args.config.resolve()), '--single-task=' + name,
                        '--single-cpu=' + str(cpu), env=environment, stdout=log, stderr=log)
                    active[name]['pid'] = child.pid
                    first = output / 'first-admission.json'
                    if not first.exists():
                        save_json(first, {'at': now(), 'model': config['model'],
                            'task_id': name, 'cpu': cpu, 'child_pid': child.pid,
                            'parent_pid': os.getpid(), 'leased_cpu_ids': sorted(handoffs),
                            'solver_seconds': 1800, 'cpus_per_task': 1,
                            'memory_mib': 4096, 'context_tokens': 65536, 'output_tokens': 8192})
                    while child.returncode is None:
                        if (output / 'generation' / name / 'result.json').exists():
                            active[name]['phase'] = 'replay'
                        checkpoint('running')
                        try:
                            await asyncio.wait_for(child.wait(), timeout=10)
                        except TimeoutError:
                            pass
                outcome = output / 'audit' / (name + '.merged-outcome.json')
                terminal[name] = json.loads(outcome.read_text())['state'] if outcome.exists() else 'worker_infrastructure_requires_audit'
                active.pop(name)
                checkpoint('running')

    async def observe_source_handoff():
        while True:
            record_source_handoff(config, output, expert_release_state(config, ids), handoffs)
            await asyncio.sleep(10)

    metrics = asyncio.create_task(observe_serving(config, output))
    source_observer = asyncio.create_task(observe_source_handoff())
    try:
        await asyncio.gather(*(worker(cpu) for cpu in config['cpu_ids']))
    finally:
        metrics.cancel()
        source_observer.cancel()
        await asyncio.gather(metrics, source_observer, return_exceptions=True)
    checkpoint('service_expiring' if pending and not service_safe(config) else
               'stopped_admission' if pending else 'all51_attempts_finished')
    if not pending and not active:
        while True:
            prior = expert_release_state(config, ids)
            claim_released_cpus(config, output, prior, handoffs, config['cpu_ids'],
                                'final-unused-slots-' + str(len(handoffs)))
            record_source_handoff(config, output, prior, handoffs)
            if (prior['all_source_consumers_finished'] and len(handoffs) == len(config['cpu_ids'])
                    and not base_scopes(set(config['cpu_ids']))):
                break
            checkpoint('draining_source_and_avg_cpu_scopes')
            await asyncio.sleep(5)
        checkpoint('all51_attempts_finished')
        save_json(output / 'all_cpu_consumers_finished.json', {
            'at': now(), 'state': 'finished', 'all_cpu_consumers_finished': True,
            'cpu_consumers_finished': True, 'model_consumer_finished': True,
            'model': config['model'], 'attempted': len(terminal), 'expected': 51,
            'active': {}, 'pending': [], 'cpu_ids': config['cpu_ids'], 'remaining_cpu_scopes': [],
            'source_all_consumers_finished': True,
            'source_handoff': str((output / 'source-expert-consumers-finished.json').relative_to(ROOT)),
            'benchmark_complete': json.loads((output / 'summary.json').read_text())['complete'],
            'invalid_scores_remain_disclosed': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--single-task')
    parser.add_argument('--single-cpu', type=int)
    parser.add_argument('--prepare-only', action='store_true')
    asyncio.run(main(parser.parse_args()))
