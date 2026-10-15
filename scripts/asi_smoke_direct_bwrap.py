#!/usr/bin/env python3
"""Stub one controller completion; exercise native DirectLLM solve and bwrap.

Only dependency metadata and self-authored programs are used. No real API,
benchmark input, reference, grading, regeneration, or interactive model tools.
"""

import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from ai4sci_bench.core.types import PromptLevel, TaskInstance
from asi_direct_bwrap import BwrapDirectLLMAdapter


SCIENCE = {
    24: '''import numpy as np, scipy.linalg, sympy as sp, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
solution = scipy.linalg.solve([[3., 1.], [1., 2.]], [9., 8.])
assert np.allclose(solution, [2., 3.])
x = sp.symbols("x")
assert sp.expand(sp.factor(x*x - 1)) == x*x - 1
plt.plot([0, 1], [0, 1]); plt.savefig("synthetic_plot.png"); plt.close()
import re, shutil, subprocess
pathlib.Path("divider.cir").write_text("* Synthetic 1V divider\\nV1 in 0 1\\nR1 in out 1k\\nR2 out 0 1k\\n.control\\nop\\nprint v(out)\\nquit\\n.endc\\n.end\\n")
spice = subprocess.run(["ngspice", "-b", "divider.cir"], capture_output=True, text=True, timeout=15)
pathlib.Path("ngspice.log").write_text(spice.stdout + spice.stderr)
voltage = float(re.search(r"v\\(out\\)\\s*=\\s*([0-9.eE+-]+)", spice.stdout).group(1))
assert spice.returncode == 0 and abs(voltage - 0.5) < 1e-9
assert "Error" not in spice.stderr and "cannot open" not in spice.stderr
checks = {"solution": solution.tolist(), "divider_voltage": voltage, "ngspice_path": shutil.which("ngspice"),
          "plot_bytes": pathlib.Path("synthetic_plot.png").stat().st_size}
modules = {"numpy": np.__file__, "sympy": sp.__file__}
''',
    15: '''import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression
frame = pd.DataFrame({"x": [0., 1., 2.], "y": [1., 3., 5.]})
model = LinearRegression().fit(frame[["x"]], frame["y"])
assert np.allclose(model.coef_, [2.]) and abs(model.intercept_ - 1) < 1e-9
checks = {"coefficient": model.coef_.tolist(), "intercept": float(model.intercept_)}
modules = {"numpy": np.__file__, "pandas": pd.__file__}
''',
    17: '''import numpy as np, torch
a = torch.tensor([[1., 2.], [3., 4.]], device="cpu")
product = (a @ a).numpy()
assert np.allclose(product, [[7., 10.], [15., 22.]])
assert torch.from_numpy(product).device.type == "cpu"
checks = {"product": product.tolist(), "device": "cpu", "torch_version": torch.__version__}
modules = {"numpy": np.__file__, "torch": torch.__file__}
''',
}

BOUNDARY = '''import hashlib, json, os, pathlib, socket, sys
settings = SETTINGS
def connects(host, port):
    try:
        with socket.create_connection((host, port), timeout=1): return True
    except OSError: return False
secret_seen = False
for path in pathlib.Path("/proc").glob("[0-9]*/environ"):
    try:
        for entry in path.read_bytes().split(b"\\0"):
            if b"=" in entry and hashlib.sha256(entry.split(b"=", 1)[1]).hexdigest() == settings["secret_sha256"]:
                secret_seen = True
    except OSError: pass
boundary = {
    "namespace_separate": {name: os.readlink("/proc/self/ns/" + name) != value for name, value in settings["host_ns"].items()},
    "sentinel_visible": pathlib.Path(settings["sentinel"]).exists(),
    "host_proc_visible": pathlib.Path("/proc/" + str(settings["controller_pid"]) + "/environ").exists(),
    "host_root_via_proc1_visible": pathlib.Path("/proc/1/root" + settings["sentinel"]).exists(),
    "project_visible": pathlib.Path(settings["project"] + "/scripts/setup_asi.sh").exists(),
    "reference_visible": pathlib.Path(settings["project"] + "/artifacts/benchmarks/asi/tasks").exists(),
    "host_ssh_visible": pathlib.Path(settings["home"] + "/.ssh").exists(),
    "controller_secret_seen": secret_seen,
    "controller_env_name_present": "ASI_SYNTHETIC_CONTROLLER_SECRET" in os.environ,
    "host_loopback_connected": connects("127.0.0.1", settings["host_port"]),
    "external_connected": connects("1.1.1.1", 443),
    "interfaces": socket.if_nameindex(), "routes": pathlib.Path("/proc/net/route").read_text().splitlines()[1:],
    "cap_eff": next(line.split()[1] for line in pathlib.Path("/proc/self/status").read_text().splitlines() if line.startswith("CapEff:")),
    "run_entries": sorted(path.name for path in pathlib.Path("/run").iterdir()),
    "opencode_visible": pathlib.Path("/opt/apex/bin/opencode").exists(),
    "opencode_config_present": "OPENCODE_CONFIG_CONTENT" in os.environ,
}
try:
    pathlib.Path("prompt.md").write_text("unexpected mutation")
    boundary["prompt_readonly"] = False
except OSError: boundary["prompt_readonly"] = True
'''


def main():
    root = Path(__file__).resolve().parents[1]
    receipts = root / "artifacts/preflight/asi"
    run = Path(tempfile.mkdtemp(prefix="direct-bwrap-", dir=receipts))
    sentinel = run / "controller-only-sentinel.txt"
    sentinel.write_text("Self-authored controller sentinel\n")
    secret = "synthetic-only-" + secrets.token_urlsafe(24)
    os.environ["ASI_SYNTHETIC_CONTROLLER_SECRET"] = secret
    groups = json.loads((root / "configs/asi/task_requirements.json").read_text())["runtime_groups"]
    results = []
    with socket.socket() as host_listener:
        host_listener.bind(("127.0.0.1", 0)); host_listener.listen()
        settings = {"sentinel": str(sentinel), "controller_pid": os.getpid(), "project": str(root),
            "home": str(Path.home()), "host_port": host_listener.getsockname()[1],
            "secret_sha256": hashlib.sha256(secret.encode()).hexdigest(),
            "host_ns": {name: os.readlink(f"/proc/self/ns/{name}") for name in ("user", "mnt", "pid", "net")}}
        try:
            for number, timeout_case in ((24, False), (15, False), (17, False), (24, True)):
                name = "timeout" if timeout_case else f"env-{number}"
                workspace = run / name
                workspace.mkdir()
                (workspace / "prompt.md").write_text("Generate one complete Python program for a self-authored environment check.\n")
                (workspace / "data").mkdir()
                (workspace / "data/input.txt").write_text("synthetic input\n")
                runtime = next(group["runtime"] for group in groups if group["group"] == number)
                metadata = {"_runtime_python": runtime.get("python"), "_runtime_packages": runtime.get("packages", []),
                    "output": {"files": [{"name": "generated.py", "type": "code"}, {"name": "science.json", "type": "data"}]}}
                program = BOUNDARY.replace("SETTINGS", repr(settings), 1)
                if timeout_case:
                    program += '''import subprocess, time
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], start_new_session=True)
pathlib.Path("started.json").write_text(json.dumps({"pid_ns": os.readlink("/proc/self/ns/pid")}))
while True:
    pathlib.Path("heartbeat.txt").write_text(str(time.time_ns()))
    time.sleep(0.1)
'''
                else:
                    program += SCIENCE[number] + '''
report = {"boundary": boundary, "checks": checks, "env_dir": sys.prefix, "executable": sys.executable,
          "virtual_env": os.environ.get("VIRTUAL_ENV"), "modules": modules}
pathlib.Path("science.json").write_text(json.dumps(report, indent=2) + "\\n")
print("Synthetic direct program finished.")
'''
                generation_calls = []

                def completion(**kwargs):
                    generation_calls.append({"message_roles": [m["role"] for m in kwargs["messages"]],
                                             "tools_present": "tools" in kwargs})
                    return SimpleNamespace(id="synthetic-completion", choices=[SimpleNamespace(finish_reason="stop",
                        message=SimpleNamespace(content="```python\n" + program + "\n```", tool_calls=None))],
                        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=5))

                adapter = BwrapDirectLLMAdapter(model="openai/synthetic", api_key=secret,
                                               ngspice_root=root / "artifacts/tools/ngspice")
                adapter.setup({"sandbox": "task", "repo_root": str(root / "artifacts/benchmarks/asi"), "timeout": 120})
                manager = adapter.task_env_manager
                if not manager._is_cache_hit(manager.cache_root / manager.compute_cache_key(metadata)):
                    raise RuntimeError("This smoke requires a preinstalled cached task env")
                task_env = manager.ensure_env(metadata)
                instance = TaskInstance(task_id="synthetic-direct", instance_id=name, task_dir=run, workspace_dir=workspace,
                    reference_dir=run / "unused-reference", prompt_level=PromptLevel.B3, parameters={}, metadata=metadata,
                    effective_timeout_seconds=8 if timeout_case else 120)
                started = time.monotonic()
                with patch("litellm.completion", side_effect=completion):
                    output = adapter.solve(instance)
                elapsed = time.monotonic() - started
                (workspace / "stdout.log").write_text(output.raw_stdout or "")
                (workspace / "stderr.log").write_text(output.raw_stderr or "")
                (workspace / "native_log.json").write_text(output.raw_model_output or "")
                (workspace / "mounts.json").write_text(json.dumps(adapter.last_mounts, indent=2) + "\n")
                native_log = json.loads(output.raw_model_output)
                extraction = next(event for event in native_log if event["step"] == "code_extraction")
                base_pass = (len(generation_calls) == adapter.execution_count == len(output.model_call_records) == 1
                    and extraction["selected_code"] == program.strip()
                    and len([event for event in native_log if event["step"] == "code_execution"]) == 1
                    and generation_calls[0] == {"message_roles": ["system", "user"], "tools_present": False}
                    and output.code_files == ["generated.py"] and task_env.cache_hit
                    and secret not in (output.raw_model_output or "") + (output.raw_stdout or "") + (output.raw_stderr or ""))
                case = {"name": name, "group": number, "status": output.status.value, "seconds": round(elapsed, 3),
                    "generation_count": len(generation_calls), "execution_count": adapter.execution_count,
                    "native_extraction_preserved": extraction["selected_code"] == program.strip(),
                    "collected_code": output.code_files, "collected_data": output.data_files,
                    "env_dir": str(task_env.env_dir), "cache_hit": task_env.cache_hit}
                if timeout_case:
                    marker = json.loads((workspace / "started.json").read_text()) if (workspace / "started.json").exists() else {}
                    old = (workspace / "heartbeat.txt").read_text() if marker else None
                    time.sleep(1)
                    stopped = old is not None and (workspace / "heartbeat.txt").read_text() == old
                    remaining = []
                    for path in Path("/proc").glob("[0-9]*/ns/pid"):
                        try:
                            if marker and os.readlink(path) == marker["pid_ns"]: remaining.append(int(path.parts[2]))
                        except OSError: pass
                    case.update(heartbeat_stopped=stopped, remaining_namespace_processes=remaining, native_log=output.log)
                    case["passed"] = base_pass and output.status.value == "failed" and "Execution timed out (8s)" in output.log and stopped and not remaining
                else:
                    report = json.loads((workspace / "science.json").read_text()) if (workspace / "science.json").exists() else {}
                    boundary = report.get("boundary", {})
                    negative = ("sentinel_visible", "host_proc_visible", "host_root_via_proc1_visible", "project_visible",
                        "reference_visible", "host_ssh_visible", "controller_secret_seen", "controller_env_name_present",
                        "host_loopback_connected", "external_connected", "opencode_visible", "opencode_config_present")
                    passed = (base_pass and output.status.value == "completed" and output.data_files == ["science.json"]
                        and report.get("env_dir") == str(task_env.env_dir) and report.get("virtual_env") == str(task_env.env_dir)
                        and all(path.startswith(str(task_env.env_dir) + "/") for path in report.get("modules", {}).values())
                        and all(boundary.get(name) is False for name in negative)
                        and len(boundary.get("namespace_separate", {})) == 4 and all(boundary.get("namespace_separate", {}).values())
                        and boundary.get("cap_eff") == "0000000000000000" and boundary.get("prompt_readonly")
                        and boundary.get("interfaces") == [[1, "lo"]] and boundary.get("routes") == [] and boundary.get("run_entries") == [])
                    case.update(passed=bool(passed), report=report)
                results.append(case)
            summary = {"passed": all(case["passed"] for case in results), "run_dir": str(run), "cases": results,
                "generation_stubbed": True, "real_api_requests": 0, "benchmark_tasks_executed": 0,
                "candidate_only": True, "native_task_env_tested": True, "ngspice_tested": True,
                "shared1200s_deadline_implemented": False, "request64k8k_policy_implemented": False,
                "cpu_limit_enforced": False, "memory_limit_enforced": False, "real_vllm_tested": False}
            (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(json.dumps(summary, indent=2))
            if not summary["passed"]: raise SystemExit(1)
        finally:
            os.environ.pop("ASI_SYNTHETIC_CONTROLLER_SECRET", None)


if __name__ == "__main__":
    main()
