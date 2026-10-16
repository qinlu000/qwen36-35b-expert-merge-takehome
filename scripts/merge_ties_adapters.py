#!/usr/bin/env python3
"""Fixed dense-delta TIES pilot/export; no model, training or inference loads.

Real matrices run only on one allocated CUDA device. Self-tests use tiny CPU
matrices and the pinned installed PEFT utility without importing model classes.
"""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import sys
import time

import torch
from safetensors import safe_open
from safetensors.torch import save_file


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def load_ties(package, expected_hash):
    assert '__version__ = "0.20.0"' in (package / '__init__.py').read_text()
    path = package / 'utils/merge_utils.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
    spec = importlib.util.spec_from_file_location('pinned_peft_merge_utils', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ties


def rss():
    current = None
    status = Path('/proc/self/status')
    if status.exists():
        current = int(next(line.split()[1] for line in status.read_text().splitlines()
                           if line.startswith('VmRSS:'))) * 1024
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'current_bytes': current,
            'process_lifetime_high_water_bytes': peak if sys.platform == 'darwin' else peak * 1024}


def true_delta(a, b, alpha, rank):
    return (alpha / rank) * (b @ a)


def svd_factors(dense, rank, driver=None):
    u, singular, vh = torch.linalg.svd(dense, full_matrices=False, driver=driver)
    q = min(rank, singular.numel())
    a = dense.new_zeros((rank, dense.shape[1]))
    b = dense.new_zeros((dense.shape[0], rank))
    a[:q] = vh[:q]
    b[:, :q] = u[:, :q] * singular[:q]
    total = float(singular.double().square().sum())
    tail = float(singular[q:].double().square().sum())
    stats = {'svd_components': q, 'zero_padded_components': rank - q,
        'svd_singular_energy': total, 'svd_tail_energy': tail,
        'ideal_tail_relative_frobenius': math.sqrt(tail / total) if total else 0.0,
        'retained_singular_energy_fraction': 1 - tail / total if total else 1.0}
    return a, b, stats


def self_test(ties):
    factors = [
        (torch.tensor([[1., 3.]]), torch.tensor([[2.], [5.]])),
        (torch.tensor([[2., -1.]]), torch.tensor([[1.], [-3.]])),
        (torch.tensor([[1., -3.]]), torch.tensor([[-2.], [5.]])),
        (torch.tensor([[3., 1.]]), torch.tensor([[1.], [2.]]))]
    deltas = [true_delta(a, b, alpha=32, rank=16) for a, b in factors]
    for delta in deltas:
        values = delta.abs().flatten().sort(descending=True).values
        assert values[1] > values[2], 'Fixture must not tie at the top-k threshold'
    result = ties(deltas, torch.ones(4), density=.5, majority_sign_method='total')
    # No absolute-value tie at any input's top-k threshold. The bottom-left
    # sign-election total is zero; pinned PEFT explicitly elects positive.
    expected = torch.tensor([[6., 12.], [12., 18.]])
    torch.testing.assert_close(result, expected)
    assert not torch.allclose(result, 2 * expected), 'Reject repeated alpha/r'
    quarter = ties(deltas, torch.full((4,), .25), density=.5, majority_sign_method='total')
    torch.testing.assert_close(quarter, result / 4)
    means = 2 * (sum(b for _, b in factors) / 4) @ (sum(a for a, _ in factors) / 4)
    assert not torch.allclose(means, sum(deltas) / 4), 'Reject factor mean cross terms'
    sparse = [torch.tensor([[5., -4., 3., -2., 1.]]) * value for value in [1, 2, 3, 4]]
    fixed_density = ties(sparse, torch.ones(4), density=.2, majority_sign_method='total')
    torch.testing.assert_close(fixed_density, torch.tensor([[12.5, 0., 0., 0., 0.]]))
    small = torch.tensor([[1., 0., 2.], [0., 3., 1.]])
    a, b, stats = svd_factors(small, 64)
    assert a.shape == (64, 3) and b.shape == (2, 64)
    assert stats['zero_padded_components'] == 62
    torch.testing.assert_close(b @ a, small, rtol=2e-5, atol=2e-6)
    a1, b1, rank1 = svd_factors(small, 1)
    measured = float(torch.linalg.vector_norm(small - b1 @ a1) / torch.linalg.vector_norm(small))
    assert abs(measured - rank1['ideal_tail_relative_frobenius']) < 2e-6
    return {'passed': True, 'device': 'cpu', 'torch_version': torch.__version__,
        'real_adapter_tensor_reads': 0,
        'tests': ['single_scaled_true_delta_ties_matches_manual_result',
            'reject_double_scaling', 'disjoint_mean_does_not_need_quarter_weights',
            'reject_factor_mean_cross_terms', 'fixed_density_point2_topk', 'rank64_zero_padding_for_min_dim2',
            'truncated_svd_error_matches_singular_tail'],
        'manual_ties_result': result.tolist()}


def input_inventory(project, config):
    configs, readers, source_stats = [], [], []
    fields = ['base_model_name_or_path', 'target_modules', 'r', 'lora_alpha',
        'fan_in_fan_out', 'use_rslora', 'use_dora', 'bias', 'lora_bias',
        'modules_to_save', 'rank_pattern', 'alpha_pattern', 'target_parameters']
    for row in config['inputs']:
        directory = project / row['adapter']
        metadata = read(directory / 'adapter_config.json')
        assert metadata['r'] == 16 and metadata['lora_alpha'] == 32
        assert Path(metadata['base_model_name_or_path']).name == config['base_revision']
        assert metadata.get('revision') in (None, config['base_revision'])
        assert not any(metadata.get(key) for key in ['use_rslora', 'use_dora',
            'fan_in_fan_out', 'lora_bias', 'modules_to_save', 'rank_pattern',
            'alpha_pattern', 'target_parameters'])
        assert metadata['bias'] == 'none'
        if configs:
            assert all(metadata.get(key) == configs[0].get(key) for key in fields)
        configs.append(metadata)
        weight = directory / 'adapter_model.safetensors'
        stat = weight.stat()
        source_stats.append({'adapter': row['adapter'], 'bytes': stat.st_size,
                             'mtime_ns': stat.st_mtime_ns})
        readers.append(safe_open(weight, framework='pt', device='cpu'))
    keys = sorted(readers[0].keys())
    assert len(keys) == 620 and all(sorted(reader.keys()) == keys for reader in readers)
    modules = []
    for key in keys:
        if not key.endswith('.lora_A.weight'):
            continue
        b_key = key.replace('.lora_A.weight', '.lora_B.weight')
        assert '.language_model.layers.' in key and '.experts.' not in key and '.visual.' not in key
        assert re.fullmatch(configs[0]['target_modules'], key.removeprefix('base_model.model.').removesuffix('.lora_A.weight'))
        a_shape = readers[0].get_slice(key).get_shape()
        b_shape = readers[0].get_slice(b_key).get_shape()
        assert len(a_shape) == len(b_shape) == 2 and a_shape[0] == b_shape[1] == 16
        assert all(reader.get_slice(key).get_shape() == a_shape and
                   reader.get_slice(b_key).get_shape() == b_shape for reader in readers)
        modules.append({'a_key': key, 'b_key': b_key, 'shape': [b_shape[0], a_shape[1]]})
    counts = Counter(tuple(module['shape']) for module in modules)
    expected = {tuple(row['shape']): row['modules'] for row in config['expected_shapes']}
    assert len(modules) == 310 and dict(counts) == expected
    base = project / 'artifacts/models/Qwen3.6-35B-A3B' / config['base_revision']
    assert (base / 'config.json').exists()
    return configs, readers, modules, counts, source_stats


def merge_module(module, readers, configs, ties, config):
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    baseline_allocated = torch.cuda.memory_allocated()
    cpu_before = rss()
    started = time.perf_counter()
    timings = {}

    def stage(name, operation):
        torch.cuda.synchronize()
        before = time.perf_counter()
        result = operation()
        torch.cuda.synchronize()
        timings[name] = time.perf_counter() - before
        return result

    factors = stage('read_and_h2d', lambda: [(reader.get_tensor(module['a_key']).to('cuda', dtype=torch.float32),
        reader.get_tensor(module['b_key']).to('cuda', dtype=torch.float32)) for reader in readers])
    deltas = stage('true_delta_matmul', lambda: [true_delta(a, b, metadata['lora_alpha'], metadata['r'])
        for metadata, (a, b) in zip(configs, factors)])
    del factors
    dense = stage('ties', lambda: config['lambda'] * ties(deltas,
        torch.ones(len(deltas), dtype=torch.float32, device='cuda'),
        density=config['density'], majority_sign_method=config['majority_sign_method']))
    del deltas
    a, b, svd = stage('reduced_svd_and_factorize',
        lambda: svd_factors(dense, config['rank'], config['svd_driver']))

    def reconstruction():
        residual = dense - b @ a  # alpha/r=1; no second coefficient multiplier.
        norm2 = float(dense.double().square().sum())
        error2 = float(residual.double().square().sum())
        return norm2, error2

    norm2, error2 = stage('reconstruction_check', reconstruction)
    actual_error = math.sqrt(error2 / norm2) if norm2 else 0.0
    assert math.isfinite(actual_error)
    assert actual_error <= svd['ideal_tail_relative_frobenius'] + 1e-4
    a_cpu, b_cpu = stage('factor_d2h', lambda: (a.cpu().contiguous(), b.cpu().contiguous()))
    allocated = torch.cuda.max_memory_allocated()
    reserved = torch.cuda.max_memory_reserved()
    row = {**module, 'elapsed_seconds': time.perf_counter() - started,
        'stage_seconds': timings, 'cpu_rss_before': cpu_before, 'cpu_rss_after': rss(),
        'torch_allocator_baseline_allocated_bytes': baseline_allocated,
        'torch_allocator_peak_allocated_bytes': allocated,
        'torch_allocator_incremental_peak_allocated_bytes': allocated - baseline_allocated,
        'torch_allocator_peak_reserved_bytes': reserved,
        'gpu_peak_definition': 'PyTorch CUDA allocator peaks, not a sampled whole-device peak',
        'dense_frobenius_squared': norm2, 'saved_factor_error_squared': error2,
        'actual_reconstruction_relative_frobenius': actual_error, **svd}
    return row, a_cpu, b_cpu


def run(args, config, ties):
    assert os.environ.get('SLURM_JOB_ID'), 'Real-weight SVD requires an allocated Slurm job'
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1
    assert 'H100' in torch.cuda.get_device_name(0)
    assert config['density'] == .2 and config['majority_sign_method'] == 'total'
    assert config['weights'] == [1, 1, 1, 1] and config['lambda'] == 1
    assert config['rank'] == config['lora_alpha'] == 64
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    started = time.perf_counter()
    torch.cuda.init()
    # Tiny warmup only; no real layer or task is executed twice.
    torch.linalg.svd(torch.eye(8, device='cuda'), full_matrices=False)
    torch.cuda.synchronize()
    initialization_seconds = time.perf_counter() - started
    project = args.project.resolve()
    configs, readers, modules, counts, source_stats = input_inventory(project, config)
    if args.mode == 'pilot':
        by_shape = {}
        for module in modules:  # inventory order is lexicographic A-key order.
            by_shape.setdefault(tuple(module['shape']), module)
        selected = [by_shape[shape] for shape in sorted(by_shape, key=lambda s: (s[0] * s[1], s))]
    else:
        selected = modules
    output = project / config['output_root']
    report_dir = output / (args.mode + '-' + os.environ['SLURM_JOB_ID'])
    report_dir.mkdir(parents=True, exist_ok=False)
    if args.mode == 'export':
        assert not (output / 'adapter_model.safetensors').exists()
        assert not (output / 'adapter_config.json').exists()
    report = {'state': 'running', 'mode': args.mode, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'config': config, 'input_stats': source_stats,
        'self_tests': self_test(ties), 'torch_version': torch.__version__, 'cuda_version': torch.version.cuda,
        'gpu_name': torch.cuda.get_device_name(0), 'initialization_seconds': initialization_seconds,
        'rows': [], 'model_requests': 0, 'training_or_loss_evaluations': 0,
        'primary_avg64_modified': False, 'real_task_metrics_used': False}
    weights_out = {}
    try:
        for module in selected:
            gc.collect()
            torch.cuda.empty_cache()
            row, a_cpu, b_cpu = merge_module(module, readers, configs, ties, config)
            report['rows'].append(row)
            if args.mode == 'export':
                weights_out[module['a_key']], weights_out[module['b_key']] = a_cpu, b_cpu
            del a_cpu, b_cpu
            save(report_dir / 'report.json', report)
            print(json.dumps({'module': module['a_key'], 'shape': module['shape'],
                'seconds': row['elapsed_seconds'], 'peak_allocated_bytes': row['torch_allocator_peak_allocated_bytes'],
                'relative_frobenius': row['actual_reconstruction_relative_frobenius']}), flush=True)
        for row in source_stats:
            stat = (project / row['adapter'] / 'adapter_model.safetensors').stat()
            assert stat.st_size == row['bytes'] and stat.st_mtime_ns == row['mtime_ns']
        if args.mode == 'pilot':
            report['shape_weighted_estimate'] = {'module_seconds': sum(
                counts[tuple(row['shape'])] * row['elapsed_seconds'] for row in report['rows']),
                'method': 'sum(shape_module_count * one representative elapsed_seconds)',
                'shape_counts': [{'shape': list(shape), 'modules': count} for shape, count in sorted(counts.items())],
                'initialization_seconds_separate': initialization_seconds,
                'excludes_final_serialization_and_filesystem_sync': True,
                'uncertainty': 'One representative per shape; cold I/O and matrix-dependent SVD convergence can differ.'}
            report['adapter_exported'] = False
        else:
            target_config = copy.deepcopy(configs[0])
            target_config.update(r=64, lora_alpha=64, lora_dropout=0.0,
                                 inference_mode=True, revision=config['base_revision'])
            assert len(weights_out) == 620
            save(output / 'adapter_config.json', target_config)
            save_file(weights_out, output / 'adapter_model.safetensors', metadata={'format': 'pt'})
            with safe_open(output / 'adapter_model.safetensors', framework='pt', device='cpu') as saved:
                assert sorted(saved.keys()) == sorted(weights_out)
                assert all(torch.equal(saved.get_tensor(key), value) for key, value in weights_out.items())
            norm2 = sum(row['dense_frobenius_squared'] for row in report['rows'])
            error2 = sum(row['saved_factor_error_squared'] for row in report['rows'])
            report['global_reconstruction_relative_frobenius'] = math.sqrt(error2 / norm2) if norm2 else 0.0
            report['parameter_count'] = sum(value.numel() for value in weights_out.values())
            assert report['parameter_count'] == 84664320
            report['adapter_exported'] = True
            save(output / 'merge_manifest.json', {'method': 'PEFT0.20 dense-delta per-module TIES + SVD64',
                'selected_final': False, 'primary_unchanged': config['primary_adapter'],
                'config': config, 'source_stats': source_stats, 'report': str((report_dir / 'report.json').relative_to(project)),
                'factor_scaling': 'Real input alpha/r once; output alpha64/r64=1; no additional serving multiplier',
                'approximation': 'Truncated SVD64 of nonlinear dense TIES; see measured residuals',
                'parameter_count': report['parameter_count']})
            save(output / 'EXPORT_COMPLETE.json', {'passed': True, 'report': str(report_dir / 'report.json')})
        report.update(state='finished', finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      measured_pipeline_seconds=time.perf_counter() - started, sources_unchanged=True)
    except BaseException as error:
        report.update(state='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save(report_dir / 'report.json', report)
    print(json.dumps({'state': report['state'], 'mode': args.mode, 'report': str(report_dir / 'report.json'),
                      'estimate': report.get('shape_weighted_estimate')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mode', choices=['self-test', 'pilot', 'export'], default='pilot')
    parser.add_argument('--peft-package', type=Path, help='Optional pinned source location for local tiny checks')
    args = parser.parse_args()
    config = read(args.config)
    torch.set_num_threads(1 if args.mode == 'self-test' else config['cpu_threads'])
    torch.set_num_interop_threads(1)
    package = args.peft_package or args.project / config['peft_package']
    ties = load_ties(package, config['merge_utils_sha256'])
    if args.mode == 'self-test':
        print(json.dumps(self_test(ties)), flush=True)
    else:
        run(args, config, ties)
