#!/usr/bin/env bash
set -euo pipefail
umask 077
APEX_PROJECT=$(cd "$(dirname "$0")/.." && pwd)
cd "$APEX_PROJECT"
APEX_PYTHON="$APEX_PROJECT/artifacts/envs/hle/bin/python"
"$APEX_PYTHON" -u scripts/probe_base_full_decode.py \
  --key-file artifacts/private/base_smoke_api_key \
  --output artifacts/preflight/base-night-724196
"$APEX_PYTHON" -u scripts/run_hle_v2.py --mode formal \
  --key-file artifacts/private/base_smoke_api_key \
  --output artifacts/runs/base_hle_v2_724196
