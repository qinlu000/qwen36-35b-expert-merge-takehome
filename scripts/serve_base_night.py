"""Run the fixed, authenticated TP2 Base endpoint for the overnight evaluation block."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys

from smoke_base import REVISION, CONTEXT_TOKENS, OUTPUT_TOKENS


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project', type=Path, required=True)
args = parser.parse_args()
root = args.project.resolve()
os.umask(0o077)
key_path = root / 'artifacts/private/base_smoke_api_key'
key = key_path.read_text().strip()
assert key
assert len(os.environ['CUDA_VISIBLE_DEVICES'].split(',')) == 2
model = root / 'artifacts/models/Qwen3.6-35B-A3B' / REVISION
out = root / 'artifacts/preflight' / ('base-service-' + os.environ['SLURM_JOB_ID'])
out.mkdir(parents=True, exist_ok=True)
command = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
           '--model', str(model), '--served-model-name', 'apex-qwen',
           '--host', '0.0.0.0', '--port', '18000', '--dtype', 'bfloat16',
           '--tensor-parallel-size', '2', '--distributed-executor-backend', 'mp',
           '--max-model-len', str(CONTEXT_TOKENS), '--max-num-seqs', '4',
           '--max-num-batched-tokens', '8192', '--enable-chunked-prefill',
           '--gpu-memory-utilization', '0.85', '--enforce-eager',
           '--gdn-prefill-backend', 'triton', '--moe-backend', 'triton',
           '--enable-auto-tool-choice', '--tool-call-parser', 'qwen3_coder',
           '--reasoning-parser', 'qwen3', '--no-enable-log-requests']
(out / 'launch.json').write_text(json.dumps({
    'started_at_utc': datetime.now(timezone.utc).isoformat(),
    'job_id': os.environ['SLURM_JOB_ID'], 'hostname': socket.gethostname(),
    'model_revision': REVISION, 'context_tokens': CONTEXT_TOKENS,
    'output_cap_per_request': OUTPUT_TOKENS, 'command': command,
    'authentication': 'VLLM_API_KEY read from private file; never logged',
    'purpose': 'Native acceptance followed by fixed Base evaluation if accepted',
}, indent=2) + '\n')
os.execvpe(sys.executable, command, dict(os.environ, VLLM_API_KEY=key))
