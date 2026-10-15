"""Local synthetic checks; no Harbor install, container, model, or remote host needed."""
import argparse
import ast
import asyncio
import inspect
import json
import logging
import os
from pathlib import Path
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, HTTPServer


class RequestError(Exception):
    pass


class ConnectError(RequestError):
    pass


class Denied(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code


class LocalClient:
    def __init__(self, **kwargs):
        assert kwargs.get('trust_env') is False
        assert kwargs.get('follow_redirects') is False

    async def request(self, method, url, timeout):
        async def exchange():
            target = urlsplit(url)
            reader, writer = await asyncio.open_connection(target.hostname, target.port)
            try:
                writer.write((f'{method} {target.path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n').encode())
                await writer.drain()
                headers = await reader.readuntil(b'\r\n\r\n')
                length = int(next(line.split(b':', 1)[1] for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:')))
                body = await reader.readexactly(length)
                return SimpleNamespace(status_code=int(headers.split()[1]), json=lambda: json.loads(body))
            finally:
                writer.close()
                await writer.wait_closed()
        try:
            return await asyncio.wait_for(exchange(), timeout)
        except ConnectionRefusedError as exc:
            raise ConnectError(str(exc)) from exc
        except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as exc:
            raise RequestError(str(exc)) from exc

    async def get(self, url, timeout=2):
        return await self.request('GET', url, timeout)

    async def post(self, url, timeout=2):
        return await self.request('POST', url, timeout)

    async def aclose(self):
        pass


def load_methods(source, apex_source, fixture_dir):
    """Execute actual patched methods, replacing only imports and the container binary."""
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SingularityEnvironment')
    names = {'__init__', '_staging', '_reserve_port', '_shutdown_owned_server',
             '_stop_server_process', '_cleanup_server_resources', '_start_server', 'start', 'stop'}
    body = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    for node in body:
        node.decorator_list = [d for d in node.decorator_list if not isinstance(d, ast.Name) or d.id != 'override']
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                             ast.ClassDef(name='CheckedEnvironment', bases=[], keywords=[], body=body, decorator_list=[])], type_ignores=[])
    namespace = dict(asyncio=asyncio, os=os, sys=sys, secrets=secrets, socket=socket,
                     tempfile=SimpleNamespace(mkdtemp=lambda **kw: tempfile.mkdtemp(dir=fixture_dir, **kw)),
                     shutil=shutil, subprocess=subprocess, Path=Path,
                     httpx=SimpleNamespace(AsyncClient=LocalClient, RequestError=RequestError, ConnectError=ConnectError),
                     __file__=str(fixture_dir / 'singularity.py'))
    exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), namespace)
    namespace['SingularityEnvironment'] = namespace['CheckedEnvironment']
    apex = next(n for n in ast.parse(apex_source.read_text()).body if isinstance(n, ast.ClassDef))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[apex], type_ignores=[])), str(apex_source), 'exec'), namespace)
    assert 'stop' not in namespace['ApexSingularityEnvironment'].__dict__
    return namespace['ApexSingularityEnvironment']


def load_handlers(source, token, kill=os.kill):
    handlers = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.AsyncFunctionDef) and n.name in {'health_check', 'shutdown'}]
    for handler in handlers:
        handler.decorator_list = []
    scope = dict(app=SimpleNamespace(state=SimpleNamespace(instance_token=token)),
                 HTTPException=Denied, asyncio=asyncio, signal=signal,
                 os=SimpleNamespace(getpid=os.getpid, kill=kill), logger=logging.getLogger('synthetic'))
    exec(compile(ast.fix_missing_locations(ast.Module(body=handlers, type_ignores=[])), str(source), 'exec'), scope)
    return scope


def child_server(port, token, delay, legacy=False):
    time.sleep(delay)
    handlers = load_handlers(Path(os.environ['APEX_CHECK_SERVER']), token)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

        def do_GET(self):
            self.reply(200, asyncio.run(handlers['health_check']()))

        def do_POST(self):
            accepted = self.path == ('/shutdown' if legacy else '/shutdown/' + token)
            with (Path(os.environ['APEX_CHECK_DIR']) / 'posts.jsonl').open('a') as stream:
                stream.write(json.dumps({'port': port, 'accepted': accepted}) + '\n')
            if legacy:
                self.reply(200 if accepted else 404, {})
            elif self.path.startswith('/shutdown/'):
                async def shutdown_with_real_delay():
                    try:
                        result = await handlers['shutdown'](self.path[len('/shutdown/'):])
                        self.reply(200, result)
                        # The real handler schedules SIGTERM after 0.1 sec.
                        await asyncio.sleep(0.5)
                    except Denied as exc:
                        self.reply(exc.status_code, {})
                asyncio.run(shutdown_with_real_delay())
            else:
                self.reply(404, {})
            if accepted and legacy:
                threading.Thread(target=self.server.shutdown, daemon=True).start()
    with HTTPServer(('127.0.0.1', port), Handler) as server:
        server.serve_forever(poll_interval=0.01)


def fake_launcher(argv):
    port = argv[argv.index('--port') + 1]
    token = argv[argv.index('--instance-token') + 1]
    child = subprocess.Popen([sys.executable, __file__, '--child-server', port, token,
                              os.environ.get('APEX_CHECK_DELAY', '0')])
    with (Path(os.environ['APEX_CHECK_DIR']) / 'children.txt').open('a') as stream:
        stream.write(str(child.pid) + '\n')
    time.sleep(60)


async def check_pipe_regression():
    # Exact old failure pattern: launcher killed, detached child retains stdout PIPE.
    script = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True); print(p.pid,flush=True); time.sleep(30)"
    process = await asyncio.create_subprocess_exec(sys.executable, '-c', script, stdout=asyncio.subprocess.PIPE)
    child = int(await process.stdout.readline())
    waiter = asyncio.create_task(process.wait())
    await asyncio.sleep(0)
    process.kill()
    try:
        try:
            await asyncio.wait_for(waiter, 0.15)
        except asyncio.TimeoutError:
            print('PASS: original inherited-PIPE wait reproduces timeout')
        else:
            raise AssertionError('Old PIPE failure did not reproduce')
    finally:
        os.kill(child, signal.SIGTERM)
        await asyncio.wait_for(process.wait(), 1)


async def run_checks(source, apex_source):
    with tempfile.TemporaryDirectory(prefix='harbor-startup-check-') as directory:
        root = Path(directory)
        for name in ['server.py', 'bootstrap.sh']:
            (root / name).write_text('# synthetic fixture only\n')
        launcher = root / 'singularity'
        launcher.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} --launcher "$@"\n')
        launcher.chmod(0o700)
        env_before = dict(os.environ)
        os.environ.update(PATH=str(root) + ':' + os.environ['PATH'], APEX_CHECK_DIR=str(root), APEX_CHECK_SERVER=str(source.with_name('server.py')))
        Checked = load_methods(source, apex_source, root)
        assert inspect.signature(Checked.__init__).parameters['singularity_startup_timeout_sec'].default == 300.0

        def environment(timeout):
            async def noop(): pass
            env = object.__new__(Checked)
            env.__dict__.update(_server_process=None, _server_port=None, _server_token=None,
                                _server_log_path=None, _preserve_startup_log=False,
                                _http_client=None, _staging_dir=None, _memory_watchdog_task=None,
                                _memory_limit_bytes=None, _mounts=[], _singularity_no_mount=None,
                                _startup_timeout_sec=timeout, _workdir='/tmp', _sif_path='synthetic.sif',
                                _docker_image='synthetic.sif', _is_sif_image=True,
                                _upload_environment_dir_after_start=noop,
                                environment_dir=root / 'environment', logger=logging.getLogger('synthetic'))
            env.environment_dir.mkdir(exist_ok=True)
            return env

        try:
            await check_pipe_regression()
            # Exercise the patched server's actual auth handler, without FastAPI.
            kills = []
            scope = load_handlers(source.with_name('server.py'), 'expected', lambda *args: kills.append(args))
            assert (await scope['health_check']())['instance_token'] == 'expected'
            try:
                await scope['shutdown']('foreign')
            except Denied as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError('Server accepted another instance token')
            assert not kills
            await scope['shutdown']('expected')
            await asyncio.sleep(0.15)
            assert kills == [(os.getpid(), signal.SIGTERM)]
            print('PASS: actual server handler rejects wrong token and shuts down expected instance')
            # Normal startup and authenticated detached-server shutdown.
            os.environ['APEX_CHECK_DELAY'] = '0.05'
            normal = environment(2.5)
            await normal.start(force_build=False)
            assert normal._server_process.stdout is None  # direct file, no inherited PIPE
            port = normal._server_port
            await normal.stop(delete=False)
            assert not normal._preserve_startup_log
            with socket.socket() as probe:
                assert probe.connect_ex(('127.0.0.1', port)) != 0
            print('PASS: delayed startup, owned shutdown, launcher exit; no PIPE')

            # No listener yet: return promptly, preserve log, report unconfirmed shutdown.
            os.environ['APEX_CHECK_DELAY'] = '30'
            cold = environment(0.1)
            started = time.monotonic()
            try:
                await cold.start(force_build=False)
            except RuntimeError as exc:
                assert 'exceeded' in str(exc)
            else:
                raise AssertionError('Startup timeout did not fail')
            assert time.monotonic() - started < 1
            assert cold._server_process.returncode is not None and cold._server_log_path.exists()
            assert cold._preserve_startup_log
            print('PASS: startup deadline returns; unconfirmed detached-bootstrap boundary retained')

            cancelled = environment(30)
            pending = asyncio.create_task(cancelled.start(force_build=False))
            while cancelled._server_process is None:
                await asyncio.sleep(0.01)
            pending.cancel()
            try:
                await asyncio.wait_for(pending, 1)
            except asyncio.CancelledError:
                pass
            assert cancelled._server_process.returncode is not None
            assert cancelled._preserve_startup_log and cancelled._server_log_path.exists()
            print('PASS: cancelled startup keeps its log and cleans the held launcher')

            # Public start remains responsible until the upload step completes.
            os.environ['APEX_CHECK_DELAY'] = '0'
            uploading = environment(2.5)
            upload_started = asyncio.Event()
            async def blocked_upload():
                upload_started.set()
                await asyncio.Future()
            uploading._upload_environment_dir_after_start = blocked_upload
            pending = asyncio.create_task(uploading.start(force_build=False))
            await asyncio.wait_for(upload_started.wait(), 3)
            pending.cancel()
            try:
                await asyncio.wait_for(pending, 1)
            except asyncio.CancelledError:
                pass
            with socket.socket() as probe:
                assert probe.connect_ex(('127.0.0.1', uploading._server_port)) != 0
            assert uploading._preserve_startup_log and uploading._server_log_path.exists()
            print('PASS: cancelled upload after readiness shuts down its owned server')

            # A foreign legacy server accepts /shutdown, so it must never receive that URL.
            reserved, foreign_port = normal._reserve_port()
            reserved.close()
            foreign = subprocess.Popen([sys.executable, __file__, '--child-server', str(foreign_port), 'foreign', '0', '--legacy'])
            try:
                client = LocalClient(trust_env=False, follow_redirects=False)
                for _ in range(20):
                    try:
                        await client.get(f'http://127.0.0.1:{foreign_port}/health')
                        break
                    except RequestError:
                        await asyncio.sleep(0.02)
                collision = environment(1)
                collision._reserve_port = lambda: (SimpleNamespace(close=lambda: None), foreign_port)
                try:
                    await collision.start(force_build=False)
                except RuntimeError as exc:
                    assert 'collision' in str(exc)
                else:
                    raise AssertionError('Foreign server accepted as owned')
                assert foreign.poll() is None
                # Simulate port reuse between the matching health response and POST.
                race = environment(1)
                race._server_port, race._server_token = foreign_port, 'expected'
                race._http_client = client
                original_get = client.get
                async def prior_owned_health(*args, **kwargs):
                    return SimpleNamespace(status_code=200, json=lambda: {'instance_token': 'expected'})
                client.get = prior_owned_health
                assert not await race._shutdown_owned_server()
                client.get = original_get
                assert foreign.poll() is None
                posts = [json.loads(x) for x in (root / 'posts.jsonl').read_text().splitlines()]
                assert not any(p['accepted'] for p in posts if p['port'] == foreign_port)
                print('PASS: wrong-token health and legacy port-reuse race do not shut down foreign server')
            finally:
                foreign.terminate()
                foreign.wait(timeout=1)

            class StubbornLauncher:
                returncode = None
                terminated = killed = False
                def terminate(self): self.terminated = True
                def kill(self): self.killed = True
                async def wait(self): await asyncio.Future()
            stubborn = environment(1)
            stubborn._server_process = StubbornLauncher()
            await asyncio.wait_for(stubborn._stop_server_process(), 8)
            assert stubborn._server_process.terminated and stubborn._server_process.killed
            assert stubborn._preserve_startup_log
            print('PASS: terminate and kill waits both remain bounded')
        finally:
            # Only fixture PIDs explicitly created by this script; no process searches.
            children = root / 'children.txt'
            if children.exists():
                for pid in map(int, children.read_text().splitlines()):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            os.environ.clear()
            os.environ.update(env_before)


if __name__ == '__main__':
    if '--launcher' in sys.argv:
        fake_launcher(sys.argv[2:])
    elif '--child-server' in sys.argv:
        child_server(int(sys.argv[2]), sys.argv[3], float(sys.argv[4]), '--legacy' in sys.argv)
    else:
        if sys.version_info < (3, 12):
            raise SystemExit('Use Python 3.12+ to reproduce the project runtime PIPE wait behavior')
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--source', type=Path, required=True, help='singularity.py from a temporary patched copy')
        parser.add_argument('--apex-source', type=Path, required=True, help='apex_singularity.py with the companion patch')
        args = parser.parse_args()
        asyncio.run(run_checks(args.source, args.apex_source))
