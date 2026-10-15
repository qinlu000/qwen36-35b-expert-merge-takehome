#!/usr/bin/env bash
#SBATCH --job-name=apex-base-smoke
#SBATCH --partition=emergency_acd
#SBATCH --qos=formal-user
#SBATCH --account=qinlucao
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=192G
#SBATCH --time=00:30:00
#SBATCH --export=NONE
#SBATCH --chdir=/data/user/qinlucao/projects/apex-takehome
#SBATCH --output=/data/user/qinlucao/projects/apex-takehome/artifacts/preflight/base-smoke-%j.log

set -euo pipefail
umask 077
source /etc/profile.d/modules.sh
module use /data/modulefiles/opensource
module load apptainer/1.4.5

APEX_PROJECT=/data/user/qinlucao/projects/apex-takehome
APEX_PYTHON_ROOT=/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/python
APEX_RUNTIME_CACHE="$APEX_PROJECT/artifacts/cache/base-runtime"
APEX_BUILD_TMP="$APEX_RUNTIME_CACHE/tmp-$SLURM_JOB_ID"
mkdir -p "$APEX_RUNTIME_CACHE"/{triton,vllm,torch,huggingface} "$APEX_BUILD_TMP"
[[ -n "${CUDA_VISIBLE_DEVICES:-}" ]]

exec singularity exec --nv --cleanenv --containall \
    --bind "$APEX_PROJECT:$APEX_PROJECT" \
    --bind "$APEX_PYTHON_ROOT:$APEX_PYTHON_ROOT:ro" \
    --bind "$APEX_BUILD_TMP:/tmp" \
    --env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    --env SLURM_JOB_ID="$SLURM_JOB_ID" \
    --env OMP_NUM_THREADS=4 \
    --env MAX_JOBS=4 \
    --env TMPDIR=/tmp \
    --env XDG_CACHE_HOME="$APEX_RUNTIME_CACHE" \
    --env TRITON_CACHE_DIR="$APEX_RUNTIME_CACHE/triton" \
    --env VLLM_CACHE_ROOT="$APEX_RUNTIME_CACHE/vllm" \
    --env TORCHINDUCTOR_CACHE_DIR="$APEX_RUNTIME_CACHE/torch" \
    --env FLASHINFER_WORKSPACE_BASE="$APEX_RUNTIME_CACHE" \
    --env HF_HOME="$APEX_RUNTIME_CACHE/huggingface" \
    --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
    --env VLLM_NO_USAGE_STATS=1 --env VLLM_WORKER_MULTIPROC_METHOD=spawn \
    /data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif \
    "$APEX_PROJECT/artifacts/envs/base-inference/bin/python" \
    "$APEX_PROJECT/scripts/smoke_base.py" --project="$APEX_PROJECT"
