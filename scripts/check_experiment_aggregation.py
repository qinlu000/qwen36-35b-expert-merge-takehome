#!/usr/bin/env python3
"""Small hand-calculated examples for the final aggregation contract."""
import json
import math

import numpy as np

from summarize_experiment import (bootstrap_scores, cluster_arrays, expected_records,
    interval, macro, materialize, observation, scored)


def owner(count, primary, complete=True):
    return {'summary': 'manual-example', 'owner_complete': complete,
            'owner_expected': count, 'owner_primary': primary}


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
    return {'passed': True, 'fixture_scope': 'Hand-calculated artificial scores only; no benchmark questions or model calls',
            'bootstrap_repetitions': 10000, 'seed': 20261015, 'checks': checks}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
