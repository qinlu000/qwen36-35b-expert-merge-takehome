"""Run the approved SWE lower-LR, whole-trajectory-filtered SFT candidate."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    root = args.project
    plan = json.loads(args.plan.read_text())
    original = json.loads((root / plan['source_training_config']).read_text())
    data = root / plan['data_dir']
    data_summary = json.loads((data / 'summary.json').read_text())
    assert original['learning_rate'] == 1e-4 and original['max_length'] == 65536
    assert not original.get('resume_from_checkpoint') and not original.get('adapters')
    job_id = os.environ['SLURM_JOB_ID']
    output = root / 'artifacts/runs' / f"{plan['name']}-{job_id}"
    output.mkdir(parents=True, exist_ok=False)
    config = dict(original)
    config.update(learning_rate=plan['learning_rate'],
        dataset=[str(data / 'train.messages.jsonl')],
        val_dataset=[str(data / 'val.messages.jsonl')],
        output_dir=str(output / 'training'), report_to=['tensorboard'],
        logging_dir=str(output / 'tensorboard'), run_name=output.name)
    changes = {k: {'original': original.get(k), 'candidate': v}
               for k, v in config.items() if original.get(k) != v}
    config_path = output / 'training_config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    (output / 'config_changes.json').write_text(json.dumps(changes, indent=2) + '\n')
    (output / 'experiment_plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    (output / 'data_summary.json').write_text(json.dumps(data_summary, indent=2) + '\n')
    env = os.environ.copy()
    env['NPROC_PER_NODE'] = str(plan['world_size'])
    env['MASTER_ADDR'] = '127.0.0.1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        env['MASTER_PORT'] = str(sock.getsockname()[1])
    command = [str(root / 'artifacts/envs/sft/bin/python'), '-m', 'torch.distributed.run',
        '--nproc_per_node', str(plan['world_size']), '--master_addr', env['MASTER_ADDR'],
        '--master_port', env['MASTER_PORT'], str(root / 'scripts/swift_sft_from_config.py'),
        str(config_path)]
    (output / 'training_command.json').write_text(json.dumps(command, indent=2) + '\n')
    print(json.dumps({'job_id': job_id, 'output': str(output),
        'world_size': plan['world_size'], 'learning_rate': config['learning_rate'],
        'max_length': config['max_length'], 'global_batch_size': 8,
        'config_changes': changes}), flush=True)
    started = time.monotonic()
    with (output / 'training.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    checkpoints = sorted((output / 'training').glob('checkpoint-*'),
        key=lambda p: int(p.name.split('-')[-1]))
    final = checkpoints[-1]
    state = json.loads((final / 'trainer_state.json').read_text())
    result = {'passed': True, 'job_id': job_id, 'final_checkpoint': str(final),
        'global_steps': state['global_step'], 'wall_seconds': time.monotonic() - started,
        'checkpoint_policy': 'Final checkpoint; no loss-based model selection.',
        'log_history': state['log_history']}
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'log_history'}), flush=True)


if __name__ == '__main__':
    main()
