#!/usr/bin/env python3
"""Separate the existing complete Terminal records; leave combined and SAB sources untouched."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    source = args.root / 'artifacts/data/candidates/execution_sft_20261016'
    output = args.root / 'artifacts/data/candidates/terminal_sft_20261016'
    output.mkdir(parents=True, exist_ok=True)
    provenance = []
    counts = {}
    for split, count, total in [('train', 374, 456), ('val', 42, 62)]:
        rows = [json.loads(line) for line in (source / (split + '.messages.jsonl')).open()]
        assert len(rows) == total
        assert all(row.get('domain') == 'terminal' for row in rows[:count])
        with (output / (split + '.messages.jsonl')).open('w') as stream:
            for index, row in enumerate(rows[:count]):
                record = {'messages': row['messages'], 'tools': row.get('tools', [])}
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
                provenance.append({'split': split, 'row_index': index,
                                   **{k: v for k, v in row.items() if k not in ('messages', 'tools')}})
        counts[split] = count
    with (output / 'provenance.jsonl').open('w') as stream:
        for row in provenance:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    summary = {'expert': 'Terminal', 'counts': counts, 'source': str(source), 'output': str(output),
               'selection': 'Existing combined dataset prefix: Terminal train374/val42, same order.',
               'schema': ['messages', 'tools'], 'messages_and_tools_unchanged': True,
               'complete_history_context_limit': 65536, 'assistant_output_limit': 8192,
               'source_length_measurements_reused': True, 'new_tokenization_or_hash': False,
               'combined_source_modified': False, 'SAB_source_modified': False,
               'SAB_separate_expert_counts': {'train': 82, 'val': 20},
               'frozen_terminal_task_val_count': 99,
               'val_scope': 'Teacher trace loss; frozen task-success val99 remains separate.'}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
