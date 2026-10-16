#!/usr/bin/env python3
"""Read fixed owner outputs; report complete scores and paired cluster bootstrap."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np


BENCHMARKS = ('swe', 'hle', 'asi', 'terminal')
COUNTS = {'swe': 51, 'hle': 2500, 'asi': 60, 'terminal': 89}


def load(path):
    return json.loads(path.read_text())


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def observation(key, status, source, score=None, maximum=None, reason=None):
    return {'key': key, 'status': status, 'score': score, 'max_score': maximum,
            'source': str(source), 'reason': reason}


def scored(key, score, maximum, source, *, binary=False):
    valid = (number(score) and number(maximum) and maximum > 0 and 0 <= score <= maximum
             and (not binary or score in (0, 1)))
    return observation(key, 'valid' if valid else 'invalid', source,
                       float(score) if valid else None, float(maximum) if valid else None,
                       None if valid else 'invalid_numeric_score')


def expected_records(benchmark, manifest):
    ids = manifest['task_ids']
    within = list(range(5)) if benchmark == 'terminal' else manifest['prompt_levels'] if benchmark == 'asi' else [None]
    rows = {}
    for unit in ids:
        for part in within:
            key = unit if part is None else unit + ('/seed' + str(part) if benchmark == 'terminal' else '/' + part)
            rows[key] = {'unit_id': unit, 'within_unit': part}
    return rows


def read_source(project, benchmark, spec):
    path = project / spec['summary']
    info = {'summary': str(path), 'adapter': spec['adapter'], 'notes': spec.get('notes', [])}
    issues, rows = [], []
    if not path.exists():
        info.update(available=False, owner_complete=False)
        return rows, info, issues
    try:
        owner = load(path)
    except (ValueError, OSError) as error:
        info.update(available=False, owner_complete=False)
        return rows, info, ['owner_source_unreadable:' + type(error).__name__]
    info.update(available=True, owner_complete=owner.get('complete') is True,
        summary_mtime_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        owner_expected=owner.get('expected_instance_count') if benchmark == 'asi' else
                       owner.get('expected_trials', owner.get('expected')) if benchmark == 'terminal' else owner.get('expected'),
        owner_primary=owner.get({'swe': 'primary_score_percent', 'hle': 'score',
                                'asi': 'mean_percent', 'terminal': 'primary_mean_percent'}[benchmark]),
        provenance={key: owner[key] for key in ('official', 'score_scope', 'provider', 'metric', 'model', 'checkpoint', 'selection',
            'selection_policy', 'mode', 'scorer_error_count', 'local_gate_repairs') if key in owner})
    if spec.get('selection_manifest'):
        selection_path = project / spec['selection_manifest']
        info['selection_manifest'] = str(selection_path)
        if selection_path.exists():
            selection = load(selection_path)
            info['selection_rule'] = selection.get('selection_rule')
            info['selection_counts'] = {key: len(selection.get(key, [])) for key in ('retained', 'selected')}

    if spec['adapter'] == 'swe_tasks':
        terminal = owner.get('terminal', {})
        for raw in owner['tasks']:
            key = raw['task_id']
            source = raw.get('accepted_result') or raw.get('result') or str(path)
            reason = raw.get('invalid_reason')
            if reason is None and (raw.get('status') == 'valid_scored' or not raw.get('status')):
                rows.append(scored(key, raw.get('reward'), 1, source, binary=True))
            else:
                pending = (raw.get('status') == 'awaiting_generation_or_replay'
                           or reason == 'not_scored' and key not in terminal)
                rows.append(observation(key, 'pending' if pending else 'invalid', source,
                    reason=reason or raw.get('status') or 'missing_native_replay'))
    elif spec['adapter'] == 'hle_results':
        directory = project / spec['results']
        info['records_directory'] = str(directory)
        for result_path in sorted(directory.glob('*.json')):
            try:
                raw = load(result_path)
            except (ValueError, OSError) as error:
                rows.append(observation(result_path.stem, 'invalid', result_path,
                                        reason='unreadable_score_record:' + type(error).__name__))
                continue
            key, status = raw['id'], raw.get('evaluation_status')
            if key != result_path.stem:
                issues.append('HLE_filename_ID_mismatch:' + str(result_path))
            if status in ('judged', 'native_no_answer') and type(raw.get('correct')) is bool:
                row = scored(key, int(raw['correct']), 1, result_path, binary=True)
                if status == 'native_no_answer' and raw['correct']:
                    row = observation(key, 'invalid', result_path, reason='native_no_answer_marked_correct')
            else:
                row = observation(key, 'pending' if status in ('pending', 'prepared') else 'invalid',
                                  result_path, reason=status or 'evaluation_status_missing')
            row.update(source_generation_result=raw.get('source_result'), native_no_answer=status == 'native_no_answer',
                       judge_identity=raw.get('reported_identity'), is_image=raw.get('is_image'))
            rows.append(row)
    elif spec['adapter'] == 'asi_native':
        scoring_config = project / spec['scoring_config']
        info['scoring_config'] = str(scoring_config)
        result_root = Path(load(scoring_config)['results'])
        if not result_root.is_absolute():
            result_root = project / result_root
        info['generation_results_root'] = str(result_root)
        for raw in owner['results']:
            key = raw['task_id'] + '/' + raw['prompt_level']
            source = str(path) + '#results/' + raw['condition']
            status = raw.get('evaluation_status')
            if status == 'completed' and not raw.get('scorer_internal_error'):
                row = scored(key, raw.get('final_score'), raw.get('max_score'), source)
                if raw.get('max_score') != 100:
                    row = observation(key, 'invalid', source, reason='ASI_expected_max_score_100')
            else:
                row = observation(key, 'pending' if status in ('pending', 'prepared') else 'invalid',
                                  source, reason=status or 'evaluation_status_missing')
            generation = raw.get('source_result')
            if generation and not Path(generation).is_absolute():
                generation = str(result_root / generation)
            row.update(source_generation_result=generation, native_condition=raw['condition'])
            rows.append(row)
        if owner.get('scorer_error_count', 0):
            info['native_scorer_error_count'] = owner['scorer_error_count']
    elif spec['adapter'] == 'terminal_accepted':
        accepted = owner['accepted_first_valid']
        for key, raw in accepted.items():
            rows.append(scored(key, raw.get('reward'), 1, raw.get('path') or path, binary=True))
        # This source supplies failure status only. It never adds/replaces an answer or score.
        status_path = project / spec['status_only_source']
        info['status_only_source'] = str(status_path)
        if status_path.exists():
            for key, raw in load(status_path).get('scores', {}).items():
                if key not in accepted and raw is not None:
                    rows.append(observation(key, 'invalid' if raw.get('valid') is False else 'pending',
                        raw.get('path') or status_path,
                        reason=raw.get('verifier_issue') or raw.get('exception') or 'not_accepted_by_canonical_owner'))
    elif spec['adapter'] == 'terminal_scores':
        scores = owner['scores']
        for key, raw in scores.items():
            if raw is not None and raw.get('valid') is True:
                rows.append(scored(key, raw.get('reward'), 1, raw.get('path') or path, binary=True))
            else:
                rows.append(observation(key, 'invalid', (raw or {}).get('path') or path,
                    reason=(raw or {}).get('verifier_issue') or (raw or {}).get('exception') or 'missing_native_result'))
        for key in set(owner.get('pending', [])) | set(owner.get('active', {})):
            if key not in scores:
                rows.append(observation(key, 'pending', path,
                    reason='active' if key in owner.get('active', {}) else 'not_admitted'))
    else:
        raise ValueError('Unknown adapter: ' + spec['adapter'])
    return rows, info, issues


def materialize(benchmark, expected, rows, source, issues):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['key']].append(row)
    unexpected = sorted(set(grouped) - set(expected))
    observations, duplicates = {}, []
    for key, metadata in expected.items():
        candidates = grouped.get(key, [])
        if not candidates:
            row = observation(key, 'missing', source['summary'], reason='no_scoring_record')
        elif len(candidates) > 1:
            duplicates.append(key)
            row = observation(key, 'invalid', source['summary'], reason='duplicate_ID_no_selection')
            row['duplicate_sources'] = [item['source'] for item in candidates]
        else:
            row = dict(candidates[0])
        observations[key] = dict(row, **metadata)
    counts = Counter(row['status'] for row in observations.values())
    valid = [row for row in observations.values() if row['status'] == 'valid']
    numerator, denominator = sum(row['score'] for row in valid), sum(row['max_score'] for row in valid)
    complete = (len(valid) == len(expected) and not unexpected and not duplicates and not issues
                and source['owner_complete'] and not source.get('native_scorer_error_count'))
    computed = 100 * numerator / denominator if len(valid) == len(expected) else None
    issues = list(issues)
    if source.get('owner_expected') not in (None, len(expected)):
        issues.append('owner_expected_count_mismatch')
        complete = False
    if complete and (not number(source.get('owner_primary')) or
                     not math.isclose(computed, source['owner_primary'], abs_tol=1e-8)):
        issues.append('owner_primary_does_not_match_complete_records')
        complete = False
    result = {'expected': len(expected), 'valid_scored': len(valid),
        'invalid': counts['invalid'], 'pending': counts['pending'], 'missing': counts['missing'],
        'complete': complete, 'primary_score_percent': computed if complete else None,
        'score_numerator_observed': numerator, 'max_score_observed': denominator,
        'unexpected_IDs': unexpected, 'duplicate_IDs': duplicates, 'source_issues': issues,
        'source': source, 'primary_ci95_percent': None}
    if benchmark == 'asi':
        result.update(valid_zero_score=sum(row['score'] == 0 for row in valid),
            valid_partial_score=sum(0 < row['score'] < row['max_score'] for row in valid),
            valid_full_score=sum(row['score'] == row['max_score'] for row in valid),
            metric='100 * native sum(final_score) / sum(max_score); local seed31415, not Portal-certified')
    else:
        result.update(correct=sum(row['score'] == 1 for row in valid),
                      wrong=sum(row['score'] == 0 for row in valid))
    if benchmark == 'terminal':
        per_seed = []
        for seed in range(5):
            subset = [row for row in observations.values() if row['within_unit'] == seed]
            accepted = [row for row in subset if row['status'] == 'valid']
            per_seed.append({'seed': seed, 'expected': len(subset), 'valid_scored': len(accepted),
                'correct': sum(row['score'] for row in accepted),
                'score_percent': 100 * sum(row['score'] for row in accepted) / len(subset)
                                 if len(accepted) == len(subset) else None})
        result['per_seed'] = per_seed
        values = [row['score_percent'] for row in per_seed]
        result['sample_sd_percent_ddof1'] = float(np.std(values, ddof=1)) if complete else None
        result['five_seed_mean_percent'] = float(np.mean(values)) if complete else None
    return result, observations


def cluster_arrays(expected, observations):
    units = defaultdict(list)
    for key, metadata in expected.items():
        units[metadata['unit_id']].append(observations[key])
    numerator, denominator = [], []
    for rows in units.values():
        assert all(row['status'] == 'valid' for row in rows)
        numerator.append(sum(row['score'] for row in rows))
        denominator.append(sum(row['max_score'] for row in rows))
    return np.asarray(numerator), np.asarray(denominator)


def bootstrap_scores(arrays, *, seed_sequence, repetitions=10000):
    """One sampled ID sequence per replicate, shared by all compared models."""
    if not arrays:
        return {}
    size = len(next(iter(arrays.values()))[0])
    assert all(len(num) == len(den) == size for num, den in arrays.values())
    random = np.random.default_rng(seed_sequence)
    result = {name: np.empty(repetitions) for name in arrays}
    for start in range(0, repetitions, 256):
        end = min(start + 256, repetitions)
        indices = random.integers(size, size=(end - start, size))
        for name, (numerator, denominator) in arrays.items():
            result[name][start:end] = 100 * numerator[indices].sum(axis=1) / denominator[indices].sum(axis=1)
    return result


def interval(values):
    low, high = np.percentile(values, [2.5, 97.5])
    return {'lower': float(low), 'upper': float(high), 'method': 'percentile cluster bootstrap'}


def macro(scores):
    return sum(scores[name] for name in BENCHMARKS) / 4 if all(scores.get(name) is not None for name in BENCHMARKS) else None


def aggregate(project, config):
    manifests, expected = {}, {}
    for name in BENCHMARKS:
        manifests[name] = load(project / config['benchmarks'][name]['manifest'])
        ids = manifests[name]['task_ids']
        assert len(ids) == len(set(ids)) == COUNTS[name], 'Fixed task manifest changed: ' + name
        expected[name] = expected_records(name, manifests[name])
    assert manifests['asi']['prompt_levels'] == ['b1', 'b2', 'b3', 'b4']
    assert len(set(manifests['hle']['image_task_ids'])) == 342
    assert set(manifests['hle']['image_task_ids']) <= set(manifests['hle']['task_ids'])
    models, observations = {}, {}
    for model, model_spec in config['models'].items():
        results, observations[model] = {}, {}
        for name, spec in model_spec['benchmarks'].items():
            try:
                rows, source, issues = read_source(project, name, spec)
            except (ValueError, KeyError, TypeError, OSError) as error:
                rows, source, issues = [], {'summary': str(project / spec['summary']), 'owner_complete': False}, ['source_schema_error:' + str(error)]
            results[name], observations[model][name] = materialize(name, expected[name], rows, source, issues)
            if name == 'hle':
                image_ids = set(manifests[name]['image_task_ids'])
                results[name]['subgroups'] = {}
                for label, ids in [('image', image_ids), ('text', set(manifests[name]['task_ids']) - image_ids)]:
                    valid = [observations[model][name][key] for key in ids if observations[model][name][key]['status'] == 'valid']
                    results[name]['subgroups'][label] = {'expected': len(ids), 'valid_scored': len(valid),
                        'correct': sum(row['score'] for row in valid),
                        'accuracy_percent': 100 * sum(row['score'] for row in valid) / len(ids)
                                            if len(valid) == len(ids) else None}
        scores = {name: value['primary_score_percent'] for name, value in results.items()}
        artifact = model_spec.get('artifact')
        if artifact and artifact.startswith('artifacts/'):
            artifact = str(project / artifact)
        models[model] = {'label': model_spec['label'], 'artifact': artifact,
            'required_benchmarks': list(results), 'benchmarks': results,
            'required_scope_complete': all(value['complete'] for value in results.values()),
            'macro_primary_percent': macro(scores), 'macro_ci95_percent': None,
            'macro_eligible': set(results) == set(BENCHMARKS)}

    stats = config['statistics']
    assert (stats['repetitions'], stats['seed'], stats['confidence_level']) == (10000, 20261015, 0.95)
    streams = np.random.SeedSequence(stats['seed']).spawn(len(BENCHMARKS))
    draws = {}
    for name, stream in zip(BENCHMARKS, streams):
        arrays = {model: cluster_arrays(expected[name], observations[model][name])
            for model, data in models.items() if name in data['benchmarks'] and data['benchmarks'][name]['complete']}
        draws[name] = bootstrap_scores(arrays, seed_sequence=stream, repetitions=stats['repetitions'])
        for model, values in draws[name].items():
            models[model]['benchmarks'][name]['primary_ci95_percent'] = interval(values)
    for model, data in models.items():
        if data['macro_primary_percent'] is not None:
            data['macro_ci95_percent'] = interval(sum(draws[name][model] for name in BENCHMARKS) / 4)

    comparisons = {}
    reference = config['reference_model']
    for model in models:
        if model == reference:
            continue
        cells = {}
        for name in models[model]['benchmarks']:
            paired = {key for key in expected[name] if observations[reference][name][key]['status'] ==
                      observations[model][name][key]['status'] == 'valid'}
            paired_units = sum(all(key in paired for key, meta in expected[name].items() if meta['unit_id'] == unit)
                               for unit in manifests[name]['task_ids'])
            ready = model in draws[name] and reference in draws[name]
            cells[name] = {'complete_pair': ready, 'expected_observations': len(expected[name]),
                'valid_paired_observations': len(paired), 'expected_clusters': COUNTS[name],
                'complete_paired_clusters': paired_units,
                'delta_percent_points': (models[model]['benchmarks'][name]['primary_score_percent'] -
                    models[reference]['benchmarks'][name]['primary_score_percent']) if ready else None,
                'delta_ci95_percent_points': interval(draws[name][model] - draws[name][reference]) if ready else None}
        delta = macro({name: cell['delta_percent_points'] for name, cell in cells.items()})
        comparisons[model + '_vs_' + reference] = {'benchmarks': cells, 'macro_delta_percent_points': delta,
            'macro_delta_ci95_percent_points': interval(sum(draws[name][model] - draws[name][reference]
                for name in BENCHMARKS) / 4) if delta is not None else None}
    return {'as_of_utc': datetime.now(timezone.utc).isoformat(), 'models': models, 'comparisons': comparisons,
        'interpretation_notes': config.get('interpretation_notes', []),
        'statistics': dict(stats, numpy_version=np.__version__, bit_generator='PCG64',
            benchmark_stream_order=list(BENCHMARKS), stream_rule='SeedSequence(20261015).spawn(4); independent benchmark streams',
            resampling_units={'swe': '51 task IDs', 'hle': '2500 question IDs',
                'asi': '60 project IDs retaining all four conditions', 'terminal': '89 task IDs retaining all five seeds'},
            interpretation='Conditional on fixed task versions, resource budgets, evaluated runs and disclosed scheduling/judge differences'),
        'source_manifests': {name: str(project / config['benchmarks'][name]['manifest']) for name in BENCHMARKS},
        'protocol': str(project / config['protocol']),
        'complete_primary_comparison': comparisons[config['final_model'] + '_vs_' + reference]['macro_delta_percent_points'] is not None,
        'partial_results_policy': 'No subset primary means or intervals; missing/invalid/pending remain distinct from valid wrong/zero scores'}, observations


def markdown(report):
    lines = ['# 正式评测统一汇总', '', 'UTC：' + report['as_of_utc'], '',
        '| 模型 | SWE % | HLE % | ASI % | Terminal % | 四项等权宏平均 % |', '|---|---:|---:|---:|---:|---:|']
    for data in report['models'].values():
        cells = []
        for name in BENCHMARKS:
            row = data['benchmarks'].get(name)
            cells.append('—（非目标未评）' if row is None else f"{row['primary_score_percent']:.8f}" if row['complete']
                         else f"未完成 {row['valid_scored']}/{row['expected']}；invalid {row['invalid']}")
        score = data['macro_primary_percent']
        lines.append('| ' + ' | '.join([data['label'], *cells, f'{score:.8f}' if score is not None else 'null']) + ' |')
    lines += ['', '所有分母固定；有效错误/零分保留，评分 invalid、pending 和 missing 不计成错误，也不剔除后给完整主分。', '',
              '专家只评目标项，不把四个不同专家拼成一个模型的宏平均。', '']
    for comparison, data in report['comparisons'].items():
        delta = data['macro_delta_percent_points']
        lines.append(f"{comparison}：宏平均差值=" + (f'{delta:.8f} pp；95%CI={data["macro_delta_ci95_percent_points"]}' if delta is not None else 'null（四项未完整配对）'))
    lines += ['', '区间：10000次paired cluster bootstrap，seed20261015。Terminal保留任务内五seed；ASI保留项目内四condition。',
              '完整来源、逐项区间与invalid原因见summary.json；逐观测状态和原始路径见observations.jsonl。', '']
    lines += ['协议限制：', '', *['- ' + note for note in report['interpretation_notes']], '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--config', type=Path, default=Path('configs/eval/final_results_20261017.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    config_path = args.config if args.config.is_absolute() else project / args.config
    config = load(config_path)
    report, observations = aggregate(project, config)
    report['path_config'] = str(config_path)
    output = args.output if args.output.is_absolute() else project / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    (output / 'report.md').write_text(markdown(report))
    with (output / 'observations.jsonl').open('w') as stream:
        for model, benchmarks in observations.items():
            for name, rows in benchmarks.items():
                for row in rows.values():
                    stream.write(json.dumps(dict(model=model, benchmark=name, **row), ensure_ascii=False, allow_nan=False) + '\n')
    with (output / 'matrix.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model', *BENCHMARKS, 'macro_primary_percent'])
        for model, data in report['models'].items():
            writer.writerow([model, *[data['benchmarks'].get(name, {}).get('primary_score_percent') for name in BENCHMARKS], data['macro_primary_percent']])
    print(json.dumps({'complete_primary_comparison': report['complete_primary_comparison'],
        'coverage': {model: {name: row['valid_scored'] for name, row in data['benchmarks'].items()}
                     for model, data in report['models'].items()}, 'output': str(output.resolve())}))


if __name__ == '__main__':
    main()
