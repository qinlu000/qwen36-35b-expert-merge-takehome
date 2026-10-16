"""Four fixed native Swift loss evaluations; no training or answer generation."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace


def evaluate_only(trainer, expected_rows):
    assert len(trainer.eval_dataset) == expected_rows
    assert not trainer.args.do_train and trainer.args.do_eval
    assert trainer.args.prediction_loss_only and not trainer.args.predict_with_generate
    assert trainer.optimizer is None and trainer.lr_scheduler is None
    assert trainer.state.global_step == 0
    trainer.model.requires_grad_(False)
    # Swift's training log callbacks require an on_train_begin timestamp.
    for callback in list(trainer.callback_handler.callbacks):
        if type(callback).__name__ in ('ProgressCallbackNew', 'PrinterCallbackNew'):
            trainer.remove_callback(type(callback))
    metrics = trainer.evaluate()
    assert trainer.optimizer is None and trainer.lr_scheduler is None
    assert trainer.state.global_step == 0
    assert not list(Path(trainer.args.output_dir).glob('checkpoint-*'))
    return {'metrics': metrics, 'native_eval_rows': len(trainer.eval_dataset),
            'global_step': 0, 'optimizer_created': False, 'scheduler_created': False,
            'train_called': False, 'generate_enabled': False, 'checkpoint_written': False}


def cpu_check(plan, project):
    assert plan['candidate_order'] == ['base', 'avg64', 'avg16', 'mixed883']
    assert plan['expected_rows'] == 249 and plan['max_length'] == 65536 and plan['gpus'] == 4
    source = project / plan['val_dataset']
    rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    assert len(rows) == 249 and all(row.get('messages') for row in rows)
    with tempfile.TemporaryDirectory() as folder:
        events = []

        class Model:
            def requires_grad_(self, enabled):
                assert enabled is False
                events.append('freeze_parameters')

            def generate(self, *args, **kwargs):
                raise AssertionError('Generation must never be called')

        class Trainer:
            args = SimpleNamespace(do_train=False, do_eval=True, prediction_loss_only=True,
                                   predict_with_generate=False, output_dir=folder)
            optimizer = lr_scheduler = None
            state = SimpleNamespace(global_step=0)
            model = Model()
            eval_dataset = rows
            callback_handler = SimpleNamespace(callbacks=[type('ProgressCallbackNew', (), {})(),
                                                          type('PrinterCallbackNew', (), {})()])

            def remove_callback(self, callback_class):
                events.append('remove_' + callback_class.__name__)
                self.callback_handler.callbacks = [c for c in self.callback_handler.callbacks if type(c) is not callback_class]

            def evaluate(self):
                events.append('evaluate')
                return {'cpu_spy_only': True}

            def train(self, *args, **kwargs):
                raise AssertionError('Trainer.train must never be called')

            def create_optimizer(self):
                raise AssertionError('An optimizer must never be created')

            def save_model(self, *args, **kwargs):
                raise AssertionError('Model weights must never be saved')

        trainer = Trainer()
        result = evaluate_only(trainer, 249)
        assert events == ['freeze_parameters', 'remove_ProgressCallbackNew', 'remove_PrinterCallbackNew', 'evaluate']
        assert not list(Path(folder).iterdir())
        trainer.eval_dataset = rows[:-1]
        try:
            evaluate_only(trainer, 249)
        except AssertionError:
            rejected_dropped_row = True
        else:
            raise AssertionError('A 248-row evaluation must be rejected')
    return {'passed': True, 'raw_rows': len(rows), 'max_length': plan['max_length'],
            'hook_events': events, 'rejects_missing_validation_row': rejected_dropped_row,
            'model_weights_loaded': False, 'gpu_used': False, 'hook_result': result,
            'scope': 'CPU spy trainer only; no model score or forward pass'}


def native_config(plan, project, output, candidate):
    config = json.loads((project / plan['native_config_source']).read_text())
    val = str(project / plan['val_dataset'])
    config.update(dataset=[val], val_dataset=[val], output_dir=str(output / 'native_args'),
                  do_train=False, do_eval=True, predict_with_generate=False,
                  prediction_loss_only=True, max_length=65536, split_dataset_ratio=0,
                  save_strategy='no', eval_strategy='no', load_best_model_at_end=False,
                  report_to=['none'], callbacks=[], external_plugins=[], add_version=False,
                  load_from_cache_file=True, dataloader_drop_last=False,
                  per_device_eval_batch_size=1, resume_from_checkpoint=None,
                  adapters=[], tuner_type='full', load_args=False)
    if candidate['adapter']:
        path = project / candidate['adapter']
        adapter = json.loads((path / 'adapter_config.json').read_text())
        config.update(adapters=[str(path)], tuner_type='lora',
                      lora_rank=adapter['r'], lora_alpha=adapter['lora_alpha'])
    assert config['loss_scale'] == 'default+ignore_empty_think'
    assert config['use_liger_kernel'] and config['liger_kernel_config']['fused_linear_cross_entropy']
    assert config['deepspeed'] == 'zero3' and not config['packing'] and not config['padding_free']
    assert config['truncation_strategy'] == 'delete'
    return config


def worker(path, expected_rows):
    from sft_eval_loss import enable_liger_eval_loss
    enable_liger_eval_loss()
    from swift.arguments import SftArguments
    from swift.pipelines.train.sft import SwiftSft
    from swift.utils import parse_args_from_dict

    config = json.loads(path.read_text())
    args = parse_args_from_dict(SftArguments, config)

    class LossOnly(SwiftSft):
        def train(self, trainer):
            return evaluate_only(trainer, expected_rows)

    started = time.monotonic()
    result = LossOnly(args).main()
    result.update(elapsed_seconds=time.monotonic() - started,
                  completed_at=datetime.now(timezone.utc).isoformat(),
                  native_config=str(path), max_length=65536,
                  scope='Existing full249 SFT validation loss only; no task benchmark or generation')
    if int(os.environ.get('RANK', '0')) == 0:
        output = path.parent / 'result.json'
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)


def run(plan, project):
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == plan['gpus'] == 4
    cpu = cpu_check(plan, project)
    mixed = json.loads((project / plan['required_mixed_summary']).read_text())
    assert mixed['passed'] is True and mixed['global_steps'] == 883
    assert mixed['final_checkpoint'].endswith('/checkpoint-883')
    output = project / (plan['output_prefix'] + '-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    (output / 'cpu_check.json').write_text(json.dumps(cpu, indent=2) + '\n')
    results = {}
    for name in plan['candidate_order']:
        directory = output / name
        directory.mkdir()
        config = native_config(plan, project, directory, plan['candidates'][name])
        path = directory / 'native_config.json'
        path.write_text(json.dumps(config, indent=2) + '\n')
        environment = dict(os.environ, MASTER_ADDR='127.0.0.1', NPROC_PER_NODE='4')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            environment['MASTER_PORT'] = str(sock.getsockname()[1])
        command = [sys.executable, '-m', 'torch.distributed.run', '--nproc_per_node=4',
                   '--master_addr=127.0.0.1', '--master_port=' + environment['MASTER_PORT'],
                   str(Path(__file__).resolve()), '--worker=' + str(path), '--expected-rows=249']
        (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        with (directory / 'execution.log').open('w') as log:
            subprocess.run(command, cwd=project, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
        results[name] = json.loads((directory / 'result.json').read_text())
        (output / 'summary.json').write_text(json.dumps({
            'completed_candidates': list(results), 'candidate_order': plan['candidate_order'],
            'complete': len(results) == 4, 'expected_rows': 249, 'max_length': 65536,
            'primary_model_remains': 'avg64', 'results': results}, indent=2) + '\n')
        print(json.dumps({'candidate_finished': name, 'result': results[name]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path)
    parser.add_argument('--cpu-check', action='store_true')
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--expected-rows', type=int, default=249)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.expected_rows)
    else:
        plan = json.loads(args.config.read_text())
        if args.cpu_check:
            print(json.dumps(cpu_check(plan, args.project), indent=2))
        else:
            run(plan, args.project)


if __name__ == '__main__':
    main()
