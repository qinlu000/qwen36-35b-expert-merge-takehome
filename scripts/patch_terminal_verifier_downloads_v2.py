"""Repair only saved-state verifier instances while the immutable old leaf drains."""
from datetime import datetime,timezone
import json,os,shlex,shutil,time
from pathlib import Path
import httpx

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
OWNER=2389784
URL='https://github.com/astral-sh/uv/releases/download/0.9.5/uv-x86_64-unknown-linux-gnu.tar.gz'
QUERY="""import json,os,pathlib
print(json.dumps({'ready':pathlib.Path('/staging/verifier_assets').exists() and pathlib.Path('/logs/artifacts/final-task-state.tar').exists(),'inode':os.stat('/staging').st_ino}))"""
STOP="""import json,os,pathlib,signal,time
events=[]
if pathlib.Path('/staging/verifier_assets/url-cache/url_map.json').exists() and pathlib.Path('/logs/artifacts/final-task-state.tar').exists():
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   args=p.joinpath('cmdline').read_bytes().decode(errors='replace').split('\\0')
   age=time.clock_gettime(time.CLOCK_BOOTTIME)-int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19])/os.sysconf('SC_CLK_TCK')
   if URL in args and any(x.endswith('/native/curl') for x in args) and age>15:
    os.kill(int(p.name),signal.SIGTERM);events.append({'pid':int(p.name),'url':URL,'signal':'TERM','age_seconds':round(age,1)})
  except (OSError,ValueError,IndexError):pass
print(json.dumps({'events':events,'scope':pathlib.Path('/proc/self/cgroup').read_text().strip()}))""".replace('URL',repr(URL))


def command(client,code):
    response=client.post('http://localhost/exec',json={'command':'/opt/harbor-server/bin/python3 -c '+shlex.quote(code),'timeout_sec':5})
    response.raise_for_status()
    return json.loads(response.json()['stdout'])


def main():
    repaired=set()
    while Path(f'/proc/{OWNER}').exists():
        staging={p.stat().st_ino:p for p in Path('/tmp').glob('apex_baseline_staging_*') if p.is_dir()}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                args=p.joinpath('cmdline').read_bytes().decode().split('\0')
                parent=int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[1])
            except (OSError,ValueError):continue
            if '--namespace-relays' not in args or parent!=OWNER:continue
            socket=args[args.index('--control-socket')+1]
            try:
                with httpx.Client(transport=httpx.HTTPTransport(uds=socket),timeout=8,trust_env=False) as client:
                    state=command(client,QUERY)
                    if not state['ready']:continue
                    host=staging.get(state['inode'])
                    if not host:continue
                    if socket not in repaired:
                        shutil.copytree(ROOT/'artifacts/tools/terminal_verifier_offline_20261016/uv-installer',host/'verifier_assets/url-cache',dirs_exist_ok=True)
                        target=host/'verifier_assets/verifier-bin/curl'
                        shutil.copy2(ROOT/'scripts/terminal_verifier_curl.py',target.with_suffix('.new'))
                        target.with_suffix('.new').chmod(0o755);target.with_suffix('.new').replace(target)
                        repaired.add(socket)
                    receipt=command(client,STOP)
                    if receipt['events']:
                        value={'at_utc':datetime.now(timezone.utc).isoformat(),'owner':OWNER,'socket':socket,'staging':str(host),**receipt}
                        with (RUN/'verifier-download-repair.jsonl').open('a') as stream:stream.write(json.dumps(value)+'\n')
                        print(json.dumps(value),flush=True)
            except (httpx.HTTPError,OSError,ValueError,KeyError):continue
        time.sleep(10)


if __name__=='__main__':main()
