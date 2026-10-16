"""Run Base100 then SWE249100 on existing source dev, as CPU slots become available."""
import argparse
import asyncio
from datetime import datetime, timezone
import fcntl
from functools import partial
import json
import os
from pathlib import Path
import subprocess
import sys

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
import run_swe_baseline_v2_native as native
from swe_baseline_v2 import ROOT, save_json
from swe_logged_model_bridge import LoggedSweModelBridge
from release_validation_cpus import base_scopes


def now():
    return datetime.now(timezone.utc).isoformat()


def service_safe(args):
    return (args.service_ends - datetime.now(timezone.utc)).total_seconds() >= 2100


def direct_finished(path):
    blocks = ['base_hle', 'base_asi', 'hle16', 'hle250', 'asi128']
    return all((path / label / 'summary.json').exists() and
               json.loads((path / label / 'summary.json').read_text())['saved'] == (100 if 'hle' in label else 20)
               for label in blocks)


def released_cpus(marker):
    if not marker.is_file():
        return False
    record = json.loads(marker.read_text())
    if not record.get('ready') or not record.get('cpu_consumers_finished'):
        return False
    return not base_scopes(set(range(16)))


def score(path):
    if not path.is_file():
        return {'reward': None, 'state': 'not_scored'}
    result = json.loads(path.read_text())
    rewards = (result.get('verifier_result') or {}).get('rewards') or {}
    reward = rewards.get('reward')
    exception = result.get('exception_info')
    return {'reward': reward if not exception else None,
            'state': 'valid_scored' if reward in (0, 1) and not exception else 'infrastructure_invalid',
            'exception': exception}


async def prefetch(args, rows):
    tools = ROOT / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin/apptainer'
    logdir = args.output / 'image_logs'
    logdir.mkdir(exist_ok=True)
    states = {}
    environment = dict(os.environ, APPTAINER_CACHEDIR=str(args.output / 'image_cache'),
                       APPTAINER_TMPDIR=str(args.output / 'image_tmp'),
                       GOMAXPROCS='1', OMP_NUM_THREADS='1',
                       APPTAINER_MKSQUASHFS_PROCS='1', GODEBUG='http2client=0',
                       HTTP_PROXY='http://127.0.0.1:38080', HTTPS_PROXY='http://127.0.0.1:38080',
                       http_proxy='http://127.0.0.1:38080', https_proxy='http://127.0.0.1:38080')
    for key in ['APPTAINER_CACHEDIR', 'APPTAINER_TMPDIR']:
        Path(environment[key]).mkdir(parents=True, exist_ok=True)
    for row in rows:
        image = Path(row['sif'])
        if image.is_file():
            states[row['task_name']] = {'state': 'ready_existing', 'bytes': image.stat().st_size}
            save_json(args.output / 'image_status.json', states)
            continue
        temporary = image.with_suffix('.partial.sif')
        with (logdir / (row['task_name'] + '.log')).open('ab') as log:
            for attempt in (1, 2):
                temporary.unlink(missing_ok=True)
                states[row['task_name']] = {'state': 'pulling', 'attempt': attempt, 'at': now()}
                save_json(args.output / 'image_status.json', states)
                process = await asyncio.create_subprocess_exec(
                    'taskset', '-c', '125', str(tools), 'pull', '--arch', 'amd64',
                    str(temporary), 'docker://' + row['image_name'],
                    env=environment, stdout=log, stderr=log)
                code = await process.wait()
                if code == 0:
                    temporary.replace(image)
                    break
            states[row['task_name']] = {'state': 'ready' if image.is_file() else 'pull_failed',
                'return_code': code, 'attempts': attempt, 'finished_at': now(),
                'bytes': image.stat().st_size if image.is_file() else None}
            save_json(args.output / 'image_status.json', states)
    save_json(args.output / 'images_finished.json', {'at': now(), 'states': states})


async def replay(args, task, output, patch, cpu, trial_name=None):
    name = trial_name or task.name
    if (output / name / 'result.json').exists():
        return
    if (output / name).exists():
        save_json(output / name / 'interrupted.json', {'at': now(), 'regenerated': False})
        return
    config = TrialConfig.model_validate({
        'task': {'path': str(task)}, 'trial_name': name, 'trials_dir': str(output),
        'agent': {'import_path': 'swe_validation_runtime:SweValidationReplayAgent',
                  'model_name': 'replay', 'override_timeout_sec': 300,
                  'kwargs': {'patch_path': str(patch)}},
        'verifier': {'override_timeout_sec': 3000},
        'environment': {**native.environment_config(1, cpu_offset=cpu),
            'import_path': 'swe_score_bootstrap_runtime:SweScoreBootstrapRuntimeEnvironment'}})
    trial = await Trial.create(config)
    await trial.run()


async def block(args, rows, label, model):
    output = args.output / label
    output.mkdir(exist_ok=True)
    (output / 'audit').mkdir(exist_ok=True)
    native.SweModelBridge = partial(LoggedSweModelBridge, model=model)
    original = native.trial_config

    def configure(*pos, **kwargs):
        config = original(*pos, **kwargs)
        config.environment.import_path = 'swe_score_bootstrap_runtime:SweScoreBootstrapRuntimeEnvironment'
        config.verifier.disable = True
        return config

    native.trial_config = configure
    active, finished = {}, {}
    pending = [row for row in rows if not (output / 'replay' / row['task_name'] / 'result.json').exists()]
    workers = {}

    def checkpoint():
        results = {row['task_name']: score(output / 'replay' / row['task_name'] / 'result.json') for row in rows}
        valid = sum(row['state'] == 'valid_scored' for row in results.values())
        resolved = sum(row['reward'] == 1 for row in results.values())
        save_json(output / 'summary.json', {'at': now(), 'model': model, 'expected': 100,
            'valid_scored': valid, 'resolved': resolved, 'complete': valid == 100,
            'primary_percent': resolved if valid == 100 else None,
            'pending': [row['task_name'] for row in pending], 'active': active,
            'finished': finished, 'results': results,
            'protocol': 'mini2.4.6,1CPU4GiB,1800s,65536/8192,seed0,nonthinking,fresh rebench replay'})

    async def worker(cpu):
        while pending:
            if cpu == 125 and expanded:
                return
            if not service_safe(args):
                save_json(args.output / 'service_expiring.json', {'at': now(),
                    'state': 'service_expiring', 'service_ends': args.service_ends.isoformat(),
                    'minimum_remaining_seconds': 2100, 'block': label,
                    'pending': [row['task_name'] for row in pending],
                    'inflight_drains_without_new_admission': True})
                return
            available = next((row for row in pending if Path(row['sif']).is_file()), None)
            if available is None:
                if (args.output / 'images_finished.json').exists():
                    return
                await asyncio.sleep(10)
                continue
            pending.remove(available)
            name = available['task_name']
            task = args.output / 'tasks' / name
            active[name] = {'cpu': cpu, 'phase': 'generation', 'started_at': now()}
            checkpoint()
            result = await native.run_phase(task, output, 'generation', 1,
                endpoint=args.endpoint, key_path=args.key_file, cpu_offset=cpu)
            if result is not None and result.agent_execution is not None and result.agent_execution.started_at:
                active[name]['phase'] = 'replay'
                checkpoint()
                try:
                    await replay(args, task, output / 'replay', output / 'generation' / name / 'agent/model.patch', cpu)
                    finished[name] = 'generation_and_replay_finished'
                except Exception as error:
                    finished[name] = 'replay_infrastructure_invalid'
                    save_json(output / 'audit' / (name + '.replay-error.json'), {
                        'at': now(), 'error_type': type(error).__name__, 'error': str(error)})
            else:
                finished[name] = 'generation_infrastructure_invalid'
            active.pop(name)
            checkpoint()

    expanded = False
    workers[125] = asyncio.create_task(worker(125))
    while any(not worker.done() for worker in workers.values()):
        if not expanded and released_cpus(args.cpu_release_marker):
            # The old CPU125 task drains; 15 new slots keep the transitional peak at16.
            expanded = True
            for cpu in range(15):
                workers[cpu] = asyncio.create_task(worker(cpu))
            save_json(args.output / 'cpu_expansion.json', {'at': now(),
                'permanent_marker': str(args.cpu_release_marker), 'additional_cpus': list(range(15)),
                'initial_cpu': 125, 'max_parallel': 16})
        if expanded and workers[125].done() and 15 not in workers:
            workers[15] = asyncio.create_task(worker(15))
        checkpoint()
        await asyncio.sleep(10)
    await asyncio.gather(*workers.values())
    checkpoint()
    save_json(output / 'block_finished.json', {'at': now(), 'pending_environment_tasks': [row['task_name'] for row in pending]})
    native.trial_config = original


async def main(args):
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / '.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    save_json(args.output / 'controller.json', {'pid': os.getpid(), 'started_at': now(),
        'initial_cpu': 125, 'initial_parallel': 1, 'max_parallel': 16,
        'models': ['apex-val-base', 'apex-val-swe249'], 'tasks_each': 100,
        'wait_for_direct': str(args.direct_output), 'cpu_release_marker': str(args.cpu_release_marker),
        'service_ends': args.service_ends.isoformat(), 'admission_minimum_remaining_seconds': 2100})
    rows = json.loads((args.output / 'manifest.json').read_text())
    image_task = asyncio.create_task(prefetch(args, rows))
    click = next(row for row in rows if row['instance_id'] == 'pallets__click-1852')
    await replay(args, args.output / 'tasks' / click['task_name'], args.output / 'environment_acceptance_v2',
                 args.output / 'gold_patches' / (click['task_name'] + '.patch'), 125)
    acceptance = score(args.output / 'environment_acceptance_v2' / click['task_name'] / 'result.json')
    save_json(args.output / 'environment_acceptance.json', {'at': now(), 'task': click['instance_id'], **acceptance})
    if acceptance['reward'] != 1:
        save_json(args.output / 'blocked.json', {'at': now(), 'reason': 'first_source_gold_checker_not_passed'})
        await image_task
        return
    while not direct_finished(args.direct_output):
        if not service_safe(args):
            save_json(args.output / 'service_expiring.json', {'at': now(), 'state': 'service_expiring',
                'pending_blocks': ['base100', 'swe249100'], 'model_requests': 0})
            await image_task
            return
        save_json(args.output / 'status.json', {'at': now(), 'state': 'waiting_direct_generation_blocks',
            'first_environment_gold_reward': 1, 'model_requests': 0})
        await asyncio.sleep(15)
    for label, model in [('base', 'apex-val-base'), ('swe249', 'apex-val-swe249')]:
        if not service_safe(args):
            save_json(args.output / 'service_expiring.json', {'at': now(), 'state': 'service_expiring',
                'pending_block': label, 'tasks_in_block': 100})
            await image_task
            return
        await block(args, rows, label, model)
        if (args.output / 'service_expiring.json').exists():
            await image_task
            return
    await image_task
    save_json(args.output / 'finished.json', {'at': now(), 'blocks_finished': ['base', 'swe249']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:28089')
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--direct-output', type=Path, required=True)
    parser.add_argument('--cpu-release-marker', type=Path, required=True)
    parser.add_argument('--service-ends', type=datetime.fromisoformat,
                        default=datetime.fromisoformat('2026-10-17T10:05:32+08:00'))
    asyncio.run(main(parser.parse_args()))
