#!/usr/bin/env bash
# Rebuild the project's inference env from the existing HPC wheelhouse and uv cache.
set -euo pipefail

APEX_PROJECT="${APEX_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}"
APEX_UV="${APEX_UV:-/data/user/qinlucao/bin/uv}"
APEX_PYTHON="${APEX_PYTHON:-/data/user/qinlucao/envs/agent-lightning-trainer-cu130-tmix-v1/bin/python}"
APEX_WHEELHOUSE="${APEX_WHEELHOUSE:-/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/trainer_glibc235}"
APEX_ENV="$APEX_PROJECT/artifacts/envs/base-inference"

if [[ ! -x "$APEX_ENV/bin/python" ]]; then
    "$APEX_UV" venv --python "$APEX_PYTHON" "$APEX_ENV"
fi
# The target platform is the Ubuntu 24.04 Singularity runtime, not the login OS.
"$APEX_UV" pip sync --offline --find-links "$APEX_WHEELHOUSE" \
    --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python" \
    "$APEX_PROJECT/scripts/requirements-base-runtime.lock"
"$APEX_UV" pip check --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python"
mkdir -p "$APEX_PROJECT/artifacts/preflight/base-runtime"
"$APEX_UV" pip freeze --python "$APEX_ENV/bin/python" \
    > "$APEX_PROJECT/artifacts/preflight/base-runtime/requirements.freeze.txt"
printf 'Base inference environment installed: %s\n' "$APEX_ENV"
