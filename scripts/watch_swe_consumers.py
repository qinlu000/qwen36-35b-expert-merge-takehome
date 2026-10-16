#!/usr/bin/env python3
"""Publish separate permanent model and legacy-CPU completion handoffs."""
import fcntl
import json
import os
from pathlib import Path
import time

from swe_baseline_v2 import ROOT, save_json

BASE = ROOT / 'artifacts/eval'
RUN = ROOT / 'artifacts/runs/swe-base-725705'
FULL = BASE / 'base_swe_v2_20261016_full_x2'
MANUAL = BASE / 'base_swe_v2_20261016_manual_infra1'
FUTURE_SCORE_CPUS = [124]


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def alive(pid, output):
    path = Path('/proc') / str(pid) / 'cmdline'
    return path.exists() and str(output).encode() in path.read_bytes()


def legacy_processes():
    found = []
    needle = str(BASE / 'base_swe_v2_20261016_').encode()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc / 'stat').read_text().rpartition(') ')[2].startswith('Z '):
                continue
            if needle not in (proc / 'mountinfo').read_bytes():
                continue
            cpus = sorted(os.sched_getaffinity(int(proc.name)))
            if set(cpus).intersection(range(64, 120)):
                found.append({'pid': int(proc.name), 'cpus': cpus})
        except OSError as error:
            if error.errno not in (2, 3, 13, 22):
                raise
    return found


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    lock = (RUN / '.swe-consumer-watch.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    closed_since = None
    while True:
        definitions = [(FULL / name, load(FULL / name / 'admission_ids.json'))
                       for name in ['group0', 'group1']]
        definitions.append((MANUAL, load(MANUAL / 'admission_ids.json')))
        checkpoints = [load(root / 'admission_checkpoint.json') for root, _ in definitions]
        ids_ready = all(ids is not None for _, ids in definitions)
        no_pending = all(cp and not cp['pending'] for cp in checkpoints)
        no_infra = all(cp and not cp.get('reason') and cp['state'] != 'paused_infrastructure'
                       for cp in checkpoints)
        pending_relays, unsafe = [], []
        if ids_ready:
            for root, ids in definitions:
                for name in ids:
                    trial = root / 'generation' / name
                    relay = load(trial / 'agent/v2-relay.json')
                    if relay is None:
                        pending_relays.append(name)
                        continue
                    exception = trial / 'exception.txt'
                    error = exception.read_text(errors='replace') if exception.exists() else ''
                    if 'CancelledError' in error:
                        unsafe.append(name + ':cancelled_incomplete')
                    bad_http = any(e['status'] != 200 for e in relay['events'])
                    budget = 'exit 124' in error and 'timeout' in error
                    overflow = False
                    if bad_http and not budget:
                        overflow = any('context_budget_exceeded' in str(load(path).get('error', ''))
                            for path in (root / 'requests' / name).glob('*.json'))
                    cp = checkpoints[[r for r, _ in definitions].index(root)]
                    audited_terminal = cp and cp['state'] == 'finished_available_images'
                    if bad_http and not (budget or overflow or audited_terminal):
                        unsafe.append(name + ':transport_requires_audit')
        models_closed = ids_ready and not pending_relays and not unsafe and no_pending and no_infra
        if models_closed:
            closed_since = closed_since or time.monotonic()
        else:
            closed_since = None
        if (closed_since and time.monotonic() - closed_since >= 10
                and not (RUN / 'model-consumer-finished.json').exists()):
            save_json(RUN / 'model-consumer-finished.json', {
                'model_consumer_finished': True, 'all_relay_end_files': 23,
                'active_model_connections': 0, 'pending_generation': 0,
                'scoring_may_still_be_running': True,
                'confirmation': 'All17+manual6 relay.end files, no pending/infra, stable10seconds',
                'source': 'scripts/watch_swe_consumers.py'})
        terminal = all(cp and cp['state'] == 'finished_available_images'
                       and not cp['active'] and not cp['pending']
                       and len(cp['terminal']) == len(ids)
                       for cp, (_, ids) in zip(checkpoints, definitions)) if ids_ready else False
        main_config = load(FULL / 'controller.json')
        manual_config = load(MANUAL / 'controller.json')
        controllers_done = (main_config and manual_config
            and not alive(main_config['pid'], FULL)
            and not alive(manual_config['pid'], MANUAL))
        remaining = legacy_processes() if terminal and controllers_done else None
        cpu_done = terminal and controllers_done and remaining == []
        if cpu_done:
            save_json(RUN / 'cpu-consumers-finished.json', {
                'cpu_consumers_finished': True, 'legacy_swe_cpu_range': [64, 119],
                'all17_and_manual6_including_scores_terminal': True,
                'pending': 0, 'active': 0, 'remaining_legacy_scope_processes': [],
                'no_future_swe_consumers_on_64_to_119': True,
                'future_patch_score_repair_cpu_ids': FUTURE_SCORE_CPUS,
                'future_patch_score_repair_max_concurrency': len(FUTURE_SCORE_CPUS),
                'source': 'scripts/watch_swe_consumers.py'})
        save_json(RUN / 'swe-consumer-watch.json', {'pid': os.getpid(),
            'state': 'finished' if cpu_done else 'waiting_legacy_cpu' if models_closed else 'waiting_model',
            'model_relay_pending': pending_relays, 'unsafe_infra': unsafe,
            'no_pending': no_pending, 'no_infra': no_infra,
            'all_trials_terminal': terminal, 'controllers_done': bool(controllers_done),
            'legacy_processes': remaining, 'future_score_cpu_ids': FUTURE_SCORE_CPUS})
        if cpu_done:
            return
        time.sleep(5)


if __name__ == '__main__':
    main()
