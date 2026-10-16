"""Independent repair run: native PATH, early state capture, confirmed cleanup."""
import asyncio
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time

from baseline_singularity import BaselineSingularityEnvironment
from terminal_native_environment import CACHE, OFFLINE
import terminal_verifier_environment as verifier_runtime
from terminal_verifier_environment import TOOLS
from terminal_verifier_apt_environment import APT_SETUP, TerminalVerifierAptEnvironment


class TerminalRepairEnvironment(TerminalVerifierAptEnvironment):
    async def _start_server(self):
        image_env = await asyncio.to_thread(subprocess.check_output,
            ['singularity', 'inspect', '--environment', str(self._sif_path)], text=True)
        self._native_path = re.search(r'^export PATH="([^"]+)"$', image_env, re.M)[1]
        await super()._start_server()

    async def exec(self, command, *args, env=None, **kwargs):
        verifier = '/tests/' in command and not command.lstrip().startswith('chmod ')
        if verifier and not getattr(self, '_verifier_assets_ready', False):
            await self._save_final_state('before_native_verifier')
            await self._prepare_verifier()
        phase_env = self._repair_verifier_env if verifier else {}
        return await super().exec(command, *args,
            env={'PATH': self._native_path, **phase_env, **(env or {})}, **kwargs)

    async def _prepare_verifier(self):
        target = self._staging / 'verifier_assets'
        self._repair_verifier_assets = target
        self._repair_verifier_env = {}
        task_id = self.environment_dir.parent.name

        def copy():
            def tree(source, destination):
                destination.mkdir(parents=True, exist_ok=True)
                # Independent inodes on every filesystem; never hardlink a
                # writable per-trial UV cache back into the frozen source.
                subprocess.run(['cp', '-a', '--reflink=auto', str(source) + '/.',
                                str(destination)], check=True)

            for name in ('native', 'verifier-bin', 'uv-wheel', 'python'):
                tree(CACHE / name, target / name)
            if OFFLINE.exists():
                tree(OFFLINE, target / 'uv-cache')
            mapping = TOOLS / 'task_cache_map.json'
            if mapping.exists():
                data = json.loads(mapping.read_text())
                rows = data.get('tasks', data)
                item = rows.get(task_id, {})
                cache = item.get('uv_cache_dir') or item.get('cache') or item.get('cache_dir')
                if item.get('ready') and cache:
                    tree(Path(cache), target / 'uv-cache')
                    self._repair_verifier_env.update(UV_PYTHON_DOWNLOADS='never', UV_OFFLINE='1')
                if item.get('ready') and item.get('pip_wheelhouse'):
                    tree(Path(item['pip_wheelhouse']), target / 'pip-wheels')
                    self._repair_verifier_env.update(
                        PIP_FIND_LINKS='/staging/verifier_assets/pip-wheels', PIP_NO_INDEX='1')
                if item.get('ready') and item.get('python_version') == '3.12':
                    python = Path(item['python']).parent.parent
                    tree(python, target / 'python' / python.name)
                    self._repair_verifier_env.update(UV_PYTHON_DOWNLOADS='never', UV_OFFLINE='1')
            if (TOOLS / 'uv-installer').exists():
                tree(TOOLS / 'uv-installer', target / 'url-cache')
            shim = Path(verifier_runtime.__file__).with_name('terminal_verifier_curl.py')
            shutil.copy2(shim, target / 'verifier-bin/curl')
            (target / 'verifier-bin/curl').chmod(0o755)

        await asyncio.to_thread(copy)
        self._verifier_assets_ready = True
        result = await self.exec(APT_SETUP, timeout_sec=20)
        if result.return_code:
            raise RuntimeError('Verifier package transport setup failed')

    async def _stop_server_process(self):
        confirmed = await super()._stop_server_process()
        target = getattr(self, '_repair_verifier_assets', None)
        if confirmed and target and target.exists():
            await asyncio.to_thread(shutil.rmtree, target)
        return confirmed

    async def _apply_network_policy(self, policy):
        await super()._apply_network_policy(policy)
        if policy.network_mode.value == 'no-network':
            self._solver_started_ns = time.time_ns()

    async def _save_final_state(self, reason):
        if getattr(self, '_repair_state_saved', False):
            return self._repair_state_receipt
        # Capture before Harbor uploads tests or adds verifier dependencies.
        # A metadata scan includes files changed outside the declared workdir;
        # no model request, task test, content hash, or replay is involved.
        code = '''import json,os,pathlib,stat,subprocess,time
started=STARTED
roots={WORKDIR.lstrip('/'),'etc'}
if os.path.isdir('/var/www'):roots.add('var/www')
for value in EXTRA:
 if value.startswith('/') and value not in ['/','/app','/usr','/var','/opt','/tmp','/root','/home'] and not value.startswith(('/proc','/sys','/dev','/logs','/tests','/staging','/opt/apex','/opt/harbor')):
  roots.add(value.lstrip('/'))
roots=sorted(p for p in roots if p and os.path.lexists('/'+p))
roots=[p for p in roots if not any(p.startswith(parent+'/') for parent in roots if parent!=p)]
rootdev=os.stat('/').st_dev
skip={'proc','sys','dev','logs','tests','staging','.singularity.d'}
changed=[]
for base,dirs,files in os.walk('/',topdown=True,followlinks=False):
 keep=[]
 for name in dirs:
  path=os.path.join(base,name)
  try:
   info=os.lstat(path)
   if info.st_dev==rootdev and not (base=='/' and name in skip) and not path.startswith(('/opt/apex','/opt/harbor')):
    keep.append(name)
    if stat.S_ISLNK(info.st_mode) and info.st_ctime_ns>=started:files.append(name)
  except OSError:pass
 dirs[:]=keep
 for name in files:
  path=os.path.join(base,name)
  try:
   info=os.lstat(path)
   if info.st_dev==rootdev and info.st_ctime_ns>=started and (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
    rel=path.lstrip('/')
    if not any(rel==p or rel.startswith(p+'/') for p in roots):changed.append(rel)
  except OSError:pass
paths=roots+sorted(set(changed))
out=pathlib.Path('/logs/artifacts');out.mkdir(parents=True,exist_ok=True)
listing=out/'final-task-state.paths';listing.write_bytes(b'\\0'.join(p.encode() for p in paths)+b'\\0')
r=subprocess.run(['tar','--ignore-failed-read','-cf',str(out/'final-task-state.tar'),'-C','/','--null','-T',str(listing)],capture_output=True,text=True)
processes=[]
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdigit():
  try:processes.append({'pid':int(p.name),'command':p.joinpath('cmdline').read_bytes().decode(errors='replace').replace('\\0',' ').strip()})
  except OSError:pass
receipt={'reason':REASON,'paths':paths,'workdir':WORKDIR,'complete_prefixes':roots,'changed_external_files':sorted(set(changed)),'solver_started_ns':started,'return_code':r.returncode,'stderr':r.stderr[-4000:],'processes_at_capture':processes,'captured_before_verifier':True,'live_service_state_is_not_reconstructed_by_tar':True}
(out/'final-task-state.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps({'return_code':r.returncode,'path_count':len(paths),'external_changed_file_count':len(changed),'stderr':r.stderr[-1000:]}))
'''.replace('STARTED', repr(getattr(self, '_solver_started_ns', time.time_ns())), 1)
        code = code.replace('WORKDIR', repr(self._workdir))
        code = code.replace('EXTRA', repr(self._final_output_paths()), 1)
        code = code.replace('REASON', repr(reason), 1)
        result = await BaselineSingularityEnvironment.exec(self,
            '/opt/harbor-server/bin/python3 -c ' + shlex.quote(code),
            env={'PATH': self._native_path}, timeout_sec=180)
        self._repair_state_receipt = {'return_code': result.return_code, 'stdout': result.stdout}
        tar_result = json.loads(result.stdout) if result.return_code == 0 else {}
        self._repair_state_saved = result.return_code == 0 and tar_result.get('return_code') == 0
        return self._repair_state_receipt

    async def terminate_solver_processes(self, reason):
        self._solver_cleanup_failed = True
        if self._solver_baseline is None:
            raise RuntimeError('Missing pre-solver process snapshot')
        code = '''import json,os,pathlib,signal,time
baseline=set(map(tuple,BASELINE))
def processes():
 out={}
 for p in pathlib.Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    fields=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
    out[int(p.name)]=(fields[19],int(fields[1]),fields[0])
   except (OSError,IndexError,ValueError):pass
 return out
current=processes();keep=set();pid=os.getpid()
while pid in current and pid not in keep:
 keep.add(pid);pid=current[pid][1]
def remaining():
 return {pid:row for pid,row in processes().items() if pid not in keep and (pid,row[0]) not in baseline and row[2]!='Z'}
events=[];empty=0
for iteration in range(12):
 rows=remaining()
 if not rows:
  empty+=1
  if empty==2:break
 else:
  empty=0
  sig=signal.SIGTERM if iteration==0 else signal.SIGKILL
  for pid,row in rows.items():
   try:os.kill(pid,sig);events.append({'pid':pid,'start':row[0],'signal':int(sig)})
   except ProcessLookupError:pass
 time.sleep(0.2)
rows=remaining();detail=[]
for pid,row in rows.items():
 try:command=pathlib.Path('/proc',str(pid),'cmdline').read_bytes().decode(errors='replace').replace('\\0',' ')
 except OSError:command=''
 detail.append({'pid':pid,'start':row[0],'state':row[2],'command':command})
print(json.dumps({'killed':events,'remaining_pids':list(rows),'remaining_processes':detail,'confirmed':not rows and empty==2}))
'''.replace('BASELINE', repr(self._solver_baseline), 1)
        result = await self.exec('/opt/harbor-server/bin/python3 -c ' + shlex.quote(code),
                                 timeout_sec=20)
        if result.return_code:
            raise RuntimeError('Solver process cleanup failed')
        receipt = {'reason': reason, **json.loads(result.stdout)}
        if not receipt['confirmed']:
            raise RuntimeError('Solver processes remain after cleanup: ' + json.dumps(receipt))
        self._solver_cleanup_failed = False
        return receipt
