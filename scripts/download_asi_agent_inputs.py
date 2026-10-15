#!/usr/bin/env python3
"""Fetch fixed public ASI inputs without opening prompts or reference material."""

import json
from pathlib import Path
import sys

from huggingface_hub import HfApi, snapshot_download


root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
receipts = root / "artifacts/preflight/asi"
receipts.mkdir(parents=True, exist_ok=True)
revision = "0fa14219cafdbab634d8b3cfbce238a8735a214f"
repo = "Apexintelligence-AI/ASI-Bench-seed31415"
index_path = root / "artifacts/protocol_sources/asi/seed31415_file_index.json"
if index_path.is_file():
    index = json.loads(index_path.read_text())
    assert index["revision"] == revision
else:
    index = {"repo": repo, "revision": revision,
             "files": HfApi().list_repo_files(repo, repo_type="dataset", revision=revision, token=False)}
files = []
for name in index["files"]:
    parts = Path(name).parts
    if len(parts) < 3 or parts[0] != "tasks":
        continue
    if any(part.lower() in {"reference", "solution", "solutions", "answers"} for part in parts):
        continue
    if (len(parts) == 3 and parts[2] in {"prompt_b1.md", "prompt_b2.md", "prompt_b3.md", "prompt_b4.md",
                                                       "task_info.json", "framework_task_info.json"}) or parts[2] == "data":
        files.append(name)

destination = root / "artifacts/asi/hf_seed31415_agent_inputs"
snapshot_download(repo_id="Apexintelligence-AI/ASI-Bench-seed31415", repo_type="dataset", revision=revision,
                  token=False, allow_patterns=files, local_dir=destination,
                  cache_dir=root / "artifacts/cache/hf", max_workers=2)
instances = root / "artifacts/asi/instances_seed31415"
instances.mkdir(parents=True, exist_ok=True)
task_ids = []
for source in sorted((destination / "tasks").iterdir()):
    if not source.is_dir():
        continue
    link = instances / source.name
    if not link.exists():
        link.symlink_to(source)
    assert all((source / f"prompt_b{level}.md").is_file() for level in range(1, 5))
    task_ids.append(source.name.split("__", 1)[0])
assert len(task_ids) == 60 and len(set(task_ids)) == 60
receipt = {"repository": index["repo"], "revision": revision, "scope": "agent_inputs_only_no_references",
           "file_count": len(files), "instance_count": len(task_ids), "condition_count": len(task_ids) * 4,
           "instances_dir": str(instances), "task_ids": task_ids, "content_inspected": False,
           "reference_material_downloaded": False}
(receipts / "agent_input_download.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: value for key, value in receipt.items() if key != "task_ids"}, indent=2))
