"""Download and verify the pinned public Base, without loading it or using a GPU."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def checksum(path, algorithm):
    digest = hashlib.new(algorithm)
    if algorithm == 'sha1':
        digest.update(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(source, item, output, aria2=None):
    target = output / item['path']
    partial = target.with_name(target.name + '.part')
    aria2_state = partial.with_name(partial.name + '.aria2')
    finished_partial = partial.exists() and partial.stat().st_size == item['size'] and not aria2_state.exists()
    if not target.exists() and not finished_partial:
        print(json.dumps({'event': 'start', 'file': item['path'], 'bytes': item['size']}), flush=True)
        for attempt in range(4):
            url = (f"https://huggingface.co/{source['repo_id']}/resolve/{source['revision']}/{item['path']}"
                   f"?download=true&request_ts={time.time_ns()}")
            if aria2 and item.get('sha256'):
                headers = subprocess.check_output(['curl', '--fail', '--silent', '--show-error',
                                                   '--head', '--connect-timeout', '20', '--max-time', '40', url], text=True)
                locations = [line.split(':', 1)[1].strip() for line in headers.splitlines()
                             if line.lower().startswith('location:')]
                env = os.environ.copy()
                for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
                    env.pop(key, None)
                env['LD_LIBRARY_PATH'] = str(aria2.parent.parent / 'lib/x86_64-linux-gnu')
                result = subprocess.run([str(aria2), '--continue=true', '--split=8',
                                         '--max-connection-per-server=8', '--min-split-size=8M',
                                         '--file-allocation=none', '--auto-file-renaming=false',
                                         '--allow-overwrite=true', '--max-tries=5', '--retry-wait=3',
                                         '--connect-timeout=20', '--timeout=90', '--quiet=true',
                                         '--dir=' + str(partial.parent), '--out=' + partial.name,
                                         locations[-1]], env=env)
            else:
                result = subprocess.run(['curl', '--http1.1', '--fail', '--location', '--silent', '--show-error',
                                         '--retry', '5', '--retry-delay', '3', '--connect-timeout', '20',
                                         '--speed-time', '120', '--speed-limit', '1024', '--continue-at', '-',
                                         '--output', str(partial), url])
            if result.returncode == 0:
                break
            print(json.dumps({'event': 'resume', 'file': item['path'],
                              'attempt': attempt + 1, 'curl_exit': result.returncode}), flush=True)
        result.check_returncode()
    candidate = target if target.exists() else partial
    if candidate.stat().st_size != item['size']:
        raise ValueError(f"Size mismatch: {item['path']}")
    algorithm = 'sha256' if item.get('sha256') else 'sha1'
    expected = item.get('sha256') or item['git_blob_id']
    actual = checksum(candidate, algorithm)
    if actual != expected:
        raise ValueError(f"Checksum mismatch: {item['path']}")
    if candidate == partial:
        partial.replace(target)
    result = {'file': item['path'], 'bytes': item['size'], algorithm: actual}
    print(json.dumps({'event': 'verified', **result}), flush=True)
    return result


def verify_index(output):
    index = json.loads((output / 'model.safetensors.index.json').read_text())
    observed = {}
    for filename in sorted(set(index['weight_map'].values())):
        with (output / filename).open('rb') as stream:
            header_length = int.from_bytes(stream.read(8), 'little')
            header = json.loads(stream.read(header_length))
        observed.update({name: filename for name in header if name != '__metadata__'})
    if observed != index['weight_map']:
        raise ValueError('Safetensors headers do not match the weight index')
    return {'shards': len(set(observed.values())), 'tensors': len(observed),
            'tensor_bytes': index['metadata']['total_size']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'model_sources.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--aria2', type=Path, help='On a host with direct HF CDN access, use segmented LFS downloads')
    parser.add_argument('--check-only', action='store_true', help='Require every final file; never download missing files')
    args = parser.parse_args()
    source = json.loads(args.manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        missing = [item['path'] for item in source['files'] if not (args.output / item['path']).is_file()]
        if missing:
            raise SystemExit('Missing final files: ' + ', '.join(missing))
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download, source, item, args.output, args.aria2): item for item in source['files']}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                failure = {'file': futures[future]['path'], 'error': str(error)}
                failures.append(failure)
                print(json.dumps({'event': 'failed', **failure}), flush=True)
    receipt = {'repo_id': source['repo_id'], 'revision': source['revision'],
               'recorded_at': datetime.now(timezone.utc).isoformat(),
               'files': sorted(results, key=lambda item: item['file']), 'failures': failures,
               'complete': not failures}
    if not failures:
        receipt['index_check'] = verify_index(args.output)
    (args.output / 'download_receipts.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'event': 'complete', 'verified_files': len(results),
                      'failed_files': len(failures), 'output': str(args.output)}), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
