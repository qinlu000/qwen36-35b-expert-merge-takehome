"""Artificial file examples for the explicit SWE audit; no task/model execution."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from collect_swe249_audited import collect, sha256, approved_official_report_row


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def report_examples():
    checks = {}
    with TemporaryDirectory(prefix='apex-swe-report-examples-') as directory:
        root = Path(directory)
        source = root / 'source'
        name = ('instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-'
                'vf2cf3cbd463b7ad942381f1c6d077626485a1e9e')
        original = source / 'replay' / name / 'result.json'
        attempt = root / 'artifacts/recovery/example' / name / 'attempt1'
        accepted = attempt / 'native' / name / 'result.json'
        task = source / 'tasks' / name
        patch = source / 'generation' / name / 'agent/model.patch'
        patch.parent.mkdir(parents=True); patch.write_text('fixed patch')
        config = {'task': {'path': str(task)}, 'agent': {'import_path': 'patch_replay:PatchReplayAgent',
            'kwargs': {'source_job': str(source / 'generation')}, 'override_timeout_sec': 1800},
            'environment': {'override_cpus': 1, 'override_memory_mb': 4096, 'override_gpus': 0,
                'cpu_enforcement_policy': 'limit', 'memory_enforcement_policy': 'limit'},
            'verifier': {'override_timeout_sec': 3000}}
        result = {'task_checksum': 'fixed-task', 'finished_at': '2026-10-17T00:50:01Z',
            'verifier': {'started_at': '2026-10-17T00:00:00Z', 'finished_at': '2026-10-17T00:50:00Z'},
            'verifier_result': None, 'exception_info': {'exception_type': 'VerifierTimeoutError'}}
        for path in (original, accepted):
            write(path, result); write(path.parent / 'config.json', config)
            write(path.parent / 'agent/replay.json', {'task': name, 'patch': str(patch), 'apply_rc': 0})
        write(source / 'generation' / name / 'config.json', {'agent': {'model_name': 'openai/fixture'}})
        ftp = ['test.js | fail-' + str(i) for i in range(4)]
        ptp = ['test.js | pass-' + str(i) for i in range(307)]
        write(task / 'tests/config.json', {'fail_to_pass': repr(ftp), 'pass_to_pass': json.dumps(ptp)})
        for file in ['task.toml', 'tests/parser.py', 'tests/test.sh', 'tests/run_script.sh', 'tests/test_patch.patch']:
            p = task / file; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('fixture only')
        evidence = root / 'evidence'; evidence.mkdir()
        raw = {'stats': {'tests': 335, 'passes': 331, 'pending': 0, 'failures': 4,
                        'start': '2026-10-17T00:01:00Z', 'end': '2026-10-17T00:02:00Z'},
            'passes': [{'file': '/app/test.js', 'fullTitle': n.split(' | ')[1]} for n in ptp + ptp[:24]],
            'pending': [], 'failures': [{'file': '/app/test.js', 'fullTitle': n.split(' | ')[1]} for n in ftp]}
        stdout, stderr = evidence / 'raw-stdout.txt', evidence / 'raw-stderr.txt'
        stdout.write_text(json.dumps(raw, indent=2) + '\n'); stderr.write_text('')
        verifier = accepted.parent / 'verifier'; verifier.mkdir()
        (verifier / 'live-run-script-stdout.txt').write_bytes(stdout.read_bytes())
        (verifier / 'live-run-script-stderr.txt').write_bytes(stderr.read_bytes())
        write(evidence / 'raw-mocha.json', raw)
        write(evidence / 'official-output.json', {'tests': [
            *[{'name': n, 'status': 'PASSED'} for n in ptp], *[{'name': n, 'status': 'FAILED'} for n in ftp]]})
        runner = evidence / 'runner.py'; runner.write_text('fixed completed runner')
        cohort = root / 'artifacts/recovery/swe-additional-short-tmp-20261017/cohort-attempt1'
        state = {'pid': 99, 'startticks': '123', 'state': 'finished_pending_root_review',
            'lock_held': False, 'guard_stopped': True, 'remaining_scopes': [],
            'consecutive_empty_native_scope_samples': [
                {'at_utc': '2026-10-17T00:50:02Z', 'remaining_scopes': []},
                {'at_utc': '2026-10-17T00:50:03Z', 'remaining_scopes': []}],
            'consecutive_empty_scope_samples_after_guard_stop': [
                {'at_utc': '2026-10-17T00:50:04Z', 'remaining_scopes': []},
                {'at_utc': '2026-10-17T00:50:05Z', 'remaining_scopes': []}],
            'released_at_utc': '2026-10-17T00:50:06Z'}
        write(cohort / 'parent-state.json', state)
        write(cohort / 'execution-claim.json', {'pid': 99, 'startticks': '123', 'script_sha256': sha256(runner)})
        write(attempt / 'pending-root-review.json', {'child_returncode': 0,
            'original_bytes_unchanged': True, 'result': str(accepted), 'native_reward': None})
        image = root / 'image.sif'; image.write_bytes(b'not an image; stat fixture only')
        rel = lambda path: str(path.relative_to(root))
        audit = {'task_id': name, 'original_result': rel(original), 'accepted_result': rel(accepted),
            'original_result_sha256': sha256(original), 'accepted_result_sha256': sha256(accepted),
            'source_patch': rel(patch), 'patch_bytes': patch.stat().st_size, 'patch_sha256': sha256(patch),
            'task_checksum': 'fixed-task', 'generation_model': 'openai/fixture',
            'original_invalid_reason': 'harbor_replay_exception:VerifierTimeoutError',
            'audit_kind': 'complete_official_test_report_with_failures', 'audited_reward': 0, 'native_reward': None,
            'official_parser': rel(task / 'tests/parser.py'), 'official_test_config': rel(task / 'tests/config.json'),
            'raw_stdout': rel(stdout), 'raw_stderr': rel(stderr), 'raw_mocha_report': rel(evidence / 'raw-mocha.json'),
            'parsed_report': rel(evidence / 'official-output.json'), 'parse_receipt': rel(evidence / 'receipt.json'),
            'cohort_state': rel(cohort / 'parent-state.json'), 'cohort_claim': rel(cohort / 'execution-claim.json'),
            'pending_review': rel(attempt / 'pending-root-review.json'), 'frozen_runner': rel(runner),
            'sif': rel(image), 'sif_bytes': image.stat().st_size, 'sif_mtime_ns': str(image.stat().st_mtime_ns),
            'reason': 'Artificial complete report only'}
        receipt = {'schema': 'swe_nodebb_official_parser_read_only_v1', 'at_utc': '2026-10-17T00:50:07Z',
            'task_id': name, 'returncode': 0, 'candidate_calls': 0, 'test_runs': 0, 'model_calls': 0,
            'command': [str(root / 'artifacts/envs/harbor/bin/python'), str(task / 'tests/parser.py'),
                        str(stdout), str(stderr), str(evidence / 'official-output.json')],
            'official_parser': audit['official_parser'], 'parser_sha256': sha256(task / 'tests/parser.py'),
            'accepted_result': rel(accepted), 'accepted_result_sha256': sha256(accepted),
            'raw_stdout_source': rel(verifier / 'live-run-script-stdout.txt'),
            'raw_stderr_source': rel(verifier / 'live-run-script-stderr.txt'),
            'cohort_state': audit['cohort_state'], 'cohort_state_sha256': sha256(cohort / 'parent-state.json')}
        def rebind(value):
            for key, field in [('raw_stdout', 'raw_stdout_sha256'), ('raw_stderr', 'raw_stderr_sha256'),
                               ('raw_mocha_report', 'raw_mocha_sha256'), ('parsed_report', 'parsed_report_sha256')]:
                receipt[key] = value[key]; receipt[field] = sha256(root / value[key])
            write(root / value['parse_receipt'], receipt)
            value['bound_sha256'] = {rel(p): sha256(p) for p in root.rglob('*') if p.is_file()}
        rebind(audit)
        baseline = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        baseline_times = {p: (p.stat().st_atime_ns, p.stat().st_mtime_ns) for p in baseline}
        def restore():
            for path, data in baseline.items():
                path.write_bytes(data)
                os.utime(path, ns=baseline_times[path])
        def reject(value, message):
            try:
                approved_official_report_row(root, source, value, 'fixture')
                raise RuntimeError('Invalid report was accepted')
            except AssertionError as error:
                assert message in str(error), str(error)
        row = approved_official_report_row(root, source, audit, 'fixture')
        assert row['reward'] == 0 and row['native_reward'] is None
        assert accepted.read_bytes() == baseline[accepted]
        checks['complete_official_report_keeps_raw_null_and_yields_separate_audited_zero'] = True
        zero_name = 'native-zero'
        zero = source / 'replay' / zero_name / 'result.json'
        write(zero, {'exception_info': None, 'verifier_result': {'rewards': {'reward': 0}}})
        zero_config = deepcopy(config); zero_config['task']['path'] = str(source / 'tasks' / zero_name)
        write(zero.parent / 'config.json', zero_config)
        write(zero.parent / 'agent/replay.json', {'task': zero_name, 'patch': None})
        zero_patch = source / 'generation' / zero_name / 'agent/model.patch'
        zero_patch.parent.mkdir(parents=True); zero_patch.write_bytes(b'')
        reward_file = zero.parent / 'verifier/reward.txt'; reward_file.parent.mkdir(); reward_file.write_text('0\n')
        zero_audit = {'task_id': zero_name, 'original_result': rel(zero), 'accepted_result': rel(zero),
            'original_result_sha256': sha256(zero), 'accepted_result_sha256': sha256(zero),
            'source_patch': rel(zero_patch), 'patch_bytes': 0, 'patch_sha256': sha256(zero_patch),
            'original_invalid_reason': 'example-invalid', 'reason': 'Existing native-zero fixture'}
        ids = [name, zero_name] + ['valid-' + str(i) for i in range(49)]
        rows = [{'task_id': key, 'result': str(original if key == name else zero if key == zero_name else source / key),
            'reward': None if key == name else 0,
            'invalid_reason': audit['original_invalid_reason'] if key == name else 'example-invalid' if key == zero_name else None}
            for key in ids]
        write(source / 'summary.json', {'as_of': 'fixture', 'expected': 51, 'model': 'fixture',
            'checkpoint': 'fixture', 'tasks': rows, 'valid_scored': 49, 'active': {}, 'pending': [],
            'terminal': dict.fromkeys(ids, 'finished')})
        write(root / 'ids.json', {'task_ids': ids})
        write(source / 'marker.json', {'model_consumer_finished': True, 'scoring_may_still_be_running': False})
        manifest = {'source_output': 'source', 'source_summary': 'source/summary.json', 'task_manifest': 'ids.json',
            'model': 'fixture', 'checkpoint': 'fixture', 'resource_marker': 'source/marker.json', 'source_cpu_ids': [0],
            'source_cpu_handoff': 'artifacts/eval/avg64_swe_hard51_20261017/admission-opened.json',
            'approved_native_zero': [zero_audit], 'approved_official_test_reports': [audit]}
        write(root / 'manifest.json', manifest)
        value = collect(root, root / 'manifest.json', scope_reader=lambda cpus: [])
        assert value['complete'] and value['valid_scored'] == 51
        assert value['audited_native_zero_count'] == value['audited_official_test_report_count'] == 1
        assert value['tasks'][0]['native_reward'] is None and value['tasks'][1]['native_reward'] == 0
        checks['collector_keeps_native_zero_and_parsed_report_branches_separate'] = True
        broken = deepcopy(audit); data = json.loads((root / broken['parsed_report']).read_text())
        data['tests'].pop(); write(root / broken['parsed_report'], data); rebind(broken)
        reject(broken, 'Official parsed mapping mismatch'); restore()
        checks['missing_one_test_rejected_even_with_updated_digests'] = True
        broken = deepcopy(audit); conflict = deepcopy(raw); conflict['failures'][0] = deepcopy(conflict['passes'][0])
        (root / broken['raw_stdout']).write_text(json.dumps(conflict, indent=2) + '\n')
        (verifier / 'live-run-script-stdout.txt').write_bytes((root / broken['raw_stdout']).read_bytes())
        write(root / broken['raw_mocha_report'], conflict); rebind(broken)
        reject(broken, 'Conflicting duplicate test status'); restore()
        checks['duplicate_name_with_conflicting_status_rejected'] = True
        broken = deepcopy(audit); broken['source_patch'] = 'foreign/patch'
        reject(broken, 'Patch source mismatch')
        checks['parsed_report_wrong_patch_path_rejected'] = True
        broken = deepcopy(audit); cfg = deepcopy(config); cfg['agent']['kwargs']['source_job'] = str(root / 'foreign')
        write(accepted.parent / 'config.json', cfg); rebind(broken)
        reject(broken, 'Generation source mismatch'); restore()
        checks['parsed_report_wrong_generation_source_rejected_even_with_updated_digests'] = True
        broken = deepcopy(audit)
        trap_reward = accepted.parent / 'verifier/reward.txt'; trap_reward.write_text('1\n')
        broken['raw_reward_file'] = {'path': rel(trap_reward), 'value': '1'}
        rebind(broken)
        row = approved_official_report_row(root, source, broken, 'fixture')
        assert row['reward'] == 0 and row['native_reward'] is None
        assert row['raw_reward_file']['value'] == '1' and row['raw_reward_file_used_as_score'] is False
        assert trap_reward.read_text() == '1\n' and accepted.read_bytes() == baseline[accepted]
        checks['exit_trap_one_is_preserved_but_not_treated_as_success'] = True
    return checks


def run():
    checks = {}
    with TemporaryDirectory(prefix='apex-swe-audit-examples-') as directory:
        root = Path(directory)
        source = root / 'source'
        ids = ['task-' + str(i) for i in range(51)]
        write(root / 'ids.json', {'task_ids': ids})
        audits, rows = [], []
        for i, name in enumerate(ids):
            result = source / 'replay' / name / 'result.json'
            rows.append({'task_id': name, 'result': str(result), 'reward': 0,
                         'invalid_reason': 'empty_tests_requires_audit' if i < 5 else None})
            if i >= 4:
                continue
            write(result, {'finished_at': 'example', 'exception_info': None,
                           'verifier_result': {'rewards': {'reward': 0}}})
            write(result.parent / 'config.json', {'task': {'path': str(source / 'tasks' / name)},
                'agent': {'import_path': 'patch_replay:PatchReplayAgent',
                          'kwargs': {'source_job': str(source / 'generation')}}})
            write(result.parent / 'agent/replay.json', {'task': name, 'patch': None})
            reward = result.parent / 'verifier/reward.txt'
            reward.parent.mkdir()
            reward.write_text('0\n')
            patch = source / 'generation' / name / 'agent/model.patch'
            patch.parent.mkdir(parents=True)
            patch.write_bytes(b'')
            audits.append({'task_id': name, 'original_result': str(result.relative_to(root)),
                'accepted_result': str(result.relative_to(root)),
                'original_result_sha256': sha256(result), 'accepted_result_sha256': sha256(result),
                'source_patch': str(patch.relative_to(root)), 'patch_bytes': 0,
                'patch_sha256': sha256(patch), 'original_invalid_reason': 'empty_tests_requires_audit',
                'reason': 'Approved artificial native zero'})
        raw = {'as_of': 'example', 'expected': 51, 'model': 'fixture', 'checkpoint': 'fixture-adapter',
            'valid_scored': 46, 'active': {}, 'pending': [], 'terminal': dict.fromkeys(ids, 'finished'),
            'tasks': rows}
        write(source / 'summary.json', raw)
        manifest = {'source_output': 'source', 'source_summary': 'source/summary.json',
            'model': 'fixture', 'checkpoint': 'fixture-adapter', 'task_manifest': 'ids.json',
            'resource_marker': 'source/model-consumer-finished.json', 'source_cpu_ids': [0],
            'source_cpu_handoff': 'artifacts/eval/avg64_swe_hard51_20261017/admission-opened.json',
            'approved_native_zero': audits}
        path = root / 'manifest.json'
        write(path, manifest)

        def snapshot():
            return collect(root, path, scope_reader=lambda cpus: [])

        value = snapshot()
        assert value['valid_scored'] == 50 and not value['complete']
        assert value['tasks'][4]['reward'] is None
        assert value['tasks'][4]['native_reward'] == 0
        checks['unapproved_invalid_native_zero_stays_unscored'] = True

        broken = deepcopy(manifest)
        broken['approved_native_zero'][0]['original_result'] = 'another/result.json'
        write(path, broken)
        try:
            snapshot()
            raise RuntimeError('Wrong source was accepted')
        except AssertionError as error:
            assert 'another result' in str(error)
        checks['wrong_result_source_rejected'] = True
        write(path, manifest)

        result = root / audits[0]['accepted_result']
        original_bytes = result.read_bytes()
        content = json.loads(original_bytes)
        content['verifier_result']['rewards']['reward'] = 1
        write(result, content)
        broken = deepcopy(manifest)
        broken['approved_native_zero'][0].update(original_result_sha256=sha256(result),
                                                accepted_result_sha256=sha256(result))
        write(path, broken)
        try:
            snapshot()
            raise RuntimeError('Nonzero native reward was accepted')
        except AssertionError as error:
            assert 'native reward must be zero' in str(error)
        checks['nonzero_native_reward_rejected_even_with_matching_digest'] = True
        result.write_bytes(original_bytes)
        write(path, manifest)

        config_path = result.parent / 'config.json'
        config = json.loads(config_path.read_text())
        broken = deepcopy(config)
        broken['agent']['kwargs']['source_job'] = str(root / 'another-generation')
        write(config_path, broken)
        try:
            snapshot()
            raise RuntimeError('Foreign generation was accepted')
        except AssertionError as error:
            assert 'Generation source mismatch' in str(error)
        checks['foreign_generation_source_rejected'] = True
        write(config_path, config)

        raw['tasks'][4]['invalid_reason'] = None
        raw['valid_scored'] = 47
        write(source / 'summary.json', raw)
        assert not snapshot()['complete']
        checks['all_valid_but_missing_resource_marker_blocks_complete'] = True
        write(root / manifest['resource_marker'], {'model_consumer_finished': True,
            'scoring_may_still_be_running': False, 'at': '2026-10-17T03:00:00+08:00'})
        assert snapshot()['complete'] and snapshot()['primary_score_percent'] == 0
        checks['all_valid_terminal_and_drained_can_complete'] = True

        def busy_snapshot():
            return collect(root, path, scope_reader=lambda cpus: ['apex-baseline-foreign.scope'])

        assert not busy_snapshot()['complete']
        handoff = {'at': '2026-10-16T19:00:01+00:00', 'cpu_ids': [0],
            'swe_expert_all_cpu_and_model_consumers_finished': True,
            'base_scopes_on_target_cpus': []}
        write(root / manifest['source_cpu_handoff'], handoff)
        value = busy_snapshot()
        assert value['complete'] and value['source_cpu_handoff_valid']
        assert value['active_source_cpu_scopes'] == ['apex-baseline-foreign.scope']
        checks['foreign_scope_with_exact_valid_handoff_can_complete'] = True
        for update in ({'cpu_ids': [1]}, {'at': '2026-10-16T18:59:59+00:00'}):
            write(root / manifest['source_cpu_handoff'], dict(handoff, **update))
            value = busy_snapshot()
            assert not value['complete'] and not value['source_cpu_handoff_valid']
        checks['wrong_cpu_or_handoff_before_final_marker_blocks_complete'] = True
        write(root / manifest['source_cpu_handoff'], handoff)
        raw['active'] = {ids[-1]: {'phase': 'replay'}}
        write(source / 'summary.json', raw)
        assert not snapshot()['complete']
        checks['active_original_attempt_blocks_complete'] = True

        # The new receipt proves source release CPU by CPU while AVG is active.
        raw['active'] = {}
        raw['as_of'] = '2026-10-16T19:00:00+00:00'
        write(source / 'summary.json', raw)
        manifest['source_cpu_ids'] = list(range(10))
        manifest['source_specific_cpu_handoff'] = (
            'artifacts/eval/avg64_swe_hard51_20261017/source-expert-consumers-finished.json')
        write(path, manifest)
        (root / manifest['source_cpu_handoff']).unlink()
        marker = {'model': 'fixture', 'expected': 51, 'model_consumer_finished': True,
            'scoring_may_still_be_running': False, 'at': '2026-10-16T19:00:01+00:00'}
        write(root / manifest['resource_marker'], marker)
        receipt_path = root / manifest['source_specific_cpu_handoff']
        avg = receipt_path.parent
        evidence = avg / 'source-cpu-release-checkpoints'
        full_path = evidence / 'full-source-finished.json'
        initial_path = evidence / 'initial.json'
        write(full_path, raw)
        initial = deepcopy(raw)
        initial['as_of'] = '2026-10-16T18:59:00+00:00'
        initial['terminal'].pop(ids[-1])
        initial['active'] = {ids[-1]: {'cpu': 5, 'phase': 'replay'}}
        write(initial_path, initial)
        proofs = []
        for cpu in range(10):
            saved, saved_path = (raw, full_path) if cpu == 5 else (initial, initial_path)
            empty = '2026-10-16T19:00:02+00:00' if cpu == 5 else '2026-10-16T18:59:01+00:00'
            acquired = '2026-10-16T19:00:04+00:00' if cpu == 5 else '2026-10-16T18:59:02+00:00'
            proofs.append({'cpu': cpu, 'scope_empty_at': empty, 'permanent_release': True,
                'actual_scopes_before_avg_admission': [], 'source_pending': 0,
                'source_active': len(saved['active']), 'source_terminal': len(saved['terminal']),
                'source_active_cpu_ids': [5] if cpu != 5 else [],
                'source_checkpoint_as_of': saved['as_of'],
                'source_checkpoint_snapshot': str(saved_path.relative_to(root))})
            write(avg / 'generation' / ids[cpu] / 'config.json', {
                'agent': {'model_name': 'openai/apex-avg64'},
                'environment': {'kwargs': {'baseline_cpu_offset': cpu}}})
            write(avg / 'audit' / (ids[cpu] + '.generation.started.json'), {
                'task': ids[cpu], 'phase': 'generation', 'started_at': acquired})
        handoff = {'schema': 'swe_source_cpu_handoff_v1', 'at': '2026-10-16T19:00:03+00:00',
            'source': manifest['source_output'], 'source_all_cpu_and_model_consumers_finished': True,
            'source_terminal': 51, 'source_active': {}, 'source_pending': [],
            'cpu_ids': list(range(10)), 'source_model_marker': marker,
            'source_checkpoint_snapshot': str(full_path.relative_to(root)),
            'per_cpu_release_before_avg_admission': proofs,
            'current_avg_scopes_on_released_cpus': ['apex-baseline-avg.scope'],
            'whole_pool_empty_at_this_time': False}
        write(receipt_path, handoff)
        value = busy_snapshot()
        assert value['complete'] and value['source_specific_cpu_handoff_valid']
        assert not value['source_cpu_handoff_valid'] and value['active_source_cpu_scopes']
        checks['v1_per_cpu_history_can_complete_while_avg_scopes_remain'] = True

        bad_receipts = []
        bad = deepcopy(handoff); bad['schema'] = 'initial-admission-opened'
        bad_receipts.append(('initial_receipt_is_not_full_source_proof', bad))
        bad = deepcopy(handoff); bad['per_cpu_release_before_avg_admission'][-1]['cpu'] = 0
        bad_receipts.append(('duplicate_or_missing_cpu_release_rejected', bad))
        bad = deepcopy(handoff)
        bad['per_cpu_release_before_avg_admission'][0]['scope_empty_at'] = '2026-10-16T18:59:03+00:00'
        bad_receipts.append(('scope_empty_after_avg_acquisition_rejected', bad))
        bad = deepcopy(handoff)
        bad['per_cpu_release_before_avg_admission'][0]['actual_scopes_before_avg_admission'] = ['avg.scope']
        bad_receipts.append(('occupied_avg_scope_is_not_empty_pool_evidence', bad))
        bad = deepcopy(handoff)
        bad['per_cpu_release_before_avg_admission'][0]['scope_empty_at'] = '2026-10-16T18:59:01'
        bad_receipts.append(('timezone_naive_release_time_rejected', bad))
        bad = deepcopy(handoff); bad['source_model_marker']['scoring_may_still_be_running'] = True
        bad_receipts.append(('unfinished_or_different_canonical_marker_rejected', bad))
        for name, bad in bad_receipts:
            write(receipt_path, bad)
            value = busy_snapshot()
            assert not value['complete'] and not value['source_specific_cpu_handoff_valid']
            checks[name] = True
        write(receipt_path, handoff)
        broken = deepcopy(initial)
        broken['active'][ids[-1]]['cpu'] = 0
        write(initial_path, broken)
        assert not busy_snapshot()['source_specific_cpu_handoff_valid']
        checks['immutable_source_cpu_still_active_rejected'] = True
        write(initial_path, initial)
        write(full_path, initial)
        assert not busy_snapshot()['source_specific_cpu_handoff_valid']
        checks['full_source_checkpoint_with_active_attempt_rejected'] = True
        write(full_path, raw)
        receipt_path.unlink()
        value = busy_snapshot()
        assert not value['complete'] and not value['source_specific_cpu_handoff_valid']
        assert value['primary_score_percent'] is None
        checks['missing_full_source_receipt_stays_incomplete_without_error'] = True
    checks.update(report_examples())
    return {'passed': True, 'scope': 'Artificial JSON/file identities only', 'checks': checks,
            'model_calls': 0, 'task_or_verifier_executions': 0}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
