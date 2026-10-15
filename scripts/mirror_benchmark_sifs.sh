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
    if [[ "$APEX_PROGRESS_STATUS" = complete ]]; then
      # The previous file list may predate the last image's atomic rename.
      sync_sifs
      break
    fi
    # A repair pass may replace a finished report containing earlier failures.
    # Keep mirroring until the source itself reports complete.
    sleep 45
  else
    sleep 30
  fi
done

# Verify the complete transfer against the source's per-SIF receipt.
python3 - "$APEX_ROOT" <<'PY'
from pathlib import Path
import datetime
import hashlib
import json
import sys

root = Path(sys.argv[1])
cache = root / 'artifacts/benchmarks/sif'
report = json.loads((cache / '_prefetch_progress.json').read_text())
manifest = root / 'configs/envs/swe_tb_image_digests.json'
assert report['manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
assert report['status'] == 'complete' and report['failed'] == 0, 'Source download is incomplete'
assert report['completed'] == len(report['results']) == len(json.loads(manifest.read_text()))
for item in report['results']:
    path = cache / item['sif_file']
    assert path.stat().st_size == item['sif_bytes'], path
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            checksum.update(chunk)
    assert checksum.hexdigest() == item['sif_sha256'], path
    alias = cache / item['harbor_cache_name']
    assert alias.is_symlink() and alias.resolve() == path.resolve(), alias
receipt = {'complete': True, 'sha256_verified': report['completed'],
           'manifest_sha256': report['manifest_sha256'],
           'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
output = root / 'artifacts/preflight/swe_tb/sif-hpc-integrity.json'
output.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
PY
