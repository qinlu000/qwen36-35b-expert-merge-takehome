#!/usr/bin/env python3
"""Inventory verified native task packages and extract selected val tasks, without execution."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tarfile
import tomllib

from candidate_selection import text_hash


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    envroot = base / "environments"
    out = base / "val_native_tasks"
    out.mkdir(parents=True, exist_ok=True)
    targets = {x["task_id"]: x for x in map(json.loads, (base / "proportional_candidates/val_tasks.provisional.jsonl").open())}
    metadata = {x["task_id"]: x for x in map(json.loads, (base / "environment_metadata.jsonl").open())}
    inventories, extraction_errors = {}, []
    for receipt_path in sorted((envroot / "download_receipts").glob("*.json")):
        receipt = json.load(receipt_path.open())
        assert receipt["verified_lfs"] and receipt["sha256"] == receipt["expected_sha256"]
        archive = Path(receipt["path"])
        inventory_path = envroot / (archive.name + ".inventory.json")
        if inventory_path.exists():
            inventories[archive.name] = json.load(inventory_path.open())
            extraction_errors.extend(inventories[archive.name].get("extraction_errors", []))
            continue
        tasks = defaultdict(lambda: {"files": [], "compose": False})
        errors_before = len(extraction_errors)
        with tarfile.open(archive, "r|gz") as stream:
            for member in stream:
                task_id, _, relative = member.name.partition("/")
                if not relative: continue
                task = tasks[task_id]
                task["files"].append(relative)
                task["compose"] |= relative in ("environment/docker-compose.yaml", "environment/docker-compose.yml")
                # data filter prevents an untrusted archive escaping the dedicated output tree.
                if task_id in targets:
                    try:
                        stream.extract(member, path=out, filter="data")
                    except tarfile.FilterError as error:
                        extraction_errors.append({"task_id": task_id, "member": member.name,
                                                  "reason": type(error).__name__})
        result = {"archive": archive.name, "archive_sha256": receipt["sha256"], "tasks": dict(tasks),
                  "extraction_errors": extraction_errors[errors_before:]}
        inventory_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        inventories[archive.name] = result
        print(json.dumps({"archive_inventoried": archive.name, "tasks": len(tasks)}), flush=True)
    locations = {}
    for archive, inventory in inventories.items():
        for task_id, details in inventory["tasks"].items():
            assert task_id not in locations
            locations[task_id] = (archive, details)
    val_rows = []
    for task_id, selection in targets.items():
        path = out / task_id
        entry = {"task_id": task_id, "category": selection["category"], "native_task_path": str(path),
                 "source_archive": locations[task_id][0] if task_id in locations else None,
                 "full_source_package_extracted": False, "native_runtime_validated": False,
                 "reference_or_verifier_executed": False}
        required = ("instruction.md", "task.toml", "environment/Dockerfile", "solution/solve.sh", "tests/test.sh")
        missing = [name for name in required if not (path / name).is_file()]
        entry["missing_required_files"] = missing
        if not missing:
            config = tomllib.loads((path / "task.toml").read_text())
            entry.update(environment=config.get("environment"), agent=config.get("agent"), verifier=config.get("verifier"),
                         compose=locations[task_id][1]["compose"],
                         instruction_matches_index=text_hash((path / "instruction.md").read_text()) == text_hash(metadata[task_id]["instruction"]))
            entry["full_source_package_extracted"] = entry["instruction_matches_index"] and not any(x["task_id"] == task_id for x in extraction_errors)
            entry["singularity_prebuilt_image_present"] = bool(config.get("environment", {}).get("docker_image"))
        val_rows.append(entry)
    (base / "val_environment_manifest.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in val_rows))
    extracted = [x for x in val_rows if x["full_source_package_extracted"]]
    summary = {"archives_inventoried": len(inventories), "all_native_tasks_inventoried": len(locations),
               "val_selected": len(targets), "val_full_source_package_extracted": len(extracted),
               "val_archive_not_downloaded_yet": [x["task_id"] for x in val_rows if not x["source_archive"]],
               "val_compose_tasks": sum(x["compose"] for x in extracted),
               "val_prebuilt_image_configured": sum(x["singularity_prebuilt_image_present"] for x in extracted),
               "val_environment_cpus": dict(Counter(str(x["environment"].get("cpus")) for x in extracted)),
               "val_environment_memory_mb": dict(Counter(str(x["environment"].get("memory_mb")) for x in extracted)),
               "val_original_agent_timeout_sec": dict(Counter(str(x["agent"].get("timeout_sec")) for x in extracted)),
               "archive_extraction_errors": extraction_errors,
               "native_runtime_validated_tasks": 0, "executable_val_ready": False,
               "note": "Native source files only; no Dockerfile RUN, reference, verifier or trajectory command executed. Original configs retained; build/Compose/permission/runtime acceptance remains required."}
    (base / "val_environment_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
