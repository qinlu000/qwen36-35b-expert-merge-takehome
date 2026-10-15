#!/usr/bin/env python3
"""Five frozen native Harbor jobs; completed trials resume without regeneration."""
import argparse
import asyncio
import hashlib
from importlib import metadata
import inspect
import json
from pathlib import Path
import shutil
import tomllib

from harbor.agents.terminus_2 import terminus_2
from harbor.job import Job
from harbor.models.job.config import JobConfig
from harbor.models.trial.result import TrialResult
from harbor.models.task.task import Task


def write_json(path, obj):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, indent=2) + "\n")
    temp.replace(path)


def config_for(args, seed):
    environment = json.loads(args.environment_config.read_text())
    environment.update(override_cpus=4, override_memory_mb=8192, override_gpus=0,
                       cpu_enforcement_policy="limit", memory_enforcement_policy="limit")
    return JobConfig.model_validate({
        "job_name": f"terminal-base-v2-seed{seed}", "jobs_dir": str(args.output),
        "n_attempts": 1, "n_concurrent_trials": args.concurrency,
        "retry": {"max_retries": 0}, "environment": environment,
        "agents": [{"import_path": "terminal_baseline_v2:TerminalBaselineV2",
                    "model_name": args.model, "override_timeout_sec": 1800,
                    "kwargs": {
                        "api_base": args.endpoint, "api_key_path": str(args.api_key_path.resolve()),
                        "seed": seed, "parser_name": "json", "temperature": 1,
                        "enable_summarize": True, "proactive_summarization_threshold": 32768,
                        "interleaved_thinking": False, "use_responses_api": False,
                        "store_all_messages": True,
                        "model_info": {"max_input_tokens": 65536, "max_output_tokens": 8192,
                                       "input_cost_per_token": 0, "output_cost_per_token": 0},
                    }}],
        "datasets": [{"path": str((args.output / "tasks").resolve())}],
    })


def stage_network_metadata(args, task_ids):
    # The 89 upstream task files have no agent phase network setting. Keep
    # every task file verbatim, and add only the selected solver network phase
    # to copied metadata so Harbor itself switches public -> deny -> public.
    receipts = {}
    for name in task_ids:
        source = (args.tasks / name).resolve()
        stage = args.output / "tasks" / name
        stage.mkdir(parents=True, exist_ok=True)
        original = (source / "task.toml").read_text()
        metadata_obj = tomllib.loads(original)
        if metadata_obj["agent"].get("network_mode") is not None:
            raise ValueError("upstream agent network policy changed: " + name)
        overlay = original.replace("[agent]", '[agent]\nnetwork_mode = "no-network"', 1)
        if tomllib.loads(overlay)["agent"]["network_mode"] != "no-network":
            raise ValueError("failed to apply agent network metadata: " + name)
        target = stage / "task.toml"
        if target.exists() and target.read_text() != overlay:
            raise ValueError("cannot change frozen metadata overlay: " + name)
        target.write_text(overlay)
        for child in source.iterdir():
            if child.name != "task.toml" and not (stage / child.name).exists():
                if child.is_dir():
                    shutil.copytree(child, stage / child.name)
                else:
                    shutil.copy2(child, stage / child.name)
        if not Task.is_valid_dir(stage):
            raise ValueError("native Harbor rejects staged task layout: " + name)
        receipts[name] = {"original_task_toml_sha256": hashlib.sha256(original.encode()).hexdigest(),
                          "solver_network_overlay_sha256": hashlib.sha256(overlay.encode()).hexdigest()}
    write_json(args.output / "network_metadata.json", receipts)


def preserve_incomplete(job_dir):
    # Harbor's native resume deletes directories with no result.json. Stop here
    # instead so an interrupted formal attempt is retained for infrastructure audit.
    if not job_dir.exists():
        return
    for trial in job_dir.iterdir():
        if not trial.is_dir():
            continue
        result = trial / "result.json"
        if not result.exists():
            raise RuntimeError(f"incomplete trial retained; infrastructure audit required: {trial}")
        TrialResult.model_validate_json(result.read_text())


def aggregate(args, task_ids):
    seeds = []
    for seed in range(5):
        results = {}
        job_dir = args.output / f"terminal-base-v2-seed{seed}"
        for path in job_dir.glob("*/result.json"):
            result = json.loads(path.read_text())
            task = result["task_name"]
            if task in results:
                raise ValueError(f"duplicate result: seed{seed}/{task}")
            results[task] = result
        if set(results) - set(task_ids):
            raise ValueError("unexpected task result")
        successful = 0
        failures = []
        exceptions = []
        policy_prompt_tokens = 0
        policy_completion_tokens = 0
        requests_without_response = 0
        for path in job_dir.glob("*/agent/v2_requests/*.json"):
            request = json.loads(path.read_text())
            response = request.get("response")
            if response:
                policy_prompt_tokens += response["usage"]["prompt_tokens"]
                policy_completion_tokens += response["usage"]["completion_tokens"]
            elif any(a["path"] == "/v1/chat/completions" for a in request["http_attempts"]):
                requests_without_response += 1
        for task in task_ids:
            result = results.get(task)
            rewards = (result or {}).get("verifier_result") or {}
            reward = (rewards.get("rewards") or {}).get("reward")
            if reward == 1:
                successful += 1
            if result and result.get("exception_info"):
                exceptions.append({"task_id": task, "exception": result["exception_info"]})
            if result is None or reward not in (0, 1):
                failures.append(task)
        seeds.append({"seed": seed, "expected": 89, "saved": len(results),
                      "successful": successful, "unresolved": failures, "exceptions": exceptions,
                      "raw_policy_prompt_tokens": policy_prompt_tokens,
                      "raw_policy_completion_tokens": policy_completion_tokens,
                      "policy_requests_without_response": requests_without_response,
                      "complete_score_percent": 100 * successful / 89 if not failures else None,
                      "conservative_success_percent": 100 * successful / 89})
    scores = [s["complete_score_percent"] for s in seeds]
    import statistics
    write_json(args.output / "coverage.json", {
        "protocol_id": "apex-eval-v2-unified64k8k", "expected_trials": 445,
        "task_ids": task_ids, "seeds": seeds,
        "primary_mean_percent": statistics.mean(scores) if all(s is not None for s in scores) else None,
        "sample_sd_percent": statistics.stdev(scores) if all(s is not None for s in scores) else None,
        "report_label": "Terminal-Bench2 / full89x5 / resource constrained64K-8K / 30min-4CPU-8GiB",
    })


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="apex-qwen")
    parser.add_argument("--api-key-path", type=Path, required=True)
    parser.add_argument("--environment-config", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, default=root / "artifacts/benchmarks/terminal-bench-2-registered")
    parser.add_argument("--output", type=Path, default=root / "artifacts/results/base-terminal-v2")
    parser.add_argument("--concurrency", type=int, default=8, choices=range(1, 9))
    parser.add_argument("--acceptance-receipt", type=Path)
    parser.add_argument("--config-only", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    protocol = json.loads((root / "configs/eval/protocol_v2_unified64k8k.json").read_text())
    manifest = json.loads((root / "analysis/source_snapshots/protocol/terminal_task_ids.json").read_text())
    task_ids = manifest["task_ids"]
    actual = sorted(p.name for p in args.tasks.iterdir() if (p / "task.toml").is_file())
    if sorted(task_ids) != actual or len(actual) != 89:
        raise ValueError("registered task set differs from full frozen 89 manifest")
    if metadata.version("harbor") != "0.24.0":
        raise ValueError("wrong Harbor version")
    source_dir = Path(inspect.getfile(terminus_2)).parent
    expected = protocol["prompt_and_source_fingerprints"]
    for rel, key in [("terminus_2.py", "terminus_agent_sha256"),
                     ("terminus_json_plain_parser.py", "terminus_parser_sha256"),
                     ("templates/terminus-json-plain.txt", "terminus_json_prompt_sha256")]:
        if hashlib.sha256((source_dir / rel).read_bytes()).hexdigest() != expected[key]:
            raise ValueError("pinned native Terminus source changed: " + rel)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        aggregate(args, task_ids)
        return
    stage_network_metadata(args, task_ids)
    for seed in range(5):
        config = config_for(args, seed)
        config_path = args.output / f"seed{seed}.json"
        serialized = json.loads(config.model_dump_json(exclude_defaults=True))
        if config_path.exists() and json.loads(config_path.read_text()) != serialized:
            raise ValueError("cannot overwrite frozen seed config")
        write_json(config_path, serialized)
    aggregate(args, task_ids)
    if args.config_only:
        print("five 89-task configs written; no model/container calls")
        return
    receipt = json.loads(args.acceptance_receipt.read_text()) if args.acceptance_receipt else {}
    if not all(receipt.get(key) is True for key in
               ("native_terminus", "exact_token_guard", "cpu_memory_network", "endpoint_cancellation")):
        raise ValueError("formal run requires completed native/resource/token/cancellation acceptance")
    for seed in range(5):
        config = config_for(args, seed)
        preserve_incomplete(args.output / config.job_name)
        job = await Job.create(config)
        try:
            await job.run()
        finally:
            aggregate(args, task_ids)


if __name__ == "__main__":
    asyncio.run(main())
