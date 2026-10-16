"""Concatenate the exact expert partitions once for the Mixed SFT control."""
import argparse
import json
from pathlib import Path


def concatenate(paths, output):
    counts = []
    with output.open('w') as target:
        for path in paths:
            count = 0
            with path.open() as source:
                for line in source:
                    if line.strip():
                        row = json.loads(line)
                        training_row = {'messages': row['messages'], 'tools': row.get('tools') or []}
                        target.write(json.dumps(training_row, ensure_ascii=False) + '\n')
                        count += 1
            counts.append({'path': str(path), 'rows': count})
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, nargs='+', required=True)
    parser.add_argument('--val', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = concatenate(args.train, args.output_dir / 'train.messages.jsonl')
    val = concatenate(args.val, args.output_dir / 'val.messages.jsonl')
    manifest = {'train_sources': train, 'val_sources': val,
        'train_rows': sum(r['rows'] for r in train),
        'val_rows': sum(r['rows'] for r in val),
        'rule': 'Each expert training/validation example appears once; no oversampling or truncation',
        'columns': ['messages', 'tools'],
        'metadata': 'Source metadata remains in the expert partitions; missing tools are empty lists'}
    (args.output_dir / 'summary.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
