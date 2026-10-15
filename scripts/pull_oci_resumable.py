"""Resume pinned OCI blobs in a project cache, then let Apptainer create the SIF."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import requests


CHUNK_SIZE = 8 * 1024 * 1024
ACCEPT = 'application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'


def digest_hex(digest):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Expected a pinned sha256 digest')
    return digest.split(':', 1)[1]


def blob_path(cache, digest):
    return cache / 'blobs/sha256' / digest_hex(digest)


def verify_file(path, digest, size):
    if path.stat().st_size != size:
        raise ValueError(f'Blob size mismatch: {digest}')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != digest_hex(digest):
        raise ValueError(f'Blob SHA256 mismatch: {digest}')


@contextmanager
def blob_lock(cache, digest):
    locks = cache / 'locks'
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / (digest_hex(digest) + '.lock')).open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


class Registry:
    """Anonymous registry requests, refreshing the standard Bearer challenge."""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['Accept-Encoding'] = 'identity'

    def get(self, url, **kwargs):
        response = self.session.get(url, **kwargs)
        if response.status_code == 401:
            challenge = response.headers.get('WWW-Authenticate', '')
            scheme, _, values = challenge.partition(' ')
            if scheme.lower() != 'bearer':
                raise RuntimeError('Registry requires unsupported authentication')
            fields = requests.utils.parse_dict_header(values)
            response.close()
            token_response = self.session.get(
                fields['realm'],
                params={key: fields[key] for key in ('service', 'scope') if key in fields},
                timeout=(20, 60),
            )
            if token_response.status_code != 200:
                raise RuntimeError(f'Anonymous token endpoint returned HTTP {token_response.status_code}')
            token = token_response.json()
            self.session.headers['Authorization'] = 'Bearer ' + (token.get('token') or token['access_token'])
            response = self.session.get(url, **kwargs)
        return response


def download_blob(session, url, digest, size, cache, native_cache=None):
    """Keep complete 8 MiB segments; publish only after whole-blob size/SHA checks."""
    final = blob_path(cache, digest)
    final.parent.mkdir(parents=True, exist_ok=True)
    parts = cache / 'parts'
    parts.mkdir(parents=True, exist_ok=True)
    part = parts / (digest_hex(digest) + '.part')
    with blob_lock(cache, digest):
        if final.exists():
            verify_file(final, digest, size)
            print(f'CACHED {digest} {size}', flush=True)
            return final
        if native_cache is not None:
            native = blob_path(native_cache, digest)
            if native.exists():
                try:
                    verify_file(native, digest, size)
                except ValueError:
                    pass
                else:
                    os.link(native, final)  # Complete immutable blob, no native index writes.
                    print(f'REUSED {digest} {size}', flush=True)
                    return final
        part.touch(exist_ok=True)
        if part.stat().st_size > size:
            raise ValueError(f'Resumable file exceeds blob size: {digest}')
        while (offset := part.stat().st_size) < size:
            end = min(offset + CHUNK_SIZE, size) - 1
            expected = end - offset + 1
            for attempt in range(6):
                try:
                    with session.get(
                        url, headers={'Range': f'bytes={offset}-{end}', 'Accept-Encoding': 'identity'},
                        stream=True, timeout=(20, 120),
                    ) as response:
                        if response.status_code != 206:
                            raise ValueError(f'Expected HTTP 206, received {response.status_code}')
                        if response.headers.get('Content-Range') != f'bytes {offset}-{end}/{size}':
                            raise ValueError('Incorrect Content-Range')
                        if response.headers.get('Content-Encoding', 'identity') != 'identity':
                            raise ValueError('Unexpected HTTP content encoding')
                        data = bytearray()
                        for chunk in response.iter_content(1024 * 1024):
                            data.extend(chunk)
                            if len(data) > expected:
                                raise ValueError('Range body exceeds requested size')
                        if len(data) != expected:
                            raise ValueError('Incomplete Range body')
                    with part.open('ab') as stream:
                        stream.write(data)
                    break
                except (requests.RequestException, ValueError) as exc:
                    print(f'RETRY {digest} {offset}-{end} {attempt + 1}/6 {type(exc).__name__}', flush=True)
                    if attempt == 5:
                        raise RuntimeError(f'Range failed for {digest} bytes {offset}-{end}') from None
                    time.sleep(min(2 ** attempt, 8))
            print(f'RANGE {digest} {part.stat().st_size}/{size}', flush=True)
        try:
            verify_file(part, digest, size)
        except ValueError:
            os.replace(part, part.with_suffix('.invalid'))
            raise
        os.replace(part, final)
        return final


def save_manifest(cache, digest, raw):
    if hashlib.sha256(raw).hexdigest() != digest_hex(digest):
        raise ValueError('Pinned manifest SHA256 mismatch')
    final = blob_path(cache, digest)
    final.parent.mkdir(parents=True, exist_ok=True)
    with blob_lock(cache, digest):
        if final.exists():
            verify_file(final, digest, len(raw))
        else:
            temporary = final.with_suffix('.partial')
            temporary.write_bytes(raw)
            os.replace(temporary, final)
    return final


def registry_reference(image):
    repository, digest = image.rsplit('@', 1)
    digest_hex(digest)
    first, _, rest = repository.partition('/')
    if '.' in first or ':' in first or first == 'localhost':
        registry, repository = first, rest
    else:
        registry = 'registry-1.docker.io'
        if '/' not in repository:
            repository = 'library/' + repository
    return f'https://{registry}/v2/{repository}', digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--image', required=True, help='Repository@sha256:<linux/amd64 manifest>')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    cache = root / 'artifacts/cache/ranged-oci'
    native = root / 'artifacts/cache/apptainer/cache/blob'
    base, digest = registry_reference(args.image)
    registry = Registry()
    with registry.get(base + '/manifests/' + digest, headers={'Accept': ACCEPT}, timeout=(20, 60)) as response:
        if response.status_code != 200:
            raise RuntimeError(f'Manifest endpoint returned HTTP {response.status_code}')
        raw = response.content
    manifest_path = save_manifest(cache, digest, raw)
    manifest = json.loads(raw)
    if 'config' not in manifest or 'layers' not in manifest:
        raise ValueError('Expected a pinned image manifest, not a multi-platform index')
    objects = [manifest['config']] + manifest['layers']
    paths = [manifest_path]
    for descriptor in objects:
        paths.append(download_blob(registry, base + '/blobs/' + descriptor['digest'],
                                   descriptor['digest'], descriptor['size'], cache, native))
    layout = cache / 'layouts' / digest_hex(digest)
    (layout / 'blobs/sha256').mkdir(parents=True, exist_ok=True)
    for source in paths:
        destination = layout / 'blobs/sha256' / source.name
        if not destination.exists():
            os.link(source, destination)
    (layout / 'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}\n')
    index = {'schemaVersion': 2, 'manifests': [
        {'mediaType': manifest['mediaType'], 'digest': digest, 'size': len(raw)}]}
    (layout / 'index.json').write_text(json.dumps(index) + '\n')
    temporary = cache / 'tmp'
    temporary.mkdir(exist_ok=True)
    tool = root / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin/apptainer'
    env = os.environ | {'APPTAINER_TMPDIR': str(temporary)}
    subprocess.run([str(tool), 'pull', '--disable-cache', '--arch', 'amd64',
                    str(args.output), 'oci:' + str(layout)], env=env, check=True)
    receipt = {'image': args.image, 'manifest_sha256': digest, 'objects_verified': len(paths),
               'oci_layout': str(layout), 'output': str(args.output),
               'scope': 'Blob transfer and official OCI-to-SIF conversion only; no image commands'}
    args.output.with_suffix(args.output.suffix + '.oci.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    try:
        main()
    except requests.RequestException as exc:
        # Request exception strings may contain redirected, signed CDN URLs.
        raise SystemExit(f'Registry request failed: {type(exc).__name__}') from None
