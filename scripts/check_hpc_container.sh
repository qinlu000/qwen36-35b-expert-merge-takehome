#!/usr/bin/env bash
# Run with sbatch; no benchmark content or model calls are involved.
set -euo pipefail
: "${SLURM_JOB_ID:?Submit this check through Slurm}"
APEX_ROOT=${APEX_ROOT:-/data/user/qinlucao/projects/apex-takehome}
APEX_IMAGE=${APEX_IMAGE:-/data/user/qinlucao/software/containers/hpc-benchmarks_24.09.sif}
APEX_CHECK_DIR="$APEX_ROOT/artifacts/preflight/container-$SLURM_JOB_ID"
mkdir -p "$APEX_CHECK_DIR/workspace"
hostname
singularity --version
export CUDA_VISIBLE_DEVICES=''
singularity exec --cleanenv --containall --no-home --pid --fakeroot \
    --writable-tmpfs --bind "$APEX_CHECK_DIR/workspace:/workspace" \
    "$APEX_IMAGE" /bin/sh -c \
    'id; mkdir -p /apex-container-smoke; printf "container-write-ok\n" > /apex-container-smoke/result; cp /apex-container-smoke/result /workspace/result.txt; cat /workspace/result.txt'
test "$(cat "$APEX_CHECK_DIR/workspace/result.txt")" = 'container-write-ok'
printf 'CONTAINER_SMOKE_PASS\n'
