"""Private SWE musl plumbing; inherit native namespace/resource/cleanup backend."""
from pathlib import Path
from baseline_singularity import BaselineSingularityEnvironment

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
ASSETS=ROOT/'artifacts/preflight/swe_v2/musl_compat'
PYTHON=ROOT/'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'


class MuslRuntimeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        runtime=ROOT/'artifacts/cache/swe-v2-runtime'
        pairs=[
            (runtime,'/opt/apex-swe-runtime'),
            (runtime/'harbor-server','/opt/harbor-server'),
            (PYTHON,str(PYTHON)),
            (ASSETS,'/opt/apex-musl-runtime'),
            (ASSETS/'python-wrapper',str(PYTHON/'bin/python3.12')),
            (ASSETS/'uv-wrapper','/usr/local/bin/uv'),
            (runtime/'python3.12','/usr/local/bin/python3.12'),
            (ROOT/'artifacts/cache/swe-v2-wheels','/opt/apex-swe-wheels'),
            (ASSETS/'bootstrap.sh','/staging/bootstrap.sh'),
            (ASSETS/'rootmap.sh','/.singularity.d/env/98-apex-swe-runtime.sh'),
        ]
        mounts=[{'type':'bind','source':str(s),'target':t,'read_only':True} for s,t in pairs]
        self._mounts.extend(mounts)
        try:
            await super()._start_server()
        finally:
            for mount in mounts:self._mounts.remove(mount)
