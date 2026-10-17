#!/usr/bin/env python3
"""Prepare one frozen git-leak answer; --execute is reserved for root's reviewed one-shot launch."""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import signal
import subprocess
import tarfile
import time

from run_terminal_native_gap_queue_20261017 import busy_scopes, now, save

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
KEY = 'git-leak-recovery/seed1'
CPUS = {92, 93, 94, 95}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ticks(pid):
    try:
        fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[19] if fields[0] != 'Z' else None
    except FileNotFoundError:
        return None


def effective_cpus():
    group = Path('/proc/self/cgroup').read_text().strip().split('::')[-1]
    directory = Path('/sys/fs/cgroup') / group.lstrip('/')
    while not (directory / 'cpuset.cpus.effective').exists():
        directory = directory.parent
    result = set()
    for part in (directory / 'cpuset.cpus.effective').read_text().strip().split(','):
        ends = list(map(int, part.split('-')))
        result.update(range(ends[0], ends[-1] + 1))
    return result


def terminal_has_lease():
    for name in ('terminal250_full445_20261017', 'avg64_terminal_full445_20261017'):
        output = ROOT / 'artifacts/eval' / name
        if (output / 'cpu-expansion-asi_finished.json').exists():
            return True
        offsets = read(output / 'summary.json')['leased_cpu_offsets']
        if any(set(range(cpu, cpu + 4)) & CPUS for cpu in offsets):
            return True
    return False


def production_env(config):
    tools = ROOT / 'artifacts/tools'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(ROOT / config['runtime'] / 'scripts'),
        XDG_RUNTIME_DIR='/run/user/1012', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1012/bus',
        TMPDIR=config['host_tmpdir'], OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env['PATH'] = ':'.join(map(str, [tools / 'apptainer-1.4.5/rootfs/usr/bin',
        tools / 'fakeroot-1.25.3/rootfs/usr/bin'])) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
    return env


def unchanged(config):
    return all(sha(ROOT / path) == value for path, value in config['source_sha256'].items())


def validate(config):
    assert config['key'] == KEY and config['model'] == 'apex-terminal250' and config['seed'] == 1
    assert unchanged(config), 'Frozen source changed'
    original = read(ROOT / config['original_result'])
    native = original['config']
    assert original['task_checksum'] == config['task_checksum']
    assert native['agent']['model_name'] == config['model'] and native['agent']['kwargs']['seed'] == 1
    assert original['verifier_result'] is None
    assert original['exception_info']['exception_message'] == 'Refusing public network after unconfirmed solver cleanup'
    assert native['environment']['override_cpus'] == 4
    assert native['environment']['override_memory_mb'] == 8192
    assert native['environment']['override_gpus'] == 0
    assert native['environment']['cpu_enforcement_policy'] == native['environment']['memory_enforcement_policy'] == 'limit'
    assert native['verifier']['override_timeout_sec'] == 900 and native['agent']['override_timeout_sec'] == 1800
    snapshot = read(ROOT / config['snapshot'])
    assert snapshot['captured_before_verifier'] and snapshot['return_code'] == 0 and not snapshot['stderr']
    assert snapshot['complete_prefixes'] == ['app', 'etc'] and snapshot['changed_external_files'] == ['root/.lesshst']
    image = ROOT / config['sif_tag']
    assert str(image.resolve()) == str(ROOT / config['sif_resolved'])
    assert image.stat().st_size == config['sif_size_bytes'] and str(image.stat().st_mtime_ns) == config['sif_mtime_ns']
    static = read(ROOT / config['static_receipt'])
    assert static['git']['exit_code'] == 0 and static['git']['stdout_bytes'] == static['git']['stderr_bytes'] == 0
    assert static['git']['extracted_app_unchanged'] and static['source_bindings_final_recheck']['all_unchanged']
    assert static['static_etc']['differences'] == config['etc_delta'] and len(config['etc_delta']) == 23
    assert all(Path(row['path']).exists() for row in static['verifier_dependencies']['source_paths']), 'Original verifier assets unavailable'
    assert not any(row['path'] == '/etc/resolv.conf' for row in config['etc_delta'])
    assert config['minimum_runway_seconds'] >= 2400
    assert config['cpu_ids'] == sorted(CPUS) and config['logical_cpu_offset'] == 0
    assert config['memory_mib'] == 8192 and config['verifier_seconds'] == 900
    assert CPUS <= effective_cpus(), 'Parent cgroup cannot admit the unchanged physical CPU lease'
    assert not (ROOT / config['output'] / 'attempt1').exists(), 'Existing attempt retained; no retry'
    assert not terminal_has_lease(), 'Terminal already owns the grader pool'
    assert Path(config['host_tmpdir']).is_absolute()
    socket_path = Path(config['host_tmpdir']) / ('apex_baseline_net_' + 'x' * 8) / 'control.sock'
    assert len(os.fsencode(socket_path)) < 108, 'Frozen namespace socket exceeds sun_path'
    assert len(Path(config['host_tmpdir']).parts) == 4 and str(config['host_tmpdir']).startswith('/data/caoqinlu/')
    return {'namespace_control_socket_bytes': len(os.fsencode(socket_path)),
            'source_bindings_verified': len(config['source_sha256']), 'terminal_has_grader_lease': False}


def write_once(path, data):
    if path.exists():
        assert path.read_bytes() == data, 'Prepared artifact changed'
    else:
        path.write_bytes(data)


def prepare(config):
    output = ROOT / config['output'] / 'prepared'
    output.mkdir(parents=True, exist_ok=True)
    archive = ROOT / config['archive']
    selected = {row['path'].lstrip('/') for row in config['etc_delta']}
    delta = output / 'etc-delta.tar'
    temporary = output / 'etc-delta.building.tar'
    with tarfile.open(archive) as source, tarfile.open(temporary, 'w') as target:
        members = source.getmembers()
        assert len(members) == len({m.name for m in members}) == 561
        byname = {m.name: m for m in members}
        for member in members:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert member.isdir() or member.isfile() or member.issym() or member.islnk()
        chosen = [m for m in members if m.name in selected]
        assert len(chosen) == 23
        links = [(m.name, m.linkname) for m in members if m.islnk()]
        assert links == [('etc/apt/apt.conf.d/01-vendor-ubuntu', 'app/repo/.git/info/refs')]
        assert byname[links[0][1]].isfile()
        assert sum(m.name == 'app' or m.name.startswith('app/') for m in members) == 50
        for member in chosen:
            target.addfile(member, source.extractfile(member) if member.isfile() else None)
    data = temporary.read_bytes()
    temporary.unlink()
    write_once(delta, data)
    nondirs = [row['path'] for row in config['etc_delta'] if row['candidate_kind'] != 'dir']
    # This isolated, no-site harness Python only compares archived bytes/metadata; no candidate import.
    verification = '''import hashlib,json,os,stat,tarfile
from pathlib import Path
archive=tarfile.open('/staging/git-leak-final-state.tar')
selected=SELECTED
checked=0
for m in archive.getmembers():
 if not(m.name=='app' or m.name.startswith('app/') or m.name in selected):continue
 p=Path('/')/m.name;s=p.lstat()
 assert stat.S_IMODE(s.st_mode)==m.mode, 'restore mode mismatch'
 if m.isdir():assert stat.S_ISDIR(s.st_mode), 'restore directory mismatch'
 elif m.issym():assert stat.S_ISLNK(s.st_mode) and os.readlink(p)==m.linkname, 'restore symlink mismatch'
 else:
  assert stat.S_ISREG(s.st_mode), 'restore regular-file mismatch'
  assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(archive.extractfile(m).read()).digest(), 'restore content mismatch'
  if m.islnk():assert os.path.samefile(p,Path('/')/m.linkname), 'restore hardlink topology mismatch'
 checked+=1
expected={m.name.rstrip('/') for m in archive.getmembers() if m.name=='app' or m.name.startswith('app/')}
actual={'app'}
for root,ds,fs in os.walk('/app',followlinks=False):
 actual.update(str((Path(root)/name).relative_to('/')) for name in ds+fs)
assert actual==expected, 'restore app inventory mismatch'
print(json.dumps({'restored_members_verified':checked,'app_members':len(expected),'etc_delta_members':len(selected),'cross_path_hardlink_verified':True,'candidate_code_executed':False}))
'''.replace('SELECTED', repr(sorted(selected)), 1)
    commands = [
        {'command': 'set -e; sha256sum /etc/resolv.conf > /staging/managed-resolver.sha256; '
            'rm -rf -- /app; tar --overwrite -xpf /staging/git-leak-final-state.tar -C / -- app', 'timeout_sec': 90},
        {'command': 'set -e; rm -f -- ' + shlex.join(nondirs) + '; '
            'tar --overwrite -xpf /staging/git-leak-etc-delta.tar -C /; '
            'sha256sum -c /staging/managed-resolver.sha256', 'timeout_sec': 90},
        {'command': '/opt/harbor-server/bin/python3 -I -S -c ' + shlex.quote(verification), 'timeout_sec': 60}]
    restore = {'original_result': str(ROOT / config['original_result']), 'model': config['model'], 'seed': 1,
        'task_checksum': config['task_checksum'], 'sif': str(ROOT / config['sif_resolved']),
        'files': [{'source': str(archive), 'target': '/staging/git-leak-final-state.tar'},
                  {'source': str(delta), 'target': '/staging/git-leak-etc-delta.tar'}],
        'commands': commands, 'restore_command_budget_seconds': 240, 'new_model_calls': 0,
        'resolver_policy': {'excluded': '/etc/resolv.conf', 'retain_frozen_runtime_policy': True},
        'etc_delta_paths': sorted(selected), 'hardlink': {'path': '/etc/apt/apt.conf.d/01-vendor-ubuntu',
        'target': '/app/repo/.git/info/refs', 'restore_app_first': True},
        'no_install_or_service_start': True, 'status': 'prepared_not_executed'}
    manifest = output / 'restore.json'
    write_once(manifest, (json.dumps(restore, indent=2) + '\n').encode())
    return manifest, delta


def swe_drained(config):
    source = read(ROOT / config['priority_swe_state'])
    assert source['pid'] == 1765416 and source['startticks'] == '869931371'
    if ticks(1765416) == source['startticks'] or source['lock_held']:
        return False
    if not source.get('guard_stopped') or source['state'] not in ('finished_pending_root_review', 'failed_pending_root_review'):
        return False
    for key in ('consecutive_empty_native_scope_samples', 'consecutive_empty_scope_samples_after_guard_stop'):
        if len(source.get(key, [])) != 2 or any(row['remaining_scopes'] for row in source[key]):
            return False
    return True


def asi_ready(config):
    generation = ROOT / config['priority_asi_generation_marker']
    finished = ROOT / config['priority_asi_all_cpu_marker']
    return (generation.exists() and read(generation).get('state') == 'finished'
            and not (finished.exists() and read(finished).get('state') == 'finished'))


def run(args, config, restore, delta):
    attempt = ROOT / config['output'] / 'attempt1'
    native = attempt / 'native-grade'
    end = datetime.fromisoformat(config['core_deadline']).timestamp()
    enough = lambda: end - time.time() >= config['minimum_runway_seconds']
    assert enough() and not terminal_has_lease()
    attempt.mkdir(exist_ok=False)
    Path(config['host_tmpdir']).mkdir(parents=True, exist_ok=True)
    env = production_env(config)
    command = ['taskset', '-c', '92-95', str(ROOT / 'artifacts/envs/harbor/bin/python'),
        str(ROOT / config['runtime'] / 'scripts/run_terminal_repair_grade_v2.py'),
        '--original-result', str(ROOT / config['original_result']), '--restore-manifest', str(restore),
        '--output', str(native), '--cpu-offset', '0']
    state = {'pid': os.getpid(), 'startticks': ticks(os.getpid()), 'state': 'claimed', 'lock_held': False,
        'model_calls': 0, 'command': command, 'native_output': str(native), 'accepted_into_formal_summary': False}
    frozen = {**{str(ROOT / p): v for p, v in config['source_sha256'].items()},
              str(restore): sha(restore), str(delta): sha(delta), str(args.manifest): sha(args.manifest),
              str(Path(__file__)): sha(Path(__file__))}
    (attempt / 'execution-claim.json').write_text(json.dumps({**state, 'at_utc': now(), 'bound_sha256': frozen}, indent=2) + '\n')
    os.sched_setaffinity(0, {10})  # Ordinary affinity only: child still inherits the broad session cgroup.
    signal.signal(signal.SIGTERM, lambda *_: state.update(stop_requested=True))
    signal.signal(signal.SIGINT, lambda *_: state.update(stop_requested=True))
    def checkpoint(label, **fields):
        state.update(state=label, at_utc=now(), **fields)
        try:
            save(attempt / 'parent-state.json', state)
        except OSError:
            state['checkpoint_write_failed'] = True
    def drain(ignore_guard=False):
        samples = []
        while len(samples) < 2:
            try:
                busy = [s for s in busy_scopes() if not (ignore_guard and s == unit + '.scope')]
            except Exception as error:
                checkpoint('waiting_scope_observer', observer_error_type=type(error).__name__)
                time.sleep(2)
                continue  # A failed observer is not evidence that the lease is empty.
            samples = [] if busy else samples + [{'at_utc': now(), 'remaining_scopes': []}]
            checkpoint('draining_native' if ignore_guard else 'draining_after_guard_stop', remaining_scopes=busy)
            if len(samples) < 2:
                time.sleep(2)
        return samples
    guard, child, unit = None, None, 'apex-baseline-git-leak-' + str(os.getpid())
    with (ROOT / config['shared_lock']).open('r+') as lease:
        while True:
            if not enough() or terminal_has_lease() or asi_ready(config) or state.get('stop_requested'):
                checkpoint('stopped_before_native')
                return
            if not swe_drained(config):
                checkpoint('waiting_priority_swe_drain'); time.sleep(5); continue
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_shared_lease'); time.sleep(5); continue
            if not busy_scopes():
                break
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint('waiting_real_cpu_drain'); time.sleep(5)
        checkpoint('lease_acquired', lock_held=True)
        try:
            with (attempt / 'guard.log').open('x') as log:
                guard = subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
                    '-p', 'MemoryMax=33554432', '-p', 'MemorySwapMax=0', 'taskset', '-c', '92-95', 'sleep', 'infinity'],
                    env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log, pass_fds=(lease.fileno(),))
            time.sleep(1)
            assert guard.poll() is None and unit + '.scope' in busy_scopes()
            group = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope', '--property=ControlGroup', '--value'], env=env, text=True).strip()
            cg = Path('/sys/fs/cgroup') / group.lstrip('/')
            affinity = {p: sorted(os.sched_getaffinity(int(p))) for p in (cg / 'cgroup.procs').read_text().split()}
            assert affinity and all(v == sorted(CPUS) for v in affinity.values())
            assert int((cg / 'memory.max').read_text()) == 33554432 and int((cg / 'memory.swap.max').read_text()) == 0
            checkpoint('guard_verified', guard_observed={'unit': unit + '.scope', 'affinities': affinity, 'memory_max': 33554432, 'memory_swap_max': 0})
            assert enough() and not terminal_has_lease() and not asi_ready(config) and not state.get('stop_requested')
            assert swe_drained(config)
            assert all(sha(Path(p)) == value for p, value in frozen.items())
            assert not [s for s in busy_scopes() if s != unit + '.scope']
            with (attempt / 'native-child.log').open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, pass_fds=(lease.fileno(),))
            checkpoint('native_running', child_pid=child.pid, child_startticks=ticks(child.pid))
            child.wait()  # No parent timeout, cancellation, retry, or model call.
            result = read(native / 'result.json') if (native / 'result.json').exists() else {}
            checkpoint('finished_pending_root_review', child_returncode=child.returncode,
                native_reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                exception_type=(result.get('exception_info') or {}).get('exception_type'),
                original_and_restore_unchanged=all(sha(Path(p)) == value for p, value in frozen.items()))
        except Exception as error:
            checkpoint('failed_pending_root_review', error_type=type(error).__name__)
            raise
        finally:
            final_state = state['state']
            # Even observer/log failures hold the same lease until native has naturally drained.
            if child is not None:
                child.wait()
            native_samples = drain(ignore_guard=True)
            if guard is not None:
                subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], env=env, check=True)
                guard.wait(timeout=10)
            empty_samples = drain()
            assert unit + '.scope' not in busy_scopes()
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint(final_state, lock_held=False, guard_stopped=True, released_at_utc=now(),
                consecutive_empty_native_scope_samples=native_samples,
                consecutive_empty_scope_samples_after_guard_stop=empty_samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/terminal_git_leak_grade_only_20261017.json')
    parser.add_argument('--execute', action='store_true', help='Only root may launch this reviewed one-shot lease/grade')
    args = parser.parse_args()
    args.manifest = args.manifest.absolute()
    config = read(args.manifest)
    checks = validate(config)
    restore, delta = prepare(config)
    if args.execute:
        run(args, config, restore, delta)
        return
    lease = ROOT / config['shared_lock']
    print(json.dumps({'at_utc': now(), 'mode': 'prepare_only', **checks,
        'script_sha256': sha(Path(__file__)), 'manifest_sha256': sha(args.manifest),
        'prepared': [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in [restore, delta]],
        'production_environment': {k: production_env(config)[k] for k in ['PATH', 'PYTHONPATH', 'TMPDIR', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS']},
        'shared_lock': {'path': str(lease), 'inode': lease.stat().st_ino, 'acquired': False},
        'priority_swe_drained': swe_drained(config), 'priority_asi_ready_for_grader': asi_ready(config),
        'native_started': False, 'execution_claim_created': False, 'guard_created': False,
        'model_calls': 0, 'new_api_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
