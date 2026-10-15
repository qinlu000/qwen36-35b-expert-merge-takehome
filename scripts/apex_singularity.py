"""Small HPC bootstrap/cleanup adaptations; execution and capabilities stay upstream."""
from pathlib import Path

from harbor.environments.singularity.singularity import SingularityEnvironment


class ApexSingularityEnvironment(SingularityEnvironment):
    async def _start_server(self):
        # Apptainer sources this read-only hook before Harbor's bootstrap.
        # Upstream serializes bind targets verbatim, so :ro is explicit here.
        hook = {'type': 'bind',
                'source': str(Path(__file__).with_name('apex_rootmap_bootstrap.sh').resolve()),
                'target': '/.singularity.d/env/99-apex-rootmap.sh:ro',
                'read_only': True}
        self._mounts.append(hook)
        try:
            await super()._start_server()
        finally:
            self._mounts.remove(hook)
