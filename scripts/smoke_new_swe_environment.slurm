#!/usr/bin/env bash
#SBATCH --job-name=apex-swe-dev-env
#SBATCH --partition=debug
#SBATCH --qos=formal-user
#SBATCH --account=qinlucao
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:25:00
#SBATCH --export=NONE
#SBATCH --chdir=/data/user/qinlucao/projects/apex-takehome
#SBATCH --output=/data/user/qinlucao/projects/apex-takehome/artifacts/preflight/swe-dev-env-%j.log
set -euo pipefail
source /etc/profile.d/modules.sh
module use /data/modulefiles/opensource
module load apptainer/1.4.5
APEX_PROJECT=/data/user/qinlucao/projects/apex-takehome
APEX_ENV="$APEX_PROJECT/artifacts/data/candidates/new_swe_20261016/env_smoke/click_1852"
APEX_TMP=$(mktemp -d "/tmp/apex-swe-dev-${SLURM_JOB_ID}.XXXXXX")
trap 'rm -rf -- "$APEX_TMP"' EXIT
export APPTAINER_TMPDIR="$APEX_TMP"
export APPTAINER_CACHEDIR="$APEX_TMP/cache"
export OMP_NUM_THREADS=4
if [ ! -f "$APEX_ENV/click_1852.sif" ]; then
    apptainer build --disable-cache --mksquashfs-args "-processors 4" "$APEX_ENV/click_1852.sif" "oci:$APEX_ENV/oci"
fi
sha256sum "$APEX_ENV/click_1852.sif" > "$APEX_ENV/image.sha256"
apptainer exec --containall --cleanenv --no-home --pwd /click \
    "$APEX_ENV/click_1852.sif" python3 -c '
import importlib.metadata as md
import json
import os
from pathlib import Path
import subprocess
import sys
expected = "82a83fda1fafd4a43c67755140555bfd5afbd592"
revision = subprocess.check_output(["git", "-C", "/click", "rev-parse", "HEAD"], text=True).strip()
status = subprocess.check_output(["git", "-C", "/click", "status", "--porcelain"], text=True)
packages = {}
for name in ["click", "pytest", "setuptools", "pip"]:
    try:
        packages[name] = md.version(name)
    except md.PackageNotFoundError:
        packages[name] = None
report = dict(passed=revision == expected, expected_commit=expected, actual_commit=revision,
    cwd=os.getcwd(), python=sys.version, packages=packages, git_status=status,
    testbed_exists=Path("/testbed").exists(), testbed_is_symlink=Path("/testbed").is_symlink(),
    testbed_realpath=os.path.realpath("/testbed"),
    scope="Independent dev image initial-state inspection only. No task commands, patches, tests or grader executed; source collector remapping is not proven.")
print(json.dumps(report, indent=2))
assert report["passed"]
' > "$APEX_ENV/initial_state.json"
cat "$APEX_ENV/initial_state.json"
