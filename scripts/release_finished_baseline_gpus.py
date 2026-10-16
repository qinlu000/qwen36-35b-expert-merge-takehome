"""Remote lifecycle cleanup after native controllers finish, without app scheduling."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    args.state.parent.mkdir(parents=True, exist_ok=True)
    lock = args.state.with_suffix('.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state = json.loads(args.state.read_text()) if args.state.exists() else {'released': {}, 'errors': {}}
    while True:
        config = json.loads(args.config.read_text())
        for worker in config['workers']:
            job = str(worker['job_id'])
            if job in state['released']:
                continue
            path = Path(worker['completion_receipt'])
            if not path.exists():
                continue
            receipt = json.loads(path.read_text())
            if worker['benchmark'] == 'hle':
                finished = receipt.get('state') == 'completed'
            elif worker['benchmark'] == 'terminal':
                final = receipt.get('queue_summary')
                finished = isinstance(final, dict) and final.get('halted') is False and final.get('pending_not_admitted') == 0
            else:
                finished = receipt.get('model_consumer_finished') is True
            if not finished:
                continue
            command = ['ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes',
                '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=8',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
                '-o', 'UserKnownHostsFile=' + config['known_hosts'],
                '-i', config['identity_file'], config['user'] + '@' + config['host'],
                'release ' + job]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            event = {'at_utc': datetime.now(timezone.utc).isoformat(),
                     'completion_receipt': str(path), 'returncode': result.returncode,
                     'output': result.stdout.strip(), 'error': result.stderr.strip()}
            if result.returncode == 0:
                state['released'][job] = event
            else:
                state['errors'][job] = event
            temporary = args.state.with_suffix('.tmp')
            temporary.write_text(json.dumps(state, indent=2) + '\n')
            temporary.replace(args.state)
        if len(state['released']) == len(config['workers']):
            return
        time.sleep(30)


if __name__ == '__main__':
    main()
