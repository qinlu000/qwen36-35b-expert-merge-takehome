#!/usr/bin/env python3
"""Remove audited, unused verifier dependency copies; retain original task state."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--phase', choices=['root_tmp', 'data_verifier'], default='root_tmp')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    volume = '/tmp' if args.phase == 'root_tmp' else '/data'
    live = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc / 'cmdline').read_bytes()
            if b'_hbexec.py' in command:
                live.append((proc / 'mountinfo').read_text())
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    receipt = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'free_metrics_volume': volume,
        'free_before': shutil.disk_usage(volume).free, 'deleted': [], 'skipped': [],
        'retained': 'All parent staging state archives/logs and original runs; all live mounts'}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    items = plan['delete_paths'] if args.phase == 'root_tmp' else plan['phase2_verifier_assets']['candidates']
    for item in items:
        path = Path(item if isinstance(item, str) else item[0] if isinstance(item, list) else item['path'])
        assert path.name == 'verifier_assets'
        if args.phase == 'root_tmp':
            assert path.parent.parent == Path('/tmp')
        else:
            assert str(path.parent.parent).startswith('/data/caoqinlu/apex-')
        assert path.parent.name.startswith('apex_baseline_staging_')
        if not path.exists():
            receipt['skipped'].append({'path': str(path), 'reason': 'already_absent'})
        elif path.is_symlink() or path.stat().st_uid != os.getuid():
            receipt['skipped'].append({'path': str(path), 'reason': 'not_owned_plain_directory'})
        elif any(str(path.parent) in mount for mount in live):
            receipt['skipped'].append({'path': str(path), 'reason': 'live_mount'})
        else:
            shutil.rmtree(path)
            receipt['deleted'].append(str(path))
        receipt['free_after'] = shutil.disk_usage(volume).free
        temporary = args.receipt.with_suffix('.tmp')
        temporary.write_text(json.dumps(receipt, indent=2) + '\n')
        temporary.replace(args.receipt)
        print(json.dumps({'deleted': len(receipt['deleted']), 'skipped': len(receipt['skipped']),
            'free_gib': receipt['free_after'] / 1024**3}), flush=True)
    receipt['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
