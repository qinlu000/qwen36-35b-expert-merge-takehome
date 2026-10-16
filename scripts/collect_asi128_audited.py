#!/usr/bin/env python3
"""Read-only source audit; substitute one approved native grade, never evaluate."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, row):
    path = root / row['path']
    assert path.is_file() and sha(path) == row['sha256'], row['path']
    if 'bytes' in row:
        assert path.stat().st_size == row['bytes']
    return path


def internal_error(value):
    # Same frozen native evaluator-error predicate, without importing an evaluator.
    if isinstance(value, dict):
        if (value.get('scorer_internal_error') or value.get('evaluator_unavailable')
                or (value.get('parse_failures', 0) and value.get('valid_judge_count') == 0)
                or ('parsed_responses' in value and value.get('raw_responses')
                    and not value['parsed_responses'])):
            return True
        return any(internal_error(child) for child in value.values())
    return isinstance(value, list) and any(internal_error(child) for child in value)


def collect(root, config):
    report_path = checked(root, config['original_report'])
    original = read(report_path)
    condition = config['condition']
    rows = original['results']
    assert len(rows) == len({r['condition'] for r in rows}) == 240
    assert Counter(r['evaluation_status'] for r in rows) == {'completed': 239, 'evaluation_invalid': 1}
    previous = next(r for r in rows if r['condition'] == condition)
    assert previous['evaluation_status'] == 'evaluation_invalid'
    invalid = read(checked(root, config['original_invalid']))
    assert invalid == previous
    native_path = checked(root, config['native_result'])
    native = read(native_path)
    receipt_path = checked(root, config['receipt'])
    receipt = read(receipt_path)
    assert native['condition'] == condition and native['evaluation_status'] == 'completed'
    assert native['attempt'] == 2 and native['max_score'] == 100
    assert not internal_error(native)
    assert native['final_score'] == config['approved_native_score']
    assert receipt['condition'] == condition and receipt['state'] == 'finished'
    assert receipt['pass_count'] == 1 and receipt['evaluation_status'] == 'completed'
    assert receipt['new_calls'] == 0 and receipt['cache_reuses'] == 9
    assert all(receipt[k] is True for k in ['source_bytes_unchanged', 'canonical_report_unchanged',
        'native_runtime_tree_unchanged', 'journal_original_prefix_unchanged',
        'canonical_record_not_accepted_or_overwritten'])
    samples = receipt['scope_empty_samples']
    assert len(samples) == 2 and receipt['active_program_scopes'] == []
    assert all(s['active_program_scopes'] == [] for s in samples)
    assert (datetime.fromisoformat(samples[1]['at_utc']) -
            datetime.fromisoformat(samples[0]['at_utc'])).total_seconds() >= 2
    source = checked(root, config['source_result'])
    assert native['source_result'] == str(source)
    for row in config['persisted_outputs'] + config['cache_files']:
        checked(root, row)
    recovery = native_path.parent
    for row in config['cache_files']:
        copied = recovery / 'judge_calls' / (condition + '.grading2') / Path(row['path']).name
        assert sha(copied) == row['sha256']
    assert len(config['persisted_outputs']) == 3 and len(config['cache_files']) == 18
    claim = read(recovery / 'claim.json')
    assert claim['condition'] == condition and claim['pass_limit'] == 1
    assert claim['source']['sha256'] == config['source_result']['sha256']
    assert claim['cache_namespace'] == condition + '.grading2'
    prefix = checked(root, config['journal_prefix']).read_bytes()
    journal = (root / config['original_journal']).read_bytes()
    assert journal.startswith(prefix)
    assert len(prefix) == receipt['original_prefix_bytes']
    assert hashlib.sha256(prefix).hexdigest() == receipt['original_prefix_sha256']
    appended = [json.loads(line) for line in journal[len(prefix):].splitlines() if line.strip()]
    assert len(appended) == 9 and all(r['event'] == 'cache_reused' and
        r['condition'] == condition + '.grading2' for r in appended)
    starts = [json.loads(line) for line in journal.splitlines() if line.strip()]
    starts = [r for r in starts if r.get('event') == 'started']
    assert len(starts) == 15 and sum(r.get('reserved_cny', 0) for r in starts) <= 20
    assert receipt['budget_after']['started'] == 15 and receipt['budget_after']['unsettled_started'] == 0
    scoring_config = checked(root, config['scoring_config'])
    judge_identity = checked(root, config['judge_identity'])
    assert read(scoring_config)['hard_budget'] == {'max_generation_calls': 396, 'max_cny': 20.0}
    assert sha(judge_identity) == sha(recovery / 'judge_identity.json')
    for row in receipt['native_task_criteria_parser_files_unchanged']:
        checked(root, row)
    accepted_source = {'native_result': config['native_result'], 'receipt': config['receipt'],
        'original_result': config['source_result'], 'persisted_outputs': config['persisted_outputs'],
        'original_scoring_config': str(scoring_config), 'original_judge_identity': str(judge_identity),
        'original_journal': str(root / config['original_journal']),
        'one_native_grade_pass': True, 'new_paid_calls': 0, 'cache_reuses': 9}
    accepted = dict(previous, **native)
    accepted['previous_invalid'] = previous
    accepted['accepted_source'] = accepted_source
    result_rows = [accepted if r['condition'] == condition else r for r in rows]
    assert all(new == old for old, new in zip(rows, result_rows) if old['condition'] != condition)
    assert all(r['evaluation_status'] == 'completed' and not r.get('scorer_internal_error') for r in result_rows)
    clusters = {}
    for row in result_rows:
        clusters.setdefault(row['task_id'], []).append(row)
    assert len(clusters) == 60 and all(len(group) == 4 for group in clusters.values())
    total = sum(float(r['final_score']) for r in result_rows)
    maximum = sum(float(r['max_score']) for r in result_rows)
    result = dict(original, results=result_rows, instance_count=240, scored_instance_count=240,
        complete=True, prepared_instance_count=0, scorer_error_count=0, pending_count=0,
        total_score=total, total_max_score=maximum, mean_percent=100 * total / maximum,
        native_valid_subset_mean_percent=100 * total / maximum,
        expected_total_max_score=24000, auxiliary_zero_fill_mean_percent=total / 240,
        task_cluster_count=60)
    result['task_clusters'] = [{'task_id': task, 'condition_count': 4,
        'total_score': sum(float(r['final_score']) for r in group),
        'total_max_score': sum(float(r['max_score']) for r in group)}
        for task, group in sorted(clusters.items())]
    result['audit'] = {'schema': 'asi_fixed_onecase_recovery_v1',
        'collected_at_utc': datetime.now(timezone.utc).isoformat(),
        'original_report': config['original_report'], 'replaced_condition': condition,
        'unchanged_other_conditions': 239, 'new_evaluations_by_collector': 0,
        'previous_invalid': previous, 'accepted_source': accepted_source}
    assert sha(report_path) == config['original_report']['sha256']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    config = read(args.config)
    output = root / config['output']
    assert not output.exists(), 'Audited output exists; do not overwrite this fixed collection'
    result = collect(root, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output)
    assert sha(root / config['original_report']['path']) == config['original_report']['sha256']
    print(json.dumps({'output': str(output), 'output_sha256': sha(output),
        **{k:result[k] for k in ['instance_count', 'scored_instance_count', 'task_cluster_count',
          'complete', 'scorer_error_count', 'pending_count', 'total_score', 'total_max_score', 'mean_percent']},
        'original_report_sha256_unchanged': config['original_report']['sha256'],
        'native_evaluations': 0}, indent=2))
