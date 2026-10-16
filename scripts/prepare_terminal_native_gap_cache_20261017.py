#!/usr/bin/env python3
"""Prepare exact verifier dependencies for the six saved-answer repairs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
OUT = ROOT / 'artifacts/recovery/terminal-v2/native-gaps-20261017'
TOOLS = ROOT / 'artifacts/tools/terminal_verifier_offline_20261016'
UV = ROOT / 'artifacts/cache/terminal-v2-native/uv-wheel/bin/uv'
PY11 = TOOLS / 'python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11'
REQ = ['torch==2.5.1', 'torchvision==0.20.1', 'pandas==2.3.2',
       'timm==1.0.19', 'opencv-python==4.12.0.88', 'shapely==2.1.1',
       'pytest==8.4.1', 'pytest-json-ctrf==0.3.5',
       'git+https://github.com/ChaoningZhang/MobileSAM.git@34bbbfdface3c18e5221aa7de6032d7220c6c6a1']


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def cache_sam():
    target = OUT / 'sam-cache'
    target.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, UV_CACHE_DIR=str(target / 'uv-cache'),
               UV_PYTHON_INSTALL_DIR=str(TOOLS / 'python'), UV_PYTHON_DOWNLOADS='never',
               UV_HTTP_TIMEOUT='120', UV_CONCURRENT_DOWNLOADS='12',
               UV_CONCURRENT_INSTALLS='2', UV_CONCURRENT_BUILDS='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               TMPDIR='/data/caoqinlu/apex-cache-gap-tmp')
    Path(env['TMPDIR']).mkdir(exist_ok=True)
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
        env.pop(key, None)
    command = [str(UV), 'pip', 'install', '--python', str(PY11), '--target', str(target / 'target'),
               '--index', 'https://download.pytorch.org/whl/cpu',
               '--index-strategy', 'unsafe-best-match', *REQ]
    with (target / 'prefetch.log').open('a') as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=3600)
        url_cache = target / 'url-cache'
        url_cache.mkdir(exist_ok=True)
        weights_url = 'https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt'
        download = subprocess.run(['curl', '-fL', '--retry', '2', '--connect-timeout', '15',
            '--max-time', '300', '-o', str(url_cache / 'mobile_sam.pt'), weights_url],
            env=env, stdout=log, stderr=log)
        save(url_cache / 'url_map.json', {weights_url: 'mobile_sam.pt'})
    packages = {d.metadata['Name']: d.version for d in
                importlib.metadata.distributions(path=[str(target / 'target')])}
    record = dict(task='sam-cell-seg', ready=result.returncode == 0 and download.returncode == 0,
                  returncode=result.returncode, weights_download_returncode=download.returncode,
                  url_cache_dir=str(url_cache), public_weights_url=weights_url,
                  requirements=REQ, command=command, python=str(PY11),
                  uv_cache_dir=str(target / 'uv-cache'), resolved_packages=packages,
                  fixed_git_commit='34bbbfdface3c18e5221aa7de6032d7220c6c6a1',
                  tests_run=False, model_calls=0, finished_at_utc=datetime.now(timezone.utc).isoformat())
    save(target / 'receipt.json', record)
    print(json.dumps({'cache': 'sam', 'ready': record['ready']}), flush=True)
    return record


def cache_doom_apt():
    target = OUT / 'doom-apt'
    target.mkdir(parents=True, exist_ok=True)
    image = ROOT / 'artifacts/benchmarks/sif/alexgshaw_make-doom-for-mips_20251031.sif'
    with image.open('rb') as stream:
        offset = stream.read(1048576).find(b'hsqs')
    if offset < 0:
        raise RuntimeError('SIF squashfs offset not found')
    for source, destination in [('var/lib/dpkg/status', target / 'status'),
                                ('usr/share/keyrings/debian-archive-keyring.gpg', target / 'keyring.gpg')]:
        with destination.open('wb') as stream:
            subprocess.run(['unsquashfs', '-o', str(offset), '-cat', str(image), source],
                           stdout=stream, stderr=subprocess.DEVNULL, check=True)
    for name in ['lists/partial', 'archives/partial', 'log']:
        (target / name).mkdir(parents=True, exist_ok=True)
    # The candidate's snapshot source and exact dated package versions remain intact.
    # Its two other source stanzas fail (expired updates and malformed security URL).
    source = 'http://snapshot.debian.org/archive/debian/20250811T000000Z'
    (target / 'sources.list').write_text(
        f'deb [check-valid-until=no signed-by={target / "keyring.gpg"}] {source} bookworm main\n')
    options = {'Dir::Etc::sourcelist': str(target / 'sources.list'), 'Dir::Etc::sourceparts': '-',
               'Dir::State::lists': str(target / 'lists'), 'Dir::State::status': str(target / 'status'),
               'Dir::Cache::archives': str(target / 'archives'), 'Dir::Log': str(target / 'log'),
               'APT::Architecture': 'amd64', 'APT::Architectures::': 'amd64',
               'Acquire::Languages': 'none', 'Acquire::Retries': '1',
               'Acquire::http::Timeout': '30', 'Acquire::https::Timeout': '30',
               'Debug::NoLocking': 'true'}
    args = [part for key, value in options.items() for part in ['-o', key + '=' + value]]
    commands = [['apt-get', *args, 'update'],
                ['apt-get', *args, '--download-only', '-y', 'install', 'curl', 'python3-pillow']]
    returns = []
    with (target / 'prefetch.log').open('a') as log:
        for command in commands:
            ret = subprocess.run(command, stdout=log, stderr=log, timeout=1800).returncode
            returns.append(ret)
            if ret:
                break
    record = dict(task='make-doom-for-mips', ready=returns == [0, 0], returncodes=returns,
                  dated_snapshot=source, native_packages=['curl', 'python3-pillow'],
                  archives=[p.name for p in (target / 'archives').glob('*.deb')],
                  original_dpkg_status_from=str(image), tests_run=False, model_calls=0,
                  commands=[shlex.join(c) for c in commands],
                  finished_at_utc=datetime.now(timezone.utc).isoformat())
    save(target / 'receipt.json', record)
    print(json.dumps({'cache': 'doom-apt', 'ready': record['ready']}), flush=True)
    return record


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fn) for fn in [cache_sam, cache_doom_apt]]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({'ready': False, 'exception': repr(exc)})
        save(OUT / 'prefetch-summary.json', {'results': results, 'tests_run': False, 'model_calls': 0})


if __name__ == '__main__':
    main()
