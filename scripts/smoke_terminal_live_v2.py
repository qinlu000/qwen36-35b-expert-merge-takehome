#!/usr/bin/env python3
"""One independent native Terminus/Qwen/tmux trial; no benchmark task contents."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from harbor.job import Job
from harbor.models.job.config import JobConfig
from harbor.agents.terminus_2.terminus_json_plain_parser import TerminusJSONPlainParser


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--api-key-path", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--environment-config", type=Path, required=True)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scratch = args.root / "artifacts/preflight/terminal-v2" / ("live-" + stamp)
    task = scratch / "tasks/apex-terminal-v2-synthetic"
    (task / "environment").mkdir(parents=True)
    (task / "tests").mkdir()
    (task / "instruction.md").write_text(
        "This is an independent synthetic harness acceptance check. "
        "Create /tmp/apex-terminal-v2-synthetic.txt containing exactly "
        "APEX_NATIVE_TERM_V2_OK followed by a newline. Read it back. "
        "Then mark the task complete using the specified terminal JSON format.\n")
    (task / "environment/Dockerfile").write_text("FROM ubuntu:24.04\nWORKDIR /tmp\n")
    (task / "task.toml").write_text(
        'version = "1.0"\n[metadata]\ncategory = "synthetic"\n'
        '[agent]\ntimeout_sec = 1800\nnetwork_mode = "no-network"\n'
        '[verifier]\ntimeout_sec = 60\n'
        '[environment]\ncpus = 4\nmemory = "8G"\ngpus = 0\n'
        + 'docker_image = ' + json.dumps(str(args.image.resolve())) + '\n')
    (task / "tests/test.sh").write_text(
        '#!/bin/bash\nmkdir -p /logs/verifier\n'
        'if test "$(cat /tmp/apex-terminal-v2-synthetic.txt 2>/dev/null)" = APEX_NATIVE_TERM_V2_OK; then\n'
        '  echo 1 > /logs/verifier/reward.txt\nelse\n'
        '  echo 0 > /logs/verifier/reward.txt\nfi\n')
    environment = json.loads(args.environment_config.read_text())
    environment.update(override_cpus=4, override_memory_mb=8192, override_gpus=0,
                       cpu_enforcement_policy="limit", memory_enforcement_policy="limit")
    config = JobConfig.model_validate({
        "job_name": "native-live", "jobs_dir": str(scratch), "n_attempts": 1,
        "n_concurrent_trials": 1, "retry": {"max_retries": 0}, "environment": environment,
        "agents": [{"import_path": "terminal_baseline_v2:TerminalBaselineV2",
                    "model_name": "apex-qwen", "override_timeout_sec": 1800,
                    "kwargs": {"api_base": args.endpoint,
                               "api_key_path": str(args.api_key_path.resolve()), "seed": 0,
                               "parser_name": "json", "enable_summarize": True,
                               "proactive_summarization_threshold": 32768,
                               "interleaved_thinking": False, "store_all_messages": True,
                               "model_info": {"max_input_tokens": 65536, "max_output_tokens": 8192,
                                              "input_cost_per_token": 0, "output_cost_per_token": 0}}}],
        "datasets": [{"path": str(task.parent)}],
    })
    (scratch / "config.json").write_text(config.model_dump_json(indent=2))
    report = {"scope": "independent synthetic native Terminus + real Qwen + persistent tmux",
              "scratch": str(scratch), "status": "started"}
    report_path = scratch / "acceptance.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    try:
        job = await Job.create(config)
        await job.run()
        paths = list((scratch / "native-live").glob("*/result.json"))
        if len(paths) != 1:
            raise ValueError("expected one saved native trial")
        result = json.loads(paths[0].read_text())
        report["exception_info"] = result.get("exception_info")
        report["rewards"] = (result.get("verifier_result") or {}).get("rewards")
        requests = sorted(paths[0].parent.glob("agent/v2_requests/*.json"))
        records = [json.loads(p.read_text()) for p in requests]
        report["requests"] = [{"phase": r["phase"], "status": r["status"],
                               "prompt_tokens_exact": r.get("prompt_tokens_exact"),
                               "finish_reason": (r.get("response", {}).get("choices") or [{}])[0].get("finish_reason")}
                              for r in records]
        native_parser = TerminusJSONPlainParser()
        report["task_complete_turns"] = sum(native_parser.parse_response(
            (r.get("response", {}).get("choices") or [{}])[0].get("message", {}).get("content", "")
        ).is_task_complete for r in records)
        if result.get("exception_info") or (report["rewards"] or {}).get("reward") != 1:
            raise ValueError("native synthetic trial failed")
        if len(records) < 2 or report["task_complete_turns"] < 2 or any(r["status"] != "completed" for r in records):
            raise ValueError("native turn/guard acceptance incomplete")
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
