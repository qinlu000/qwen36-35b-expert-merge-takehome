#!/usr/bin/env bash
#SBATCH --job-name=apex-ties-pilot
#SBATCH --partition=acd_u
#SBATCH --qos=formal-user
#SBATCH --nice=1000
#SBATCH --account=qinlucao
#SBATCH --exclude=ACD1-59
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --export=NONE
#SBATCH --chdir=/data/user/qinlucao/projects/apex-takehome
#SBATCH --output=/data/user/qinlucao/projects/apex-takehome/artifacts/eval/ties-merge-%j.log
set -euo pipefail
umask 077
source /etc/profile.d/modules.sh
module use /data/modulefiles/opensource
module load apptainer/1.4.5
APEX_PROJECT=/data/user/qinlucao/projects/apex-takehome
APEX_PYTHON_ROOT=/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/python
APEX_TIES_MODE=${1:-pilot}
case "$APEX_TIES_MODE" in pilot|export) ;; *) exit 2 ;; esac
APEX_LOCAL_TMP=$(mktemp -d "/tmp/apex-ties-${SLURM_JOB_ID}.XXXXXX")
trap 'rm -rf -- "$APEX_LOCAL_TMP"' EXIT
singularity exec --nv --cleanenv --containall \
  --bind "$APEX_PROJECT:$APEX_PROJECT" \
  --bind "$APEX_PYTHON_ROOT:$APEX_PYTHON_ROOT:ro" \
  --bind "$APEX_LOCAL_TMP:/tmp" \
  --env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
  --env SLURM_JOB_ID="$SLURM_JOB_ID" \
  --env OMP_NUM_THREADS=8 --env OPENBLAS_NUM_THREADS=8 --env MKL_NUM_THREADS=8 \
  --env TMPDIR=/tmp --env PYTHONUNBUFFERED=1 --env PYTHONDONTWRITEBYTECODE=1 \
  --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  /data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif \
  "$APEX_PROJECT/artifacts/envs/sft/bin/python" "$APEX_PROJECT/scripts/merge_ties_adapters.py" \
  --project="$APEX_PROJECT" --config="$APEX_PROJECT/configs/merge/four_experts_ties_svd64_v1.json" \
  --mode="$APEX_TIES_MODE"
