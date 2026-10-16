"""Fetch requested Linux/Python-3.12 wheels or source archives from PyPI, with SHA receipts."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version, InvalidVersion

out = Path(__file__).resolve().parents[1] / 'artifacts/wheels/sft'
out.mkdir(parents=True, exist_ok=True)


def fetch(url):
    return subprocess.run(['curl', '-fsSL', '--retry', '2', '--max-time', '120', url], capture_output=True, check=True).stdout


def compatible_wheel(name):
    if name.endswith(('-py3-none-any.whl', '-py2.py3-none-any.whl')):
        return True
    return name.endswith('.whl') and 'x86_64' in name and ('manylinux' in name or 'linux_x86_64' in name) and (
        'cp312-' in name or '-abi3-' in name or '-py3-none-' in name)


def download(spec):
    req = Requirement(spec)
    metadata = json.loads(fetch('https://pypi.org/pypi/' + req.name + '/json'))
    versions = []
    for value in metadata['releases']:
        try:
            version = Version(value)
        except InvalidVersion:
            continue
        if not version.is_prerelease and version in req.specifier:
            versions.append((version, value))
    for version, release_key in sorted(versions, reverse=True):
        files = [x for x in metadata['releases'][release_key] if not x.get('yanked')]
        choices = [x for x in files if compatible_wheel(x['filename'])]
        choices = choices or [x for x in files if x['filename'].endswith('.tar.gz')]
        if choices:
            break
    item = choices[0]
    path = out / item['filename']
    if not path.exists():
        path.write_bytes(fetch(item['url']))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['digests']['sha256']
    report = {'package': req.name, 'version': str(version), 'file': path.name, 'bytes': path.stat().st_size,
              'sha256': item['digests']['sha256'], 'url': item['url']}
    (out / (req.name.replace('-', '_') + '.receipt.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['package', 'version', 'file', 'bytes']}), flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(download, sys.argv[1:]))
