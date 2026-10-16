"""Map native second-stage submission specs to the already verified rootless ASI runtime."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from ai4sci_bench.runner import submission_sandbox
from ai4sci_bench.runner.task_env import TaskEnvironmentManager
from asi_bwrap import namespace_prefix, program_env


class TaskEnvironmentImage:
    def __init__(self, repo):
        self.manager=TaskEnvironmentManager(repo)

    def ensure_image(self, metadata, agent_type=None):
        runtime=self.manager.ensure_env(metadata)
        self.python_version=runtime.resolved_python_version
        return str(runtime.env_dir)

    def get_image_identity(self, image):
        return 'bwrap:cached-native-task-env:'+image+':python='+str(self.python_version)


class GraderSubmissionRunner(submission_sandbox.SandboxedSubmissionRunner):
    audit_root=None

    def __init__(self, repo_root, *, image_builder=None):
        super().__init__(repo_root,image_builder=image_builder or TaskEnvironmentImage(repo_root))
        self.units={}

    def run(self, spec):
        cpu_root=Path(self.audit_root)/'cpu_leases';cpu_root.mkdir(parents=True,exist_ok=True)
        while True:
            for index,_cpu in enumerate(sorted(os.sched_getaffinity(0))):
                lock=(cpu_root/str(index)).open('a')
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:lock.close();continue
                self.cpu_offset=index;self.cpu_lock=lock;break
            else:time.sleep(.05);continue
            break
        try:return super().run(spec)
        finally:self.cpu_lock.close()

    def _build_docker_command(self,spec,*,image,container_name,submission_dir,readonly_inputs,output_dir):
        prefix,_,_=namespace_prefix(submission_dir,Path(image))
        prefix[0]=str(self.repo_root.parents[2]/'artifacts/asi/scoring_tools/bubblewrap-0.8/rootfs/usr/bin/bwrap')
        for i,value in enumerate(prefix):
            if value=='/workspace':prefix[i]='/submission';prefix[i-2]='--ro-bind'
            elif value.startswith('/workspace/'):prefix[i]=value.replace('/workspace/','/submission/',1)
        sized=[]
        for i,value in enumerate(prefix):
            if value=='--tmpfs' and prefix[i+1] in ['/tmp','/home']:
                sized += ['--size',str(1024**3)]
            sized.append(value)
        prefix=sized+['--uid','65534','--gid','65534','--size',str(256*1024**2),'--tmpfs','/dev/shm']
        prefix += ['--ro-bind',image,'/opt/venv']
        for mount in readonly_inputs:prefix += ['--ro-bind',str(mount.host_path),mount.container_path]
        prefix += ['--bind',str(output_dir),'/output','--chdir','/submission']
        environment=program_env(Path(image)) | {'PATH':'/opt/venv/bin:/usr/bin:/bin',
            'VIRTUAL_ENV':'/opt/venv','PYTHONDONTWRITEBYTECODE':'1'}
        prefix += ['--clearenv']
        for key,value in environment.items():prefix += ['--setenv',key,value]
        memory=spec.memory_limit.lower()
        factor={'g':1024**3,'m':1024**2,'k':1024}
        memory_bytes=int(float(memory[:-1])*factor[memory[-1]]) if memory[-1] in factor else int(memory)
        if float(spec.cpu_limit)!=int(spec.cpu_limit):raise ValueError('Noninteger native CPU spec needs explicit support')
        helper=Path(__file__).with_name('baseline_exec_limits.py')
        self.units[container_name]=container_name
        # Scope membership is verified by the shared helper before the sandbox starts.
        command=['systemd-run','--user','--scope','--quiet','--unit',container_name,
            '-p',f'MemoryMax={memory_bytes}','-p','MemorySwapMax=0','-p',f'TasksMax={spec.pids_limit}',
            sys.executable,str(helper),'--cpus',str(int(spec.cpu_limit)),
            '--memory-bytes',str(memory_bytes),'--cpu-offset',str(self.cpu_offset),'--',
            *prefix,'/usr/bin/prlimit',f'--fsize={spec.max_output_file_bytes}:{spec.max_output_file_bytes}',
            '--',*spec.command]
        return command

    def _control_container(self,command,*,timeout):
        name=command[-1];unit=self.units.get(name)
        if not unit:return False
        signal='SIGTERM' if command[1]=='stop' else 'SIGKILL'
        result=subprocess.run(['systemctl','--user','kill','--kill-who=all','--signal='+signal,unit+'.scope'],
            capture_output=True,timeout=max(1,timeout))
        if command[1]=='stop' and result.returncode==0:
            grace=int(command[command.index('--time')+1]);time.sleep(min(grace,max(0,timeout-1)))
        return result.returncode==0


@contextmanager
def mapped_submission_runtime(audit_root):
    GraderSubmissionRunner.audit_root=Path(audit_root)
    # The controller needs its user bus, which is not mounted into the submission.
    bus=f'/run/user/{os.getuid()}'
    with (patch.object(submission_sandbox,'SandboxedSubmissionRunner',GraderSubmissionRunner),
          patch.dict(os.environ,{'XDG_RUNTIME_DIR':bus,'DBUS_SESSION_BUS_ADDRESS':'unix:path='+bus+'/bus'})):
        yield
