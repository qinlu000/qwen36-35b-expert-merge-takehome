#!/usr/bin/env bash
# After copying the pinned source archives and managed Python to this project.
set -euo pipefail
ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
ART="$ROOT/artifacts"
export UV_CACHE_DIR="$ART/cache/uv"
export UV_PYTHON_INSTALL_DIR="$ART/tools/python"
export UV_PYTHON_BIN_DIR="$ART/tools/python-bin"
export UV_PROJECT_ENVIRONMENT="$ART/envs/harbor"
export LITELLM_LOCAL_MODEL_COST_MAP=True
UV=${UV_BIN:-$(command -v uv)}
mkdir -p "$ART/preflight/swe_tb"
APEX_ROOT="$ROOT" bash "$ROOT/scripts/apply_harbor_startup_patch.sh"
"$UV" sync --project "$ART/benchmarks/harbor" --frozen --no-dev --extra modal \
  --python "$UV_PYTHON_INSTALL_DIR/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12"
"$ART/envs/harbor/bin/harbor" --help > "$ART/preflight/swe_tb/harbor-help.txt"
"$ART/envs/harbor/bin/harbor" run --help > "$ART/preflight/swe_tb/harbor-run-help.txt"
APEX_ROOT="$ROOT" "$ART/envs/harbor/bin/python" - <<'PY'
import importlib.metadata
import json
import os
from pathlib import Path
import tomllib

from harbor.agents.terminus_2.terminus_2 import Terminus2
from harbor.environments.singularity.singularity import SingularityEnvironment

root = Path(os.environ['APEX_ROOT'])
benchmarks = root / 'artifacts/benchmarks'
registry = json.loads((benchmarks / 'harbor/registry.json').read_text())
tb = next(e for e in registry if e['name'] == 'terminal-bench' and e['version'] == '2.0')
swe = (benchmarks / 'swe-bench-pro/v2/hard51_ids.txt').read_text().splitlines()
for directory, source, names in [
    ('terminal-bench-2-registered', benchmarks / 'terminal-bench-2', [t['name'] for t in tb['tasks']]),
    ('swe-hard51', benchmarks / 'swe-bench-pro/v2/tasks', swe),
]:
    subset = benchmarks / directory
    subset.mkdir(exist_ok=True)
    for name in names:
        # Metadata validation only; do not open instruction/solution/tests.
        tomllib.loads((source / name / 'task.toml').read_text())
        link = subset / name
        if not link.exists():
            link.symlink_to(source / name, target_is_directory=True)
report = {
    'versions': {name: importlib.metadata.version(name) for name in ('harbor', 'litellm', 'openai')},
    'swe_tasks': len(swe), 'terminal_tasks': len(tb['tasks']),
    'backend_import': SingularityEnvironment.__name__,
    'resource_capabilities': SingularityEnvironment.resource_capabilities().model_dump(),
    'agent_import': Terminus2.__name__,
    'scope': 'CLI/import/metadata verification only; no container trial or model request executed.'
}
(root / 'artifacts/preflight/swe_tb/hpc_install_check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
PY
