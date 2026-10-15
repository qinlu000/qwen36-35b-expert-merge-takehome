"""Harbor 0.24.0 backend with per-trial namespaces and enforced Linux limits.

Uses the pinned Harbor bootstrap/server and cached image without modifying the
agent. Accepted on the project's Ubuntu22 host; runtime limits fail closed.
"""
import asyncio
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile

import httpx

from harbor.environments.singularity.singularity import SingularityEnvironment
from harbor.environments.capabilities import EnvironmentCapabilities, EnvironmentResourceCapabilities
from harbor.models.task.config import NetworkMode

from baseline_netns import NetworkNamespace


class BaselineSingularityEnvironment(SingularityEnvironment):
    _cpu_pools = {}

    def __init__(self, *args, baseline_model_host_port=None,
                 baseline_model_socket=None, baseline_cpu_offset=0,
                 baseline_cpu_slots=1, **kwargs):
        self._namespace = None
        self._scope_unit = None
        self._network_dir = None
        self._baseline_model_port = int(baseline_model_host_port) if baseline_model_host_port else None
        self._baseline_model_socket = baseline_model_socket
        self._baseline_cpu_offset = int(baseline_cpu_offset)
        self._baseline_cpu_slots = int(baseline_cpu_slots)
        self._cpu_pool = None
        self._cpu_slot = None
        self._solver_baseline = None
        self._solver_cleanup_failed = False
        super().__init__(*args, **kwargs)

    @classmethod
    def resource_capabilities(cls):
        return EnvironmentResourceCapabilities(cpu_limit=True, memory_limit=True)

    @property
    def capabilities(self):
        return EnvironmentCapabilities(mounted=True, disable_internet=True,
                                       dynamic_network_policy=True)

    async def _apply_network_policy(self, policy):
        if policy.network_mode not in (NetworkMode.PUBLIC, NetworkMode.NO_NETWORK):
            raise ValueError("Only public/no-network phases are implemented")
        if policy.network_mode == NetworkMode.PUBLIC and self._solver_cleanup_failed:
            raise RuntimeError("Refusing public network after unconfirmed solver cleanup")
        await asyncio.to_thread(self._namespace.set_public,
                                policy.network_mode == NetworkMode.PUBLIC)
        if policy.network_mode == NetworkMode.NO_NETWORK:
            code = "import json,pathlib; out=[]\nfor p in pathlib.Path('/proc').iterdir():\n if p.name.isdigit():\n  try: out.append([int(p.name),p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]])\n  except (OSError,IndexError): pass\nprint(json.dumps(out))"
            result = await self.exec("/opt/harbor-server/bin/python3 -c " + shlex.quote(code), timeout_sec=10)
            if result.return_code:
                raise RuntimeError("Cannot snapshot pre-solver processes")
            self._solver_baseline = json.loads(result.stdout)

    async def terminate_solver_processes(self, reason):
        """On timeout/error, stop new processes before the caller restores public.

        A normal native completion does not call this: required task services
        must remain available to the official verifier.
        """
        self._solver_cleanup_failed = True
        if self._solver_baseline is None:
            raise RuntimeError("Missing pre-solver process snapshot")
        code = '''import json,os,pathlib,signal,time
baseline=set(map(tuple,BASELINE))
def processes():
 out={}
 for p in pathlib.Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    stat=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
    out[int(p.name)]=(stat[19],int(stat[1]),stat[0])
   except (OSError,IndexError,ValueError): pass
 return out
current=processes(); keep=set(); pid=os.getpid()
while pid in current and pid not in keep:
 keep.add(pid); pid=current[pid][1]
events=[]
for sig in (signal.SIGTERM,signal.SIGKILL):
 for pid,(start,parent,state) in processes().items():
  if pid not in keep and (pid,start) not in baseline and state!='Z':
   try: os.kill(pid,sig); events.append({'pid':pid,'start':start,'signal':int(sig)})
   except ProcessLookupError: pass
 time.sleep(0.2)
remaining=[pid for pid,(start,parent,state) in processes().items() if pid not in keep and (pid,start) not in baseline and state!='Z']
print(json.dumps({'killed':events,'remaining_pids':remaining,'confirmed':not remaining}))
'''.replace("BASELINE", repr(self._solver_baseline), 1)
        result = await self.exec("/opt/harbor-server/bin/python3 -c " + shlex.quote(code), timeout_sec=10)
        if result.return_code:
            raise RuntimeError("Solver process cleanup failed")
        receipt = {"reason": reason, **json.loads(result.stdout)}
        if not receipt["confirmed"]:
            raise RuntimeError("Solver processes remain after cleanup: " + json.dumps(receipt))
        self._solver_cleanup_failed = False
        return receipt

    async def _start_server(self):
        await self._cleanup_server_resources()
        self._preserve_startup_log = False
        key = (self._baseline_cpu_offset, self._baseline_cpu_slots, self._effective_cpus)
        if key not in self._cpu_pools:
            pool = asyncio.Queue()
            for slot in range(self._baseline_cpu_slots):
                pool.put_nowait(slot)
            self._cpu_pools[key] = pool
        self._cpu_pool = self._cpu_pools[key]
        self._cpu_slot = await self._cpu_pool.get()
        self._staging_dir = Path(tempfile.mkdtemp(prefix="apex_baseline_staging_"))
        self._staging_dir.chmod(0o755)
        self._network_dir = Path(tempfile.mkdtemp(prefix="apex_baseline_net_"))
        upstream = Path(sys.modules[SingularityEnvironment.__module__].__file__).parent
        shutil.copy(upstream / "server.py", self._staging / "_hbexec.py")
        shutil.copy(upstream / "bootstrap.sh", self._staging / "bootstrap.sh")
        (self._staging / "bootstrap.sh").chmod(0o755)
        reserved, self._server_port = self._reserve_port()
        reserved.close()
        self._server_token = secrets.token_urlsafe(32)
        self._server_log_path = self._staging / "server.log"
        self._namespace = NetworkNamespace(Path(__file__).resolve().parent.parent,
                                            self._network_dir)
        await self._namespace.start(self._server_port, self._baseline_model_port,
                                    self._baseline_model_socket)
        bind = ["-B", f"{self._staging}:/staging",
                "-B", f"{self._namespace.resolver}:/etc/resolv.conf:ro",
                "-B", f"{Path(__file__).with_name('apex_rootmap_bootstrap.sh')}:/"
                      ".singularity.d/env/99-apex-rootmap.sh:ro"]
        for mount in self._mounts:
            if mount.get("type") == "bind":
                target = mount["target"]
                suffix = ":ro" if mount.get("read_only") and not target.endswith(":ro") else ""
                bind += ["-B", f"{mount['source']}:{target}{suffix}"]
        files = self.environment_dir / "files"
        if files.exists():
            bind += ["-B", f"{files}:/staging/env_files:ro"]
        cpus = self._effective_cpus
        memory = self._effective_memory_mb * 1024**2
        self._scope_unit = "apex-baseline-" + secrets.token_hex(6)
        command = ["systemd-run", "--user", "--scope", "--quiet",
                   "--unit", self._scope_unit, "-p", f"MemoryMax={memory}",
                   "-p", "MemorySwapMax=0", "-p", "TasksMax=4096",
                   sys.executable, str(Path(__file__).with_name("baseline_exec_limits.py")),
                   "--cpus", str(cpus), "--memory-bytes", str(memory),
                   "--cpu-offset", str(self._baseline_cpu_offset + self._cpu_slot * cpus), "--",
                   *self._namespace.command("singularity", "exec", "--cleanenv",
                       "--no-mount", "home,tmp,bind-paths,hostfs,cwd,sys",
                       "--pwd", self._workdir, "--writable-tmpfs", "--fakeroot",
                       "--drop-caps", "CAP_NET_ADMIN,CAP_NET_RAW,CAP_SYS_ADMIN",
                       "--containall", "--pid", *bind, self._sif_path,
                       "bash", "-c", 'exec /staging/bootstrap.sh "$@"', "bash",
                       self._workdir, "/staging/_hbexec.py", "--port", self._server_port,
                       "--workdir", self._workdir, "--instance-token", self._server_token)]
        allowed = {"PATH", "HOME", "USER", "LOGNAME", "XDG_RUNTIME_DIR",
                   "DBUS_SESSION_BUS_ADDRESS", "APPTAINER_IGNORE_SUBUID", "LANG"}
        environment = {key: value for key, value in os.environ.items() if key in allowed}
        environment["APPTAINER_IGNORE_SUBUID"] = "1"
        with self._server_log_path.open("wb") as log:
            self._server_process = await asyncio.create_subprocess_exec(
                *map(str, command), stdout=log, stderr=asyncio.subprocess.STDOUT,
                env=environment)
        self._http_client = httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(uds=str(self._namespace.control_socket)),
            timeout=2, trust_env=False, follow_redirects=False)
        deadline = asyncio.get_running_loop().time() + self._startup_timeout_sec
        while asyncio.get_running_loop().time() < deadline:
            try:
                health = await self._http_client.get("http://127.0.0.1/health")
                if health.status_code == 200 and health.json().get("instance_token") == self._server_token:
                    await self._apply_network_policy(self._network_policy)
                    return
            except (httpx.RequestError, ValueError):
                pass
            if self._server_process.returncode is not None:
                break
            await asyncio.sleep(0.5)
        self._preserve_startup_log = True
        raise RuntimeError(f"Baseline bootstrap failed; see {self._server_log_path}")

    async def _stop_server_process(self):
        confirmed = await super()._stop_server_process()
        if self._scope_unit:
            await asyncio.to_thread(subprocess.run,
                ["systemctl", "--user", "stop", self._scope_unit + ".scope"],
                capture_output=True, timeout=10)
            self._scope_unit = None
        if self._namespace:
            await self._namespace.close()
            self._namespace = None
        if self._network_dir:
            shutil.rmtree(self._network_dir, ignore_errors=True)
            self._network_dir = None
        if self._cpu_slot is not None:
            self._cpu_pool.put_nowait(self._cpu_slot)
            self._cpu_slot = None
        return confirmed
