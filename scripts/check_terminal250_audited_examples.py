"""Artificial metadata examples only; never reads or runs a real Terminal trial."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from collect_terminal250_audited import approved_native_grade, collect, sha256


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(root):
    key, model = 'git-leak-recovery/seed1', 'apex-terminal250'
    names = ('original_result', 'accepted_result', 'restore_manifest', 'parent_launch',
             'parent_state', 'execution_claim', 'execution_review', 'ctrf')
    audit = {name: 'fixture/' + name + '.json' for name in names}
    audit.update(key=key, model=model, seed=1, task_checksum='fixed-task', expected_native_reward=1,
        parent_pid=123, parent_startticks='456', parent_script_sha256='fixed-script',
        parent_manifest_sha256='fixed-manifest', frozen_parent_sha256='fixed-parent',
        official_test_names=['official-test-' + str(i) for i in range(5)], reason='Artificial fixed approval')
    previous = {'path': str(root / audit['original_result']), 'valid': False, 'reward': None,
                'exception': 'RuntimeError', 'verifier_issue': None}
    audit['original_invalid'] = deepcopy(previous)
    config = {'agent': {'model_name': model, 'kwargs': {'seed': 1}, 'override_timeout_sec': 1800},
        'environment': {'override_cpus': 4, 'override_memory_mb': 8192, 'override_gpus': 0,
            'cpu_enforcement_policy': 'limit', 'memory_enforcement_policy': 'limit',
            'kwargs': {'baseline_cpu_offset': 0, 'baseline_cpu_slots': 1}},
        'verifier': {'override_timeout_sec': 900}, 'timeout_multiplier': 1}
    original = {'task_checksum': 'fixed-task', 'config': deepcopy(config),
                'verifier_result': None, 'exception_info': {'exception_type': 'RuntimeError'}}
    accepted = {'task_checksum': 'fixed-task', 'config': deepcopy(config),
                'verifier_result': {'rewards': {'reward': 1.0}}, 'exception_info': None}
    restore = {'original_result': previous['path'], 'model': model, 'seed': 1, 'task_checksum': 'fixed-task',
        'no_install_or_service_start': True, 'new_model_calls': 0,
        'resolver_policy': {'excluded': '/etc/resolv.conf', 'retain_frozen_runtime_policy': True},
        'mode_audit': {'key': key, 'alias': '/etc/apt/apt.conf.d/01-vendor-ubuntu',
            'regular_target': '/app/repo/.git/info/refs', 'raw_alias_mode': '0o644', 'canonical_mode': '0o600',
            'candidate_chmod_or_hardlink_split': False, 'all_other_mode_checks_unchanged': True}}
    launch = {'pid': 123, 'startticks': '456', 'root_and_independent_review_passed': True,
        'new_model_calls': 0, 'script_sha256': 'fixed-script', 'manifest_sha256': 'fixed-manifest',
        'frozen_parent_sha256': 'fixed-parent', 'cpu_ids': [92, 93, 94, 95],
        'logical_offset': 0, 'memory_mib': 8192, 'verifier_seconds': 900}
    output = str((root / audit['accepted_result']).parent)
    command = ['grade-only', '--original-result', previous['path'], '--restore-manifest', str(root / audit['restore_manifest'])]
    state = {'pid': 123, 'startticks': '456', 'command': command, 'model_calls': 0, 'native_output': output,
        'state': 'finished_pending_root_review', 'child_returncode': 0, 'native_reward': 1.0,
        'exception_type': None, 'original_and_restore_unchanged': True, 'lock_held': False, 'remaining_scopes': [],
        'guard_observed': {'affinities': {'124': [92, 93, 94, 95]}, 'memory_max': 33554432, 'memory_swap_max': 0},
        'guard_stopped': True, 'released_at_utc': '2026-10-17T00:00:05Z',
        'consecutive_empty_native_scope_samples': [
            {'at_utc': '2026-10-17T00:00:01Z', 'remaining_scopes': []},
            {'at_utc': '2026-10-17T00:00:02Z', 'remaining_scopes': []}],
        'consecutive_empty_scope_samples_after_guard_stop': [
            {'at_utc': '2026-10-17T00:00:03Z', 'remaining_scopes': []},
            {'at_utc': '2026-10-17T00:00:04Z', 'remaining_scopes': []}]}
    proof = {'restored_members_verified': 73, 'app_members': 50, 'etc_delta_members': 23,
        'cross_path_hardlink_verified': True, 'exact_hardlink_header_mode_normalized': True,
        'raw_alias_mode': '0o644', 'canonical_regular_mode': '0o600', 'candidate_code_executed': False}
    commands = []
    for i in range(3):
        path = Path(output) / ('restore-command-' + str(i) + '.json')
        write(path, {'return_code': 0, 'stderr': '', 'stdout': json.dumps(proof) if i == 2 else ''})
        commands.append({'path': str(path), 'sha256': sha256(path)})
    ctrf = {'results': {'summary': {'tests': 5, 'passed': 5, 'failed': 0, 'skipped': 0, 'pending': 0, 'other': 0},
        'tests': [{'name': name, 'status': 'passed'} for name in audit['official_test_names']]}}
    evidence = dict(zip(names[:5], [original, accepted, restore, launch, state]))
    for name in ('original_result', 'restore_manifest'):
        write(root / audit[name], evidence[name])
    bound = {str(root / audit[name]): sha256(root / audit[name]) for name in ('original_result', 'restore_manifest')}
    for i in range(42):
        path = root / ('source-' + str(i)); path.write_text('unchanged source fixture')
        bound[str(path)] = sha256(path)
    claim = {'pid': 123, 'startticks': '456', 'command': command, 'model_calls': 0,
             'native_output': output, 'bound_sha256': bound}
    review = {'key': key, 'model': model, 'seed': 1, 'task_checksum': 'fixed-task',
        'root_launch': deepcopy(launch), 'parent_state': deepcopy(state),
        'native_result': {'path': str(root / audit['accepted_result'])}, 'resolver_unchanged': True,
        'actual_execution_protocol': {'no_candidate_install_service_or_reexecution': True},
        'strict_restore_proof': proof, 'exact_header_normalization': {
            'candidate_chmod_or_link_split': False, 'other72_mode_checks_unchanged': True},
        'restore_commands': commands, 'official_verifier': {'ctrf_binding': {}},
        'source_recheck': {'bound_files': 44, 'all_unchanged': True,
            'entries': [{'path': p, 'sha256': h, 'unchanged': True} for p, h in bound.items()]}}
    evidence.update(execution_claim=claim, execution_review=review, ctrf=ctrf)
    # The native result must be named result.json; all evidence paths remain explicit.
    audit['accepted_result'] = 'fixture/result.json'
    review['native_result']['path'] = str(root / audit['accepted_result'])
    return audit, previous, {'task_id': 'git-leak-recovery', 'seed': 1, 'task_checksum': 'fixed-task'}, evidence


def persist(root, audit, evidence):
    for name, value in evidence.items():
        if name != 'execution_review':
            write(root / audit[name], value)
            audit[name + '_sha256'] = sha256(root / audit[name])
    review = evidence['execution_review']
    review['native_result']['sha256'] = audit['accepted_result_sha256']
    review['official_verifier']['ctrf_binding']['sha256'] = audit['ctrf_sha256']
    write(root / audit['execution_review'], review)
    audit['execution_review_sha256'] = sha256(root / audit['execution_review'])


def integration_examples():
    with TemporaryDirectory(prefix='apex-terminal445-artificial-') as directory:
        root = Path(directory); grade, previous, entry, evidence = fixture(root)
        persist(root, grade, evidence)
        nginx = {name: 'nginx/' + name + '.json' for name in (
            'original_result', 'accepted_result', 'restore_manifest', 'parent_launch', 'parent_state', 'execution_claim')}
        nginx['accepted_result'] = 'nginx/result.json'
        nginx.update(key='nginx-request-logging/seed0', task_checksum='fixed-task',
                     parent_script_sha256='nginx-script', reason='Existing artificial nginx approval')
        old = deepcopy(previous); old['path'] = str(root / nginx['original_result']); nginx['original_invalid'] = old
        original = deepcopy(evidence['original_result']); original['config']['agent']['kwargs']['seed'] = 0
        accepted = deepcopy(original); accepted.update(exception_info=None, verifier_result={'rewards': {'reward': 0}})
        restore = {'original_result': old['path'], 'model': 'apex-terminal250', 'seed': 0,
            'task_checksum': 'fixed-task', 'no_install_or_service_start': True,
            'resolver_policy': {'excluded': '/etc/resolv.conf', 'use_candidate_file_as_runtime_resolver': False}}
        launch = {'root_reviewed': True, 'pid': 1240267, 'startticks': '869176365', 'script_sha256': 'nginx-script'}
        state = {'pid': 1240267, 'startticks': '869176365', 'state': 'finished_pending_review',
            'child_returncode': 0, 'lock_held': False, 'native_result_exists': True, 'native_reward': 0,
            'original_and_restore_files_unchanged': True, 'exception_type': None, 'new_model_calls': 0,
            'bootstrap_cpu_recovery': True, 'native_output': str((root / nginx['accepted_result']).parent),
            'consecutive_empty_scope_samples': [{'remaining_cpu_scopes': []}, {'remaining_cpu_scopes': []}],
            'released_at_utc': '2026-10-17T00:00:05Z'}
        source = root / 'source-0'
        claim = {'pid': 1240267, 'startticks': '869176365', 'script_sha256': 'nginx-script',
                 'bound_file_sha256': {str(source): sha256(source)}}
        for name, value in zip(('original_result', 'accepted_result', 'restore_manifest', 'parent_launch',
                               'parent_state', 'execution_claim'), (original, accepted, restore, launch, state, claim)):
            write(root / nginx[name], value); nginx[name + '_sha256'] = sha256(root / nginx[name])
        task_ids = ['nginx-request-logging', 'git-leak-recovery'] + ['task-' + str(i) for i in range(87)]
        entries = [{'key': task + '/seed' + str(seed), 'task_id': task, 'seed': seed,
            'task_checksum': 'fixed-task', 'trial_config': {'agent': {'model_name': 'apex-terminal250'}}}
            for task in task_ids for seed in range(5)]
        scores = {row['key']: {'path': 'untouched', 'valid': True, 'reward': 0,
                               'exception': None, 'verifier_issue': None} for row in entries}
        scores[nginx['key']] = deepcopy(old); scores[grade['key']] = deepcopy(previous)
        unknown = 'task-0/seed0'; scores[unknown].update(valid=False, reward=None, exception='Unreviewed')
        raw = {'model': 'apex-terminal250', 'expected': 445, 'scores': scores, 'valid_scored': 442,
            'active': {}, 'pending': [], 'terminal': dict.fromkeys(scores, 'finished'),
            'state': 'all445_attempts_finished', 'complete': False, 'primary_mean_percent': None,
            'updated_at_utc': 'artificial snapshot'}
        write(root / 'raw.json', raw)
        write(root / 'tasks.json', {'task_ids': task_ids, 'expected': 445, 'entries': entries})
        manifest = {'model': 'apex-terminal250', 'source_summary': 'raw.json', 'task_manifest': 'tasks.json',
            'task_manifest_sha256': sha256(root / 'tasks.json'), 'approved_native_zero': nginx}
        write(root / 'manifest.json', manifest)
        legacy = collect(root, root / 'manifest.json')
        assert legacy['valid_scored'] == 443 and legacy['audited_native_zero_count'] == 1
        assert legacy['audited_native_grade_count'] == 0 and legacy['scores'][grade['key']] == previous
        manifest['approved_native_grades'] = [grade]; write(root / 'manifest.json', manifest)
        source_bytes = (root / 'raw.json').read_bytes()
        updated = collect(root, root / 'manifest.json')
        assert updated['valid_scored'] == 444 and updated['audited_native_grade_one_count'] == 1
        assert updated['scores'][grade['key']]['reward'] == 1.0 and not updated['complete']
        assert updated['scores'][unknown]['reward'] is None
        assert all(updated['scores'][key] == row for key, row in scores.items() if key not in (nginx['key'], grade['key']))
        assert (root / 'raw.json').read_bytes() == source_bytes
        manifest['approved_native_grades'] = [grade, grade]; write(root / 'manifest.json', manifest)
        try:
            collect(root, root / 'manifest.json')
            raise RuntimeError('Duplicate explicit approval accepted')
        except AssertionError:
            pass
        return {'old_manifest_and_nginx_native_zero_compatible': True,
                'native_one_overlays_only_approved_row_and_preserves_other_nulls': True,
                'original_source_bytes_unchanged': True, 'duplicate_explicit_key_rejected': True}


def main():
    checks = {}
    cases = {
        'wrong_model_rejected': lambda a, p, e: e['accepted_result']['config']['agent'].update(model_name='foreign'),
        'wrong_seed_rejected': lambda a, p, e: e['accepted_result']['config']['agent']['kwargs'].update(seed=2),
        'wrong_task_checksum_rejected': lambda a, p, e: e['accepted_result'].update(task_checksum='foreign'),
        'wrong_accepted_source_path_rejected': lambda a, p, e: a.update(accepted_result='foreign/result.json'),
        'unapproved_native_reward_rejected': lambda a, p, e: e['accepted_result']['verifier_result']['rewards'].update(reward=0),
        'changed_original_invalid_rejected': lambda a, p, e: p.update(exception='foreign'),
        'missing_official_test_rejected': lambda a, p, e: e['ctrf']['results']['tests'].pop(),
        'candidate_chmod_rejected': lambda a, p, e: e['restore_manifest']['mode_audit'].update(candidate_chmod_or_hardlink_split=True),
        'incomplete_restore_rejected': lambda a, p, e: e['execution_review']['strict_restore_proof'].update(restored_members_verified=72),
        'scope_not_drained_rejected': lambda a, p, e: e['parent_state']['consecutive_empty_native_scope_samples'][0].update(remaining_scopes=['busy']),
        'wrong_source_binding_rejected': lambda a, p, e: e['execution_claim']['bound_sha256'].update({next(iter(e['execution_claim']['bound_sha256'])): 'wrong'}),
    }
    for name, mutate in [(None, None)] + list(cases.items()):
        with TemporaryDirectory(prefix='apex-terminal-audit-fixture-') as directory:
            root = Path(directory); audit, previous, entry, evidence = fixture(root)
            if mutate:
                mutate(audit, previous, evidence)
            persist(root, audit, evidence)
            try:
                reward = approved_native_grade(root, audit, previous, entry, 'apex-terminal250')
            except AssertionError:
                assert mutate, 'Valid artificial native1 was rejected'
                checks[name] = True
            else:
                assert not mutate, 'Broken artificial evidence was accepted: ' + str(name)
                assert reward == 1.0 and previous['reward'] is None
                checks['original_native_one_preserved_and_raw_null_unchanged'] = True
    with TemporaryDirectory(prefix='apex-terminal-null-stderr-artificial-') as directory:
        root = Path(directory); audit, previous, entry, evidence = fixture(root)
        for command in evidence['execution_review']['restore_commands']:
            path = Path(command['path']); value = json.loads(path.read_text()); value['stderr'] = None
            write(path, value); command['sha256'] = sha256(path)
        persist(root, audit, evidence)
        assert approved_native_grade(root, audit, previous, entry, 'apex-terminal250') == 1.0
        checks['successful_restore_null_stderr_accepted'] = True
    checks.update(integration_examples())
    print(json.dumps({'artificial_checks': checks, 'passed': len(checks),
                      'real_summary_runs': 0, 'new_native_runs': 0, 'new_model_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
