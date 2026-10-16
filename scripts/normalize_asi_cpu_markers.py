"""Add a derived CPU-release bool to two completed ASI producer receipts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time


MARKERS = [
    'artifacts/eval/asi128_asi240_20261017/all_cpu_consumers_finished.json',
    'artifacts/eval/avg64_asi240_20261017/all_cpu_consumers_finished.json',
]


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize_marker(root, relative, receipts):
    marker = root / relative
    if not marker.is_file():
        return None
    original = marker.read_text()
    data = json.loads(original)
    ready = (data.get('state') == 'finished'
             and data.get('generation_worker_pool_shutdown') is True
             and data.get('grader_process_finished') is True
             and data.get('active_program_scopes') == []
             and data.get('generation_conditions') == 240)
    if not ready:
        return None
    # The producer writes this final receipt once, using atomic replace.
    # Keep the exact original text and avoid replacing a changed source.
    if marker.read_text() != original:
        return None
    receipts.mkdir(parents=True, exist_ok=True)
    snapshot = receipts / (marker.parent.name + '.original.json')
    snapshot.write_text(original)
    normalized_at = now()
    data['all_cpu_consumers_finished'] = True
    data['normalized_at'] = normalized_at
    data['normalization_source'] = {
        'script': 'scripts/normalize_asi_cpu_markers.py',
        'reason': 'Derived synonymous bool for already-running Terminal expansion gates.',
        'required_original_fields': {
            'state': 'finished', 'generation_worker_pool_shutdown': True,
            'grader_process_finished': True, 'active_program_scopes': [],
            'generation_conditions': 240,
        },
        'original_snapshot': str(snapshot.relative_to(root)),
    }
    temporary = marker.with_name('.all_cpu_consumers_finished.normalizer.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(marker)
    return {'source': relative, 'original_snapshot': str(snapshot.relative_to(root)),
            'normalized_at': normalized_at, 'original_at_utc': data.get('at_utc'),
            'all_cpu_consumers_finished': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    receipts = root / 'artifacts/eval/asi-cpu-marker-normalization-20261017'
    pending = list(MARKERS)
    completed = []
    print(json.dumps({'state': 'waiting_for_producer_final_markers', 'markers': pending,
                      'at': now()}), flush=True)
    while pending:
        for relative in list(pending):
            result = normalize_marker(root, relative, receipts)
            if result is not None:
                completed.append(result)
                pending.remove(relative)
                receipt = {'state': 'finished' if not pending else 'waiting_for_other_marker',
                           'at': now(), 'normalized': completed, 'pending': pending}
                temporary = receipts / 'receipt.tmp'
                temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
                temporary.replace(receipts / 'receipt.json')
                print(json.dumps(result), flush=True)
        if pending:
            time.sleep(10)
    print(json.dumps({'state': 'finished', 'at': now()}), flush=True)


if __name__ == '__main__':
    main()
