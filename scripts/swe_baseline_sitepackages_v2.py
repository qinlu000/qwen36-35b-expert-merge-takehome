"""Verify the installed mini venv, excluding the benchmark repository metadata."""
from swe_baseline_v2 import SweBaselineV2


class SweBaselineSitePackagesV2(SweBaselineV2):
    async def exec_as_agent(self, environment, command, **kwargs):
        if 'import importlib.metadata as m,json;' in command:
            command = command.replace('m.distributions()',
                'm.distributions(path=__import__("site").getsitepackages())')
        return await super().exec_as_agent(environment, command, **kwargs)
