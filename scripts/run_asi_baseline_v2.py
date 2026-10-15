#!/usr/bin/env python3
"""Fixed ASI seed31415 produce-only runner, retaining native DirectLLM solve.

Each admitted condition runs in its own independent worker process.
The official system/prompt, code extraction, one execution and output collector
are inherited. No judge is called. Every admitted condition is journaled before
its one attempt; interrupted or failed conditions are never regenerated.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

import httpx
import litellm

from ai4sci_bench.adapters.direct_llm import DirectLLMAdapter
from ai4sci_bench.core.types import AgentOutput, EvalResult, PromptLevel, RunStatus, TaskInstance
from ai4sci_bench.runner.orchestrator import BenchmarkOrchestrator, RunConfig


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


class DeadlineExceeded(TimeoutError):
    pass


@contextmanager
def condition_alarm(seconds):
    def expired(signum, frame):
        raise DeadlineExceeded("ASI shared generation/execution deadline exceeded")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class BaselineDirectLLM(DirectLLMAdapter):
    def __init__(self, *, endpoint, key_file, protocol, ngspice_root, audit_dir, cpu_list=None):
        self.endpoint = endpoint.rstrip("/").removesuffix("/v1")
        self.key = Path(key_file).read_text().strip()
        self.protocol = protocol
        self.ngspice_root = Path(ngspice_root).resolve(strict=True)
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.cpu_list = cpu_list
        self.events = []
        self.execution_count = 0
        self.deadline = None
        super().__init__(model="apex-qwen", api_key=self.key,
                         api_base=self.endpoint + "/v1", api_protocol="openai")

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise DeadlineExceeded("ASI shared deadline exhausted")
        return remaining

    def _completion(self, *, messages, **kwargs):
        """One HTTP layer, no SDK retries; tokenize the exact native messages."""
        template = {"enable_thinking": False, "preserve_thinking": False}
        request = {"model": "apex-qwen", "messages": messages,
            "temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0,
            "presence_penalty": 0, "repetition_penalty": 1, "seed": 0,
            "max_tokens": 8192, "stream": False, "chat_template_kwargs": template}
        with httpx.Client(transport=httpx.HTTPTransport(retries=0), trust_env=False,
                          headers={"Authorization": f"Bearer {self.key}"}) as client:
            tokenized = client.post(self.endpoint + "/tokenize", json={"model": "apex-qwen",
                "messages": messages, "add_generation_prompt": True,
                "chat_template_kwargs": template}, timeout=self.remaining())
            tokenized.raise_for_status()
            prompt_tokens = tokenized.json()["count"]
            self.events.append({"event": "guard", "prompt_tokens": prompt_tokens,
                "request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
                "sampling": {key: value for key, value in request.items() if key not in ("messages",)},
                "remaining_seconds": self.remaining()})
            if prompt_tokens + 8192 > 65536:
                raise ValueError(f"context_budget_exceeded: {prompt_tokens}+8192 >65536")
            for attempt in (1, 2):
                self.events.append({"event": "generation_started", "attempt": attempt,
                    "remaining_seconds": self.remaining(), "at": datetime.now(timezone.utc).isoformat()})
                try:
                    response = client.post(self.endpoint + "/v1/chat/completions",
                                           json=request, timeout=self.remaining())
                except (httpx.ConnectError, httpx.ConnectTimeout) as error:
                    # httpx Connect* are failures establishing the connection;
                    # no application request has been sent on this attempt.
                    self.events.append({"event": "transport_failed_before_send", "attempt": attempt,
                                        "error_class": type(error).__name__})
                    if attempt == 1:
                        continue
                    raise
                except httpx.HTTPError as error:
                    self.events.append({"event": "ambiguous_transport_failure_no_retry",
                        "attempt": attempt, "error_class": type(error).__name__})
                    raise
                self.events.append({"event": "response", "attempt": attempt,
                    "http_status": response.status_code})
                # 429 is deliberately terminal here: this endpoint has not
                # provided evidence that a 429 guarantees no generation.
                response.raise_for_status()
                payload = response.json()
                # Preserve the original returned answer (including length
                # truncation) before parsing/extraction or running any code.
                write_json(self.audit_dir / (self.condition_key + ".response.json"), payload)
                usage = payload.get("usage", {})
                if usage.get("prompt_tokens") != prompt_tokens:
                    raise ValueError("Exact /tokenize guard differs from generation usage")
                self.events.append({"event": "generation_complete", "attempt": attempt,
                    "usage": usage, "finish_reason": payload["choices"][0].get("finish_reason")})
                return litellm.ModelResponse(**payload)

    def solve(self, instance):
        self.deadline = time.monotonic() + instance.effective_timeout_seconds
        self.events = []
        self.execution_count = 0
        self.condition_key = instance.run_key
        try:
            with condition_alarm(instance.effective_timeout_seconds):
                with patch("litellm.completion", self._completion):
                    output = super().solve(instance)
            if self.execution_count > 1:
                raise RuntimeError("ASI direct_llm executed more than once")
            return output
        finally:
            write_json(self.audit_dir / (instance.run_key + ".request.json"), {
                "condition": instance.run_key, "execution_count": self.execution_count,
                "shared_deadline_seconds": instance.effective_timeout_seconds,
                "events": self.events})

    def _execute(self, instance, code_file):
        if not (self.audit_dir / (self.condition_key + ".response.json")).is_file():
            raise RuntimeError("Original response must be persisted before program execution")
        task_env = self._get_task_environment(instance)
        if not task_env.cache_hit:
            raise RuntimeError("Task dependencies must be staged before the solve timer")
        self.execution_count += 1
        unit = "apex-asi-" + uuid.uuid4().hex + ".scope"
        receipt = self.audit_dir / (instance.run_key + ".limits.json")
        helper = Path(__file__).with_name("asi_baseline_limits.py")
        command = ["systemd-run", "--user", "--scope", "--quiet", "--unit", unit,
            "-p", "MemoryMax=8589934592", "-p", "MemorySwapMax=0", "--",
            sys.executable, str(helper), "--workspace", str(instance.workspace_dir),
            "--env-dir", str(task_env.env_dir), "--code", code_file,
            "--ngspice", str(self.ngspice_root), "--receipt", str(receipt)]
        if self.cpu_list is not None:
            command += ["--cpu-list", ",".join(str(n) for n in self.cpu_list)]
        # systemd's user bus is controller-only; generated programs receive the
        # explicit clean environment from asi_bwrap.program_env instead.
        env = {key: os.environ[key] for key in ("HOME", "PATH", "LANG", "XDG_RUNTIME_DIR",
               "DBUS_SESSION_BUS_ADDRESS") if key in os.environ}
        process = subprocess.Popen(command, cwd=instance.workspace_dir, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
            start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=self.remaining())
        except (subprocess.TimeoutExpired, DeadlineExceeded):
            timed_out = True
            subprocess.run(["systemctl", "--user", "kill", "--signal=KILL", unit],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        finally:
            subprocess.run(["systemctl", "--user", "stop", unit], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        if timed_out:
            return False, "Execution timed out within shared ASI deadline", stdout, stderr
        return process.returncode == 0, stdout + "\n" + stderr, stdout, stderr


def run_condition(orchestrator, adapter, task, level, output):
    """Run/save once, or preserve the interrupted attempt without regeneration."""
    key = f"{task['id']}__seed31415__{level}"
    result_path = output / task["id"] / (key + ".json")
    started_path = output / "audit" / (key + ".started.json")
    if result_path.exists():
        json.loads(result_path.read_text())  # Never regenerate failed results.
        return False
    if started_path.exists():
        # Previous request may have generated: preserve a failed
        # denominator entry and the original workspace. Calling the
        # native preparation again would replace its workspace link.
        started = json.loads(started_path.read_text())
        workspace = Path(started["workspace"])
        instance = TaskInstance(task_id=task["id"], instance_id=task["id"] + "__seed31415",
            task_dir=task["_task_dir"], workspace_dir=workspace,
            reference_dir=Path(orchestrator.config.instances_dir) / (task["id"] + "__seed31415") / "reference",
            prompt_level=PromptLevel(level), parameters=started["parameters"], metadata=task,
            effective_timeout_seconds=1200)
        failure = AgentOutput(instance_id=instance.instance_id, output_dir=workspace,
            code_files=[f["name"] for f in task.get("output", {}).get("files", []) if f.get("type") == "code"],
            data_files=adapter._collect_data_files(instance), log="Interrupted previous attempt; no regeneration",
            execution_time_seconds=0, status=RunStatus.FAILED,
            error_message="interrupted_attempt")
        result = EvalResult(instance_id=instance.instance_id, task_id=instance.task_id,
            prompt_level=instance.prompt_level, agent_name=adapter.__class__.__name__,
            parameters=instance.parameters, gate_results=[], gates_passed=False,
            score_results=[], final_score=0, status=RunStatus.FAILED, agent_output=failure)
        orchestrator._save_result(result)
    else:
        instances = orchestrator._load_pregenerated_instances(task, PromptLevel(level),
                                                              effective_timeout_seconds=1200)
        assert len(instances) == 1 and instances[0].run_key == key
        instance = instances[0]
        write_json(started_path, {"condition": key, "started_at": datetime.now(timezone.utc).isoformat(),
            "workspace": str(instance.workspace_dir), "parameters": instance.parameters})
        orchestrator._run_single_instance(instance)
    return True


def worker_init(cpu_queue):
    global WORKER_CPUS
    WORKER_CPUS = cpu_queue.get()


def condition_worker(project, endpoint, key_file, protocol, output, task, level):
    root, output = Path(project), Path(output)
    adapter = BaselineDirectLLM(endpoint=endpoint, key_file=key_file, protocol=protocol,
        ngspice_root=root / "artifacts/tools/ngspice", audit_dir=output / "audit", cpu_list=WORKER_CPUS)
    config = RunConfig(agent=adapter, instances_dir=str(root / "artifacts/asi/instances_seed31415"),
        parallel=1, timeout=1200, sandbox="task", output_dir=str(output), retries=1,
        analyze=False, score=False, tasks_dir=str(root / "artifacts/benchmarks/asi/tasks"))
    orchestrator = BenchmarkOrchestrator(config)
    run_condition(orchestrator, adapter, task, level, output)
    return f"{task['id']}__seed31415__{level}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--parallel", type=int, default=8, choices=range(1, 9))
    parser.add_argument("--cpu-offset", type=int, default=0,
                        help="Reserve distinct groups of four CPUs per worker from this affinity offset")
    args = parser.parse_args()
    root, output = args.project.resolve(), args.output.resolve()
    protocol_path = root / "configs/eval/protocol_v2_unified64k8k.json"
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads((root / protocol["benchmarks"]["asi"]["task_manifest"]).read_text())
    tasks, levels = manifest["task_ids"], manifest["prompt_levels"]
    assert len(tasks) == 60 and levels == ["b1", "b2", "b3", "b4"]
    assert protocol["benchmarks"]["asi"]["agent_timeout_seconds"] == 1200
    source = root / "artifacts/benchmarks/asi"
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == protocol["benchmarks"]["asi"]["code_revision"]
    output.mkdir(parents=True, exist_ok=True)
    adapter = BaselineDirectLLM(endpoint=args.endpoint, key_file=args.key_file, protocol=protocol,
        ngspice_root=root / "artifacts/tools/ngspice", audit_dir=output / "audit")
    config = RunConfig(agent=adapter, tasks=tasks, prompt_levels=levels, seed=31415,
        instances_dir=str(root / "artifacts/asi/instances_seed31415"), parallel=1,
        timeout=1200, sandbox="task", output_dir=str(output), retries=1,
        analyze=False, score=False, tasks_dir=str(source / "tasks"))
    orchestrator = BenchmarkOrchestrator(config)
    loaded = orchestrator._load_tasks(tasks)
    for task in loaded:
        manager = adapter.task_env_manager
        if not manager._is_cache_hit(manager.cache_root / manager.compute_cache_key(task)):
            raise RuntimeError("Missing pre-staged task runtime: " + task["id"])
        if task.get("runtime", {}).get("services"):
            raise RuntimeError("runtime.services needs official lifecycle acceptance")
    expected = [f"{task}__seed31415__{level}" for task in tasks for level in levels]
    available_cpus = sorted(os.sched_getaffinity(0))
    cpu_sets = [available_cpus[args.cpu_offset + 4 * index:args.cpu_offset + 4 * (index + 1)]
                for index in range(args.parallel)]
    if args.cpu_offset < 0 or any(len(group) != 4 for group in cpu_sets):
        raise RuntimeError("Not enough available CPUs for the fixed per-worker CPU limits")
    memory_available = next(int(line.split()[1]) * 1024 for line in Path("/proc/meminfo").read_text().splitlines()
                            if line.startswith("MemAvailable:"))
    if memory_available < args.parallel * 8 * 1024**3:
        raise RuntimeError("Available memory cannot support the requested 8GiB worker limits")
    metadata = {"protocol": protocol["protocol_id"], "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "tasks": 60, "conditions": 240, "expected_conditions": expected,
        "endpoint": args.endpoint.rstrip("/"), "model": protocol["model"]["repo_id"],
        "model_revision": protocol["model"]["revision"],
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits_sha256": hashlib.sha256(Path(__file__).with_name("asi_baseline_limits.py").read_bytes()).hexdigest(),
        "source_runtime_lock": "scripts/requirements-asi.lock",
        "source_runtime_lock_sha256": hashlib.sha256((root / "scripts/requirements-asi.lock").read_bytes()).hexdigest(),
        "source_uv_lock_sha256": hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest(),
        "inference_runtime_lock_sha256": protocol["model"]["inference_candidate"]["runtime_lock_sha256"],
        "submission_order": "fixed manifest task order, then b1,b2,b3,b4",
        "mode": "produce_only_unscored", "adapter": "official direct_llm plus v2 transport/resource hooks",
        "parallel": args.parallel, "cpus_per_worker": 4, "cpu_sets": cpu_sets,
        "memory_bytes_per_worker": 8 * 1024**3, "retries_per_condition": 0, "judge_calls": 0}
    metadata_path = output / "asi_v2_run.json"
    if metadata_path.exists() and json.loads(metadata_path.read_text()) != metadata:
        raise RuntimeError("Refuse to resume with changed protocol or scope")
    write_json(metadata_path, metadata)
    if args.prepare_only:
        print(json.dumps({"prepared": True, "conditions": 240, "generation_calls": 0}))
        return
    # The queue is populated in fixed manifest/level order. Only running worker
    # processes admit a condition and start its wall clock; server queuing then
    # shares that same deadline. Each worker owns a disjoint four-CPU set.
    context = multiprocessing.get_context("spawn")
    cpu_queue = context.Queue()
    for group in cpu_sets:
        cpu_queue.put(group)
    with ProcessPoolExecutor(max_workers=args.parallel, mp_context=context,
                            initializer=worker_init, initargs=(cpu_queue,)) as pool:
        futures = [pool.submit(condition_worker, str(root), args.endpoint, str(args.key_file.resolve()),
                    protocol, str(output), task, level) for task in loaded for level in levels]
        for future in as_completed(futures):
            key = future.result()
            completed = sum((output / task_id / (condition + ".json")).is_file()
                            for task_id in tasks for condition in expected if condition.startswith(task_id + "__"))
            write_json(output / "progress.json", {"completed_conditions": completed,
                "expected_conditions": 240, "last_condition": key,
                "updated_at": datetime.now(timezone.utc).isoformat(), "scored": False})
            print(json.dumps({"condition": key, "completed": completed, "expected": 240}), flush=True)


if __name__ == "__main__":
    main()
