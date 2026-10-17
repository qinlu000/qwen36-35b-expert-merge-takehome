#!/usr/bin/env python3
"""Prepare one saved Terminal grade; only --execute may claim CPU124-127."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
POOL = {124, 125, 126, 127}
LOCK = ROOT / 'artifacts/eval/avg64_teleport7744_cpu124_127.lock'
GENERATION = ROOT / 'artifacts/eval/avg64_asi240_20261017/generation_cpu_finished.json'
T774 = ROOT / 'artifacts/recovery/avg64-teleport7744-original-proxy-20261017/attempt1/parent-state.json'
T774_SHA = '99d39e8e81572b14fd0e6d5681818d5b6171b64267c8c0cf0123fdc216effbba'
TERMINALS = ('terminal250_full445_20261017', 'avg64_terminal_full445_20261017')
read = lambda path: json.loads(path.read_bytes())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()


def ticks(pid):
    try:
        fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[19] if fields[0] != 'Z' else None
    except FileNotFoundError:
        return None


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def effective_cpus():
    directory = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::')[-1].lstrip('/')
    while not (directory / 'cpuset.cpus.effective').exists():
        directory = directory.parent
    cpus = set()
    for part in (directory / 'cpuset.cpus.effective').read_text().strip().split(','):
        ends = list(map(int, part.split('-')))
        cpus.update(range(ends[0], ends[-1] + 1))
    return cpus


def live_scopes():
    scopes = {}
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            state = (process / 'stat').read_text().rsplit(')', 1)[1].split()[0]
            group = (process / 'cgroup').read_text().strip().split('/')[-1]
            if state != 'Z' and any(p in group for p in ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-')):
                scopes.setdefault(group, set()).update(os.sched_getaffinity(int(process.name)))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return scopes


def pool_scopes(ignore=None):
    return sorted(s for s, cpus in live_scopes().items() if s != ignore and POOL.intersection(cpus))


def gates(config):
    marker = read(GENERATION)
    assert marker['state'] == 'finished' and marker['completed_conditions'] == marker['owned_scope_count'] == 240
    assert marker['worker_pool_shutdown'] is True and marker['active_owned_scopes'] == []
    assert marker['cpu_sets'] == [list(range(i, i + 4)) for i in range(96, 128, 4)]
    for name in TERMINALS:
        output = ROOT / 'artifacts/eval' / name
        for file in ('config.json', 'experiment.json'):
            c = read(output / file)
            offsets = c['initial_cpu_offsets'] + c['cpu_offsets'] + [v for s in c['expansion_stages'] for v in s['cpu_offsets']]
            assert all(0 <= offset and offset + 3 <= 123 for offset in offsets)
        assert set(read(output / 'summary.json')['leased_cpu_offsets']) <= set(c['cpu_offsets'])
    assert sha(T774) == T774_SHA and LOCK.stat().st_ino == 90780234
    previous = read(T774)
    assert previous['pid'] == 2223041 and previous['startticks'] == '870388084'
    assert previous['state'] == 'finished_pending_root_review' and previous['child_returncode'] == 0
    assert previous['original_sources_unchanged'] and previous['guard_stopped'] and previous['lock_held'] is False
    samples = previous['consecutive_empty_native_scope_samples'] + previous['consecutive_empty_scope_samples_after_guard_stop']
    assert len(previous['consecutive_empty_native_scope_samples']) == len(previous['consecutive_empty_scope_samples_after_guard_stop']) == 2
    assert all(s['remaining_scopes'] == [] for s in samples)
    assert [s['at_utc'] for s in samples] == sorted(s['at_utc'] for s in samples)
    assert ticks(previous['pid']) != previous['startticks'] and ticks(previous['child_pid']) != previous['child_startticks']
    source = read(ROOT / config['pid_source'])
    assert source['original_result'] == config['original_result'] and source['old_namespace_solver_clear'] is True
    assert source['old_scope'].startswith('apex-baseline-') and source['old_scope'] not in live_scopes()
    assert all(not p.get('startticks') or ticks(p['pid']) != p['startticks'] for p in source['captured_solver_processes'])
    return {'generation_marker_sha256': sha(GENERATION), 't774_state_sha256': T774_SHA, 'old_scope': source['old_scope']}


def prepare(config, manifest):
    required = [config['original_result'], config['restore_manifest'], config['pid_source'],
                str(Path(config['runtime']) / 'scripts/run_terminal_repair_grade_v2.py')]
    assert all(p in config['source_sha256'] for p in required)
    assert all(sha(ROOT / p) == value for p, value in config['source_sha256'].items())
    for path, expected in config['source_stat'].items():
        st = (ROOT / path).stat()
        assert st.st_size == expected['size'] and str(st.st_mtime_ns) == str(expected['mtime_ns'])
    original = read(ROOT / config['original_result'])['config']
    e = original['environment']
    assert (e['override_cpus'], e['override_memory_mb'], e['override_gpus']) == (4, 8192, 0)
    assert e['cpu_enforcement_policy'] == e['memory_enforcement_policy'] == 'limit'
    assert original['verifier']['override_timeout_sec'] == 900 and original['timeout_multiplier'] == 1
    assert config['minimum_runway_seconds'] >= 2400 and POOL <= effective_cpus()
    assert not (ROOT / config['output'] / 'attempt1').exists(), 'Existing attempt retained; no retry'
    assert len(os.fsencode(Path(config['host_tmpdir']) / 'apex_baseline_net_XXXXXXXX/control.sock')) < 108
    return gates(config)


def run(config, manifest, checks):
    attempt = ROOT / config['output'] / 'attempt1'
    attempt.mkdir(parents=True, exist_ok=False)
    runtime = ROOT / config['runtime'] / 'scripts'
    tools = ROOT / 'artifacts/tools'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(runtime), TMPDIR=config['host_tmpdir'],
        XDG_RUNTIME_DIR='/run/user/1012', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1012/bus',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env['PATH'] = ':'.join(map(str, [tools / 'apptainer-1.4.5/rootfs/usr/bin', tools / 'fakeroot-1.25.3/rootfs/usr/bin'])) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
    command = ['taskset', '-c', '124-127', str(ROOT / 'artifacts/envs/harbor/bin/python'), str(runtime / 'run_terminal_repair_grade_v2.py'),
        '--original-result', str(ROOT / config['original_result']), '--restore-manifest', str(ROOT / config['restore_manifest']),
        '--output', str(attempt / 'native'), '--cpu-offset', '0']
    frozen = {**{str(ROOT / p): h for p, h in config['source_sha256'].items()},
              str(manifest): sha(manifest), str(Path(__file__)): sha(Path(__file__))}
    state = {'pid': os.getpid(), 'startticks': ticks(os.getpid()), 'state': 'waiting_private_lease',
             'lock_held': False, 'model_calls': 0, 'accepted_into_formal_summary': False}
    save(attempt / 'execution-claim.json', {**state, 'at_utc': now(), 'bound_sha256': frozen, 'source_stat': config['source_stat'], 'command': command, **checks})
    os.sched_setaffinity(0, {10})
    signal.signal(signal.SIGTERM, lambda *_: state.update(stop_requested=True))
    signal.signal(signal.SIGINT, lambda *_: state.update(stop_requested=True))
    enough = lambda: datetime.fromisoformat(config['core_deadline']).timestamp() - time.time() >= config['minimum_runway_seconds']
    def checkpoint(label, **fields):
        state.update(state=label, at_utc=now(), **fields)
        save(attempt / 'parent-state.json', state)
    def drain(ignore=None):
        samples = []
        while len(samples) < 2:
            try:
                busy = pool_scopes(ignore)
            except Exception:
                samples = []; time.sleep(2); continue
            samples = [] if busy else samples + [{'at_utc': now(), 'remaining_scopes': []}]
            if len(samples) < 2:
                time.sleep(2)
        return samples
    guard = child = None
    unit = 'apex-baseline-terminal-saved124-' + str(os.getpid())
    with LOCK.open('r+') as lease:
        while True:
            if not enough() or state.get('stop_requested'):
                checkpoint('stopped_before_native'); return
            gates(config)
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_private_lease'); time.sleep(5); continue
            if not pool_scopes():
                break
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint('waiting_actual_scope_drain'); time.sleep(5)
        checkpoint('lease_acquired', lock_held=True)
        try:
            Path(config['host_tmpdir']).mkdir(parents=True, exist_ok=True)
            with (attempt / 'guard.log').open('x') as log:
                guard = subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
                    '-p', 'MemoryMax=33554432', '-p', 'MemorySwapMax=0', 'taskset', '-c', '124-127', 'sleep', 'infinity'],
                    env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log, pass_fds=(lease.fileno(),))
            time.sleep(1)
            assert guard.poll() is None and unit + '.scope' in pool_scopes()
            group = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope', '--property=ControlGroup', '--value'], env=env, text=True).strip()
            cg = Path('/sys/fs/cgroup') / group.lstrip('/')
            affinity = {p: sorted(os.sched_getaffinity(int(p))) for p in (cg / 'cgroup.procs').read_text().split()}
            assert affinity and all(v == sorted(POOL) for v in affinity.values())
            assert int((cg / 'memory.max').read_text()) == 33554432 and int((cg / 'memory.swap.max').read_text()) == 0
            checks = gates(config)
            assert enough() and not state.get('stop_requested') and not pool_scopes(unit + '.scope')
            assert all(sha(Path(p)) == h for p, h in frozen.items())
            for p, expected in config['source_stat'].items():
                st = (ROOT / p).stat()
                assert st.st_size == expected['size'] and str(st.st_mtime_ns) == str(expected['mtime_ns'])
            save(attempt / 'admission.json', {**state, 'at_utc': now(), **checks, 'guard_affinities': affinity, 'guard_memory_max': 33554432, 'guard_swap_max': 0, 'bound_sha256': frozen})
            with (attempt / 'native-child.log').open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, pass_fds=(lease.fileno(),))
            checkpoint('native_running', child_pid=child.pid, child_startticks=ticks(child.pid), command=command)
            child.wait()
            result = read(attempt / 'native/result.json') if (attempt / 'native/result.json').exists() else {}
            checkpoint('finished_pending_root_review', child_returncode=child.returncode,
                native_reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                exception_type=(result.get('exception_info') or {}).get('exception_type'),
                frozen_sources_unchanged=all(sha(Path(p)) == h for p, h in frozen.items()))
        except Exception as error:
            checkpoint('failed_pending_root_review', error_type=type(error).__name__); raise
        finally:
            final_state = state['state']
            if child is not None:
                child.wait()
            native_samples = drain(unit + '.scope')
            if guard is not None:
                subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], env=env, check=True)
                guard.wait(timeout=10)
            full_samples = drain()
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint(final_state, lock_held=False, guard_stopped=True, released_at_utc=now(),
                consecutive_empty_native_scope_samples=native_samples,
                consecutive_empty_scope_samples_after_guard_stop=full_samples)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(); args.manifest = args.manifest.absolute()
    config = read(args.manifest); checks = prepare(config, args.manifest)
    if args.execute:
        run(config, args.manifest, checks)
    else:
        print(json.dumps({'mode': 'prepare_only', **checks, 'busy_scopes': pool_scopes(),
            'script_sha256': sha(Path(__file__)), 'manifest_sha256': sha(args.manifest),
            'claim_created': False, 'lock_acquired': False, 'guard_created': False,
            'native_started': False, 'model_calls': 0}, indent=2))
