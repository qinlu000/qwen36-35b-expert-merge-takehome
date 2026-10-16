"""Prepare an immutable next leaf; launch only after the existing lock drains."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import time

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
RUN = ROOT / 'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT = ROOT / 'artifacts/results/base-terminal-v2-recovery-20261016'
LEAF = RUN / 'runtime11'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prepare', action='store_true')
parser.add_argument('--launch-after-drain', action='store_true')
args = parser.parse_args()
if args.prepare:
    LEAF.mkdir(exist_ok=False)
    shutil.copytree(RUN / 'runtime10/scripts', LEAF / 'scripts')
    for name in ('run_terminal_routing_v2.py', 'terminal_endpoint_routing_v2.py'):
        shutil.copy2(ROOT / 'scripts' / name, LEAF / 'scripts' / name)
    shutil.copy2(RUN / 'runtime10/manifest.json', LEAF / 'manifest.json')
    shutil.copy2(RUN / 'runtime10/ENABLE_SECOND_REPLICA', LEAF / 'ENABLE_SECOND_REPLICA')
    (LEAF / 'endpoints.json').write_text(json.dumps({'endpoints': []}, indent=2) + '\n')
    (LEAF / 'prepared.json').write_text(json.dumps({
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'previous_runtime': 'runtime10', 'fixed_expected': 445,
        'max_solver_futures': 30, 'requested_model_max_num_seqs': 20,
        'model_manual_attempts_added': 0, 'stop_admission_created': False,
        'policy': 'Never cancel old tasks; root supplies ready endpoints and explicitly starts natural drain'
    }, indent=2) + '\n')
    print('Prepared runtime11; current controller and admissions unchanged.')
if not args.launch_after_drain:
    raise SystemExit(0)
if not any(endpoint['admit'] for endpoint in json.loads((LEAF / 'endpoints.json').read_text())['endpoints']):
    raise ValueError('root must configure a ready model endpoint before arming handoff')
while True:
    lock = (ROOT / 'artifacts/runs/base-terminal-724242.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        lock.close()
        time.sleep(2)
checkpoint = json.loads((OUT / 'checkpoint.json').read_text())
if any(status['state'] == 'admitted' for status in checkpoint['statuses'].values()):
    raise ValueError('old admitted artifacts must be preserved; refuse concurrent handoff')
shutil.copy2(OUT / 'checkpoint.json', LEAF / 'checkpoint-before-handoff.json')
task_tmp = Path('/data/caoqinlu/apex-tb-tmp')
task_tmp.mkdir(exist_ok=True)
env = os.environ.copy()
env['PATH'] = ':'.join(str(ROOT / p) for p in [
    'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin',
    'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin']) + ':' + env['PATH']
env['PYTHONPATH'] = ':'.join(map(str, [LEAF / 'scripts', RUN / 'runtime7/scripts',
    RUN / 'runtime3/scripts', ROOT / 'artifacts/runs/base-terminal-724242/runtime2/scripts']))
env.update(APPTAINER_IGNORE_SUBUID='1', PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
    TMPDIR=str(task_tmp), APPTAINER_TMPDIR=str(task_tmp),
    APPTAINER_CACHEDIR=str(ROOT / 'artifacts/cache/apptainer'))
argv = [str(ROOT / 'artifacts/envs/harbor/bin/python'), str(LEAF / 'scripts/run_terminal_routing_v2.py'),
    '--manifest', str(LEAF / 'manifest.json'), '--output', str(OUT),
    '--endpoint', 'http://127.0.0.1:28082', '--api-key-path', str(ROOT / 'artifacts/private/base_smoke_api_key'),
    '--concurrency', '16', '--resume-after-bridge-approval',
    '--endpoints-config', str(LEAF / 'endpoints.json'), '--stop-admission-file', str(LEAF / 'STOP_ADMISSION')]
with (RUN / 'runner-native11.log').open('ab', buffering=0) as stream:
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stream,
        stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
receipt = {'launched_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': child.pid,
    'argv': argv, 'pending_admissions': sum(status['state'] == 'pending' for status in checkpoint['statuses'].values()),
    'max_solver_futures': 30, 'requested_model_max_num_seqs': 20,
    'original_model_answers_regenerated': 0, 'manual_model_attempts_added': 0,
    'endpoints_config': str(LEAF / 'endpoints.json'),
    'actual_endpoint_profiles_at_launch': json.loads((LEAF / 'endpoints.json').read_text()),
    'tmpdir': str(task_tmp)}
(RUN / 'launch-native11.json').write_text(json.dumps(receipt, indent=2) + '\n')
(RUN / 'pid-native11').write_text(str(child.pid) + '\n')
print(json.dumps({key: value for key, value in receipt.items() if key != 'argv'}))
