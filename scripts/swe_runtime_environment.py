"""SWE-only cached bootstrap; inherit the frozen namespace and resource backend."""
from pathlib import Path
import json
import subprocess

from baseline_singularity import BaselineSingularityEnvironment


ROOT = Path(__file__).resolve().parents[1]


class SweRuntimeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        runtime = ROOT / 'artifacts/cache/swe-v2-runtime'
        python = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
        # Nested bootstrap bind replaces only this container's staged file.
        # The frozen parent still owns namespaces, cgroups, affinity and cleanup.
        pairs = [
            (runtime, '/opt/apex-swe-runtime'),
            (runtime / 'harbor-server', '/opt/harbor-server'),
            (python, str(python)),
            (ROOT / 'artifacts/tools/uv/uv', '/usr/local/bin/uv'),
            (runtime / 'python3.12', '/usr/local/bin/python3.12'),
            (ROOT / 'artifacts/cache/swe-v2-wheels', '/opt/apex-swe-wheels'),
            (ROOT / 'scripts/swe_runtime_bootstrap.sh', '/staging/bootstrap.sh'),
            (ROOT / 'scripts/swe_runtime_rootmap.sh', '/.singularity.d/env/98-apex-swe-runtime.sh'),
        ]
        mounts = [{'type': 'bind', 'source': str(source), 'target': target,
                   'read_only': True} for source, target in pairs]
        self._mounts.extend(mounts)
        try:
            await super()._start_server()
            group = subprocess.check_output(['systemctl', '--user', 'show',
                self._scope_unit + '.scope', '--property=ControlGroup', '--value'], text=True).strip()
            cgroup = Path('/sys/fs/cgroup') / group.lstrip('/')
            memory = int((cgroup / 'memory.max').read_text())
            swap = int((cgroup / 'memory.swap.max').read_text())
            result = await self.exec('/opt/harbor-server/bin/python3 -c '
                "'import os,json;print(json.dumps(sorted(os.sched_getaffinity(0))))'", timeout_sec=10)
            cpus = json.loads(result.stdout)
            if memory != self._effective_memory_mb * 1024**2 or swap != 0 or len(cpus) != self._effective_cpus:
                raise RuntimeError('SWE runtime resource receipt differs from requested limits')
            logs = Path(next(m['source'] for m in self._mounts if m['target'] == '/logs/agent'))
            logs.joinpath('swe-runtime-resources.json').write_text(json.dumps({
                'scope': self._scope_unit, 'cpus': cpus, 'memory_max': memory,
                'memory_swap_max': swap, 'cgroup': group}, indent=2) + '\n')
        finally:
            for mount in mounts:
                self._mounts.remove(mount)
