"""Native Swift expert SFT with the shared fixed LoRA recipe."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from sft_recipe import MODEL_REV, common_args


def native_config(arguments):
    """Keep HF's CLI type conversion, but pass the dict field as a native dict."""
    from swift.arguments import SftArguments
    from swift.utils.utils import _patch_get_type_hints
    from transformers import HfArgumentParser

    pairs = dict(zip(arguments[::2], arguments[1::2]))
    liger = json.loads(pairs.pop('--liger_kernel_config'))
    cli = [item for pair in pairs.items() for item in pair]
    with _patch_get_type_hints():
        parser = HfArgumentParser([SftArguments])
    namespace, remaining = parser.parse_known_args(cli)
    assert not remaining
    config = {key[2:]: getattr(namespace, key[2:]) for key in pairs}
    config['liger_kernel_config'] = liger
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--max-length', type=int, required=True)
    parser.add_argument('--checkpoint-steps', type=int, default=16)
    parser.add_argument('--world-size', type=int, default=4, choices=(1, 2, 4))
    args = parser.parse_args()
    root = args.project
    output = root / f'artifacts/runs/{args.name}-sft-r16-{os.environ["SLURM_JOB_ID"]}'
    output.mkdir(parents=True, exist_ok=True)
    model = root / 'artifacts/models/Qwen3.6-35B-A3B' / MODEL_REV
    # Keep all small LoRA checkpoints, including the first validation and final.
    arguments = common_args(model, args.world_size, save_total_limit=0) + [
        '--dataset', str(args.data_dir / 'train.messages.jsonl'),
        '--val_dataset', str(args.data_dir / 'val.messages.jsonl'),
        '--max_length', str(args.max_length), '--truncation_strategy', 'delete',
        '--group_by_length', 'true',
        '--use_liger_kernel', 'true', '--liger_kernel_config', json.dumps({
            'rope': False, 'rms_norm': False, 'swiglu': False,
            'cross_entropy': False, 'fused_linear_cross_entropy': True}),
        '--prediction_loss_only', 'true',
        '--num_train_epochs', '1', '--per_device_eval_batch_size', '1',
        '--eval_strategy', 'steps', '--eval_steps', str(args.checkpoint_steps),
        '--save_steps', str(args.checkpoint_steps),
        '--output_dir', str(output / 'training')]
    config = native_config(arguments)
    config_path = output / 'training_config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    env = os.environ.copy()
    env['NPROC_PER_NODE'] = str(args.world_size)
    env['MASTER_ADDR'] = '127.0.0.1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        env['MASTER_PORT'] = str(sock.getsockname()[1])
    command = [str(root / 'artifacts/envs/sft/bin/python'), '-m', 'torch.distributed.run',
               '--nproc_per_node', str(args.world_size), '--master_addr', env['MASTER_ADDR'],
               '--master_port', env['MASTER_PORT'], str(root / 'scripts/swift_sft_from_config.py'),
               str(config_path)]
    (output / 'training_command.json').write_text(json.dumps(command, indent=2) + '\n')
    print(json.dumps({'native_swift_launched': True, 'name': args.name, 'world_size': args.world_size,
        'gradient_accumulation_steps': 8 // args.world_size, 'max_length': args.max_length,
        'data_dir': str(args.data_dir), 'output': str(output)}), flush=True)
    started = time.monotonic()
    with (output / 'training.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    checkpoints = sorted((output / 'training').glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[-1]))
    final = checkpoints[-1]
    state = json.loads((final / 'trainer_state.json').read_text())
    result = {'passed': True, 'name': args.name, 'world_size': args.world_size,
        'global_batch_size': 8, 'global_steps': state['global_step'], 'final_checkpoint': str(final),
        'best_model_checkpoint': state.get('best_model_checkpoint'),
        'wall_seconds': time.monotonic() - started, 'log_history': state['log_history']}
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'log_history'}), flush=True)


if __name__ == '__main__':
    main()
