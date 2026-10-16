#!/usr/bin/env python3
"""Prepare by default; explicit flags install a future import shim or grade once.

One fixed CMOS condition, unchanged source answer/native scoring. New native
Judge calls share the ORIGINAL financial journal and its existing budget.
"""
import argparse
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from prepare_asi_import_recovery import CONDITION, identity, inspect


EXPECTED_SOURCE_SHA = '0515dfd5628e9c9d3b7f697a2497692a932e85983389b1939c80453271aa3608'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def load_native(project, runtime):
    sys.dont_write_bytecode = True
    for path in [project / 'artifacts/benchmarks/asi', runtime, runtime / 'scripts']:
        sys.path.insert(0, str(path))
    return importlib.import_module('score_asi_baseline_v2'), importlib.import_module('asi_score_transport')


def recovery_worker(connection, job, settings, condition):
    """Use the frozen worker, changing only journal location/cache namespace."""
    native, transport = load_native(Path(settings['project']), Path(settings['runtime']))
    original_transport = transport.DeepSeekJudgeTransport

    class SharedBudgetTransport(original_transport):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # A proxy avoids temporarily changing self.root across native calls.
            self.budget_proxy = copy.copy(self)
            self.budget_proxy.root = Path(settings['original_scoring'])

        def journal(self, event, *, reserve=False):
            if reserve:
                # Unique grade claim prevents another writer for this condition.
                # Never resend a logical request that may already have run.
                journal = self.budget_proxy.root / 'judge_calls.jsonl'
                records = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
                key = (event['condition'].rsplit('.grading', 1)[0], event['request_sha256'], event['occurrence'])
                prior = [row for row in records if row.get('event') == 'started' and
                         (row.get('condition', '').rsplit('.grading', 1)[0],
                          row.get('request_sha256'), row.get('occurrence')) == key]
                if prior:
                    raise RuntimeError('Already-started logical Judge request: no resend')
            # Exact frozen396-call/20CNY reserve+flock logic, ORIGINAL ledger.
            return original_transport.journal(self.budget_proxy, event, reserve=reserve)

    native.DeepSeekJudgeTransport = SharedBudgetTransport
    native.worker(connection, job, settings, condition)


def stable_identities(plan):
    files = [plan['source_result'], plan['parameter_metadata'], plan['original_condition_record']]
    files += plan['persisted_outputs']
    for row in plan['verified_cache']:
        files += [row['request_file'], row['response_file']]
    return [{key: row[key] for key in ['path', 'bytes', 'sha256']} for row in files]


def assert_stable(rows):
    assert all(identity(Path(row['path'])) == row for row in rows)


def grader_scopes(project):
    # Count any intersection, including a program with broader affinity.
    listing = subprocess.check_output(['systemctl', '--user', 'list-units', '--type=scope',
        '--state=running', '--no-legend', '--plain'], text=True)
    rows = []
    for line in listing.splitlines():
        scope = line.split()[0]
        if not scope.startswith(('apex-', 'asi-', 'ai4sci-')):
            continue
        group = subprocess.check_output(['systemctl', '--user', 'show', scope,
            '--property=ControlGroup', '--value'], text=True).strip()
        cgroup = Path('/sys/fs/cgroup') / group.lstrip('/')
        pids = set()
        for path in cgroup.rglob('cgroup.procs'):
            for value in path.read_text().split():
                try:
                    if os.sched_getaffinity(int(value)) & set(range(92, 96)):
                        pids.add(int(value))
                except ProcessLookupError:
                    pass
        if pids:
            rows.append({'scope': scope, 'pids': sorted(pids)})
    return rows


def drain_twice(project, output):
    samples = []
    while len(samples) < 2:
        scopes = grader_scopes(project)
        if scopes:
            samples = []
            save(output / 'state.json', {'state': 'waiting_native_cpu_scope_drain', 'at_utc': now()})
        else:
            samples.append({'at_utc': now(), 'active_program_scopes': []})
        if len(samples) < 2:
            time.sleep(2)
    return samples


def journal_summary(data):
    rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    starts = [row for row in rows if row.get('event') == 'started']
    terminal = {row.get('id') for row in rows if row.get('event') in ('completed', 'failed')}
    return {'started': len(starts), 'completed': sum(row.get('event') == 'completed' for row in rows),
        'cache_reused': sum(row.get('event') == 'cache_reused' for row in rows),
        'reserved_cny': sum(row.get('reserved_cny', 0) for row in starts),
        'unsettled_started': sum(row.get('id') not in terminal for row in starts)}


def grade_once(project, plan):
    original = project / 'artifacts/eval/asi128_asi240_20261017/scoring'
    runtime = original / 'runtime'
    output = project / 'artifacts/eval/asi128_asi240_20261017/import_recovery_20261017'
    assert plan['source_result']['sha256'] == EXPECTED_SOURCE_SHA
    assert not output.exists(), 'Existing claim/output: never repeat an uncertain attempt'
    assert os.environ.get('XDG_RUNTIME_DIR') and os.environ.get('DBUS_SESSION_BUS_ADDRESS')
    os.sched_setaffinity(0, range(92, 96))
    before = stable_identities(plan)
    full_report = identity(original / 'local_score_seed31415.json')
    with (project / 'artifacts/eval/direct_asi_grader_cpu92_95.lock').open('r') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not grader_scopes(project), 'Legitimate existing CPU consumer; wait rather than interrupt'
        journal = original / 'judge_calls.jsonl'
        journal_before = journal.read_bytes()
        budget_before = journal_summary(journal_before)
        assert budget_before['unsettled_started'] == 0, 'Unknown paid request: do not resend'
        code_before = tree_identity(runtime)
        task = project / 'artifacts/benchmarks/asi/tasks/electrical_engineering/cmos_opamp_design'
        task_before = [identity(task / name) for name in
            ['task_eval.yaml', 'custom_scorer.py', 'cmos_eval_runtime.py']]
        output.mkdir(exist_ok=False)
        save(output / 'claim.json', {'pid': os.getpid(), 'at_utc': now(), 'condition': CONDITION,
            'pass_limit': 1, 'source': plan['source_result'], 'cache_namespace': CONDITION + '.grading2'})
        backup = output / 'original'; backup.mkdir()
        for name in ['local_score_seed31415.json', 'scoring_config.json', 'judge_identity.json', 'judge_calls.jsonl']:
            shutil.copy2(original / name, backup / name)
        shutil.copy2(Path(plan['original_condition_record']['path']), backup / 'invalid_condition.json')
        shutil.copy2(Path(plan['source_result']['path']), backup / 'source_result.json')
        for row in plan['persisted_outputs']:
            shutil.copy2(row['path'], backup / Path(row['path']).name)
        cache = output / 'judge_calls' / (CONDITION + '.grading2')
        cache.mkdir(parents=True)
        for row in plan['verified_cache']:
            for kind in ['request_file', 'response_file']:
                source = Path(row[kind]['path']); destination = cache / source.name
                shutil.copy2(source, destination)
                assert identity(destination)['sha256'] == row[kind]['sha256']
        shutil.copy2(original / 'judge_identity.json', output / 'judge_identity.json')
        config = json.loads((original / 'scoring_config.json').read_text())
        assert config['hard_budget'] == {'max_generation_calls': 396, 'max_cny': 20.0}
        assert config['condition_timeout_seconds'] == 7200 and config['http_timeout_seconds'] == 90
        identity_config = json.loads((original / 'judge_identity.json').read_text())
        settings = {'project': str(project), 'runtime': str(runtime), 'original_scoring': str(original),
            'output': str(output), 'endpoint': config['endpoint'], 'mode': 'paid',
            'credentials': str(project / 'artifacts/private/deepseek.env'),
            'input_bound_mode': 'utf8_plus_image_ceiling', 'max_generation_calls': 396,
            'max_cny': 20, 'http_timeout': 90, 'condition_timeout': 7200,
            'ngspice_runtime': str(project / 'artifacts/asi/scoring_ngspice_20261016/rootfs'),
            'tasks': str(project / 'artifacts/benchmarks/asi/tasks'),
            'expected_reported_model': identity_config['reported_model']}
        native, _ = load_native(project, runtime)
        source = Path(plan['source_result']['path']); raw = json.loads(source.read_text())
        if not raw.get('parameters'):
            raw = dict(raw, parameters=json.loads(Path(plan['parameter_metadata']['path']).read_text())['parameters'])
        job = native._prepare_score_jobs([(source, raw)], results_root=original.parent,
            instances_root=project / 'artifacts/asi/scoring_seed31415/instances',
            tasks_root=Path(settings['tasks']))[0]
        native.check_declared_references(job.evaluation, job.reference_dir)
        save(output / 'execution.json', {'state': 'native_grade_started', 'at_utc': now(),
            'condition': CONDITION, 'settings_without_credentials': {k:v for k,v in settings.items() if k != 'credentials'},
            'original_shared_journal': str(original / 'judge_calls.jsonl'),
            'copied_cache_pairs': 9, 'worker_count': 1, 'canonical_overwrite': False})
        frozen_worker = native.worker
        native.worker = recovery_worker
        try:
            result = native.evaluate(job, settings, CONDITION + '.grading2')
        finally:
            native.worker = frozen_worker
            # Retain the global lease even on evaluator errors until real programs drain.
            samples = drain_twice(project, output)
        # Reuse the frozen evaluator error detector, no grading formula changes.
        if native.evaluator_error([result['gate_results'], result['score_results']]):
            result.update(native_final_score=result['final_score'], final_score=None,
                          evaluation_status='evaluation_invalid', scorer_internal_error=True)
        result.update(condition=CONDITION, attempt=2, source_result=str(source), recovery_reason='import_path_tasks')
        save(output / 'native_result.json', result)
        assert_stable(before)
        assert identity(original / 'local_score_seed31415.json') == full_report
        assert tree_identity(runtime) == code_before
        assert_stable(task_before)
        journal_after = journal.read_bytes()
        assert journal_after.startswith(journal_before), 'Original ledger prefix changed'
        budget_after = journal_summary(journal_after)
        appended = journal_summary(journal_after[len(journal_before):])
        assert budget_after['started'] <= 396 and budget_after['reserved_cny'] <= 20
        save(output / 'receipt.json', {'state': 'finished', 'at_utc': now(), 'condition': CONDITION,
            'evaluation_status': result['evaluation_status'], 'source_bytes_unchanged': True,
            'canonical_report_unchanged': True, 'active_program_scopes': [],
            'scope_empty_samples': samples, 'native_runtime_tree_unchanged': True,
            'native_task_criteria_parser_files_unchanged': task_before,
            'shared_budget_journal': str(journal), 'pass_count': 1,
            'journal_original_prefix_unchanged': True, 'original_prefix_bytes': len(journal_before),
            'original_prefix_sha256': hashlib.sha256(journal_before).hexdigest(),
            'budget_before': budget_before, 'budget_after': budget_after,
            'new_calls': appended['started'], 'cache_reuses': appended['cache_reused'],
            'canonical_record_not_accepted_or_overwritten': True})


def tree_identity(root):
    rows = {}
    for path in sorted(root.rglob('*')):
        name = str(path.relative_to(root))
        if path.is_symlink():
            target = path.resolve(strict=True)
            rows[name] = {'symlink_target': os.readlink(path), 'resolved_target': str(target),
                'target_files': {str(p.relative_to(target)): identity(p)['sha256']
                    for p in sorted(target.rglob('*')) if p.is_file()} if target.is_dir()
                    else {'file': identity(target)['sha256']}}
        elif path.is_file():
            rows[name] = identity(path)['sha256']
    return rows


def stage_runtime(project, source, staging):
    """Full frozen copy plus one shim; no activation, evaluation or HTTP."""
    before = tree_identity(source)
    assert 'sitecustomize.py' not in before
    shutil.copytree(source, staging, symlinks=True)
    repo = project / 'artifacts/benchmarks/asi'
    (staging / 'sitecustomize.py').write_text('import sys\nsys.path.append(' + repr(str(repo)) + ')\n')
    after = tree_identity(staging); shim_sha = after.pop('sitecustomize.py')
    assert after == before and tree_identity(source) == before
    env = dict(os.environ, PYTHONPATH=str(staging), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    code = ("import socket; "
            "socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('network forbidden')); "
            'from tasks.electrical_engineering.cmos_opamp_design import cmos_eval_runtime; '
            'print(cmos_eval_runtime.__file__)')
    tested = subprocess.check_output(['taskset', '-c', '92',
        str(project / 'artifacts/envs/asi-py312/bin/python'), '-c', code],
        cwd=project, env=env, text=True, timeout=30).strip()
    assert tested == str(repo / 'tasks/electrical_engineering/cmos_opamp_design/cmos_eval_runtime.py')
    after_probe = tree_identity(staging)
    assert after_probe.pop('sitecustomize.py') == shim_sha and after_probe == before
    assert tree_identity(source) == before
    return before, shim_sha


def install_avg_runtime(project):
    """Only a future child's import path changes; no live PID is signalled."""
    source = project / 'artifacts/asi/scoring_v2_formal_params_20261016/runtime'
    asi = project / 'artifacts/eval/avg64_asi240_20261017'
    target = asi / 'scoring/runtime'
    pipe = project / 'artifacts/eval/merged_direct_pipeline_20261017'
    receipt = project / 'artifacts/eval/asi-import-fix-installation-20261017/receipt.json'
    with (project / 'artifacts/eval/direct_asi_grader_cpu92_95.lock').open('r') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not target.exists() and not receipt.exists() and not (pipe / 'asi_score_launch.json').exists()
        assert not (asi / 'generation_cpu_finished.json').exists()
        progress = json.loads((asi / 'progress.json').read_text())
        assert progress['state'] == 'running'
        state = json.loads((pipe / 'state.json').read_text())
        assert state['state'] == 'asi_generation'
        pid = state['pid']
        proc = Path('/proc') / str(pid)
        proc_state = proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()
        assert proc_state[0] != 'Z'
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.with_name('runtime.stage-' + uuid.uuid4().hex)
        before, shim_sha = stage_runtime(project, source, staging)
        assert not target.exists()
        staging.rename(target)
        save(receipt, {'state': 'installed', 'at_utc': now(), 'target': str(target),
            'source_tree_unchanged': True, 'copied_file_count': len(before), 'added_only': 'sitecustomize.py',
            'shim_sha256': shim_sha, 'import_probe': 'green', 'generator_pid_observed': pid,
            'generator_starttime_ticks': int(proc_state[19]), 'progress_state_observed': progress['state'],
            'generation_not_interrupted': True, 'scoring_workers': 1, 'source_tree': before})


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--execute', action='store_true')
    actions.add_argument('--install-avg-runtime', action='store_true')
    args = parser.parse_args()
    project = args.project.resolve()
    plan = inspect(project)
    assert plan['source_result']['sha256'] == EXPECTED_SOURCE_SHA
    if args.execute:
        grade_once(project, plan)
    elif args.install_avg_runtime:
        install_avg_runtime(project)
    else:
        print(json.dumps({'mode': 'prepare_only', 'condition': CONDITION,
            'source': plan['source_result'], 'persisted_outputs_verified': len(plan['persisted_outputs']),
            'cache_pairs_verified': len(plan['verified_cache']), 'grading_namespace': CONDITION + '.grading2',
            'new_native_http_first_calls': 'shared original396calls/20CNY journal only',
            'actions_taken': [], 'native_evaluations': 0, 'production_runtime_installed': False}, indent=2))
