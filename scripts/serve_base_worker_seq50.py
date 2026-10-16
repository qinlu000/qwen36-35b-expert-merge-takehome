"""Independent TP2 Base replica with fifty simultaneous sequences; other inference settings unchanged."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys

from smoke_base import REVISION, CONTEXT_TOKENS, OUTPUT_TOKENS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--worker', choices=['hle', 'asi', 'terminal', 'swe'], required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    os.umask(0o077)
    assert 18001 <= args.port <= 18003
    assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    assert key
    with socket.socket() as probe:
        probe.bind(('0.0.0.0', args.port))
    command = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION),
        '--served-model-name', 'apex-qwen', '--host', '0.0.0.0', '--port', str(args.port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2',
        '--distributed-executor-backend', 'mp', '--max-model-len', str(CONTEXT_TOKENS),
        '--max-num-seqs', '50', '--max-num-batched-tokens', '8192',
        '--enable-chunked-prefill', '--gpu-memory-utilization', '0.85', '--enforce-eager',
        '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton',
        '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
        '--reasoning-parser', 'qwen3', '--no-enable-log-requests']
    output = root / 'artifacts/preflight' / ('base-worker-seq50-' + os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'launch.json').write_text(json.dumps({
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': os.environ['SLURM_JOB_ID'], 'worker': args.worker,
        'hostname': socket.gethostname(), 'port': args.port, 'command': command,
        'model_revision': REVISION, 'context_tokens': CONTEXT_TOKENS,
        'output_cap_per_request': OUTPUT_TOKENS, 'max_num_seqs': 50,
        'port_available_before_launch': True,
        'authentication': 'private file via VLLM_API_KEY, never logged',
        'state': 'starting; wait native health and max_num_seqs50 startup log before handoff',
    }, indent=2) + '\n')
    os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))


if __name__ == '__main__':
    main()
