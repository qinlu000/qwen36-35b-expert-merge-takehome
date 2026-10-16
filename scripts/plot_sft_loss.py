"""Save native SFT loss history as a CSV and a figure."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    parser.add_argument('--title', required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    history = result['log_history']
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    columns = ['step', 'epoch', 'loss', 'eval_loss', 'learning_rate']
    with args.output_prefix.with_suffix('.csv').open('w') as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(history)
    train = [r for r in history if 'loss' in r]
    val = [r for r in history if 'eval_loss' in r]
    fig, ax = plt.subplots(figsize=(8, 4.5), layout='constrained')
    ax.plot([r['step'] for r in train], [r['loss'] for r in train],
            label='Training batch', color='#2563eb', linewidth=1.4)
    ax.plot([r['step'] for r in val], [r['eval_loss'] for r in val],
            label='SFT held-out examples', color='#d97706', marker='o', linewidth=1.8)
    best = min(val, key=lambda row: row['eval_loss'])
    selected = result.get('selected_checkpoint_step')
    labels = {best['step']: 'min val'}
    if result.get('native_completed', True):
        labels[val[-1]['step']] = labels.get(val[-1]['step'], '') + ' final'
    if selected is not None:
        labels[selected] = labels.get(selected, '') + ' selected'
    for row in val:
        if row['step'] in labels:
            near_end = row['step'] >= .85 * val[-1]['step']
            below = selected is not None and row['step'] != selected and abs(row['step'] - selected) < .1 * val[-1]['step']
            ax.annotate('cp {} ({})'.format(row['step'], labels[row['step']].strip()),
                        (row['step'], row['eval_loss']), xytext=(-4 if near_end else 0, -22 if below else 10),
                        textcoords='offset points', ha='right' if near_end else 'center', fontsize=8)
    ax.set(title=args.title, xlabel='Optimizer step', ylabel='Cross-entropy loss')
    ax.set_ylim(bottom=0)
    ax.grid(alpha=.2)
    ax.legend(loc='lower left', frameon=False)
    fig.savefig(args.output_prefix.with_suffix('.png'), dpi=200)
    plt.close(fig)


if __name__ == '__main__':
    main()
