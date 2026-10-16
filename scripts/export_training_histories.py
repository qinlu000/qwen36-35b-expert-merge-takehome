"""Export native loss histories without running training or task validation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


RUNS = {
    'swe': ('swe2k-sft-r16-726335', 249),
    'terminal': ('terminal-retry-sft-r16-726665', 250),
    'hle': ('hle-existing2k-sft-r16-726664', 250),
    'asi': ('asi-expanded-sft-r16-726336', 128),
    'mixed': ('mixed-existing2k-sft-r16-726666', 883),
}


def export(project, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (run, selected) in RUNS.items():
        root = project / 'artifacts/runs' / run
        summary_path = root / 'summary.json'
        log_path = root / 'training/logging.jsonl'
        logs = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        history = summary.get('log_history')
        if history is None:
            history = []
            for row in logs:
                if 'loss' not in row and 'eval_loss' not in row:
                    continue
                row = dict(row)
                if 'step' not in row:
                    row['step'] = int(row['global_step/max_steps'].split('/')[0])
                history.append(row)
        train = [row for row in history if 'loss' in row]
        validation = [row for row in history if 'eval_loss' in row]
        best = min(validation, key=lambda row: row['eval_loss'])
        complete = summary.get('passed') is True
        memory = [row['memory(GiB)'] for row in logs if isinstance(row.get('memory(GiB)'), (int, float))]
        value = {
            'run': run, 'captured_at_utc': datetime.now(timezone.utc).isoformat(),
            'native_completed': complete,
            'source': str(summary_path if complete else log_path),
            'selected_checkpoint_step': selected if complete else None,
            'selected_checkpoint_note': 'Frozen experiment checkpoint; HLE selection uses saved independent results, not minimum CE. Mixed final883 is the same-data one-pass control.' if complete else 'Still training; no final control checkpoint available.',
            'best_loss_checkpoint_step': best['step'],
            'best_eval_loss': best['eval_loss'],
            'observed_optimizer_steps': max(row['step'] for row in train),
            'wall_seconds': summary.get('wall_seconds'),
            'world_size': summary.get('world_size'),
            'native_memory_gib_reported_max': max(memory) if memory else None,
            'memory_note': 'Native rank0 current-CUDA-device PyTorch max_memory_reserved /2**30, rounded2 decimals, high-water mark since latest reset. Maximum across log rows; not all ranks, allocated memory, or complete device peak. Verified Swift trainers/patcher.py and utils/torch_utils.py with LOCAL_WORLD_SIZE>1.',
            'log_history': history,
        }
        destination = output / (name + '_loss.json')
        destination.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        manifest[name] = {key: value[key] for key in [
            'run', 'native_completed', 'selected_checkpoint_step', 'best_loss_checkpoint_step',
            'best_eval_loss', 'observed_optimizer_steps', 'wall_seconds', 'world_size',
            'native_memory_gib_reported_max']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.project.resolve(), args.output.resolve())
