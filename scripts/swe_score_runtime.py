"""Fresh replay runtime: keep the task image's Python and PATH intact."""
from pathlib import Path
import json
import re
import subprocess

from baseline_singularity import BaselineSingularityEnvironment

ROOT = Path(__file__).resolve().parents[1]


class SweNativeRuntimeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        image_env = subprocess.check_output(
            ['singularity', 'inspect', '--environment', str(self._sif_path)], text=True)
        self._native_path = re.search(r'^export PATH="([^"]+)"$', image_env, re.M)[1]
        runtime = ROOT / 'artifacts/cache/swe-v2-runtime'
        python = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
        # The server uses its own absolute interpreter. Do not bind managed
        # Python or uv over /usr/local/bin, which belongs to the task image.
        pairs = [
            (runtime, '/opt/apex-swe-runtime'),
            (runtime / 'harbor-server', '/opt/harbor-server'),
            (python, str(python)),
            (ROOT / 'artifacts/tools/uv/uv', '/opt/apex-swe-tools/uv'),
            (ROOT / 'artifacts/cache/swe-v2-wheels', '/opt/apex-swe-wheels'),
            (ROOT / 'scripts/swe_runtime_bootstrap.sh', '/staging/bootstrap.sh'),
            (ROOT / 'scripts/swe_runtime_rootmap.sh', '/.singularity.d/env/98-apex-swe-runtime.sh'),
        ]
        mounts = [{'type': 'bind', 'source': str(s), 'target': t, 'read_only': True}
                  for s, t in pairs]
        self._mounts.extend(mounts)
        try:
            await super()._start_server()
            command = """printf 'PATH=%s\\n' "$PATH"
for candidate in python python3; do
  command -v "$candidate" || continue
  "$candidate" -c 'import sys,importlib.util,json; print(json.dumps({"executable":sys.executable,"version":sys.version,"pytest":bool(importlib.util.find_spec("pytest")),"pip":bool(importlib.util.find_spec("pip"))}))'
done"""
            result = await self.exec(command, timeout_sec=20)
            logs = Path(next(m['source'] for m in self._mounts if m['target'] == '/logs/agent'))
            (logs / 'native-python-context.json').write_text(json.dumps({
                'native_path': self._native_path, 'return_code': result.return_code,
                'stdout': result.stdout}, indent=2) + '\n')
        finally:
            for mount in mounts:
                self._mounts.remove(mount)

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        return await super().exec(command, cwd=cwd,
            env={'PATH': self._native_path, **(env or {})},
            timeout_sec=timeout_sec, user=user)


SweScoreRuntimeEnvironment = SweNativeRuntimeEnvironment
