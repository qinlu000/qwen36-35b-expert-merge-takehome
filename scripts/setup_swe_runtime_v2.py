#!/usr/bin/env python3
"""Prepare auditable offline mini wheels and the small Harbor server runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12'
UV = ROOT / 'artifacts/tools/uv/uv'
WHEELS = ROOT / 'artifacts/cache/swe-v2-wheels'
RUNTIME = ROOT / 'artifacts/cache/swe-v2-runtime'
CONSTRAINTS = ROOT / 'configs/envs/mini-swe-py312.txt'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    WHEELS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if args.download:
        subprocess.run([str(PYTHON), '-m', 'pip', 'download', '--only-binary=:all:',
            '--no-deps', '-r', str(CONSTRAINTS), 'uvicorn==0.48.0', '-d', str(WHEELS)], check=True)
    server = RUNTIME / 'harbor-server'
    if not (server / 'bin/python3').exists():
        subprocess.run([str(UV), 'venv', '--python', str(PYTHON), str(server)], check=True)
    subprocess.run([str(UV), 'pip', 'install', '--python', str(server / 'bin/python3'),
        '--no-index', '--find-links', str(WHEELS), '--link-mode', 'copy',
        '--constraints', str(CONSTRAINTS), 'fastapi', 'uvicorn==0.48.0'], check=True)
    code = ('import importlib.metadata as m,json; '
            'print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()},sort_keys=True))')
    versions = json.loads(subprocess.check_output([str(server / 'bin/python3'), '-c', code], text=True))
    wrapper = RUNTIME / 'python3.12'
    wrapper.write_text('#!/bin/sh\nexec ' + str(PYTHON) + ' "$@"\n')
    wrapper.chmod(0o755)
    # A private loader/library bundle supplies curl only where an image lacks it;
    # it does not replace an image's own libc or existing curl.
    native = RUNTIME / 'native'
    native.mkdir(exist_ok=True)
    curl = Path('/usr/bin/curl')
    linked = subprocess.check_output(['ldd', str(curl)], text=True)
    libraries = re.findall(r'(?:=>\s+|^\s*)(/\S+)', linked, re.M)
    for source in [curl, *map(Path, libraries)]:
        shutil.copyfile(source, native / source.name)
        (native / source.name).chmod(0o755)
    curl_wrapper = RUNTIME / 'curl'
    curl_wrapper.write_text('#!/bin/sh\nexec /opt/apex-swe-runtime/native/ld-linux-x86-64.so.2 '
        '--library-path /opt/apex-swe-runtime/native /opt/apex-swe-runtime/native/curl "$@"\n')
    curl_wrapper.chmod(0o755)
    wheel_files = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                   for p in sorted(WHEELS.glob('*.whl'))}
    manifest = {'python': str(PYTHON), 'python_sha256': digest(PYTHON),
        'uv_sha256': digest(UV), 'constraint_sha256': digest(CONSTRAINTS),
        'server_versions': versions, 'wheels': wheel_files,
        'native_files': {p.name: digest(p) for p in sorted(native.iterdir())},
        'setup': 'cached server, native constrained uv tool install offline; no task or model data'}
    (RUNTIME / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'manifest': str(RUNTIME / 'manifest.json'), 'wheels': len(wheel_files),
                      'server_versions': versions}, indent=2))


if __name__ == '__main__':
    main()
