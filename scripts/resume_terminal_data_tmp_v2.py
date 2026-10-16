"""Resume only zero-model ENOSPC setup failures, keeping all prior artifacts."""
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
LEAF = RUN / 'runtime9'
lock = (ROOT / 'artifacts/runs/base-terminal-724242.lock').open('a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
checkpoint = json.loads((OUT / 'checkpoint.json').read_text())
manifest = json.loads((RUN / 'runtime8/manifest.json').read_text())
entries = {entry['key']: entry for entry in manifest['entries']}
retry = []
for key, status in checkpoint['statuses'].items():
    if status['state'] != 'failed_attempt' or not status.get('result_path'):
        continue
    path = Path(status['result_path'])
    result = json.loads(path.read_text())
    exception = result.get('exception_info') or {}
    if 'No space left on device' not in exception.get('exception_message', ''):
        continue
    if result.get('agent_execution') is not None or result.get('agent_result') is not None:
        raise ValueError('ENOSPC result has model execution; preserve for separate audit')
    entry = entries[key]
    previous = entry['manual_attempt']
    if previous >= 2:
        raise ValueError('manual infrastructure retry limit reached')
    evidence = {'result_path': str(path), 'exception_type': exception['exception_type'],
                'classification': 'ENOSPC_before_agent_setup_and_zero_model_execution'}
    if previous == 0:
        entry.update(original_result=str(path), prior_manual_attempts=[])
    else:
        entry['prior_manual_attempts'] = [*entry.get('prior_manual_attempts', []), evidence]
    entry.update(manual_attempt=previous + 1,
                 manual_retry_authorization='user authorized infrastructure repair; max2; zero-model setup failure')
    retry.append({'key': key, 'manual_attempt': previous + 1, **evidence})
if not retry:
    raise ValueError('no zero-model setup failures selected')
LEAF.mkdir(exist_ok=False)
shutil.copytree(RUN / 'runtime8/scripts', LEAF / 'scripts')
shutil.copy2(RUN / 'runtime8/ENABLE_SECOND_REPLICA', LEAF / 'ENABLE_SECOND_REPLICA')
shutil.copy2(OUT / 'checkpoint.json', LEAF / 'checkpoint-before-resume.json')
manifest.update(entries=list(entries.values()),
                zero_model_setup_recovery=retry,
                policy='fixed445; rolling; retain complete model answers; zero-model ENOSPC recovery only')
(LEAF / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for item in retry:
    checkpoint['statuses'][item['key']].update(
        state='pending', manual_attempt=item['manual_attempt'],
        retained_prior_result=item['result_path'],
        infrastructure_retry_reason=item['classification'])
temporary = OUT / 'checkpoint.tmp'
temporary.write_text(json.dumps(checkpoint, indent=2) + '\n')
temporary.replace(OUT / 'checkpoint.json')
task_tmp = ROOT / 'artifacts/tmp/terminal-native9'
task_tmp.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PATH'] = ':'.join(str(ROOT / p) for p in [
    'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin',
    'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin']) + ':' + env['PATH']
env['PYTHONPATH'] = ':'.join(map(str, [LEAF / 'scripts', RUN / 'runtime7/scripts',
    RUN / 'runtime3/scripts', ROOT / 'artifacts/runs/base-terminal-724242/runtime2/scripts']))
env.update(APPTAINER_IGNORE_SUBUID='1', PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
           TMPDIR=str(task_tmp), APPTAINER_TMPDIR=str(task_tmp),
           APPTAINER_CACHEDIR=str(ROOT / 'artifacts/cache/apptainer'))
argv = [str(ROOT / 'artifacts/envs/harbor/bin/python'), str(LEAF / 'scripts/run_terminal_native7.py'),
    '--manifest', str(LEAF / 'manifest.json'), '--output', str(OUT),
    '--endpoint', 'http://127.0.0.1:28082', '--api-key-path', str(ROOT / 'artifacts/private/base_smoke_api_key'),
    '--concurrency', '16', '--resume-after-bridge-approval',
    '--stop-admission-file', str(LEAF / 'STOP_ADMISSION')]
with (RUN / 'runner-native9.log').open('ab', buffering=0) as stream:
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stream,
        stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
receipt = {'launched_at_utc': datetime.now(timezone.utc).isoformat(), 'pid': child.pid,
    'argv': argv, 'pending_admissions': len(retry), 'max_solver_futures': 30,
    'tmpdir': str(task_tmp), 'disk_available_bytes': shutil.disk_usage(task_tmp).free,
    'zero_model_setup_failures_selected': retry, 'complete_answers_regenerated': 0,
    'prior_results_retained': True}
(RUN / 'launch-native9.json').write_text(json.dumps(receipt, indent=2) + '\n')
(RUN / 'pid-native9').write_text(str(child.pid) + '\n')
print(json.dumps({key: value for key, value in receipt.items() if key not in ('argv', 'zero_model_setup_failures_selected')}))
