"""Replay three frozen Base patches with disk-backed scratch and live verifier logs."""
import argparse
import asyncio
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from collect_swe_final import score
from release_validation_cpus import base_scopes
from swe_baseline_v2 import ROOT, save_json
from swe_clean_glibc_runtime import SweCleanGlibcRuntimeEnvironment, SweCleanGlibcGoRuntimeEnvironment
from swe_clean_musl_runtime import SweCleanMuslScoreEnvironment


SOURCE = ROOT / 'artifacts/eval/base_swe_v2_20261016_clean28'
OUTPUT = ROOT / 'artifacts/eval/base_swe_gap_repair_20261017'
TASKS = {
    'vuls': ('instance_future-architect__vuls-5af1a227339e46c7abf3f2815e4c636a0c01098e', 'BaseGlibcGoRepair'),
    'teleport': ('instance_gravitational__teleport-2b15263e49da5625922581569834eec4838a9257-vee9b09fb20c43af7e520f57e9239bbcf46b7113d', 'BaseMuslRepair'),
    'nodebb': ('instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e', 'BaseGlibcRepair'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def other_scopes(cpu):
    guard = OUTPUT / 'lease-scope-guard.json'
    own = json.loads(guard.read_text())['unit'] + '.scope' if guard.exists() else None
    return [scope for scope in base_scopes({cpu}) if scope != own and
            not scope.startswith('apex-baseline-final-collector-')]


class DiskScratchAndLogs:
    async def _start_server(self):
        scratch = Path('/data/caoqinlu/apex-base-swe-repair-tmp')
        scratch.mkdir(exist_ok=True)
        self._repair_scratch = Path(tempfile.mkdtemp(prefix='native-', dir=scratch))
        self._repair_scratch.chmod(0o755)
        self._mounts.append({'type': 'bind', 'source': str(self._repair_scratch),
                             'target': '/tmp', 'read_only': False})
        await super()._start_server()
        self._repair_logs = Path(next(m['source'] for m in self._mounts
                                     if m['target'] == '/logs/verifier'))
        context = await super().exec('df -h /tmp /dev/shm; ulimit -n; '
                                     'printf "\\nPATH=%s\\n" "$PATH"', timeout_sec=20)
        save_json(self._repair_logs / 'repair-runtime.json', {
            'at': now(), 'scratch': str(self._repair_scratch), 'scope': self._scope_unit,
            'cpus': 1, 'memory_mib': 4096, 'verifier_seconds': 3000,
            'model_calls': 0, 'context': context.stdout, 'stderr': context.stderr,
            'return_code': context.return_code})
        native = await super().exec('command -v go >/dev/null 2>&1 && go env GOCACHE GOMODCACHE',
                                    timeout_sec=30)
        if native.return_code == 0:
            build_cache, module_cache = native.stdout.strip().splitlines()[-2:]
            targets = ['/tmp/apex-native-go-build-cache', '/tmp/apex-native-go-module-cache']
            command = 'set -e; ' + '; '.join(
                'mkdir -p ' + shlex.quote(destination) + '; if [ -d ' + shlex.quote(source) +
                ' ]; then cp -a ' + shlex.quote(source.rstrip('/') + '/.') + ' ' +
                shlex.quote(destination) + '; fi'
                for source, destination in zip([build_cache, module_cache], targets))
            copied = await super().exec(command, timeout_sec=1800)
            save_json(self._repair_logs / 'native-go-disk-cache.json', {
                'original_caches': [build_cache, module_cache], 'disk_caches': targets,
                'return_code': copied.return_code, 'stderr': copied.stderr,
                'original_cache_contents_preserved': True})
            assert copied.return_code == 0, 'Native Go cache disk copy failed'
            self._persistent_env.update(GOCACHE=targets[0], GOMODCACHE=targets[1])

    async def _stop_server_process(self):
        logs = getattr(self, '_repair_logs', None)
        if logs:
            server_log = getattr(self, '_server_log_path', None)
            if server_log and server_log.exists():
                shutil.copy2(server_log, logs / 'repair-server.log')
            scope = getattr(self, '_scope_unit', None)
            if scope:
                cgroup = Path(f'/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{scope}.scope')
                events = {name: (cgroup / name).read_text() for name in
                          ['memory.events', 'memory.current', 'memory.peak', 'cpu.stat']
                          if (cgroup / name).exists()}
                save_json(logs / 'repair-resource-events.json', events)
        return await super()._stop_server_process()

    async def _tap(self):
        code = '''import json,pathlib,shutil
logs=pathlib.Path('/logs/verifier')
seen=[]
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  command=(process/'cmdline').read_bytes()
  if b'/tests/run_script.sh' not in command:continue
  row={'pid':int(process.name),'command':command.replace(b'\\0',b' ').decode(errors='replace')[:200]}
  for fd,label in [('1','stdout'),('2','stderr')]:
   source=(process/'fd'/fd).resolve()
   if str(source).startswith('/tmp/') and source.is_file():
    shutil.copyfile(source,logs/('live-run-script-'+label+'.txt'))
    row[label]=str(source)
  seen.append(row)
 except (OSError,ValueError):pass
(logs/'live-processes.json').write_text(json.dumps(seen))
'''
        command = '/opt/harbor-server/bin/python3 -c ' + shlex.quote(code)
        while True:
            await asyncio.sleep(10)
            try:
                await super().exec(command, timeout_sec=15)
            except Exception as error:
                (self._repair_logs / 'live-log-error.txt').write_text(type(error).__name__)

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' not in command:
            return await super().exec(command, cwd=cwd, env=env,
                                      timeout_sec=timeout_sec, user=user)
        tap = asyncio.create_task(self._tap())
        try:
            return await super().exec(command, cwd=cwd, env=env,
                                      timeout_sec=timeout_sec, user=user)
        finally:
            tap.cancel()
            await asyncio.gather(tap, return_exceptions=True)


class BaseGlibcRepair(DiskScratchAndLogs, SweCleanGlibcRuntimeEnvironment):
    pass


class BaseGlibcGoRepair(DiskScratchAndLogs, SweCleanGlibcGoRuntimeEnvironment):
    pass


class BaseMuslRepair(DiskScratchAndLogs, SweCleanMuslScoreEnvironment):
    pass


async def replay(name, cpu, replay_subdir):
    task, environment = TASKS[name]
    musl_shim = ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim'
    if name == 'teleport':
        assert (musl_shim / 'singularity').exists(), 'Missing original musl cohort shim'
        os.environ['PATH'] = str(musl_shim) + ':' + os.environ['PATH']
    assert not other_scopes(cpu), f'CPU {cpu} already leased'
    destination = OUTPUT / replay_subdir / task
    assert not destination.exists(), 'Previous attempt preserved; do not rerun completed answers'
    config = json.loads((SOURCE / 'replay' / task / 'config.json').read_text())
    assert config['environment']['override_cpus'] == 1
    assert config['environment']['override_memory_mb'] == 4096
    assert config['verifier']['override_timeout_sec'] == 3000
    assert config['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
    assert config['agent']['kwargs']['source_job'] == str(SOURCE / 'generation')
    config['trials_dir'] = str(OUTPUT / replay_subdir)
    config['environment']['kwargs'].update(baseline_cpu_offset=cpu, baseline_cpu_slots=1)
    config['environment']['import_path'] = 'repair_base_swe_gaps_20261017:' + environment
    patch = SOURCE / 'generation' / task / 'agent/model.patch'
    original = patch.read_bytes()
    save_json(OUTPUT / 'audit' / (name + '.started.json'), {
        'at': now(), 'task_id': task, 'cpu': cpu, 'source_patch': str(patch),
        'patch_bytes': len(original), 'original_result': str(SOURCE / 'replay' / task / 'result.json'),
        'source_task_unchanged': True, 'model_calls': 0, 'controller_pid': os.getpid(),
        'launcher_path': os.environ['PATH'], 'command_line': sys.argv,
        'musl_shim': str(musl_shim) if name == 'teleport' else None})
    trial = await Trial.create(TrialConfig.model_validate(config))
    result = await trial.run()
    assert patch.read_bytes() == original
    scored = score(destination / 'result.json')
    save_json(OUTPUT / 'audit' / (name + '.finished.json'), {
        'at': now(), **scored, 'patch_unchanged': True, 'model_calls': 0,
        'active_scopes_after': base_scopes({cpu}),
        'exception_type': result.exception_info.exception_type if result.exception_info else None})


async def main(args):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.wait_pid:
        while Path(f'/proc/{args.wait_pid}').exists():
            await asyncio.sleep(2)
    lock = (OUTPUT / (f'.cpu{args.cpu}.lock')).open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for name in args.task:
        task = TASKS[name][0]
        if (OUTPUT / args.replay_subdir / task / 'result.json').exists():
            continue
        await replay(name, args.cpu, args.replay_subdir)
    assert not other_scopes(args.cpu), 'Native replay scope has not drained'
    if args.worker:
        save_json(OUTPUT / f'cpu{args.cpu}-finished.json', {
            'at': now(), 'tasks': args.task, 'model_calls': 0, 'pid': os.getpid(),
            'active_scopes_after': base_scopes({args.cpu}), 'cpu_consumers_finished': True})
        return
    latest = [json.loads((OUTPUT / 'audit' / (name + '.finished.json')).read_text())
              for name in args.task]
    if any(row['invalid_reason'] for row in latest):
        save_json(OUTPUT / 'infrastructure-attempt-waiting-repair.json', {
            'at': now(), 'scope_consumers_drained': True, 'guard_retained': True,
            'attempts': latest, 'model_calls': 0})
        return
    guard = OUTPUT / 'lease-scope-guard.json'
    if guard.exists():
        unit = json.loads(guard.read_text())['unit']
        subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], check=True)
    lease = json.loads((OUTPUT / 'cpu11-lease.json').read_text())
    lease.update(all_cpu_consumers_finished=True, finished_at=now())
    save_json(OUTPUT / 'cpu11-lease.json', lease)
    save_json(OUTPUT / f'cpu{args.cpu}-finished.json', {
        'at': now(), 'tasks': args.task, 'model_calls': 0, 'pid': os.getpid(),
        'active_scopes_after': base_scopes({args.cpu}), 'all_cpu_consumers_finished': True})
    receipts = {name: json.loads((OUTPUT / 'audit' / (name + '.finished.json')).read_text())
                if (OUTPUT / 'audit' / (name + '.finished.json')).exists() else None
                for name in TASKS}
    save_json(OUTPUT / 'all_cpu_consumers_finished.json', {
        'at': now(), 'all_cpu_consumers_finished': True, 'cpu_consumers_finished': True,
        'new_model_calls': 0, 'native_receipts': receipts,
        'candidate_failure_audits': str(OUTPUT / 'candidate-failure-audits.json'),
        'guard_stopped': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', action='append', choices=TASKS, required=True)
    parser.add_argument('--cpu', type=int, required=True)
    parser.add_argument('--wait-pid', type=int)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--replay-subdir', default='replay')
    asyncio.run(main(parser.parse_args()))
