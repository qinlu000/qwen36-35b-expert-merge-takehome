#!/usr/bin/env bash
# Temporary read-only transfer of this public checkpoint from 80 to HPC.
set -euo pipefail
APEX_ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
APEX_MODEL="$APEX_ROOT/artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0"
APEX_STATE="$APEX_ROOT/artifacts/preflight/base-transfer"
mkdir -p "$APEX_STATE"
cat > "$APEX_STATE/rsyncd.conf" <<EOF
pid file = $APEX_STATE/rsyncd.pid
log file = $APEX_STATE/rsyncd.log
use chroot = no
read only = yes
hosts allow = 10.120.48.33
hosts deny = *
[apex-base]
path = $APEX_MODEL
list = no
EOF
exec rsync --daemon --no-detach --config="$APEX_STATE/rsyncd.conf" \
    --address=10.123.4.80 --port=43873
