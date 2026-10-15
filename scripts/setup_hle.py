"""Install the pinned HLE harness and verify it without evaluating benchmark questions.

Run on the benchmark host after installing the project's uv binary:
  python3 scripts/setup_hle.py --proxy http://127.0.0.1:38080
  artifacts/envs/hle/bin/python scripts/setup_hle.py --check-only

The gated test data stays in ignored artifacts. Only id/image columns are read.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace


CODE_REVISION = "22ed3074b1e7b134bcbc09028d0ba320839b0655"
DATA_REVISION = "5a81a4c7271a2a2a312b9a690f0c2fde837e4c29"
DATA_SHA256 = "6d0ee0602e8aea6b159509577e884f48ecac7b8e3f6822a35f51335a446c726a"
DATA_BYTES = 274276147


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, env, **kwargs):
    return subprocess.run([str(item) for item in command], env=env, check=True,
                          text=True, **kwargs)


def check(project, credentials):
    sys.dont_write_bytecode = True
    import pyarrow.parquet as pq
    from datasets import Dataset, Features, Image, Value, load_dataset
    from huggingface_hub import hf_hub_download
    from PIL import Image as PILImage
    from pydantic import ValidationError

    base = project / "artifacts/benchmarks/hle"
    source = base / "source"
    data_dir = base / DATA_REVISION
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    data_dir.chmod(0o700)
    parquet = data_dir / "test-00000-of-00001.parquet"
    if not parquet.exists():
        token = os.environ.get("HF_TOKEN")
        if credentials and credentials.exists():
            values = dict(line.split("=", 1) for line in credentials.read_text().splitlines()
                          if line and not line.startswith("#") and "=" in line)
            token = values.get("HF_TOKEN", token)
        downloaded = hf_hub_download(
            repo_id="cais/hle", repo_type="dataset", revision=DATA_REVISION,
            filename="data/test-00000-of-00001.parquet", token=token or False,
            local_dir=data_dir,
        )
        shutil.move(downloaded, parquet)
    parquet.chmod(0o600)
    assert parquet.stat().st_size == DATA_BYTES, "HLE test file size mismatch"
    assert sha256(parquet) == DATA_SHA256, "HLE test file hash mismatch"

    # Parquet projection avoids materializing question, answer, or rationale columns.
    safe = pq.read_table(parquet, columns=["id", "image"]).to_pydict()
    ids = safe["id"]
    image_ids = [task_id for task_id, image in zip(ids, safe["image"]) if image]
    assert len(ids) == len(set(ids)) == 2500
    assert len(image_ids) == 342
    manifest = {
        "dataset_repo": "cais/hle", "dataset_revision": DATA_REVISION,
        "split": "test", "source_file_bytes": DATA_BYTES,
        "source_file_sha256": DATA_SHA256, "inspection_columns": ["id", "image"],
        "count": len(ids), "image_count": len(image_ids),
        "text_only_count": len(ids) - len(image_ids),
        "task_ids": ids, "image_task_ids": image_ids,
        "training_use": "forbidden; evaluation data only",
    }
    canonical = project / "analysis/source_snapshots/protocol/hle_task_ids.json"
    if canonical.exists():
        frozen = json.loads(canonical.read_text())
        assert set(frozen["task_ids"]) == set(ids), "Frozen HLE task IDs differ"
    (data_dir / "setup_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    synthetic_dir = base / "setup"
    synthetic_dir.mkdir(exist_ok=True)
    pixels = io.BytesIO()
    PILImage.new("RGB", (32, 32), "red").save(pixels, format="PNG")
    image_bytes = pixels.getvalue()
    image_uri = "data:image/png;base64," + base64.b64encode(image_bytes).decode()
    synthetic_path = synthetic_dir / "synthetic.parquet"
    synthetic = Dataset.from_dict({
        "id": ["synthetic-text", "synthetic-image"],
        "question": ["Synthetic: 2 + 3?", "Synthetic: identify the solid color."],
        "answer": ["5", "red"], "image": ["", image_uri],
        "image_preview": [None, {"bytes": image_bytes, "path": None}],
    }, features=Features({"id": Value("string"), "question": Value("string"),
                          "answer": Value("string"), "image": Value("string"),
                          "image_preview": Image()}))
    synthetic.to_parquet(synthetic_path)
    loaded_dataset = load_dataset("parquet", data_files={"test": str(synthetic_path)},
                                  split="test", cache_dir=str(synthetic_dir / "cache"))
    loaded = loaded_dataset.to_dict()
    assert loaded["answer"] == ["5", "red"]
    assert loaded_dataset[1]["image_preview"].getpixel((0, 0)) == (255, 0, 0)

    # Dummy credentials satisfy the official client's import-time constructor.
    # Neither --help nor these local function/schema checks make HTTP requests.
    env = dict(os.environ, OPENAI_API_KEY="synthetic-no-network",
               OPENAI_BASE_URL="http://127.0.0.1:9/v1", CUDA_VISIBLE_DEVICES="",
               HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")
    os.environ.update({key: env[key] for key in (
        "OPENAI_API_KEY", "OPENAI_BASE_URL", "CUDA_VISIBLE_DEVICES",
        "HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE")})
    modules = {}
    help_paths = []
    for name in ("run_model_predictions", "run_judge_results"):
        path = source / "hle_eval" / (name + ".py")
        output = run([sys.executable, path, "--help"], env, capture_output=True)
        assert "--dataset" in output.stdout
        help_path = base / (name + "_help.txt")
        help_path.write_text(output.stdout)
        help_paths.append(str(help_path.relative_to(project)))
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[name] = module

    predictions = modules["run_model_predictions"]
    predictions.args = SimpleNamespace(model="synthetic-model")
    text = predictions.format_message({"question": "Synthetic: 2 + 3?", "image": ""})
    image = predictions.format_message({
        "question": "Synthetic image transport check.",
        "image": image_uri,
    })
    assert text[0]["role"] == "system" and len(text[1]["content"]) == 1
    assert image[1]["content"][1]["type"] == "image_url"
    judge = modules["run_judge_results"]
    valid = dict(extracted_final_answer="5", reasoning="Synthetic match.",
                 correct="yes", confidence=80, strict=True)
    judge.ExtractedAnswer.model_validate(valid)
    rejected = 0
    for invalid in ({key: value for key, value in valid.items() if key != "strict"},
                    dict(valid, correct="maybe"), dict(valid, strict=False)):
        try:
            judge.ExtractedAnswer.model_validate(invalid)
        except ValidationError:
            rejected += 1
    assert rejected == 3
    prompt = judge.JUDGE_PROMPT.format(question="Synthetic: 2 + 3?",
                                       correct_answer="5", response="Answer: 5")
    assert "[correct_answer]: 5" in prompt
    uv = project / "artifacts/tools/uv/uv"
    run([uv, "pip", "check", "--python", sys.executable], env, capture_output=True)
    freeze = run([uv, "pip", "freeze", "--python", sys.executable], env,
                 capture_output=True)
    lock = base / "requirements.freeze.txt"
    lock.write_text(freeze.stdout)
    receipt = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_revision": run(["git", "-C", source, "rev-parse", "HEAD"], env,
                             capture_output=True).stdout.strip(),
        "source_clean": not run(["git", "-C", source, "status", "--porcelain"], env,
                                capture_output=True).stdout.strip(),
        "python": sys.version, "python_executable": sys.executable,
        "dataset_revision": DATA_REVISION, "dataset_sha256": DATA_SHA256,
        "questions": len(ids), "image_questions": len(image_ids),
        "manifest_sha256": sha256(data_dir / "setup_manifest.json"),
        "dependency_lock_sha256": sha256(lock), "cli_help": help_paths,
        "uv_pip_check": "passed",
        "source_file_sha256": {
            str(path.relative_to(source)): sha256(path) for path in (
                source / "requirements.txt",
                source / "hle_eval/run_model_predictions.py",
                source / "hle_eval/run_judge_results.py")
        },
        "synthetic_checks": {"text_messages": True, "image_messages": True,
                             "parquet_load_with_image_preview": True,
                             "valid_schema": True, "invalid_schemas_rejected": rejected,
                             "judge_prompt_format": True},
        "network_model_calls": 0, "formal_questions_evaluated": 0,
        "reference_columns_read": False,
        "limits": ["No real model endpoint or API judge called.",
                   "Official CLI does not pin dataset revision or apply temperature.",
                   "Native judge confidence has no 0..100 bound; enforce the experiment schema in the final runner.",
                   "DeepSeek JSON judge adapter and outer deadlines still need a runner and validation."],
    }
    assert receipt["code_revision"] == CODE_REVISION
    (base / "setup_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in (
        "code_revision", "questions", "image_questions", "synthetic_checks",
        "network_model_calls", "formal_questions_evaluated")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", default="3.12.13")
    parser.add_argument("--proxy")
    parser.add_argument("--credentials", type=Path,
                        help="Optional private HF_TOKEN file, used only if data is missing")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    env = os.environ.copy()
    if args.proxy:
        env.update(HTTP_PROXY=args.proxy, HTTPS_PROXY=args.proxy)
    env.update(UV_CACHE_DIR=str(project / "artifacts/cache/uv"),
               UV_PYTHON_INSTALL_DIR=str(project / "artifacts/tools/python"))
    os.environ.update(env)
    base = project / "artifacts/benchmarks/hle"
    base.mkdir(parents=True, exist_ok=True)
    source = base / "source"
    venv = project / "artifacts/envs/hle"
    if not args.check_only:
        if not (source / ".git").exists():
            run(["git", "clone", "--filter=blob:none", "--no-checkout",
                 "https://github.com/centerforaisafety/hle.git", source], env)
        run(["git", "-C", source, "checkout", "--detach", CODE_REVISION], env)
        uv = project / "artifacts/tools/uv/uv"
        if not (venv / "bin/python").exists():
            run([uv, "venv", "--python", args.python, venv], env)
        frozen = project / "scripts/requirements-hle.lock"
        run([uv, "pip", "sync", "--python", venv / "bin/python", frozen], env)
    if Path(sys.prefix).resolve() != venv.resolve():
        command = [venv / "bin/python", Path(__file__).resolve(),
                   "--project", project, "--check-only"]
        if args.credentials:
            command += ["--credentials", args.credentials]
        run(command, env)
    else:
        check(project, args.credentials)


if __name__ == "__main__":
    main()
