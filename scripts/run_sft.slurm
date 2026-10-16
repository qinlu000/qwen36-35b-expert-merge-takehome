#!/usr/bin/env bash
#SBATCH --job-name=apex-expert-sft
#SBATCH --partition=emergency_acd
#SBATCH --qos=formal-user
#SBATCH --account=qinlucao
# ACD1-59 failed before Python: squashfuse_ll could not load libfuse3.so.3.
#SBATCH --exclude=ACD1-59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --gres=gpu:4
#SBATCH --mem=256G
#SBATCH --time=08:00:00
#SBATCH --export=NONE
#SBATCH --chdir=/data/user/qinlucao/projects/apex-takehome
#SBATCH --output=/data/user/qinlucao/projects/apex-takehome/artifacts/runs/expert-sft-%j.log
set -euo pipefail
source /etc/profile.d/modules.sh
module use /data/modulefiles/opensource
module load apptainer/1.4.5
APEX_PROJECT=/data/user/qinlucao/projects/apex-takehome
APEX_PYTHON_ROOT=/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/python
APEX_LOCAL_TMP=$(mktemp -d "/tmp/apex-sft-${SLURM_JOB_ID}.XXXXXX")
trap 'rm -rf -- "$APEX_LOCAL_TMP"' EXIT
mkdir -p "$APEX_LOCAL_TMP"/cache/{triton,torch,extensions,huggingface,datasets,modelscope}
singularity exec --nv --cleanenv --containall \
    --bind "$APEX_PROJECT:$APEX_PROJECT" --bind "$APEX_PYTHON_ROOT:$APEX_PYTHON_ROOT:ro" \
    --bind "$APEX_LOCAL_TMP:/tmp" \
    --env APEX_ASSIGNED_GPUS="$CUDA_VISIBLE_DEVICES" --env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
    --env SLURM_JOB_ID="$SLURM_JOB_ID" --env OMP_NUM_THREADS=4 --env MAX_JOBS=4 \
    --env TMPDIR=/tmp --env XDG_CACHE_HOME=/tmp/cache \
    --env TRITON_CACHE_DIR=/tmp/cache/triton --env TORCHINDUCTOR_CACHE_DIR=/tmp/cache/torch \
    --env TORCH_EXTENSIONS_DIR=/tmp/cache/extensions --env HF_HOME=/tmp/cache/huggingface \
    --env HF_DATASETS_CACHE=/tmp/cache/datasets --env MODELSCOPE_CACHE=/tmp/cache/modelscope \
    --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 --env USE_HF=1 \
    --env TOKENIZERS_PARALLELISM=false --env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif \
    "$APEX_PROJECT/artifacts/envs/sft/bin/python" "$APEX_PROJECT/scripts/run_sft.py" \
    --project="$APEX_PROJECT" "$@"
