#!/usr/bin/env python3
"""Run the fixed repair cohort independently, then reuse naturally freed CPUs."""
import argparse
import asyncio
from collections import deque
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import statistics
import sys

import httpx

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from terminal_verifier_evidence import verifier_infra_reason

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
OLD = ROOT / 'artifacts/results/base-terminal-v2-recovery-20261016'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def alive(pid):
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


def label(entry):
    suffix = '__nativeinfra1' if entry.get('native_grade_infrastructure_retry') else ''
    return entry['task_id'] + '__seed' + str(entry['seed']) + '__independent1' + suffix


def grade(path):
    if not path.exists():
        return None
    result = json.loads(path.read_text())
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (result.get('exception_info') or {}).get('exception_type')
    valid = reward in (0, 1) and exception in (None, 'AgentTimeoutError',
        'ContextBudgetExceeded', 'NonZeroAgentExitCodeError', 'OutputLengthExceededError')
    reason = verifier_infra_reason(result)
    return {'path': str(path), 'reward': reward if valid and not reason else None,
            'valid': valid and not reason, 'exception': exception, 'verifier_issue': reason}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--key-path', type=Path, required=True)
    parser.add_argument('--endpoints', nargs='+', required=True)
    parser.add_argument('--old-grader-child', type=int, default=0)
    parser.add_argument('--single-key')
    parser.add_argument('--single-cpu', type=int)
    parser.add_argument('--single-endpoint')
    parser.add_argument('--old-manifest', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    entries = {row['key']: row for row in plan['entries']}
    frozen_keys = set(entries)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    extra = output / 'takeover-entries.json'
    if extra.exists():
        entries.update({row['key']: row for row in json.loads(extra.read_text())['entries']})
    retries = output / 'native-grade-retries.json'
    if retries.exists():
        for row in json.loads(retries.read_text())['entries']:
            assert row['mode'] == 'grade_only' and row['native_grade_infrastructure_retry']
            original = grade(Path(row['retained_grade_result']))
            assert original and not original['valid'] and original['verifier_issue']
            entries[row['key']] = row
    if args.single_key:
        entry = entries[args.single_key]
        directory = output / 'trials' / label(entry)
        if directory.exists():
            raise RuntimeError('Existing attempt retained; no automatic answer regeneration')
        if entry['mode'] == 'grade_only':
            import run_terminal_repair_grade_v2 as grader
            sys.argv = [grader.__file__, '--original-result', entry['original_result'],
                '--restore-manifest', entry['restore_manifest'], '--output', str(directory),
                '--cpu-offset', str(args.single_cpu)]
            await grader.main()
        else:
            base = entry.get('base_trial_config')
            if base is None:
                base = json.loads(Path(entry['original_result']).read_text())['config']
            config = TrialConfig.model_validate(base)
            config.trials_dir, config.trial_name, config.job_id = output / 'trials', label(entry), None
            config.environment.import_path = 'terminal_repair_environment_v2:TerminalRepairEnvironment'
            config.environment.kwargs.update(baseline_cpu_offset=args.single_cpu, baseline_cpu_slots=1)
            config.environment.override_cpus, config.environment.override_memory_mb = 4, 8192
            config.agent.import_path = 'terminal_repair_agent_v2:TerminalRepairAgent'
            config.agent.kwargs.update(api_base=args.single_endpoint, api_key_path=str(args.key_path))
            assert config.agent.kwargs['seed'] == entry['seed']
            config.agent.override_timeout_sec = 1800
            config.verifier.override_timeout_sec = 900
            trial = await Trial.create(config)
            await trial.run()
        return

    lock = (output / '.controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    save(output / 'experiment.json', {'plan_id': plan['plan_id'], 'entries': list(entries.values()),
        'old_run_preserved': True, 'new_generation_experiment': True,
        'selection': 'Entire predetermined unscored cohort; no reward selection',
        'initial_cpu_ids': [120, 121, 122, 123], 'later_cpu_ids': list(range(120)),
        'expansion': 'After original in-flight tasks end and controller lock is free; transfer untouched pending entries',
        'endpoints': args.endpoints, 'model_max_num_seqs': 20,
        'cpus_per_task': 4, 'memory_mb': 8192, 'solver_seconds': 1800, 'verifier_seconds': 900})
    previous = json.loads((output / 'checkpoint.json').read_text()) if (output / 'checkpoint.json').exists() else {}
    active, terminal = previous.get('active', {}), previous.get('terminal', {})
    for key, entry in entries.items():
        if entry.get('native_grade_infrastructure_retry') and key not in active:
            if not (output / 'trials' / label(entry)).exists():
                terminal.pop(key, None)
    pending = deque(sorted((key for key in entries if key not in active and key not in terminal),
                           key=lambda key: entries[key]['mode'] != 'grade_only'))

    def checkpoint():
        scores = {key: grade(output / 'trials' / label(entry) / 'result.json') for key, entry in entries.items()}
        valid = {key: row for key, row in scores.items() if row and row['valid']}
        summary = {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
            'expected': len(entries), 'valid_scored': len(valid), 'active': active,
            'pending': list(pending), 'terminal': terminal, 'scores': scores,
            'complete': len(valid) == len(entries), 'resolved': sum(row['reward'] == 1 for row in valid.values())}
        save(output / 'checkpoint.json', summary)
        old = json.loads((OLD / 'final_summary.json').read_text())
        combined = {key: row for key, row in old['accepted_first_valid'].items() if key not in entries}
        combined.update(valid)
        seeds = []
        for seed in range(5):
            rows = [row for key, row in combined.items() if key.endswith('/seed' + str(seed))]
            seeds.append({'seed': seed, 'valid_scored': len(rows), 'expected': 89,
                'correct': sum(row['reward'] for row in rows),
                'score_percent': 100 * sum(row['reward'] for row in rows) / 89 if len(rows) == 89 else None})
        complete = len(combined) == 445
        values = [row['score_percent'] for row in seeds]
        old_checkpoint = json.loads((OLD / 'checkpoint.json').read_text())
        old_active = sum(row['state'] == 'admitted' for key, row in old_checkpoint['statuses'].items() if key not in entries)
        old_pending = sum(row['state'] == 'pending' for key, row in old_checkpoint['statuses'].items() if key not in entries)
        active_count, pending_count = len(active) + old_active, len(pending) + old_pending
        for row in seeds:
            row['valid_covered'], row['correct_count'] = row['valid_scored'], row['correct']
        save(output / 'corrected445_summary.json', {'updated_at_utc': summary['updated_at_utc'],
            'expected': 445, 'expected_trials': 445, 'valid_scored': len(combined),
            'valid_covered': len(combined), 'active_trials': active_count,
            'pending_not_admitted': pending_count,
            'infrastructure_unscored': 445 - len(combined) - active_count - pending_count,
            'complete': complete, 'accepted_first_valid': combined, 'per_seed': seeds,
            'primary_mean_percent': statistics.mean(values) if complete else None,
            'mean_percent': statistics.mean(values) if complete else None,
            'sample_sd_percent_ddof1': statistics.stdev(values) if complete else None,
            'selection': 'Replace every frozen repair-cohort row; keep other original first-valid rows',
            'original_summary': str(OLD / 'final_summary.json'), 'accepted': combined})
        if not pending and not active:
            save(output / 'model-consumer-finished.json', {'model_consumer_finished': True,
                'benchmark_complete': complete, 'valid_repair_scores': len(valid),
                'scope': 'All fixed repair attempts ended; invalid scoring remains disclosed'})

    async def worker(cpu, index):
        endpoint = args.endpoints[index % len(args.endpoints)]
        inherited = next((key for key, row in active.items() if row['cpu_offset'] == cpu), None)
        if inherited:
            while alive(active[inherited]['pid']):
                checkpoint()
                await asyncio.sleep(5)
            terminal[inherited] = grade(output / 'trials' / label(entries[inherited]) / 'result.json')
            active.pop(inherited)
        async with httpx.AsyncClient(trust_env=False, timeout=3) as client:
            while pending:
                try:
                    (await client.get(endpoint + '/health')).raise_for_status()
                except httpx.HTTPError:
                    await asyncio.sleep(10)
                    continue
                if not pending or (output / 'STOP_ADMISSION').exists():
                    return
                key = pending.popleft()
                entry = entries[key]
                if entry['mode'] == 'grade_only':
                    manifest = json.loads(Path(entry['restore_manifest']).read_text())
                    if not all(Path(row['source']).exists() for row in manifest['files']):
                        pending.append(key)
                        await asyncio.sleep(5)
                        continue
                logfile = output / 'logs' / (label(entry) + '.log')
                logfile.parent.mkdir(exist_ok=True)
                active[key] = {'pid': None, 'cpu_offset': cpu, 'endpoint': endpoint, 'mode': entry['mode']}
                with logfile.open('ab') as log:
                    process = await asyncio.create_subprocess_exec(sys.executable, str(Path(__file__).resolve()),
                        *sys.argv[1:], '--single-key', key, '--single-cpu', str(cpu),
                        '--single-endpoint', endpoint, stdout=log, stderr=log)
                active[key]['pid'] = process.pid
                checkpoint()
                print(json.dumps({'event': 'admitted', 'key': key, **active[key]}), flush=True)
                while process.returncode is None:
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        checkpoint()
                terminal[key] = grade(output / 'trials' / label(entry) / 'result.json')
                active.pop(key)
                checkpoint()
                print(json.dumps({'event': 'finished', 'key': key, 'score': terminal[key]}), flush=True)

    workers = []
    checkpoint()
    while args.old_grader_child and alive(args.old_grader_child):
        await asyncio.sleep(5)
    workers.append(asyncio.create_task(worker(120, 0)))
    pool_lock = None
    while pending or active:
        if pool_lock is None:
            old = json.loads((OLD / 'checkpoint.json').read_text())
            busy = any(row['state'] == 'admitted' for row in old['statuses'].values())
            if not busy:
                candidate = (ROOT / 'artifacts/runs/base-terminal-724242.lock').open('a+')
                try:
                    fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    candidate.close()
                else:
                    pool_lock = candidate
                    from terminal_repair_takeover_v2 import takeover_entries
                    additions = takeover_entries(args.old_manifest, OLD / 'checkpoint.json',
                                                 OLD / 'final_summary.json', set(entries))
                    save(output / 'takeover-entries.json', {'at_utc': datetime.now(timezone.utc).isoformat(),
                        'policy': 'All untouched pending and newly unscored terminal entries; no reward selection',
                        'entries': [row for key, row in entries.items() if key not in frozen_keys] + additions})
                    for entry in additions:
                        entries[entry['key']] = entry
                        pending.append(entry['key'])
                    save(ROOT / 'artifacts/runs/base-terminal-recovery-v2-20261016/model-consumers/terminal-seq20-current-manifest-finished.json', {
                        'model_consumer_finished': True, 'benchmark_complete': False,
                        'reason': 'Original runtime retired; all pending entries transferred to repaired runtime',
                        'transferred_entries': len(additions), 'new_output': str(output),
                        'original_checkpoint_preserved': True})
                    for index, cpu in enumerate(range(0, 120, 4), 1):
                        workers.append(asyncio.create_task(worker(cpu, index)))
                    save(output / 'cpu-handoff.json', {'at_utc': datetime.now(timezone.utc).isoformat(),
                        'original_queue_pending_transferred': sum(row['state'] == 'pending' for row in old['statuses'].values()),
                        'original_queue_active': 0, 'cpu_ids': list(range(124)),
                        'rolling_task_capacity': 31})
        checkpoint()
        for task in workers:
            if task.done() and not task.cancelled() and task.exception() is not None:
                raise task.exception()
        await asyncio.sleep(5)
    await asyncio.gather(*workers)
    checkpoint()


if __name__ == '__main__':
    asyncio.run(main())
