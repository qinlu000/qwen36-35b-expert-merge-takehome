#!/usr/bin/env python3
"""Synthetic Harbor backend acceptance; never opens a benchmark task or solution."""
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading
import time

from baseline_singularity import BaselineSingularityEnvironment
from harbor.models.task.config import EnvironmentConfig, NetworkMode, NetworkPolicy
from harbor.models.trial.paths import TrialPaths


class SyntheticModel(BaseHTTPRequestHandler):
    def do_GET(self):
        raw = b'{"synthetic":true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        pass


async def main(args):
    root = args.root.resolve()
    directory = Path(tempfile.mkdtemp(prefix="smoke-", dir=root / "artifacts/preflight/backend_v2"))
    environment = directory / "environment"
    environment.mkdir()
    (environment / "Dockerfile").write_text("FROM synthetic/local\nWORKDIR /tmp\n")
    paths = TrialPaths(directory / "trial")
    paths.mkdir()
    model = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticModel)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    env = BaselineSingularityEnvironment(
        environment_dir=environment, environment_name="synthetic-baseline",
        session_id="synthetic-acceptance", trial_paths=paths,
        task_env_config=EnvironmentConfig(docker_image=str(args.image), cpus=args.cpus,
                                        memory_mb=args.memory_mb, gpus=0),
        baseline_cpu_offset=args.cpu_offset,
        baseline_cpu_slots=args.cpu_slots,
        baseline_model_host_port=model.server_address[1], singularity_startup_timeout_sec=300)
    report = {"scope": "Synthetic only; no benchmark instruction/tests/solutions or model calls",
              "image": str(args.image), "cpus": args.cpus, "memory_mb": args.memory_mb,
              "commands": []}

    async def command(label, code, timeout=20):
        result = await env.exec(code, timeout_sec=timeout)
        report["commands"].append({"label": label, **result.model_dump()})
        return result

    started = time.monotonic()
    try:
        await env.start(force_build=False)
        report["startup_seconds"] = time.monotonic() - started
        report["namespace_pid"] = env._namespace.owner.pid
        report["unit"] = env._scope_unit
        show = subprocess.run(["systemctl", "--user", "show", env._scope_unit + ".scope",
                               "--property=ControlGroup", "--value"], capture_output=True, text=True, check=True)
        group = Path("/sys/fs/cgroup") / show.stdout.strip().lstrip("/")
        report["cgroup"] = {name: (group / name).read_text().strip()
                            for name in ("memory.max", "memory.swap.max", "memory.events")}
        assert report["cgroup"]["memory.max"] == str(args.memory_mb * 1024**2)
        assert report["cgroup"]["memory.swap.max"] == "0"
        python = "/opt/harbor-server/bin/python3"
        resource_code = "import json,os,subprocess; a=sorted(os.sched_getaffinity(0)); print(json.dumps({'cpus':a,'user_namespace':os.readlink('/proc/self/ns/user'),'env_names':sorted(os.environ)})); "
        resource_code += "exec(\"try:\\n os.sched_setaffinity(0,range(4096))\\n print('EXPANSION_UNEXPECTED')\\nexcept PermissionError:\\n print('AFFINITY_BLOCKED')\"); "
        resource_code += "subprocess.run(['python3','-c',\"import os;print('CHILD_CPUS',len(os.sched_getaffinity(0)))\"],check=True)"
        result = await command("cpu-affinity-and-clean-env", python + " -c " + shlex.quote(resource_code))
        assert result.return_code == 0 and "AFFINITY_BLOCKED" in result.stdout
        assert "CHILD_CPUS " + str(args.cpus) in result.stdout
        assert "base_smoke_api_key" not in result.stdout
        result = await command("filesystem-boundaries", "test ! -e /data/caoqinlu/projects/apex-takehome/claud.md && test ! -S /run/user/1012/bus && test ! -e /sys/fs/cgroup/cgroup.procs && echo FILESYSTEM_BOUNDARIES_OK")
        assert result.return_code == 0
        public = python + " -c " + shlex.quote("import urllib.request; print(urllib.request.urlopen('https://github.com',timeout=12).status)")
        result = await command("public-network", public)
        assert result.return_code == 0 and result.stdout.strip() == "200"
        await env.set_network_policy(NetworkPolicy(network_mode=NetworkMode.NO_NETWORK))
        blocked = python + " -c " + shlex.quote("import urllib.request; print(urllib.request.urlopen('https://github.com',timeout=2).status)")
        result = await command("solver-public-egress-denied", blocked)
        assert result.return_code != 0
        direct = python + " -c " + shlex.quote("import socket; socket.create_connection(('20.205.243.166',443),2)")
        result = await command("solver-direct-IP-egress-denied", direct)
        assert result.return_code != 0
        result = await command("solver-model-fixed-bridge", python + " -c " + shlex.quote("import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:18000/',timeout=3).read().decode())"))
        assert result.return_code == 0 and json.loads(result.stdout)["synthetic"] is True
        netlink = "import socket,struct; s=socket.socket(socket.AF_NETLINK,socket.SOCK_RAW,0); s.bind((0,0)); p=struct.pack('BBHiII',0,0,0,1,1,1); s.send(struct.pack('IHHII',16+len(p),16,5,1,0)+p); r=s.recv(4096); e=struct.unpack('i',r[16:20])[0]; print('NETLINK_ERRNO',e); assert e==-1"
        result = await command("solver-cannot-administer-network", python + " -c " + shlex.quote(netlink))
        assert result.return_code == 0 and "NETLINK_ERRNO -1" in result.stdout
        raw = "import socket; s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,3)"
        result = await command("solver-cannot-bypass-firewall-with-raw-packets", python + " -c " + shlex.quote(raw))
        assert result.return_code != 0 and "Operation not permitted" in result.stdout
        result = await command("persistent-tmux", "tmux -S /tmp/apex-v2-test.sock new-session -d -s synthetic 'sleep 60'; tmux -S /tmp/apex-v2-test.sock has-session -t synthetic; echo TMUX_OK")
        assert result.return_code == 0 and "TMUX_OK" in result.stdout
        await env.set_network_policy(NetworkPolicy(network_mode=NetworkMode.PUBLIC))
        result = await command("verifier-public-restored", public)
        assert result.return_code == 0 and result.stdout.strip() == "200"
        result = await command("same-tmux-after-phase-change", "tmux -S /tmp/apex-v2-test.sock has-session -t synthetic && tmux -S /tmp/apex-v2-test.sock kill-server && echo PERSISTENT_TMUX_OK")
        assert result.return_code == 0
        await env.set_network_policy(NetworkPolicy(network_mode=NetworkMode.NO_NETWORK))
        heartbeat = "import pathlib,time\np=pathlib.Path('/tmp/apex-v2-heartbeat')\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.05)"
        spawn = "import subprocess; subprocess.Popen(['/opt/harbor-server/bin/python3','-c'," + repr(heartbeat) + "],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)"
        result = await command("spawn-detached-solver", python + " -c " + shlex.quote(spawn))
        assert result.return_code == 0
        await asyncio.sleep(0.2)
        report["timeout_cleanup"] = await env.terminate_solver_processes("synthetic timeout")
        assert report["timeout_cleanup"]["confirmed"] and report["timeout_cleanup"]["killed"]
        await env.set_network_policy(NetworkPolicy(network_mode=NetworkMode.PUBLIC))
        result = await command("server-survived-timeout-cleanup", "echo CLEANUP_OK")
        assert result.return_code == 0
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error=repr(error), server_log=str(env._server_log_path))
        raise
    finally:
        report["duration_seconds"] = time.monotonic() - started
        unit = env._scope_unit
        await env.stop(delete=True)
        model.shutdown()
        model.server_close()
        if unit:
            state = subprocess.run(["systemctl", "--user", "is-active", unit + ".scope"], capture_output=True, text=True)
            report["stopped_scope_state"] = state.stdout.strip()
            assert state.returncode != 0
        (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"directory": str(directory), **report}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--memory-mb", type=int, default=8192)
    parser.add_argument("--cpu-offset", type=int, default=32)
    parser.add_argument("--cpu-slots", type=int, default=1)
    parser.add_argument("--parallel", type=int, default=1)
    logging.basicConfig(level=logging.INFO)
    arguments = parser.parse_args()

    async def run():
        await asyncio.gather(*(main(arguments) for _ in range(arguments.parallel)))

    asyncio.run(run())
