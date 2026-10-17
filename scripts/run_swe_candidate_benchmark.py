"""Run the lower-LR SWE candidate on the complete fixed HARD51."""
import argparse
import asyncio
from collections import deque
from datetime import datetime, timezone
import fcntl
from functools import partial
import json
import os
from pathlib import Path
import sys

import httpx

import run_swe_baseline_v2_native as native
from collect_swe_final import score
from release_validation_cpus import base_scopes
from swe_baseline_v2 import ROOT, save_json
from swe_logged_model_bridge import LoggedSweModelBridge


def now():
    return datetime.now(timezone.utc).isoformat()


def service_safe(config):
    return (datetime.fromisoformat(config['service_ends']) - datetime.now(timezone.utc)).total_seconds() >= 2100


def configure_native(model, musl):
    original = native.trial_config
    native.SweModelBridge = partial(LoggedSweModelBridge, model=model)

    def trial_config(task, *pos, **kwargs):
        config = original(task, *pos, **kwargs)
        phase = pos[1] if len(pos) > 1 else kwargs['phase']
        if phase == 'generation':
            # LoggedRelay checks the incoming alias before its request validator.
            config.agent.model_name = 'openai/' + model
        if task.name in musl:
            config.environment.import_path = ('swe_clean_musl_runtime:SweCleanMuslScoreEnvironment'
                if phase == 'replay' else 'swe_clean_musl_runtime:SweCleanMuslRuntimeEnvironment')
        else:
            config.environment.import_path = 'swe_clean_glibc_runtime:SweCleanGlibcRuntimeEnvironment'
            if phase == 'replay' and task.name.startswith(('instance_flipt-io__', 'instance_future-architect__')):
                config.environment.import_path = 'swe_clean_glibc_runtime:SweCleanGlibcGoRuntimeEnvironment'
        return config

    native.trial_config = trial_config


async def observe_serving(config, output):
    names = ('vllm:num_requests_running', 'vllm:num_requests_waiting',
             'vllm:kv_cache_usage_perc', 'vllm:gpu_cache_usage_perc', 'vllm:num_preemptions_total')
    async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
        while True:
            record = {'at': now(), 'scope': 'Native service-wide metrics during expert production',
                'native_service_log_hpc': config['native_service_log_hpc']}
            try:
                response = await client.get(config['endpoint'].rstrip('/') + '/metrics')
                response.raise_for_status()
                record['native_metric_lines'] = [line for line in response.text.splitlines()
                    if line.startswith(names)]
            except httpx.HTTPError as error:
                record['metrics_read_error_type'] = type(error).__name__
            save_json(output / 'serving_metrics.json', record)
            with (output / 'serving_metrics.jsonl').open('a') as log:
                log.write(json.dumps(record) + '\n')
            await asyncio.sleep(30)


async def main(args):
    config = json.loads(args.config.read_text())
    assert config['model'] == 'apex-val-swe-lr2e5-max32k'
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
        save_json(output / 'audit' / (task.name + '.expert-outcome.json'), {'state': state, 'at': now()})
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

    checkpoint('waiting_permanent_cpu_release')
    while True:
        if (output / 'STOP_ADMISSION').exists():
            checkpoint('stopped_admission')
            return
        if not service_safe(config):
            checkpoint('service_expiring')
            return
        marker = ROOT / config['cpu_release_marker']
        released = json.loads(marker.read_text()) if marker.is_file() else {}
        if (released.get('ready') is True
                and released.get('cpu_consumers_finished') is True
                and not base_scopes(set(config['cpu_ids']))):
            break
        await asyncio.sleep(15)
    save_json(output / 'admission-opened.json', {'at': now(), 'cpu_ids': config['cpu_ids'],
        'permanent_marker': config['cpu_release_marker'], 'independent_task_validation_required': False,
        'base_scopes_on_target_cpus': [], 'max_parallel': len(config['cpu_ids'])})

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
                outcome = output / 'audit' / (name + '.expert-outcome.json')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--single-task')
    parser.add_argument('--single-cpu', type=int)
    parser.add_argument('--prepare-only', action='store_true')
    asyncio.run(main(parser.parse_args()))
