"""One approved fixed-patch replay with a task-local original Go-proxy route."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from harbor.models.trial.config import TrialConfig
from harbor.trial.trial import Trial
from release_validation_cpus import base_scopes
from swe_baseline_v2 import ROOT, save_json
from swe_clean_musl_runtime import SweCleanMuslScoreEnvironment

TASK = 'instance_gravitational__teleport-7744f72c6eb631791434b648ba41083b5f6d2278-vce94f93ad1030e3136852817f2423c1b3ac37bc4'
NODEBB = 'instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e'
SOURCE = ROOT / 'artifacts/eval/swe249_hard51_20261016'
OUTPUT = ROOT / 'artifacts/eval/swe249_teleport7744_proxy_repair_20261017'
SOCKET = Path('/tmp/apex-swe249-original-proxy.sock')


def now():
    return datetime.now(timezone.utc).isoformat()


async def copy(reader, writer):
    while data := await reader.read(65536):
        writer.write(data)
        await writer.drain()


async def connect_proxy(reader, writer):
    other = None
    try:
        request = await reader.readuntil(b'\r\n\r\n')
        method, address, _ = request.split(b'\r\n', 1)[0].decode().split()
        allowed = method == 'CONNECT' and address == 'proxy.golang.org:443'
        with (OUTPUT / 'connect_requests.jsonl').open('a') as log:
            log.write(json.dumps({'at': now(), 'method': method, 'address': address,
                                 'allowed': allowed}) + '\n')
        if not allowed:
            writer.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
            await writer.drain()
            return
        upstream, other = await asyncio.open_connection('127.0.0.1', 38443)
        writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
        await writer.drain()
        tasks = [asyncio.create_task(copy(reader, other)),
                 asyncio.create_task(copy(upstream, writer))]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (OSError, asyncio.IncompleteReadError, ValueError):
        pass
    finally:
        writer.close()
        if other:
            other.close()


class SweOriginalProxyScoreEnvironment(SweCleanMuslScoreEnvironment):
    async def _start_server(self):
        await super()._start_server()
        self._original_proxy_relay = subprocess.Popen(self._namespace.command(
            sys.executable, str(Path(__file__).resolve()), '--namespace-relay'),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(0.3)
        probe = await super().exec(
            '/opt/apex-swe-tools/curl --fail --silent --show-error --max-time 20 '
            '--proxy http://127.0.0.1:18002 '
            '--output /tmp/apex-original-go-proxy-list '
            '--write-out "%{http_code}" '
            'https://proxy.golang.org/github.com/mdlayher/netlink/@v/list',
            timeout_sec=25)
        receipt = {'at': now(), 'url': 'https://proxy.golang.org/github.com/mdlayher/netlink/@v/list',
            'return_code': probe.return_code, 'http_status': (probe.stdout or '').strip(),
            'stderr': probe.stderr, 'scope': self._scope_unit,
            'cpu': 10, 'memory_mib': 4096, 'tls_verification_disabled': False,
            'original_origin_ip': '142.251.34.209', 'model_calls': 0,
            'official_verifier_started': False}
        receipt['passed'] = probe.return_code == 0 and receipt['http_status'] == '200'
        save_json(OUTPUT / 'native_proxy_probe.json', receipt)
        if not receipt['passed']:
            raise RuntimeError('Original Go-proxy native probe failed; verifier not started')

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command:
            env = {**(env or {}), 'HTTPS_PROXY': 'http://127.0.0.1:18002',
                   'https_proxy': 'http://127.0.0.1:18002',
                   'NO_PROXY': 'localhost,127.0.0.1,::1'}
            save_json(OUTPUT / 'official_verifier_started.json', {'at': now(),
                'scope': self._scope_unit, 'original_test_command': command,
                'verifier_timeout_seconds': 3000, 'model_calls': 0})
        return await super().exec(command, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user)

    async def _stop_server_process(self):
        try:
            return await super()._stop_server_process()
        finally:
            relay = getattr(self, '_original_proxy_relay', None)
            if relay and relay.poll() is None:
                relay.terminate()
                await asyncio.to_thread(relay.wait, 5)


async def namespace_relay():
    async def forward(reader, writer):
        other = None
        try:
            upstream, other = await asyncio.open_unix_connection(str(SOCKET))
            tasks = [asyncio.create_task(copy(reader, other)),
                     asyncio.create_task(copy(upstream, writer))]
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            writer.close()
            if other:
                other.close()
    server = await asyncio.start_server(forward, '127.0.0.1', 18002)
    async with server:
        await server.serve_forever()


def config_for(task, cpu, output):
    config = json.loads((SOURCE / 'replay' / task / 'config.json').read_text())
    config['trials_dir'] = str(output)
    config['environment']['kwargs']['baseline_cpu_offset'] = cpu
    config['environment']['kwargs']['baseline_cpu_slots'] = 1
    assert config['environment']['override_cpus'] == 1
    assert config['environment']['override_memory_mb'] == 4096
    assert config['verifier']['override_timeout_sec'] == 3000
    assert config['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
    assert config['agent']['kwargs']['source_job'] == str(SOURCE / 'generation')
    return config


async def nodebb_probe():
    assert not base_scopes({11}), 'CPU11 already leased'
    path = OUTPUT / 'nodebb_pristine_probe'
    config = config_for(NODEBB, 11, path)
    trial = await Trial.create(TrialConfig.model_validate(config))
    environment = trial.agent_environment
    try:
        await environment.start(force_build=False)
        result = await environment.exec(
            'cd /app; git status --short; printf "\\n---MOCHA---\\n"; '
            'git ls-files --stage .mocharc.yml; '
            'if [ -f .mocharc.yml ]; then cat .mocharc.yml; else echo MISSING; fi; '
            'printf "\\n---PRISTINE-DIFFSTAT---\\n"; git diff --stat', timeout_sec=30)
        save_json(OUTPUT / 'nodebb_pristine_probe.json', {'at': now(),
            'task': NODEBB, 'scope': environment._scope_unit, 'cpu': 11,
            'return_code': result.return_code, 'stdout': result.stdout, 'stderr': result.stderr,
            'model_calls': 0, 'agent_ran': False, 'verifier_ran': False,
            'source_task_modified': False})
    finally:
        await environment.stop(delete=True)
        await trial._close_bridge()
        trial._close_logger_handler()
    save_json(OUTPUT / 'nodebb_probe_cpu_finished.json', {'at': now(),
        'active_scopes': base_scopes({11}), 'cpu': 11})


async def replay():
    assert not base_scopes({10}), 'CPU10 already leased'
    assert not (OUTPUT / 'replay').exists(), 'Preserve previous repair attempt'
    patch = SOURCE / 'generation' / TASK / 'agent/model.patch'
    before = hashlib.sha256(patch.read_bytes()).hexdigest()
    save_json(OUTPUT / 'repair_manifest.json', {'at': now(), 'task': TASK,
        'source_generation': str(SOURCE / 'generation'),
        'original_invalid_result': str(SOURCE / 'replay' / TASK / 'result.json'),
        'source_patch_sha256': before, 'source_patch_bytes': patch.stat().st_size,
        'cpu': 10, 'cpus': 1, 'memory_mib': 4096, 'verifier_timeout_seconds': 3000,
        'original_origin_ip': '142.251.34.209', 'original_uri_unchanged': True,
        'tls_sni_and_certificate_validation_preserved': True, 'model_calls': 0,
        'canonical_outputs_modified': False, 'scope_name_prefix': 'apex-baseline-'})
    if SOCKET.exists():
        SOCKET.unlink()
    server = await asyncio.start_unix_server(connect_proxy, str(SOCKET))
    SOCKET.chmod(0o600)
    try:
        config = config_for(TASK, 10, OUTPUT / 'replay')
        config['environment']['import_path'] = 'swe_score_original_proxy_repair:SweOriginalProxyScoreEnvironment'
        trial = await Trial.create(TrialConfig.model_validate(config))
        async with server:
            result = await trial.run()
        assert hashlib.sha256(patch.read_bytes()).hexdigest() == before
        save_json(OUTPUT / 'repair_finished.json', {'at': now(), 'model_calls': 0,
            'source_patch_unchanged': True,
            'result': str(OUTPUT / 'replay' / TASK / 'result.json'),
            'exception_type': result.exception_info.exception_type if result.exception_info else None,
            'reward': result.verifier_result.rewards if result.verifier_result else None,
            'active_scopes': base_scopes({10}), 'canonical_outputs_modified': False})
    finally:
        server.close()
        await server.wait_closed()
        SOCKET.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace-relay', action='store_true')
    parser.add_argument('--nodebb-probe', action='store_true')
    args = parser.parse_args()
    tools = ROOT / 'artifacts/tools'
    path = [tools / 'apptainer-1.4.5/rootfs/usr/bin',
            tools / 'fakeroot-1.25.3/rootfs/usr/bin']
    if not args.nodebb_probe and not args.namespace_relay:
        path.insert(0, ROOT / 'artifacts/preflight/swe_v2/musl_compat/shim')
    os.environ['PATH'] = ':'.join(map(str, path)) + ':' + os.environ['PATH']
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.namespace_relay:
        asyncio.run(namespace_relay())
    elif args.nodebb_probe:
        asyncio.run(nodebb_probe())
    else:
        asyncio.run(replay())
