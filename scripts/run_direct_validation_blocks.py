"""Run validation in adapter blocks after the dedicated service is accepted."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main(args):
    root, output = args.project.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    def cancelled():
        return (output / 'STOP_ADMISSION').exists() or (output / 'CANCELLED_BY_USER.json').exists()
    if cancelled():
        print('Independent validation cancelled by user; no blocks launched', flush=True)
        return
    while not args.ready_file.is_file():
        if cancelled():
            return
        print('Waiting for the dedicated service acceptance receipt', flush=True)
        time.sleep(15)
    hle = root / 'artifacts/data/candidates/hle_existing_2k_20261016/swift_ready/val.tasks.jsonl'
    asi = root / 'artifacts/data/candidates/asi_sft_expanded_20261016/val.tasks.jsonl'
    blocks = [('base_hle', 'hle', 'apex-val-base', hle),
              ('base_asi', 'asi', 'apex-val-base', asi),
              ('hle16', 'hle', 'apex-val-hle16', hle),
              ('hle250', 'hle', 'apex-val-hle250', hle),
              ('asi128', 'asi', 'apex-val-asi128', asi)]
    for label, kind, model, tasks in blocks:
        if cancelled():
            return
        command = [sys.executable, str(root / 'scripts/run_direct_validation.py'),
                   '--project=' + str(root), '--kind=' + kind, '--tasks=' + str(tasks),
                   '--endpoint=' + args.endpoint, '--key-file=' + str(args.key_file),
                   '--model=' + model, '--output=' + str(output / label), '--parallel=8']
        print(json.dumps({'block': label, 'state': 'starting'}), flush=True)
        with (output / (label + '.log')).open('a') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        print(json.dumps({'block': label, 'state': 'generation_finished'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--endpoint', default='http://127.0.0.1:28089')
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--ready-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args())
