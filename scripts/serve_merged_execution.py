"""Serve the frozen four-expert AVG64 adapter on its own TP2 execution replica."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import struct
import sys

from smoke_base import REVISION, CONTEXT_TOKENS, OUTPUT_TOKENS
from serve_validation_lora import PROJECTIONS, RUNTIME_PROJECTIONS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18000)
    args = parser.parse_args()
    root = args.project.resolve()
    os.umask(0o077)
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', args.port))
    checkpoint = root / 'artifacts/merges/four-experts-avg-v1-20261017/avg-r64'
    config = json.loads((checkpoint / 'adapter_config.json').read_text())
    assert config['r'] == 64 and config['lora_alpha'] == 64
    with (checkpoint / 'adapter_model.safetensors').open('rb') as handle:
        size = struct.unpack('<Q', handle.read(8))[0]
        header = json.loads(handle.read(size))
    tensors = {name: value for name, value in header.items() if name != '__metadata__'}
    assert len(tensors) == 620
    assert {name.split('.')[-3] for name in tensors} == PROJECTIONS
    assert all('.language_model.layers.' in name for name in tensors)
    assert not any('.experts.' in name or '.visual.' in name for name in tensors)
    alias = 'apex-avg64'
    command = [
        sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION),
        '--served-model-name', 'apex-avg64-base', '--host', '0.0.0.0', '--port', str(args.port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2',
        '--distributed-executor-backend', 'mp', '--max-model-len', str(CONTEXT_TOKENS),
        '--max-num-seqs', '20', '--max-num-batched-tokens', '8192',
        '--enable-chunked-prefill', '--gpu-memory-utilization', '0.85', '--enforce-eager',
        '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton',
        '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
        '--reasoning-parser', 'qwen3',
        '--default-chat-template-kwargs', '{"enable_thinking":false,"preserve_thinking":false}',
        '--enable-lora', '--max-lora-rank', '64', '--max-loras', '1', '--max-cpu-loras', '1',
        '--lora-dtype', 'bfloat16', '--lora-target-modules', *RUNTIME_PROJECTIONS,
        '--lora-modules', f'{alias}={checkpoint}', '--no-enable-log-requests',
    ]
    output = root / 'artifacts/eval' / ('merged-execution-service-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'launch.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'hostname': socket.gethostname(),
        'port': args.port, 'command': command, 'model_revision': REVISION,
        'context_tokens': CONTEXT_TOKENS, 'output_cap_per_request': OUTPUT_TOKENS,
        'merged_alias': alias, 'base_alias': 'apex-avg64-base',
        'adapter': {'path': str(checkpoint), 'tensors': len(tensors),
                    'modules': len(tensors) // 2, 'rank': 64, 'alpha': 64},
        'max_num_seqs': 20, 'thinking': False, 'preserve_thinking': False,
        'authentication': 'existing private key file via VLLM_API_KEY; never logged',
        'source_merge': 'four-experts-avg-v1-20261017; primary selected a priori',
        'state': 'starting; formal queue requires native endpoint acceptance',
    }, indent=2) + '\n')
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))


if __name__ == '__main__':
    main()
