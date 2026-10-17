#!/usr/bin/env python3
"""Extract fixed SWE SIF images for hosts without squashfuse."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import shutil
import subprocess


def image_names(task_root, digest_manifest):
    wanted = set()
    for task in Path(task_root).glob("*/task.toml"):
        match = re.search(r'docker_image\s*=\s*"([^"]+)"', task.read_text())
        if match:
            wanted.add(match.group(1))
    rows = {row["image"]: row for row in json.loads(Path(digest_manifest).read_text())}
    return [(rows[image].get("linux_amd64_manifest_digest") or
             rows[image]["digest"]).split(":", 1)[1] for image in sorted(wanted)]


def extract(digest, sif_dir, cache_dir, work_dir):
    target = Path(cache_dir) / f"sha256-{digest}"
    marker = target / ".apex_extract_complete"
    if marker.is_file() and ((target / "bin/bash").exists() or
                             (target / "usr/bin/bash").exists()):
        return digest, "cached"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    sqfs = Path(work_dir) / f"sha256-{digest}.sqfs"
    sif = Path(sif_dir) / f"sha256-{digest}.sif"
    if not sif.is_file():
        raise FileNotFoundError(sif)
    with sqfs.open("wb") as output:
        subprocess.run(["singularity", "sif", "dump", "4", str(sif)],
                       check=True, stdout=output)
    subprocess.run(["/usr/sbin/unsquashfs", "-no-xattrs", "-processors", "1",
                    "-d", str(target), str(sqfs)], check=True)
    marker.touch()
    sqfs.unlink(missing_ok=True)
    return digest, "extracted"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", required=True)
    parser.add_argument("--digest-manifest", required=True)
    parser.add_argument("--sif-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    Path(args.work_dir).mkdir(parents=True, exist_ok=True)
    digests = image_names(args.task_root, args.digest_manifest)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(extract, digest, args.sif_dir, args.cache_dir,
                                args.work_dir) for digest in digests]
        for future in as_completed(futures):
            print(*future.result(), flush=True)


if __name__ == "__main__":
    main()
