#!/bin/bash
export WORKDIR="${1:-/app}"; shift
export HARBOR_STAGING=/staging/env_files
export HARBOR_PYTHON=/opt/harbor-server/bin/python3
export DEBIAN_FRONTEND=noninteractive
export TMUX_TMPDIR="${TMUX_TMPDIR:-/tmp/.harbor-tmux}"
mkdir -p "$WORKDIR" "$TMUX_TMPDIR"
for f in "$HOME/.bashrc" "$HOME/.bash_profile"; do
 [ -f "$f" ] || touch "$f"
 grep -q TMUX_TMPDIR "$f" 2>/dev/null || echo "alias tmux='tmux -S $TMUX_TMPDIR/default'" >> "$f"
done
if [ -f "$HARBOR_STAGING/setup.sh" ]; then source "$HARBOR_STAGING/setup.sh"; fi
args=()
while [ "$#" -gt 0 ]; do
 if [ "$1" = --instance-token ]; then args+=("--instance-token=$2"); shift 2
 else args+=("$1"); shift; fi
done
exec "$HARBOR_PYTHON" "${args[@]}"
