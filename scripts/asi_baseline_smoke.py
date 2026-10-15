#!/usr/bin/env python3
"""Self-authored ASI v2 acceptance; no benchmark inputs, judge or real API."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
from unittest.mock import patch

import httpx
from ai4sci_bench.core.types import PromptLevel, TaskInstance
from asi_smoke_direct_bwrap import SCIENCE
from run_asi_baseline_v2 import BaselineDirectLLM, write_json, run_condition, condition_worker, worker_init
from ai4sci_bench.runner.orchestrator import BenchmarkOrchestrator, RunConfig


BOUNDARY = '''import json, os, pathlib, socket, subprocess, sys
affinity = sorted(os.sched_getaffinity(0))
assert len(affinity) == 4
try:
    os.sched_setaffinity(0, range(4096))
    widened = True
except OSError as error:
    assert error.errno == 1
    widened = False
child_affinity = json.loads(subprocess.check_output([sys.executable, "-c", "import json,os; print(json.dumps(sorted(os.sched_getaffinity(0))))"], text=True))
assert child_affinity == affinity and not widened
assert "ASI_SYNTHETIC_SECRET" not in os.environ
assert not pathlib.Path(SENTINEL).exists()
assert not pathlib.Path(PROJECT + "/artifacts/benchmarks/asi/tasks").exists()
assert not pathlib.Path(PROJECT + "/artifacts/private").exists()
assert sorted(path.name for path in pathlib.Path("/run").iterdir()) == []
for host, port in [("127.0.0.1", PORT), ("1.1.1.1", 443)]:
    try:
        socket.create_connection((host, port), timeout=.2)
        raise AssertionError("Network connection unexpectedly succeeded")
    except OSError:
        pass
try:
    pathlib.Path("prompt.md").write_text("mutation")
    raise AssertionError("prompt is writable")
except OSError:
    pass
'''


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append({"path": self.path, "body": body})
        if self.path == "/tokenize":
            payload = {"count": self.server.prompt_tokens}
        else:
            if self.server.disconnect:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            barrier = getattr(self.server, "generation_barrier", None)
            if barrier is not None:
                barrier.wait(timeout=30)
            time.sleep(self.server.delay)
            payload = {"id": "synthetic-asi", "object": "chat.completion", "created": 0,
                "model": "apex-qwen", "choices": [{"index": 0, "finish_reason": getattr(self.server, "finish_reason", "stop"),
                    "message": {"role": "assistant", "content": "```python\n" + self.server.program + "\n```"}}],
                "usage": {"prompt_tokens": self.server.prompt_tokens, "completion_tokens": 10,
                          "total_tokens": self.server.prompt_tokens + 10}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.project.resolve()
    run = Path(tempfile.mkdtemp(prefix="baseline-v2-", dir=root / "artifacts/preflight/asi"))
    key = run / "synthetic.key"
    key.write_text("self-authored-acceptance-only")
    sentinel = run / "controller-sentinel"
    sentinel.write_text("self-authored controller sentinel")
    os.environ["ASI_SYNTHETIC_SECRET"] = "controller-only-self-authored"
    groups = json.loads((root / "configs/asi/task_requirements.json").read_text())["runtime_groups"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cases = []
    try:
        for number, mode in [(24, "science"), (15, "science"), (17, "science"),
                             (24, "deadline"), (24, "overflow"), (24, "ambiguous"),
                             (24, "safe_connect_retry"), (24, "length")]:
            name = f"env{number}-{mode}"
            workspace = run / name
            workspace.mkdir()
            (workspace / "prompt.md").write_text("Write a complete Python program for this self-authored synthetic acceptance.\n")
            (workspace / "data").mkdir()
            (workspace / "data/input.txt").write_text("self-authored input")
            runtime = next(group["runtime"] for group in groups if group["group"] == number)
            metadata = {"_runtime_python": runtime.get("python"), "_runtime_packages": runtime.get("packages", []),
                "output": {"files": [{"name": "generated.py", "type": "code"}, {"name": "science.json", "type": "data"}]}}
            program = BOUNDARY.replace("SENTINEL", repr(str(sentinel))).replace("PROJECT", repr(str(root))).replace("PORT", str(server.server_port))
            if mode == "deadline":
                program += '''import time
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], start_new_session=True)
pathlib.Path("pid_namespace").write_text(os.readlink("/proc/self/ns/pid"))
while True:
    pathlib.Path("heartbeat").write_text(str(time.time_ns()))
    time.sleep(.1)
'''
            else:
                program += SCIENCE[number] + '''
pathlib.Path("science.json").write_text(json.dumps({"checks": checks, "affinity": affinity, "child_affinity": child_affinity, "widened": widened, "modules": modules, "prefix": sys.prefix}))
'''
            server.requests, server.program = [], program
            server.finish_reason = "length" if mode == "length" else "stop"
            server.prompt_tokens = 57345 if mode == "overflow" else 123
            server.disconnect, server.delay = mode == "ambiguous", 1.0 if mode == "deadline" else 0
            adapter = BaselineDirectLLM(endpoint=f"http://127.0.0.1:{server.server_port}", key_file=key,
                protocol={}, ngspice_root=root / "artifacts/tools/ngspice", audit_dir=run / "audit")
            adapter.setup({"sandbox": "task", "repo_root": str(root / "artifacts/benchmarks/asi"), "timeout": 1200})
            manager = adapter.task_env_manager
            assert manager._is_cache_hit(manager.cache_root / manager.compute_cache_key(metadata))
            task_env = manager.ensure_env(metadata)
            instance = TaskInstance(task_id="synthetic-v2", instance_id=name, task_dir=run,
                workspace_dir=workspace, reference_dir=run / "unmounted-reference", prompt_level=PromptLevel.B3,
                parameters={}, metadata=metadata, effective_timeout_seconds=4 if mode == "deadline" else 120)
            original = httpx.Client.post
            injected = []
            def post(client, url, **kwargs):
                if mode == "safe_connect_retry" and url.endswith("/v1/chat/completions") and not injected:
                    injected.append(True)
                    raise httpx.ConnectError("synthetic connect failed before sending")
                return original(client, url, **kwargs)
            started = time.monotonic()
            with patch("httpx.Client.post", post):
                output = adapter.solve(instance)
            elapsed = time.monotonic() - started
            generation_requests = [r for r in server.requests if r["path"] == "/v1/chat/completions"]
            audit = json.loads((run / "audit" / (instance.run_key + ".request.json")).read_text())
            case = {"name": name, "mode": mode, "seconds": round(elapsed, 3), "status": output.status.value,
                "execution_count": adapter.execution_count, "generation_requests": len(generation_requests)}
            (workspace / "stdout.log").write_text(output.raw_stdout or "")
            (workspace / "stderr.log").write_text(output.raw_stderr or "")
            (workspace / "native_log.json").write_text(output.raw_model_output or "")
            if mode == "overflow":
                passed = output.status.value == "failed" and not generation_requests and adapter.execution_count == 0
            elif mode == "ambiguous":
                passed = output.status.value == "failed" and len(generation_requests) == 1 and adapter.execution_count == 0
            elif mode == "deadline":
                heartbeat = workspace / "heartbeat"
                previous = heartbeat.read_text() if heartbeat.exists() else None
                time.sleep(.3)
                stopped = previous is not None and previous == heartbeat.read_text()
                namespace = (workspace / "pid_namespace").read_text() if (workspace / "pid_namespace").exists() else None
                alive = []
                for path in Path("/proc").glob("[0-9]*/ns/pid"):
                    try:
                        if namespace and os.readlink(path) == namespace:
                            alive.append(str(path))
                    except OSError:
                        pass
                case.update(heartbeat_stopped=stopped, remaining_namespace_processes=alive)
                passed = output.status.value == "failed" and 3.8 <= elapsed <= 7 and stopped and not alive
            else:
                report = json.loads((workspace / "science.json").read_text()) if (workspace / "science.json").exists() else {}
                limits_path = run / "audit" / (instance.run_key + ".limits.json")
                limits = json.loads(limits_path.read_text()) if limits_path.exists() else {}
                case.update(report=report, limits={k: limits.get(k) for k in ("memory_max", "memory_swap_max", "allowed_cpus", "sched_setaffinity")})
                passed = (output.status.value == "completed" and len(generation_requests) == 1 and adapter.execution_count == 1
                    and report.get("prefix") == str(task_env.env_dir) and len(report.get("affinity", [])) == 4
                    and limits.get("memory_max") == 8 * 1024**3 and limits.get("memory_swap_max") == 0
                    and output.data_files == ["science.json"])
                if mode == "safe_connect_retry":
                    passed = passed and len([e for e in audit["events"] if e["event"] == "generation_started"]) == 2
                if mode == "length":
                    response = json.loads((run / "audit" / (instance.run_key + ".response.json")).read_text())
                    passed = passed and response["choices"][0]["finish_reason"] == "length"
                    passed = passed and response["choices"][0]["message"]["content"] == "```python\n" + program + "\n```"
            for request in generation_requests:
                body = request["body"]
                passed = passed and body["max_tokens"] == 8192 and body["seed"] == 0 and "tools" not in body
                passed = passed and body["chat_template_kwargs"] == {"enable_thinking": False, "preserve_thinking": False}
            case["passed"] = bool(passed)
            if not passed:
                case["failure_log"] = output.log
            cases.append(case)
        # Exercise native per-condition result persistence and the start journal.
        # A completed failure and an ambiguous interrupted attempt both remain
        # in the result denominator without a fresh model answer.
        native_output = run / "native-run"
        instances_dir = run / "synthetic-instances"
        input_dir = instances_dir / "synthetic-v2__seed31415"
        input_dir.mkdir(parents=True)
        (input_dir / "data").mkdir()
        for level in ("b1", "b2", "b3", "b4"):
            (input_dir / f"prompt_{level}.md").write_text("Write a self-authored synthetic Python acceptance program.\n")
        adapter = BaselineDirectLLM(endpoint=f"http://127.0.0.1:{server.server_port}", key_file=key,
            protocol={}, ngspice_root=root / "artifacts/tools/ngspice", audit_dir=native_output / "audit")
        config = RunConfig(agent=adapter, instances_dir=str(instances_dir), sandbox="task", score=False,
            analyze=False, retries=1, timeout=1200, output_dir=str(native_output),
            tasks_dir=str(root / "artifacts/benchmarks/asi/tasks"))
        orchestrator = BenchmarkOrchestrator(config)
        task = dict(metadata, id="synthetic-v2", _task_dir=run)
        server.requests, server.prompt_tokens, server.delay, server.disconnect, server.finish_reason = [], 123, 0, False, "stop"
        server.program = 'from pathlib import Path\nPath("science.json").write_text("self-authored success")\n'
        run_condition(orchestrator, adapter, task, "b1", native_output)
        requests_before = len(server.requests)
        skipped = not run_condition(orchestrator, adapter, task, "b1", native_output)
        instance = orchestrator._load_pregenerated_instances(task, PromptLevel.B2, effective_timeout_seconds=1200)[0]
        (instance.workspace_dir / "science.json").write_text("preserved partial output")
        write_json(native_output / "audit" / (instance.run_key + ".started.json"), {
            "condition": instance.run_key, "workspace": str(instance.workspace_dir), "parameters": {}})
        run_condition(orchestrator, adapter, task, "b2", native_output)
        interrupted = json.loads((native_output / "synthetic-v2/synthetic-v2__seed31415__b2.json").read_text())
        journal_passed = (skipped and len(server.requests) == requests_before
            and (instance.workspace_dir / "science.json").read_text() == "preserved partial output"
            and interrupted["status"] == "failed"
            and interrupted["agent_output"]["error_message"] == "interrupted_attempt")
        server.disconnect = True
        run_condition(orchestrator, adapter, task, "b3", native_output)
        requests_before = len(server.requests)
        failed_skipped = not run_condition(orchestrator, adapter, task, "b3", native_output)
        failed_result = json.loads((native_output / "synthetic-v2/synthetic-v2__seed31415__b3.json").read_text())
        journal_passed = journal_passed and failed_skipped and len(server.requests) == requests_before and failed_result["status"] == "failed"
        cases.append({"name": "native-result-journal-resume", "passed": bool(journal_passed),
            "completed_failure_never_regenerated": bool(failed_skipped),
            "interrupted_attempt_never_regenerated": interrupted["status"] == "failed",
            "interrupted_workspace_preserved": (instance.workspace_dir / "science.json").read_text() == "preserved partial output"})
        # Run eight real worker processes concurrently through the production
        # condition_worker function, using only self-authored inputs.
        fake_project = run / "parallel-project"
        (fake_project / "artifacts/benchmarks").mkdir(parents=True)
        (fake_project / "artifacts/tools").mkdir()
        (fake_project / "artifacts/asi/instances_seed31415").mkdir(parents=True)
        (fake_project / "artifacts/benchmarks/asi").symlink_to(root / "artifacts/benchmarks/asi", target_is_directory=True)
        (fake_project / "artifacts/tools/ngspice").symlink_to(root / "artifacts/tools/ngspice", target_is_directory=True)
        parallel_output = run / "parallel-run"
        synthetic_tasks = []
        for index in range(8):
            identifier = f"synthetic-parallel-{index}"
            task_input = fake_project / "artifacts/asi/instances_seed31415" / (identifier + "__seed31415")
            task_input.mkdir()
            (task_input / "prompt_b1.md").write_text("Write the self-authored CPU affinity acceptance program.\n")
            synthetic_tasks.append(dict(metadata, id=identifier, _task_dir=run))
        server.requests, server.prompt_tokens, server.delay, server.disconnect = [], 123, 0, False
        server.generation_barrier = threading.Barrier(8)
        server.program = '''import json, os, pathlib, subprocess, sys, time
affinity = sorted(os.sched_getaffinity(0))
assert len(affinity) == 4
try:
    os.sched_setaffinity(0, range(4096))
    raise AssertionError("CPU set widened")
except PermissionError:
    pass
child = json.loads(subprocess.check_output([sys.executable, "-c", "import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))"], text=True))
assert child == affinity
pathlib.Path("started").write_text("synthetic parallel program started")
time.sleep(5)
pathlib.Path("science.json").write_text(json.dumps({"affinity": affinity, "child_affinity": child}))
'''
        monitor_stop = threading.Event()
        peak_scopes = [0]
        def monitor():
            while not monitor_stop.is_set():
                count = 0
                for receipt in (parallel_output / "audit").glob("*.limits.json"):
                    try:
                        limits = json.loads(receipt.read_text())
                        if Path(limits["cgroup"]).exists():
                            count += 1
                    except (OSError, ValueError):
                        pass
                peak_scopes[0] = max(peak_scopes[0], count)
                monitor_stop.wait(.02)
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        context = multiprocessing.get_context("spawn")
        cpu_queue = context.Queue()
        cpu_sets = [sorted(os.sched_getaffinity(0))[i * 4:(i + 1) * 4] for i in range(8)]
        for cpu_set in cpu_sets:
            cpu_queue.put(cpu_set)
        try:
            with ProcessPoolExecutor(max_workers=8, mp_context=context, initializer=worker_init,
                                    initargs=(cpu_queue,)) as pool:
                futures = [pool.submit(condition_worker, str(fake_project), f"http://127.0.0.1:{server.server_port}",
                    str(key), {}, str(parallel_output), task, "b1") for task in synthetic_tasks]
                keys = [future.result() for future in futures]
        finally:
            monitor_stop.set()
            monitor_thread.join()
            server.generation_barrier = None
        observed_cpu_sets = []
        statuses = []
        for task, condition_key in zip(synthetic_tasks, keys):
            result = json.loads((parallel_output / task["id"] / (condition_key + ".json")).read_text())
            statuses.append(result["status"])
            receipt = json.loads((parallel_output / "audit" / (condition_key + ".limits.json")).read_text())
            observed_cpu_sets.append(receipt["allowed_cpus"])
        parallel_passed = (statuses == ["completed"] * 8 and peak_scopes[0] == 8
            and len(set(tuple(group) for group in observed_cpu_sets)) == 8
            and set(cpu for group in observed_cpu_sets for cpu in group) == set(cpu for group in cpu_sets for cpu in group)
            and len([r for r in server.requests if r["path"] == "/v1/chat/completions"]) == 8)
        cases.append({"name": "eight-process-production-worker-concurrency", "passed": bool(parallel_passed),
            "worker_count": 8, "peak_live_memory_scopes": peak_scopes[0], "observed_cpu_sets": observed_cpu_sets,
            "statuses": statuses, "generation_requests": len([r for r in server.requests if r["path"] == "/v1/chat/completions"])})
        summary = {"passed": all(case["passed"] for case in cases), "run_dir": str(run), "cases": cases,
            "completion_endpoint": "local self-authored HTTP stub", "guard_count_source": "synthetic stub; real /tokenize acceptance remains required",
            "benchmark_conditions_executed": 0, "judge_calls": 0, "real_model_calls": 0}
        write_json(run / "summary.json", summary)
        print(json.dumps(summary, indent=2))
        if not summary["passed"]:
            raise SystemExit(1)
    finally:
        server.shutdown()
        server.server_close()
        os.environ.pop("ASI_SYNTHETIC_SECRET", None)


if __name__ == "__main__":
    main()
