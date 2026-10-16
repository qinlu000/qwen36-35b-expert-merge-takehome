#!/usr/bin/env python3
"""Fixed true-delta TIES into a new, self-contained HF snapshot; no SVD.

Read/write one Base shard at a time. Never modify or hardlink source weights.
The output keeps the Base architecture/dtypes and is not a PEFT adapter.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gc
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch

import torch
from safetensors import safe_open
from safetensors.torch import save_file

from merge_ties_adapters import (input_inventory, load_ties, read, rss, save,
                                 self_test, true_delta)


def same_bits(left, right):
    return (left.shape == right.shape and left.dtype == right.dtype and
            torch.equal(left.contiguous().reshape(-1).view(torch.uint8),
                        right.contiguous().reshape(-1).view(torch.uint8)))


def norm_squared(value):
    return float(value.double().square().sum())


def relative(numerator, denominator):
    return math.sqrt(numerator / denominator) if denominator else None


def compose(base, delta):
    """Compute in FP32, store the original dtype; measure both rounding steps."""
    original = base.to(device=delta.device, dtype=torch.float32)
    full = original + delta
    assert torch.isfinite(full).all()
    stored = full.to(base.dtype)
    assert torch.isfinite(stored).all()
    cast_error = stored.double() - full.double()
    effective = stored.double() - original.double()
    d2, w2 = norm_squared(delta), norm_squared(full)
    cast2 = norm_squared(cast_error)
    effective_error2 = norm_squared(effective - delta.double())
    addition2 = norm_squared(full.double() - (original.double() + delta.double()))
    unchanged = int((effective == 0).sum())
    stats = {'delta_frobenius_squared': d2, 'composed_weight_frobenius_squared': w2,
        'cast_error_squared': cast2, 'cast_error_frobenius': math.sqrt(cast2),
        'cast_error_relative_to_composed_weight': relative(cast2, w2),
        'cast_error_relative_to_delta': relative(cast2, d2),
        'fp32_addition_roundoff_squared': addition2,
        'effective_delta_frobenius_squared': norm_squared(effective),
        'effective_update_deviation_squared': effective_error2,
        'effective_update_deviation_relative_to_delta': relative(effective_error2, d2),
        'element_count': delta.numel(), 'numerically_unchanged_elements': unchanged,
        'numerically_unchanged_fraction': unchanged / delta.numel()}
    return stored.cpu().contiguous(), stats


def merge_tensor(base, module, readers, configs, ties, config, device):
    cuda = torch.device(device).type == 'cuda'
    if cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    factors = [(reader.get_tensor(module['a_key']).to(device, dtype=torch.float32),
                reader.get_tensor(module['b_key']).to(device, dtype=torch.float32)) for reader in readers]
    deltas = [true_delta(a, b, metadata['lora_alpha'], metadata['r'])
              for metadata, (a, b) in zip(configs, factors)]
    del factors
    dense = config['lambda'] * ties(deltas,
        torch.ones(len(deltas), device=device, dtype=torch.float32),
        density=config['density'], majority_sign_method=config['majority_sign_method'])
    del deltas
    stored, stats = compose(base, dense)
    if cuda:
        torch.cuda.synchronize()
    return stored, {**stats, 'elapsed_seconds': time.perf_counter() - started,
        'torch_allocator_peak_allocated_bytes': torch.cuda.max_memory_allocated() if cuda else None,
        'torch_allocator_peak_reserved_bytes': torch.cuda.max_memory_reserved() if cuda else None}


def write_shard(source, destination, targets, merge_one):
    started = time.perf_counter()
    target_rows, inventory = [], []
    with safe_open(source, framework='pt', device='cpu') as original:
        keys = sorted(original.keys())
        tensors = {key: original.get_tensor(key) for key in keys}
        for key in keys:
            before = tensors[key]
            if key in targets:
                tensors[key], row = merge_one(before, targets[key])
                assert tensors[key].shape == before.shape and tensors[key].dtype == before.dtype
                target_rows.append({'key': key, 'shape': list(before.shape), 'dtype': str(before.dtype), **row})
            inventory.append({'key': key, 'shape': list(before.shape), 'dtype': str(before.dtype),
                              'target': key in targets})
        temporary = destination.with_name(destination.name + '.tmp')
        save_file(tensors, temporary, metadata=original.metadata())
        temporary.replace(destination)
        a, b = source.stat(), destination.stat()
        assert (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino), 'Never hardlink a weight shard'
        assert not destination.is_symlink()
        with safe_open(destination, framework='pt', device='cpu') as reloaded:
            assert sorted(reloaded.keys()) == keys
            for key in keys:
                saved = reloaded.get_tensor(key)
                expected = tensors[key] if key in targets else original.get_tensor(key)
                assert same_bits(saved, expected), key
        logical_bytes = sum(value.numel() * value.element_size() for value in tensors.values())
    return {'shard': source.name, 'elapsed_seconds': time.perf_counter() - started,
        'all_tensors': len(keys), 'targets_modified': len(target_rows),
        'non_targets_verified_bitwise': len(keys) - len(target_rows),
        'reload_verified': True, 'tensor_bytes': logical_bytes,
        'cpu_rss_after': rss(), 'targets': target_rows, 'inventory': inventory}


def dense_self_test(ties):
    # Tiny Base shards, including NaN and signed zero in a non-target tensor.
    # This exercises the same writer/reloader and BF16 composition as export.
    a = [torch.tensor([row]) * .001 for row in [[1., 3.], [2., -1.], [1., -3.], [3., 1.]]]
    b = [torch.tensor(row).reshape(2, 1) for row in [[2., 5.], [1., -3.], [-2., 5.], [1., 2.]]]
    class Reader:
        def __init__(self, index):
            self.index = index
        def get_tensor(self, key):
            return a[self.index] if key.endswith('A') else b[self.index]
    readers = [Reader(i) for i in range(4)]
    configs = [{'r': 1, 'lora_alpha': 2} for _ in readers]
    config = {'density': .5, 'majority_sign_method': 'total', 'lambda': 1}
    target = {'a_key': 'tiny.A', 'b_key': 'tiny.B'}
    base = torch.tensor([[.75, 2.25], [-1.5, 8.]], dtype=torch.bfloat16)
    expected_delta = torch.tensor([[.006, .012], [.012, .018]])
    expected = (base.float() + expected_delta).to(base.dtype)
    fixtures = [
        {'target.one': base, 'vision.unchanged': torch.tensor([float('nan'), -0.], dtype=torch.float32)},
        {'target.two': base, 'embedding.unchanged': torch.arange(6, dtype=torch.bfloat16),
         'router.unchanged': torch.tensor(-0., dtype=torch.float32)}]
    with patch.object(torch.linalg, 'svd', side_effect=AssertionError('Dense merge must not call SVD')) as svd:
        with tempfile.TemporaryDirectory(prefix='apex-ties-dense-tiny-') as directory:
            folder = Path(directory)
            for i, fixture in enumerate(fixtures):
                source, output = folder / ('source%d.safetensors' % i), folder / ('output%d.safetensors' % i)
                save_file(fixture, source, metadata={'format': 'pt'})
                key = 'target.one' if i == 0 else 'target.two'
                result = write_shard(source, output, {key: target},
                    lambda value, module: merge_tensor(value, module, readers, configs, ties, config, 'cpu'))
                assert result['targets_modified'] == 1 and result['reload_verified']
                with safe_open(output, framework='pt', device='cpu') as saved:
                    assert same_bits(saved.get_tensor(key), expected)
                row = result['targets'][0]
                assert row['cast_error_squared'] > 0 and row['effective_update_deviation_squared'] > 0
                assert row['numerically_unchanged_fraction'] > 0
            svd.assert_not_called()
    return {'passed': True, 'device': 'cpu', 'real_adapter_tensor_reads': 0,
        'tiny_shards': 2, 'tiny_all_tensors': 5, 'tiny_targets': 2, 'tiny_non_targets_bitwise': 3,
        'svd_calls': 0, 'tests': ['same_true_delta_ties_writer_without_svd',
            'bf16_rounding_and_effective_update_measured', 'single_shard_reopen_shape_dtype_bits',
            'non_target_nan_signed_zero_preserved', 'new_files_not_hardlinks']}


def source_stats(paths, project):
    return [{'path': str(path.relative_to(project)), 'bytes': path.stat().st_size,
             'mtime_ns': path.stat().st_mtime_ns} for path in paths]


def run(args, config, ties):
    assert os.environ.get('SLURM_JOB_ID'), 'Real-weight merging requires an allocated Slurm job'
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1
    assert 'H100' in torch.cuda.get_device_name(0)
    assert config['density'] == .2 and config['majority_sign_method'] == 'total'
    assert config['weights'] == [1, 1, 1, 1] and config['lambda'] == 1
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    project = args.project.resolve()
    base, output = project / config['base_path'], project / config['output_root']
    assert base.name == config['base_revision']
    configs, readers, modules, _, adapter_stats = input_inventory(project, config)
    targets = {module['a_key'].removeprefix('base_model.model.').removesuffix('.lora_A.weight') + '.weight': module
               for module in modules}
    index = read(base / 'model.safetensors.index.json')
    weight_map = index['weight_map']
    shards = sorted(set(weight_map.values()))
    assert len(targets) == 310 and targets.keys() <= weight_map.keys()
    assert len(weight_map) == config['expected_all_tensors'] == 1045
    assert len(shards) == config['expected_shards'] == 26
    assert set(shards) == {path.name for path in base.glob('*.safetensors')}
    assert set(shards) == {weight_map[key] for key in targets}
    assets = [base / name for name in config['copy_assets']]
    assert all(path.is_file() for path in assets)
    source_paths = [base / name for name in shards] + assets
    for row in config['inputs']:
        source_paths.extend(project / row['adapter'] / name for name in ['adapter_config.json', 'adapter_model.safetensors'])
    before = source_stats(source_paths, project)
    assert shutil.disk_usage(output.parent).free > sum((base / name).stat().st_size for name in shards)
    output.mkdir(exist_ok=False)
    report = {'state': 'running', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'config': config, 'snapshot_type': 'full_hf_model',
        'source_base_revision': config['base_revision'], 'source_stats': before,
        'adapter_input_stats': adapter_stats, 'torch_version': torch.__version__, 'cuda_version': torch.version.cuda,
        'gpu_name': torch.cuda.get_device_name(0), 'real_weight_svd_calls': 0,
        'svd_in_merging': False, 'selected_final': False, 'primary_avg64_modified': False,
        'model_requests': 0, 'training_or_loss_evaluations': 0, 'shard_reports': []}
    started = time.perf_counter()
    try:
        report['dense_tiny_checks'] = dense_self_test(ties)  # no SVD, including tiny checks
        for source in assets:
            destination = output / source.name
            shutil.copy2(source, destination, follow_symlinks=True)
            assert not destination.is_symlink() and source.read_bytes() == destination.read_bytes()
        report['copied_assets'] = [path.name for path in assets]
        for shard in shards:
            local_targets = {key: targets[key] for key in targets if weight_map[key] == shard}
            expected_keys = {key for key in weight_map if weight_map[key] == shard}
            def merge_one(value, module):
                assert list(value.shape) == module['shape'] and value.dtype == torch.bfloat16
                return merge_tensor(value, module, readers, configs, ties, config, 'cuda')
            row = write_shard(base / shard, output / shard, local_targets, merge_one)
            assert {entry['key'] for entry in row['inventory']} == expected_keys
            report['shard_reports'].append(row)
            save(output / 'merge_report.json', report)
            print(json.dumps({'shard': shard, 'targets': row['targets_modified'],
                'all_tensors': row['all_tensors'], 'seconds': row['elapsed_seconds']}), flush=True)
            gc.collect()
        assert source_stats(source_paths, project) == before
        assert read(output / 'model.safetensors.index.json') == index
        entries = [entry for row in report['shard_reports'] for entry in row['inventory']]
        assert Counter(entry['key'] for entry in entries) == Counter(weight_map.keys())
        report.update(targets_modified=sum(row['targets_modified'] for row in report['shard_reports']),
            non_targets_verified_bitwise=sum(row['non_targets_verified_bitwise'] for row in report['shard_reports']),
            all_tensors=len(entries), shards=len(report['shard_reports']))
        assert report['targets_modified'] == 310 and report['non_targets_verified_bitwise'] == 735
        assert sum(row['tensor_bytes'] for row in report['shard_reports']) == index['metadata']['total_size']
        rows = [target for row in report['shard_reports'] for target in row['targets']]
        sums = {field: sum(row[field] for row in rows) for field in ['delta_frobenius_squared',
            'composed_weight_frobenius_squared', 'cast_error_squared', 'fp32_addition_roundoff_squared',
            'effective_delta_frobenius_squared', 'effective_update_deviation_squared']}
        report['global_rounding'] = {**sums,
            'cast_error_frobenius': math.sqrt(sums['cast_error_squared']),
            'cast_error_relative_to_composed_weight': relative(sums['cast_error_squared'], sums['composed_weight_frobenius_squared']),
            'cast_error_relative_to_delta': relative(sums['cast_error_squared'], sums['delta_frobenius_squared']),
            'effective_update_deviation_relative_to_delta': relative(sums['effective_update_deviation_squared'], sums['delta_frobenius_squared']),
            'target_elements': sum(row['element_count'] for row in rows),
            'numerically_unchanged_elements': sum(row['numerically_unchanged_elements'] for row in rows),
            'fully_numerically_unchanged_target_tensors': sum(row['numerically_unchanged_fraction'] == 1 for row in rows)}
        assert report['global_rounding']['target_elements'] == 1409024000
        report['tensor_dtype_counts'] = dict(Counter(entry['dtype'] for entry in entries))
        report['target_count_definition'] = '310 tensors processed/written; BF16 rounding may leave some values unchanged'
        report['resource_peaks'] = {
            'torch_allocator_peak_allocated_bytes': max(row['torch_allocator_peak_allocated_bytes'] for row in rows),
            'torch_allocator_peak_reserved_bytes': max(row['torch_allocator_peak_reserved_bytes'] for row in rows),
            'cpu_process_lifetime_high_water_bytes': max(row['cpu_rss_after']['process_lifetime_high_water_bytes'] for row in report['shard_reports'])}
        report.update(state='finished', finished_at_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.perf_counter() - started, sources_unchanged=True, reload_verified=True)
        save(output / 'merge_manifest.json', {'snapshot_type': 'full_hf_model', 'method': config['method'],
            'source_base_revision': config['base_revision'], 'selected_final': False,
            'primary_unchanged': config['primary_adapter'], 'config': config,
            'real_weight_svd_calls': 0, 'report': 'merge_report.json',
            'precision': 'FP32 true deltas and sum; original BF16 target storage; rounding reported separately',
            'representation_difference': 'Dense full snapshot vs primary AVG64 adapter; no rank truncation or LoRA serving scale'})
        save(output / 'merge_report.json', report)
        # Only this last file permits serving; partial snapshots never qualify.
        save(output / 'EXPORT_COMPLETE.json', {'passed': True, 'snapshot_type': 'full_hf_model',
            'source_base_revision': config['base_revision'], 'report': 'merge_report.json',
            'targets_modified': 310, 'non_targets_verified_bitwise': 735,
            'all_tensors': 1045, 'shards': 26, 'reload_verified': True,
            'sources_unchanged': True, 'real_weight_svd_calls': 0, 'selected_final': False})
    except BaseException as error:
        report.update(state='failed', error_type=type(error).__name__, error=str(error))
        save(output / 'merge_report.json', report)
        raise
    print(json.dumps({'state': report['state'], 'output': str(output),
        'global_rounding': report['global_rounding']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--peft-package', type=Path)
    args = parser.parse_args()
    config = read(args.config)
    torch.set_num_threads(1 if args.self_test else config['cpu_threads'])
    torch.set_num_interop_threads(1)
    ties = load_ties(args.peft_package or args.project / config['peft_package'], config['merge_utils_sha256'])
    with torch.inference_mode():
        if args.self_test:
            print(json.dumps({'shared_tiny_checks': self_test(ties), 'dense_checks': dense_self_test(ties)}), flush=True)
        else:
            run(args, config, ties)
