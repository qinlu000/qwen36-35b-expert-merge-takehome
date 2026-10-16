"""Read preserved Base answers and grade-only recoveries; never launch a model."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import statistics
import time

from collect_swe_final import score as swe_score


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def terminal(root, output):
    original = root / 'artifacts/results/base-terminal-independent-repair32-20261016'
    repair = root / 'artifacts/results/base-terminal-native-gaps-20261017'
    source = repair / 'corrected445_summary.json'
    raw = read(source if source.exists() else original / 'corrected445_summary.json')
    accepted = raw.get('accepted_first_valid') or raw['accepted']
    seeds = []
    for seed in range(5):
        rows = [row for key, row in accepted.items() if key.endswith('/seed' + str(seed))]
        correct = sum(row['reward'] for row in rows)
        seeds.append({'seed': seed, 'expected': 89, 'valid_covered': len(rows),
                      'correct_count': correct, 'score_percent': 100 * correct / 89 if len(rows) == 89 else None})
    strict = {**raw, 'per_seed': seeds, 'source_summary': str(source),
              'strict_native_complete': len(accepted) == 445}
    save(output / 'terminal_strict_summary.json', strict)

    audit = read(root / 'analysis/source_snapshots/terminal_three_compute_timeout_audit_20261017.json')
    previous = read(original / 'checkpoint.json')['scores']
    derived = {}
    for row in audit['entries']:
        key = row['key']
        if key in accepted:
            continue
        original_result = Path(row['exact_original_result_path'])
        assert previous[key]['path'] == str(original_result)
        result = read(original_result)
        assert result.get('verifier_result') is None
        assert row['derived_budget_reward'] == 0 and row['native_grade_unchanged']
        assert row['eligibility']['official_test_started']
        assert row['eligibility']['verifier_timeout_sec'] == 900
        assert not row['eligibility']['matched_infrastructure_error_markers']
        derived[key] = {'path': str(original_result), 'native_reward': None,
                        'derived_budget_reward': 0, 'audit': str(root / 'analysis/source_snapshots/terminal_three_compute_timeout_audit_20261017.json')}
    accounted = len(accepted) + len(derived)
    budget_seeds = []
    for row in seeds:
        extra = sum(key.endswith('/seed' + str(row['seed'])) for key in derived)
        budget_seeds.append({**row, 'native_reward_trials': row['valid_covered'],
                             'derived_timeout_failures': extra,
                             'accounted_trials': row['valid_covered'] + extra,
                             'score_percent': 100 * row['correct_count'] / 89 if row['valid_covered'] + extra == 89 else None})
    complete = accounted == 445
    values = [row['score_percent'] for row in budget_seeds]
    budget = {'expected': 445, 'native_reward_trials': len(accepted), 'derived_timeout_failures': len(derived),
              'accounted_trials': accounted, 'complete': complete, 'strict_native_complete': len(accepted) == 445,
              'primary_mean_percent': statistics.mean(values) if complete else None,
              'sample_sd_percent_ddof1': statistics.stdev(values) if complete else None,
              'per_seed': budget_seeds, 'derived': derived,
              'metric': 'Harbor default Mean: existing native rewards plus zero for three audited candidate-computation verifier timeouts',
              'native_rewards_modified': False, 'same_policy_required_for_all_compared_models': True}
    save(output / 'terminal_budget_summary.json', budget)
    return strict, budget


def swe(root, output):
    original = root / 'artifacts/eval/base_swe_v2_20261016_clean28'
    repair = root / 'artifacts/eval/base_swe_gap_repair_20261017'
    frozen = read(original / 'corrected51_summary.json')
    audits_path = repair / 'candidate-failure-audits.json'
    audits = {row['task_id']: row for row in read(audits_path)['audits']} if audits_path.exists() else {}
    rows = []
    for prior in frozen['tasks']:
        row = dict(prior)
        name = row['task_id']
        valid = row.get('status') == 'valid_scored' or row.get('reward') in (0, 1) and not row.get('invalid_reason')
        if not valid and name in audits:
            audit = audits[name]
            result = read(Path(audit['original_result']))
            reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
            assert reward == audit['native_reward'] == audit['audited_reward'] == 0
            assert row.get('result') == audit['original_result']
            assert Path(audit['source_patch']).stat().st_size == audit['patch_bytes']
            row.update(reward=reward, invalid_reason=None, audit_source=str(audits_path),
                       audit_reason=audit['audit_reason'], original_invalid_reason=prior['invalid_reason'])
            valid = True
        replay = repair / 'replay' / name / 'result.json'
        if not valid and replay.exists():
            new = swe_score(replay)
            if new['invalid_reason'] is None:
                row = {**new, 'previous_invalid_result': prior.get('result')}
                valid = True
            else:
                row['additional_invalid_replay'] = new
        row['status'] = 'valid_scored' if valid else 'invalid_requires_replay'
        rows.append(row)
    valid = [row for row in rows if row['status'] == 'valid_scored']
    resolved = sum(row['reward'] == 1 for row in valid)
    complete = len(valid) == 51
    summary = {'as_of': datetime.now(timezone.utc).isoformat(), 'expected': 51,
               'valid_scored': len(valid), 'unscored': 51 - len(valid), 'resolved': resolved,
               'invalid_pending': 51 - len(valid), 'awaiting_generation_or_replay': 0,
               'complete': complete, 'primary_score_percent': 100 * resolved / 51 if complete else None,
               'manual_retry_task_count': 3, 'manual_retry_planned_task_count': 3,
               'clean28_valid_scored': len(valid) - 23, 'retained_native23': 23,
               'selection': 'Preserve first valid frozen answer grades, including zeros; original patch replay only',
               'historical_source': str(original / 'corrected51_summary.json'), 'new_model_calls': 0, 'tasks': rows}
    summary['grade_only_replays_active'] = sum((p.parent / 'config.json').exists() and not p.exists()
        for p in (repair / 'replay' / row['task_id'] / 'result.json' for row in rows))
    save(output / 'swe51_summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / '.collector.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    while True:
        strict, budget = terminal(args.project, args.output)
        sw = swe(args.project, args.output)
        hle = read(args.project / 'artifacts/runs/hle_judge_v2_20261016/summary.json')
        asi = read(args.project / 'artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json')
        complete = budget['complete'] and sw['complete'] and hle['complete'] and asi['scored_instance_count'] == 240
        summary = {'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                   'complete_under_disclosed_harbor_budget_aggregation': complete,
                   'strict_native_complete': strict['complete'] and sw['complete'] and hle['complete'],
                   'TB': budget, 'SWE': {k: v for k, v in sw.items() if k != 'tasks'},
                   'HLE': {'scored': hle['scored'], 'expected': 2500, 'score_percent': hle['score'],
                           'accounted_cost_cny': hle['accounted_cost_cny'], 'judge_calls': hle['judge_generation_calls']},
                   'ASI': {'scored': asi['scored_instance_count'], 'expected': 240, 'score_percent': asi['mean_percent']},
                   'new_model_generations': 0, 'original_raw_results_preserved': True}
        summary['equal_weight_macro_percent'] = (statistics.mean([
            budget['primary_mean_percent'], sw['primary_score_percent'], hle['score'], asi['mean_percent']])
            if complete else None)
        summary['macro_policy'] = 'Equal weight of four percentage metrics; Terminal uses the separately disclosed Harbor default fixed-budget aggregation.'
        save(args.output / 'summary.json', summary)
        with (args.output / 'swe_task_scores.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['task_id', 'status', 'reward', 'source', 'audit'])
            writer.writeheader()
            for row in sw['tasks']:
                writer.writerow({'task_id': row['task_id'], 'status': row['status'], 'reward': row.get('reward'),
                                 'source': row.get('result') or row.get('accepted_result'), 'audit': row.get('audit_source')})
        lines = ['# Base gap completion', '', summary['updated_at_utc'], '',
                 '| Benchmark | Native score coverage | Complete score (%) |', '|---|---:|---:|',
                 f"| HLE | {hle['scored']}/2500 | {hle['score']} |",
                 f"| ASI (public local) | {asi['scored_instance_count']}/240 | {asi['mean_percent']} |",
                 f"| SWE | {sw['valid_scored']}/51 | {sw['primary_score_percent']} |",
                 f"| Terminal | {budget['native_reward_trials']}/445 | {budget['primary_mean_percent']} |", '',
                 'Terminal score uses Harbor default Mean for exactly three audited candidate-computation timeouts. '
                 'Their original native rewards stay null; no dependency/infrastructure failure is silently assigned zero.', '',
                 'New Base model generations: 0. All original answers, patches and unsuccessful grading attempts are retained.', '',
                 'Equal-weight four-benchmark macro (%): ' + str(summary['equal_weight_macro_percent']), '']
        (args.output / 'report.md').write_text('\n'.join(lines))
        print(json.dumps({'updated_at_utc': summary['updated_at_utc'], 'TB_native': budget['native_reward_trials'],
                          'TB_budget_accounted': budget['accounted_trials'], 'SWE_valid': sw['valid_scored'],
                          'complete_under_disclosed_budget_aggregation': complete}), flush=True)
        if complete or args.once:
            return
        time.sleep(15)


if __name__ == '__main__':
    main()
