"""Private musl compatibility assets; no task filesystem or shared runtime changes."""
import json
import shutil
from pathlib import Path

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
OUT = ROOT / 'artifacts/preflight/swe_v2/musl_compat'
PYTHON = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'native').mkdir(exist_ok=True)
for name in ['ld-linux-x86-64.so.2', 'libc.so.6', 'libm.so.6', 'libpthread.so.0',
             'libdl.so.2', 'libutil.so.1', 'librt.so.1', 'libresolv.so.2', 'libgcc_s.so.1', 'libstdc++.so.6']:
    shutil.copy2(Path('/lib/x86_64-linux-gnu') / name, OUT / 'native' / name)
shutil.copy2(PYTHON / 'bin/python3.12', OUT / 'python-elf')
wrapper = OUT / 'python-wrapper'
wrapper.write_text('''#!/bin/sh
exec /opt/apex-musl-runtime/native/ld-linux-x86-64.so.2 --library-path /opt/apex-musl-runtime/native --argv0 "$0" /opt/apex-musl-runtime/python-elf "$@"
''')
wrapper.chmod(0o755)
shutil.copy2(ROOT / 'artifacts/tools/uv/uv', OUT / 'uv-elf')
uv_wrapper = OUT / 'uv-wrapper'
uv_wrapper.write_text('''#!/bin/sh
if [ "$1" = tool ] && [ "$2" = install ]; then
  shift 2
  exec /opt/apex-musl-runtime/native/ld-linux-x86-64.so.2 --library-path /opt/apex-musl-runtime/native /opt/apex-musl-runtime/uv-elf tool install --python-platform x86_64-manylinux_2_35 "$@"
fi
exec /opt/apex-musl-runtime/native/ld-linux-x86-64.so.2 --library-path /opt/apex-musl-runtime/native /opt/apex-musl-runtime/uv-elf "$@"
''')
uv_wrapper.chmod(0o755)
musl = [r for r in json.loads((ROOT / 'artifacts/preflight/swe_v2/image-tools-20261016/summary.json').read_text())['results'] if r['exists'] and r.get('returncode', 0) != 0]
(OUT / 'images.json').write_text(json.dumps(musl, indent=2) + '\n')
(OUT / 'shim').mkdir(exist_ok=True)
shim = OUT / 'shim/singularity'
real = ROOT / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin/singularity'
shim.write_text(f'''#!/bin/sh
# Prepend this shim only in the dedicated musl cohort process.
if [ "$1" = exec ]; then
  shift
  exec {real} exec --ignore-fakeroot-command "$@"
fi
exec {real} "$@"
''')
shim.chmod(0o755)
print(json.dumps({'images': len(musl), 'assets': str(OUT)}))
