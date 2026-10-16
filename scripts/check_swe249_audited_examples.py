"""Artificial file examples for the explicit SWE audit; no task/model execution."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from collect_swe249_audited import collect, sha256


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


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
    return {'passed': True, 'scope': 'Artificial JSON/file identities only', 'checks': checks,
            'model_calls': 0, 'task_or_verifier_executions': 0}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
