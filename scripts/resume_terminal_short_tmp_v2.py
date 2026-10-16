"""Continue zero-model namespace setup on a short /data Unix-socket path."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl
import json
import os
import shutil
import subprocess

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
RUN = ROOT / 'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT = ROOT / 'artifacts/results/base-terminal-v2-recovery-20261016'
LEAF = RUN / 'runtime10'
lock = (ROOT / 'artifacts/runs/base-terminal-724242.lock').open('a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
checkpoint = json.loads((OUT / 'checkpoint.json').read_text())
manifest = json.loads((RUN / 'runtime9/manifest.json').read_text())
entries = {entry['key']: entry for entry in manifest['entries']}
retry = []
for key, status in checkpoint['statuses'].items():
    if status['state'] != 'failed_attempt' or not status.get('result_path'):
        continue
    path = Path(status['result_path'])
    result = json.loads(path.read_text())
    exception = result.get('exception_info') or {}
    if exception.get('exception_message') != 'Namespace relay exited':
        continue
    if result.get('agent_execution') is not None or result.get('agent_result') is not None:
        raise ValueError('setup recovery requires no model execution')
    entry = entries[key]
    entry.update(physical_setup_suffix='__shorttmp1', retained_zero_model_setup_result=str(path))
    retry.append({'key': key, 'manual_attempt': entry['manual_attempt'],
                  'physical_setup_failure': str(path), 'model_execution_started': False})
if len(retry) != 378:
    raise ValueError('unexpected zero-model setup failure selection')
LEAF.mkdir(exist_ok=False)
shutil.copytree(RUN / 'runtime9/scripts', LEAF / 'scripts')
shutil.copy2(RUN / 'runtime9/ENABLE_SECOND_REPLICA', LEAF / 'ENABLE_SECOND_REPLICA')
driver = LEAF / 'scripts/run_terminal_native7.py'
source = driver.read_text().replace(
    'return f"{entry[\'task_id\']}__seed{entry[\'seed\']}__{label}"',
    'return f"{entry[\'task_id\']}__seed{entry[\'seed\']}__{label}" + entry.get("physical_setup_suffix", "")')
source = source.replace("exception = result.get('exception_info') or {}\n                    status['unscored_reason']", 
    "exception = result.get('exception_info') or {}\n                    if result.get('agent_execution') is None and any(reason in exception.get('exception_message', '') for reason in ('No space left on device', 'Namespace relay exited')):\n                        args.stop_admission_file.write_text(exception.get('exception_message', '') + '\\n')\n                    status['unscored_reason']")
driver.write_text(source)
shutil.copy2(OUT / 'checkpoint.json', LEAF / 'checkpoint-before-resume.json')
manifest.update(entries=list(entries.values()), physical_setup_recovery=retry,
                policy='same solver manual attempt; zero-model physical setup suffix; retain all results')
(LEAF / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for item in retry:
    checkpoint['statuses'][item['key']].update(state='pending', physical_setup_suffix='__shorttmp1',
        retained_zero_model_setup_result=item['physical_setup_failure'])
temporary = OUT / 'checkpoint.tmp'
temporary.write_text(json.dumps(checkpoint, indent=2) + '\n')
temporary.replace(OUT / 'checkpoint.json')
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
argv = [str(ROOT / 'artifacts/envs/harbor/bin/python'), str(driver),
    '--manifest', str(LEAF / 'manifest.json'), '--output', str(OUT),
    '--endpoint', 'http://127.0.0.1:28082', '--api-key-path', str(ROOT / 'artifacts/private/base_smoke_api_key'),
    '--concurrency', '16', '--resume-after-bridge-approval',
    '--stop-admission-file', str(LEAF / 'STOP_ADMISSION')]
with (RUN / 'runner-native10.log').open('ab', buffering=0) as stream:
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stream,
        stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
receipt = {'launched_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': child.pid,
    'argv': argv, 'pending_admissions': len(retry), 'max_solver_futures': 30,
    'tmpdir': str(task_tmp), 'disk_available_bytes': shutil.disk_usage(task_tmp).free,
    'physical_setup_failures_selected': retry, 'complete_answers_regenerated': 0,
    'additional_model_manual_attempts': 0, 'prior_results_retained': True}
(RUN / 'launch-native10.json').write_text(json.dumps(receipt, indent=2) + '\n')
(RUN / 'pid-native10').write_text(str(child.pid) + '\n')
print(json.dumps({key: value for key, value in receipt.items() if key not in ('argv', 'physical_setup_failures_selected')}))
