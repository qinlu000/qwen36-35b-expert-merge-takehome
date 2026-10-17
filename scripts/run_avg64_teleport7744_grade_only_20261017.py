"""Prepare one saved AVG answer; root alone may launch its reviewed grade once."""
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
import signal
import subprocess
import sys
import time

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from run_swe_additional_grade_only_20261017 import DiskScratchAndLogs
from run_swe_remaining_grade_only_20261017 import (
    ROOT, now, read, sha, save, ticks, effective_cpus, production_env as base_env)
from swe_clean_musl_runtime import SweCleanMuslScoreEnvironment

MODULE = 'run_avg64_teleport7744_grade_only_20261017'
POOL = {124, 125, 126, 127}
URL = 'https://proxy.golang.org/github.com/mdlayher/netlink/@v/list'


def production_env(config):
    env = base_env()
    env['TMPDIR'] = config['host_tmpdir']
    env['PATH'] = str(ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim') + ':' + env['PATH']
    return env


def pool_scopes(ignore=None):
    scopes = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            state = (process / 'stat').read_text().rsplit(')', 1)[1].split()[0]
            group = (process / 'cgroup').read_text().strip().split('/')[-1]
            if (state != 'Z' and group != ignore and
                    any(p in group for p in ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and POOL.intersection(os.sched_getaffinity(int(process.name)))):
                scopes.add(group)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return sorted(scopes)


def terminal_contract(config):
    for expected in config['terminal_contracts']:
        output = ROOT / expected['output']
        for name in ('config.json', 'experiment.json'):
            actual = read(output / name)
            stages = [{k: s[k] for k in ('name', 'cpu_offsets')} for s in actual['expansion_stages']]
            assert actual['initial_cpu_offsets'] == expected['initial_cpu_offsets']
            assert actual['cpu_offsets'] == expected['cpu_offsets'] and stages == expected['expansion_stages']
            offsets = actual['initial_cpu_offsets'] + actual['cpu_offsets']
            offsets += [v for s in stages for v in s['cpu_offsets']]
            assert not POOL.intersection(cpu + j for cpu in offsets for j in range(4))
        assert set(read(output / 'summary.json')['leased_cpu_offsets']) <= set(expected['cpu_offsets'])
    return True


def generation_released(config):
    path = ROOT / config['generation_marker']
    if not path.exists():
        return False
    marker = read(path)
    return (marker.get('state') == 'finished' and marker.get('completed_conditions') == 240
            and marker.get('worker_pool_shutdown') is True and marker.get('active_owned_scopes') == []
            and marker.get('owned_scope_count') == 240
            and marker.get('cpu_sets') == config['expected_generation_cpu_sets'])


def route_ready(config):
    path = ROOT / config['route_receipt']
    if not path.exists():
        return False
    route = read(path)
    assert route['schema'] == 'avg64_teleport7744_original_route_v1' and route['state'] == 'ready'
    for key in ('origin_host', 'origin_ip', 'origin_port', 'upstream_bind_host', 'upstream_bind_port', 'original_url'):
        assert route[key] == config[key]
    if route.get('mode', 'local_ssh_L') == 'mac_ssh_reverse':
        assert route.get('root_reviewed') is True and route.get('owner_fd_visibility') is False
        mac, connection = route['mac_ssh'], route['listener']
        assert isinstance(mac['pid'], int) and mac['pid'] > 0 and mac['ps_lstart'].strip()
        argv = mac['argv']
        assert Path(argv[0]).name == 'ssh' and shlex.split(mac['actual_ps_command']) == argv
        assert mac['control_master_check'] == f"Master running (pid={mac['pid']})"
        def options(flag):
            return [argv[i + 1] if value == flag else value[len(flag):]
                    for i, value in enumerate(argv) if value == flag or value.startswith(flag)]
        forward = f"127.0.0.1:{config['upstream_bind_port']}:{config['origin_ip']}:443"
        assert options('-R') == [forward]
        assert options('-S') == [route['same_connection_control_socket']] == ['/tmp/apex-t774-route-20261017.ctl']
        assert connection['bind_host'] == '127.0.0.1' and connection['bind_port'] == config['upstream_bind_port']
        assert connection['comm'] == 'sshd'
        pid = connection['pid']
        if ticks(pid) != connection['startticks']:
            return False
        assert Path('/proc', str(pid), 'comm').read_text().strip() == connection['comm']
        proof = route['ancestorproof']
        assert all(child['ppid'] == parent['pid'] for child, parent in zip(proof, proof[1:]))
        assert any(row['pid'] == pid and row['startticks'] == connection['startticks'] and row['comm'] == 'sshd' for row in proof)
        assert any(row['ppid'] == pid and row['comm'] == 'sshd' for row in proof)
        assert sha(Path(route['host_head_receipt'])) == route['host_head_receipt_sha256']
        rows = subprocess.check_output(['ss', '-lntp', 'sport = :' + str(config['upstream_bind_port'])], text=True).splitlines()[1:]
        if not rows:
            return False
        # The root-owned sshd FD is not visible to this user. This proves a live
        # same-connection sshd and unique loopback bind, not direct FD ownership.
        assert len(rows) == 1 and rows[0].split()[3] == f"127.0.0.1:{config['upstream_bind_port']}"
        return True
    assert route.get('mode', 'local_ssh_L') == 'local_ssh_L'
    pid = route['ssh_pid']
    if ticks(pid) != route['ssh_startticks']:
        return False
    proc = Path('/proc', str(pid))
    assert (proc / 'comm').read_text().strip() == 'ssh'
    if (proc / 'stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z':
        return False
    args = (proc / 'cmdline').read_bytes().decode().split('\0')
    forward = f"127.0.0.1:{config['upstream_bind_port']}:{config['origin_ip']}:443"
    assert forward in args or '-L' + forward in args, 'Route is not the fixed original-origin SSH local forward'
    listener = subprocess.check_output(['ss', '-lntp', 'sport = :' + str(config['upstream_bind_port'])], text=True)
    return f'pid={pid},' in listener


def configured(config, manifest):
    original = copy.deepcopy(read(ROOT / config['original_config']))
    original['trials_dir'] = str(ROOT / config['output'] / 'attempt1/native')
    original['environment']['import_path'] = MODULE + ':AvgOriginalProxyEnvironment'
    original['environment']['kwargs'].update(baseline_cpu_offset=0, baseline_cpu_slots=1,
        avg_proxy_manifest=str(manifest))
    return original


def validate(config, manifest):
    assert config['key'] == 'avg64/teleport7744' and config['model'] == 'apex-avg64'
    assert config['origin_ip'] == '142.250.73.145' and config['original_url'] == URL
    assert config['origin_host'] == 'proxy.golang.org' and config['origin_port'] == 443
    assert config['upstream_bind_host'] == '127.0.0.1' and config['upstream_bind_port'] == 38444
    assert config['minimum_runway_seconds'] >= 7200
    assert config['lease_cpus'] == sorted(POOL) and config['native_cpu'] == 124
    assert config['logical_cpu_offset'] == 0 and config['memory_mib'] == 4096 and config['verifier_seconds'] == 3000
    assert all(sha(ROOT / p) == h for p, h in config['source_sha256'].items()), 'Frozen source changed'
    original = read(ROOT / config['original_config'])
    assert original['trial_name'] == config['task_id']
    assert read(ROOT / config['source_output'] / 'generation' / config['task_id'] / 'config.json')['agent']['model_name'] == 'openai/apex-avg64'
    assert original['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
    assert original['agent']['kwargs']['source_job'] == str(ROOT / config['source_output'] / 'generation')
    assert original['agent']['override_timeout_sec'] == config['patch_replay_seconds'] == 1800
    assert original['environment']['import_path'] == 'swe_clean_musl_runtime:SweCleanMuslScoreEnvironment'
    assert original['environment']['override_cpus'] == 1 and original['environment']['override_memory_mb'] == 4096
    assert original['environment']['override_gpus'] == 0 and original['verifier']['override_timeout_sec'] == 3000
    assert original['environment']['cpu_enforcement_policy'] == original['environment']['memory_enforcement_policy'] == 'limit'
    assert read(ROOT / config['original_result'])['task_checksum'] == config['task_checksum']
    assert (ROOT / config['patch']).stat().st_size == config['patch_bytes'] == 0
    image = ROOT / config['sif']
    assert image.stat().st_size == config['sif_size'] and str(image.stat().st_mtime_ns) == config['sif_mtime_ns']
    assert POOL <= effective_cpus(), 'Parent cgroup cannot admit CPU124'
    assert len(os.fsencode(Path(config['host_tmpdir']) / 'apex_baseline_net_XXXXXXXX/control.sock')) < 108
    assert len(os.fsencode(config['private_proxy_socket'])) < 108
    assert not (ROOT / config['output'] / 'attempt1').exists(), 'Existing attempt retained; no retry'
    assert terminal_contract(config)
    named = importlib.import_module(MODULE)
    assert Path(named.__file__) == Path(__file__) and issubclass(named.AvgOriginalProxyEnvironment, SweCleanMuslScoreEnvironment)
    TrialConfig.model_validate(configured(config, manifest))


async def copy_stream(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()


async def connect_proxy(config, reader, writer):
    other = None
    try:
        header = await reader.readuntil(b'\r\n\r\n')
        method, host, _ = header.split(b'\r\n', 1)[0].decode().split()
        allowed = method == 'CONNECT' and host == 'proxy.golang.org:443'
        with (ROOT / config['output'] / 'attempt1/connect_requests.jsonl').open('a') as log:
            log.write(json.dumps({'at_utc': now(), 'method': method, 'host': host, 'allowed': allowed}) + '\n')
        if not allowed:
            writer.write(b'HTTP/1.1 403 Forbidden\r\n\r\n'); await writer.drain(); return
        upstream, other = await asyncio.open_connection(config['upstream_bind_host'], config['upstream_bind_port'])
        writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n'); await writer.drain()
        tasks = [asyncio.create_task(copy_stream(reader, other)), asyncio.create_task(copy_stream(upstream, writer))]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (OSError, ValueError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()
        if other:
            other.close()


class AvgOriginalProxyEnvironment(DiskScratchAndLogs, SweCleanMuslScoreEnvironment):
    def __init__(self, *args, avg_proxy_manifest, **kwargs):
        self._avg_manifest = Path(avg_proxy_manifest)
        self._avg_config = read(self._avg_manifest)
        self.scratch_root = ROOT / self._avg_config['output'] / 'attempt1/scratch'
        super().__init__(*args, **kwargs)

    async def _start_server(self):
        await super()._start_server()
        config = self._avg_config
        self._avg_log = (ROOT / config['output'] / 'attempt1/namespace-proxy.log').open('x')
        self._avg_relay = subprocess.Popen(self._namespace.command(sys.executable, str(Path(__file__)),
            '--manifest', str(self._avg_manifest), '--namespace-relay'), stdout=self._avg_log, stderr=self._avg_log)
        ready = ROOT / config['output'] / 'attempt1/namespace-proxy-ready.json'
        for _ in range(400):
            assert self._avg_relay.poll() is None, 'Private namespace relay exited'
            if ready.exists() and read(ready)['pid'] == self._avg_relay.pid:
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError('Private namespace relay did not bind')
        probe = await super().exec('/opt/apex-swe-tools/curl --fail --silent --show-error --max-time 20 '
            '--proxy http://127.0.0.1:18002 --output /tmp/apex-original-go-proxy-list --write-out "%{http_code}" '
            + shlex.quote(URL), timeout_sec=25)
        receipt = {'at_utc': now(), 'url': URL, 'return_code': probe.return_code,
            'http_status': (probe.stdout or '').strip(), 'stderr': probe.stderr, 'origin_ip': config['origin_ip'],
            'scope': self._scope_unit, 'tls_verification_disabled': False, 'model_calls': 0,
            'official_verifier_started': False}
        receipt['passed'] = probe.return_code == 0 and receipt['http_status'] == '200'
        save(ROOT / config['output'] / 'attempt1/native-proxy-probe.json', receipt)
        if not receipt['passed']:
            raise RuntimeError('Original URL native probe failed before replay/verifier')

    async def exec(self, command, *args, env=None, **kwargs):
        if '/tests/test.sh' in command:
            env = {**(env or {}), 'HTTPS_PROXY': 'http://127.0.0.1:18002',
                   'https_proxy': 'http://127.0.0.1:18002', 'NO_PROXY': 'localhost,127.0.0.1,::1'}
            save(ROOT / self._avg_config['output'] / 'attempt1/verifier-started.json',
                {'at_utc': now(), 'original_test_command': command, 'verifier_seconds': 3000, 'model_calls': 0})
        return await super().exec(command, *args, env=env, **kwargs)

    async def _stop_server_process(self):
        try:
            return await super()._stop_server_process()
        finally:
            relay = getattr(self, '_avg_relay', None)
            if relay and relay.poll() is None:
                relay.terminate(); await asyncio.to_thread(relay.wait, 5)
            if getattr(self, '_avg_log', None):
                self._avg_log.close()


async def namespace_relay(config):
    # Called only through the pinned NetworkNamespace.command (nsenter --user --net).
    claim = read(ROOT / config['output'] / 'attempt1/execution-claim.json')
    assert ticks(claim['pid']) == claim['startticks']
    async def forward(reader, writer):
        other = None
        try:
            upstream, other = await asyncio.open_unix_connection(config['private_proxy_socket'])
            tasks = [asyncio.create_task(copy_stream(reader, other)), asyncio.create_task(copy_stream(upstream, writer))]
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            writer.close()
            if other:
                other.close()
    server = await asyncio.start_server(forward, '127.0.0.1', 18002)
    save(ROOT / config['output'] / 'attempt1/namespace-proxy-ready.json',
         {'pid': os.getpid(), 'startticks': ticks(os.getpid()), 'at_utc': now(), 'bound_port': 18002})
    async with server:
        await server.serve_forever()


async def grade(config, manifest):
    socket = Path(config['private_proxy_socket'])
    assert not socket.exists(), 'Private socket already exists; do not unlink another consumer'
    server = await asyncio.start_unix_server(lambda r, w: connect_proxy(config, r, w), str(socket))
    socket.chmod(0o600)
    try:
        trial = await Trial.create(TrialConfig.model_validate(configured(config, manifest)))
        assert trial.task.checksum == config['task_checksum']
        async with server:
            await trial.run()
    finally:
        server.close(); await server.wait_closed(); socket.unlink(missing_ok=True)


def run(config, manifest):
    attempt = ROOT / config['output'] / 'attempt1'
    attempt.mkdir(parents=True, exist_ok=False)
    env = production_env(config)
    state = {'pid': os.getpid(), 'startticks': ticks(os.getpid()), 'state': 'waiting_source_handoff',
             'lock_held': False, 'model_calls': 0, 'accepted_into_formal_summary': False}
    frozen = {**{str(ROOT / p): h for p, h in config['source_sha256'].items()},
              str(manifest): sha(manifest), str(Path(__file__)): sha(Path(__file__))}
    save(attempt / 'execution-claim.json', {**state, 'at_utc': now(), 'bound_sha256': frozen})
    os.sched_setaffinity(0, {10})
    signal.signal(signal.SIGTERM, lambda *_: state.update(stop_requested=True))
    signal.signal(signal.SIGINT, lambda *_: state.update(stop_requested=True))
    enough = lambda: datetime.fromisoformat(config['core_deadline']).timestamp() - time.time() >= config['minimum_runway_seconds']
    def checkpoint(label, **fields):
        state.update(state=label, at_utc=now(), **fields)
        try:
            save(attempt / 'parent-state.json', state)
        except OSError:
            state['checkpoint_write_failed'] = True
    unit = 'apex-baseline-avg-t7744-' + str(os.getpid())
    def drain(ignore_guard=False):
        samples = []
        while len(samples) < 2:
            try:
                busy = pool_scopes(unit + '.scope' if ignore_guard else None)
            except Exception as error:
                samples = []
                checkpoint('waiting_scope_observer', observer_error_type=type(error).__name__)
                time.sleep(2)
                continue
            samples = [] if busy else samples + [{'at_utc': now(), 'remaining_scopes': []}]
            checkpoint('draining_native' if ignore_guard else 'draining_after_guard_stop', remaining_scopes=busy)
            if len(samples) < 2:
                time.sleep(2)
        return samples
    guard, child = None, None
    with (ROOT / config['shared_lock']).open('a+') as lease:
        while True:
            if not enough() or state.get('stop_requested'):
                checkpoint('stopped_before_native'); return
            assert terminal_contract(config)
            if not generation_released(config) or not route_ready(config):
                checkpoint('waiting_source_or_route'); time.sleep(5); continue
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_private_lease'); time.sleep(5); continue
            if not pool_scopes():
                break
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint('waiting_actual_source_scope_drain'); time.sleep(5)
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
            assert enough() and generation_released(config) and terminal_contract(config) and route_ready(config)
            assert not state.get('stop_requested') and not pool_scopes(unit + '.scope')
            assert all(sha(Path(p)) == h for p, h in frozen.items())
            checkpoint('guard_verified', guard_observed={'unit': unit + '.scope', 'affinities': affinity,
                'memory_max': 33554432, 'memory_swap_max': 0}, generation_source=read(ROOT / config['generation_marker']),
                generation_marker_sha256=sha(ROOT / config['generation_marker']), route_receipt_sha256=sha(ROOT / config['route_receipt']))
            for path in (ROOT / config['generation_marker'], ROOT / config['route_receipt']):
                frozen[str(path)] = sha(path)
            save(attempt / 'admission.json', {**state, 'bound_sha256': frozen})
            command = ['taskset', '-c', '124', sys.executable, str(Path(__file__)), '--manifest', str(manifest),
                       '--child', '--lease-fd', str(lease.fileno())]
            with (attempt / 'native-child.log').open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, pass_fds=(lease.fileno(),))
            checkpoint('native_running', child_pid=child.pid, child_startticks=ticks(child.pid), command=command)
            child.wait()
            result_path = attempt / 'native' / config['task_id'] / 'result.json'
            result = read(result_path) if result_path.exists() else {}
            checkpoint('finished_pending_root_review', child_returncode=child.returncode, native_result=str(result_path),
                native_reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                exception_type=(result.get('exception_info') or {}).get('exception_type'),
                original_sources_unchanged=all(sha(Path(p)) == h for p, h in frozen.items()))
        except Exception as error:
            checkpoint('failed_pending_root_review', error_type=type(error).__name__); raise
        finally:
            final_state = state['state']
            if child is not None:
                child.wait()
            native_samples = drain(ignore_guard=True)
            if guard is not None:
                subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], env=env)
                guard.wait(timeout=10)
            full_samples = drain()
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint(final_state, lock_held=False, guard_stopped=True, released_at_utc=now(),
                consecutive_empty_native_scope_samples=native_samples,
                consecutive_empty_scope_samples_after_guard_stop=full_samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/avg64_teleport7744_grade_only_20261017.json')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--lease-fd', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--namespace-relay', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(); args.manifest = args.manifest.absolute(); config = read(args.manifest)
    if args.namespace_relay:
        asyncio.run(namespace_relay(config)); return
    if args.child:
        claim = read(ROOT / config['output'] / 'attempt1/execution-claim.json')
        assert ticks(claim['pid']) == claim['startticks'] and os.sched_getaffinity(0) == {124}
        assert Path('/proc/self/fd/' + str(args.lease_fd)).resolve() == ROOT / config['shared_lock']
        admission = read(ROOT / config['output'] / 'attempt1/admission.json')
        assert admission['pid'] == claim['pid'] and admission['startticks'] == claim['startticks']
        assert all(sha(Path(p)) == h for p, h in admission['bound_sha256'].items())
        os.environ.update(production_env(config)); asyncio.run(grade(config, args.manifest)); return
    validate(config, args.manifest)
    if args.execute:
        run(config, args.manifest); return
    print(json.dumps({'at_utc': now(), 'mode': 'prepare_only', 'bindings_verified': len(config['source_sha256']),
        'script_sha256': sha(Path(__file__)), 'manifest_sha256': sha(args.manifest),
        'generation_released': generation_released(config), 'terminal_contract_verified': True,
        'busy_scopes_on_124_127': pool_scopes(), 'route_receipt_exists': (ROOT / config['route_receipt']).exists(),
        'route_ready': route_ready(config), 'original_ip': config['origin_ip'],
        'namespace_socket_bytes': len(os.fsencode(Path(config['host_tmpdir']) / 'apex_baseline_net_XXXXXXXX/control.sock')),
        'private_socket_bytes': len(os.fsencode(config['private_proxy_socket'])),
        'claim_created': False, 'lock_acquired': False, 'native_started': False, 'network_probes': 0,
        'new_ssh_forward': False, 'model_calls': 0, 'new_api_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
