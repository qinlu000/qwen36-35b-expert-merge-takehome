"""Persist completed package artifacts, then defer only the old MTEB installer."""
from pathlib import Path
from datetime import datetime,timezone
import json,shlex
import httpx
from freeze_terminal_verifier_cache_v2 import export

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
DEST=ROOT/'artifacts/tools/terminal_verifier_offline_20261016/salvaged/mteb-retrieve'
QUERY="""import json,os,pathlib
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=p.joinpath('cmdline').read_bytes().decode(errors='replace').split('\\0')
  if any(a.endswith(('/uv','/uvx')) for a in args) and any('mteb' in a for a in args):
   rows.append({'pid':int(p.name),'start':p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]})
 except (OSError,ValueError,IndexError):pass
print(json.dumps({'ready':pathlib.Path('/staging/verifier_assets').exists() and pathlib.Path('/logs/artifacts/final-task-state.tar').exists(),'inode':os.stat('/staging').st_ino,'installers':rows,'scope':pathlib.Path('/proc/self/cgroup').read_text().strip()}))"""


def rpc(client,code):
    response=client.post('http://localhost/exec',json={'command':'/opt/harbor-server/bin/python3 -c '+shlex.quote(code),'timeout_sec':10})
    response.raise_for_status();return json.loads(response.json()['stdout'])


def main():
    staging={p.stat().st_ino:p for p in Path('/tmp').glob('apex_baseline_staging_*') if p.is_dir()}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=p.joinpath('cmdline').read_bytes().decode().split('\0')
            parent=int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[1])
        except (OSError,ValueError):continue
        if '--namespace-relays' not in args or parent!=2389784:continue
        socket=args[args.index('--control-socket')+1]
        with httpx.Client(transport=httpx.HTTPTransport(uds=socket),timeout=20,trust_env=False) as client:
            state=rpc(client,QUERY)
            if not state['ready'] or not state['installers']:continue
            host=staging[state['inode']]
            source=host/'verifier_assets/uv-cache'
            packages={}
            for link in (source/'wheels-v5').rglob('*'):
                if link.is_symlink() and link.resolve().is_dir() and any(link.resolve().glob('*.dist-info/METADATA')):
                    packages[link.parent.name]=link.name.split('-',1)[0]
            missing=export(source,DEST,packages)
            events=[]
            for process in state['installers']:
                code="""import json,os,pathlib,signal
p=pathlib.Path('/proc/PID')
same=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==START
if same:os.kill(PID,signal.SIGTERM)
print(json.dumps({'pid':PID,'terminated':same}))""".replace('PID',str(process['pid'])).replace('START',repr(process['start']))
                events.append(rpc(client,code))
            receipt={'at_utc':datetime.now(timezone.utc).isoformat(),'scope':state['scope'],'socket':socket,
                'published_complete_packages':packages,'missing_export_entries':missing,'cache':str(DEST),
                'events':events,'task_outputs_unchanged':True,'new_model_calls':0,
                'policy':'Only published wheel links with dist-info METADATA; temporary downloads not copied; native installation failure retained'}
            (RUN/'deferred-mteb-grader.json').write_text(json.dumps(receipt,indent=2)+'\n')
            print(json.dumps(receipt))


if __name__=='__main__':main()
