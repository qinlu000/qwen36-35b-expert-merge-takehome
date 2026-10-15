"""Keep this workflow's two SSH forwarding processes alive; no model retries."""
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
    config = json.loads(args.config.read_text())
    common = ['ssh', '-NT', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
              '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
              '-o', 'ExitOnForwardFailure=yes', '-o', 'ControlPersist=no',
              '-o', 'ProxyCommand=none', '-o', 'ProxyJump=none']
    commands = {}
    for side, host, mode in [('hpc', config['hpc_host'], '-L'),
                             ('runner', config['runner_host'], '-R')]:
        command = common + ['-M', '-S', config[side + '_socket']]
        for worker in config['workers']:
            port = worker['bridge_port']
            destination = (f"{worker['node']}:{worker['service_port']}"
                           if side == 'hpc' else f'127.0.0.1:{port}')
            command += [mode, f'127.0.0.1:{port}:{destination}']
        commands[side] = command + [host]
    children = {}
    logs = {side: (args.state_dir / (side + '.log')).open('a') for side in commands}
    restarts = {side: 0 for side in commands}
    last_exit = {}
    next_start = {side: 0.0 for side in commands}
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    try:
        while not stopped:
            for side, command in commands.items():
                child = children.get(side)
                if child is not None and child.poll() is not None:
                    last_exit[side] = {'code': child.returncode,
                                       'at': datetime.now(timezone.utc).isoformat()}
                    del children[side]
                    next_start[side] = time.monotonic() + 5
                if side not in children and time.monotonic() >= next_start[side]:
                    children[side] = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                                      stdout=logs[side], stderr=logs[side])
                    restarts[side] += 1
            state = {'at': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                     'config': str(args.config.resolve()), 'starts': restarts,
                     'last_exit': last_exit,
                     'children': {side: child.pid for side, child in children.items()},
                     'note': 'SSH liveness only; runners must gate admission on HTTP health.'}
            temporary = args.state_dir / 'state.json.tmp'
            temporary.write_text(json.dumps(state, indent=2) + '\n')
            temporary.replace(args.state_dir / 'state.json')
            time.sleep(2)
    finally:
        for child in children.values():
            child.terminate()
        for child in children.values():
            try:
                child.wait(timeout=12)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for log in logs.values():
            log.close()


if __name__ == '__main__':
    main()
