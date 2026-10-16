#!/usr/bin/env python3
"""Small hand-calculated examples for the final aggregation contract."""
import json
import math
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np

from summarize_experiment import (aggregate, bootstrap_scores, cluster_arrays, expected_records,
    interval, macro, materialize, observation, scored, terminal_budget_rows)


def owner(count, primary, complete=True):
    return {'summary': 'manual-example', 'owner_complete': complete,
            'owner_expected': count, 'owner_primary': primary}


def budget_checks():
    """One synthetic genuine timeout, one infra failure, one unadmitted trial."""
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        expected = expected_records('terminal', {'task_ids': [f't{i:02d}' for i in range(89)]})
        result_path = project / 'results/base/t00__seed0/result.json'
        result_path.parent.mkdir(parents=True)
        (result_path.parent / 'verifier').mkdir()
        snapshot = result_path.parent / 'artifacts/logs/artifacts/final-task-state.json'
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text(json.dumps({'return_code': 0, 'captured_before_verifier': True, 'complete_prefixes': ['app']}))
        snapshot.with_suffix('.tar').write_bytes(b'synthetic archive fixture; no benchmark payload')
        trial_log = result_path.parent / 'trial.log'
        trial_log.write_text('harbor.trial.errors.VerifierTimeoutError: Verifier execution timed out after 900.0 seconds\n')
        stdout = result_path.parent / 'verifier/test-stdout.txt'
        stdout.write_text('collected 1 item\n../tests/test_outputs.py::test_fixture\n')
        official = project / 'tasks/t00/tests/test_outputs.py'
        official.parent.mkdir(parents=True)
        official.write_text('# synthetic filename proof only; never executed\n')
        raw = {'task_name': 't00', 'finished_at': '2026-10-17T00:15:00.100000+00:00', 'verifier_result': None,
               'exception_info': {'exception_type': 'AgentTimeoutError'},
               'config': {'agent': {'model_name': 'base-alias', 'kwargs': {'seed': 0}},
                          'verifier': {'override_timeout_sec': 900}},
               'verifier': {'started_at': '2026-10-17T00:00:00+00:00', 'finished_at': '2026-10-17T00:15:00.100000+00:00'}}
        result_path.write_text(json.dumps(raw))
        audit = {'key': 't00/seed0', 'task_name': 't00', 'seed': 0, 'exact_original_result_path': str(result_path),
                 'native_reward': None, 'native_grade_unchanged': True, 'strict_valid_scored': False,
                 'derived_budget_reward': 0, 'derivation_kind': 'synthetic reviewed computation timeout',
                 'eligibility': {'verifier_timeout_sec': 900, 'verifier_wall_seconds': 900.1, 'official_test_started': True,
                     'official_pytest_collected': 1, 'native_verifier_timeout_in_trial_log': True,
                     'preverifier_snapshot_complete': True, 'native_reward_files_absent': True,
                     'matched_infrastructure_error_markers': []},
                 'evidence': {'trial_log': str(trial_log), 'verifier_stdout': str(stdout), 'official_test': str(official),
                     'snapshot_receipt': str(snapshot), 'snapshot_archive': str(snapshot.with_suffix('.tar')),
                     'candidate_member': 'app/fixture.py', 'candidate_computation_snippets': [{'line': 1, 'text': 'synthetic'}]}}
        audit_path = project / 'audit.json'
        audit_path.write_text(json.dumps({'entries': [audit]}))
        policy = {'policy_id': 'manual', 'models': {'base': {'model_id': 'base', 'served_model': 'base-alias',
                  'owner_kind': 'trial_queue', 'source_summary': 'owner.json', 'result_root': 'results/base',
                  'audit_files': ['audit.json']}}}
        rows = [scored(key, int(meta['unit_id'] == 't88'), 1, 'synthetic-' + key, binary=True)
                for key, meta in expected.items()]
        rows[0] = observation('t00/seed0', 'invalid', result_path, reason='AgentTimeoutError')
        rows[5] = observation('t01/seed0', 'invalid', 'infra-result', reason='missing_dependency')
        rows[10] = observation('t02/seed0', 'pending', 'owner.json', reason='not_admitted')
        source = owner(445, None, False)
        source['summary'] = str(project / 'owner.json')
        queue = {'expected': 445, 'model': 'base-alias', 'valid_scored': 442, 'active': {}, 'pending': ['t02/seed0'],
                 'terminal': {key: 'finished' for key in expected if key != 't02/seed0'}}
        (project / 'owner.json').write_text(json.dumps(queue))
        original = json.dumps([rows, source, raw], sort_keys=True)
        converted, info, issues = terminal_budget_rows(project, 'base', rows, source, [], expected, policy)
        result, records = materialize('terminal', expected, converted, info, issues)
        assert result['native_valid'] == 442 and result['derived_timeout'] == 1 and result['accounted'] == 443
        assert records['t00/seed0']['derived'] and records['t00/seed0']['native_status'] == 'invalid'
        assert records['t00/seed0']['native_reward'] is None and records['t00/seed0']['score'] == 0
        assert records['t01/seed0']['score'] is None and records['t02/seed0']['score'] is None
        assert result['primary_score_percent'] is None
        assert original == json.dumps([rows, source, json.loads(result_path.read_text())], sort_keys=True)

        # A path mismatch and a copied Base audit under another model cannot supply zeros.
        audit['exact_original_result_path'] = str(project / 'other-result.json')
        audit_path.write_text(json.dumps({'entries': [audit]}))
        rejected, _, problems = terminal_budget_rows(project, 'base', rows, source, [], expected, policy)
        assert not rejected[0]['derived'] and any('exact_result_path_mismatch' in p for p in problems)
        audit['exact_original_result_path'] = str(result_path)
        audit_path.write_text(json.dumps({'entries': [audit]}))
        expert = dict(policy['models']['base'], model_id='expert', served_model='expert-alias', result_root='results/expert')
        rejected, _, problems = terminal_budget_rows(project, 'expert', rows, source, [], expected,
                                                     {'policy_id': 'manual', 'models': {'expert': expert}})
        assert not rejected[0]['derived'] and any('wrong_model_result_root' in p for p in problems)
        stdout.write_text('collected 1 item\n../tests/test_outputs.py\nModuleNotFoundError: missing fixture dependency\n')
        rejected, _, problems = terminal_budget_rows(project, 'base', rows, source, [], expected, policy)
        assert not rejected[0]['derived'] and any('infrastructure_marker' in p for p in problems)
        stdout.write_text('collected 1 item\n../tests/test_outputs.py::test_fixture\n')

        # Full445 budget, with one audited null; all89 cluster denominators stay five.
        rows[5] = scored('t01/seed0', 0, 1, 'native-infra-recovered', binary=True)
        rows[10] = scored('t02/seed0', 0, 1, 'native-admitted', binary=True)
        queue.update(valid_scored=444, pending=[], terminal={key: 'finished' for key in expected})
        (project / 'owner.json').write_text(json.dumps(queue))
        converted, info, issues = terminal_budget_rows(project, 'base', rows, source, [], expected, policy)
        result, records = materialize('terminal', expected, converted, info, issues)
        assert result['complete'] and result['accounted'] == 445 and result['native_valid'] == 444
        assert result['strict_native_complete'] is False and result['derived_timeout'] == 1
        num, den = cluster_arrays(expected, records)
        assert len(num) == 89 and den.tolist() == [5] * 89
        draws = bootstrap_scores({'base': (num, den), 'candidate': cluster_arrays(expected, dict(reversed(list(records.items()))))},
                                 seed_sequence=np.random.SeedSequence(20261015))
        ci = interval(draws['candidate'] - draws['base'])
        assert ci['lower'] == ci['upper'] == 0
        assert macro({'swe': 10, 'hle': None, 'asi': 30, 'terminal': result['primary_score_percent']}) is None
        queue['active'] = {'t02/seed0': 'still active'}
        (project / 'owner.json').write_text(json.dumps(queue))
        converted, info, issues = terminal_budget_rows(project, 'base', rows, source, [], expected, policy)
        assert not materialize('terminal', expected, converted, info, issues)[0]['complete']
    return {'one_compute_timeout_only_zero': True, 'infra_and_unadmitted_remain_unscored': True,
            'exact_path_and_wrong_model_rejected': True, 'strict_rows_source_and_native_result_unchanged': True,
            'all445_and_empty_active_pending_required': True, 'clusters': 89, 'seeds_per_cluster': 5,
            'identical_paired_ci': ci, 'other_missing_benchmark_blocks_macro': True}


def reference_checks():
    """Distinct HLE references must keep their own deltas and incomplete gates."""
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        manifests = {name: {'task_ids': [f'{name}-{i}' for i in range(count)]}
                     for name, count in [('swe', 51), ('hle', 2500), ('asi', 60), ('terminal', 89)]}
        manifests['hle']['image_task_ids'] = manifests['hle']['task_ids'][:342]
        manifests['asi']['prompt_levels'] = ['b1', 'b2', 'b3', 'b4']
        for name, manifest in manifests.items():
            (project / (name + '.json')).write_text(json.dumps(manifest))
        cutoffs = {'base': 0, 'mixed883': 2500, 'avg16': 1250, 'avg64': 1875}
        config = {'protocol': 'synthetic-no-execution', 'reference_model': 'base', 'final_model': 'avg64',
            'statistics': {'repetitions': 10000, 'seed': 20261015, 'confidence_level': .95},
            'benchmarks': {name: {'manifest': name + '.json'} for name in manifests},
            'models': {name: {'label': name, 'benchmarks': {'hle': {'fixture_model': name}}} for name in cutoffs},
            'additional_comparisons': [{'model': 'avg64', 'reference': ref, 'benchmarks': ['hle']}
                                       for ref in ('mixed883', 'avg16')]}
        incomplete = False

        def fixture_source(_project, benchmark, spec):
            assert benchmark == 'hle'
            name = spec['fixture_model']
            rows = [scored(key, int(i < cutoffs[name]), 1, 'synthetic-' + key, binary=True)
                    for i, key in enumerate(manifests['hle']['task_ids'])]
            if name == 'avg16':
                rows.reverse()  # Reference pairing must follow IDs, not row order.
            missing = incomplete and name == 'avg16'
            return (rows[:-1] if missing else rows,
                    owner(2500, None if missing else cutoffs[name] / 25, not missing), [])

        with patch('summarize_experiment.read_source', side_effect=fixture_source):
            report, _ = aggregate(project, config)
            comparisons = report['comparisons']
            deltas = {ref: comparisons['avg64_vs_' + ref]['benchmarks']['hle']['delta_percent_points']
                      for ref in ('base', 'mixed883', 'avg16')}
            assert deltas == {'base': 75, 'mixed883': -25, 'avg16': 25}
            base_ci = comparisons['avg64_vs_base']['benchmarks']['hle']['delta_ci95_percent_points']
            mixed_ci = comparisons['avg64_vs_mixed883']['benchmarks']['hle']['delta_ci95_percent_points']
            for bound in ('lower', 'upper'):
                assert math.isclose(mixed_ci[bound], base_ci[bound] - 100, abs_tol=1e-10)
            assert all(row['macro_delta_percent_points'] is None for row in comparisons.values())
            assert all(row['macro_primary_percent'] is None for row in report['models'].values())
            incomplete = True
            partial, _ = aggregate(project, config)
            blocked = partial['comparisons']['avg64_vs_avg16']['benchmarks']['hle']
            assert blocked['valid_paired_observations'] == 2499 and not blocked['complete_pair']
            assert blocked['delta_percent_points'] is None and blocked['delta_ci95_percent_points'] is None
            assert partial['comparisons']['avg64_vs_base']['benchmarks']['hle']['delta_percent_points'] == 75
            assert partial['comparisons']['avg64_vs_mixed883']['benchmarks']['hle']['delta_percent_points'] == -25
    return {'fixed_HLE_questions': 2500, 'image_questions': 342, 'distinct_reference_deltas_pp': deltas,
            'paired_CI_uses_requested_reference': True, 'incomplete_reference_blocks_only_its_pair': True,
            'HLE_only_controls_have_no_four_benchmark_macro': True}


def run():
    checks = {}
    expected = expected_records('swe', {'task_ids': ['a', 'b']})
    rows = [scored('a', 0, 1, 'manual-a', binary=True),
            observation('b', 'invalid', 'manual-b', reason='verifier_unavailable')]
    result, _ = materialize('swe', expected, rows, owner(2, None, False), [])
    assert (result['valid_scored'], result['wrong'], result['invalid'], result['missing']) == (1, 1, 1, 0)
    assert result['primary_score_percent'] is None
    checks['wrong_is_valid_zero_but_verifier_invalid_is_unscored'] = True

    complete_rows = [scored('a', 0, 1, 'manual-a', binary=True), scored('b', 1, 1, 'manual-b', binary=True)]
    complete, records = materialize('swe', expected, complete_rows, owner(2, 50), [])
    assert complete['primary_score_percent'] == 50
    for label, extra, source in [
        ('unexpected_ID', [scored('c', 1, 1, 'manual-c', binary=True)], owner(2, 50)),
        ('duplicate_ID', [scored('a', 1, 1, 'manual-duplicate', binary=True)], owner(2, 50)),
        ('owner_not_complete', [], owner(2, 50, False)),
        ('owner_score_mismatch', [], owner(2, 100))]:
        result, _ = materialize('swe', expected, complete_rows + extra, source, [])
        assert not result['complete'] and result['primary_score_percent'] is None, label
    missing, _ = materialize('swe', expected, complete_rows[:1], owner(2, None, False), [])
    assert missing['missing'] == 1 and missing['primary_score_percent'] is None
    checks['missing_duplicate_unexpected_or_owner_mismatch_blocks_primary'] = True

    # Same ID scores in reversed physical order must still have exactly zero paired delta.
    reversed_records = dict(reversed(list(records.items())))
    arrays = {'base': cluster_arrays(expected, records), 'candidate': cluster_arrays(expected, reversed_records)}
    draws = bootstrap_scores(arrays, seed_sequence=np.random.SeedSequence(20261015))
    delta = interval(draws['candidate'] - draws['base'])
    assert delta['lower'] == delta['upper'] == 0
    checks['pair_by_ID_not_physical_row_order'] = delta

    # Hand calculation: two tasks, each repeated five times. Resampling two task IDs
    # gives paired deltas {-100, 0, 100} pp, with probabilities {1/4, 1/2, 1/4}.
    tb_expected = expected_records('terminal', {'task_ids': ['a', 'b']})
    tb = [scored(key, int(meta['unit_id'] == 'b'), 1, key, binary=True) for key, meta in tb_expected.items()]
    _, base = materialize('terminal', tb_expected, tb, owner(10, 50), [])
    tb_other = [scored(key, int(meta['unit_id'] == 'a'), 1, key, binary=True) for key, meta in tb_expected.items()]
    _, candidate = materialize('terminal', tb_expected, tb_other, owner(10, 50), [])
    numerator, maximum = cluster_arrays(tb_expected, base)
    assert numerator.tolist() == [0, 5] and maximum.tolist() == [5, 5]
    draws = bootstrap_scores({'base': (numerator, maximum), 'candidate': cluster_arrays(tb_expected, candidate)},
                             seed_sequence=np.random.SeedSequence(20261015))
    tb_ci = interval(draws['candidate'] - draws['base'])
    assert tb_ci['lower'] == -100 and tb_ci['upper'] == 100
    checks['TB_all_five_seeds_resampled_as_one_task_cluster'] = tb_ci

    values = {'a': [0, 1, 1, 0, 0], 'b': [0, 0, 1, 1, 0]}
    rows = [scored(key, values[meta['unit_id']][meta['within_unit']], 1, key, binary=True)
            for key, meta in tb_expected.items()]
    result, _ = materialize('terminal', tb_expected, rows, owner(10, 40), [])
    assert [row['score_percent'] for row in result['per_seed']] == [0, 50, 100, 50, 0]
    assert result['five_seed_mean_percent'] == 40
    assert math.isclose(result['sample_sd_percent_ddof1'], math.sqrt(1750))
    checks['TB_mean40_sample_SD_sqrt1750'] = {'mean': 40, 'sample_sd': result['sample_sd_percent_ddof1']}

    asi_expected = expected_records('asi', {'task_ids': ['a', 'b'], 'prompt_levels': ['b1', 'b2', 'b3', 'b4']})
    native = [0, 25, 50, 100, 100, 0, 0, 0]  # 275 / 800 * 100 = 34.375%.
    rows = [scored(key, score, 100, key) for key, score in zip(asi_expected, native)]
    result, records = materialize('asi', asi_expected, rows, owner(8, 34.375), [])
    numerator, maximum = cluster_arrays(asi_expected, records)
    assert result['primary_score_percent'] == 34.375
    assert numerator.tolist() == [175, 100] and maximum.tolist() == [400, 400]
    assert result['valid_zero_score'] == 4 and result['valid_partial_score'] == 2 and result['invalid'] == 0
    checks['ASI_native_275_over800_and_four_condition_clusters'] = True

    assert macro({'swe': 0, 'hle': 100, 'asi': 0, 'terminal': 0}) == 25
    assert macro({'swe': 100, 'hle': None, 'asi': 100, 'terminal': 100}) is None
    checks['four_benchmarks_equal_weight_missing_benchmark_blocks_macro'] = True
    checks['audited_terminal_budget_view'] = budget_checks()
    checks['additional_comparison_references'] = reference_checks()
    return {'passed': True, 'fixture_scope': 'Hand-calculated artificial scores only; no benchmark questions or model calls',
            'bootstrap_repetitions': 10000, 'seed': 20261015, 'checks': checks}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
