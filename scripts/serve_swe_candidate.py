"""Serve one candidate SWE LoRA adapter on a dedicated TP2 replica."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import struct
import sys

REVISION = '995ad96eacd98c81ed38be0c5b274b04031597b0'
PROJECTIONS = {'q_proj', 'k_proj', 'v_proj', 'o_proj', 'in_proj_qkv', 'in_proj_z',
               'in_proj_b', 'in_proj_a', 'out_proj', 'gate_proj', 'up_proj', 'down_proj'}
RUNTIME_PROJECTIONS = ['qkv_proj', 'o_proj', 'in_proj_qkv', 'in_proj_z', 'in_proj_ba',
                       'out_proj', 'gate_up_proj', 'down_proj']


def checkpoint_inventory(checkpoint):
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
    return {'path': str(checkpoint), 'tensors': len(tensors), 'modules': len(tensors) // 2,
            'rank': 16, 'alpha': 32}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--alias', required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    root, checkpoint = args.project.resolve(), args.checkpoint.resolve()
    assert 18004 <= args.port <= 18010
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    assert key
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', args.port))
    inventory = checkpoint_inventory(checkpoint)
    command = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION),
        '--served-model-name', 'apex-val-base', '--host', '0.0.0.0', '--port', str(args.port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2', '--distributed-executor-backend', 'mp',
        '--max-model-len', '65536', '--max-num-seqs', '20', '--max-num-batched-tokens', '8192',
        '--enable-chunked-prefill', '--gpu-memory-utilization', '0.85', '--enforce-eager',
        '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton', '--enable-auto-tool-choice',
        '--tool-call-parser', 'qwen3_coder', '--reasoning-parser', 'qwen3',
        '--default-chat-template-kwargs', '{"enable_thinking":false,"preserve_thinking":false}',
        '--enable-lora', '--max-lora-rank', '16', '--max-loras', '1', '--max-cpu-loras', '1',
        '--lora-dtype', 'bfloat16', '--lora-target-modules', *RUNTIME_PROJECTIONS,
        '--lora-modules', f'{args.alias}={checkpoint}', '--no-enable-log-requests']
    output = root / 'artifacts/validation' / ('swe-candidate-service-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'launch.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'job_id': os.environ['SLURM_JOB_ID'],
        'hostname': socket.gethostname(), 'port': args.port, 'alias': args.alias,
        'checkpoint': str(checkpoint), 'command': command, 'model_revision': REVISION,
        'context_tokens': 65536, 'output_cap_per_request': 8192, 'adapter': inventory,
        'thinking': False, 'preserve_thinking': False, 'state': 'starting'}, indent=2) + '\n')
    os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))


if __name__ == '__main__':
    main()
