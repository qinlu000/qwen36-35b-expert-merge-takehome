"""Native task PATH, private harness tools, full verifier transport and state capture."""
import json
from pathlib import Path
import shlex
import shutil
import asyncio

from baseline_singularity import BaselineSingularityEnvironment

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
CACHE=ROOT/'artifacts/cache/terminal-v2-native'
OFFLINE=ROOT/'artifacts/tools/terminal_verifier_offline_20261016/core-uv-cache'


class TerminalNativeEnvironment(BaselineSingularityEnvironment):
    async def _start_server(self):
        server=ROOT/'artifacts/cache/swe-v2-runtime/harbor-server'
        python=ROOT/'artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu'
        pairs=[(CACHE/'harness-only','/opt/apex-terminal-native'),
            (server,'/opt/harbor-server'),(python,str(python)),
            (CACHE/'bootstrap.sh','/staging/bootstrap.sh'),
            (CACHE/'server.py','/staging/_hbexec.py'),
            (CACHE/'rootmap.sh','/.singularity.d/env/99-apex-rootmap.sh')]
        mounts=[{'type':'bind','source':str(s),'target':t,'read_only':True} for s,t in pairs]
        self._mounts.extend(mounts)
        try:await super()._start_server()
        finally:
            for mount in mounts:self._mounts.remove(mount)

    async def _save_final_state(self,reason):
        # Preserve answers before the original namespace/tmpfs is destroyed.
        code='''import json,os,pathlib,re,subprocess
paths={WORKDIR.lstrip('/')}
for value in EXTRA:
 if value.startswith('/') and value not in ['/','/app'] and not value.startswith(('/proc','/sys','/dev','/logs','/tests','/opt/apex','/opt/harbor')):
  paths.add(value.lstrip('/'))
paths=sorted(p for p in paths if p and os.path.exists('/'+p))
os.makedirs('/logs/artifacts',exist_ok=True)
r=subprocess.run(['tar','--ignore-failed-read','-cf','/logs/artifacts/final-task-state.tar','-C','/','--',*paths],capture_output=True,text=True)
receipt={'reason':REASON,'paths':paths,'return_code':r.returncode,'stderr':r.stderr[-2000:]}
pathlib.Path('/logs/artifacts/final-task-state.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps(receipt))
'''.replace('WORKDIR',repr(self._workdir),1).replace('EXTRA',repr(self._final_output_paths()),1).replace('REASON',repr(reason),1)
        return await super().exec('/opt/harbor-server/bin/python3 -c '+shlex.quote(code),timeout_sec=180)

    async def _prepare_verifier(self):
        # Added only after the solver has ended; no scoring assets in its sandbox.
        target=self._staging/'verifier_assets'
        def copy():
            target.mkdir(exist_ok=True)
            for name in ('native','verifier-bin','uv-wheel','python'):
                shutil.copytree(CACHE/name,target/name,dirs_exist_ok=True)
            if OFFLINE.exists():
                shutil.copytree(OFFLINE,target/'uv-cache',dirs_exist_ok=True)
        await asyncio.to_thread(copy)
        self._verifier_assets_ready=True

    def _final_output_paths(self):
        import re
        paths=set()
        tests=self.environment_dir.parent/'tests'
        for p in tests.rglob('*'):
            if p.is_file() and p.suffix in ('.py','.sh','.json'):
                for value in re.findall(r'''["'](/[^"'\n]*)["']''',p.read_text(errors='replace')):
                    value=value.split('{',1)[0]
                    if value:paths.add(value)
        return sorted(paths)

    async def exec(self,command,*args,timeout_sec=None,env=None,**kwargs):
        verifier='/tests/' in command and not command.lstrip().startswith('chmod ')
        if verifier:
            timeout_sec=timeout_sec or 3600
            if not getattr(self,'_verifier_assets_ready',False):
                await self._save_final_state('before_native_verifier')
                await self._prepare_verifier()
            command=('export UV_CACHE_DIR=/staging/verifier_assets/uv-cache '
                'UV_PYTHON_INSTALL_DIR=/staging/verifier_assets/python; '
                'export PATH=/staging/verifier_assets/verifier-bin:$PATH; '+command)
        try:
            result=await super().exec(command,*args,timeout_sec=timeout_sec,env=env,**kwargs)
        except BaseException as exc:
            if verifier:
                self.logger.warning('Verifier interrupted; pre-verifier task state retained: %s',type(exc).__name__)
            raise
        if verifier:
            logs=next((Path(m['source']) for m in self._mounts if m['target']=='/logs/verifier'),None)
            if logs and (logs/'test-stdout.txt').exists():
                text=(logs/'test-stdout.txt').read_text(errors='replace')
                if any(x in text for x in ('curl: command not found','uvx: command not found','uv: command not found')):
                    self.logger.warning('Verifier dependencies missing; pre-verifier task state retained')
        return result
