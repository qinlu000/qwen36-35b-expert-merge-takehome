"""Resolve public SWE/TB image tags without opening benchmark contents or running containers."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import requests

ACCEPT = ', '.join([
    'application/vnd.oci.image.index.v1+json',
    'application/vnd.docker.distribution.manifest.list.v2+json',
    'application/vnd.oci.image.manifest.v1+json',
    'application/vnd.docker.distribution.manifest.v2+json',
])


def resolve(image):
    record = {'image': image, 'checked_at': datetime.now(timezone.utc).isoformat()}
    try:
        parts = image.split('/')
        registry = parts.pop(0) if '.' in parts[0] or ':' in parts[0] else 'registry-1.docker.io'
        repository = '/'.join(parts)
        if '/' not in repository:
            repository = 'library/' + repository
        if '@' in repository:
            repository, reference = repository.rsplit('@', 1)
        elif ':' in repository:
            repository, reference = repository.rsplit(':', 1)
        else:
            reference = 'latest'
        url = f'https://{registry}/v2/{repository}/manifests/{reference}'
        session = requests.Session()
        headers = {'Accept': ACCEPT}
        response = session.get(url, headers=headers, timeout=45)
        if response.status_code == 401:
            scheme, challenge = response.headers['WWW-Authenticate'].split(' ', 1)
            assert scheme.lower() == 'bearer'
            auth = dict(re.findall(r'(\w+)="([^"]+)"', challenge))
            token = session.get(auth.pop('realm'), params=auth, timeout=45)
            token.raise_for_status()
            headers['Authorization'] = 'Bearer ' + (token.json().get('token') or token.json()['access_token'])
            response = session.get(url, headers=headers, timeout=45)
        response.raise_for_status()
        metadata = response.json()
        record.update(digest=response.headers['Docker-Content-Digest'], media_type=metadata.get('mediaType'),
                      pinned_image=f'{image.split("@")[0]}@{response.headers["Docker-Content-Digest"]}')
        if 'manifests' in metadata:
            record['linux_amd64'] = [m for m in metadata['manifests'] if m.get('platform', {}).get('os') == 'linux'
                                     and m.get('platform', {}).get('architecture') == 'amd64']
            assert len(record['linux_amd64']) == 1
            platform_digest = record['linux_amd64'][0]['digest']
            platform_manifest = session.get(f'https://{registry}/v2/{repository}/manifests/{platform_digest}',
                                            headers=headers, timeout=45)
            platform_manifest.raise_for_status()
            metadata = platform_manifest.json()
            record['linux_amd64_manifest_digest'] = platform_digest
        if 'layers' in metadata:
            record['compressed_layer_bytes'] = sum(layer['size'] for layer in metadata['layers'])
        record['status'] = 'resolved'
    except Exception as exc:
        record.update(status='error', error=str(exc))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('images', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    images = list(dict.fromkeys(args.images.read_text().splitlines()))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(resolve, images))
    args.output.write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps({'images': len(records), 'resolved': sum(r['status'] == 'resolved' for r in records),
                      'errors': sum(r['status'] == 'error' for r in records)}))


if __name__ == '__main__':
    main()
