#!/usr/bin/env python3
"""Metadata-only inventory and self-authored namespace smoke; no ASI tasks run."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import yaml
from ai4sci_bench.runner.linux_ns_sandbox import (
    LinuxNSSandbox,
    check_linux_ns_available,
)


root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
source = root / "artifacts/benchmarks/asi"
receipts = root / "artifacts/preflight/asi"
receipts.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / "analysis/source_snapshots/protocol/asi_task_ids.json").read_text())
tasks = []
for task_id in manifest["task_ids"]:
    subject, name = task_id.split(".", 1)
    path = source / "tasks" / subject / name / "task_meta.yaml"
    data = yaml.safe_load(path.read_text())
    runtime = data.get("runtime", {})
    # Only public dependency/resource declarations are retained.
    tasks.append({
        "task_id": task_id,
        "metadata_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "runtime": {key: runtime[key] for key in ("python", "packages", "image", "dockerfile") if key in runtime},
        "requires_gpu": bool(data.get("difficulty", {}).get("requires_gpu", False)),
    })

runtime_groups = {}
for task in tasks:
    runtime_groups.setdefault(json.dumps(task["runtime"], sort_keys=True), []).append(task["task_id"])
inventory = {
    "code_revision": manifest["code_revision"],
    "dataset_revision": manifest["dataset_revision"],
    "task_count": len(tasks),
    "conditions": len(tasks) * len(manifest["prompt_levels"]),
    "requires_gpu_count": sum(task["requires_gpu"] for task in tasks),
    "unique_runtime_count": len(runtime_groups),
    "tasks": tasks,
    "runtime_groups": [{"runtime": json.loads(runtime), "task_ids": ids} for runtime, ids in runtime_groups.items()],
}
(receipts / "task_runtime_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")

workspace = receipts / "synthetic_namespace_workspace"
workspace.mkdir(exist_ok=True)
sentinel = receipts / "synthetic_outside_workspace.txt"
sentinel.write_text("self-authored-namespace-sentinel\n")
available, reason = check_linux_ns_available()
namespace = {"available": available, "reason": reason, "real_tasks_executed": False}
if available:
    command = [sys.executable, "-c", "from pathlib import Path; import os; "
               f"p=Path({str(sentinel)!r}); "
               "print('outside_workspace_visible=' + str(p.exists())); "
               "print('home_is_workspace=' + str(Path.home() == Path.cwd())); "
               "Path('synthetic_artifact.txt').write_text('namespace-smoke-only\\n')"]
    success, log, stdout, stderr = LinuxNSSandbox().run_command(
        command=command, cwd=workspace, timeout=15,
    )
    namespace.update(success=success, log=log, stdout=stdout, stderr=stderr)
(receipts / "linux_ns_smoke.json").write_text(json.dumps(namespace, indent=2) + "\n")
print(json.dumps({
    "python": sys.version.split()[0],
    "asibench": importlib.metadata.version("asibench"),
    "task_count": len(tasks),
    "conditions": inventory["conditions"],
    "unique_runtime_count": len(runtime_groups),
    "requires_gpu_count": inventory["requires_gpu_count"],
    "linux_ns": namespace,
}, indent=2))
