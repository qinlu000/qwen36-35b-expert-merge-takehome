#!/usr/bin/env python3
"""Reuse group1 only after its natural drain for six audited incomplete trials."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

from swe_baseline_v2 import ROOT, save_json


def main():
    output = ROOT / 'artifacts/eval/base_swe_v2_20261016_manual_infra1'
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / '.follow-on.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    prior = ROOT / 'artifacts/eval/base_swe_v2_20261016_glibc_setup1'
    full = ROOT / 'artifacts/eval/base_swe_v2_20261016_full'
    active_cohort = ROOT / 'artifacts/eval/base_swe_v2_20261016_full_x2'
    ids = json.loads((ROOT / 'analysis/source_snapshots/protocol/swe_hard_task_ids.json').read_text())['task_ids']
    fresh = set(json.loads((full / 'first-generation-43.json').read_text()))
    budget = set(json.loads((ROOT / 'artifacts/eval/base_swe_v2_20261016_budget_replay/preserved_manifest.json').read_text())['task_ids'])
    selected = [n for n in ids if n not in fresh | budget]
    assert len(selected) == 6
    manifest = []
    for name in selected:
        directory = prior / 'generation' / name
        result = json.loads((directory / 'result.json').read_text())
        trajectory = json.loads((directory / 'agent/mini-swe-agent.trajectory.json').read_text())
        info = trajectory.get('info', {})
        assert result['exception_info']['exception_type'] == 'CancelledError'
        assert not info.get('exit_status') and not info.get('submission')
        manifest.append({'task_id': name, 'classification': 'engine_cancelled_incomplete',
            'original_result': str(directory / 'result.json'),
            'original_trajectory': str(directory / 'agent/mini-swe-agent.trajectory.json'),
            'original_requests': str(prior / 'requests' / name),
            'original_api_calls': (info.get('model_stats') or {}).get('api_calls'),
            'original_agent_execution': result.get('agent_execution'),
            'original_answer_complete': False, 'original_files_preserved': True,
            'manual_infrastructure_retry': 1, 'generation_attempt': 2,
            'seed': 0, 'solver_budget_seconds': 1800,
            'authorization': 'User requested complete final baseline; parent explicitly authorized incomplete infrastructure whole-task retry, maximum2 manual retries',
            'resume': 'No verified native remaining-budget resume entry; do not invent a trajectory continuation'})
    save_json(output / 'manual_retry_manifest.json', {'scope': 51, 'tasks': manifest,
        'selection': 'Only six CancelledError tasks without native exit status/submission; never retry completed model tasks',
        'prior_costs_and_responses_preserved': True})
    save_json(output / 'admission_ids.json', selected)
    save_json(output / 'follow-on.json', {'pid': os.getpid(), 'state': 'waiting_group1_natural_drain',
        'wait_for': str(active_cohort), 'manual_retry_ids': selected, 'scope': 51})
    group = active_cohort / 'group1'
    group_output = str(group).encode()
    def group1_processes():
        found = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if group_output in (proc / 'mountinfo').read_bytes():
                    found.append(int(proc.name))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
        return found
    while True:
        state = group / 'admission_checkpoint.json'
        if state.exists():
            checkpoint = json.loads(state.read_text())
            child = next(c for c in json.loads((active_cohort / 'controller.json').read_text())['children']
                         if c['output'] == str(group))
            cmdline = Path('/proc') / str(child['pid']) / 'cmdline'
            child_alive = cmdline.exists() and bool(cmdline.read_bytes())
            if (checkpoint['state'] == 'finished_available_images' and not checkpoint['active']
                    and not checkpoint['pending'] and not child_alive):
                remaining = group1_processes()
                if not remaining:
                    save_json(output / 'cpu-reuse-receipt.json', {'group': str(group),
                        'controller_pid': child['pid'], 'controller_exited': True,
                        'old_container_pids': [], 'manual6_cpus': list(range(76, 82)),
                        'group0_max_solvers': 8, 'combined_max_solvers': 14})
                    break
        time.sleep(5)
    command = [str(ROOT / 'artifacts/envs/harbor/bin/python'), '-u',
        str(ROOT / 'scripts/run_swe_baseline_v2_manual1.py'), '--endpoint', 'http://127.0.0.1:28084',
        '--key-path', str(ROOT / 'artifacts/private/base_smoke_api_key'), '--output', str(output),
        '--admit-task-ids', str(output / 'admission_ids.json'), '--concurrency', '6', '--cpu-offset', '76',
        '--environment-import-path', 'swe_score_runtime:SweNativeRuntimeEnvironment',
        '--engine-max-seqs', '8', '--acceptance-receipt',
        str(ROOT / 'artifacts/preflight/swe_v2/acceptance_glibc41_20261016.json')]
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts'))
    prefix = ':'.join(str(ROOT / p) for p in ['artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin',
        'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin'])
    env['PATH'] = prefix + ':' + env['PATH']
    with (output / 'controller.log').open('ab') as log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, env=env)
    save_json(output / 'follow-on.json', {'pid': os.getpid(), 'state': 'manual_infra_retry1_running',
        'child_pid': child.pid, 'task_ids': selected, 'scope': 51})
    child.wait()
    checkpoint = json.loads((output / 'admission_checkpoint.json').read_text())
    complete = checkpoint['state'] == 'finished_available_images' and not checkpoint['pending'] and not checkpoint['active']
    save_json(output / 'follow-on.json', {'pid': os.getpid(), 'state': 'finished' if complete else 'requires_infrastructure_audit',
        'child_returncode': child.returncode, 'checkpoint': str(output / 'admission_checkpoint.json')})
    if complete:
        while not (active_cohort / 'cohort-finished.json').exists():
            time.sleep(5)
        cohort = json.loads((active_cohort / 'checkpoint.json').read_text())
        if cohort['active'] or cohort['pending']:
            save_json(output / 'follow-on.json', {'pid': os.getpid(),
                'state': 'requires_audit_active17_not_complete', 'manual6_complete': True})
            return
        save_json(ROOT / 'artifacts/runs/swe-base-725705/model-consumer-finished.json', {
            'model_consumer_finished': True, 'active': 0, 'current17': str(active_cohort),
            'manual6': str(output), 'generation_task_count': 23,
            'replay_requires_model': False, 'old_model_answers_preserved': True})
    subprocess.run([str(ROOT / 'artifacts/envs/harbor/bin/python'),
        str(ROOT / 'scripts/collect_swe_final.py'), '--watch'], env=env, check=True)


if __name__ == '__main__':
    main()
