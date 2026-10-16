"""Run the complete Terminal expert experiment after SWE releases the CPU pool."""
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


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def grade(path):
    if not path.exists():
        return None
    result = json.loads(path.read_text())
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    exception = (result.get('exception_info') or {}).get('exception_type')
    reason = verifier_infra_reason(result)
    valid = reward in (0, 1) and exception in (None, 'AgentTimeoutError',
        'ContextBudgetExceeded', 'NonZeroAgentExitCodeError', 'OutputLengthExceededError') and not reason
    return {'path': str(path), 'valid': valid, 'reward': reward if valid else None,
            'exception': exception, 'verifier_issue': reason}


def busy_scopes(cpus):
    busy = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            scope = (process / 'cgroup').read_text()
            if (any(prefix in scope for prefix in ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and cpus.intersection(os.sched_getaffinity(int(process.name)))):
                busy.add(scope.strip().split('/')[-1])
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return sorted(busy)


def resource_gate(root, config):
    swe_states = []
    for relative in config['wait_for_swe_outputs']:
        swe = root / relative
        path, model_marker = swe / 'checkpoint.json', swe / 'model-consumer-finished.json'
        checkpoint = json.loads(path.read_text()) if path.exists() else {}
        model_done = model_marker.exists() and json.loads(model_marker.read_text()).get('model_consumer_finished') is True
        drained = (checkpoint.get('active') == {} and checkpoint.get('pending') == [] and
                   len(checkpoint.get('terminal', {})) == 51 and model_done)
        swe_states.append({'output': relative, 'all_cpu_and_model_consumers_finished': drained,
            'active': len(checkpoint.get('active', {})), 'pending': len(checkpoint.get('pending', [])),
            'terminal': len(checkpoint.get('terminal', {}))})
    released = json.loads((root / config['base_cpu_release_marker']).read_text())
    markers = [root / relative for relative in config['wait_for_all_cpu_markers']]
    prior_done = all(path.exists() and json.loads(path.read_text()).get('all_cpu_consumers_finished') is True
                     for path in markers)
    drained = all(row['all_cpu_and_model_consumers_finished'] for row in swe_states) and prior_done
    busy = busy_scopes(set(range(92)))
    return {'ready': drained and released.get('cpu_consumers_finished') is True and not busy,
            'swe_all_cpu_and_model_consumers_finished': drained,
            'swe_consumers': swe_states, 'busy_scopes_on_cpus0_91': busy,
            'required_all_cpu_markers_finished': prior_done,
            'base_cpu_release_confirmed': released.get('cpu_consumers_finished') is True}


async def main(args):
    output = args.output.resolve()
    root = Path('/data/caoqinlu/projects/apex-takehome')
    config = json.loads((output / 'config.json').read_text())
    manifest = json.loads((output / 'manifest.json').read_text())
    entries = {row['key']: row for row in manifest['entries']}
    assert len(entries) == 445
    assert all(row['trial_config']['agent']['model_name'] == config['model'] for row in entries.values())
    if args.single_key:
        row = entries[args.single_key]
        trial_config = TrialConfig.model_validate(row['trial_config'])
        trial_config.environment.kwargs['baseline_cpu_offset'] = args.single_cpu
        directory = trial_config.trials_dir / trial_config.trial_name
        assert not directory.exists(), 'Original attempt retained; no automatic answer regeneration'
        trial = await Trial.create(trial_config)
        assert trial.task.checksum == row['task_checksum']
        await trial.run()
        return

    lock = (output / '.controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    previous = json.loads((output / 'checkpoint.json').read_text()) if (output / 'checkpoint.json').exists() else {}
    assert not previous.get('active'), 'In-flight attempts retained; inspect before restarting controller'
    terminal = previous.get('terminal', {})
    pending = deque(key for key in entries if key not in terminal)
    active = {}
    used_offsets = set(config['initial_cpu_offsets'])
    save(output / 'experiment.json', dict(config, expected=445, tasks=89, seeds=list(range(5)),
        base_generation_tasks=0, automatic_answer_regeneration=False,
        original_base_outputs_untouched=True, native_tests_unchanged=True,
        native_runtime_source_inventory=str(output / 'runtime/source_inventory.json')))

    def checkpoint(state):
        scores = {key: grade(output / 'trials' / row['trial_config']['trial_name'] / 'result.json')
                  for key, row in entries.items() if key in terminal}
        valid = {key: row for key, row in scores.items() if row and row['valid']}
        per_seed = []
        for seed in range(5):
            rows = [row for key, row in valid.items() if key.endswith('/seed' + str(seed))]
            correct = sum(row['reward'] for row in rows)
            per_seed.append({'seed': seed, 'expected': 89, 'valid_scored': len(rows), 'correct': correct,
                             'score_percent': 100 * correct / 89 if len(rows) == 89 else None})
        complete = len(valid) == 445
        values = [row['score_percent'] for row in per_seed]
        value = {'updated_at_utc': now(), 'pid': os.getpid(), 'state': state, 'model': config['model'],
            'expected': 445, 'valid_scored': len(valid), 'complete': complete,
            'resolved': sum(row['reward'] for row in valid.values()),
            'active': active, 'pending': list(pending), 'terminal': terminal, 'scores': scores,
            'per_seed': per_seed, 'primary_mean_percent': statistics.mean(values) if complete else None,
            'sample_sd_percent_ddof1': statistics.stdev(values) if complete else None,
            'infrastructure_unscored_finished': len(terminal) - len(valid)}
        save(output / 'checkpoint.json', value)
        save(output / 'summary.json', value)
        used_cpus = {cpu + index for cpu in used_offsets for index in range(4)}
        if not pending and not active and not busy_scopes(used_cpus):
            finished = {'at': now(), 'state': 'finished', 'model_consumer_finished': True,
                'all_cpu_consumers_finished': True, 'expected': 445, 'attempted': len(terminal),
                'valid_scored': len(valid), 'benchmark_complete': complete,
                'invalid_scores_remain_disclosed': not complete,
                'used_cpu_ids': sorted(used_cpus), 'remaining_cpu_scopes': []}
            save(output / 'model-consumer-finished.json', finished)
            save(output / 'all_cpu_consumers_finished.json', finished)

    def service_safe():
        return (datetime.fromisoformat(config['service_ends']) - datetime.now(timezone.utc)).total_seconds() >= 2100

    checkpoint('waiting_swe_cpu_and_model_consumers')
    while True:
        if not service_safe() or (output / 'STOP_ADMISSION').exists():
            checkpoint('service_expiring' if not service_safe() else 'stopped_admission')
            return
        gate = resource_gate(root, config)
        acceptance = output / 'acceptance/acceptance.json'
        accepted = acceptance.exists() and json.loads(acceptance.read_text()).get('ready') is True
        save(output / 'resource_gate.json', dict(gate, at=now(), endpoint_accepted=accepted))
        if gate['ready'] and accepted:
            break
        await asyncio.sleep(15)
    save(output / 'admission-opened.json', {'at': now(), 'cpus': list(range(92)),
        'cpu_offsets': config['initial_cpu_offsets'], 'initial_max_parallel_tasks': len(config['initial_cpu_offsets']),
        'native_endpoint_accepted': True, 'all_swe_consumers_finished': True})

    async def worker(cpu):
        async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
            while pending:
                if not service_safe() or (output / 'STOP_ADMISSION').exists():
                    return
                if busy_scopes(set(range(cpu, cpu + 4))):
                    await asyncio.sleep(10)
                    continue
                try:
                    (await client.get(config['endpoint'] + '/health')).raise_for_status()
                except httpx.HTTPError:
                    checkpoint('waiting_endpoint')
                    await asyncio.sleep(10)
                    continue
                if not pending:
                    return
                key = pending.popleft()
                name = entries[key]['trial_config']['trial_name']
                assert not (output / 'trials' / name).exists(), 'Retain prior unregistered attempt; audit required'
                active[key] = {'cpu_offset': cpu, 'started_at': now(), 'pid': None}
                log_path = output / 'logs' / (name + '.log')
                log_path.parent.mkdir(exist_ok=True)
                with log_path.open('ab') as log:
                    child = await asyncio.create_subprocess_exec(sys.executable, str(Path(__file__).resolve()),
                        '--output=' + str(output), '--single-key=' + key, '--single-cpu=' + str(cpu),
                        stdout=log, stderr=log)
                    active[key]['pid'] = child.pid
                    checkpoint('running')
                    while child.returncode is None:
                        try:
                            await asyncio.wait_for(child.wait(), timeout=10)
                        except TimeoutError:
                            checkpoint('running')
                terminal[key] = {'finished_at': now(), 'process_exit_code': child.returncode}
                active.pop(key)
                checkpoint('running')
                print(json.dumps({'event': 'finished', 'key': key, **terminal[key]}), flush=True)

    workers = [asyncio.create_task(worker(cpu)) for cpu in config['initial_cpu_offsets']]
    expanded = False
    while any(not task.done() for task in workers):
        markers = [root / relative for relative in config['expansion_cpu_release_markers']]
        ready = all(path.exists() and json.loads(path.read_text()).get('state') == 'finished' for path in markers)
        if not expanded and ready and not busy_scopes(set(range(92, 124))):
            expanded = True
            extra = [cpu for cpu in config['cpu_offsets'] if cpu not in config['initial_cpu_offsets']]
            used_offsets.update(extra)
            workers.extend(asyncio.create_task(worker(cpu)) for cpu in extra)
            save(output / 'cpu-expansion.json', {'at': now(), 'additional_cpu_offsets': extra,
                'all_asi_cpu_consumers_finished': True, 'max_parallel_tasks': len(config['cpu_offsets'])})
        checkpoint('running')
        await asyncio.sleep(10)
    await asyncio.gather(*workers)
    used_cpus = {cpu + index for cpu in used_offsets for index in range(4)}
    while not pending and busy_scopes(used_cpus):
        checkpoint('waiting_final_cpu_scope_drain')
        await asyncio.sleep(5)
    checkpoint('service_expiring' if pending and not service_safe() else
               'stopped_admission' if pending else 'all445_attempts_finished')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--single-key')
    parser.add_argument('--single-cpu', type=int)
    asyncio.run(main(parser.parse_args()))
