"""Install the fixed mini toolchain privately; leave task Python and uv intact."""
from swe_baseline_sitepackages_v2 import SweBaselineSitePackagesV2
from swe_baseline_v2 import ROOT


class SweBaselineNativeV2(SweBaselineSitePackagesV2):
    async def exec_as_agent(self, environment, command, **kwargs):
        if 'uv tool install --python 3.12 mini-swe-agent' in command:
            python = ROOT / 'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12'
            command = command.replace('uv python install 3.12', 'test -x ' + str(python), 1)
            command = command.replace('uv tool install --python 3.12 mini-swe-agent',
                'uv tool install --constraints /tmp/apex-mini-lock/constraints.txt '
                '--python ' + str(python) + ' mini-swe-agent', 1)
            kwargs['env'] = {**(kwargs.get('env') or {}),
                'PATH': '/opt/apex-swe-tools:' + environment._native_path,
                'UV_OFFLINE': '1', 'UV_FIND_LINKS': '/opt/apex-swe-wheels',
                'UV_PYTHON_DOWNLOADS': 'never', 'UV_LINK_MODE': 'copy'}
        return await super().exec_as_agent(environment, command, **kwargs)
