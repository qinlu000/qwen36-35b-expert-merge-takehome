#!/usr/bin/env bash
# Run on HPC. Only finalized files from the verified 80 download are copied.
set -euo pipefail
APEX_ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
APEX_MODEL="$APEX_ROOT/artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0"
APEX_PYTHON=${APEX_PYTHON:-/data/user/qinlucao/envs/qwen35-sft-cu130-v1/bin/python}
mkdir -p "$APEX_MODEL"
while true; do
    rsync -rtv --partial --append-verify --size-only \
        --exclude='*.part' --exclude='*.aria2' \
        rsync://10.123.4.80:43873/apex-base/ "$APEX_MODEL/"
    if [[ -f "$APEX_MODEL/download_receipts.json" ]] && \
        "$APEX_PYTHON" -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["complete"])' \
        "$APEX_MODEL/download_receipts.json"; then
        "$APEX_PYTHON" "$APEX_ROOT/scripts/download_base.py" --output "$APEX_MODEL" --workers 2
        break
    fi
    sleep 30
done
