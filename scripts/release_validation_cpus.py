"""Release validation CPU pools once the current Terminal runtime has fully drained."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def base_scopes(cpus):
    busy = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            scope = (process / 'cgroup').read_text()
            if 'apex-baseline-' in scope and cpus.intersection(os.sched_getaffinity(int(process.name))):
                busy.add(scope.strip().split('/')[-1])
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return sorted(busy)


def readiness(root):
    repair = root / 'artifacts/results/base-terminal-independent-repair32-20261016'
    original = root / 'artifacts/results/base-terminal-v2-recovery-20261016/checkpoint.json'
    handoff = repair / 'cpu-handoff.json'
    finished = repair / 'model-consumer-finished.json'
    checkpoint = repair / 'checkpoint.json'
    transferred = root / 'artifacts/runs/base-terminal-recovery-v2-20261016/model-consumers/terminal-seq20-current-manifest-finished.json'
    required = [handoff, finished, checkpoint, original, transferred]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return {'ready': False, 'waiting_for': missing}
    h, f, c, o, t = [json.loads(path.read_text()) for path in required]
    drained = (h['original_queue_active'] == 0 and f.get('model_consumer_finished') is True
               and c.get('active') == {} and c.get('pending') == []
               and t.get('new_output') == str(repair)
               and not any(row['state'] == 'admitted' for row in o['statuses'].values()))
    busy = base_scopes(set(range(120)))
    return {'ready': drained and not busy, 'queues_drained': drained, 'busy_base_scopes': busy,
            'repair_expected': c.get('expected'), 'repair_valid_scored': c.get('valid_scored')}


def main(args):
    output = args.project / 'artifacts/eval/validation_direct_20261016'
    output.mkdir(parents=True, exist_ok=True)
    previous, stable = None, 0
    while True:
        state = readiness(args.project)
        stable = stable + 1 if state['ready'] else 0
        record = dict(state, pid=os.getpid(), updated_at_utc=datetime.now(timezone.utc).isoformat(),
                      consecutive_ready_checks=stable)
        save(output / 'cpu_release_state.json', record)
        if state != previous:
            print(json.dumps(record), flush=True)
            previous = state
        if stable >= 2:
            record.update(ready=True, cpu_consumers_finished=True, cpus=list(range(120)),
                          swe_cpus=list(range(16)), sab_cpus=[112, 113, 114, 115])
            save(output / 'shared_cpu_ready.json', record)
            save(output / 'sab_cpu_ready.json', dict(record, cpus=record['sab_cpus']))
            return
        time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    main(parser.parse_args())
