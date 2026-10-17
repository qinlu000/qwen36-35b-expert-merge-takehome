"""Replay native training scalars into TensorBoard; does not run a model."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from tensorboard.compat.proto.event_pb2 import Event
from tensorboard.compat.proto.summary_pb2 import Summary
from tensorboard.summary.writer.event_file_writer import EventFileWriter

TAGS = {
    'loss': 'train/cross_entropy',
    'learning_rate': 'train/learning_rate',
    'grad_norm': 'train/gradient_norm',
    'epoch': 'progress/epoch',
    'eval_loss': 'diagnostic/teacher_forced_eval_cross_entropy',
    'eval_token_acc': 'diagnostic/teacher_forced_token_accuracy',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('curves/training_20261017/source'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    exported = time.time()
    runs = {}
    for source in sorted(args.source.glob('*_loss.json')):
        native = json.loads(source.read_text())
        name = source.stem.removesuffix('_loss')
        writer = EventFileWriter(str(args.output / name))
        counts = {}
        for row in native['log_history']:
            step = int(row['step'])
            for field, tag in TAGS.items():
                if row.get(field) is None:
                    continue
                writer.add_event(Event(wall_time=exported, step=step,
                    summary=Summary(value=[Summary.Value(tag=tag, simple_value=float(row[field]))])))
                counts[tag] = counts.get(tag, 0) + 1
        writer.flush()
        writer.close()
        runs[name] = {'source': str(source), 'native_run': native['run'], 'scalar_counts': counts}
    report = {'exported_at_utc': datetime.fromtimestamp(exported, timezone.utc).isoformat(),
        'logdir': str(args.output.resolve()), 'runs': runs,
        'entropy_recorded': False, 'new_training_or_forward_calls': 0,
        'limitations': ['All event wall_time values are export time; use the step axis, not elapsed time.',
            'Cross-entropy and teacher-forced token accuracy are training diagnostics, not benchmark scores or checkpoint selection criteria.',
            'Entropy was not logged and is not synthesized or set to zero.']}
    (args.output / 'export.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
