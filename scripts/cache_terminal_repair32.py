#!/usr/bin/env python3
"""Download exact missing verifier dependencies; no models or task tests."""
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess

from freeze_terminal_verifier_cache_v2 import export

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
TOOLS = ROOT / 'artifacts/tools/terminal_verifier_offline_20261016'
OUT = TOOLS / 'repair32-20261016'
UV = ROOT / 'artifacts/cache/terminal-v2-native/uv-wheel/bin/uv'
PY13 = ROOT / 'artifacts/cache/terminal-v2-native/python/cpython-3.13.9-linux-x86_64-gnu/bin/python3.13'
PY12_ROOT = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
BASE = ['pytest==8.4.1', 'pytest-json-ctrf==0.3.5']
JOBS = [
    ('build-cython-ext', '3.13', BASE),
    ('largest-eigenval', '3.13', BASE),
    ('hf-model-inference', '3.13', BASE + ['psutil==7.0.0', 'requests==2.32.4']),
    ('kv-store-grpc', '3.13', ['pytest==8.4.2', 'requests==2.32.5', 'psutil==7.0.0', 'pytest-json-ctrf==0.3.5']),
    ('mailman', '3.12', BASE + ['mailman==3.3.8']),
]


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    py12 = TOOLS / 'python' / PY12_ROOT.name
    if not py12.exists():
        shutil.copytree(PY12_ROOT, py12, symlinks=True, copy_function=os.link)
    env = dict(os.environ, UV_CACHE_DIR=str(TOOLS / 'uv-cache'),
               UV_PYTHON_INSTALL_DIR=str(TOOLS / 'python'),
               UV_HTTP_TIMEOUT='60', UV_CONCURRENT_BUILDS='1',
               UV_CONCURRENT_DOWNLOADS='4', UV_CONCURRENT_INSTALLS='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               TMPDIR='/data/caoqinlu/apex-cache-tmp')
    Path(env['TMPDIR']).mkdir(exist_ok=True)
    for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        env.pop(key, None)
    outcomes = []
    for task, version, requirements in JOBS:
        target = OUT / ('target-' + task)
        frozen = OUT / ('cache-' + task)
        wheels = OUT / ('pip-wheels-' + task)
        python = PY13 if version == '3.13' else py12 / 'bin/python3.12'
        record = {'task_id': task, 'python_version': version, 'python': str(python),
                  'requirements': requirements, 'tests_run': False, 'model_calls': 0}
        with (OUT / (task + '.log')).open('a') as log:
            command = [str(UV), 'pip', 'install', '--python', str(python), '--target', str(target),
                       '--default-index', 'https://pypi.org/simple', *requirements]
            result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=1800)
            record['uv_install_returncode'] = result.returncode
            if result.returncode:
                record['ready'] = False
                save(OUT / (task + '.json'), record)
                outcomes.append(record)
                continue
            packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions(path=[str(target)])}
            missing = export(TOOLS / 'uv-cache', frozen, packages)
            record.update(uv_cache_dir=str(frozen), resolved_packages=packages, missing_cache_entries=missing)
            if version == '3.13':
                wheels.mkdir(exist_ok=True)
                command = [str(UV), 'tool', 'run', '--python', str(PY13), '--from', 'pip',
                           'pip', 'download', '--index-url', 'https://pypi.org/simple',
                           '--only-binary=:all:', '--dest', str(wheels), *requirements]
                result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=1800)
                record.update(pip_download_returncode=result.returncode, pip_wheelhouse=str(wheels),
                              wheel_files=sorted(p.name for p in wheels.glob('*.whl')))
            record['ready'] = not missing and record.get('pip_download_returncode', 0) == 0
            record['frozen_no_further_writes'] = True
            record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
            save(frozen / 'snapshot_receipt.json', record)
            save(OUT / (task + '.json'), record)
            if record['ready']:
                mapping_path = TOOLS / 'task_cache_map.json'
                mapping = json.loads(mapping_path.read_text())
                mapping[task] = {key: record[key] for key in
                    ('python', 'uv_cache_dir', 'ready', 'missing_cache_entries', 'requirements', 'python_version')}
                if 'pip_wheelhouse' in record:
                    mapping[task]['pip_wheelhouse'] = record['pip_wheelhouse']
                save(mapping_path, mapping)
            outcomes.append(record)
        save(OUT / 'summary.json', {'outcomes': outcomes, 'model_calls': 0, 'tests_run': False})
        print(json.dumps({'task': task, 'ready': record['ready'], 'packages': len(packages)}), flush=True)


if __name__ == '__main__':
    main()
