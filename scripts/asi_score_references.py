#!/usr/bin/env python3
"""Prepare pinned public seed31415 gold in a grader-only tree; never change solver inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import httpx
from huggingface_hub import hf_hub_url

from asi_score_transport import write_json


def verify(path, metadata):
    size = path.stat().st_size
    sha256 = hashlib.sha256()
    blob = hashlib.sha1(f"blob {size}\0".encode())
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            sha256.update(chunk); blob.update(chunk)
    actual_sha = sha256.hexdigest()
    if size != metadata.size:
        raise ValueError("Reference size mismatch: " + metadata.rfilename)
    expected = metadata.lfs.sha256 if metadata.lfs else metadata.blob_id
    actual = actual_sha if metadata.lfs else blob.hexdigest()
    if actual != expected:
        raise ValueError("Reference upstream hash mismatch: " + metadata.rfilename)
    return {"path": metadata.rfilename, "size": size, "sha256": actual_sha,
            "upstream_oid": expected, "upstream_object_type": "LFS-SHA256" if metadata.lfs else "Git-blob-SHA1"}


def download_one(item, repo, revision, destination, endpoint):
    target = destination / item.rfilename
    if target.is_file():
        verify(target, item)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".download")
    url = hf_hub_url(repo, item.rfilename, repo_type="dataset", revision=revision, endpoint=endpoint)
    for attempt in range(3):
        try:
            # A separate client per file avoids the shared Hub client's observed
            # ReadError/EBADF during concurrent HEAD requests. Only this process's
            # existing proxy environment is used; no proxy configuration is changed.
            with httpx.Client(follow_redirects=True, timeout=60) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with temporary.open("wb") as stream:
                        for chunk in response.iter_bytes(1024 * 1024):
                            stream.write(chunk)
            verify(temporary, item)
            temporary.replace(target)
            return
        except (httpx.HTTPError, OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(1)


def git_metadata(directory, repo, revision, expected_instances, endpoint):
    bare = directory / "upstream.git"
    if not bare.exists():
        subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "clone", "--bare", "--single-branch",
                        endpoint.rstrip("/") + "/datasets/" + repo, str(bare)], check=True)
    git = ["git", "--git-dir", str(bare)]
    subprocess.run(git + ["fsck", "--full", "--no-reflogs"], check=True, capture_output=True)
    commit = subprocess.check_output(git + ["cat-file", "commit", revision])
    assert hashlib.sha1(f"commit {len(commit)}\0".encode() + commit).hexdigest() == revision
    tree = subprocess.check_output(git + ["ls-tree", "-rz", revision])
    selected = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        attributes, name = entry.split(b"\t", 1)
        name = name.decode()
        parts = Path(name).parts
        if len(parts) >= 4 and parts[0] == "tasks" and parts[1] in expected_instances and parts[2] == "reference":
            selected.append((name, attributes.split()[2].decode()))
    batch = subprocess.run(git + ["cat-file", "--batch"],
        input="".join(oid + "\n" for _, oid in selected).encode(), capture_output=True, check=True).stdout
    cursor = 0
    result = []
    for name, oid in selected:
        end = batch.index(b"\n", cursor)
        header = batch[cursor:end].split()
        size = int(header[2]); raw = batch[end + 1:end + 1 + size]; cursor = end + size + 2
        assert header[0].decode() == oid and hashlib.sha1(f"blob {size}\0".encode() + raw).hexdigest() == oid
        lfs = None
        if raw.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            pointer = dict(line.split(b" ", 1) for line in raw.splitlines())
            lfs = SimpleNamespace(sha256=pointer[b"oid"].decode().removeprefix("sha256:"))
            size = int(pointer[b"size"])
        result.append(SimpleNamespace(rfilename=name, size=size, lfs=lfs, blob_id=oid))
    return result


def main(args):
    root = args.project.resolve()
    protocol = json.loads((root / "configs/eval/protocol_v2_unified64k8k.json").read_text())
    asi = protocol["benchmarks"]["asi"]
    manifest = json.loads((root / asi["task_manifest"]).read_text())
    expected_instances = {name + "__seed31415" for name in manifest["task_ids"]}
    assert len(expected_instances) == 60
    source = root / "artifacts/benchmarks/asi"
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    assert revision == asi["code_revision"]
    destination = root / "artifacts/asi/scoring_seed31415"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    entries = git_metadata(destination, asi["dataset_repo"], asi["dataset_revision"],
                           expected_instances, args.download_endpoint)
    present = {Path(item.rfilename).parts[1] for item in entries}
    assert present == expected_instances
    write_json(destination / "download_plan.json", {"repo": asi["dataset_repo"], "revision": asi["dataset_revision"],
        "source_revision": revision, "reference_files": len(entries),
        "reference_bytes": sum(item.size for item in entries), "instances": 60,
        "download_endpoint": args.download_endpoint, "hash_metadata_source": "Git objects verified to pinned commit, including LFS pointers",
        "scope": "Public seed31415 reference subtrees only, no solution/generation code or policy answers"})
    print(json.dumps({"event": "download_plan", "files": len(entries),
                      "bytes": sum(item.size for item in entries), "instances": 60}), flush=True)
    download = destination / "download"
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_one, item, asi["dataset_repo"], asi["dataset_revision"], download,
                               args.download_endpoint) for item in entries]
        for completed, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed % 40 == 0:
                print(json.dumps({"event": "download_progress", "complete": completed, "expected": len(entries)}), flush=True)
    verified = [verify(download / item.rfilename, item) for item in entries]
    instances = destination / "instances"
    instances.mkdir(exist_ok=True, mode=0o700)
    data_files = 0
    for instance_id in sorted(expected_instances):
        target = instances / instance_id
        target.mkdir(exist_ok=True, mode=0o700)
        reference = target / "reference"
        original_reference = download / "tasks" / instance_id / "reference"
        if not reference.exists():
            reference.symlink_to(original_reference.resolve(), target_is_directory=True)
        assert reference.resolve() == original_reference.resolve()
        original = root / "artifacts/asi/instances_seed31415" / instance_id
        if (original / "data").is_dir() and not (target / "data").exists():
            shutil.copytree(original / "data", target / "data")
        if (target / "data").exists():
            for item in (target / "data").rglob("*"):
                if item.is_file():
                    origin = original / "data" / item.relative_to(target / "data")
                    assert hashlib.sha256(item.read_bytes()).digest() == hashlib.sha256(origin.read_bytes()).digest()
                    data_files += 1
        if (original / "instance_meta.json").is_file() and not (target / "instance_meta.json").exists():
            shutil.copy2(original / "instance_meta.json", target / "instance_meta.json")
        assert not (original / "reference").exists(), "Do not populate or change the running solver tree"
    for item in verified:
        (download / item["path"]).chmod(0o444)
    receipt = {"status": "passed", "repo": asi["dataset_repo"], "dataset_revision": asi["dataset_revision"],
        "download_endpoint": args.download_endpoint, "hash_metadata_source": "Git objects verified to pinned commit, including LFS pointers",
        "source_revision": revision, "reference_instances": 60, "reference_file_count": len(verified),
        "reference_bytes": sum(item["size"] for item in verified), "all_upstream_hashes_verified": True,
        "files": verified, "grader_instances": str(instances), "copied_input_data_files": data_files,
        "solver_instances": str(root / "artifacts/asi/instances_seed31415"),
        "solver_reference_directories": 0, "solver_tree_modified": False,
        "gold_usage": "grader-only; not mounted into policy or training workspaces",
        "content_semantically_inspected": False, "paid_api_calls": 0,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "official_contract": "https://github.com/apexin-ai/ASI-Bench/blob/" + revision + "/docs/guide/how-scoring-works.md"}
    write_json(destination / "reference_integrity.json", receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != "files"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--download-endpoint", default="https://huggingface.co")
    main(parser.parse_args())
