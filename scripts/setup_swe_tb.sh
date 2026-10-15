#!/usr/bin/env bash
# Run on the Linux evaluation host; no model calls, benchmark trials, or sudo.
set -euo pipefail
ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
ART="$ROOT/artifacts"
export UV_CACHE_DIR="$ART/cache/uv"
export UV_PYTHON_INSTALL_DIR="$ART/tools/python"
export UV_PYTHON_BIN_DIR="$ART/tools/python-bin"
export MSWEA_GLOBAL_CONFIG_DIR="$ART/preflight/swe_tb/mini-config"
export LITELLM_LOCAL_MODEL_COST_MAP=True
UV="$ART/tools/uv/uv"
HARBOR_REV=f527f8e447038fd242d08ecfa8aaa8029100da97
SWE_REV=66f92766bba642462d4bbe5479e83f91f9211862
TB_REV=69671fbaac6d67a7ef0dfec016cc38a64ef7a77c
mkdir -p "$ART/tools/uv" "$ART/envs" "$ART/benchmarks" "$ART/preflight/swe_tb"
if [[ ! -x "$UV" ]]; then
  curl -fsSL --retry 3 https://github.com/astral-sh/uv/releases/download/0.8.22/uv-x86_64-unknown-linux-gnu.tar.gz -o "$ART/tools/uv/uv-0.8.22.tar.gz"
  tar -xzf "$ART/tools/uv/uv-0.8.22.tar.gz" --strip-components=1 -C "$ART/tools/uv"
fi
if [[ ! -x "$UV_PYTHON_INSTALL_DIR/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12" ]]; then
  "$UV" python install 3.12.11
fi

checkout() {
  local name=$1 url=$2 revision=$3
  local dest="$ART/benchmarks/$name"
  if [[ ! -d "$dest/.git" ]]; then
    git init -q "$dest"
    git -C "$dest" remote add origin "$url"
  fi
  # Restore only our known native patch before the pinned checkout. Other
  # tracked changes still fail the clean checks; dependency lock stays upstream.
  if [[ "$name" == harbor ]] && ! git -C "$dest" diff --quiet; then
    APEX_ROOT="$ROOT" bash "$ROOT/scripts/apply_harbor_startup_patch.sh" reverse-native
  fi
  git -C "$dest" diff --quiet
  git -C "$dest" diff --cached --quiet
  if ! git -C "$dest" cat-file -e "$revision^{commit}" 2>/dev/null; then
    git -C "$dest" fetch --depth=1 origin "$revision"
  fi
  git -C "$dest" checkout --detach "$revision"
}
checkout harbor https://github.com/harbor-framework/harbor.git "$HARBOR_REV"
APEX_ROOT="$ROOT" bash "$ROOT/scripts/apply_harbor_startup_patch.sh"
checkout swe-bench-pro https://github.com/scaleapi/SWE-bench_Pro-os.git "$SWE_REV"
checkout terminal-bench-2 https://github.com/laude-institute/terminal-bench-2.git "$TB_REV"

# Honor the official Harbor uv.lock rather than resolving its minimum versions anew.
UV_PROJECT_ENVIRONMENT="$ART/envs/harbor" "$UV" sync --project "$ART/benchmarks/harbor" --frozen --no-dev --extra modal --python 3.12.11
"$UV" venv --python 3.12.11 --allow-existing "$ART/envs/mini-swe"
if [[ -f "$ROOT/configs/envs/mini-swe-py312.txt" ]]; then
  "$UV" pip sync --python "$ART/envs/mini-swe/bin/python" "$ROOT/configs/envs/mini-swe-py312.txt"
else
  "$UV" pip install --python "$ART/envs/mini-swe/bin/python" mini-swe-agent==2.4.6 fastapi orjson
fi
"$UV" pip freeze --python "$ART/envs/harbor/bin/python" > "$ART/preflight/swe_tb/harbor-requirements.txt"
"$UV" pip freeze --python "$ART/envs/mini-swe/bin/python" > "$ART/preflight/swe_tb/mini-swe-requirements.txt"
"$ART/envs/harbor/bin/harbor" --help > "$ART/preflight/swe_tb/harbor-help.txt"
"$ART/envs/harbor/bin/harbor" run --help > "$ART/preflight/swe_tb/harbor-run-help.txt"

APEX_ROOT="$ROOT" "$ART/envs/harbor/bin/python" - <<'PY'
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import tomllib

from harbor.agents.terminus_2.terminus_2 import Terminus2
from harbor.environments.docker.docker import DockerEnvironment
from harbor.models.job.config import JobConfig

root = Path(os.environ['APEX_ROOT'])
art = root / 'artifacts'
swe = art / 'benchmarks/swe-bench-pro/v2'
ids_path = swe / 'hard51_ids.txt'
assert hashlib.sha256(ids_path.read_bytes()).hexdigest() == '6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1'
swe_ids = ids_path.read_text().splitlines()
assert len(swe_ids) == len(set(swe_ids)) == 51
registry = json.loads((art / 'benchmarks/harbor/registry.json').read_text())
if isinstance(registry, dict):
    registry = registry.get('datasets', registry)
entries = [e for e in registry if e['name'] == 'terminal-bench' and e['version'] == '2.0']
assert len(entries) == 1
tb_tasks = entries[0]['tasks']
assert len(tb_tasks) == 89
tb_ids = [item['name'] for item in tb_tasks]
assert len(set(tb_ids)) == 89

records = []
for benchmark, names, source in [
    ('swe_hard51', swe_ids, swe / 'tasks'),
    ('terminal_bench_2', tb_ids, art / 'benchmarks/terminal-bench-2'),
]:
    # Only task resource metadata is parsed; instruction/solution/tests stay unopened.
    subset = art / 'benchmarks' / ('swe-hard51' if benchmark == 'swe_hard51' else 'terminal-bench-2-registered')
    subset.mkdir(exist_ok=True)
    for name in names:
        task = source / name
        cfg = tomllib.loads((task / 'task.toml').read_text())
        link = subset / name
        if not link.exists():
            link.symlink_to(task, target_is_directory=True)
        env = cfg.get('environment', {})
        records.append({'benchmark': benchmark, 'task_id': name,
                        'task_path': str(task.relative_to(root)),
                        'image': env.get('docker_image'),
                        'environment': env,
                        'agent': cfg.get('agent', {}),
                        'verifier_timeout_sec': cfg.get('verifier', {}).get('timeout_sec')})
out = art / 'preflight/swe_tb'
(out / 'task_image_manifest.json').write_text(json.dumps(records, indent=2) + '\n')
(out / 'images.txt').write_text('\n'.join(dict.fromkeys(r['image'] for r in records if r['image'])) + '\n')
report = {'harbor': importlib.metadata.version('harbor'),
          'litellm': importlib.metadata.version('litellm'),
          'openai': importlib.metadata.version('openai'),
          'swe_tasks': len(swe_ids), 'terminal_tasks': len(tb_ids),
          'terminus_agent_class': Terminus2.__name__,
          'docker_backend_import': DockerEnvironment.__name__,
          'job_config_import': JobConfig.__name__,
          'scope': 'CLI/import/metadata check; no task instructions, solutions, tests, agents, or model requests executed.'}
(out / 'install_check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
PY
"$ART/envs/mini-swe/bin/python" -c 'import importlib.metadata, minisweagent, litellm, fastapi, orjson; print("mini-swe-agent", importlib.metadata.version("mini-swe-agent"))'
