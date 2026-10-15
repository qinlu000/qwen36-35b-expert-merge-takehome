#!/usr/bin/env python3
"""Self-authored, free/offline ASI isolation acceptance; never loads a task.

Run with the pinned ASI environment on 80. Receipts are ignored artifacts.
This is an opt-in candidate check, not a formal benchmark or protocol change.
"""

from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time

from ai4sci_bench.core.types import PromptLevel, TaskInstance
from asi_bwrap import BwrapOpenCodeAdapter
from asi_fixed_relay import FixedModelRelay


def run_task_env_cases(root, run, config, relay, requests, tool_command):
    """Use cached upstream env metadata, but exclusively self-authored inputs."""
    groups = json.loads((root / "configs/asi/task_requirements.json").read_text())["runtime_groups"]
    scientific_commands = {
        24: '''import numpy as np, scipy.linalg, sympy as sp, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
answer = scipy.linalg.solve(np.array([[3., 1.], [1., 2.]]), np.array([9., 8.]))
assert np.allclose(answer, [2., 3.])
x = sp.symbols("x")
factor = sp.factor(x*x - 1)
assert sp.expand(factor) == x*x - 1
plt.plot([0, 1], [0, 1]); plt.savefig("synthetic_plot.png"); plt.close()
checks.update(linear_solution=answer.tolist(), symbolic_factor=str(factor), plot_bytes=pathlib.Path("synthetic_plot.png").stat().st_size)
import re, shutil, subprocess
pathlib.Path("divider.cir").write_text("* Self-authored 1V divider\\nV1 in 0 1\\nR1 in out 1k\\nR2 out 0 1k\\n.control\\nop\\nprint v(out)\\nquit\\n.endc\\n.end\\n")
spice = subprocess.run(["ngspice", "-b", "divider.cir"], capture_output=True, text=True, timeout=15)
pathlib.Path("ngspice.log").write_text(spice.stdout + spice.stderr)
voltage = float(re.search(r"v\\(out\\)\\s*=\\s*([0-9.eE+-]+)", spice.stdout).group(1))
assert spice.returncode == 0 and abs(voltage - 0.5) < 1e-9
assert "Error" not in spice.stderr and "cannot open" not in spice.stderr
checks.update(ngspice_path=shutil.which("ngspice"), divider_voltage=voltage, ngspice_returncode=spice.returncode)
modules = {name: module.__file__ for name, module in (("numpy", np), ("sympy", sp))}
''',
        15: '''import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression
frame = pd.DataFrame({"x": [0., 1., 2., 3.], "y": [1., 3., 5., 7.]})
model = LinearRegression().fit(frame[["x"]], frame["y"])
assert np.allclose(model.coef_, [2.]) and abs(model.intercept_ - 1.) < 1e-9
checks.update(coefficient=model.coef_.tolist(), intercept=float(model.intercept_), rows=len(frame))
modules = {"numpy": np.__file__, "pandas": pd.__file__}
''',
        17: '''import numpy as np, torch
a = torch.tensor([[1., 2.], [3., 4.]], device="cpu")
product = a @ a
array = product.numpy()
assert np.allclose(array, [[7., 10.], [15., 22.]])
assert torch.from_numpy(array).device.type == "cpu"
checks.update(torch_version=torch.__version__, product=array.tolist(), device=str(product.device))
modules = {"numpy": np.__file__, "torch": torch.__file__}
''',
    }
    adapter = BwrapOpenCodeAdapter(model="synthetic-model", config=config, relay=relay,
        opencode_binary=root / "artifacts/tools/opencode-1.17.15/node_modules/opencode-linux-x64/bin/opencode",
        default_env=root / "artifacts/envs/asi-py312", ngspice_root=root / "artifacts/tools/ngspice",
        timeout_seconds=120)
    adapter.setup({"sandbox": "task", "repo_root": str(root / "artifacts/benchmarks/asi"), "timeout": 120})
    manager = adapter.task_env_manager
    results = []
    for number, scientific in scientific_commands.items():
        group = next(group for group in groups if group["group"] == number)
        runtime = group["runtime"]
        metadata = {"_runtime_python": runtime.get("python"), "_runtime_packages": runtime.get("packages", []),
                    "output": {"files": [{"name": "science.json"}]}}
        cache_key = manager.compute_cache_key(metadata)
        # This acceptance must never install or mutate an upstream task env.
        if not manager._is_cache_hit(manager.cache_root / cache_key):
            raise RuntimeError(f"Required preinstalled env group {number} is not cached")
        task_env = manager.ensure_env(metadata)
        workspace = run / f"env-{number:02d}"
        workspace.mkdir()
        (workspace / "prompt.md").write_text("Use bash to run python science.py, then finish. Self-authored scientific environment check.\n")
        script = "import json, os, pathlib, sys\nchecks = {}\n" + scientific + '''
report = {"checks": checks, "env_dir": sys.prefix, "executable": sys.executable,
          "virtual_env": os.environ.get("VIRTUAL_ENV"), "modules": modules}
pathlib.Path("science.json").write_text(json.dumps(report, indent=2) + "\\n")
print("Self-authored scientific environment check passed.")
'''
        (workspace / "science.py").write_text(script)
        tool_command[0] = "python science.py"
        before = len(requests)
        instance = TaskInstance(task_id="synthetic-runtime", instance_id=f"synthetic-runtime-{number}", task_dir=run,
            workspace_dir=workspace, reference_dir=run / "unused-empty-reference", prompt_level=PromptLevel.B3,
            parameters={}, metadata=metadata, effective_timeout_seconds=120)
        output = adapter.solve(instance)
        (workspace / "stdout.jsonl").write_text(output.raw_stdout or "")
        (workspace / "stderr.log").write_text(output.raw_stderr or "")
        (workspace / "mounts.json").write_text(json.dumps(adapter.last_mounts, indent=2) + "\n")
        report = json.loads((workspace / "science.json").read_text()) if (workspace / "science.json").exists() else {}
        env_dir = str(task_env.env_dir)
        mounts = adapter.last_mounts
        passed = (output.status.value == "completed" and task_env.cache_hit
            and report.get("env_dir") == env_dir and report.get("virtual_env") == env_dir
            and all(path.startswith(env_dir + "/") for path in report.get("modules", {}).values())
            and any(mount["source"] == env_dir and mount["readonly"] for mount in mounts)
            and not any(mount["source"] == str(adapter.default_env) for mount in mounts)
            and any(request["tool_feedback"] for request in requests[before:]))
        results.append({"group": number, "passed": bool(passed), "status": output.status.value,
            "error": output.error_message, "cache_hit": task_env.cache_hit, "cache_key": task_env.cache_key,
            "env_dir": env_dir, "runtime": runtime, "science": report,
            "default_env_mounted": any(mount["source"] == str(adapter.default_env) for mount in mounts),
            "ngspice_ro_mounted": any(mount["source"] == str(adapter.ngspice_root) and mount["readonly"] for mount in mounts),
            "native_usage_parsed": output.cost is not None, "native_stdout_format": output.raw_stdout_format})
    return {"passed": all(result["passed"] for result in results), "run_dir": str(run), "cases": results,
        "task_env_manager_tested": True, "candidate_only": True, "cpu_limit_enforced": False,
        "memory_limit_enforced": False, "real_vllm_tested": False, "benchmark_tasks_executed": 0,
        "paid_api_calls": 0, "formal_protocol_changed": False, "request_count": len(requests)}


def main():
    root = Path(__file__).resolve().parents[1]
    receipts = root / "artifacts/preflight/asi"
    receipts.mkdir(parents=True, exist_ok=True)
    task_env_only = "--task-env" in sys.argv[1:]
    run = Path(tempfile.mkdtemp(prefix="bwrap-task-env-" if task_env_only else "bwrap-candidate-", dir=receipts))
    workspace = run / "workspace"
    workspace.mkdir()
    (workspace / "data").mkdir()
    (workspace / "prompt.md").write_text("Run python check_boundary.py using bash, then finish. Self-authored isolation test.\n")
    (workspace / "task_info.json").write_text('{"synthetic": true}\n')
    sentinel = run / "controller-only-sentinel.txt"
    sentinel.write_text("synthetic controller-owned file; never an official answer\n")
    key = "synthetic-controller-" + secrets.token_urlsafe(24)
    os.environ["ASI_SYNTHETIC_CONTROLLER_SECRET"] = key
    host_ns = {name: os.readlink(f"/proc/self/ns/{name}") for name in ("user", "mnt", "pid", "net")}
    requests = []
    tool_command = ["python check_boundary.py"]

    class FakeModel(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            tools = {tool["function"]["name"] for tool in body.get("tools", [])}
            feedback = any(message.get("role") == "tool" for message in body.get("messages", []))
            requests.append({"path": self.path, "model": body.get("model"),
                             "controller_auth_received": self.headers.get("Authorization") == "Bearer " + key,
                             "tool_feedback": feedback, "stream": body.get("stream", False)})
            call_tool = "bash" in tools and not feedback
            tool_call = {"id": "synthetic_boundary_tool", "type": "function", "function": {
                "name": "bash", "arguments": json.dumps({"command": tool_command[0],
                                                          "description": "Check the synthetic isolation boundary"})}}
            text = "Synthetic boundary check finished."
            usage = {"prompt_tokens": 30, "completion_tokens": 12, "total_tokens": 42}
            self.send_response(200)
            if body.get("stream"):
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                deltas = [{"role": "assistant"}]
                deltas += ([{"tool_calls": [{"index": 0, **tool_call}]}] if call_tool else [{"content": text}])
                for delta in deltas:
                    chunk = {"id": "synthetic", "object": "chat.completion.chunk", "created": int(time.time()),
                             "model": "synthetic-model", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                    self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                    self.wfile.flush()
                chunk["choices"] = [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if call_tool else "stop"}]
                chunk["usage"] = usage
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
            else:
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"id": "synthetic", "object": "chat.completion", "model": "synthetic-model",
                    "created": int(time.time()), "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop"}], "usage": usage}).encode())
            self.wfile.flush()

    fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    probe_settings = {"sentinel": str(sentinel), "controller_pid": os.getpid(), "host_ns": host_ns,
                      "host_port": fake.server_port, "secret_sha256": hashlib.sha256(key.encode()).hexdigest(),
                      "project_root": str(root), "host_home": str(Path.home())}
    # Only self-authored paths and a synthetic secret's digest go into this input.
    probe = '''import hashlib, http.client, json, os, pathlib, socket
settings = SETTINGS
config = json.loads(os.environ["OPENCODE_CONFIG_CONTENT"])
token = config["provider"]["bench"]["options"]["apiKey"]
def request(method, path, model="synthetic-model", authorized=True, content=None):
    connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=10)
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "synthetic relay probe" if content is None else content}]})
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token if authorized else "Bearer invalid"}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    status = response.status
    response.read()
    connection.close()
    return status
def connects(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False
namespaces = {name: os.readlink("/proc/self/ns/" + name) for name in settings["host_ns"]}
secret_seen = False
for path in pathlib.Path("/proc").glob("[0-9]*/environ"):
    try:
        for value in path.read_bytes().split(b"\\0"):
            if b"=" in value and hashlib.sha256(value.split(b"=", 1)[1]).hexdigest() == settings["secret_sha256"]:
                secret_seen = True
    except OSError:
        pass
report = {
    "namespace_ids": namespaces,
    "namespace_separate": {name: namespaces[name] != value for name, value in settings["host_ns"].items()},
    "sentinel_readable": pathlib.Path(settings["sentinel"]).exists(),
    "host_proc_environ_readable": pathlib.Path("/proc/" + str(settings["controller_pid"]) + "/environ").exists(),
    "host_root_via_proc1_readable": pathlib.Path("/proc/1/root" + settings["sentinel"]).exists(),
    "project_scripts_visible": pathlib.Path(settings["project_root"] + "/scripts/setup_asi.sh").exists(),
    "reference_root_visible": pathlib.Path(settings["project_root"] + "/artifacts/benchmarks/asi/tasks").exists(),
    "host_ssh_visible": pathlib.Path(settings["host_home"] + "/.ssh").exists(),
    "controller_secret_in_namespace_environ": secret_seen,
    "controller_secret_env_name_present": "ASI_SYNTHETIC_CONTROLLER_SECRET" in os.environ,
    "host_loopback_connected": connects("127.0.0.1", settings["host_port"]),
    "external_connected": connects("1.1.1.1", 443),
    "interfaces": socket.if_nameindex(),
    "routes": pathlib.Path("/proc/net/route").read_text().splitlines()[1:],
    "cap_eff": next(line.split()[1] for line in pathlib.Path("/proc/self/status").read_text().splitlines() if line.startswith("CapEff:")),
    "relay_status": {"allowed": request("POST", "/v1/chat/completions"),
        "wrong_path": request("POST", "/v1/other"),
        "absolute_url": request("POST", "http://example.invalid/v1/chat/completions"),
        "query": request("POST", "/v1/chat/completions?url=http://example.invalid"),
        "connect": request("CONNECT", "example.invalid:443"),
        "wrong_model": request("POST", "/v1/chat/completions", model="other-model"),
        "wrong_token": request("POST", "/v1/chat/completions", authorized=False),
        "remote_image": request("POST", "/v1/chat/completions", content=[{"type": "image_url", "image_url": {"url": "https://example.invalid/private.png"}}]),
        "remote_video": request("POST", "/v1/chat/completions", content=[{"type": "video_url", "video_url": {"url": "https://example.invalid/private.mp4"}}]),
        "data_image": request("POST", "/v1/chat/completions", content=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRc8AAAAASUVORK5CYII="}}])},
    "writable_workspace": pathlib.Path.cwd() == pathlib.Path("/workspace"),
}
try:
    pathlib.Path("/workspace/prompt.md").write_text("unexpected mutation")
    report["prompt_readonly"] = False
except OSError:
    report["prompt_readonly"] = True
pathlib.Path("isolation.json").write_text(json.dumps(report, indent=2) + "\\n")
print("Synthetic isolation probe written.")
'''.replace("SETTINGS", repr(probe_settings), 1)
    (workspace / "check_boundary.py").write_text(probe)
    config = json.loads((root / "configs/asi/opencode.json").read_text())
    config["model"] = config["small_model"] = "bench/synthetic-model"
    model = config["provider"]["bench"]["models"].pop("apex-qwen")
    model["name"] = "synthetic-model"
    config["provider"]["bench"]["models"]["synthetic-model"] = model
    for name in ("title", "summary", "compaction"):
        config["agent"][name]["model"] = "bench/synthetic-model"
    try:
        # Short /tmp path avoids Linux's 108-byte Unix socket path ceiling.
        with tempfile.TemporaryDirectory(prefix="asi-relay-") as relay_dir:
            with FixedModelRelay(Path(relay_dir) / "model.sock", base_url=f"http://127.0.0.1:{fake.server_port}/v1",
                                 model="synthetic-model", api_key=key, timeout=120) as relay:
                if task_env_only:
                    summary = run_task_env_cases(root, run, config, relay, requests, tool_command)
                    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
                    print(json.dumps(summary, indent=2))
                    if not summary["passed"]:
                        raise SystemExit(1)
                    return
                adapter = BwrapOpenCodeAdapter(model="synthetic-model", config=config, relay=relay,
                    opencode_binary=root / "artifacts/tools/opencode-1.17.15/node_modules/opencode-linux-x64/bin/opencode",
                    default_env=root / "artifacts/envs/asi-py312", ngspice_root=root / "artifacts/tools/ngspice",
                    timeout_seconds=120)
                adapter.setup({"sandbox": "none", "repo_root": str(root / "artifacts/benchmarks/asi"), "timeout": 120})
                instance = TaskInstance(task_id="synthetic-only", instance_id="synthetic-only", task_dir=run,
                    workspace_dir=workspace, reference_dir=run / "unused-empty-reference", prompt_level=PromptLevel.B3,
                    parameters={}, metadata={"output": {"files": [{"name": "isolation.json"}]}}, effective_timeout_seconds=120)
                output = adapter.solve(instance)
                (run / "stdout.jsonl").write_text(output.raw_stdout or "")
                (run / "stderr.log").write_text(output.raw_stderr or "")
                (run / "mounts.json").write_text(json.dumps(adapter.last_mounts, indent=2) + "\n")
                report = json.loads((workspace / "isolation.json").read_text()) if (workspace / "isolation.json").exists() else {}
                negative_checks = ("sentinel_readable", "host_proc_environ_readable", "host_root_via_proc1_readable",
                    "project_scripts_visible", "reference_root_visible", "host_ssh_visible", "controller_secret_in_namespace_environ",
                    "controller_secret_env_name_present", "host_loopback_connected", "external_connected")
                expected_status = {"allowed": 200, "wrong_path": 403, "absolute_url": 403, "query": 403,
                                   "connect": 403, "wrong_model": 403, "wrong_token": 401,
                                   "remote_image": 403, "remote_video": 403, "data_image": 200}
                passed = bool(report) and (output.status.value == "completed"
                    and all(report.get(name) is False for name in negative_checks)
                    and all(report.get("namespace_separate", {}).values())
                    and len(report.get("namespace_separate", {})) == 4
                    and report.get("relay_status") == expected_status
                    and report.get("cap_eff") == "0000000000000000"
                    and report.get("routes") == [] and report.get("interfaces") == [[1, "lo"]]
                    and report.get("prompt_readonly") and report.get("writable_workspace")
                    and all(request["controller_auth_received"] for request in requests)
                    and any(request["tool_feedback"] for request in requests)
                    and key not in (output.raw_stdout or "") + (output.raw_stderr or ""))
                summary = {"passed": bool(passed), "adapter_status": output.status.value, "error": output.error_message,
                    "run_dir": str(run), "native_stdout_format": output.raw_stdout_format,
                    "native_usage_parsed": output.cost is not None, "request_count": len(requests),
                    "requests": requests, "relay_events": relay.events, "isolation": report,
                    "cpu_limit_enforced": False, "memory_limit_enforced": False,
                    "formal_protocol_changed": False, "benchmark_tasks_executed": 0, "paid_api_calls": 0,
                    "candidate_only": True, "task_env_manager_tested": False}
                if not passed:
                    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
                    print(json.dumps(summary, indent=2))
                    raise SystemExit(1)
                # A second, self-authored run hangs with a detached child. This
                # exercises native TERM/KILL handling, rather than trusting flags.
                tool_command[0] = "python hang.py"
                hanging = run / "timeout-workspace"
                hanging.mkdir()
                (hanging / "prompt.md").write_text("Use bash to run python hang.py. Synthetic timeout check.\n")
                (hanging / "hang.py").write_text('''import json, os, pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], start_new_session=True)
pathlib.Path("started.json").write_text(json.dumps({"pid_ns": os.readlink("/proc/self/ns/pid"), "pid": os.getpid(), "child": child.pid}))
while True:
    pathlib.Path("heartbeat.txt").write_text(str(time.time_ns()))
    time.sleep(0.1)
''')
                instance.workspace_dir = hanging
                instance.instance_id = "synthetic-timeout"
                instance.effective_timeout_seconds = 8
                started = time.monotonic()
                timed = adapter.solve(instance)
                duration = time.monotonic() - started
                (run / "timeout-stdout.jsonl").write_text(timed.raw_stdout or "")
                (run / "timeout-stderr.log").write_text(timed.raw_stderr or "")
                marker = json.loads((hanging / "started.json").read_text()) if (hanging / "started.json").exists() else {}
                heartbeat = hanging / "heartbeat.txt"
                old_heartbeat = heartbeat.read_text() if heartbeat.exists() else None
                # Bound to one second; this is a liveness measurement, not setup.
                time.sleep(1)
                heartbeat_stopped = old_heartbeat is not None and heartbeat.read_text() == old_heartbeat
                same_namespace = []
                if marker:
                    for path in Path("/proc").glob("[0-9]*/ns/pid"):
                        try:
                            if os.readlink(path) == marker["pid_ns"]:
                                same_namespace.append(int(path.parts[2]))
                        except OSError:
                            pass
                summary["timeout_check"] = {"status": timed.status.value, "seconds": round(duration, 3),
                    "hanging_tool_started": bool(marker), "heartbeat_stopped": heartbeat_stopped,
                    "remaining_namespace_processes": same_namespace,
                    "passed": timed.status.value == "timeout" and bool(marker) and heartbeat_stopped and not same_namespace}
                summary["passed"] = summary["passed"] and summary["timeout_check"]["passed"]
            summary["relay_socket_removed"] = not relay.socket_path.exists()
            summary["passed"] = summary["passed"] and summary["relay_socket_removed"]
            summary["request_count"] = len(requests)
        (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        if not summary["passed"]:
            raise SystemExit(1)
    finally:
        fake.shutdown()
        fake.server_close()
        os.environ.pop("ASI_SYNTHETIC_CONTROLLER_SECRET", None)


if __name__ == "__main__":
    main()
