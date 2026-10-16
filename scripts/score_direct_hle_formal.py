"""Use the unchanged frozen HLE scorer with the per-model formal budget."""
import argparse
import os
from pathlib import Path
from score_hle_baseline_v2_rolling import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--retry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, default=Path('/data/caoqinlu/projects/data-perception/.env'))
    parser.add_argument('--tls-tunnel-port', type=int, default=28443)
    parser.add_argument('--max-cny', type=float, default=20)
    parser.add_argument('--max-calls', type=int, default=5000)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--poll-seconds', type=int, default=30)
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    assert 0 < args.max_cny <= 20 and 0 < args.max_calls <= 5000 and 1 <= args.workers <= 4
    os.umask(0o077)
    run(args)
