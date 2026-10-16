"""Replot the four completed native SFT loss results; no model evaluation."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path,
                        default=root / 'curves/merge_loss249_20261017/source_summary.json')
    parser.add_argument('--output-prefix', type=Path,
                        default=root / 'curves/merge_loss249_20261017')
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    order = ['base', 'avg64', 'avg16', 'mixed883']
    labels = ['Base', 'AVG64', 'AVG16', 'Mixed883']
    assert summary['complete'] and summary['completed_candidates'] == order
    assert summary['expected_rows'] == 249 and summary['max_length'] == 65536
    rows = []
    for candidate, label in zip(order, labels):
        result = summary['results'][candidate]
        assert result['native_eval_rows'] == 249 and result['max_length'] == 65536
        assert result['global_step'] == 0 and not result['train_called']
        rows.append({'candidate': label, 'eval_loss': result['metrics']['eval_loss'],
                     'native_eval_rows': result['native_eval_rows'],
                     'max_length': result['max_length'], 'global_step': result['global_step']})

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    with args.output_prefix.with_suffix('.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.titleweight': 'bold', 'axes.spines.top': False,
                         'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(10.4, 6.3))
    values = [row['eval_loss'] for row in rows]
    bars = ax.bar(labels, values, width=0.62,
                  color=['#98A2B3', '#087F8C', '#76B6BB', '#627A9D'], zorder=3)
    ax.bar_label(bars, labels=[f'{value:.4f}' for value in values], padding=7, fontsize=12)
    ax.set_ylabel('Native SFT held-out cross-entropy')
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#E5E7EB', linewidth=0.8)
    ax.tick_params(axis='x', length=0, pad=10)
    ax.spines['left'].set_color('#AAB2BE')
    ax.spines['bottom'].set_color('#AAB2BE')
    fig.suptitle('Four-expert merge: native held-out SFT loss', fontsize=17, y=0.97,
                 fontweight='bold')
    fig.text(0.5, 0.91, 'Same 249 examples | 64K (65,536-token) limit | not a task benchmark',
             ha='center', fontsize=11, color='#475467')
    fig.text(0.5, 0.065, 'AVG64: exact rank 64 (84.66M adapter parameters); '
             'AVG16: SVD rank 16 (21.17M).', ha='center', fontsize=9, color='#475467')
    fig.text(0.5, 0.035, 'One fixed native evaluation per model; no error bars.',
             ha='center', fontsize=9, color='#475467')
    fig.subplots_adjust(left=0.105, right=0.97, bottom=0.18, top=0.84)
    fig.savefig(args.output_prefix.with_suffix('.png'), dpi=180, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
