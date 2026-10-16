"""Run native Swift SFT on the approved academic 500/100 data."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from sft_recipe import MODEL_REV, LOSS_SCALE, TARGET, common_args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--world-size', type=int, default=1, choices=(1, 2, 4))
    parser.add_argument('--check-args-only', action='store_true')
    args = parser.parse_args()
    root = args.project
    run_id = os.environ.get('SLURM_JOB_ID', 'cpu-args')
    out = root / f'artifacts/runs/hle-sft-r16-{run_id}'
    out.mkdir(parents=True, exist_ok=True)
    data = root / 'artifacts/data/candidates/night_hle_20261016/swift_ready'
    model = root / 'artifacts/models/Qwen3.6-35B-A3B' / MODEL_REV
    swift_args = common_args(model, args.world_size) + [
        '--dataset', str(data / 'train.messages.jsonl'), '--val_dataset', str(data / 'val.messages.jsonl'),
        '--max_length', '2048', '--num_train_epochs', '1', '--per_device_eval_batch_size', '1',
        '--eval_strategy', 'steps', '--eval_steps', '16', '--save_steps', '16',
        '--output_dir', str(out / 'training')]
    if args.check_args_only:
        from transformers import HfArgumentParser
        from swift import SftArguments
        native, = HfArgumentParser(SftArguments).parse_args_into_dataclasses(swift_args + ['--use_cpu', 'true'])
        assert native.lora_rank == 16 and native.lora_alpha == 32 and native.lora_dropout == .05
        assert native.target_regex == TARGET and native.loss_scale == LOSS_SCALE
        assert native.training_args.gradient_accumulation_steps * args.world_size == 8
        print(json.dumps({'passed': True, 'world_size': args.world_size,
            'gradient_accumulation_steps': native.training_args.gradient_accumulation_steps,
            'global_batch_size': 8, 'lora_rank': native.lora_rank, 'loss_scale': native.loss_scale,
            'num_train_epochs': native.training_args.num_train_epochs,
            'zero_stage': native.training_args.hf_deepspeed_config.config['zero_optimization']['stage'],
            'cpu_argument_construction_only': True}), flush=True)
        return
    env = os.environ.copy()
    env['NPROC_PER_NODE'] = str(args.world_size)
    env['MASTER_ADDR'] = '127.0.0.1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        env['MASTER_PORT'] = str(sock.getsockname()[1])
    command = [str(root / 'artifacts/envs/sft/bin/swift'), 'sft'] + swift_args
    (out / 'training_command.json').write_text(json.dumps(command, indent=2) + '\n')
    print(json.dumps({'training_started': True, 'world_size': args.world_size,
        'global_batch_size': 8, 'output': str(out)}), flush=True)
    started = time.monotonic()
    with (out / 'training.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    checkpoints = sorted((out / 'training').glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[-1]))
    final = checkpoints[-1]
    state = json.loads((final / 'trainer_state.json').read_text())
    report = {'passed': True, 'world_size': args.world_size, 'global_batch_size': 8,
        'global_steps': state['global_step'], 'final_checkpoint': str(final),
        'wall_seconds': time.monotonic() - started, 'log_history': state['log_history']}
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'log_history'}), flush=True)


if __name__ == '__main__':
    main()
