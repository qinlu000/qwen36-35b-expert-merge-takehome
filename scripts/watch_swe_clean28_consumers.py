#!/usr/bin/env python3
"""Retain the two shared services until both Terminal and clean SWE finish."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from swe_baseline_v2 import save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal-marker', type=Path, required=True)
    parser.add_argument('--swe-marker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    while True:
        paths = [args.terminal_marker, args.swe_marker]
        if all(path.exists() and json.loads(path.read_text()).get('model_consumer_finished') is True
               for path in paths):
            save_json(args.output, {'model_consumer_finished': True,
                'at_utc': datetime.now(timezone.utc).isoformat(),
                'consumer_markers': list(map(str, paths)), 'cpu_scoring_may_continue': True})
            return
        time.sleep(15)


if __name__ == '__main__':
    main()
