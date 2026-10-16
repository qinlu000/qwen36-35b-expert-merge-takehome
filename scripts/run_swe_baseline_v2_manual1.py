#!/usr/bin/env python3
"""Fixed HARD51 native mini solve and authoritative fresh-sandbox patch replay."""
import argparse
import asyncio
from collections import deque
from datetime import datetime, timezone
import fcntl
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import tempfile
import tomllib

import httpx

from harbor.models.trial.config import TrialConfig
from harbor.models.trial.result import TrialResult
from harbor.trial.trial import Trial
from swe_baseline_v2 import ROOT, save_json
from swe_manual1_model_bridge import Manual1SweModelBridge as SweModelBridge

ENVIRONMENT_CLASS = 'swe_score_runtime:SweNativeRuntimeEnvironment'

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def environment_config(concurrency, model_socket=None, cpu_offset=64):
    kwargs = {'singularity_image_cache_dir': str(ROOT / 'artifacts/benchmarks/sif'),
              'baseline_cpu_offset': cpu_offset, 'baseline_cpu_slots': concurrency,
              'singularity_startup_timeout_sec': 300}
    if model_socket:
        kwargs['baseline_model_socket'] = str(model_socket)
    return {'import_path': ENVIRONMENT_CLASS,
            'override_cpus': 1, 'override_memory_mb': 4096, 'override_gpus': 0,
            'cpu_enforcement_policy': 'limit', 'memory_enforcement_policy': 'limit', 'kwargs': kwargs}


def trial_config(task, output, phase, concurrency, *, bridge=None, cpu_offset=64):
    if phase == 'generation':
        agent = {'import_path': 'swe_baseline_native_v2:SweBaselineNativeV2', 'model_name': 'openai/apex-qwen',
            'override_timeout_sec': 1800, 'override_setup_timeout_sec': 1800,
            'kwargs': {'version': '2.4.6', 'v2_bridge_id': bridge.identifier},
            'env': {'MSWEA_API_KEY': bridge.relay.agent_token,
                    'OPENAI_API_KEY': bridge.relay.agent_token,
                    'OPENAI_BASE_URL': 'http://127.0.0.1:18000/v1',
                    'OPENAI_API_BASE': 'http://127.0.0.1:18000/v1'}}
    else:
        agent = {'import_path': 'patch_replay:PatchReplayAgent', 'model_name': 'replay',
            'override_timeout_sec': 1800, 'kwargs': {'source_job': str(output / 'generation')}}
    return TrialConfig.model_validate({'task': {'path': str(task)}, 'trial_name': task.name,
        'trials_dir': str(output / phase), 'agent': agent,
        'verifier': {'override_timeout_sec': 3000},
        'environment': environment_config(concurrency, bridge.relay.socket_path if bridge else None, cpu_offset)})


async def run_phase(task, output, phase, concurrency, *, endpoint=None, key_path=None, cpu_offset=64):
    directory = output / phase / task.name
    result_path = directory / 'result.json'
    journal = output / 'audit' / (task.name + '.' + phase + '.started.json')
    if result_path.exists():
        return TrialResult.model_validate_json(result_path.read_text())
    if journal.exists() or directory.exists():
        save_json(output / 'audit' / (task.name + '.' + phase + '.interrupted.json'), {
            'task': task.name, 'phase': phase, 'status': 'interrupted_attempt_retained',
            'regenerated': False, 'trial_dir': str(directory)})
        return None
    save_json(journal, {'task': task.name, 'phase': phase,
                      'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        if phase == 'generation':
            relay_dir = Path(tempfile.mkdtemp(prefix='swe-v2-'))
            try:
                with SweModelBridge(relay_dir / 'm.sock', endpoint, key_path,
                                    output / 'requests' / task.name) as bridge:
                    trial = await Trial.create(trial_config(task, output, phase, concurrency,
                                                           bridge=bridge, cpu_offset=cpu_offset))
                    return await trial.run()
            finally:
                shutil.rmtree(relay_dir)
        trial = await Trial.create(trial_config(task, output, phase, concurrency, cpu_offset=cpu_offset))
        return await trial.run()
    except Exception as error:
        save_json(output / 'audit' / (task.name + '.' + phase + '.driver-error.json'), {
            'error_type': type(error).__name__, 'error': str(error), 'regenerated': False})
        return None


def stage_tasks(output, tasks, ids, admit_ids=None):
    images = {entry['image']: entry for entry in json.loads((ROOT / 'configs/envs/swe_tb_image_digests.json').read_text())}
    progress_path = ROOT / 'artifacts/benchmarks/sif/_prefetch_progress.json'
    progress = json.loads(progress_path.read_text())
    receipts = {entry['image']: entry for entry in progress['results']
                if entry.get('status') in ('cached', 'downloaded', 'completed', 'success')}
    readiness = {}
    for name in ids:
        source = tasks / name
        original = (source / 'task.toml').read_text()
        task_metadata = tomllib.loads(original)
        assert task_metadata['agent']['network_mode'] == 'no-network'
        assert task_metadata['environment']['network_mode'] == task_metadata['verifier']['network_mode'] == 'public'
        image = task_metadata['environment']['docker_image']
        pinned = images[image]
        digest = pinned.get('linux_amd64_manifest_digest', pinned['digest'])
        sif = ROOT / 'artifacts/benchmarks/sif' / (digest.replace(':', '-') + '.sif')
        receipt = receipts.get(image, {})
        eligible = admit_ids is None or name in admit_ids
        # User authorized using the existing pinned download cache immediately;
        # preserve its receipt without rereading hundreds of GB before launch.
        ready = eligible and sif.is_file()
        stage = output / 'tasks' / name
        stage.mkdir(parents=True, exist_ok=True)
        overlay = original.replace('docker_image = ' + json.dumps(image), 'docker_image = ' + json.dumps(str(sif)), 1)
        assert tomllib.loads(overlay)['environment']['docker_image'] == str(sif)
        target = stage / 'task.toml'
        if target.exists() and target.read_text() != overlay:
            raise ValueError('Refuse to alter frozen task metadata: ' + name)
        target.write_text(overlay)
        for child in source.iterdir():
            if child.name != 'task.toml' and not (stage / child.name).exists():
                # Harbor resolves task inputs and rejects links outside this task.
                if child.is_dir():
                    shutil.copytree(child, stage / child.name)
                else:
                    shutil.copyfile(child, stage / child.name)
        readiness[name] = {'ready': ready, 'admission_eligible': eligible,
            'pinned_image': pinned['pinned_image'], 'sif': str(sif),
            'sif_sha256': receipt.get('sif_sha256'), 'image_validation': 'existing pinned cache; prior receipt retained, no rehash',
            'original_task_toml_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'overlay_sha256': hashlib.sha256(overlay.encode()).hexdigest()}
    save_json(output / 'image_readiness.json', readiness)
    return readiness


def aggregate(output, ids):
    entries = []
    for name in ids:
        item = {'task_id': name, 'initial_reward': None, 'replay_reward': None}
        for phase, key in [('generation', 'initial_reward'), ('replay', 'replay_reward')]:
            path = output / phase / name / 'result.json'
            if path.exists():
                result = json.loads(path.read_text())
                rewards = (result.get('verifier_result') or {}).get('rewards') or {}
                item[key] = rewards.get('reward')
                if result.get('exception_info'):
                    item[phase + '_exception'] = result['exception_info']
            if (output / 'audit' / (name + '.' + phase + '.interrupted.json')).exists():
                item[phase + '_interrupted'] = True
        patch = output / 'generation' / name / 'agent/model.patch'
        if patch.is_file():
            item['patch_sha256'], item['patch_bytes'] = sha256(patch), patch.stat().st_size
        entries.append(item)
    resolved = sum(entry['replay_reward'] == 1 for entry in entries)
    covered = sum(entry['replay_reward'] in (0, 1) for entry in entries)
    save_json(output / 'coverage.json', {'expected': len(ids), 'replay_scored': covered, 'resolved': resolved,
        'complete': covered == len(ids), 'primary_score_percent': 100 * resolved / len(ids) if covered == len(ids) else None,
        'conservative_resolved_percent': 100 * resolved / len(ids), 'tasks': entries,
        'report_label': 'SWE Pro V2 HARD-51 / mini2.4.6 / reduced30min / 64K-8K / fresh replay'})


async def main():
    global ENVIRONMENT_CLASS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--key-path', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tasks', type=Path, default=ROOT / 'artifacts/benchmarks/swe-hard51')
    parser.add_argument('--concurrency', type=int, default=8, choices=range(1, 9))
    parser.add_argument('--cpu-offset', type=int, default=64)
    parser.add_argument('--environment-import-path', default=ENVIRONMENT_CLASS)
    parser.add_argument('--model-finished-marker', type=Path)
    parser.add_argument('--engine-max-seqs', type=int, default=8)
    parser.add_argument('--acceptance-receipt', type=Path)
    parser.add_argument('--admit-task-ids', type=Path, required=True,
        help='Explicit prepared subset; the benchmark denominator remains all51')
    parser.add_argument('--config-only', action='store_true')
    args = parser.parse_args()
    ENVIRONMENT_CLASS = args.environment_import_path
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    controller_lock = (args.output / '.swe-controller.lock').open('a+')
    fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    save_json(args.output / 'controller.json', {'pid': os.getpid(),
        'started_at': datetime.now(timezone.utc).isoformat()})
    ids = json.loads((ROOT / 'analysis/source_snapshots/protocol/swe_hard_task_ids.json').read_text())['task_ids']
    admit_ids = json.loads(args.admit_task_ids.read_text())
    assert isinstance(admit_ids, list) and len(admit_ids) == len(set(admit_ids))
    assert admit_ids and set(admit_ids).issubset(ids)
    assert len(ids) == 51 and metadata.version('harbor') == '0.24.0'
    assert sorted(p.name for p in args.tasks.iterdir() if (p / 'task.toml').exists()) == sorted(ids)
    args.output.mkdir(parents=True, exist_ok=True)
    files = ['scripts/run_swe_baseline_v2_manual1.py', 'scripts/swe_baseline_sitepackages_v2.py',
             'scripts/run_swe_baseline_v2_materialized.py', 'scripts/run_swe_baseline_v2.py', 'scripts/swe_baseline_v2.py',
             'scripts/swe_runtime_environment.py', 'scripts/swe_runtime_bootstrap.sh',
             'scripts/swe_runtime_rootmap.sh',
             'scripts/setup_swe_runtime_v2.py', 'artifacts/cache/swe-v2-runtime/manifest.json',
             'scripts/baseline_singularity.py', 'scripts/baseline_netns.py', 'scripts/baseline_exec_limits.py',
             'scripts/asi_fixed_relay.py', 'configs/envs/mini-swe-py312.txt', 'configs/eval/protocol_v2_unified64k8k.json']
    run_metadata = {'scope': 'fixed HARD51; explicit manual infra retry1 for six incomplete tasks only; first valid result', 'task_ids': ids,
        'concurrency': args.concurrency, 'cpu_offset': args.cpu_offset, 'endpoint': args.endpoint,
        'environment_import_path': ENVIRONMENT_CLASS,
        'model_max_num_seqs': args.engine_max_seqs, 'seed': 0, 'generation_attempt': 2, 'manual_infrastructure_retry': 1,
        'admission_task_ids': admit_ids, 'unadmitted_task_ids': [name for name in ids if name not in admit_ids],
        'source_files': files + ['scripts/swe_manual1_model_bridge.py', 'scripts/swe_manual1_relay.py', 'scripts/swe_logged_model_bridge.py', 'scripts/swe_logged_relay.py', 'scripts/swe_baseline_native_v2.py', 'scripts/swe_score_runtime.py']}
    frozen = args.output / 'swe_v2_run.json'
    if frozen.exists() and json.loads(frozen.read_text()) != run_metadata:
        raise ValueError('Cannot change an existing SWE baseline run')
    save_json(frozen, run_metadata)
    readiness = stage_tasks(args.output, args.tasks, ids, admit_ids)
    aggregate(args.output, ids)
    if args.config_only:
        print(json.dumps({'expected': 51, 'images_ready': sum(r['ready'] for r in readiness.values()), 'model_calls': 0}))
        return
    acceptance = json.loads(args.acceptance_receipt.read_text()) if args.acceptance_receipt else {}
    if not all(acceptance.get(key) is True for key in ('native_mini', 'container_runtime_lock',
            'real_endpoint_tokenize', 'cpu_memory_network', 'fresh_patch_replay')):
        raise ValueError('SWE requires native/runtime/network/real-token/replay acceptance')
    async def condition(name):
        if not readiness[name]['ready']:
            return
        task = args.output / 'tasks' / name
        previously_started = (args.output / 'audit' / (name + '.generation.started.json')).exists()
        result = await run_phase(task, args.output, 'generation', args.concurrency, endpoint=args.endpoint,
                                 key_path=args.key_path, cpu_offset=args.cpu_offset)
        if result is None:
            return 'driver_error_or_interrupted_trial_requires_audit'
        if result.exception_info and (result.agent_execution is None or result.agent_execution.started_at is None):
            save_json(args.output / 'audit' / (name + '.pre-model-setup-failed.json'), {
                'task_id': name, 'status': 'environment_setup_failed_without_generation',
                'exception': result.exception_info.model_dump(mode='json'), 'regenerated': False})
            return None
        error = result.exception_info.model_dump(mode='json') if result.exception_info else {}
        execution = result.agent_execution
        elapsed = ((execution.finished_at - execution.started_at).total_seconds()
                   if execution and execution.started_at and execution.finished_at else 0)
        budget_end = (('exit 124' in str(error) and 'timeout' in str(error)) or
                      (elapsed >= 1790 and 'Timeout' in str(error)))
        if budget_end:
            save_json(args.output / 'audit' / (name + '.budget-finished.json'), {
                'task_id': name, 'elapsed_seconds': elapsed, 'status': 'normal_solver_budget_finished',
                'regenerated': False, 'next': 'fresh replay of the captured patch'})
        relay_path = args.output / 'generation' / name / 'agent/v2-relay.json'
        if relay_path.exists() and not previously_started:
            relay = json.loads(relay_path.read_text())
            records = [json.loads(path.read_text()) for path in (args.output / 'requests' / name).glob('*.json')]
            context_overflow = any('context_budget_exceeded' in str(record.get('error', '')) for record in records)
            if not budget_end and not context_overflow and any(event['status'] != 200 for event in relay['events']):
                return 'transport_failure_requires_audit'
        if result is not None:
            await run_phase(task, args.output, 'replay', args.concurrency, cpu_offset=args.cpu_offset)
        aggregate(args.output, ids)
        return None
    pending = deque(name for name in ids if readiness[name]['admission_eligible'])
    active = {}
    admitted = []
    terminal = []
    pause_reason = None
    stop_admission = False
    def checkpoint(state):
        save_json(args.output / 'admission_checkpoint.json', {'state': state, 'reason': pause_reason,
            'admitted_this_session': admitted, 'active': list(active.values()), 'pending': list(pending),
            'terminal': terminal, 'expected': 51, 'seed': 0, 'generation_attempt': 2, 'manual_infrastructure_retry': 1,
            'cpu_ids': list(range(args.cpu_offset, args.cpu_offset + args.concurrency)),
            'model_max_num_seqs': args.engine_max_seqs, 'endpoint': args.endpoint,
            'result_paths': {'generation': str(args.output / 'generation'), 'replay': str(args.output / 'replay')}})
    def models_finished():
        complete = all((args.output / 'generation' / name / 'result.json').exists() for name in admit_ids)
        if complete and args.model_finished_marker and not args.model_finished_marker.exists():
            save_json(args.model_finished_marker, {'model_consumer_finished': True,
                'generation_results': len(admit_ids), 'task_ids': admit_ids,
                'output': str(args.output), 'replay_may_still_be_running': True})
        return complete
    async with httpx.AsyncClient(trust_env=False, timeout=2) as health_client:
        async def healthy():
            try:
                response = await health_client.get(args.endpoint.rstrip('/').removesuffix('/v1') + '/health')
                return response.status_code == 200
            except httpx.HTTPError:
                return False
        try:
            while active or pending:
                stop_admission = (args.output / 'STOP_ADMISSION').exists()
                if not models_finished() and not await healthy():
                    pause_reason = 'endpoint_health_failed'
                    break
                for _ in range(len(pending)):
                    if stop_admission or len(active) >= args.concurrency:
                        break
                    if not models_finished() and not await healthy():
                        pause_reason = 'endpoint_health_failed_before_admission'
                        break
                    name = pending.popleft()
                    readiness[name]['ready'] = Path(readiness[name]['sif']).is_file()
                    if not readiness[name]['ready']:
                        pending.append(name)
                        continue
                    future = asyncio.create_task(condition(name))
                    active[future] = name
                    admitted.append(name)
                    checkpoint('running')
                if pause_reason:
                    break
                if not active:
                    if stop_admission:
                        break
                    checkpoint('waiting_for_images')
                    await asyncio.sleep(5)
                    continue
                done, _ = await asyncio.wait(active, timeout=.5, return_when=asyncio.FIRST_COMPLETED)
                for future in done:
                    name = active.pop(future)
                    failure = future.result()
                    terminal.append({'task_id': name, 'status': failure or 'finished',
                        'result': str(args.output / 'generation' / name / 'result.json')})
                    if failure:
                        pause_reason = str(failure) + ':' + name
                        break
                if pause_reason:
                    break
                checkpoint('stopping_admission' if stop_admission else 'running')
        except BaseException as error:
            pause_reason = 'controller_exception:' + type(error).__name__
            raise
        finally:
            if active:
                for future in active:
                    future.cancel()
                await asyncio.gather(*active, return_exceptions=True)
            aggregate(args.output, ids)
            models_finished()
            checkpoint('paused_infrastructure' if pause_reason else
                       'stopped_admission' if stop_admission else 'finished_available_images')


if __name__ == '__main__':
    asyncio.run(main())
