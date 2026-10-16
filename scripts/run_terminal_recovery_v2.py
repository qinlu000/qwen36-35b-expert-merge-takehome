#!/usr/bin/env python3
"""445 explicit admissions: approved infrastructure retry1 and untouched first0."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics

import httpx

from harbor.models.trial.config import TrialConfig, TaskConfig
from harbor.models.job.config import JobConfig
from harbor.job_plan import JobPlan
from harbor.trial.trial import Trial
import terminal_recovery_v2 as recovery


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj, indent=2) + '\n')
    temporary.replace(path)


def valid_result(result):
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (result.get('exception_info') or {}).get('exception_type')
    # Normal solver budget/program failures remain valid scored attempts.
    # Infrastructure/cancellation cannot become a valid zero by accident.
    return (isinstance(reward, (int, float)) and reward in (0, 1) and
            exception in (None, 'AgentTimeoutError', 'ContextBudgetExceeded',
                          'NonZeroAgentExitCodeError', 'OutputLengthExceededError'))


def result_record(path):
    result = json.loads(path.read_text())
    return {'path': str(path), 'sha256': digest(path),
            'reward': result['verifier_result']['rewards']['reward']}


def trial_name(entry):
    label = 'first' if entry['manual_attempt'] == 0 else 'manual' + str(entry['manual_attempt'])
    return f"{entry['task_id']}__seed{entry['seed']}__{label}"


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--api-key-path', type=Path, required=True)
    parser.add_argument('--concurrency', type=int, choices=range(1, 9), default=8)
    parser.add_argument('--resume-after-bridge-approval', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if not manifest['explicit_manual_infrastructure_authorization']:
        raise ValueError('requires explicit infrastructure authorization')
    entries = manifest['entries']
    expected_keys = {f'{task}/seed{seed}' for seed in range(5) for task in manifest['task_ids']}
    if len(entries) != 445 or {e['key'] for e in entries} != expected_keys:
        raise ValueError('manual manifest must preserve the full445 task/seed denominator')
    if any(e['manual_attempt'] not in (0, 1, 2) for e in entries):
        raise ValueError('at most two explicitly approved manual retries')
    freeze_path = Path(manifest['frozen_source_manifest'])
    if digest(freeze_path) != manifest['frozen_source_manifest_sha256']:
        raise ValueError('frozen source manifest changed')
    freeze = json.loads(freeze_path.read_text())
    runtime = Path(freeze['runtime'])
    for rel, expected in freeze['source_sha256'].items():
        path = runtime / 'scripts' / rel if rel.startswith('harbor/') else runtime / rel
        if digest(path) != expected:
            raise ValueError('old frozen source changed: ' + str(path))
    seed_configs = {}
    for seed, item in manifest['seed_job_configs'].items():
        path = Path(item['path'])
        if digest(path) != item['sha256']:
            raise ValueError('original seed config changed')
        seed_configs[int(seed)] = JobConfig.model_validate_json(path.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output / 'checkpoint.json'
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint['manifest_sha256'] != digest(args.manifest):
            raise ValueError('cannot resume with a different manifest')
        if checkpoint.get('halted') and not args.resume_after_bridge_approval and not args.prepare_only:
            raise ValueError('bridge audit approval required before pending admission resumes')
    else:
        checkpoint = {'manifest_sha256': digest(args.manifest), 'expected_full_scope': 445,
                      'statuses': {}, 'first_valid': {}, 'halted': False}
    statuses = checkpoint['statuses']
    for entry in entries:
        status = statuses.setdefault(entry['key'], {'state': 'pending', 'manual_attempt': entry['manual_attempt']})
        candidates = []
        if entry['manual_attempt']:
            source = Path(entry['original_result'])
            if digest(source) != entry['original_result_sha256']:
                raise ValueError('original result changed: ' + entry['key'])
            original = json.loads(source.read_text())
            if original['task_name'] != entry['task_id'] or original['config']['agent']['kwargs']['seed'] != entry['seed']:
                raise ValueError('manual task/seed mismatch')
            for rel, expected in entry['original_files_sha256'].items():
                if digest(source.parent / rel) != expected:
                    raise ValueError('original artifact changed: ' + entry['key'] + '/' + rel)
            candidates.append(source)
            prior = entry.get('prior_manual_attempts', [])
            if len(prior) != entry['manual_attempt'] - 1:
                raise ValueError('manual retry count/history mismatch')
            for item in prior:
                path = Path(item['result_path'])
                if digest(path) != item['sha256']:
                    raise ValueError('prior manual result changed')
                candidates.append(path)
        for path in candidates:
            if valid_result(json.loads(path.read_text())):
                status.update(state='first_valid_preserved', result_path=str(path))
                checkpoint['first_valid'].setdefault(entry['key'], result_record(path))
                break
        if status['state'] == 'first_valid_preserved':
            continue
        directory = args.output / 'trials' / trial_name(entry)
        result_path = directory / 'result.json'
        if result_path.exists():
            result = json.loads(result_path.read_text())
            status.update(state='valid' if valid_result(result) else 'failed_attempt', result_path=str(result_path))
            if valid_result(result):
                checkpoint['first_valid'].setdefault(entry['key'], result_record(result_path))
        elif directory.exists() or status['state'] == 'admitted':
            status.update(state='incomplete_preserved', trial_dir=str(directory))
            write_json(checkpoint_path, checkpoint)
            raise ValueError('incomplete attempt retained; explicit infrastructure audit/new manifest required')
    breaker = recovery.CircuitBreaker()
    recovery.BREAKER = breaker

    def save():
        checkpoint.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),
                          halted=breaker.event.is_set(), stop_reason=breaker.reason)
        write_json(checkpoint_path, checkpoint)
        seeds = []
        for seed in range(5):
            records = [checkpoint['first_valid'].get(f'{task}/seed{seed}') for task in manifest['task_ids']]
            covered = [r for r in records if r]
            seeds.append({'seed': seed, 'expected': 89, 'valid_covered': len(covered),
                          'complete_score_percent': 100 * sum(r['reward'] for r in covered) / 89 if len(covered) == 89 else None})
        scores = [s['complete_score_percent'] for s in seeds]
        write_json(args.output / 'coverage.json', {
            'expected_trials': 445, 'valid_covered': len(checkpoint['first_valid']), 'seeds': seeds,
            'primary_mean_percent': statistics.mean(scores) if all(s is not None for s in scores) else None,
            'sample_sd_percent': statistics.stdev(scores) if all(s is not None for s in scores) else None,
            'admission_classes': {str(n): sum(e['manual_attempt'] == n for e in entries) for n in (0, 1, 2)},
            'halted': breaker.event.is_set(), 'stop_reason': breaker.reason})
    save()
    if args.prepare_only:
        print(json.dumps({'status': 'prepared', 'scope': len(entries),
                          'retry1': sum(e['manual_attempt'] == 1 for e in entries),
                          'first0': sum(e['manual_attempt'] == 0 for e in entries),
                          'first_valid_preserved': len(checkpoint['first_valid'])}))
        return

    async def execute(entry):
        owner_token = recovery.ACTIVE_ENTRY.set(entry['key'])
        status = statuses[entry['key']]
        if entry['manual_attempt']:
            original = json.loads(Path(entry['original_result']).read_text())
            config = TrialConfig.model_validate(original['config'])
        else:
            config = JobPlan.build_trial_configs(
                seed_configs[entry['seed']], [TaskConfig.model_validate(entry['task_config'])], job_id=None)[0]
        config.trials_dir = args.output / 'trials'
        config.trial_name = trial_name(entry)
        config.job_id = None
        config.agent.import_path = 'terminal_recovery_v2:RecoveryTerminalBaselineV2'
        config.agent.kwargs['api_base'] = args.endpoint
        config.agent.kwargs['api_key_path'] = str(args.api_key_path.resolve())
        result_path = config.trials_dir / config.trial_name / 'result.json'
        try:
            trial = await Trial.create(config)
            if trial.task.checksum != entry['task_checksum']:
                raise ValueError('original task bytes changed')
            result = await trial.run()
            status['state'] = 'valid' if valid_result(result.model_dump(mode='json')) else 'failed_attempt'
        except BaseException as exc:
            status.update(state='cancelled' if isinstance(exc, asyncio.CancelledError) else 'failed_attempt',
                          exception_type=type(exc).__name__)
            if not isinstance(exc, asyncio.CancelledError):
                breaker.trip(f'trial infrastructure exception: {type(exc).__name__}: {exc}')
        finally:
            if result_path.exists():
                result = json.loads(result_path.read_text())
                status['result_path'] = str(result_path)
                if valid_result(result):
                    status['state'] = 'valid'
                    checkpoint['first_valid'].setdefault(entry['key'], result_record(result_path))
                else:
                    status['state'] = 'cancelled' if status['state'] == 'cancelled' else 'failed_attempt'
                    exception = result.get('exception_info') or {}
                    if not breaker.event.is_set():
                        breaker.trip('unscored native result; audit required: ' + str(exception.get('exception_type')))
            else:
                status.update(state='incomplete_preserved', trial_dir=str(result_path.parent))
                breaker.trip('trial result missing; artifacts retained')
            save()
            recovery.ACTIVE_ENTRY.reset(owner_token)

    endpoint = args.endpoint.rstrip('/').removesuffix('/v1')
    headers = {'Authorization': 'Bearer ' + args.api_key_path.read_text().strip()}
    async with httpx.AsyncClient(base_url=endpoint, headers=headers, trust_env=False) as client:
        async def healthy():
            response = await client.get('/health', timeout=1)
            response.raise_for_status()
        summary = await recovery.run_queue(entries, statuses, execute, healthy, breaker, save, args.concurrency)
    checkpoint['queue_summary'] = summary
    save()
    print(json.dumps({'scope': len(entries), 'first_valid': len(checkpoint['first_valid']), **summary}))


if __name__ == '__main__':
    asyncio.run(main())
