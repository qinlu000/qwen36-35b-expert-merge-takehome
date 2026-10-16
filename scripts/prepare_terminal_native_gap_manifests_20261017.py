#!/usr/bin/env python3
"""Freeze only saved answers whose native verifier lacked dependencies or data."""
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
SOURCE = ROOT / 'artifacts/results/base-terminal-independent-repair32-20261016'
OUT = ROOT / 'artifacts/recovery/terminal-v2/native-gaps-20261017'
MNIST = ROOT / 'artifacts/cache/terminal-verifier-public/mnist/raw'
KEYS = ['train-fasttext/seed3', 'pytorch-model-cli/seed3',
        'train-fasttext/seed4', 'pytorch-model-cli/seed4',
        'make-doom-for-mips/seed3', 'sam-cell-seg/seed3']


def main():
    checkpoint = json.loads((SOURCE / 'checkpoint.json').read_text())
    entries = []
    for key in KEYS:
        row = checkpoint['terminal'][key]
        assert not row['valid']
        original = Path(row['path'])
        archive = original.parent / 'artifacts/logs/artifacts/final-task-state.tar'
        receipt = json.loads(archive.with_suffix('.json').read_text())
        assert receipt['return_code'] == 0 and receipt['captured_before_verifier']
        assert set(receipt['complete_prefixes']) >= {'app', 'etc'}
        task, seed = key.split('/seed')
        label = task + '__seed' + seed
        directory = OUT / 'manifests' / label
        directory.mkdir(parents=True, exist_ok=False)
        manifest = dict(original_result=str(original), files=[{'source': str(archive),
            'target': '/staging/saved-final-state.tar'}], commands=[{
            'command': 'tar -xf /staging/saved-final-state.tar -C /',
            'source_evidence': str(archive), 'timeout_sec': 180}],
            restored_from_pre_verifier_artifact=True, reconstructed_from_transcript=False,
            archived_file_contents_preserved=True, unchanged_candidate_answer=True,
            native_tests_unchanged=True, restore_scope_complete_for_verifier=True,
            original_native_verifier_timeout_seconds=900, new_model_calls=0,
            new_verifier_runs_by_preparation=0, one_additional_verifier_attempt_only=True,
            state_receipt=str(archive.with_suffix('.json')))
        if task == 'pytorch-model-cli':
            for f in sorted(MNIST.iterdir()):
                if f.is_file() and not f.name.endswith('.json'):
                    manifest['files'].append({'source': str(f), 'target': '/staging/mnist/' + f.name})
            manifest['commands'].append({'command': 'mkdir -p /app/data/MNIST/raw && cp /staging/mnist/* /app/data/MNIST/raw/',
                'timeout_sec': 30, 'source_evidence': 'Official tests use MNIST(root=./data, train=False, download=True); public upstream bytes already frozen.'})
        path = directory / 'restore.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        cache_receipt = {'make-doom-for-mips': OUT / 'doom-apt/receipt.json',
                         'sam-cell-seg': OUT / 'sam-cache/receipt.json'}.get(task)
        entries.append({'key': key, 'task_id': task, 'seed': int(seed), 'mode': 'grade_only',
            'original_result': str(original), 'restore_manifest': str(path),
            'cache_receipt': str(cache_receipt) if cache_receipt else None})
    plan = {'plan_id': 'terminal-native-gaps-20261017', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'entries': entries, 'excluded_computation_timeouts': ['feal-differential-cryptanalysis/seed0',
            'feal-differential-cryptanalysis/seed4', 'model-extraction-relu-logits/seed4'],
        'selection': 'All six missing-dependency/public-data verifier failures; retain each original answer.',
        'model_calls': 0, 'cpus': 4, 'memory_mb': 8192, 'native_verifier_seconds': 900,
        'source_summary': str(SOURCE / 'corrected445_summary.json')}
    (OUT / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps({'manifests': len(entries), 'plan': str(OUT / 'plan.json')}))


if __name__ == '__main__':
    main()
