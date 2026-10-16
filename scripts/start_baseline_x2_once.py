"""Wait remotely for the x2 allocation and continue full SWE generation when healthy."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--launch-spec', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    out = root / 'artifacts/runs/baseline-x2-725705'
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (out / 'consumer_started.json').exists():
        raise RuntimeError('Consumer admission already recorded; inspect before restarting')
    tunnel_path = root / 'configs/eval/direct_hpc_tunnels_20261016.json'
    config = json.loads(tunnel_path.read_text())
    job = '725705'
    ssh = ['ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
           '-o', 'ConnectTimeout=8', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
           '-o', 'UserKnownHostsFile=' + config['known_hosts'],
           '-i', config['identity_file'], config['user'] + '@' + config['host']]

    def save(state, **extra):
        receipt = {'state': state, 'job_id': job,
                   'at_utc': datetime.now(timezone.utc).isoformat(), **extra}
        temporary = out / 'state.json.tmp'
        temporary.write_text(json.dumps(receipt, indent=2) + '\n')
        temporary.replace(out / 'state.json')
        with (out / 'events.jsonl').open('a') as log:
            log.write(json.dumps(receipt) + '\n')

    def control(action):
        response = subprocess.run(ssh + [action + ' ' + job],
                                  capture_output=True, text=True, timeout=20)
        response.check_returncode()
        return json.loads(response.stdout)

    def remaining(status):
        end = datetime.fromisoformat(status['end_time']).replace(
            tzinfo=timezone(timedelta(hours=8)))
        return (end - datetime.now(timezone.utc)).total_seconds()

    save('waiting_allocation')
    while True:
        try:
            status = control('status')
        except (subprocess.SubprocessError, ValueError):
            save('waiting_status_connection')
            time.sleep(30)
            continue
        if not status.get('status'):
            save('allocation_already_ended')
            return
        if status.get('state') == 'RUNNING':
            break
        save('waiting_allocation', scheduler=status)
        time.sleep(30)
    # Only this new worker is added; existing forwards and active requests stay intact.
    config = json.loads(tunnel_path.read_text())
    worker = {'benchmark': 'swe_x2', 'job_id': int(job), 'node': status['node'],
              'service_port': 18001, 'bridge_port': 28084}
    config['workers'] = [w for w in config['workers'] if w['benchmark'] != 'swe_x2'] + [worker]
    temporary = tunnel_path.with_suffix('.json.x2.tmp')
    temporary.write_text(json.dumps(config, indent=2) + '\n')
    temporary.replace(tunnel_path)
    save('waiting_model_health', worker=worker, synthetic_model_requests=0)
    opener = build_opener(ProxyHandler({}))
    ready_deadline = time.monotonic() + 1200
    while True:
        try:
            with opener.open('http://127.0.0.1:28084/health', timeout=3) as response:
                if response.status == 200:
                    break
        except (URLError, TimeoutError):
            pass
        if time.monotonic() >= ready_deadline:
            save('model_not_ready_no_formal_admission')
            control('release')
            return
        time.sleep(3)
    status = control('status')
    if status.get('state') != 'RUNNING' or remaining(status) < 35 * 60:
        save('insufficient_allocation_margin_no_formal_admission', scheduler=status)
        control('release')
        return
    spec = json.loads(args.launch_spec.read_text())
    # The consumer owns native checkpoints, natural drain and admission of untouched task IDs.
    started = {'at_utc': datetime.now(timezone.utc).isoformat(),
               'launch_spec': str(args.launch_spec), 'argv': spec['argv']}
    (out / 'consumer_started.json').write_text(json.dumps(started, indent=2) + '\n')
    save('launching_formal_consumer', synthetic_model_requests=0)
    with (out / 'consumer.log').open('a') as log:
        child = subprocess.Popen(spec['argv'], cwd=root, stdout=log, stderr=subprocess.STDOUT)
        (out / 'consumer.pid').write_text(str(child.pid) + '\n')
        save('running_formal_consumer', consumer_pid=child.pid,
             launch_spec=str(args.launch_spec), synthetic_model_requests=0)
        code = child.wait()
    if code == 0:
        (out / 'model-consumer-finished.json').write_text(
            json.dumps({'model_consumer_finished': True, 'returncode': code}) + '\n')
        control('release')
        save('consumer_finished_gpu_released', returncode=code)
    else:
        save('consumer_failed_audit_required', returncode=code)


if __name__ == '__main__':
    main()
