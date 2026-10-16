#!/usr/bin/env python3
"""Export small per-task uv cache snapshots from completed dependency installs."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import time


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def export(src, dst, packages):
    dst.mkdir(parents=True, exist_ok=True)
    missing = []
    for tag in ("CACHEDIR.TAG", ".gitignore"):
        if (src / tag).is_file():
            shutil.copy2(src / tag, dst / tag)
    for name, version in packages.items():
        name = re.sub(r"[-_.]+", "-", name).lower()
        for path in (src / "simple-v18").rglob(name + ".rkyv"):
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        wheels = list((src / "wheels-v5").rglob(name + "/" + version + "-*"))
        sdists = list((src / "sdists-v9").rglob(name + "/" + version))
        if not wheels and not sdists:
            missing.append(name + "==" + version)
        for path in wheels:
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                archive = path.resolve()
                archive_target = dst / archive.relative_to(src)
                if not archive_target.exists():
                    shutil.copytree(archive, archive_target, copy_function=os.link, symlinks=True)
                if target.is_symlink():
                    target.unlink()
                target.symlink_to(os.path.relpath(archive_target, target.parent))
            elif path.is_file():
                shutil.copy2(path, target)
        for path in sdists:
            target = dst / path.relative_to(src)
            if not target.exists():
                shutil.copytree(path, target, copy_function=shutil.copy2, symlinks=True)
    for link in list(dst.rglob("*")):
        if not link.is_symlink() or not os.path.isabs(os.readlink(link)):
            continue
        original = link.resolve()
        if not original.is_relative_to(src) or not original.exists():
            missing.append("unrelocated:" + str(link.relative_to(dst)))
            continue
        target = dst / original.relative_to(src)
        if not target.exists():
            shutil.copytree(original, target, copy_function=os.link, symlinks=True)
        link.unlink()
        link.symlink_to(os.path.relpath(target, link.parent))
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    exports = out / "group-caches"
    exports.mkdir(exist_ok=True)
    done, mapping = set(), {}
    while True:
        manifest = json.loads((out / "dependency_manifest.json").read_text())
        for group in manifest["groups"]:
            index = group["group"]
            receipt = out / ("group-%02d.json" % index)
            if index in done or not receipt.exists():
                continue
            info = json.loads(receipt.read_text())
            if info["returncode"] != 0:
                done.add(index)
                continue
            packages = {dist.metadata["Name"]: dist.version for dist in
                importlib.metadata.distributions(path=[info["installed_target"]])}
            target = exports / ("group-%02d" % index)
            missing = export(out / "uv-cache", target, packages)
            record = {"group": index, "tasks": info["tasks"], "python": info["python"],
                "uv_cache_dir": str(target), "resolved_packages": packages,
                "missing_cache_entries": missing, "ready": not missing,
                "tests_or_offline_fixture_run": False, "frozen_no_further_writes": True}
            save(target / "snapshot_receipt.json", record)
            for task in info["tasks"]:
                mapping[task] = {key: record[key] for key in
                    ("group", "python", "uv_cache_dir", "ready", "missing_cache_entries")}
            save(out / "task_cache_map.json", mapping)
            done.add(index)
            print(json.dumps({"group": index, "ready": not missing,
                "task_count": len(info["tasks"]), "mapped_tasks": len(mapping)}), flush=True)
        if all(group["status"] != "pending" for group in manifest["groups"]):
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
