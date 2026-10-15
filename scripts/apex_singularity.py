"""Small HPC bootstrap/cleanup adaptations; execution and capabilities stay upstream."""
import asyncio
from pathlib import Path

import httpx

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

    async def stop(self, delete):
        # The upstream server already exposes /shutdown. Use it before stopping
        # the site launcher, which otherwise leaves its appinit child running.
        if self._http_client and self._server_process and self._server_process.returncode is None:
            try:
                await self._http_client.post(f'http://localhost:{self._server_port}/shutdown')
            except httpx.RequestError:
                pass
            await asyncio.sleep(0.3)
        await super().stop(delete=delete)
