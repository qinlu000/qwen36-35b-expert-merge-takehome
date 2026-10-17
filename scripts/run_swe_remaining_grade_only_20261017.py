"""Prepare two exact Vuls grades; --execute --item selects one reviewed attempt."""
import argparse
import asyncio
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from swe_baseline_v2 import ROOT
from swe_clean_glibc_runtime import SweCleanGlibcGoRuntimeEnvironment
from run_terminal_native_gap_queue_20261017 import busy_scopes
import patch_replay

ALLOWED = {'swe249/vuls', 'avg64/vuls'}


def production_env():
    tools = ROOT / 'artifacts/tools'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', XDG_RUNTIME_DIR='/run/user/1012',
        DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1012/bus',
        TMPDIR='/data/caoqinlu/apex-swe-grade-only-20261017-tmp',
        PYTHONPATH=':'.join(map(str, [ROOT / 'scripts', ROOT / 'artifacts/benchmarks/swe-bench-pro/v2/tooling',
                                    ROOT / 'artifacts/benchmarks/harbor/src'])),
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env['PATH'] = ':'.join(map(str, [tools / 'apptainer-1.4.5/rootfs/usr/bin', tools / 'fakeroot-1.25.3/rootfs/usr/bin'])) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    return env


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def ticks(pid):
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
    except FileNotFoundError:
        return None


def effective_cpus():
    directory = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/')
    while not (directory / 'cpuset.cpus.effective').exists():
        directory = directory.parent
    cpus = set()
    for part in (directory / 'cpuset.cpus.effective').read_text().strip().split(','):
        ends = [int(value) for value in part.split('-')]
        cpus.update(range(ends[0], ends[-1] + 1))
    return cpus


def terminal_has_lease():
    for name in ('terminal250_full445_20261017', 'avg64_terminal_full445_20261017'):
        output = ROOT / 'artifacts/eval' / name
        if (output / 'cpu-expansion-asi_finished.json').exists():
            return True
        if any(set(range(cpu, cpu + 4)) & set(range(92, 96))
               for cpu in read(output / 'summary.json')['leased_cpu_offsets']):
            return True
    return False


def validate(manifest, item):
    assert item['key'] in ALLOWED and item['enabled'], 'Only the two Vuls entries are implemented'
    assert item['patch_bytes'] == 0
    bindings = {**manifest['code_sha256'], **item['small_file_sha256']}
    assert all(sha(ROOT / path) == expected for path, expected in bindings.items()), 'Frozen input changed'
    original = read(ROOT / item['original_config'])
    result = read(ROOT / item['original_result'])
    assert result['task_checksum'] == item['task_checksum']
    assert result['exception_info']['exception_type'] == 'RemoteProtocolError'
    assert read(ROOT / item['source_output'] / 'generation' / item['task_id'] / 'config.json')['agent']['model_name'] == item['generation_model']
    assert original['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
    assert original['agent']['kwargs']['source_job'] == str(ROOT / item['source_output'] / 'generation')
    assert original['environment']['import_path'] == item['environment_import_path'] == 'swe_clean_glibc_runtime:SweCleanGlibcGoRuntimeEnvironment'
    assert original['environment']['override_cpus'] == manifest['cpus'] == 1
    assert original['environment']['override_memory_mb'] == manifest['memory_mib'] == 4096
    assert original['environment']['override_gpus'] == 0
    assert original['environment']['cpu_enforcement_policy'] == original['environment']['memory_enforcement_policy'] == 'limit'
    assert original['verifier']['override_timeout_sec'] == manifest['verifier_seconds'] == 3000
    assert original['agent']['override_timeout_sec'] == 1800
    image = ROOT / item['sif']
    assert image.stat().st_size == item['sif_size'] and str(image.stat().st_mtime_ns) == item['sif_mtime_ns']
    assert Path(patch_replay.__file__) == ROOT / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/patch_replay.py'
    assert not (ROOT / item['output']).exists(), 'Existing attempt retained; no automatic retry'
    config = copy.deepcopy(original)
    config['trials_dir'] = str(ROOT / item['output'] / 'native')
    config['environment']['import_path'] = 'run_swe_remaining_grade_only_20261017:VulsDiskLogs'
    config['environment']['kwargs'].update(baseline_cpu_offset=0, baseline_cpu_slots=1)
    TrialConfig.model_validate(config)  # Real Harbor schema/import check; no environment is constructed.
    named = importlib.import_module('run_swe_remaining_grade_only_20261017')
    assert Path(named.__file__) == ROOT / 'scripts/run_swe_remaining_grade_only_20261017.py'
    assert issubclass(named.VulsDiskLogs, SweCleanGlibcGoRuntimeEnvironment)
    named.VulsDiskLogs.scratch_root = ROOT / item['output'] / 'scratch'
    assert named.VulsDiskLogs.scratch_root == Path(config['trials_dir']).parent / 'scratch'
    return config, bindings


class VulsDiskLogs(SweCleanGlibcGoRuntimeEnvironment):
    """The existing Base disk/log technique, with a separate scratch/output root."""
    scratch_root = None

    async def _start_server(self):
        self.scratch_root.mkdir(parents=True, exist_ok=True)
        self._scratch = Path(tempfile.mkdtemp(prefix='native-', dir=self.scratch_root))
        self._scratch.chmod(0o755)
        self._mounts.append({'type': 'bind', 'source': str(self._scratch), 'target': '/tmp', 'read_only': False})
        self._logs = Path(next(m['source'] for m in self._mounts if m['target'] == '/logs/verifier'))
        await super()._start_server()
        locations = await super().exec('go env GOCACHE GOMODCACHE', timeout_sec=30)
        assert locations.return_code == 0
        sources = locations.stdout.strip().splitlines()[-2:]
        targets = ['/tmp/apex-native-go-build-cache', '/tmp/apex-native-go-module-cache']
        command = 'set -e; ' + '; '.join('mkdir -p ' + shlex.quote(dst) + '; if [ -d ' + shlex.quote(src) + ' ]; then cp -a ' + shlex.quote(src.rstrip('/') + '/.') + ' ' + shlex.quote(dst) + '; fi' for src, dst in zip(sources, targets))
        copied = await super().exec(command, timeout_sec=1800)
        save(self._logs / 'native-go-disk-cache.json', {'original_caches': sources, 'disk_caches': targets,
             'return_code': copied.return_code, 'stderr': copied.stderr, 'contents_preserved': True})
        assert copied.return_code == 0
        self._persistent_env.update(GOCACHE=targets[0], GOMODCACHE=targets[1])

    async def _tap(self):
        code = """import pathlib,shutil
logs=pathlib.Path('/logs/verifier')
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if b'/tests/run_script.sh' not in (p/'cmdline').read_bytes():continue
  for fd,label in [('1','stdout'),('2','stderr')]:
   source=(p/'fd'/fd).resolve()
   if str(source).startswith('/tmp/') and source.is_file():shutil.copyfile(source,logs/('live-run-script-'+label+'.txt'))
 except OSError:pass
"""
        while True:
            await asyncio.sleep(10)
            try:
                await super().exec('/opt/harbor-server/bin/python3 -c ' + shlex.quote(code), timeout_sec=15)
            except Exception as error:
                save(self._logs / 'live-log-error.json', {'error_type': type(error).__name__})

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' not in command:
            return await super().exec(command, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user)
        tap = asyncio.create_task(self._tap())
        try:
            return await super().exec(command, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user)
        finally:
            tap.cancel()
            await asyncio.gather(tap, return_exceptions=True)

    async def _stop_server_process(self):
        logs = getattr(self, '_logs', None)
        if logs:
            server_log = getattr(self, '_server_log_path', None)
            if server_log and server_log.exists():
                shutil.copy2(server_log, logs / 'repair-server.log')
            scope = getattr(self, '_scope_unit', None)
            if scope:
                group = Path('/sys/fs/cgroup/user.slice/user-' + str(os.getuid()) + '.slice/user@' + str(os.getuid()) + '.service/app.slice/' + scope.removesuffix('.scope') + '.scope')
                save(logs / 'repair-resource-events.json', {name: (group / name).read_text() for name in
                     ['memory.max', 'memory.swap.max', 'memory.events', 'memory.current', 'memory.peak', 'cpu.stat'] if (group / name).exists()})
        return await super()._stop_server_process()


def run(args, manifest, item, config, bindings):
    output = ROOT / item['output']
    lease_path = ROOT / manifest['shared_lock']
    deadline = datetime.fromisoformat(manifest['core_deadline']).timestamp()
    enough_time = lambda: deadline - time.time() >= manifest['minimum_core_runway_seconds']
    assert set(range(92, 96)) <= effective_cpus(), 'Parent cgroup cannot admit CPU92-95'
    assert not terminal_has_lease(), '92-95 already handed to Terminal'
    assert enough_time(), 'Insufficient original-budget core runway'
    output.mkdir(parents=True)
    state = {'pid': os.getpid(), 'startticks': ticks(os.getpid()), 'item': item['key'],
             'state': 'claimed', 'lock_held': False, 'native_started': False, 'model_calls': 0}
    with (output / 'execution-claim.json').open('x') as handle:
        json.dump({**state, 'at_utc': now(), 'script_sha256': sha(Path(__file__)),
                   'manifest_sha256': sha(args.manifest), 'bound_sha256': bindings}, handle, indent=2)

    def checkpoint(label, **fields):
        state.update(state=label, at_utc=now(), **fields)
        save(output / 'parent-state.json', state)

    signal.signal(signal.SIGTERM, lambda *_: state.update(stop_requested=True))
    signal.signal(signal.SIGINT, lambda *_: state.update(stop_requested=True))
    guard, child, unit = None, None, 'apex-baseline-swe-grade-' + str(os.getpid())

    def drain(ignore_guard=False):
        samples = []
        while len(samples) < 2:
            busy = [s for s in busy_scopes() if not (ignore_guard and s == unit + '.scope')]
            samples = [] if busy else samples + [{'at_utc': now(), 'remaining_scopes': []}]
            try:
                checkpoint('draining_native' if ignore_guard else 'draining_after_guard_stop', remaining_scopes=busy)
            except OSError:
                state['checkpoint_write_failed'] = True  # A log failure must not skip resource draining.
            if len(samples) < 2:
                time.sleep(2)
        return samples

    with lease_path.open('a+') as lease:
        while True:
            if not enough_time() or terminal_has_lease() or state.get('stop_requested'):
                checkpoint('stopped_before_native')
                return
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_shared_lease')
                time.sleep(5)
                continue
            if busy_scopes():
                fcntl.flock(lease, fcntl.LOCK_UN)
                checkpoint('waiting_real_cpu_drain')
                time.sleep(5)
                continue
            break
        checkpoint('lease_acquired', lock_held=True)
        try:
            guard = subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
                '-p', 'MemoryMax=33554432', '-p', 'MemorySwapMax=0',
                'taskset', '-c', '92-95', 'sleep', 'infinity'], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=(output / 'guard.log').open('x'),
                env=production_env(), pass_fds=(lease.fileno(),))
            time.sleep(1)
            assert guard.poll() is None
            assert unit + '.scope' in busy_scopes(), 'Visible grader reservation guard missing'
            group = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope',
                                             '--property=ControlGroup', '--value'], text=True, env=production_env()).strip()
            cgroup = Path('/sys/fs/cgroup') / group.lstrip('/')
            affinities = {pid: sorted(os.sched_getaffinity(int(pid))) for pid in (cgroup / 'cgroup.procs').read_text().split()}
            guard_resources = {'unit': unit + '.scope', 'cgroup': group, 'affinities': affinities,
                'memory_max_bytes': int((cgroup / 'memory.max').read_text()),
                'memory_swap_max_bytes': int((cgroup / 'memory.swap.max').read_text())}
            assert affinities and all(cpus == [92, 93, 94, 95] for cpus in affinities.values())
            assert guard_resources['memory_max_bytes'] == 33554432 and guard_resources['memory_swap_max_bytes'] == 0
            checkpoint('guard_verified', guard_observed=guard_resources)
            assert not terminal_has_lease() and not [s for s in busy_scopes() if s != unit + '.scope']
            assert enough_time()
            assert not state.get('stop_requested'), 'Stopped before native admission'
            assert all(sha(ROOT / p) == expected for p, expected in bindings.items())
            checkpoint('native_starting', guard_unit=unit + '.scope')
            command = ['taskset', '-c', '92', str(ROOT / 'artifacts/envs/harbor/bin/python'),
                       str(Path(__file__)), '--manifest', str(args.manifest), '--item', item['key'],
                       '--child', '--lease-fd', str(lease.fileno())]
            with (output / 'child.log').open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, env=production_env(), pass_fds=(lease.fileno(),))
                checkpoint('native_running', native_started=True, child_pid=child.pid,
                           child_startticks=ticks(child.pid), command=command)
                while child.poll() is None:
                    time.sleep(5)
            result_path = output / 'native' / item['task_id'] / 'result.json'
            result = read(result_path) if result_path.exists() else {}
            checkpoint('finished_pending_root_review', child_returncode=child.returncode,
                result=str(result_path),
                native_reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                exception_type=(result.get('exception_info') or {}).get('exception_type'),
                original_bytes_unchanged=all(sha(ROOT / p) == expected for p, expected in bindings.items()),
                accepted_into_formal_summary=False)
        except Exception as error:
            checkpoint('failed_pending_root_review', error_type=type(error).__name__)
            raise
        finally:
            final_state = state['state']
            if child is not None:
                while child.poll() is None:
                    time.sleep(5)  # Even monitor/log errors must preserve the admitted native budget.
            native_samples = drain(ignore_guard=True)
            if guard is not None:
                subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], check=True, env=production_env())
                guard.wait(timeout=10)
            samples = drain()
            assert unit + '.scope' not in busy_scopes()
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint(final_state, lock_held=False, guard_stopped=True,
                       consecutive_empty_native_scope_samples=native_samples,
                       consecutive_empty_scope_samples_after_guard_stop=samples, released_at_utc=now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/swe_remaining_grade_only_20261017.json')
    parser.add_argument('--item')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--lease-fd', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ.update(production_env())
    Path(os.environ['TMPDIR']).mkdir(exist_ok=True)
    args.manifest = args.manifest.resolve()
    manifest = read(args.manifest)
    items = {row['key']: row for row in manifest['items']}
    selected = [items[args.item]] if args.item else [row for row in items.values() if row['enabled']]
    assert set(row['key'] for row in selected) <= ALLOWED
    checks = []
    for item in selected:
        if args.child:
            claim = read(ROOT / item['output'] / 'execution-claim.json')
            assert claim['script_sha256'] == sha(Path(__file__)) and claim['manifest_sha256'] == sha(args.manifest)
            assert ticks(claim['pid']) == claim['startticks']
            assert args.lease_fd is not None and Path('/proc/self/fd/' + str(args.lease_fd)).resolve() == ROOT / manifest['shared_lock']
            assert os.sched_getaffinity(0) == {92}
            # Validate immutable inputs without accepting an existing attempt as a new execution.
            assert all(sha(ROOT / p) == expected for p, expected in claim['bound_sha256'].items())
            config = read(ROOT / item['original_config'])
            config['trials_dir'] = str(ROOT / item['output'] / 'native')
            config['environment']['import_path'] = 'run_swe_remaining_grade_only_20261017:VulsDiskLogs'
            config['environment']['kwargs'].update(baseline_cpu_offset=0, baseline_cpu_slots=1)
            # Harbor imports the named module; the CLI itself is __main__.
            importlib.import_module('run_swe_remaining_grade_only_20261017').VulsDiskLogs.scratch_root = ROOT / item['output'] / 'scratch'
            async def grade():
                trial = await Trial.create(TrialConfig.model_validate(config))
                assert trial.task.checksum == item['task_checksum']
                await trial.run()
            asyncio.run(grade())
            return
        config, bindings = validate(manifest, item)
        checks.append({'item': item['key'], 'input_bindings_verified': len(bindings),
            'native_directory_exists': (ROOT / item['output']).exists(), 'model_calls': 0,
            'cpus': 1, 'memory_mib': 4096, 'verifier_seconds': 3000,
            'physical_cpu_ids': [92], 'logical_cpu_offset': 0})
        if args.execute:
            assert args.item and len(selected) == 1
            run(args, manifest, item, config, bindings)
            return
    receipt = {'at_utc': now(), 'mode': 'prepare_only', 'script_sha256': sha(Path(__file__)),
        'manifest_sha256': sha(args.manifest), 'checks': checks, 'execution_claim_created': False,
        'native_started': False, 'model_calls': 0, 'shared_lock_acquired': False,
        'terminal_has_92_95_lease': terminal_has_lease(), 'current_busy_scopes92_95': busy_scopes(),
        'parent_effective_cgroup_cpus': sorted(effective_cpus()),
        'patch_replay_origin': patch_replay.__file__, 'python_lexical': sys.executable,
        'named_environment_module': str(ROOT / 'scripts/run_swe_remaining_grade_only_20261017.py'),
        'named_environment_scratch_binding_checked': True,
        'production_environment': {key: os.environ[key] for key in ['PATH', 'PYTHONPATH', 'TMPDIR',
            'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']},
        'oom_or_transport_repair_proven': False}
    save(ROOT / manifest['output'] / 'preparation.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
