"""Apply approved package transport repair only after solver state was saved."""
from datetime import datetime,timezone
import json,shlex,time
from pathlib import Path
import httpx
from terminal_verifier_apt_environment import APT_SETUP

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
OWNER=2389784
QUERY="""import json,os,pathlib,time
ready=pathlib.Path('/staging/verifier_assets').exists() and pathlib.Path('/logs/artifacts/final-task-state.tar').exists()
rows=[]
if ready:
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   args=p.joinpath('cmdline').read_bytes().decode(errors='replace').split('\\0')
   if not args or args[0] not in ('/usr/lib/apt/methods/http','/usr/lib/apt/methods/https'):continue
   start=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
   io=dict(line.split(':',1) for line in p.joinpath('io').read_text().splitlines())
   rows.append({'pid':int(p.name),'start':start,'age':time.clock_gettime(time.CLOCK_BOOTTIME)-int(start)/os.sysconf('SC_CLK_TCK'),'io':[int(io['rchar']),int(io['wchar'])]})
  except (OSError,ValueError,IndexError):pass
print(json.dumps({'ready':ready,'methods':rows,'log_age':time.time()-pathlib.Path('/logs/verifier/test-stdout.txt').stat().st_mtime if pathlib.Path('/logs/verifier/test-stdout.txt').exists() else 0,'scope':pathlib.Path('/proc/self/cgroup').read_text().strip()}))"""


def command(client,code):
    result=client.post('http://localhost/exec',json={'command':code,'timeout_sec':20})
    result.raise_for_status()
    return result.json()


def main():
    applied=set();progress={}
    while Path(f'/proc/{OWNER}').exists():
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                args=p.joinpath('cmdline').read_bytes().decode().split('\0')
                parent=int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[1])
            except (OSError,ValueError):continue
            if '--namespace-relays' not in args or parent!=OWNER:continue
            socket=args[args.index('--control-socket')+1]
            try:
                with httpx.Client(transport=httpx.HTTPTransport(uds=socket),timeout=25,trust_env=False) as client:
                    result=command(client,'/opt/harbor-server/bin/python3 -c '+shlex.quote(QUERY))
                    state=json.loads(result['stdout'])
                    if not state['ready']:continue
                    if socket not in applied:
                        result=command(client,APT_SETUP)
                        if result['return_code']:continue
                        applied.add(socket)
                    for method in state['methods']:
                        key=(socket,method['pid'],method['start'])
                        last=progress.get(key)
                        now=time.monotonic()
                        if not last or last['io']!=method['io']:
                            progress[key]={'io':method['io'],'at':now}
                            if state['log_age']<30:continue
                            last=progress[key]
                        stalled=now-last['at']
                        if method['age']<15 or (stalled<15 and state['log_age']<30):continue
                        code="""import json,os,pathlib,signal
p=pathlib.Path('/proc/PID')
same=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==START
if same:os.kill(PID,signal.SIGTERM)
print(json.dumps({'terminated':same}))""".replace('PID',str(method['pid'])).replace('START',repr(method['start']))
                        result=command(client,'/opt/harbor-server/bin/python3 -c '+shlex.quote(code))
                        value={'at_utc':datetime.now(timezone.utc).isoformat(),'owner':OWNER,'socket':socket,
                            'scope':state['scope'],'pid':method['pid'],'stalled_io_seconds':round(stalled,1),'stdout_stall_seconds':round(state['log_age'],1),
                            'action':'TERM stalled apt HTTP method; preserve native failure; original tests unchanged',
                            'result':json.loads(result['stdout'])}
                        with (RUN/'verifier-apt-repair.jsonl').open('a') as stream:stream.write(json.dumps(value)+'\n')
                        print(json.dumps(value),flush=True)
                        progress.pop(key,None)
            except (httpx.HTTPError,OSError,ValueError,KeyError):continue
        time.sleep(5)


if __name__=='__main__':main()
