"""TB bootstrap cache; frozen Harbor agent, namespaces and limits are inherited."""
from pathlib import Path
from baseline_singularity import BaselineSingularityEnvironment

ROOT = Path('/data/caoqinlu/projects/apex-takehome')


class TerminalRuntimeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        runtime = ROOT / 'artifacts/cache/swe-v2-runtime'
        python = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
        pairs = [
            (ROOT / 'artifacts/cache/terminal-v2-runtime', '/opt/apex-terminal-runtime'),
            (runtime / 'harbor-server', '/opt/harbor-server'),
            (python, str(python)),
            (Path(__file__).with_name('terminal_runtime_bootstrap.sh'), '/staging/bootstrap.sh'),
            (Path(__file__).with_name('terminal_runtime_rootmap.sh'), '/.singularity.d/env/98-apex-terminal-runtime.sh'),
        ]
        mounts = [{'type': 'bind', 'source': str(source), 'target': target, 'read_only': True}
                  for source, target in pairs]
        self._mounts.extend(mounts)
        try:
            await super()._start_server()
        finally:
            for mount in mounts:
                self._mounts.remove(mount)
