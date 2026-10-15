#!/usr/bin/env python3
"""Install declared task dependencies with the official manager; run no tasks."""

import json
import argparse
import os
from pathlib import Path
import subprocess

from ai4sci_bench.runner.task_env import TaskEnvironmentManager


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--start-group", type=int, default=1)
parser.add_argument("--receipt-name", default="task_env_install.json")
args = parser.parse_args()
root = args.project_root.resolve()
receipts = root / "artifacts/preflight/asi"
inventory = json.loads((receipts / "task_runtime_inventory.json").read_text())
frozen_groups = json.loads((root / "configs/asi/task_requirements.json").read_text())["runtime_groups"]
manager = TaskEnvironmentManager(root / "artifacts/benchmarks/asi")
results = []
for group_index, group in enumerate(inventory["runtime_groups"], 1):
    if group_index < args.start_group:
        continue
    runtime = group["runtime"]
    frozen = frozen_groups[group_index - 1]
    assert frozen["runtime"] == runtime and frozen["task_ids"] == group["task_ids"]
    constraints = receipts / f"task_constraints_{group_index:02d}.txt"
    constraints.write_text("\n".join(frozen["requirements"]) + "\n")
    os.environ["UV_CONSTRAINT"] = str(constraints)
    metadata = {"_runtime_python": runtime.get("python"), "_runtime_packages": runtime.get("packages", [])}
    entry = {"task_ids": group["task_ids"], "runtime": runtime}
    try:
        env = manager.ensure_env(metadata)
        check = subprocess.run(["uv", "pip", "check", "--python", str(env.python_executable)],
                               capture_output=True, text=True, timeout=60)
        frozen = subprocess.run(["uv", "pip", "freeze", "--python", str(env.python_executable)],
                                capture_output=True, text=True, timeout=60)
        (env.env_dir / "requirements.lock.txt").write_text(frozen.stdout)
        entry.update(status="ready" if check.returncode == 0 else "dependency_check_failed",
                     cache_key=env.cache_key, env_dir=str(env.env_dir), python=env.resolved_python_version,
                     dependency_check=check.stdout + check.stderr)
    except Exception as error:
        entry.update(status="install_failed", error=str(error))
    results.append(entry)
    (receipts / args.receipt_name).write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"completed": group_index, "total": len(inventory["runtime_groups"]),
                      "task_ids": group["task_ids"], "status": entry["status"]}), flush=True)

raise SystemExit(any(result["status"] != "ready" for result in results))
