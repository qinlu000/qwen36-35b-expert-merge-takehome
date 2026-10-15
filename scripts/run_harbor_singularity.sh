#!/usr/bin/env bash
# Project-only runtime paths, shared by the 80 host and HPC.
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x /data/apps/apptainer/1.4.5/bin/singularity ]; then
    source /etc/profile.d/modules.sh
    module use /data/modulefiles/opensource
    module load apptainer/1.4.5
else
    export PATH="$task_root/artifacts/tools/apptainer-1.4.5/rootfs/usr/bin:$PATH"
    # Official v1.4.5 switch: use root-map + fakeroot without uidmap helpers.
    export APPTAINER_IGNORE_SUBUID=1
fi
# Add fakeroot after module loading; Apptainer --fakeroot discovers it here.
export PATH="$task_root/artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin:$PATH"
export PYTHONPATH="$task_root/scripts${PYTHONPATH:+:$PYTHONPATH}"
export LITELLM_LOCAL_MODEL_COST_MAP=True
export NO_PROXY="localhost,127.0.0.1${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY"
exec "$task_root/artifacts/envs/harbor/bin/harbor" run \
    --env apex_singularity:ApexSingularityEnvironment "$@"
