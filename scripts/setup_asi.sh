#!/usr/bin/env bash
set -euo pipefail

# Run on Linux from the project checkout. All installs remain under artifacts/.
PROJECT_ROOT="${APEX_PROJECT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
ASI_REV=cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc
OPENCODE_VERSION=1.17.15
ASI_SOURCE="$PROJECT_ROOT/artifacts/benchmarks/asi"
ASI_ENV="$PROJECT_ROOT/artifacts/envs/asi-py312"
OPENCODE_ROOT="$PROJECT_ROOT/artifacts/tools/opencode-$OPENCODE_VERSION"
NGSPICE_ROOT="$PROJECT_ROOT/artifacts/tools/ngspice"
UV="${APEX_UV:-$PROJECT_ROOT/artifacts/tools/uv/uv}"
PYTHON="${APEX_PYTHON:-/data/caoqinlu/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12}"
RECEIPTS="$PROJECT_ROOT/artifacts/preflight/asi"

mkdir -p "$RECEIPTS" "$(dirname "$ASI_SOURCE")" "$(dirname "$ASI_ENV")"
export UV_CACHE_DIR="$PROJECT_ROOT/artifacts/cache/uv"
export UV_PYTHON_DOWNLOADS=never
export CUDA_VISIBLE_DEVICES=''

if [[ ! -d "$ASI_SOURCE/.git" ]]; then
  git init "$ASI_SOURCE"
  git -C "$ASI_SOURCE" remote add origin https://github.com/apexin-ai/ASI-Bench.git
  git -C "$ASI_SOURCE" fetch --depth 1 origin "$ASI_REV"
  git -C "$ASI_SOURCE" checkout --detach FETCH_HEAD
fi
test "$(git -C "$ASI_SOURCE" rev-parse HEAD)" = "$ASI_REV"

if [[ ! -x "$ASI_ENV/bin/python" ]]; then
  "$PYTHON" -m venv "$ASI_ENV"
fi
"$UV" pip install --python "$ASI_ENV/bin/python" -r "$PROJECT_ROOT/scripts/requirements-asi.lock"
"$UV" pip install --python "$ASI_ENV/bin/python" --no-deps "$ASI_SOURCE[full]"
"$UV" pip freeze --python "$ASI_ENV/bin/python" > "$RECEIPTS/requirements.lock.txt"

mkdir -p "$OPENCODE_ROOT"
if [[ ! -x "$OPENCODE_ROOT/node_modules/.bin/opencode" ]]; then
  cp "$PROJECT_ROOT/configs/asi/package.json" "$PROJECT_ROOT/configs/asi/package-lock.json" "$OPENCODE_ROOT/"
  npm ci --prefix "$OPENCODE_ROOT" --ignore-scripts=false
fi

# Ubuntu 22.04 preparation host: unpack ngspice locally, without apt install.
if [[ ! -x "$NGSPICE_ROOT/usr/bin/ngspice" ]]; then
  mkdir -p "$NGSPICE_ROOT/debs"
  (
    cd "$NGSPICE_ROOT/debs"
    apt download ngspice=36+ds-1ubuntu0.1
    dpkg-deb -x ngspice_36+ds-1ubuntu0.1_amd64.deb "$NGSPICE_ROOT"
  )
fi
"$ASI_ENV/bin/python" - "$NGSPICE_ROOT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
path = root / "usr/share/ngspice/scripts/spinit"
path.write_text(path.read_text().replace("codemodel /usr/", f"codemodel {root}/usr/"))
PY
mkdir -p "$NGSPICE_ROOT/bin"
cat > "$NGSPICE_ROOT/bin/ngspice" <<'SH'
#!/usr/bin/env bash
NGSPICE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export SPICE_LIB_DIR="$NGSPICE_ROOT/usr/share/ngspice"
export SPICE_SCRIPTS="$NGSPICE_ROOT/usr/share/ngspice/scripts"
exec "$NGSPICE_ROOT/usr/bin/ngspice" "$@"
SH
chmod +x "$NGSPICE_ROOT/bin/ngspice"
"$NGSPICE_ROOT/usr/bin/ngspice" --version > "$RECEIPTS/ngspice_version.txt" 2>&1
sha256sum "$NGSPICE_ROOT/debs/ngspice_36+ds-1ubuntu0.1_amd64.deb" > "$RECEIPTS/ngspice_deb.sha256"

"$UV" pip check --python "$ASI_ENV/bin/python"
"$ASI_ENV/bin/asibench" --help > "$RECEIPTS/asibench_help.txt" 2>&1
"$ASI_ENV/bin/asibench" run --help > "$RECEIPTS/asibench_run_help.txt" 2>&1
"$ASI_ENV/bin/asibench" score --help > "$RECEIPTS/asibench_score_help.txt" 2>&1
"$OPENCODE_ROOT/node_modules/.bin/opencode" --version > "$RECEIPTS/opencode_version.txt"
test "$(tr -d '\r\n' < "$RECEIPTS/opencode_version.txt")" = "$OPENCODE_VERSION"
git -C "$ASI_SOURCE" rev-parse HEAD > "$RECEIPTS/asi_revision.txt"
printf '%s\n' 'ASI framework and OpenCode installed. This does not launch benchmark tasks or scoring.'
