#!/bin/bash
# Cached private server and original setup; no task /usr/local/bin overlays.
set -e
export WORKDIR="${1:-/app}"
shift
export HARBOR_STAGING=/staging/env_files
export HARBOR_PYTHON=/opt/harbor-server/bin/python3
export DEBIAN_FRONTEND=noninteractive
export TMUX_TMPDIR="${TMUX_TMPDIR:-/tmp/.harbor-tmux}"
mkdir -p "$WORKDIR" "$TMUX_TMPDIR"
"$HARBOR_PYTHON" -c 'import uvicorn, fastapi'
if command -v apt-get >/dev/null 2>&1; then
    printf 'Acquire::Retries "0";\nAcquire::http::Timeout "5";\nAcquire::https::Timeout "5";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98-apex-swe-network
fi
if [ -f "$HARBOR_STAGING/setup.sh" ]; then
    source "$HARBOR_STAGING/setup.sh"
fi
server_args=()
while [ "$#" -gt 0 ]; do
    if [ "$1" = "--instance-token" ]; then
        server_args+=("--instance-token=$2")
        shift 2
    else
        server_args+=("$1")
        shift
    fi
done
exec "$HARBOR_PYTHON" "${server_args[@]}"
