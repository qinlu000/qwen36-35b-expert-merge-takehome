"""Three exact saved-answer SWE grades; default preparation never starts native work."""
import argparse
import asyncio
import copy
from datetime import datetime
import fcntl
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
from swe_clean_glibc_runtime import SweCleanGlibcRuntimeEnvironment
from swe_clean_musl_runtime import SweCleanMuslScoreEnvironment
# Frozen a0eb0e pure helpers only; never call its Vuls run/main or mutate its classes.
from run_swe_remaining_grade_only_20261017 import (
    ROOT, now, read, sha, save, ticks, effective_cpus, terminal_has_lease, busy_scopes,
    production_env as frozen_production_env)
import patch_replay

ALLOWED = {'swe249/nodebb', 'swe249/teleport2b', 'avg64/teleport2b'}
MODULE = 'run_swe_additional_grade_only_20261017'


def production_env(item):
    env = frozen_production_env()
    env['TMPDIR'] = item['host_tmp']
    if item['cohort'] == 'musl':
        env['PATH'] = str(ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim') + ':' + env['PATH']
    return env


def configured(item):
    config = copy.deepcopy(read(ROOT / item['original_config']))
    config['trials_dir'] = str(ROOT / item['output'] / 'native')
    config['environment']['import_path'] = MODULE + ':' + item['new_environment_class']
    config['environment']['kwargs'].update(baseline_cpu_offset=0, baseline_cpu_slots=1)
    return config


def bind_named_class(item):
    named = importlib.import_module(MODULE)
    assert Path(named.__file__) == ROOT / 'scripts' / (MODULE + '.py')
    cls = getattr(named, item['new_environment_class'])
    expected = SweCleanMuslScoreEnvironment if item['cohort'] == 'musl' else SweCleanGlibcRuntimeEnvironment
    assert issubclass(cls, expected) and issubclass(cls, named.DiskScratchAndLogs)
    cls.scratch_root = ROOT / item['output'] / 'scratch'
    assert cls.scratch_root == Path(configured(item)['trials_dir']).parent / 'scratch'


def validate(manifest, item):
    assert item['key'] in ALLOWED and item['enabled'], 'Not one of the three approved preparation entries'
    bindings = {**manifest['code_sha256'], **item['small_file_sha256']}
    assert all(sha(ROOT / p) == expected for p, expected in bindings.items()), 'Frozen input changed'
    original = read(ROOT / item['original_config'])
    result = read(ROOT / item['original_result'])
    assert result['task_checksum'] == item['task_checksum']
    assert result['exception_info']['exception_type'] == item['original_exception_type']
    assert original['trial_name'] == item['task_id']
    assert read(ROOT / item['source_output'] / 'generation' / item['task_id'] / 'config.json')['agent']['model_name'] == item['generation_model']
    assert original['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
    assert original['agent']['kwargs']['source_job'] == str(ROOT / item['source_output'] / 'generation')
    assert original['environment']['import_path'] == item['environment_import_path']
    assert original['environment']['override_cpus'] == manifest['cpus'] == 1
    assert original['environment']['override_memory_mb'] == manifest['memory_mib'] == 4096
    assert original['environment']['override_gpus'] == 0
    assert original['environment']['cpu_enforcement_policy'] == original['environment']['memory_enforcement_policy'] == 'limit'
    assert original['verifier']['override_timeout_sec'] == manifest['verifier_seconds'] == 3000
    assert original['agent']['override_timeout_sec'] == 1800
    image = ROOT / item['sif']
    assert image.stat().st_size == item['sif_size'] and str(image.stat().st_mtime_ns) == item['sif_mtime_ns']
    assert (ROOT / item['patch']).stat().st_size == item['patch_bytes']
    assert Path(patch_replay.__file__) == ROOT / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/patch_replay.py'
    assert not (ROOT / item['output']).exists(), 'Existing attempt retained; no automatic retry'
    bind_named_class(item)
    config = configured(item)
    TrialConfig.model_validate(config)  # Schema only, no Trial/environment construction.
    if item['cohort'] == 'musl':
        shim = ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim/singularity'
        assert shim.is_file() and production_env(item)['PATH'].split(':')[0] == str(shim.parent)
    return config, bindings

class DiskScratchAndLogs:
    scratch_root = None

    async def _start_server(self):
        scratch = self.scratch_root
        scratch.mkdir(parents=True, exist_ok=True)
        self._repair_scratch = Path(tempfile.mkdtemp(prefix='native-', dir=scratch))
        self._repair_scratch.chmod(0o755)
        self._mounts.append({'type': 'bind', 'source': str(self._repair_scratch),
                             'target': '/tmp', 'read_only': False})
        self._repair_logs = Path(next(m['source'] for m in self._mounts
                                     if m['target'] == '/logs/verifier'))
        await super()._start_server()
        context = await super().exec('df -h /tmp /dev/shm; ulimit -n; '
                                     'printf "\\nPATH=%s\\n" "$PATH"', timeout_sec=20)
        save(self._repair_logs / 'repair-runtime.json', {
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
            save(self._repair_logs / 'native-go-disk-cache.json', {
                'original_caches': [build_cache, module_cache], 'disk_caches': targets,
                'return_code': copied.return_code, 'stderr': copied.stderr,
                'original_cache_contents_preserved': True})
            assert copied.return_code == 0, 'Native Go cache disk copy failed'
            self._persistent_env.update(GOCACHE=targets[0], GOMODCACHE=targets[1])

    async def _stop_server_process(self):
        try:
            logs = getattr(self, '_repair_logs', None)
            if logs:
                server_log = getattr(self, '_server_log_path', None)
                if server_log and server_log.exists():
                    shutil.copy2(server_log, logs / 'repair-server.log')
                scope = getattr(self, '_scope_unit', None)
                if scope:
                    cgroup = Path(f'/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{scope.removesuffix(".scope")}.scope')
                    events = {name: (cgroup / name).read_text() for name in
                              ['memory.max', 'memory.swap.max', 'memory.events', 'memory.current', 'memory.peak', 'cpu.stat']
                              if (cgroup / name).exists()}
                    save(logs / 'repair-resource-events.json', events)
        finally:
            await super()._stop_server_process()

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


class AdditionalGlibcRepair(DiskScratchAndLogs, SweCleanGlibcRuntimeEnvironment):
    pass


class AdditionalMuslRepair(DiskScratchAndLogs, SweCleanMuslScoreEnvironment):
    pass


def run(args, manifest, selected, bindings_by_key):
    cohort = ROOT / manifest['output'] / 'cohort-attempt1'
    enough_time = lambda: datetime.fromisoformat(manifest['core_deadline']).timestamp() - time.time() >= 7200
    assert set(range(92,96)) <= effective_cpus() and not terminal_has_lease() and enough_time()
    cohort.mkdir(parents=True,exist_ok=False)
    guard_tmp = cohort / 'host-tmp'
    guard_tmp.mkdir()
    guard_env = dict(production_env(selected[0]), TMPDIR=str(guard_tmp))
    state = {'pid':os.getpid(),'startticks':ticks(os.getpid()),'state':'claimed','lock_held':False,'children':{},'model_calls':0}
    claim = {**state,'at_utc':now(),'script_sha256':sha(Path(__file__)),'manifest_sha256':sha(args.manifest),
        'selection':[{'item':x['key'],'physical_cpu':manifest['cpu_by_item'][x['key']],
            'config':configured(x),'bound_sha256':bindings_by_key[x['key']]} for x in selected]}
    (cohort/'execution-claim.json').write_text(json.dumps(claim,indent=2)+'\n')
    def checkpoint(label, **fields):
        state.update(state=label,at_utc=now(),**fields)
        save(cohort/'parent-state.json',state)
    signal.signal(signal.SIGTERM,lambda *_:state.update(stop_requested=True))
    signal.signal(signal.SIGINT,lambda *_:state.update(stop_requested=True))
    guard,children,unit = None,{},'apex-baseline-swe-additional-'+str(os.getpid())
    def drain(ignore_guard=False):
        samples=[]
        while len(samples)<2:
            busy=[s for s in busy_scopes() if not(ignore_guard and s==unit+'.scope')]
            samples=[] if busy else samples+[{'at_utc':now(),'remaining_scopes':[]}]
            try:checkpoint('draining_native' if ignore_guard else 'draining_after_guard_stop',remaining_scopes=busy)
            except OSError:state['checkpoint_write_failed']=True
            if len(samples)<2:time.sleep(2)
        return samples
    with (ROOT/manifest['shared_lock']).open('a+') as lease:
        while True:
            if not enough_time() or terminal_has_lease() or state.get('stop_requested'):
                checkpoint('stopped_before_native');return
            try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_shared_lease');time.sleep(5);continue
            if not busy_scopes():break
            fcntl.flock(lease,fcntl.LOCK_UN)
            checkpoint('waiting_real_cpu_drain');time.sleep(5)
        checkpoint('lease_acquired',lock_held=True)
        try:
            with (cohort/'guard.log').open('x') as log:
                guard=subprocess.Popen(['systemd-run','--user','--scope','--quiet','--unit='+unit,
                    '-p','MemoryMax=33554432','-p','MemorySwapMax=0','taskset','-c','92-95','sleep','infinity'],
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log,
                    env=guard_env,pass_fds=(lease.fileno(),))
            time.sleep(1)
            assert guard.poll() is None and unit+'.scope' in busy_scopes()
            group=subprocess.check_output(['systemctl','--user','show',unit+'.scope','--property=ControlGroup','--value'],
                text=True,env=guard_env).strip()
            cg=Path('/sys/fs/cgroup')/group.lstrip('/')
            affinities={p:sorted(os.sched_getaffinity(int(p))) for p in (cg/'cgroup.procs').read_text().split()}
            assert affinities and all(c==[92,93,94,95] for c in affinities.values())
            assert int((cg/'memory.max').read_text())==33554432 and int((cg/'memory.swap.max').read_text())==0
            checkpoint('guard_verified',guard_observed={'unit':unit+'.scope','affinities':affinities,'memory_max_bytes':33554432,'memory_swap_max_bytes':0})
            assert not terminal_has_lease() and not[s for s in busy_scopes() if s!=unit+'.scope']
            assert enough_time() and not state.get('stop_requested')
            for item in selected:
                key=item['key'];output=ROOT/item['output'];cpu=manifest['cpu_by_item'][key]
                output.mkdir(parents=True,exist_ok=False)
                per_item={'pid':state['pid'],'startticks':state['startticks'],'item':key,'physical_cpu':cpu,
                    'cohort_claim':str(cohort/'execution-claim.json'),'script_sha256':claim['script_sha256'],
                    'manifest_sha256':claim['manifest_sha256'],'config':configured(item),
                    'bound_sha256':bindings_by_key[key],'model_calls':0}
                (output/'execution-claim.json').write_text(json.dumps(per_item,indent=2)+'\n')
            # Fixed cohort, no queue/retry. A failed child never cancels another.
            for item in selected:
                key=item['key'];output=ROOT/item['output'];cpu=manifest['cpu_by_item'][key]
                try:
                    assert not state.get('stop_requested'), 'Stop requested before this child admission'
                    assert enough_time(), 'Insufficient original-budget runway for this child'
                    assert all(sha(ROOT/p)==v for p,v in bindings_by_key[key].items())
                    Path(production_env(item)['TMPDIR']).mkdir(parents=True,exist_ok=True)
                    command=['taskset','-c',str(cpu),str(ROOT/'artifacts/envs/harbor/bin/python'),str(Path(__file__)),
                        '--manifest',str(args.manifest),'--item',key,'--child','--physical-cpu',str(cpu),'--lease-fd',str(lease.fileno())]
                    with (output/'child.log').open('x') as log:
                        child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,
                            stderr=subprocess.STDOUT,env=production_env(item),pass_fds=(lease.fileno(),))
                    children[key]=child
                    state['children'][key]={'pid':child.pid,'startticks':ticks(child.pid),'physical_cpu':cpu,'output':str(output),'command':command}
                except Exception as error:state['children'][key]={'start_failed':type(error).__name__,'output':str(output)}
                checkpoint('native_running')
            save(cohort/'execution-claim.json',dict(claim,children=state['children']))
            while any(c.poll() is None for c in children.values()):time.sleep(5)
            for item in selected:
                key=item['key'];output=ROOT/item['output'];path=output/'native'/item['task_id']/'result.json'
                result=read(path) if path.exists() else {}
                save(output/'pending-root-review.json',{'at_utc':now(),'result':str(path),
                    'child_returncode':children[key].returncode if key in children else None,
                    'native_reward':((result.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                    'exception_type':(result.get('exception_info') or {}).get('exception_type'),
                    'original_bytes_unchanged':all(sha(ROOT/p)==v for p,v in bindings_by_key[key].items()),
                    'accepted_into_formal_summary':False,'new_model_calls':0})
            checkpoint('finished_pending_root_review')
        except Exception as error:
            checkpoint('failed_pending_root_review',error_type=type(error).__name__);raise
        finally:
            final_state=state['state']
            while any(c.poll() is None for c in children.values()):time.sleep(5)
            native_samples=drain(ignore_guard=True)
            if guard is not None:
                subprocess.run(['systemctl','--user','stop',unit+'.scope'],check=True,env=production_env(selected[0]))
                guard.wait(timeout=10)
            samples=drain()
            assert unit+'.scope' not in busy_scopes()
            fcntl.flock(lease,fcntl.LOCK_UN)
            checkpoint(final_state,lock_held=False,guard_stopped=True,released_at_utc=now(),
                consecutive_empty_native_scope_samples=native_samples,consecutive_empty_scope_samples_after_guard_stop=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/swe_additional_short_tmp_recovery_20261017.json')
    parser.add_argument('--item', action='append')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--lease-fd', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--physical-cpu', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.manifest = args.manifest.resolve()
    manifest = read(args.manifest)
    items = {row['key']: row for row in manifest['items']}
    assert set(items) == ALLOWED
    selected = [items[key] for key in args.item] if args.item else list(items.values())
    assert len({x['key'] for x in selected}) == len(selected)
    assert manifest['cpu_by_item'] == {'swe249/nodebb':92,'swe249/teleport2b':93,'avg64/teleport2b':94}
    assert not args.execute or args.item, 'Execution requires explicit item selection'
    checks, bindings_by_key = [], {}
    for item in selected:
        if args.child:
            claim = read(ROOT / item['output'] / 'execution-claim.json')
            assert claim['script_sha256'] == sha(Path(__file__)) and claim['manifest_sha256'] == sha(args.manifest)
            assert ticks(claim['pid']) == claim['startticks']
            assert args.lease_fd is not None and Path('/proc/self/fd/' + str(args.lease_fd)).resolve() == ROOT / manifest['shared_lock']
            assert len(selected) == 1
            assert args.physical_cpu == manifest['cpu_by_item'][item['key']] == claim['physical_cpu']
            assert os.sched_getaffinity(0) == {args.physical_cpu}
            assert all(sha(ROOT / p) == expected for p, expected in claim['bound_sha256'].items())
            os.environ.update(production_env(item))
            bind_named_class(item)  # Harbor imports a named class, distinct from CLI __main__.
            async def grade():
                trial = await Trial.create(TrialConfig.model_validate(configured(item)))
                assert trial.task.checksum == item['task_checksum']
                await trial.run()
            asyncio.run(grade())
            return
        config, bindings = validate(manifest, item)
        bindings_by_key[item['key']] = bindings
        checks.append({'item': item['key'], 'bindings_verified': len(bindings), 'cohort': item['cohort'],
            'original_exception_type': item['original_exception_type'], 'patch_bytes': item['patch_bytes'],
            'native_directory_exists': False, 'physical_cpu_ids': [manifest['cpu_by_item'][item['key']]], 'logical_cpu_offset': 0,
            'cpus': 1, 'memory_mib': 4096, 'verifier_seconds': 3000,
            'named_environment_scratch_binding_checked': True,
            'production_environment': {k:production_env(item)[k] for k in
                ['PATH','PYTHONPATH','TMPDIR','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS']}})
    if args.execute:
        run(args, manifest, selected, bindings_by_key)
        return
    print(json.dumps({'at_utc': now(), 'mode': 'prepare_only', 'checks': checks,
        'script_sha256': sha(Path(__file__)), 'manifest_sha256': sha(args.manifest),
        'execution_claim_created': False, 'native_started': False, 'guard_created': False,
        'shared_lock_acquired': False, 'model_calls': 0, 'new_api_calls': 0,
        'patch_replay_origin': patch_replay.__file__, 'python_lexical': sys.executable,
        'root_cause_or_repair_not_proven': True}, indent=2))


if __name__ == '__main__':
    main()
