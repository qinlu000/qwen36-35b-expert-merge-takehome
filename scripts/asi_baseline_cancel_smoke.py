#!/usr/bin/env python3
"""Real Base cancellation probe, self-authored prompt and no benchmark input."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
import time

import httpx
from run_asi_baseline_v2 import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    args = parser.parse_args()
    endpoint = args.endpoint.rstrip("/")
    key = args.key_file.read_text().strip()
    run = Path(tempfile.mkdtemp(prefix="baseline-v2-cancel-", dir=args.project / "artifacts/preflight/asi"))
    headers = {"Authorization": f"Bearer {key}"}
    def metrics():
        with httpx.Client(trust_env=False, headers=headers, timeout=3) as client:
            response = client.get(endpoint + "/metrics")
            response.raise_for_status()
            values = {}
            for name in ("num_requests_running", "num_requests_waiting"):
                matches = re.findall(r"^vllm:" + name + r"(?:\{[^\n]*\})?\s+([0-9.eE+-]+)$", response.text, re.M)
                values[name] = sum(float(value) for value in matches)
            values["aborted"] = sum(float(line.rsplit(" ", 1)[1]) for line in response.text.splitlines()
                if line.startswith("vllm:request_success_total") and 'finished_reason="abort"' in line)
            return values
    before = metrics()
    if before["num_requests_running"] or before["num_requests_waiting"]:
        raise RuntimeError("Cancellation probe requires an idle dedicated endpoint")
    # min_tokens is deliberately a synthetic cancellation stimulus, not an ASI
    # policy setting. It guarantees this request cannot EOS before cancellation.
    request = {"model": "apex-qwen", "messages": [{"role": "user", "content":
        "Self-authored cancellation test. Repeatedly output the sequence 1 2 3 4 5 with spaces."}],
        "max_tokens": 8192, "min_tokens": 4096, "temperature": .7, "top_p": .8, "top_k": 20,
        "seed": 0, "stream": False, "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": False}}
    errors = []
    def generate():
        try:
            with httpx.Client(transport=httpx.HTTPTransport(retries=0), trust_env=False, headers=headers) as client:
                # Engine Prometheus gauges update on a roughly five-second
                # stats cycle; keep this longer than one cycle so the probe
                # must observe a running request before validating cancellation.
                client.post(endpoint + "/v1/chat/completions", json=request, timeout=6).raise_for_status()
            errors.append("unexpected_complete_response")
        except httpx.HTTPError as error:
            errors.append(type(error).__name__)
    thread = threading.Thread(target=generate)
    started = time.monotonic()
    thread.start()
    samples = []
    while thread.is_alive():
        samples.append({"seconds": time.monotonic() - started, **metrics()})
        time.sleep(.05)
    thread.join()
    disconnected_at = time.monotonic() - started
    for _ in range(120):
        current = metrics()
        samples.append({"seconds": time.monotonic() - started, **current})
        if current["num_requests_running"] == current["num_requests_waiting"] == 0:
            break
        time.sleep(.1)
    time.sleep(.5)
    after = metrics()
    passed = (errors == ["ReadTimeout"] and any(sample["num_requests_running"] >= 1 for sample in samples)
        and after["num_requests_running"] == after["num_requests_waiting"] == 0)
    summary = {"passed": bool(passed), "run_dir": str(run), "generation_attempts": 1,
        "benchmark_conditions_executed": 0, "judge_calls": 0,
        "error_classes": errors, "disconnected_after_seconds": round(disconnected_at, 3),
        "before": before, "after": after, "samples": samples,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "stimulus": "synthetic min_tokens4096/max_tokens8192; not production ASI sampling"}
    write_json(run / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
