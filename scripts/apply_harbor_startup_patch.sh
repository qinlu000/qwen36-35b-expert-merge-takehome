#!/usr/bin/env bash
# Explicit local patch on the pinned Harbor tree; also works on its HPC archive.
set -euo pipefail
ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
HARBOR="$ROOT/artifacts/benchmarks/harbor"
REV=f527f8e447038fd242d08ecfa8aaa8029100da97
MODE=${1:-apply}
case "$MODE" in apply|reverse-native) ;; *) echo "Usage: $0 [apply|reverse-native]" >&2; exit 1 ;; esac
if [[ -d "$HARBOR/.git" ]]; then
  [[ $(git -C "$HARBOR" rev-parse HEAD) == "$REV" ]]
  git -C "$HARBOR" diff --cached --quiet
  while IFS= read -r path; do
    case "$path" in src/harbor/environments/singularity/singularity.py|src/harbor/environments/singularity/server.py) ;;
      *) echo "Unknown Harbor modification: $path" >&2; exit 1 ;;
    esac
  done < <(git -C "$HARBOR" diff --name-only)
else
  [[ $(cat "$HARBOR/SOURCE_REVISION") == "$REV" ]]
fi
SOURCE="$HARBOR/src/harbor/environments/singularity"
hashes=$(sha256sum "$SOURCE/singularity.py" "$SOURCE/server.py" | awk '{print $1}' | paste -sd: -)
case "$hashes" in
  53a311a61eb32feb3d36dc238951456098e17ec227d0b2dc0db1e9fe8e73eb75:1c4966bc330e6bd010ec9201f947389bb858defe6bc8e9647a24980f2e0d6b5c) native=original ;;
  86e826120a375c006693c6bab6f238a80bcaae85de08d18f54c458da7728f62b:49f59b9a5286bb4eb6afcd9bd79e5a1086027eb9be1dde29ca5d6fff4c0651ea) native=patched ;;
  *) echo "Unknown Harbor source bytes; refusing patch/reverse" >&2; exit 1 ;;
esac
PATCH="$ROOT/scripts/harbor_startup.patch"
if [[ "$MODE" == reverse-native ]]; then
  if [[ "$native" == patched ]]; then
    git -C "$HARBOR" apply --reverse --check "$PATCH"
    git -C "$HARBOR" apply --reverse "$PATCH"
  fi
  echo "Harbor native patch reversed/original; use apply before running Harbor"
  exit
fi
if [[ "$native" == original ]]; then git -C "$HARBOR" apply --check "$PATCH"; else git -C "$HARBOR" apply --reverse --check "$PATCH"; fi
APEX_PATCH="$ROOT/scripts/harbor_startup_apex.patch"
if git -C "$ROOT" apply --check "$APEX_PATCH" 2>/dev/null; then
  apex=original
else
  git -C "$ROOT" apply --reverse --check "$APEX_PATCH"
  apex=patched
fi
# Validate both patches before changing either source.
if [[ "$native" == original ]]; then git -C "$HARBOR" apply "$PATCH"; fi
if [[ "$apex" == original ]]; then git -C "$ROOT" apply "$APEX_PATCH"; fi
echo "Harbor $REV + startup patch; Apex companion applied"
