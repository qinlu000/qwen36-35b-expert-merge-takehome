"""HPC launcher cleanup for Harbor; all execution and network capabilities stay upstream."""
import asyncio

import httpx

from harbor.environments.singularity.singularity import SingularityEnvironment


class ApexSingularityEnvironment(SingularityEnvironment):
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
