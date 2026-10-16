"""Run frozen AVG64 on fixed HARD51 after every SWE-expert CPU consumer drains."""
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
from release_validation_cpus import base_scopes
from swe_baseline_v2 import ROOT, save_json


from run_swe_expert_benchmark import configure_native, observe_serving, now, service_safe


def expert_drained(config):
    output = ROOT / config['wait_for_swe_output']
    checkpoint_path = output / 'checkpoint.json'
    model_path = output / 'model-consumer-finished.json'
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {}
    model = json.loads(model_path.read_text()) if model_path.exists() else {}
    return {
        'ready': (checkpoint.get('model') == 'apex-val-swe249'
                  and checkpoint.get('pending') == [] and checkpoint.get('active') == {}
                  and len(checkpoint.get('terminal', {})) == 51
                  and model.get('model_consumer_finished') is True),
        'source': config['wait_for_swe_output'],
        'pending': len(checkpoint.get('pending', [])),
        'active': len(checkpoint.get('active', {})),
        'terminal': len(checkpoint.get('terminal', {})),
        'model_consumer_finished': model.get('model_consumer_finished') is True,
    }


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
            'base_generation_tasks': 0, 'checkpoint': config['checkpoint']}
        save_json(output / 'checkpoint.json', value)
        save_json(output / 'summary.json', value)
        if not pending and not any(row['phase'] == 'generation' for row in active.values()):
            save_json(output / 'model-consumer-finished.json', {'at': now(), 'model_consumer_finished': True,
                'model': config['model'], 'expected': 51, 'scoring_may_still_be_running': bool(active)})

    checkpoint('waiting_swe_expert_all_cpu_consumers')
    while True:
        if (output / 'STOP_ADMISSION').exists():
            checkpoint('stopped_admission')
            return
        if not service_safe(config):
            checkpoint('service_expiring')
            return
        marker = ROOT / config['cpu_release_marker']
        released = json.loads(marker.read_text()) if marker.is_file() else {}
        prior = expert_drained(config)
        busy = base_scopes(set(config['cpu_ids']))
        acceptance = output / 'service-acceptance.json'
        accepted = acceptance.exists() and json.loads(acceptance.read_text()).get('ready') is True
        save_json(output / 'resource_gate.json', {'at': now(), 'expert': prior, 'busy_scopes': busy, 'endpoint_accepted': accepted})
        if (released.get('ready') is True
                and released.get('cpu_consumers_finished') is True
                and prior['ready'] and accepted and not busy):
            break
        await asyncio.sleep(15)
    save_json(output / 'admission-opened.json', {'at': now(), 'cpu_ids': config['cpu_ids'],
        'permanent_marker': config['cpu_release_marker'], 'independent_task_validation_required': False,
        'base_scopes_on_target_cpus': [], 'swe_expert_all_cpu_and_model_consumers_finished': True,
        'max_parallel': len(config['cpu_ids'])})

    async def worker(cpu):
        async with httpx.AsyncClient(trust_env=False, timeout=3) as client:
            while pending:
                if (output / 'STOP_ADMISSION').exists() or not service_safe(config):
                    return
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

    metrics = asyncio.create_task(observe_serving(config, output))
    try:
        await asyncio.gather(*(worker(cpu) for cpu in config['cpu_ids']))
    finally:
        metrics.cancel()
        await asyncio.gather(metrics, return_exceptions=True)
    checkpoint('service_expiring' if pending and not service_safe(config) else
               'stopped_admission' if pending else 'all51_attempts_finished')
    if not pending and not active:
        while base_scopes(set(config['cpu_ids'])):
            checkpoint('draining_cpu_scopes')
            await asyncio.sleep(5)
        checkpoint('all51_attempts_finished')
        save_json(output / 'all_cpu_consumers_finished.json', {
            'at': now(), 'state': 'finished', 'all_cpu_consumers_finished': True,
            'cpu_consumers_finished': True, 'model_consumer_finished': True,
            'model': config['model'], 'attempted': len(terminal), 'expected': 51,
            'active': {}, 'pending': [], 'cpu_ids': config['cpu_ids'], 'remaining_cpu_scopes': [],
            'benchmark_complete': json.loads((output / 'summary.json').read_text())['complete'],
            'invalid_scores_remain_disclosed': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--single-task')
    parser.add_argument('--single-cpu', type=int)
    parser.add_argument('--prepare-only', action='store_true')
    asyncio.run(main(parser.parse_args()))
