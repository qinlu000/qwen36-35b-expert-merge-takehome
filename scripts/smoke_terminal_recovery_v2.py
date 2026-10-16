#!/usr/bin/env python3
"""Independent outage/recovery fixtures; no benchmark input or real model call."""
import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
import time
import sys
from types import SimpleNamespace
from unittest.mock import patch

import httpx

import terminal_recovery_v2 as recovery
from run_terminal_recovery_v2 import valid_result
import run_terminal_recovery_v2 as driver
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import TrialConfig, TaskConfig, AgentConfig


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks = {}
    entries = [{'key': str(i)} for i in range(24)]
    statuses = {e['key']: {'state': 'pending'} for e in entries}
    statuses['0']['state'] = 'valid'
    seen = Counter()
    snapshots = []
    gate = asyncio.Event()
    breaker = recovery.CircuitBreaker()

    def save():
        snapshot = {k: dict(v) for k, v in statuses.items()}
        snapshots.append(snapshot)
        (args.output / 'checkpoint.json').write_text(json.dumps(snapshot, indent=2) + '\n')

    async def healthy():
        await asyncio.sleep(0)

    async def fail_once(entry):
        token = recovery.ACTIVE_ENTRY.set(entry['key'])
        seen[entry['key']] += 1
        if sum(seen.values()) == 8:
            gate.set()
        try:
            await gate.wait()
            if entry['key'] == '3':
                # Native wait_for uses a child task; ContextVar retains the
                # correct owner key so its own transport cleanup is not cancelled.
                async def nested_transport_failure():
                    breaker.trip('ReadError: independent synthetic outage')
                await asyncio.create_task(nested_transport_failure())
                await asyncio.sleep(0.01)
                statuses[entry['key']]['state'] = 'failed_attempt'
            else:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            statuses[entry['key']]['state'] = 'cancelled'
            raise
        finally:
            recovery.ACTIVE_ENTRY.reset(token)
            save()

    first = await recovery.run_queue(entries, statuses, fail_once, healthy, breaker, save, 8)
    assert first['halted'] and first['admitted_peak'] == 8 and sum(seen.values()) == 8
    assert breaker.owner_key == '3' and statuses['3']['state'] == 'failed_attempt'
    assert statuses['0']['state'] == 'valid' and seen['0'] == 0
    assert sum(s['state'] == 'pending' for s in statuses.values()) == 15
    checks['outage_stops_at8_and_preserves_nested_failure_owner'] = True

    async def success(entry):
        seen[entry['key']] += 1
        await asyncio.sleep(0)
        statuses[entry['key']]['state'] = 'valid'
        save()
    before = dict(seen)
    second = await recovery.run_queue(entries, statuses, success, healthy,
                                      recovery.CircuitBreaker(), save, 8)
    assert not second['halted'] and second['pending_not_admitted'] == 0
    assert all(seen[k] == v for k, v in before.items())
    assert all(v == 1 for v in seen.values())
    prior_calls = sum(seen.values())
    await recovery.run_queue(entries, statuses, success, healthy, recovery.CircuitBreaker(), save, 8)
    assert sum(seen.values()) == prior_calls
    checks['recovery_runs_only_never_admitted_and_never_repeats_valid'] = True

    # All active calls hang: the independent one-second health monitor must
    # trip without waiting for any model request or solver deadline to return.
    statuses2 = {str(i): {'state': 'pending'} for i in range(20)}
    entered = set()
    async def hangs(entry):
        entered.add(entry['key'])
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            statuses2[entry['key']]['state'] = 'cancelled'
            raise
    async def down_after8():
        if len(entered) == 8:
            raise httpx.ConnectError('independent outage while all requests hang')
    started = time.monotonic()
    third = await recovery.run_queue([{'key': str(i)} for i in range(20)], statuses2,
                                     hangs, down_after8, recovery.CircuitBreaker(), lambda: None, 8)
    assert third['halted'] and third['admitted_peak'] == len(entered) == 8
    assert time.monotonic() - started < 2.5
    checks['independent1s_health_monitor_cancels8_hung_calls'] = True

    def scored(exception=None):
        return {'verifier_result': {'rewards': {'reward': 0}},
                'exception_info': {'exception_type': exception} if exception else None}
    assert valid_result(scored()) and valid_result(scored('AgentTimeoutError'))
    assert valid_result(scored('ContextBudgetExceeded')) and valid_result(scored('NonZeroAgentExitCodeError'))
    assert not valid_result(scored('ReadError')) and not valid_result(scored('CancelledError'))
    checks['normal_zero_budget_program_failures_valid_but_infra_zero_invalid'] = True

    # Actual recovery LLM class, fake HTTP: read/disconnect never get an
    # identical automatic second generation, while native budget stays8192.
    key = args.output / 'synthetic-key'
    key.write_text('independent-nonsecret-fixture')
    for error_class in (httpx.ReadTimeout, httpx.RemoteProtocolError):
        calls = []
        async def transport(request):
            body = json.loads(request.content)
            calls.append((request.url.path, body))
            if request.url.path == '/tokenize':
                return httpx.Response(200, json={'count': 40, 'max_model_len': 65536})
            raise error_class('independent ambiguous outcome', request=request)
        llm = recovery.RecoveryLLM('http://synthetic.invalid', 'apex-qwen', key, 0,
                                   args.output / error_class.__name__)
        llm.deadline = time.monotonic() + 30
        recovery.BREAKER = recovery.CircuitBreaker()
        async with httpx.AsyncClient(base_url='http://synthetic.invalid',
                                    transport=httpx.MockTransport(transport)) as client:
            llm.client = client
            try:
                await llm.call('Independent synthetic marker only.')
                raise AssertionError('ambiguous error swallowed')
            except error_class:
                pass
        generations = [b for p, b in calls if p == '/v1/chat/completions']
        assert len(generations) == 1 and generations[0]['max_tokens'] == 8192
        assert recovery.BREAKER.event.is_set()
    key.unlink()
    checks['read_timeout_and_disconnect_trip_without_same_payload_retry'] = True

    # Exercise the real445-manifest driver end-to-end with fake native trials.
    # This checks first0 config conversion, explicit retry1 and resume coverage.
    sandbox = args.output / 'full-driver'
    sandbox.mkdir(exist_ok=True)
    ids = [f'synthetic-{i:02d}' for i in range(89)]
    freeze = sandbox / 'source-freeze.json'
    freeze.write_text(json.dumps({'runtime': str(sandbox), 'source_sha256': {}}))
    seed_jobs = {}
    agent_kwargs = {'api_base': 'http://synthetic.invalid', 'api_key_path': str(key), 'seed': 0}
    for seed in range(5):
        kwargs = dict(agent_kwargs, seed=seed)
        job = JobConfig.model_validate({'agents': [{'import_path': 'terminal_baseline_v2:TerminalBaselineV2',
            'model_name': 'apex-qwen', 'override_timeout_sec': 1800, 'kwargs': kwargs}],
            'environment': {'override_cpus': 4, 'override_memory_mb': 8192}})
        path = sandbox / f'seed{seed}.json'
        path.write_text(job.model_dump_json())
        seed_jobs[str(seed)] = {'path': str(path.resolve()), 'sha256': driver.digest(path)}
    key.write_text('independent-nonsecret-fixture')
    full_entries = []
    for seed in range(5):
        for index, task in enumerate(ids):
            task_config = TaskConfig(path=sandbox / task)
            entry = {'key': f'{task}/seed{seed}', 'task_id': task, 'seed': seed,
                     'task_checksum': 'SYNTHETIC_TASK_HASH',
                     'task_config': task_config.model_dump(mode='json'), 'manual_attempt': 0}
            if seed == 0 and index < 21:
                config = TrialConfig(task=task_config, agent=AgentConfig(
                    import_path='terminal_baseline_v2:TerminalBaselineV2', model_name='apex-qwen',
                    override_timeout_sec=1800, kwargs=dict(agent_kwargs)),
                    environment=job.environment)
                source = sandbox / f'original-{task}.json'
                original = {'task_name': task, 'config': config.model_dump(mode='json'),
                            'verifier_result': None, 'exception_info': {'exception_type': 'ReadError'}}
                if index == 0:
                    original.update(verifier_result={'rewards': {'reward': 0}}, exception_info=None)
                source.write_text(json.dumps(original))
                entry.update(manual_attempt=1, original_result=str(source.resolve()),
                             original_result_sha256=driver.digest(source), original_files_sha256={},
                             prior_manual_attempts=[])
            full_entries.append(entry)
    manifest = sandbox / 'manifest.json'
    manifest.write_text(json.dumps({'explicit_manual_infrastructure_authorization': True,
        'task_ids': ids, 'entries': full_entries, 'seed_job_configs': seed_jobs,
        'frozen_source_manifest': str(freeze.resolve()), 'frozen_source_manifest_sha256': driver.digest(freeze)}))
    native_calls = Counter()
    class FakeTrial:
        @classmethod
        async def create(cls, config):
            trial = cls()
            trial.config = config
            trial.task = SimpleNamespace(checksum='SYNTHETIC_TASK_HASH')
            assert config.agent.override_timeout_sec == 1800
            assert config.environment.override_cpus == 4 and config.environment.override_memory_mb == 8192
            assert config.agent.import_path == 'terminal_recovery_v2:RecoveryTerminalBaselineV2'
            return trial

        async def run(self):
            config = self.config
            name = config.task.path.name
            seed = config.agent.kwargs['seed']
            native_calls[f'{name}/seed{seed}'] += 1
            result = {'verifier_result': {'rewards': {'reward': 0}}, 'exception_info': None}
            path = config.trials_dir / config.trial_name
            path.mkdir(parents=True)
            (path / 'result.json').write_text(json.dumps(result))
            await asyncio.sleep(0)
            return SimpleNamespace(model_dump=lambda **kwargs: result)
    async def fake_health(request):
        assert request.url.path == '/health'
        return httpx.Response(200)
    real_client = httpx.AsyncClient
    def client_factory(*args, **kwargs):
        return real_client(*args, **kwargs, transport=httpx.MockTransport(fake_health))
    argv = ['driver', '--manifest', str(manifest.resolve()), '--output', str((sandbox / 'run').resolve()),
            '--endpoint', 'http://synthetic.invalid', '--api-key-path', str(key.resolve())]
    with patch.object(sys, 'argv', argv), patch.object(driver, 'Trial', FakeTrial), patch.object(httpx, 'AsyncClient', client_factory):
        await driver.main()
        assert sum(native_calls.values()) == 444 and native_calls[f'{ids[0]}/seed0'] == 0
        await driver.main()
        assert sum(native_calls.values()) == 444 and all(v == 1 for v in native_calls.values())
    coverage = json.loads((sandbox / 'run/coverage.json').read_text())
    assert coverage['expected_trials'] == coverage['valid_covered'] == 445
    assert coverage['admission_classes'] == {'0': 424, '1': 21, '2': 0}
    assert coverage['primary_mean_percent'] == 0
    key.unlink()
    checks['full445_driver_retry1_first0_resume_preserves_first_valid_zero'] = True
    report = {'status': 'passed', 'scope': 'independent fake tasks/HTTP only; no real model or benchmark text',
              'checks': checks, 'first_stop': first, 'recovery': second,
              'hung_requests_stop': third, 'per_entry_admission_counts': dict(seen),
              'original_valid_entry0_ever_admitted': seen['0'], 'snapshots_saved': len(snapshots)}
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())
