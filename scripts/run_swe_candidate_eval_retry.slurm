#!/usr/bin/env bash
#SBATCH --job-name=apex-swe-candidate-retry
#SBATCH --partition=acd_u
#SBATCH --qos=formal-user
#SBATCH --account=qinlucao
#SBATCH --nice=1000
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --gres=gpu:1
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --export=NONE
#SBATCH --chdir=/data/user/qinlucao/projects/apex-takehome
#SBATCH --output=/data/user/qinlucao/projects/apex-takehome/artifacts/eval/swe_lr2e5_max32k_retry_20261017/controller-%j.log
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ROOT=/data/user/qinlucao/projects/apex-takehome
EVAL_DIR="$ROOT/artifacts/eval/swe_lr2e5_max32k_retry_20261017"
mkdir -p "$EVAL_DIR"
ALLOC_CPUS=$(python3 - <<'PY'
value = next(line.split(':', 1)[1].strip() for line in open('/proc/self/status')
             if line.startswith('Cpus_allowed_list:'))
cpus = []
for part in value.split(','):
    bounds = [int(x) for x in part.split('-')]
    cpus.extend(range(bounds[0], bounds[-1] + 1) if len(bounds) == 2 else bounds)
print(','.join(str(x) for x in cpus[:10]))
PY
)
python3 - "$ROOT/configs/eval/swe_lr2e5_max32k_retry_hpc_20261017.json" "$EVAL_DIR/runtime_config.json" "$ALLOC_CPUS" "$SLURM_JOB_ID" <<'PY'
import json, sys
source, target, cpus, job = sys.argv[1:]
config = json.load(open(source)); config['cpu_ids'] = [int(x) for x in cpus.split(',')]
config['runtime_cpu_job'] = job
json.dump(config, open(target, 'w'), indent=2)
json.dump({'ready': True, 'cpu_consumers_finished': True, 'cpu_ids': config['cpu_ids'],
           'job_id': job, 'service_job': '728866', 'scope': 'Candidate-only allocated CPU lease'},
          open('/data/user/qinlucao/projects/apex-takehome/artifacts/eval/swe_lr2e5_max32k_retry_20261017/cpu_release.json', 'w'))
PY
exec "$ROOT/artifacts/envs/harbor/bin/python" "$ROOT/scripts/run_swe_candidate_benchmark.py" \
  --config="$EVAL_DIR/runtime_config.json"
