#!/usr/bin/env bash
# Run on HPC while the 80-host prefetch is active. Only the SIF module is exposed.
set -euo pipefail
APEX_ROOT=${APEX_ROOT:-/data/user/qinlucao/projects/apex-takehome}
APEX_SIF_DIR="$APEX_ROOT/artifacts/benchmarks/sif"
mkdir -p "$APEX_SIF_DIR"
sync_sifs() {
  rsync -rlt --partial --append-verify --contimeout=15 --timeout=180 --no-motd \
    --exclude='*.partial.sif' --exclude='*.partial.json' \
    --include='*.sif' --include='_prefetch_progress.json' --exclude='*' \
    rsync://10.123.4.80:43874/benchmark_sif/ "$APEX_SIF_DIR/"
}
while true; do
  if sync_sifs; then
    APEX_PROGRESS_STATUS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$APEX_SIF_DIR/_prefetch_progress.json")
    printf 'SIF mirror sync succeeded; source status=%s\n' "$APEX_PROGRESS_STATUS"
    if [[ "$APEX_PROGRESS_STATUS" = complete || "$APEX_PROGRESS_STATUS" = finished ]]; then
      # The previous file list may predate the last image's atomic rename.
      sync_sifs
      break
    fi
    sleep 45
  else
    sleep 30
  fi
done
