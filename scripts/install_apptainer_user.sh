#!/usr/bin/env bash
# Extract the official non-suid Debian package into this project; no system installation.
set -euo pipefail
ROOT=${APEX_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
DEST="$ROOT/artifacts/tools/apptainer-1.4.5"
mkdir -p "$DEST"
if [[ ! -f "$DEST/apptainer_1.4.5_amd64.deb" ]]; then
  curl -fL --retry 3 https://github.com/apptainer/apptainer/releases/download/v1.4.5/apptainer_1.4.5_amd64.deb \
    -o "$DEST/apptainer_1.4.5_amd64.deb"
fi
(cd "$DEST" && printf '70f19af846501acfbc2e42e7cfeee9ee11ddbbfa1c3502d0d99cde34e8e0af05  apptainer_1.4.5_amd64.deb\n' | sha256sum -c)
if [[ ! -x "$DEST/rootfs/usr/bin/apptainer" ]]; then
  dpkg-deb -x "$DEST/apptainer_1.4.5_amd64.deb" "$DEST/rootfs"
fi
# The relocatable binary infers a prefix ending in /usr; retain package config paths.
ln -sfn ../etc "$DEST/rootfs/usr/etc"
ln -sfn ../var "$DEST/rootfs/usr/var"
python3 - "$DEST/rootfs/etc/apptainer/apptainer.conf" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text().replace('mksquashfs procs = 0', 'mksquashfs procs = 4')
s = s.replace('mksquashfs procs = 2', 'mksquashfs procs = 4')
s = s.replace('# mksquashfs mem = 1G', 'mksquashfs mem = 1G')
p.write_text(s)
PY
"$DEST/rootfs/usr/bin/apptainer" version
"$DEST/rootfs/usr/bin/apptainer" buildcfg > "$DEST/buildcfg.txt"
