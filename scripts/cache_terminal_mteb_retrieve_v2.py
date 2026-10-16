#!/usr/bin/env python3
"""Download the exact mteb-retrieve verifier package set without executing tests."""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess

from freeze_terminal_verifier_cache_v2 import export, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    out = root / "artifacts/tools/terminal_verifier_offline_20261016"
    work = out / "mteb-retrieve-retry1"
    work.mkdir(exist_ok=True)
    lock = (work / "cache.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    uv = root / "artifacts/cache/terminal-v2-native/uv-wheel/bin/uv"
    python = next((root / "artifacts/cache/terminal-v2-native/python").glob("*/bin/python3.13"))
    requirements = ["pytest==8.4.1", "mteb==1.36.8", "pytest-json-ctrf==0.3.5"]
    target = work / "packages"
    cache = out / "uv-cache"
    env = dict(os.environ, UV_CACHE_DIR=str(cache), UV_HTTP_TIMEOUT="180",
               UV_CONCURRENT_BUILDS="1", UV_CONCURRENT_DOWNLOADS="4",
               UV_CONCURRENT_INSTALLS="2", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    command = [str(uv), "pip", "install", "--python", str(python), "--target", str(target),
               "--default-index", "https://pypi.org/simple", *requirements]
    record = {"task": "mteb-retrieve", "pid": os.getpid(), "python": str(python),
              "requirements": requirements, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "downloading", "ready": False, "tests_or_model_calls": 0,
              "official_test_sh_modified": False, "uv_cache_dir": str(cache)}
    save(work / "receipt.json", record)
    with (work / "download.log").open("a") as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=log)
    record.update(returncode=result.returncode, finished_at_utc=datetime.now(timezone.utc).isoformat())
    if result.returncode == 0:
        packages = {dist.metadata["Name"]: dist.version for dist in
                    importlib.metadata.distributions(path=[str(target)])}
        frozen = out / "group-caches/mteb-retrieve-retry1"
        missing = export(cache, frozen, packages)
        record.update(status="ready" if not missing else "missing_cache_entries", ready=not missing,
                      resolved_packages=packages, missing_cache_entries=missing,
                      uv_cache_dir=str(frozen), frozen_no_further_writes=True)
        save(frozen / "snapshot_receipt.json", record)
        if not missing:
            mapping = json.loads((out / "task_cache_map.json").read_text())
            mapping["mteb-retrieve"] = {key: record[key] for key in
                ("python", "uv_cache_dir", "ready", "missing_cache_entries")}
            mapping["mteb-retrieve"]["group"] = "mteb-retrieve-retry1"
            save(out / "task_cache_map.json", mapping)
    else:
        record["status"] = "download_failed"
    save(work / "receipt.json", record)
    print(json.dumps({key: record.get(key) for key in
          ("task", "status", "ready", "returncode", "uv_cache_dir", "finished_at_utc")}), flush=True)


if __name__ == "__main__":
    main()
