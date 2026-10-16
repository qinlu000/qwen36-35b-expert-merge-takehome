"""Download one independently selected SWE dev image as a verified OCI layout (no execution)."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
metadata = root / 'artifacts/data/_metadata/night_swe_20261016/registry'
receipt = json.loads((metadata / 'receipts.json').read_text())[0]
assert receipt['instance_id'] == 'pallets__click-1852'
out = root / 'artifacts/data/candidates/new_swe_20261016/env_smoke/click_1852/oci'
blobs = out / 'blobs/sha256'
blobs.mkdir(parents=True, exist_ok=True)
manifest_raw = (metadata / 'pallets__click-1852.manifest.json').read_bytes()
manifest = json.loads(manifest_raw)
image, digest = receipt['pinned_image'].removeprefix('docker.io/').split('@')
assert 'sha256:' + hashlib.sha256(manifest_raw).hexdigest() == digest


def fetch(url, headers=()):
    result = subprocess.run(['curl', '-fsSL', '--max-time', '30'] + sum([['-H', h] for h in headers], []) + [url], capture_output=True, check=True)
    return result.stdout


token = json.loads(fetch('https://auth.docker.io/token?service=registry.docker.io&scope=repository:' + image + ':pull'))['token']
authorization = 'Authorization: Bearer ' + token


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(descriptor):
    digest = descriptor['digest'].split(':')[1]
    path = blobs / digest
    if not path.exists():
        part = path.with_suffix('.part')
        completed = subprocess.run(['curl', '-fsSL', '-C', '-', '--max-time', '600', '-H', authorization,
            '-o', str(part), 'https://registry-1.docker.io/v2/' + image + '/blobs/' + descriptor['digest']],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if completed.returncode:
            raise RuntimeError('OCI blob transfer failed with curl exit ' + str(completed.returncode))
        assert part.stat().st_size == descriptor['size'] and file_hash(part) == digest
        part.rename(path)
    assert path.stat().st_size == descriptor['size'] and file_hash(path) == digest
    print(json.dumps({'verified': descriptor['digest'], 'bytes': path.stat().st_size}), flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(download, [manifest['config']] + manifest['layers']))
(blobs / digest.split(':')[1]).write_bytes(manifest_raw)
(out / 'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}\n')
(out / 'index.json').write_text(json.dumps({'schemaVersion': 2, 'manifests': [{
    'mediaType': manifest['mediaType'], 'digest': digest, 'size': len(manifest_raw)}]}) + '\n')
report = {**receipt, 'objects_verified': len(manifest['layers']) + 2, 'oci_layout': str(out),
    'status': 'all OCI object sizes and SHA256 verified; no runtime commands executed'}
(out.parent / 'download_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
