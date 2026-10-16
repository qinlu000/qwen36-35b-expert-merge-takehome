"""CPU-only exclusion fingerprints of fixed evaluation inputs; never read answers."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)


HLE_REVISION = '5a81a4c7271a2a2a312b9a690f0c2fde837e4c29'
HLE_SHA256 = '6d0ee0602e8aea6b159509577e884f48ecac7b8e3f6822a35f51335a446c726a'


def fingerprint(text):
    normalized = unicodedata.normalize('NFKC', text)
    normalized = re.sub(r'\s+', ' ', normalized).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()

    # A small normalization check; no model or task execution.
    assert fingerprint('Ａ  B\nC') == fingerprint('a b c')
    root = args.root
    hle_path = root / 'artifacts/benchmarks/hle' / HLE_REVISION / 'test-00000-of-00001.parquet'
    hle_sha = file_sha256(hle_path)
    assert hle_sha == HLE_SHA256
    hle = pq.read_table(hle_path, columns=['id', 'question']).to_pylist()
    expected_hle = set(json.loads((root / 'analysis/source_snapshots/protocol/hle_task_ids.json').read_text())['task_ids'])
    assert {row['id'] for row in hle} == expected_hle
    index = {'hle_question_sha256': defaultdict(list),
             'terminal_instruction_sha256': defaultdict(list)}
    for row in hle:
        index['hle_question_sha256'][fingerprint(row['question'])].append(row['id'])

    manifest_path = root / 'artifacts/preflight/swe_tb/task_image_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    terminal_files = []
    for task in manifest:
        if task['benchmark'] != 'terminal_bench_2':
            continue
        path = root / task['task_path'] / 'instruction.md'
        text = path.read_text()
        index['terminal_instruction_sha256'][fingerprint(text)].append(path.parent.name)
        terminal_files.append({'task_id': path.parent.name,
                               'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    assert len(terminal_files) == 89
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index_path = args.output_dir / 'index.json'
    index_path.write_text(json.dumps(index, indent=2) + '\n')
    index_path.chmod(0o600)
    report = {
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'exclusion only; no answers, rationale, patches, tests or task execution',
        'normalization': "NFKC -> collapse Unicode whitespace -> strip -> casefold -> SHA256 UTF-8",
        'hle': {'revision': HLE_REVISION, 'file_sha256': hle_sha,
                'columns': ['id', 'question'], 'rows': len(hle),
                'unique_question_hashes': len(index['hle_question_sha256'])},
        'terminal': {'task_count': len(terminal_files),
                     'unique_instruction_hashes': len(index['terminal_instruction_sha256']),
                     'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
        'index_sha256': hashlib.sha256(index_path.read_bytes()).hexdigest(),
        'index_location': str(index_path.relative_to(root)),
        'limits': ['Exact normalized full-input equality only; embedded prompts, paraphrases, '
                   'images and source-lineage overlap are not ruled out by zero matches.',
                   'No final training or validation split is created.'],
    }
    (args.output_dir / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
