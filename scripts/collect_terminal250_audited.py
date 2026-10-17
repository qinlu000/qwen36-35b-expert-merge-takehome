"""Read one Terminal445 snapshot and overlay explicitly approved saved-candidate native grades."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_bytes())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(root, filename, expected):
    path = root / filename
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, 'Approved evidence changed: ' + str(path)
    return json.loads(data)


def valid(row):
    return (row is not None and row.get('valid') is True
            and type(row.get('reward')) in (int, float) and row['reward'] in (0, 1))


def approved_native_grade(root, audit, previous, entry, model):
    """Validate the fixed grade-only evidence; return its original native reward."""
    key, seed = audit['key'], audit['seed']
    assert key == entry['task_id'] + '/seed' + str(seed) and entry['seed'] == seed
    assert audit['model'] == model and previous == audit['original_invalid'], 'Original invalid row changed'
    assert previous['valid'] is False and previous['reward'] is None
    assert Path(previous['path']) == root / audit['original_result']
    evidence = {name: pinned(root, audit[name], audit[name + '_sha256']) for name in (
        'original_result', 'accepted_result', 'restore_manifest', 'parent_launch',
        'parent_state', 'execution_claim', 'execution_review', 'ctrf')}
    original, accepted, restore = (evidence[name] for name in ('original_result', 'accepted_result', 'restore_manifest'))
    launch, state, claim, review = (evidence[name] for name in (
        'parent_launch', 'parent_state', 'execution_claim', 'execution_review'))
    assert original['verifier_result'] is None and original['exception_info']['exception_type'] == previous['exception']
    assert accepted['exception_info'] is None
    reward = accepted['verifier_result']['rewards']['reward']
    assert type(reward) in (int, float) and reward in (0, 1) and reward == audit['expected_native_reward']
    for result in (original, accepted):
        assert result['task_checksum'] == entry['task_checksum'] == audit['task_checksum']
        config = result['config']
        assert config['agent']['model_name'] == model and config['agent']['kwargs']['seed'] == seed
        assert config['agent']['override_timeout_sec'] == 1800 and config['timeout_multiplier'] == 1
        env = config['environment']
        assert (env['override_cpus'], env['override_memory_mb'], env['override_gpus']) == (4, 8192, 0)
        assert env['cpu_enforcement_policy'] == env['memory_enforcement_policy'] == 'limit'
        assert config['verifier']['override_timeout_sec'] == 900 and config['verifier'].get('max_timeout_sec') is None
    assert accepted['config']['environment']['kwargs']['baseline_cpu_offset'] == 0
    assert accepted['config']['environment']['kwargs']['baseline_cpu_slots'] == 1
    assert restore['original_result'] == str(root / audit['original_result'])
    assert (restore['model'], restore['seed'], restore['task_checksum']) == (model, seed, audit['task_checksum'])
    assert restore['no_install_or_service_start'] and restore['new_model_calls'] == 0
    assert restore['resolver_policy'] == {'excluded': '/etc/resolv.conf', 'retain_frozen_runtime_policy': True}
    mode = restore['mode_audit']
    assert mode['key'] == key and mode['alias'] == '/etc/apt/apt.conf.d/01-vendor-ubuntu'
    assert mode['regular_target'] == '/app/repo/.git/info/refs'
    assert mode['raw_alias_mode'] == '0o644' and mode['canonical_mode'] == '0o600'
    assert mode['candidate_chmod_or_hardlink_split'] is False and mode['all_other_mode_checks_unchanged']
    assert launch['root_and_independent_review_passed'] and launch['new_model_calls'] == 0
    assert launch['pid'] == state['pid'] == claim['pid'] == audit['parent_pid']
    assert launch['startticks'] == state['startticks'] == claim['startticks'] == audit['parent_startticks']
    assert launch['script_sha256'] == audit['parent_script_sha256']
    assert launch['manifest_sha256'] == audit['parent_manifest_sha256']
    assert launch['frozen_parent_sha256'] == audit['frozen_parent_sha256']
    assert launch['cpu_ids'] == [92, 93, 94, 95] and launch['logical_offset'] == 0
    assert launch['memory_mib'] == 8192 and launch['verifier_seconds'] == 900
    assert state['command'] == claim['command'] and state['model_calls'] == claim['model_calls'] == 0
    for flag, filename in (('--original-result', 'original_result'), ('--restore-manifest', 'restore_manifest')):
        assert state['command'][state['command'].index(flag) + 1] == str(root / audit[filename])
    assert Path(state['native_output']) / 'result.json' == root / audit['accepted_result']
    assert claim['native_output'] == state['native_output']
    assert state['state'] == 'finished_pending_root_review' and state['child_returncode'] == 0
    assert state['native_reward'] == reward and state['exception_type'] is None
    assert state['original_and_restore_unchanged'] and not state['lock_held'] and not state['remaining_scopes']
    guard = state['guard_observed']
    assert guard['affinities'] and all(cpus == [92, 93, 94, 95] for cpus in guard['affinities'].values())
    assert guard['memory_max'] == 32 * 1024 ** 2 and guard['memory_swap_max'] == 0
    native = state['consecutive_empty_native_scope_samples']
    drained = state['consecutive_empty_scope_samples_after_guard_stop']
    assert state['guard_stopped'] and len(native) == len(drained) == 2
    assert all(not row['remaining_scopes'] for row in native + drained)
    assert native[0]['at_utc'] < native[1]['at_utc'] < drained[0]['at_utc'] < drained[1]['at_utc'] < state['released_at_utc']
    assert (review['key'], review['model'], review['seed'], review['task_checksum']) == (key, model, seed, audit['task_checksum'])
    assert review['root_launch'] == launch and review['parent_state'] == state
    assert review['native_result']['path'] == str(root / audit['accepted_result'])
    assert review['native_result']['sha256'] == audit['accepted_result_sha256']
    assert review['resolver_unchanged'] and review['actual_execution_protocol']['no_candidate_install_service_or_reexecution']
    proof = review['strict_restore_proof']
    assert (proof['restored_members_verified'], proof['app_members'], proof['etc_delta_members']) == (73, 50, 23)
    assert proof['cross_path_hardlink_verified'] and proof['exact_hardlink_header_mode_normalized']
    assert proof['raw_alias_mode'] == '0o644' and proof['canonical_regular_mode'] == '0o600'
    assert proof['candidate_code_executed'] is False
    header = review['exact_header_normalization']
    assert header['candidate_chmod_or_link_split'] is False and header['other72_mode_checks_unchanged']
    commands = review['restore_commands']
    assert len(commands) == 3
    for command in commands:
        path = Path(command['path'])
        assert path.parent == Path(state['native_output']) and sha256(path) == command['sha256']
        result = read(path)
        assert result['return_code'] == 0 and result['stderr'] in (None, '')
    assert json.loads(read(Path(commands[2]['path']))['stdout']) == proof
    ctrf = evidence['ctrf']['results']
    assert {name: ctrf['summary'][name] for name in ('tests', 'passed', 'failed', 'skipped', 'pending', 'other')} == {
        'tests': 5, 'passed': 5, 'failed': 0, 'skipped': 0, 'pending': 0, 'other': 0}
    assert len(ctrf['tests']) == 5 and len({row['name'] for row in ctrf['tests']}) == 5
    assert {row['name'] for row in ctrf['tests']} == set(audit['official_test_names'])
    assert all(row['status'] == 'passed' for row in ctrf['tests'])
    assert review['official_verifier']['ctrf_binding']['sha256'] == audit['ctrf_sha256']
    bound = claim['bound_sha256']
    recheck = review['source_recheck']
    assert len(bound) == recheck['bound_files'] == len(recheck['entries']) == 44 and recheck['all_unchanged']
    assert {row['path']: row['sha256'] for row in recheck['entries']} == bound
    assert all(row['unchanged'] for row in recheck['entries'])
    assert all(sha256(Path(path)) == expected for path, expected in bound.items())
    assert bound[str(root / audit['original_result'])] == audit['original_result_sha256']
    assert bound[str(root / audit['restore_manifest'])] == audit['restore_manifest_sha256']
    return reward


def collect(root, manifest_path):
    manifest = read(manifest_path)
    assert manifest['model'] == 'apex-terminal250', 'This audit is only for the Terminal expert'
    source_path = root / manifest['source_summary']
    source_bytes = source_path.read_bytes()
    raw = json.loads(source_bytes)
    assert raw['model'] == manifest['model'] and raw['expected'] == 445
    tasks = pinned(root, manifest['task_manifest'], manifest['task_manifest_sha256'])
    task_ids = tasks['task_ids']
    assert len(task_ids) == len(set(task_ids)) == 89 and tasks['expected'] == 445
    expected = {task + '/seed' + str(seed) for task in task_ids for seed in range(5)}
    entries = {row['key']: row for row in tasks['entries']}
    assert len(tasks['entries']) == len(entries) == 445 and set(entries) == expected
    for key, entry in entries.items():
        assert key == entry['task_id'] + '/seed' + str(entry['seed'])
        assert entry['trial_config']['agent']['model_name'] == manifest['model']
    active, pending, terminal = set(raw['active']), set(raw['pending']), set(raw['terminal'])
    assert len(pending) == len(raw['pending'])
    assert not (active & pending or active & terminal or pending & terminal)
    assert active | pending | terminal == expected
    assert set(raw['scores']) == terminal

    audit = manifest['approved_native_zero']
    key = audit['key']
    assert key == 'nginx-request-logging/seed0' and key in terminal
    previous = raw['scores'][key]
    assert previous == audit['original_invalid'], 'Original invalid row changed'
    assert Path(previous['path']) == root / audit['original_result']
    original = pinned(root, audit['original_result'], audit['original_result_sha256'])
    accepted = pinned(root, audit['accepted_result'], audit['accepted_result_sha256'])
    restore = pinned(root, audit['restore_manifest'], audit['restore_manifest_sha256'])
    launch = pinned(root, audit['parent_launch'], audit['parent_launch_sha256'])
    state = pinned(root, audit['parent_state'], audit['parent_state_sha256'])
    claim = pinned(root, audit['execution_claim'], audit['execution_claim_sha256'])
    assert original['verifier_result'] is None and original['exception_info']['exception_type'] == 'RuntimeError'
    assert accepted['exception_info'] is None
    assert type(accepted['verifier_result']['rewards']['reward']) in (int, float)
    assert accepted['verifier_result']['rewards']['reward'] == 0
    for result in (original, accepted):
        assert result['task_checksum'] == entries[key]['task_checksum'] == audit['task_checksum']
        config = result['config']
        assert config['agent']['model_name'] == manifest['model']
        assert config['agent']['kwargs']['seed'] == 0
        assert config['agent']['override_timeout_sec'] == 1800
        assert config['environment']['override_cpus'] == 4
        assert config['environment']['override_memory_mb'] == 8192
        assert config['environment']['cpu_enforcement_policy'] == 'limit'
        assert config['environment']['memory_enforcement_policy'] == 'limit'
        assert config['verifier']['override_timeout_sec'] == 900
        assert config['verifier'].get('max_timeout_sec') is None and config['timeout_multiplier'] == 1
    assert restore['original_result'] == str(root / audit['original_result'])
    assert restore['model'] == manifest['model'] and restore['seed'] == 0
    assert restore['task_checksum'] == audit['task_checksum'] and restore['no_install_or_service_start']
    assert restore['resolver_policy']['excluded'] == '/etc/resolv.conf'
    assert not restore['resolver_policy']['use_candidate_file_as_runtime_resolver']
    assert launch['root_reviewed'] and launch['pid'] == state['pid'] == claim['pid'] == 1240267
    assert launch['startticks'] == state['startticks'] == claim['startticks'] == '869176365'
    assert launch['script_sha256'] == claim['script_sha256'] == audit['parent_script_sha256']
    assert state['state'] == 'finished_pending_review' and state['child_returncode'] == 0
    assert not state['lock_held'] and state['native_result_exists'] and state['native_reward'] == 0
    assert state['original_and_restore_files_unchanged'] and state['exception_type'] is None
    assert state['new_model_calls'] == 0 and state['bootstrap_cpu_recovery'] is True
    assert Path(state['native_output']) / 'result.json' == root / audit['accepted_result']
    assert len(state['consecutive_empty_scope_samples']) == 2
    assert all(not row['remaining_cpu_scopes'] for row in state['consecutive_empty_scope_samples'])
    assert state['released_at_utc'] and all(sha256(Path(path)) == expected_sha
        for path, expected_sha in claim['bound_file_sha256'].items())

    summary = copy.deepcopy(raw)
    summary['scores'][key].update(valid=True, reward=0, exception=None, verifier_issue=None,
        path=str(root / audit['accepted_result']), accepted_path=str(root / audit['accepted_result']),
        original_invalid=copy.deepcopy(previous), original_result=str(root / audit['original_result']),
        audit_source=str(manifest_path), audit_reason=audit['reason'],
        audit_provenance={name: audit[name] for name in audit if name not in ('original_invalid', 'reason')},
        audit_kind='root_approved_grade_only_of_exact_saved_candidate', derived=False)
    audited_keys = {key}
    grades = manifest.get('approved_native_grades', [])
    for audit in grades:
        key = audit['key']
        assert key not in audited_keys and key in terminal, 'Duplicate or unfinished approved native grade'
        previous = raw['scores'][key]
        reward = approved_native_grade(root, audit, previous, entries[key], manifest['model'])
        summary['scores'][key].update(valid=True, reward=reward, exception=None, verifier_issue=None,
            path=str(root / audit['accepted_result']), accepted_path=str(root / audit['accepted_result']),
            original_invalid=copy.deepcopy(previous), original_result=str(root / audit['original_result']),
            audit_source=str(manifest_path), audit_reason=audit['reason'],
            audit_provenance={name: audit[name] for name in audit if name not in ('original_invalid', 'reason')},
            audit_kind='root_approved_grade_only_of_exact_saved_candidate', derived=False)
        audited_keys.add(key)
    assert all(summary['scores'][name] == row for name, row in raw['scores'].items() if name not in audited_keys)
    rows = {name: row for name, row in summary['scores'].items() if valid(row)}
    assert raw['valid_scored'] == sum(valid(row) for row in raw['scores'].values())
    per_seed = []
    for seed in range(5):
        selected = [row for name, row in rows.items() if entries[name]['seed'] == seed]
        correct = sum(row['reward'] for row in selected)
        per_seed.append({'seed': seed, 'expected': 89, 'valid_scored': len(selected),
                         'correct': correct, 'score_percent': 100 * correct / 89 if len(selected) == 89 else None})
    gates = {'all445_manifest_keys_unique': len(entries) == 445,
             'all445_original_attempts_terminal': terminal == expected,
             'original_active_empty': raw['active'] == {}, 'original_pending_empty': raw['pending'] == [],
             'owner_final_state': raw['state'] == 'all445_attempts_finished',
             'all445_valid': len(rows) == 445, 'each_seed89_valid': all(row['valid_scored'] == 89 for row in per_seed)}
    complete = all(gates.values())
    values = [row['score_percent'] for row in per_seed]
    summary.update(collected_at_utc=datetime.now(timezone.utc).isoformat(),
        source_summary=str(source_path), source_summary_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_updated_at_utc=raw['updated_at_utc'], original_valid_scored=raw['valid_scored'],
        original_complete=raw['complete'], original_primary_mean_percent=raw['primary_mean_percent'],
        audit_source=str(manifest_path), audit_manifest_sha256=sha256(manifest_path),
        task_manifest=str(root / manifest['task_manifest']), task_manifest_sha256=manifest['task_manifest_sha256'],
        audited_native_zero_count=1, audited_native_grade_count=len(grades),
        audited_native_grade_one_count=sum(summary['scores'][row['key']]['reward'] == 1 for row in grades),
        valid_scored=len(rows), complete=complete,
        resolved=sum(row['reward'] for row in rows.values()), per_seed=per_seed,
        primary_mean_percent=statistics.mean(values) if complete else None,
        sample_sd_percent_ddof1=statistics.stdev(values) if complete else None,
        infrastructure_unscored_finished=len(terminal) - len(rows), completion_gates=gates,
        all_other_score_rows_unchanged=True, source_files_read_only=True,
        new_model_calls=0, new_native_verifier_runs=0,
        selection_policy='Exact explicitly root-approved saved-candidate native grades; no reward search or cross-model reuse.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path, default=Path('configs/eval/terminal250_audited_20261017.json'))
    args = parser.parse_args()
    root = args.project.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    summary = collect(root, manifest)
    output = root / read(manifest)['output']
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'summary.tmp'
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output / 'summary.json')
    print(json.dumps({key: summary[key] for key in ['collected_at_utc', 'expected', 'valid_scored',
        'original_valid_scored', 'audited_native_zero_count', 'audited_native_grade_count',
        'audited_native_grade_one_count', 'resolved', 'complete',
        'primary_mean_percent', 'sample_sd_percent_ddof1', 'completion_gates']}))
