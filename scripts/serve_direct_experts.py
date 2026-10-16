"""Serve frozen direct adapters on an isolated TP2 replica."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import struct
import sys

from smoke_base import REVISION, CONTEXT_TOKENS, OUTPUT_TOKENS


ADAPTERS = {
    'apex-hle250': ('hle-existing2k-sft-r16-726664', 250),
    'apex-asi128': ('asi-expanded-sft-r16-726336', 128),
}

PROJECTIONS = {
    'q_proj', 'k_proj', 'v_proj', 'o_proj',
    'in_proj_qkv', 'in_proj_z', 'in_proj_b', 'in_proj_a', 'out_proj',
    'gate_proj', 'up_proj', 'down_proj',
}
RUNTIME_PROJECTIONS = [
    'qkv_proj', 'o_proj', 'in_proj_qkv', 'in_proj_z', 'in_proj_ba',
    'out_proj', 'gate_up_proj', 'down_proj',
]


def dense_snapshot(root):
    """Validate the completed dense export using small metadata, never tensor payloads."""
    model = root / 'artifacts/merges/four-experts-ties-dense-v1-20261017'
    marker = json.loads((model / 'EXPORT_COMPLETE.json').read_text())
    assert marker['passed'] is True and marker['snapshot_type'] == 'full_hf_model'
    assert marker['source_base_revision'] == REVISION and marker['report'] == 'merge_report.json'
    report = json.loads((model / marker['report']).read_text())
    assert report['state'] == 'finished' and report['targets_modified'] == 310
    assert report['non_targets_verified_bitwise'] == 735 and report['all_tensors'] == 1045
    assert report['shards'] == 26 and report['sources_unchanged'] is True
    assert report['reload_verified'] is True and report['real_weight_svd_calls'] == 0
    assert report['selected_final'] is False
    assert report['tensor_dtype_counts'] == {'torch.bfloat16': 1045}
    base = root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION
    index = json.loads((model / 'model.safetensors.index.json').read_text())
    original = json.loads((base / 'model.safetensors.index.json').read_text())
    assert index['weight_map'] == original['weight_map'] and len(index['weight_map']) == 1045
    previous_merge = json.loads((root / 'artifacts/merges/four-experts-avg-v1-20261017/merge_report.json').read_text())
    targets = {row['module'][len('base_model.model.'):] + '.weight' for row in previous_merge['layers']}
    assert len(targets) == 310 and targets <= set(index['weight_map'])
    shards = set(index['weight_map'].values())
    assert len(shards) == 26 and all((model / name).stat().st_size > 0 for name in shards)
    assert json.loads((model / 'config.json').read_text()) == json.loads((base / 'config.json').read_text())
    for name in ['generation_config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
                 'merges.txt', 'chat_template.jinja', 'preprocessor_config.json', 'video_preprocessor_config.json']:
        assert (model / name).stat().st_size > 0
    return model, {'snapshot_type': 'full_hf_model', 'targets_modified': 310,
        'non_targets_verified_bitwise': 735, 'source_base_revision': REVISION,
        'all_tensors': 1045, 'shards': 26, 'real_weight_svd_calls': 0, 'lora_enabled': False,
        'tensor_dtype_counts': report['tensor_dtype_counts'], 'global_rounding': report['global_rounding']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18002)
    parser.add_argument('--merged', action='store_true')
    parser.add_argument('--profile', choices=['experts', 'merged', 'hle-expert', 'hle-merged', 'controls', 'ties-dense'])
    parser.add_argument('--check-dense-export', action='store_true', help='Only validate completed export metadata; no GPU or model request')
    args = parser.parse_args()
    root = args.project.resolve()
    os.umask(0o077)
    profile = args.profile or ('merged' if args.merged else 'experts')
    dense = profile == 'ties-dense'
    dense_info = {}
    model_path = root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION
    if dense:
        model_path, dense_info = dense_snapshot(root)
    if args.check_dense_export:
        assert dense
        print(json.dumps({'model_path': str(model_path), **dense_info}))
        return
    assert 18000 <= args.port <= 18006
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    assert key
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', args.port))

    adapter_paths = {}
    adapter_inventory = {}
    merged = profile in ('merged', 'hle-merged')
    adapters = ({'apex-avg64': root / 'artifacts/merges/four-experts-avg-v1-20261017/avg-r64'}
                if merged else {alias: root / 'artifacts/runs' / run / 'training' / f'checkpoint-{step}'
                                for alias, (run, step) in ADAPTERS.items()
                                if profile != 'hle-expert' or alias == 'apex-hle250'})
    if profile == 'controls':
        adapters = {
            'apex-mixed883': root / 'artifacts/runs/mixed-existing2k-sft-r16-726666/training/checkpoint-883',
            'apex-avg16': root / 'artifacts/merges/four-experts-avg-v1-20261017/avg-svd-r16',
        }
    if dense:
        adapters = {}
    rank, alpha = (64, 64) if merged else (16, 32)
    for alias, checkpoint in adapters.items():
        config = json.loads((checkpoint / 'adapter_config.json').read_text())
        expected_alpha = 16 if alias == 'apex-avg16' else alpha
        assert config['r'] == rank and config['lora_alpha'] == expected_alpha
        with (checkpoint / 'adapter_model.safetensors').open('rb') as handle:
            size = struct.unpack('<Q', handle.read(8))[0]
            header = json.loads(handle.read(size))
        tensors = {name: value for name, value in header.items() if name != '__metadata__'}
        assert len(tensors) == 620
        assert {name.split('.')[-3] for name in tensors} == PROJECTIONS
        assert all('.language_model.layers.' in name for name in tensors)
        assert not any('.experts.' in name or '.visual.' in name for name in tensors)
        adapter_paths[alias] = str(checkpoint)
        adapter_inventory[alias] = {
            'path': str(checkpoint), 'tensors': len(tensors),
            'modules': len(tensors) // 2, 'rank': rank, 'alpha': expected_alpha,
        }

    command = [
        sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(model_path),
        '--served-model-name', 'apex-ties-dense' if dense else 'apex-direct-base', '--host', '0.0.0.0', '--port', str(args.port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2',
        '--distributed-executor-backend', 'mp', '--max-model-len', str(CONTEXT_TOKENS),
        '--max-num-seqs', '50', '--max-num-batched-tokens', '8192',
        '--enable-chunked-prefill', '--gpu-memory-utilization', '0.85', '--enforce-eager',
        '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton',
        '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
        '--reasoning-parser', 'qwen3',
        '--default-chat-template-kwargs', '{"enable_thinking":false,"preserve_thinking":false}',
        '--no-enable-log-requests',
    ]
    if not dense:
        command += ['--enable-lora', '--max-lora-rank', str(rank), '--max-loras', '1', '--max-cpu-loras', '2',
            '--lora-dtype', 'bfloat16', '--lora-target-modules', *RUNTIME_PROJECTIONS,
            '--lora-modules', *[f'{alias}={path}' for alias, path in adapter_paths.items()],
        ]
    output = root / 'artifacts/eval' / ('direct-expert-service-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'launch.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'hostname': socket.gethostname(),
        'profile': profile,
        'model_path': str(model_path), 'dense_export': dense_info,
        'port': args.port, 'command': command, 'model_revision': REVISION,
        'context_tokens': CONTEXT_TOKENS, 'output_cap_per_request': OUTPUT_TOKENS,
        'base_alias': 'apex-ties-dense' if dense else 'apex-direct-base', 'adapters': adapter_inventory,
        'max_num_seqs': 50, 'max_loras': 0 if dense else 1, 'max_cpu_loras': 0 if dense else 2,
        'max_lora_rank': None if dense else rank, 'lora_enabled': not dense,
        'thinking': False, 'preserve_thinking': False,
        'authentication': 'private Base key file via VLLM_API_KEY; never logged',
        'state': 'starting; accept only after health, aliases, no ignored adapter layers, and generation',
    }, indent=2) + '\n')
    os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))


if __name__ == '__main__':
    main()
