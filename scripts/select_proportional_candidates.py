"""Select a metadata-only proportional core; missing benchmark strata stay explicit."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from candidate_selection import proportional_quotas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--distribution', type=Path, required=True)
    parser.add_argument('--benchmark', choices=['hle', 'terminal', 'asi'], required=True)
    parser.add_argument('--partition-field', default='candidate_partition')
    parser.add_argument('--category-field', default='hle_category')
    parser.add_argument('--rank-field', default='stable_rank_key')
    parser.add_argument('--teacher-regex')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    target = json.loads(args.distribution.read_text())[args.benchmark]
    weights = target['discipline_counts' if args.benchmark == 'asi' else 'category_counts']
    input_rows = [json.loads(line) for line in args.manifest.open()]
    rows = [row for row in input_rows if not args.teacher_regex or
            re.search(args.teacher_regex, row.get('teacher', ''), re.I)]
    aliases = {'Mathematics': 'Math', 'Biology': 'Biology/Medicine',
               'Computer Science': 'Computer Science/AI',
               'Humanities': 'Humanities/Social Science'} if args.benchmark == 'hle' else {}
    for row in rows:
        category = row[args.category_field]
        if category in aliases:
            row['source_category_before_target_alias'] = category
            row[args.category_field] = aliases[category]
    groups = defaultdict(list)
    for row in rows:
        groups[row[args.partition_field], row[args.category_field]].append(row)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {'benchmark': args.benchmark, 'target_counts': weights,
              'input_rows': len(input_rows), 'teacher_filter': args.teacher_regex,
              'explicit_target_category_aliases': aliases,
              'teacher_counts_after_filter': dict(Counter(row.get('teacher', 'not_recorded') for row in rows)),
              'selection': 'maximum available proportional candidate core over covered categories',
              'partitions': {}, 'scope': 'Not a training token budget or executable task-dev release. Missing categories are not silently replaced.'}
    selected_families = {}
    for partition in ['train', 'val']:
        available = {key: len(groups[partition, key]) for key in weights}
        covered = {key: count for key, count in weights.items() if available[key]}
        total = min((available[key] * sum(covered.values()) // weight
                     for key, weight in covered.items()), default=0)
        quotas = proportional_quotas(total, covered) if covered else {}
        while any(count > available[key] for key, count in quotas.items()):
            total -= 1
            quotas = proportional_quotas(total, covered)
        selected = []
        for category, count in quotas.items():
            selected += sorted(groups[partition, category], key=lambda row: row[args.rank_field])[:count]
        selected.sort(key=lambda row: (row[args.category_field], row[args.rank_field]))
        path = args.output_dir / (partition + '.proportional_core.jsonl')
        path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in selected))
        selected_families[partition] = {row['family_key'] for row in selected}
        assert len(selected_families[partition]) == len(selected)
        reference_total = round(len(selected) * sum(weights.values()) / sum(covered.values())) if covered else 0
        reference_quotas = proportional_quotas(reference_total, weights)
        selected_counts = Counter(row[args.category_field] for row in selected)
        report['partitions'][partition] = {
            'available_counts': available, 'selected': len(selected), 'selected_counts': dict(Counter(
                row[args.category_field] for row in selected)),
            'conditional_ratio_only': bool(len(covered) != len(weights)),
            'full_target_reference_slots_not_final_size': reference_total,
            'full_target_reference_quotas': reference_quotas,
            'unfilled_reference_category_slots': {key: max(0, reference_quotas[key] - selected_counts[key]) for key in weights},
            'unmapped_rows': sum(len(value) for (p, c), value in groups.items()
                                 if p == partition and c not in weights),
            'missing_categories': [key for key in weights if not available[key]],
            'covered_target_task_weight': sum(covered.values()),
            'total_target_task_weight': sum(weights.values()),
            'modality_counts': dict(Counter(str(row.get('modality', 'not_recorded')) for row in selected)),
            'validation_readiness': dict(Counter(str(row.get('validation_readiness', 'not_recorded')) for row in selected)),
            'train_readiness': dict(Counter(str(row.get('train_readiness', 'not_recorded')) for row in selected)),
            'output': str(path),
        }
    overlap = selected_families['train'] & selected_families['val']
    assert not overlap
    report['family_overlap_train_val'] = len(overlap)
    (args.output_dir / 'proportional_summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
