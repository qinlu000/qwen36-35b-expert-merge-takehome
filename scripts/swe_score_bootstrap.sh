#!/bin/bash
# The Harbor HTTP server is preinstalled from hashed wheels. Task setup remains
# sourced in the public phase; solver limits/network policy stay in the backend.
set -e
export WORKDIR="${1:-/app}"
shift
export HARBOR_STAGING=/staging/env_files
export HARBOR_PYTHON=/opt/harbor-server/bin/python3
export DEBIAN_FRONTEND=noninteractive
export TMUX_TMPDIR="${TMUX_TMPDIR:-/tmp/.harbor-tmux}"
mkdir -p "$WORKDIR" "$TMUX_TMPDIR"
"$HARBOR_PYTHON" -c 'import uvicorn, fastapi'
if ! command -v curl >/dev/null 2>&1; then
    ln -s /opt/apex-swe-runtime/curl /usr/local/bin/curl
fi
if command -v apt-get >/dev/null 2>&1; then
    printf 'Acquire::Retries "0";\nAcquire::http::Timeout "5";\nAcquire::https::Timeout "5";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/98-apex-swe-network
fi
if [ -f "$HARBOR_STAGING/setup.sh" ]; then
    source "$HARBOR_STAGING/setup.sh"
fi
# A URL-safe random token may begin with '-'; argparse needs an equals form.
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
