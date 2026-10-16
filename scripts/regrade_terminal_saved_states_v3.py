"""One resident native grading queue for preserved Terminal answers; no model calls."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
RUN = ROOT / 'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT = ROOT / 'artifacts/results/base-terminal-v2-recovery-20261016'
RECOVERY = ROOT / 'artifacts/recovery/terminal-v2/saved-final-states'
PRIORITY = ['query-optimize/seed0', 'gpt2-codegolf/seed0',
            'break-filter-js-from-html/seed0', 'mteb-retrieve/seed0']
BLOCKED_RESTORATIONS = {'configure-git-webserver/seed0'}


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    RECOVERY.mkdir(parents=True, exist_ok=True)
    lock = (RECOVERY / 'observer.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = os.environ.copy()
    env['TMPDIR'] = '/data/caoqinlu/apex-tbg-tmp'
    Path(env['TMPDIR']).mkdir(parents=True, exist_ok=True)
    env['PYTHONPATH'] = ':'.join(map(str, [
        RUN / 'runtime10/scripts', RUN / 'runtime8/scripts', RUN / 'runtime7/scripts',
        RUN / 'runtime3/scripts', ROOT / 'artifacts/runs/base-terminal-724242/runtime2/scripts']))
    env['PATH'] = ':'.join(str(ROOT / p) for p in [
        'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin',
        'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin']) + ':' + env['PATH']
    env['APPTAINER_IGNORE_SUBUID'] = '1'
    state = {'pid': os.getpid(), 'new_model_calls': 0, 'cpu_ids': [120, 121, 122, 123],
             'memory_mb': 8192, 'finished': []}
    while not (RUN / 'followon/full445.COMPLETE.json').exists():
        checkpoint = json.loads((OUT / 'checkpoint.json').read_text())
        summary = json.loads((OUT / 'final_summary.json').read_text())
        statuses = checkpoint['statuses']
        keys = sorted(statuses, key=lambda key: (PRIORITY.index(key) if key in PRIORITY else len(PRIORITY), key))
        found = False
        for key in keys:
            status = statuses[key]
            if key in BLOCKED_RESTORATIONS or key in summary['accepted_first_valid'] or status['state'] not in ('verifier_incomplete', 'valid', 'failed_attempt'):
                continue
            original = Path(status.get('result_path', ''))
            if not original.is_file():
                continue
            archive = next(iter(original.parent.glob('artifacts/**/final-task-state.tar')), None)
            if archive is None:
                continue
            label = original.parent.name + '__savedstate2'
            output = OUT / 'rescoring' / label
            if output.exists():
                prior = output / 'result.json'
                if not prior.exists():
                    continue
                failure = (json.loads(prior.read_text()).get('exception_info') or {}).get('exception_message')
                if failure != 'Namespace relay exited':
                    continue
                label = original.parent.name + '__savedstate3'
                output = OUT / 'rescoring' / label
                if output.exists():
                    continue
            work = RECOVERY / label
            work.mkdir(parents=True, exist_ok=True)
            receipt = json.loads(archive.with_suffix('.json').read_text())
            manifest = {
                'files': [{'source': str(archive), 'target': '/staging/saved-final-state.tar'}],
                'commands': [{'command': 'tar -xf /staging/saved-final-state.tar -C /',
                              'source_evidence': str(archive), 'timeout_sec': 180}],
                'reconstructed_from_transcript': False, 'restored_from_pre_verifier_artifact': True,
                'byte_identical': False, 'archived_file_contents_preserved': True,
                'evidence': {'original_result': str(original), 'snapshot': receipt,
                             'scope': 'Archived workdir and explicit output paths; review is required before score acceptance'},
                'new_model_calls': 0}
            restore = work / 'restore.json'
            save(restore, manifest)
            argv = [str(ROOT / 'artifacts/envs/harbor/bin/python'),
                    str(ROOT / 'scripts/run_terminal_grader_only_v4.py'),
                    '--original-result', str(original), '--restore-manifest', str(restore),
                    '--output', str(output), '--cpu-offset', '120']
            with (work / 'grader.log').open('ab', buffering=0) as log:
                child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                state.update(updated_at_utc=datetime.now(timezone.utc).isoformat(),
                             active_key=key, child_pid=child.pid, output=str(output))
                save(RECOVERY / 'resident-state.json', state)
                child.wait()
            review = RECOVERY / 'reviews' / (original.parent.name + '.json')
            if review.exists() and output.exists():
                shutil.copy2(review, output / 'reconstruction-review.json')
            state['finished'].append({'key': key, 'output': str(output), 'exit_code': child.returncode})
            state.update(updated_at_utc=datetime.now(timezone.utc).isoformat(), active_key=None, child_pid=None)
            save(RECOVERY / 'resident-state.json', state)
            found = True
            break
        if not found:
            state.update(updated_at_utc=datetime.now(timezone.utc).isoformat(), active_key=None, child_pid=None)
            save(RECOVERY / 'resident-state.json', state)
            time.sleep(30)


if __name__ == '__main__':
    main()
