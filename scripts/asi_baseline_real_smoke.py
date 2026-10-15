#!/usr/bin/env python3
"""Native ASI direct_llm + real fixed Base endpoint on one self-authored task."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from ai4sci_bench.core.types import TaskInstance, PromptLevel
from run_asi_baseline_v2 import BaselineDirectLLM, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    run = Path(tempfile.mkdtemp(prefix="baseline-v2-real-", dir=root / "artifacts/preflight/asi"))
    workspace = run / "workspace"
    workspace.mkdir()
    (workspace / "data").mkdir()
    (workspace / "data/input.json").write_text(json.dumps({"matrix": [[1, 2], [3, 4]],
        "coefficients": [[3, 1], [1, 2]], "rhs": [9, 8]}))
    (workspace / "prompt.md").write_text(
        "This is a self-authored scientific runtime acceptance task, not a benchmark problem.\n"
        "Write one complete Python program. The current working directory is /workspace. "
        "The input path is exactly 'data/input.json' (use that relative path). The JSON has "
        "three keys: matrix=[[1,2],[3,4]], coefficients=[[3,1],[1,2]], rhs=[9,8]. "
        "Read that file. Using NumPy compute np.array(data['matrix']) @ np.array(data['matrix']), "
        "and np.linalg.solve(np.array(data['coefficients']), np.array(data['rhs'])). "
        "Save result.json with keys "
        "matrix_product and solution, both JSON lists. Use matplotlib with the Agg backend to save "
        "a line plot of the solution in plot.png. Do not install packages or access the network.\n")
    groups = json.loads((root / "configs/asi/task_requirements.json").read_text())["runtime_groups"]
    runtime = next(g["runtime"] for g in groups if g["group"] == 24)
    metadata = {"_runtime_python": runtime.get("python"), "_runtime_packages": runtime.get("packages", []),
        "output": {"files": [{"name": "simulation.py", "type": "code"},
            {"name": "result.json", "type": "data"}, {"name": "plot.png", "type": "data"}]}}
    protocol = json.loads((root / "configs/eval/protocol_v2_unified64k8k.json").read_text())
    adapter = BaselineDirectLLM(endpoint=args.endpoint, key_file=args.key_file, protocol=protocol,
        ngspice_root=root / "artifacts/tools/ngspice", audit_dir=run / "audit")
    adapter.setup({"sandbox": "task", "repo_root": str(root / "artifacts/benchmarks/asi"), "timeout": 1200})
    manager = adapter.task_env_manager
    assert manager._is_cache_hit(manager.cache_root / manager.compute_cache_key(metadata))
    instance = TaskInstance(task_id="synthetic-real-base", instance_id="synthetic-real-base", task_dir=run,
        workspace_dir=workspace, reference_dir=run / "unmounted-reference", prompt_level=PromptLevel.B3,
        parameters={}, metadata=metadata, effective_timeout_seconds=1200)
    started = time.monotonic()
    output = adapter.solve(instance)
    elapsed = time.monotonic() - started
    (run / "native_log.json").write_text(output.raw_model_output or "")
    (run / "stdout.log").write_text(output.raw_stdout or "")
    (run / "stderr.log").write_text(output.raw_stderr or "")
    audit = json.loads((run / "audit" / (instance.run_key + ".request.json")).read_text())
    generated = [event for event in audit["events"] if event["event"] == "generation_complete"]
    answer = json.loads((workspace / "result.json").read_text()) if (workspace / "result.json").exists() else {}
    solution = answer.get("solution", [])
    passed = (output.status.value == "completed" and adapter.execution_count == len(generated) == 1
        and answer.get("matrix_product") == [[7, 10], [15, 22]] and len(solution) == 2
        and all(abs(float(actual) - expected) < 1e-6 for actual, expected in zip(solution, [2, 3]))
        and output.code_files == ["simulation.py"] and set(output.data_files) == {"result.json", "plot.png"}
        and (workspace / "plot.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
    summary = {"passed": bool(passed), "run_dir": str(run), "seconds": round(elapsed, 3),
        "status": output.status.value, "real_model_calls": len(generated), "execution_count": adapter.execution_count,
        "benchmark_conditions_executed": 0, "judge_calls": 0,
        "native_prompt_extraction_collector": True, "exact_guard_matches_usage": len(generated) == 1,
        "usage": generated[0]["usage"] if generated else None, "answer": answer,
        "collected_code": output.code_files, "collected_data": output.data_files,
        "events": audit["events"], "limits": json.loads((run / "audit" / (instance.run_key + ".limits.json")).read_text())
            if (run / "audit" / (instance.run_key + ".limits.json")).exists() else None,
        "source_sha256": {name: hashlib.sha256((root / "scripts" / name).read_bytes()).hexdigest()
            for name in ("run_asi_baseline_v2.py", "asi_baseline_limits.py", "asi_baseline_real_smoke.py")}}
    if not passed:
        summary["failure_log"] = output.log
    write_json(run / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
