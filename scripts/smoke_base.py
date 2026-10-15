"""Synthetic GPU/HTTP smoke only; starts a temporary local vLLM server when run."""

import argparse
import base64
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import UUID


REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"
BASE_URL = "http://127.0.0.1:18000"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--prepare-only", action="store_true",
                        help="Create only the private key and output directory; no GPU or server")
    args = parser.parse_args()
    os.umask(0o077)
    project = args.project.resolve()
    private = project / "artifacts/private"
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = private / "base_smoke_api_key"
    if not key_path.exists():
        key_path.write_text(secrets.token_urlsafe(32) + "\n")
    private.chmod(0o700)
    key_path.chmod(0o600)
    output = project / "artifacts/preflight" / (
        "base-smoke-" + os.environ.get("SLURM_JOB_ID", "prepared"))
    output.mkdir(parents=True, exist_ok=True)
    if args.prepare_only:
        print("Prepared private key and output directory; no server or GPU used.")
        return

    key = key_path.read_text().strip()
    visible = os.environ["CUDA_VISIBLE_DEVICES"]
    tensor_parallel = len(visible.split(","))
    assert tensor_parallel in (2, 4), "Smoke supports two or four allocated GPUs"
    model = project / "artifacts/models/Qwen3.6-35B-A3B" / REVISION
    index = json.loads((model / "model.safetensors.index.json").read_text())
    shards = set(index["weight_map"].values())
    assert len(shards) == 26 and all((model / name).is_file() for name in shards)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 18000))

    command = [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
               "--model", str(model), "--served-model-name", "apex-qwen",
               "--host", "127.0.0.1", "--port", "18000", "--dtype", "bfloat16",
               "--tensor-parallel-size", str(tensor_parallel), "--distributed-executor-backend", "mp",
               "--max-model-len", "262144", "--max-num-seqs", "4",
               "--gpu-memory-utilization", "0.85", "--enforce-eager",
               "--gdn-prefill-backend", "triton", "--moe-backend", "triton",
               "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_coder",
               "--reasoning-parser", "qwen3", "--no-enable-log-requests"]
    server_env = dict(os.environ, VLLM_API_KEY=key)
    summary = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
               "job_id": os.environ.get("SLURM_JOB_ID"), "model_revision": REVISION,
               "cuda_visible_devices": visible, "server_command": command,
               "purpose": "synthetic smoke; these settings do not freeze formal thinking preference",
               "cases": [], "passed": False}

    def gpu_snapshot():
        import torch
        # Slurm can remap CUDA ordinals; NVML must be queried by device UUID.
        gpu_uuids = [
            "GPU-" + str(UUID(bytes=bytes(torch.cuda.get_device_properties(i).uuid.bytes)))
            for i in range(tensor_parallel)
        ]
        result = subprocess.run([
            "nvidia-smi", "-i", ",".join(gpu_uuids),
            "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,driver_version",
            "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True)
        return {"cuda_to_gpu_uuid": dict(enumerate(gpu_uuids)),
                "columns": ["nvml_index", "name", "uuid", "total_mib", "used_mib",
                            "free_mib", "driver_version"],
                "rows": [row.split(", ") for row in result.stdout.strip().splitlines()]}

    def request(path, payload=None, timeout=180, authenticate=True):
        headers = {"Content-Type": "application/json"}
        if authenticate:
            headers["Authorization"] = "Bearer " + key
        body = None if payload is None else json.dumps(payload).encode()
        try:
            # Local smoke traffic must never traverse an inherited HTTP proxy.
            with build_opener(ProxyHandler({})).open(
                    Request(BASE_URL + path, data=body, headers=headers),
                    timeout=timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            raise RuntimeError(f"{path}: HTTP {exc.code}") from None
        return json.loads(raw) if raw else None

    def chat(name, messages, **extra):
        payload = {"model": "apex-qwen", "messages": messages, "temperature": 0,
                   "max_tokens": 256,
                   "chat_template_kwargs": {"enable_thinking": False,
                                            "preserve_thinking": False}, **extra}
        started = time.monotonic()
        response = request("/v1/chat/completions", payload)
        assert response.get("usage", {}).get("completion_tokens", 0) > 0
        (output / (name + "_request.json")).write_text(json.dumps(payload, indent=2) + "\n")
        (output / (name + "_response.json")).write_text(json.dumps(response, indent=2) + "\n")
        summary["cases"].append({"name": name, "latency_seconds": time.monotonic() - started,
                                 "usage": response["usage"],
                                 "finish_reason": response["choices"][0]["finish_reason"]})
        return response["choices"][0]["message"]

    def interrupted(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    process = None
    try:
        summary["gpu_before"] = gpu_snapshot()
        with (output / "server.log").open("w") as log:
            process = subprocess.Popen(command, env=server_env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            started = time.monotonic()
            deadline = started + 1200
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"vLLM exited before health: {process.returncode}")
                try:
                    request("/health", timeout=min(2, deadline - time.monotonic()))
                    break
                except (RuntimeError, URLError, TimeoutError):
                    time.sleep(min(2, max(0, deadline - time.monotonic())))
            else:
                raise TimeoutError("vLLM was not healthy within 1200 seconds")
            summary["startup_seconds"] = time.monotonic() - started
            models = request("/v1/models")
            assert any(item["id"] == "apex-qwen" for item in models["data"])
            try:
                request("/v1/models", authenticate=False)
            except RuntimeError as exc:
                assert str(exc).endswith("HTTP 401")
            else:
                raise AssertionError("Server accepted an unauthenticated model request")
            summary["api_authentication"] = "enforced"
            summary["gpu_ready"] = gpu_snapshot()

            text = chat("text", [{"role": "user", "content": "Reply exactly SYNTHETIC_TEXT_OK."}])
            assert "SYNTHETIC_TEXT_OK" in (text.get("content") or "")

            from PIL import Image
            pixels = io.BytesIO()
            Image.new("RGB", (32, 32), "red").save(pixels, format="PNG")
            uri = "data:image/png;base64," + base64.b64encode(pixels.getvalue()).decode()
            image = chat("image", [{"role": "user", "content": [
                {"type": "text", "text": "What color is this square? Reply with one English word."},
                {"type": "image_url", "image_url": {"url": uri}},
            ]}])
            assert "red" in (image.get("content") or "").lower()

            tools = [{"type": "function", "function": {
                "name": "add_numbers", "description": "Add two integers.",
                "parameters": {"type": "object", "properties": {
                    "a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"], "additionalProperties": False},
            }}]
            messages = [{"role": "user", "content": (
                "Call add_numbers with a=17 and b=25. Wait for its result before answering.")}]
            tool_message = chat("tool_call", messages, tools=tools, tool_choice="auto")
            calls = tool_message.get("tool_calls") or []
            assert len(calls) == 1 and calls[0]["function"]["name"] == "add_numbers"
            arguments = json.loads(calls[0]["function"]["arguments"])
            assert arguments == {"a": 17, "b": 25}
            messages += [{"role": "assistant", "content": tool_message.get("content"),
                          "tool_calls": calls},
                         {"role": "tool", "tool_call_id": calls[0]["id"],
                          "content": json.dumps({"sum": arguments["a"] + arguments["b"]})}]
            answer = chat("tool_result", messages, tools=tools, tool_choice="none")
            assert "42" in (answer.get("content") or "")
            summary["gpu_after_requests"] = gpu_snapshot()
            summary["passed"] = True
    except BaseException as exc:
        summary["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                pass
            # Also remove workers left behind if the server parent exited first.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        summary["server_returncode"] = None if process is None else process.returncode
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({"output": str(output), "passed": summary["passed"]}))


if __name__ == "__main__":
    main()
