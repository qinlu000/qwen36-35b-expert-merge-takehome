#!/usr/bin/env python3
"""Resume the fixed445 manifest with16 solver slots and natural admission drain."""
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import statistics

import httpx

from harbor.models.trial.config import TrialConfig, TaskConfig
from harbor.models.job.config import JobConfig
from harbor.job_plan import JobPlan
from harbor.trial.trial import Trial
import terminal_recovery_v2 as recovery
from terminal_admission_rolling_v2 import run_queue


def write_json(path, obj):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj, indent=2) + '\n')
    temporary.replace(path)


from terminal_verifier_evidence import verifier_infra_reason


def valid_result(result):
    if verifier_infra_reason(result): return False
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (result.get('exception_info') or {}).get('exception_type')
    # Normal solver budget/program failures remain valid scored attempts.
    # Infrastructure/cancellation cannot become a valid zero by accident.
    return (isinstance(reward, (int, float)) and reward in (0, 1) and
            exception in (None, 'AgentTimeoutError', 'ContextBudgetExceeded',
                          'NonZeroAgentExitCodeError', 'OutputLengthExceededError'))


def classify_result(result):
    if valid_result(result): return 'valid'
    kind = (result.get('exception_info') or {}).get('exception_type', '')
    if kind.startswith('Verifier') or verifier_infra_reason(result) or 'harbor/verifier/' in ((result.get('exception_info') or {}).get('exception_traceback') or ''): return 'verifier_incomplete'
    if kind == 'CancelledError': return 'cancelled'
    return 'failed_attempt'


def result_record(path):
    result = json.loads(path.read_text())
    return {'path': str(path),
            'reward': result['verifier_result']['rewards']['reward']}


def trial_name(entry):
    label = 'first' if entry['manual_attempt'] == 0 else 'manual' + str(entry['manual_attempt'])
    return f"{entry['task_id']}__seed{entry['seed']}__{label}" + entry.get("physical_setup_suffix", "")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--api-key-path', type=Path, required=True)
    parser.add_argument('--concurrency', type=int, choices=range(1, 17), default=16)
    parser.add_argument('--resume-after-bridge-approval', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--stop-admission-file', type=Path)
    args = parser.parse_args()
    args.stop_admission_file = args.stop_admission_file or args.output / "STOP_ADMISSION"
    manifest = json.loads(args.manifest.read_text())
    if not manifest['explicit_manual_infrastructure_authorization']:
        raise ValueError('requires explicit infrastructure authorization')
    entries = manifest['entries']
    expected_keys = {f'{task}/seed{seed}' for seed in range(5) for task in manifest['task_ids']}
    if len(entries) != 445 or {e['key'] for e in entries} != expected_keys:
        raise ValueError('manual manifest must preserve the full445 task/seed denominator')
    if any(e['manual_attempt'] not in (0, 1, 2) for e in entries):
        raise ValueError('at most two explicitly approved manual retries')
    seed_configs = {}
    for seed, item in manifest['seed_job_configs'].items():
        path = Path(item['path'])
        seed_configs[int(seed)] = JobConfig.model_validate_json(path.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output / 'checkpoint.json'
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get('halted') and not args.resume_after_bridge_approval and not args.prepare_only:
            raise ValueError('bridge audit approval required before pending admission resumes')
    else:
        checkpoint = {'manifest_path': str(args.manifest), 'expected_full_scope': 445,
                      'statuses': {}, 'first_valid': {}, 'halted': False}
    for key,record in list(checkpoint['first_valid'].items()):
        prior=json.loads(Path(record['path']).read_text())
        reason=verifier_infra_reason(prior)
        if reason:
            checkpoint.setdefault('invalidated_previous_claims',{})[key]={'original_first_valid':record,'reason':reason,'original_result_retained':True}
            checkpoint['first_valid'].pop(key)
            checkpoint['statuses'][key].update(state='verifier_incomplete',unscored_reason=reason)
    statuses = checkpoint['statuses']
    for entry in entries:
        status = statuses.setdefault(entry['key'], {'state': 'pending', 'manual_attempt': entry['manual_attempt']})
        candidates = []
        if entry['manual_attempt']:
            source = Path(entry['original_result'])
            original = json.loads(source.read_text())
            if original['task_name'] != entry['task_id'] or original['config']['agent']['kwargs']['seed'] != entry['seed']:
                raise ValueError('manual task/seed mismatch')
            candidates.append(source)
            prior = entry.get('prior_manual_attempts', [])
            if len(prior) != entry['manual_attempt'] - 1:
                raise ValueError('manual retry count/history mismatch')
            for item in prior:
                path = Path(item['result_path'])
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
            status.update(state=classify_result(result), result_path=str(result_path))
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

    enable_secondary=Path(__file__).resolve().parent.parent/'ENABLE_SECOND_REPLICA'
    endpoint_load={args.endpoint:0,'http://127.0.0.1:28084':0}
    secondary_enabled=False
    def enabled():
        nonlocal secondary_enabled
        secondary_enabled=secondary_enabled or enable_secondary.exists()
        return secondary_enabled

    def secondary_remaining():
        if not enabled():return -1
        try:
            value=json.loads(enable_secondary.read_text())['hpc']['end_time']
            end=datetime.fromisoformat(value.replace('Z','+00:00'))
            if end.tzinfo is None:end=end.replace(tzinfo=timezone(timedelta(hours=8)))
            return (end-datetime.now(timezone.utc)).total_seconds()
        except (OSError,ValueError,KeyError,TypeError):return -1

    def capacity():
        return 30 if secondary_remaining()>=35*60 else min(30,16+endpoint_load['http://127.0.0.1:28084'])

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
        config.environment.import_path = 'terminal_rolling_environment:TerminalRollingEnvironment'
        config.environment.kwargs.update(baseline_cpu_offset=0, baseline_cpu_slots=16)
        config.agent.import_path = 'terminal_recovery_v2:RecoveryTerminalBaselineV2'
        selected=min(endpoint_load,key=endpoint_load.get) if secondary_remaining()>=35*60 else args.endpoint
        endpoint_load[selected]+=1
        config.agent.kwargs['api_base'] = selected
        status['fixed_model_endpoint']=selected
        config.agent.kwargs['api_key_path'] = str(args.api_key_path.resolve())
        result_path = config.trials_dir / config.trial_name / 'result.json'
        try:
            trial = await Trial.create(config)
            result = await trial.run()
            status['state'] = classify_result(result.model_dump(mode='json'))
        except BaseException as exc:
            status.update(state='cancelled' if isinstance(exc, asyncio.CancelledError) else 'failed_attempt',
                          exception_type=type(exc).__name__)
            # Per-item errors remain isolated; model transport/health owns the circuit.
        finally:
            if result_path.exists():
                result = json.loads(result_path.read_text())
                status['result_path'] = str(result_path)
                if valid_result(result):
                    status['state'] = 'valid'
                    checkpoint['first_valid'].setdefault(entry['key'], result_record(result_path))
                else:
                    status['state'] = classify_result(result)
                    exception = result.get('exception_info') or {}
                    if result.get('agent_execution') is None and any(reason in exception.get('exception_message', '') for reason in ('No space left on device', 'Namespace relay exited')):
                        args.stop_admission_file.write_text(exception.get('exception_message', '') + '\n')
                    status['unscored_reason'] = exception.get('exception_type') or verifier_infra_reason(result)
            else:
                status.update(state='incomplete_preserved', trial_dir=str(result_path.parent))
                status['unscored_reason'] = 'trial result missing; artifacts retained'
            save()
            endpoint_load[selected]-=1
            recovery.ACTIVE_ENTRY.reset(owner_token)

    endpoint = args.endpoint.rstrip('/').removesuffix('/v1')
    headers = {'Authorization': 'Bearer ' + args.api_key_path.read_text().strip()}
    async with httpx.AsyncClient(base_url=endpoint, headers=headers, trust_env=False) as client:
        async def healthy():
            response = await client.get('/health', timeout=1)
            response.raise_for_status()
            remaining=secondary_remaining()
            if remaining>0 and (remaining>=35*60 or endpoint_load['http://127.0.0.1:28084']):
                second=await client.get('http://127.0.0.1:28084/health',timeout=1)
                second.raise_for_status()
        summary = await run_queue(entries, statuses, execute, healthy, breaker, save, 30, args.stop_admission_file, capacity=capacity)
    checkpoint['queue_summary'] = summary
    if summary['drained']:
        write_json(args.output / 'nextpoint.json', {'at_utc': datetime.now(timezone.utc).isoformat(),
            'active': 0, 'checkpoint': str(checkpoint_path), 'pending_keys': [key for key, status in statuses.items() if status['state'] == 'pending'],
            'first_valid_keys': list(checkpoint['first_valid']), 'summary': summary})
    save()
    print(json.dumps({'scope': len(entries), 'first_valid': len(checkpoint['first_valid']), **summary}))


if __name__ == '__main__':
    asyncio.run(main())
