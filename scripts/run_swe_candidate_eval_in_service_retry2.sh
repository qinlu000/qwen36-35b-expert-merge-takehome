#!/usr/bin/env bash
set -euo pipefail
ROOT=/data/user/qinlucao/projects/apex-takehome
EVAL_DIR="$ROOT/artifacts/eval/swe_lr2e5_max32k_retry2_20261017"
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
python3 - "$ROOT/configs/eval/swe_lr2e5_max32k_retry2_hpc_20261017.json" "$EVAL_DIR/runtime_config.json" "$ALLOC_CPUS" "$SLURM_JOB_ID" "$EVAL_DIR/cpu_release.json" <<'PY'
import json, sys
source, target, cpus, job, marker = sys.argv[1:]
config = json.load(open(source)); config['cpu_ids'] = [int(x) for x in cpus.split(',')]
config['runtime_cpu_job'] = job
json.dump(config, open(target, 'w'), indent=2)
json.dump({'ready': True, 'cpu_consumers_finished': True, 'cpu_ids': config['cpu_ids'],
           'job_id': job, 'service_job': '728866', 'scope': 'Overlapped CPU step inside candidate service job'},
          open(marker, 'w'))
PY
exec "$ROOT/artifacts/envs/harbor/bin/python" "$ROOT/scripts/run_swe_candidate_benchmark.py" \
  --config="$EVAL_DIR/runtime_config.json"
