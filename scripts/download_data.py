"""Download pinned candidate data without reading or replaying samples."""
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'artifacts' / 'data'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(name, source, item):
    target = DATA / 'raw' / name / source['revision'] / item['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    cached = target.exists()
    if not cached:
        partial = target.with_name(target.name + '.part')
        url = (f"https://huggingface.co/datasets/{source['repo_id']}/resolve/"
               f"{source['revision']}/{quote(item['path'], safe='/')}"
               f"?download=true&request_ts={time.time_ns()}")
        print(json.dumps({'event': 'start', 'source': name, 'file': item['path'],
                          'bytes': item['size']}), flush=True)
        transport = []
        if item.get('sha256'):
            headers = subprocess.run(
                ['curl', '--fail', '--silent', '--show-error', '--head',
                 '--connect-timeout', '20', '--max-time', '40', url],
                capture_output=True, text=True, check=True).stdout
            locations = [line.split(':', 1)[1].strip() for line in headers.splitlines()
                         if line.lower().startswith('location:')]
            if locations:
                url = urljoin(url, locations[-1])
                transport = ['--noproxy', '*']
        aria2 = ROOT / 'artifacts/tools/aria2/usr/bin/aria2c'
        if transport and aria2.exists():
            env = os.environ.copy()
            for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                env.pop(key, None)
            env['LD_LIBRARY_PATH'] = str(ROOT / 'artifacts/tools/aria2/usr/lib/x86_64-linux-gnu')
            command = [str(aria2), '--continue=true', '--split=8',
                       '--max-connection-per-server=8', '--min-split-size=8M',
                       '--file-allocation=none', '--auto-file-renaming=false',
                       '--allow-overwrite=true', '--max-tries=5', '--retry-wait=3',
                       '--connect-timeout=20', '--timeout=90', '--quiet=true',
                       '--dir=' + str(partial.parent), '--out=' + partial.name, url]
            result = subprocess.run(command, env=env, capture_output=True)
        else:
            result = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                                     '--retry', '4', '--retry-delay', '3', '--connect-timeout', '20',
                                     '--speed-time', '90', '--speed-limit', '1024',
                                     '--continue-at', '-', '--output', str(partial), *transport, url])
        if result.returncode:
            raise RuntimeError(f'download exit status {result.returncode}')
        actual = partial
    else:
        actual = target
    if actual.stat().st_size != item['size']:
        raise ValueError(f"Size mismatch: {name}/{item['path']}")
    checksum = sha256(actual)
    if item.get('sha256') and checksum != item['sha256']:
        raise ValueError(f"SHA-256 mismatch: {name}/{item['path']}")
    if not cached:
        actual.replace(target)
    return {'source': name, 'repo_id': source['repo_id'], 'revision': source['revision'],
            'file': item['path'], 'local_path': str(target.relative_to(ROOT)),
            'bytes': target.stat().st_size, 'sha256': checksum,
            'upstream_sha256': item.get('sha256'), 'cached': cached,
            'completed_at': datetime.now(timezone.utc).isoformat()}


def main():
    sources = json.loads((ROOT / 'data_sources.json').read_text())
    jobs = [(name, source, item) for name, source in sources.items() for item in source['files']]
    jobs.sort(key=lambda job: job[2]['size'], reverse=True)
    receipts, failures = [], []
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / 'download_progress.jsonl').open('a') as progress:
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending = {pool.submit(download, *job): (job[0], job[2]['path']) for job in jobs}
            for future in as_completed(pending):
                try:
                    receipt = future.result()
                    receipts.append(receipt)
                    event = {'event': 'complete', **receipt}
                except Exception as error:
                    name, file = pending[future]
                    event = {'event': 'failed', 'source': name, 'file': file, 'error': str(error)}
                    failures.append(event)
                progress.write(json.dumps(event) + '\n')
                progress.flush()
                print(json.dumps(event), flush=True)
    (DATA / 'download_receipts.json').write_text(json.dumps(
        {'completed': receipts, 'failed': failures}, indent=2) + '\n')
    print(json.dumps({'event': 'finished', 'files': len(receipts), 'failed': len(failures),
                      'bytes': sum(item['bytes'] for item in receipts)}), flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
