"""Keep the proven musl ABI helpers private and restore the image's task PATH."""
import json
from pathlib import Path
import re
import subprocess
import time

from baseline_singularity import BaselineSingularityEnvironment
from swe_score_go_runtime import apply_go_score_cache
from swe_score_go_preseed import preseed_go_score_cache

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
ASSETS = ROOT / 'artifacts/preflight/swe_v2/musl_compat'
PYTHON = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'


class SweCleanMuslRuntimeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        image_env = subprocess.check_output(
            ['singularity', 'inspect', '--environment', str(self._sif_path)], text=True)
        self._native_path = re.search(r'^export PATH="([^"]+)"$', image_env, re.M)[1]
        runtime = ROOT / 'artifacts/cache/swe-v2-runtime'
        pairs = [
            (runtime, '/opt/apex-swe-runtime'),
            (runtime / 'harbor-server', '/opt/harbor-server'),
            (PYTHON, str(PYTHON)),
            (ASSETS, '/opt/apex-musl-runtime'),
            # mini/server retain their absolute private interpreter, including
            # the old proven loader+glibc wrapper needed inside Alpine images.
            (ASSETS / 'python-wrapper', str(PYTHON / 'bin/python3.12')),
            (ASSETS / 'uv-wrapper', '/opt/apex-swe-tools/uv'),
            (runtime / 'curl', '/opt/apex-swe-tools/curl'),
            (ROOT / 'artifacts/cache/swe-v2-wheels', '/opt/apex-swe-wheels'),
            (ROOT / 'scripts/swe_clean_musl_bootstrap.sh', '/staging/bootstrap.sh'),
            (ASSETS / 'rootmap.sh', '/.singularity.d/env/98-apex-swe-runtime.sh'),
        ]
        mounts = [{'type': 'bind', 'source': str(source), 'target': target,
                   'read_only': True} for source, target in pairs]
        self._mounts.extend(mounts)
        try:
            await super()._start_server()
            logs = Path(next(mount['source'] for mount in self._mounts
                             if mount['target'] == '/logs/agent'))
            (logs / 'native-runtime-context.json').write_text(json.dumps({
                'native_path_from_sif': self._native_path,
                'task_exec_path_restored': True,
                'managed_python_private_path': str(PYTHON / 'bin/python3.12'),
                'private_uv': '/opt/apex-swe-tools/uv',
                'native_usr_local_bin_overlays': [],
                'mounts': mounts}, indent=2) + '\n')
        finally:
            for mount in mounts:
                self._mounts.remove(mount)

    def _resolve_user(self, user):
        resolved = super()._resolve_user(user)
        return None if resolved in ('root', 0) else resolved

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command and timeout_sec is None:
            timeout_sec = 3000
        return await super().exec(command, cwd=cwd,
            env={'PATH': self._native_path, **(env or {})}, timeout_sec=timeout_sec, user=user)


class SweCleanMuslScoreEnvironment(SweCleanMuslRuntimeEnvironment):
    async def _start_server(self):
        apply_go_score_cache(self)
        await super()._start_server()

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command and not getattr(self, '_workspace_prepared', False):
            self._workspace_prepared = True
            project = await super().exec('command -v go >/dev/null 2>&1 && '
                '{ test -f /app/go.mod || test -f /testbed/go.mod; }', timeout_sec=30)
            if project.return_code == 0:
                started = time.monotonic()
                cache = await preseed_go_score_cache(self)
                preparation = ('cd /app 2>/dev/null || cd /testbed; '
                    'export GOPROXY=file:///opt/apex-swe-score-go/gopath/pkg/mod/cache/download,https://goproxy.cn,direct; '
                    'export GOSUMDB=sum.golang.org GOTOOLCHAIN=local; '
                    'if [ -f go.work ]; then go work sync; fi; go mod download all')
                result = await super().exec(preparation, cwd=cwd, timeout_sec=1800)
                logs = Path(next(mount['source'] for mount in self._mounts
                                 if mount['target'] == '/logs/agent'))
                (logs / 'native-go-workspace-preparation.json').write_text(json.dumps({
                    'command': preparation, 'cache_preseed': cache,
                    'return_code': result.return_code,
                    'elapsed_seconds': time.monotonic() - started,
                    'stdout': result.stdout, 'stderr': result.stderr,
                    'original_test_command_unchanged': True}, indent=2) + '\n')
        return await super().exec(command, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user)
