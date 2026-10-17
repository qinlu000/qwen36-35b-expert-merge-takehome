"""One read-only source snapshot with explicitly approved, fixed-result audits."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_scopes(cpus):
    found = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            group = (process / 'cgroup').read_text()
            if (any(prefix in group for prefix in
                    ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and set(cpus).intersection(os.sched_getaffinity(int(process.name)))):
                found.add(group.strip().split('/')[-1])
        except (OSError, ProcessLookupError):
            pass
    return sorted(found)


def valid_handoff(marker, handoff, cpus):
    if (handoff.get('swe_expert_all_cpu_and_model_consumers_finished') is not True
            or handoff.get('base_scopes_on_target_cpus') != []
            or sorted(handoff.get('cpu_ids', [])) != sorted(cpus)):
        return False
    try:
        marker_at = datetime.fromisoformat(marker['at'].replace('Z', '+00:00'))
        handoff_at = datetime.fromisoformat(handoff['at'].replace('Z', '+00:00'))
        return (marker_at.utcoffset() is not None and handoff_at.utcoffset() is not None
                and handoff_at >= marker_at)
    except (KeyError, ValueError):
        return False


def aware_time(value):
    if not isinstance(value, str):
        raise ValueError('Handoff timestamp must be text')
    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.utcoffset() is None:
        raise ValueError('Handoff evidence requires an explicit timezone')
    return value


def valid_source_handoff(root, manifest, marker, handoff, ids):
    """Verify saved source-only release evidence, never treat AVG scopes as empty."""
    if handoff.get('schema') != 'swe_source_cpu_handoff_v1':
        return False
    try:
        cpus = manifest['source_cpu_ids']
        avg = (root / manifest['source_specific_cpu_handoff']).parent
        evidence = avg / 'source-cpu-release-checkpoints'

        def checkpoint(path):
            path = root / path
            if path.resolve().parent != evidence.resolve():
                raise ValueError('Source checkpoint is outside the immutable evidence directory')
            value = read(path)
            active, terminal = value['active'], value['terminal']
            if (value['model'] != manifest['model'] or value['checkpoint'] != manifest['checkpoint']
                    or value['expected'] != 51 or value['pending'] != []
                    or set(active).intersection(terminal)
                    or set(active).union(terminal) != set(ids)
                    or len(value['tasks']) != 51
                    or {row['task_id'] for row in value['tasks']} != set(ids)
                    or any(row['cpu'] not in cpus for row in active.values())):
                raise ValueError('Source checkpoint identity or 51-ID accounting mismatch')
            return value

        if (handoff['source'] != manifest['source_output']
                or handoff['source_all_cpu_and_model_consumers_finished'] is not True
                or handoff['source_terminal'] != 51 or handoff['source_active'] != {}
                or handoff['source_pending'] != [] or sorted(handoff['cpu_ids']) != sorted(cpus)
                or handoff['source_model_marker'] != marker
                or marker.get('model') != manifest['model'] or marker.get('expected') != 51
                or marker.get('model_consumer_finished') is not True
                or marker.get('scoring_may_still_be_running') is not False):
            return False
        finished_at, marker_at = aware_time(handoff['at']), aware_time(marker['at'])
        full_path = evidence / 'full-source-finished.json'
        if root / handoff['source_checkpoint_snapshot'] != full_path:
            return False
        full = checkpoint(handoff['source_checkpoint_snapshot'])
        if full['active'] != {} or set(full['terminal']) != set(ids):
            return False
        if not aware_time(full['as_of']) <= marker_at <= finished_at:
            return False
        proofs = handoff['per_cpu_release_before_avg_admission']
        if len(proofs) != len(cpus) or sorted(row['cpu'] for row in proofs) != sorted(cpus):
            return False
        empty_at = {}
        for proof in proofs:
            cpu = proof['cpu']
            saved = checkpoint(proof['source_checkpoint_snapshot'])
            active_cpus = sorted({row['cpu'] for row in saved['active'].values()})
            when = aware_time(proof['scope_empty_at'])
            if (proof['permanent_release'] is not True
                    or proof['actual_scopes_before_avg_admission'] != []
                    or proof['source_pending'] != 0 or proof['source_active'] != len(saved['active'])
                    or proof['source_terminal'] != len(saved['terminal'])
                    or proof['source_active_cpu_ids'] != active_cpus or cpu in active_cpus
                    or proof['source_checkpoint_as_of'] != saved['as_of']
                    or not aware_time(saved['as_of']) <= when <= finished_at):
                return False
            empty_at[cpu] = when
        # These are bounded, already-saved configs/journals, not task logs or answers.
        # A CPU not yet used by AVG has no acquisition to order against its release.
        for name in ids:
            path = avg / 'generation' / name / 'config.json'
            if not path.exists():
                continue
            config = read(path)
            cpu = config['environment']['kwargs']['baseline_cpu_offset']
            started = read(avg / 'audit' / (name + '.generation.started.json'))
            if (config['agent']['model_name'] != 'openai/apex-avg64'
                    or started['task'] != name or started['phase'] != 'generation'
                    or empty_at[cpu] > aware_time(started['started_at'])):
                return False
        current_avg_scopes = handoff['current_avg_scopes_on_released_cpus']
        return (isinstance(current_avg_scopes, list)
                and handoff['whole_pool_empty_at_this_time'] is (not current_avg_scopes))
    except (KeyError, ValueError, TypeError, OSError):
        return False


def approved_row(root, source, audit):
    name = audit['task_id']
    original = root / audit['original_result']
    accepted = root / audit['accepted_result']
    patch = root / audit['source_patch']
    assert original == source / 'replay' / name / 'result.json', 'Original result source mismatch'
    assert patch == source / 'generation' / name / 'agent/model.patch', 'Patch source mismatch'
    assert accepted.parent.name == name and accepted.name == 'result.json', 'Accepted result task mismatch'
    assert sha256(original) == audit['original_result_sha256'], 'Original result bytes changed'
    assert sha256(accepted) == audit['accepted_result_sha256'], 'Accepted result bytes changed'
    assert patch.stat().st_size == audit['patch_bytes']
    assert sha256(patch) == audit['patch_sha256'], 'Frozen patch changed'
    for result_path in (original, accepted):
        config = read(result_path.parent / 'config.json')
        assert Path(config['task']['path']) == source / 'tasks' / name, 'Frozen task source mismatch'
        assert config['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
        assert Path(config['agent']['kwargs']['source_job']) == source / 'generation', 'Generation source mismatch'
        replay = read(result_path.parent / 'agent/replay.json')
        assert replay['task'] == name
        if audit['patch_bytes'] == 0:
            assert replay['patch'] is None, 'Empty patch replay identity mismatch'
        else:
            assert Path(replay['patch']) == patch and replay['apply_rc'] == 0
    result = read(accepted)
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    assert type(reward) in (int, float) and reward == 0, 'Accepted native reward must be zero'
    assert not result.get('exception_info'), 'Accepted replay has a Harbor exception'
    assert float((accepted.parent / 'verifier/reward.txt').read_text()) == 0
    return {'task_id': name, 'status': 'valid_scored', 'reward': reward,
        'native_reward': reward, 'invalid_reason': None, 'accepted_result': str(accepted),
        'result': str(accepted), 'finished_at': result.get('finished_at'),
        'previous_invalid_result': str(original), 'audit_reason': audit['reason'],
        'source_patch_sha256': audit['patch_sha256']}


def mocha_test_map(report):
    """Mirror this task's original parser; reject conflicting duplicate names."""
    tests, entries = {}, 0
    for key, status in [('passes', 'PASSED'), ('pending', 'SKIPPED'), ('failures', 'FAILED')]:
        for test in report.get(key, []):
            file = re.match(r'^(?:/app/)?(.*)$', test.get('file', '')).group(1)
            title = test.get('fullTitle', '')
            match = re.search(r'(\S+)::', title)
            if match:
                file = match.group(1)
            name = file + ' | ' + title.replace(file + '::', '')
            assert name not in tests or tests[name] == status, 'Conflicting duplicate test status'
            tests[name] = status
            entries += 1
    assert entries == report['stats']['tests'] == 335
    for key, stat in [('passes', 'passes'), ('pending', 'pending'), ('failures', 'failures')]:
        assert len(report[key]) == report['stats'][stat]
    assert [report['stats'][key] for key in ['passes', 'pending', 'failures']] == [331, 0, 4]
    return tests


def approved_official_report_row(root, source, audit, model):
    """One complete NodeBB report, distinct from a native reward-zero result."""
    name = audit['task_id']
    assert name == ('instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-'
                    'vf2cf3cbd463b7ad942381f1c6d077626485a1e9e')
    original, accepted = root / audit['original_result'], root / audit['accepted_result']
    patch = root / audit['source_patch']
    task = source / 'tasks' / name
    assert original == source / 'replay' / name / 'result.json', 'Original result source mismatch'
    assert patch == source / 'generation' / name / 'agent/model.patch', 'Patch source mismatch'
    assert accepted.parent.name == name and accepted.name == 'result.json'
    assert sha256(original) == audit['original_result_sha256']
    assert sha256(accepted) == audit['accepted_result_sha256']
    assert patch.stat().st_size == audit['patch_bytes'] and sha256(patch) == audit['patch_sha256'], 'Frozen patch changed'
    assert audit['audit_kind'] == 'complete_official_test_report_with_failures' and audit['audited_reward'] == 0
    paths = {key: root / audit[key] for key in ['official_parser', 'official_test_config',
        'raw_stdout', 'raw_stderr', 'raw_mocha_report', 'parsed_report', 'parse_receipt',
        'cohort_state', 'cohort_claim', 'pending_review', 'frozen_runner']}
    assert paths['official_parser'] == task / 'tests/parser.py'
    assert paths['official_test_config'] == task / 'tests/config.json'
    assert paths['pending_review'] == accepted.parent.parent.parent / 'pending-root-review.json'
    assert paths['cohort_state'] == (root / 'artifacts/recovery/swe-additional-short-tmp-20261017'
                                    '/cohort-attempt1/parent-state.json')
    assert paths['cohort_claim'] == paths['cohort_state'].with_name('execution-claim.json')
    required_files = [original, accepted, patch, *paths.values(),
        source / 'generation' / name / 'config.json', task / 'task.toml',
        *[task / 'tests' / file for file in ['test.sh', 'run_script.sh', 'test_patch.patch']]]
    for result_path in (original, accepted):
        required_files += [result_path.parent / 'config.json', result_path.parent / 'agent/replay.json']
        config = read(result_path.parent / 'config.json')
        assert Path(config['task']['path']) == task, 'Frozen task source mismatch'
        assert config['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
        assert Path(config['agent']['kwargs']['source_job']) == source / 'generation', 'Generation source mismatch'
        assert config['agent']['override_timeout_sec'] == 1800
        env = config['environment']
        assert [env['override_cpus'], env['override_memory_mb'], env['override_gpus']] == [1, 4096, 0]
        assert env['cpu_enforcement_policy'] == env['memory_enforcement_policy'] == 'limit'
        assert config['verifier']['override_timeout_sec'] == 3000
        replay = read(result_path.parent / 'agent/replay.json')
        assert replay['task'] == name and Path(replay['patch']) == patch and replay['apply_rc'] == 0
        assert read(result_path)['task_checksum'] == audit['task_checksum']
    reward_file = accepted.parent / 'verifier/reward.txt'
    if reward_file.exists():
        observed = audit['raw_reward_file']
        assert root / observed['path'] == reward_file
        assert reward_file.read_text().strip() == observed['value']
        required_files.append(reward_file)
    else:
        assert audit.get('raw_reward_file') is None
    bindings = audit['bound_sha256']
    assert all(str(path.relative_to(root)) in bindings for path in required_files), 'Missing fixed file identity'
    assert all(sha256(root / path) == digest for path, digest in bindings.items()), 'Fixed report/source bytes changed'
    generation = read(source / 'generation' / name / 'config.json')
    assert generation['agent']['model_name'] == audit['generation_model'] == 'openai/' + model
    image = root / audit['sif']
    assert image.stat().st_size == audit['sif_bytes'] and str(image.stat().st_mtime_ns) == audit['sif_mtime_ns']
    result = read(accepted)
    assert (result.get('exception_info') or {}).get('exception_type') == 'VerifierTimeoutError'
    start, finish = (aware_time(result['verifier'][key]) for key in ['started_at', 'finished_at'])
    assert (finish - start).total_seconds() >= 2999, 'Original verifier budget not exhausted naturally'
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    assert reward == audit['native_reward'], 'Raw reward identity changed; never normalize an EXIT trap'
    receipt = read(paths['parse_receipt'])
    assert receipt['schema'] == 'swe_nodebb_official_parser_read_only_v1'
    assert receipt['returncode'] == 0 and receipt['task_id'] == name
    assert receipt['candidate_calls'] == receipt['test_runs'] == receipt['model_calls'] == 0
    assert receipt['command'] == [str(root / 'artifacts/envs/harbor/bin/python'),
        str(paths['official_parser']), str(paths['raw_stdout']), str(paths['raw_stderr']), str(paths['parsed_report'])]
    assert receipt['official_parser'] == audit['official_parser'] and receipt['parser_sha256'] == sha256(paths['official_parser'])
    assert root / receipt['accepted_result'] == accepted and receipt['accepted_result_sha256'] == sha256(accepted)
    for key in ['raw_stdout', 'raw_stderr', 'raw_mocha_report', 'parsed_report']:
        assert root / receipt[key] == paths[key]
    for key, field in [('raw_stdout', 'raw_stdout_sha256'), ('raw_stderr', 'raw_stderr_sha256'),
                       ('raw_mocha_report', 'raw_mocha_sha256'), ('parsed_report', 'parsed_report_sha256')]:
        assert receipt[field] == sha256(paths[key])
    assert root / receipt['cohort_state'] == paths['cohort_state']
    assert receipt['cohort_state_sha256'] == sha256(paths['cohort_state'])
    assert root / receipt['raw_stdout_source'] == accepted.parent / 'verifier/live-run-script-stdout.txt'
    assert root / receipt['raw_stderr_source'] == accepted.parent / 'verifier/live-run-script-stderr.txt'
    assert sha256(root / receipt['raw_stdout_source']) == sha256(paths['raw_stdout'])
    assert sha256(root / receipt['raw_stderr_source']) == sha256(paths['raw_stderr'])
    reports = []
    for match in re.finditer(r'({\n.*?\n})', paths['raw_stdout'].read_text(), re.MULTILINE | re.DOTALL):
        try:
            report = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if 'stats' in report:
            reports.append(report)
    assert len(reports) == 1 and reports[0] == read(paths['raw_mocha_report']), 'Raw complete JSON identity mismatch'
    raw_tests = mocha_test_map(reports[0])
    tests = read(paths['parsed_report'])['tests']
    parsed = {test['name']: test['status'] for test in tests}
    assert len(tests) == len(parsed) == 311 and parsed == raw_tests, 'Official parsed mapping mismatch'
    config = read(paths['official_test_config'])
    def names(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return ast.literal_eval(value)
        return value
    ftp, ptp = (set(names(config[key])) for key in ['fail_to_pass', 'pass_to_pass'])
    assert len(ftp) == 4 and len(ptp) == 307 and len(ftp | ptp) == 311
    assert set(parsed) == ftp | ptp, 'Missing or extra required test identity'
    assert {key for key, value in parsed.items() if value == 'FAILED'} == ftp
    assert {key for key, value in parsed.items() if value == 'PASSED'} == ptp
    assert start <= aware_time(reports[0]['stats']['start']) <= aware_time(reports[0]['stats']['end']) <= finish
    state, claim, pending = (read(paths[key]) for key in ['cohort_state', 'cohort_claim', 'pending_review'])
    assert state['state'] == 'finished_pending_root_review' and state['lock_held'] is False
    assert state['guard_stopped'] is True and state['remaining_scopes'] == []
    assert state['pid'] == claim['pid'] and state['startticks'] == claim['startticks']
    assert claim['script_sha256'] == sha256(paths['frozen_runner'])
    assert pending['child_returncode'] == 0 and pending['original_bytes_unchanged'] is True
    assert Path(pending['result']) == accepted and pending['native_reward'] == reward
    ordered = [aware_time(result['finished_at'])]
    for key in ['consecutive_empty_native_scope_samples', 'consecutive_empty_scope_samples_after_guard_stop']:
        samples = state[key]
        assert len(samples) == 2 and all(sample['remaining_scopes'] == [] for sample in samples)
        ordered += [aware_time(sample['at_utc']) for sample in samples]
    ordered += [aware_time(state['released_at_utc']), aware_time(receipt['at_utc'])]
    assert ordered == sorted(ordered), 'Report/cleanup/parse ordering mismatch'
    return {'task_id': name, 'status': 'valid_scored', 'reward': 0, 'audited_reward': 0,
        'native_reward': reward, 'invalid_reason': None, 'accepted_result': str(accepted),
        'result': str(accepted), 'finished_at': result['finished_at'],
        'previous_invalid_result': str(original), 'audit_reason': audit['reason'],
        'source_patch_sha256': audit['patch_sha256'], 'native_reward_modified': False,
        'audit_kind': audit['audit_kind'], 'score_source': 'Explicit complete official test report audit',
        'raw_reward_file': audit.get('raw_reward_file'), 'raw_reward_file_used_as_score': False,
        'official_parsed_report': str(paths['parsed_report']), 'required_tests': 311,
        'required_passed': 307, 'required_failed': 4}


def collect(root, manifest_path, scope_reader=active_scopes):
    manifest = read(manifest_path)
    source = root / manifest['source_output']
    source_path = root / manifest['source_summary']
    data = source_path.read_bytes()
    raw = json.loads(data)
    ids = read(root / manifest['task_manifest'])['task_ids']
    assert len(ids) == len(set(ids)) == 51 and raw['expected'] == 51
    assert raw['model'] == manifest['model']
    assert raw['checkpoint'] == manifest['checkpoint']
    by_id = {row['task_id']: row for row in raw['tasks']}
    assert len(raw['tasks']) == len(by_id) == 51 and set(by_id) == set(ids)
    audits = {row['task_id']: row for row in manifest['approved_native_zero']}
    assert len(manifest['approved_native_zero']) == len(audits) and audits
    assert set(audits) <= set(ids)
    official_rows = manifest.get('approved_official_test_reports', [])
    official = {row['task_id']: row for row in official_rows}
    assert len(official_rows) == len(official) and set(official) <= set(ids)
    assert not set(official).intersection(audits), 'An audit cannot be both native-zero and parsed-report'
    rows = []
    for name in ids:
        previous = by_id[name]
        row = dict(previous)
        if name in audits:
            original = root / audits[name]['original_result']
            assert Path(previous['result']) == original, 'Source summary points to another result'
            assert previous.get('invalid_reason') == audits[name]['original_invalid_reason']
            row.update(approved_row(root, source, audits[name]))
            row.update(previous_invalid=dict(previous),
                audit_source=str(manifest_path), audit_result_bytes_pinned=True)
        elif name in official:
            audit = official[name]
            assert Path(previous['result']) == root / audit['original_result'], 'Source summary points to another result'
            assert previous.get('invalid_reason') == audit['original_invalid_reason']
            row.update(approved_official_report_row(root, source, audit, manifest['model']))
            row.update(previous_invalid=dict(previous), audit_source=str(manifest_path),
                       audit_result_bytes_pinned=True)
        elif row.get('invalid_reason') is None and row.get('status') in (None, 'valid_scored'):
            assert type(row.get('reward')) in (int, float) and row['reward'] in (0, 1)
            row['status'] = 'valid_scored'
        else:
            row['native_reward'] = row.get('reward')
            row['reward'] = None
            row['status'] = ('awaiting_generation_or_replay' if row.get('invalid_reason') == 'not_scored'
                             and name not in raw['terminal'] else 'invalid_requires_audit')
        rows.append(row)
    valid = [row for row in rows if row['status'] == 'valid_scored']
    resolved = sum(row['reward'] == 1 for row in valid)
    marker_path = root / manifest['resource_marker']
    marker = read(marker_path) if marker_path.exists() else {}
    scopes = scope_reader(manifest['source_cpu_ids'])
    assert manifest['source_cpu_handoff'] == 'artifacts/eval/avg64_swe_hard51_20261017/admission-opened.json'
    handoff_path = root / manifest['source_cpu_handoff']
    handoff = read(handoff_path) if handoff_path.exists() else {}
    handed_off = valid_handoff(marker, handoff, manifest['source_cpu_ids'])
    source_handoff_path = None
    source_handoff, source_handed_off = {}, False
    if manifest.get('source_specific_cpu_handoff'):
        assert manifest['source_specific_cpu_handoff'] == (
            'artifacts/eval/avg64_swe_hard51_20261017/source-expert-consumers-finished.json')
        source_handoff_path = root / manifest['source_specific_cpu_handoff']
        source_handoff = read(source_handoff_path) if source_handoff_path.exists() else {}
        source_handed_off = valid_source_handoff(root, manifest, marker, source_handoff, ids)
    gates = {'all51_effectively_scored': len(valid) == 51,
        'all51_original_attempts_terminal': set(raw['terminal']) == set(ids),
        'original_active_empty': raw['active'] == {}, 'original_pending_empty': raw['pending'] == [],
        'original_model_consumer_finished': marker.get('model_consumer_finished') is True,
        'original_scoring_explicitly_finished': marker.get('scoring_may_still_be_running') is False,
        'source_cpu_drain_proven': scopes == [] or handed_off or source_handed_off}
    complete = all(gates.values())
    return {'as_of': datetime.now(timezone.utc).isoformat(),
        'state': 'complete' if complete else 'audited_snapshot_incomplete',
        'model': raw['model'], 'checkpoint': raw.get('checkpoint'), 'expected': 51,
        'valid_scored': len(valid), 'unscored': 51 - len(valid), 'resolved': resolved,
        'complete': complete, 'primary_score_percent': 100 * resolved / 51 if complete else None,
        'conservative_resolved_percent': 100 * resolved / 51,
        'invalid_pending': sum(row['status'] == 'invalid_requires_audit' for row in rows),
        'awaiting_generation_or_replay': sum(row['status'] == 'awaiting_generation_or_replay' for row in rows),
        'active': raw['active'], 'pending': raw['pending'], 'terminal': raw['terminal'],
        'source_summary': str(source_path), 'source_summary_sha256': hashlib.sha256(data).hexdigest(),
        'source_as_of': raw['as_of'], 'original_valid_scored': raw['valid_scored'],
        'audit_source': str(manifest_path), 'audit_manifest_sha256': sha256(manifest_path),
        'audited_native_zero_count': len(audits), 'audited_official_test_report_count': len(official),
        'completion_gates': gates,
        'resource_marker': str(marker_path), 'resource_marker_observed': marker,
        'source_cpu_handoff': str(handoff_path), 'source_cpu_handoff_observed': handoff,
        'source_cpu_handoff_valid': handed_off,
        'source_specific_cpu_handoff': str(source_handoff_path) if source_handoff_path else None,
        'source_specific_cpu_handoff_observed': source_handoff,
        'source_specific_cpu_handoff_valid': source_handed_off,
        'active_source_cpu_scopes': scopes, 'new_model_calls': 0, 'new_replays': 0,
        'selection_policy': (str(len(audits)) + ' exact approved native-zero results; all other original validity retained; no reward search'
            + (f'; {len(official)} explicit complete official-test report audit' if official else '')),
        'tasks': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path, default=Path('configs/eval/swe249_audited_hard51_20261017.json'))
    args = parser.parse_args()
    root = args.project.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    summary = collect(root, manifest)
    output = root / read(manifest)['output']
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'summary.tmp'
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output / 'summary.json')
    print(json.dumps({key: summary[key] for key in
        ['expected', 'valid_scored', 'original_valid_scored', 'audited_native_zero_count', 'resolved', 'complete', 'primary_score_percent']}))
