#!/usr/bin/env bash
# Project-only training environment; donor environments remain unchanged.
set -euo pipefail
APEX_PROJECT="${APEX_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}"
APEX_UV=/data/user/qinlucao/bin/uv
APEX_DONOR=/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/trainer_glibc235
APEX_PYTHON=/data/user/qinlucao/envs/agent-lightning-trainer-cu130-tmix-v1/bin/python
APEX_ENV="$APEX_PROJECT/artifacts/envs/sft"
APEX_SOURCE="$APEX_PROJECT/artifacts/source/ms-swift-a01a3ae004e0b1071814a3d357666184211ed178"
APEX_WHEELS="$APEX_PROJECT/artifacts/wheels/sft"
if [[ ! -x "$APEX_ENV/bin/python" ]]; then
    "$APEX_UV" venv --python "$APEX_PYTHON" "$APEX_ENV"
fi
"$APEX_UV" pip install --offline --find-links "$APEX_DONOR" \
    --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python" \
    'torch==2.11.0+cu130' 'transformers==5.15.1' 'peft==0.20.0' \
    'accelerate==1.14.0' 'torchvision==0.26.0+cu130' 'qwen-vl-utils==0.0.14'
if [[ "${1:-all}" == core ]]; then exit 0; fi
export DS_BUILD_OPS=0
"$APEX_UV" pip install --offline --find-links "$APEX_DONOR" --find-links "$APEX_WHEELS" \
    --find-links /data/user/qinlucao/datasets/training_mix_sft_wheelhouse_v1 \
    --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python" \
    --constraint "$APEX_PROJECT/configs/envs/sft_constraints.txt" \
    -r "$APEX_SOURCE/requirements/framework.txt" \
    'flash-linear-attention==0.5.2' 'deepspeed==0.19.6' decord
"$APEX_UV" pip install --offline --no-deps --no-build-isolation \
    --python "$APEX_ENV/bin/python" "$APEX_SOURCE"
# FLA 0.5.2 rejects Triton 3.6 on Hopper due to incorrect backward results.
# Its supported 3.7.1 compiler overrides Torch 2.11's distribution metadata pin.
"$APEX_UV" pip install --offline --no-deps --find-links "$APEX_WHEELS" \
    --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python" 'triton==3.7.1'
# Official Qwen3.5-MoE fused linear CE avoids full sequence-by-vocabulary buffers.
"$APEX_UV" pip install --offline --no-deps --python "$APEX_ENV/bin/python" \
    "$APEX_PROJECT/artifacts/wheelhouse/liger_kernel-0.8.2-py3-none-any.whl"
mkdir -p "$APEX_PROJECT/artifacts/preflight/sft-runtime"
APEX_CHECK="$APEX_PROJECT/artifacts/preflight/sft-runtime/dependency_check.txt"
# Preserve metadata warnings (Torch's older compiler pin and decord's stale ABI tag).
"$APEX_UV" pip check --python-platform x86_64-manylinux_2_35 --python "$APEX_ENV/bin/python" > "$APEX_CHECK" 2>&1 || true
"$APEX_UV" pip freeze --python "$APEX_ENV/bin/python" \
    > "$APEX_PROJECT/artifacts/preflight/sft-runtime/requirements.freeze.txt"
