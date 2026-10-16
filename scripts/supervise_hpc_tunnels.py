"""Supervise per-worker80-to-HPC SSH forwarding, independently of the laptop."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    lock = (args.state_dir / 'supervisor.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    active, starts, next_start = {}, {}, {}
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, stop)

    def terminate(child):
        child.terminate()
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()

    try:
        while not stopped:
            config = json.loads(args.config.read_text())
            targets = {w['benchmark']: w for w in config['workers']}
            for name in list(active):
                child, worker, log = active[name]
                if name not in targets or targets[name] != worker or child.poll() is not None:
                    if child.poll() is None:
                        terminate(child)
                    log.close()
                    del active[name]
                    next_start[name] = time.monotonic() + 3
            for name, worker in targets.items():
                if name in active or time.monotonic() < next_start.get(name, 0):
                    continue
                command = ['ssh', '-F', '/dev/null', '-NT', '-S', 'none',
                    '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                    '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
                    '-o', 'ConnectTimeout=8', '-o', 'ExitOnForwardFailure=yes',
                    '-o', 'StrictHostKeyChecking=yes',
                    '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
                    '-o', 'UserKnownHostsFile=' + config['known_hosts'],
                    '-i', config['identity_file'],
                    '-L', f"127.0.0.1:{worker['bridge_port']}:{worker['node']}:{worker['service_port']}",
                    config['user'] + '@' + config['host']]
                log = (args.state_dir / (name + '.log')).open('a')
                child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
                active[name] = (child, worker, log)
                starts[name] = starts.get(name, 0) + 1
            state = {'at_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                     'starts': starts, 'workers': {n: {'pid': c.pid, **w} for n, (c, w, _) in active.items()},
                     'note': 'SSH liveness only; solver controllers gate HTTP health independently.'}
            temp = args.state_dir / 'state.json.tmp'
            temp.write_text(json.dumps(state, indent=2) + '\n')
            temp.replace(args.state_dir / 'state.json')
            time.sleep(1)
    finally:
        for child, _, log in active.values():
            terminate(child)
            log.close()


if __name__ == '__main__':
    main()
