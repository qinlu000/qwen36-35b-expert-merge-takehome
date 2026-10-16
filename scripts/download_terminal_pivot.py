#!/usr/bin/env python3
"""Resume the three public Pivot Parquet files through the existing dev proxy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    out = args.root / 'artifacts/data/candidates/nemotron_terminal_pivot_20261016/raw'
    manifest = json.load((out / 'download_manifest.json').open())

    def download(record):
        path = out / record['filename']
        if path.exists() and path.stat().st_size == record['size']:
            return {'file': path.name, 'bytes': path.stat().st_size, 'complete': True}
        part, chunk = path.with_suffix('.parquet.part'), path.with_suffix('.chunk')
        start = part.stat().st_size if part.exists() else 0
        with part.open('ab') as stream:
            while start < record['size']:
                end = min(start + 32 * 1024 * 1024, record['size']) - 1
                subprocess.run(['curl', '-sSfL', '--retry', '2', '--retry-all-errors', '--connect-timeout', '10',
                                '--max-time', '120', '-x', 'http://127.0.0.1:38080',
                                '-r', '%d-%d' % (start, end),
                                record['url'] + '?download=true&chunk=%d' % start,
                                '-o', str(chunk)], check=True)
                assert chunk.stat().st_size == end - start + 1
                with chunk.open('rb') as source: shutil.copyfileobj(source, stream)
                stream.flush()
                start = end + 1
                chunk.unlink()
                print(json.dumps({'file': path.name, 'bytes': start, 'expected': record['size']}), flush=True)
        assert part.stat().st_size == record['size']
        part.rename(path)
        return {'file': path.name, 'bytes': path.stat().st_size, 'complete': True}

    with ThreadPoolExecutor(max_workers=3) as executor:
        for receipt in executor.map(download, manifest['parquet_files']):
            print(json.dumps(receipt), flush=True)


if __name__ == '__main__': main()
