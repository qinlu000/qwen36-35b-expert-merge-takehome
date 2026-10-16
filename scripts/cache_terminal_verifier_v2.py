#!/usr/bin/env python3
"""Cache the actual pinned uvx verifier dependencies; never run pytest or a model."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import threading


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.project.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    uv = root / "artifacts/cache/terminal-v2-native/uv-wheel/bin/uv"
    python313 = next((root / "artifacts/cache/terminal-v2-native/python").glob("*/bin/python3.13"))
    env = dict(os.environ, UV_CACHE_DIR=str(out / "uv-cache"),
        UV_PYTHON_INSTALL_DIR=str(out / "python"), UV_HTTP_TIMEOUT="60",
        UV_CONCURRENT_BUILDS="1", UV_CONCURRENT_DOWNLOADS="4", UV_CONCURRENT_INSTALLS="2",
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    tasks = root / "artifacts/results/base-terminal-v2-724242-r2/tasks"
    groups, unparsed = {}, []
    for path in sorted(tasks.glob("*/tests/test.sh")):
        content = path.read_text()
        lines = content.splitlines()
        found = False
        for index, line in enumerate(lines):
            if not line.strip().startswith("uvx"):
                continue
            block = []
            for text in lines[index:]:
                block.append(text)
                if not text.rstrip().endswith("\\"):
                    break
            command = "\n".join(block).replace("\\\n", " ")
            commit = re.search(r"^COMMIT_HASH=['\"]?([^'\"\s]+)", content, re.MULTILINE)
            if commit:
                command = command.replace("${COMMIT_HASH}", commit.group(1))
            tokens = shlex.split(command)
            python, requirements, options = "3.13", [], []
            for number, token in enumerate(tokens):
                if token in ("-p", "--python"):
                    python = tokens[number + 1]
                if token in ("-w", "--with"):
                    requirements.append(tokens[number + 1])
                if token in ("--index", "--index-strategy"):
                    options += [token, tokens[number + 1]]
            key = (python, tuple(sorted(requirements)), tuple(options))
            groups.setdefault(key, {"python": python, "requirements": sorted(requirements),
                "options": options, "tasks": [], "official_command": command})["tasks"].append(path.parent.parent.name)
            found = True
        if not found:
            unparsed.append(path.parent.parent.name)
    jobs = sorted(groups.values(), key=lambda job: (any(
        req.split("==")[0] in ("torch", "mteb", "torchvision") or req.startswith("git+")
        for req in job["requirements"]), -len(job["tasks"])))
    for index, job in enumerate(jobs):
        job.update(group=index, status="pending")
    manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_sh_count": len(list(tasks.glob("*/tests/test.sh"))), "uvx_tasks": sum(len(job["tasks"]) for job in jobs),
        "uv_cache_dir": env["UV_CACHE_DIR"], "groups": jobs,
        "non_uvx_task_ids": unparsed, "not_run": ["pytest", "fixtures", "model", "hash"],
        "original_test_files_modified": False, "note": "Only exact official uvx package sets and indexes; small/common groups first. Tool dependencies are grader-only."}
    save(out / "dependency_manifest.json", manifest)
    python_lock, manifest_lock = threading.Lock(), threading.Lock()

    def install(job):
        target = out / ("group-%02d-py%s" % (job["group"], job["python"].replace(".", "")))
        receipt = out / ("group-%02d.json" % job["group"])
        if receipt.exists() and json.loads(receipt.read_text()).get("returncode") == 0:
            return json.loads(receipt.read_text())
        if job["python"] == "3.13":
            python = python313
        else:
            with python_lock:
                candidates = list((out / "python").glob("*/bin/python" + job["python"]))
                if not candidates:
                    with (out / "python-download.log").open("a") as log:
                        subprocess.run([str(uv), "python", "install", job["python"]], env=env,
                            stdout=log, stderr=log, check=True, timeout=600)
                    candidates = list((out / "python").glob("*/bin/python" + job["python"]))
                python = candidates[0]
        command = [str(uv), "pip", "install", "--python", str(python), "--target", str(target),
            "--default-index", "https://pypi.org/simple", *job["options"], *job["requirements"]]
        with (out / ("group-%02d.log" % job["group"])).open("a") as log:
            try:
                result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=1800)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = "download_timeout"
        value = {"group": job["group"], "tasks": job["tasks"], "requirements": job["requirements"],
            "python": str(python), "command": command, "returncode": code,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(), "tests_run": False,
            "uv_cache_dir": env["UV_CACHE_DIR"], "installed_target": str(target)}
        save(receipt, value)
        return value

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(install, job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = {"returncode": type(error).__name__}
            with manifest_lock:
                job.update(status="cached" if result["returncode"] == 0 else "download_failed",
                           returncode=result["returncode"])
                manifest.update(cached_uvx_tasks=sum(len(row["tasks"]) for row in jobs if row["status"] == "cached"),
                    failed_uvx_tasks=sum(len(row["tasks"]) for row in jobs if row["status"] == "download_failed"),
                    updated_at_utc=datetime.now(timezone.utc).isoformat())
                save(out / "dependency_manifest.json", manifest)
            print(json.dumps({"group": job["group"], "status": job["status"],
                "tasks": len(job["tasks"]), "cached_uvx_tasks": manifest["cached_uvx_tasks"]}), flush=True)


if __name__ == "__main__":
    main()
