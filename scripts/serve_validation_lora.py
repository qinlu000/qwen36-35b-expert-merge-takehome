"""Serve Base and four completed expert adapters on a dedicated TP2 replica."""
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
    'apex-val-swe249': ('swe2k-sft-r16-726335', 249),
    'apex-val-asi128': ('asi-expanded-sft-r16-726336', 128),
    'apex-val-hle16': ('hle-existing2k-sft-r16-726664', 16),
    'apex-val-hle250': ('hle-existing2k-sft-r16-726664', 250),
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18000)
    args = parser.parse_args()
    root = args.project.resolve()
    os.umask(0o077)
    assert 18000 <= args.port <= 18003
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    assert key
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', args.port))

    adapter_paths = {}
    adapter_inventory = {}
    for alias, (run, step) in ADAPTERS.items():
        checkpoint = root / 'artifacts/runs' / run / 'training' / f'checkpoint-{step}'
        config = json.loads((checkpoint / 'adapter_config.json').read_text())
        assert config['r'] == 16 and config['lora_alpha'] == 32
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
            'modules': len(tensors) // 2, 'rank': 16, 'alpha': 32,
        }

    command = [
        sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION),
        '--served-model-name', 'apex-val-base', '--host', '0.0.0.0', '--port', str(args.port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2',
        '--distributed-executor-backend', 'mp', '--max-model-len', str(CONTEXT_TOKENS),
        '--max-num-seqs', '20', '--max-num-batched-tokens', '8192',
        '--enable-chunked-prefill', '--gpu-memory-utilization', '0.85', '--enforce-eager',
        '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton',
        '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
        '--reasoning-parser', 'qwen3',
        '--default-chat-template-kwargs', '{"enable_thinking":false,"preserve_thinking":false}',
        '--enable-lora', '--max-lora-rank', '16', '--max-loras', '1', '--max-cpu-loras', '4',
        '--lora-dtype', 'bfloat16', '--lora-target-modules', *RUNTIME_PROJECTIONS,
        '--lora-modules', *[f'{alias}={path}' for alias, path in adapter_paths.items()],
        '--no-enable-log-requests',
    ]
    output = root / 'artifacts/validation' / ('lora-service-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'launch.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'hostname': socket.gethostname(),
        'port': args.port, 'command': command, 'model_revision': REVISION,
        'context_tokens': CONTEXT_TOKENS, 'output_cap_per_request': OUTPUT_TOKENS,
        'base_alias': 'apex-val-base', 'adapters': adapter_inventory,
        'max_num_seqs': 20, 'max_loras': 1, 'max_cpu_loras': 4,
        'thinking': False, 'preserve_thinking': False,
        'authentication': 'private Base key file via VLLM_API_KEY; never logged',
        'state': 'starting; accept only after health, aliases, no ignored adapter layers, and generation',
    }, indent=2) + '\n')
    os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))


if __name__ == '__main__':
    main()
