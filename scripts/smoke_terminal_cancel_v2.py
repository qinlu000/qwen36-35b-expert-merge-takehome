#!/usr/bin/env python3
"""Actual dedicated vLLM disconnect/abort acceptance through the v2 client."""
import argparse
import asyncio
import json
from pathlib import Path
import time

import httpx

from terminal_baseline_v2 import TerminalV2LLM


def metric_total(text, name):
    return sum(float(line.rsplit(" ", 1)[1]) for line in text.splitlines()
               if line.startswith(name + "{") or line.startswith(name + " "))


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--api-key-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"scope": "one independent synthetic long generation; dedicated idle TB service",
              "status": "started"}
    llm = TerminalV2LLM(args.endpoint, "apex-qwen", args.api_key_path, 0, args.output)
    llm.deadline = time.monotonic() + 60
    headers = {"Authorization": "Bearer " + args.api_key_path.read_text().strip()}
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=llm.endpoint, headers=headers, trust_env=False) as client:
            llm.client = client

            async def counts():
                response = await client.get("/metrics", timeout=5)
                response.raise_for_status()
                return {"running": metric_total(response.text, "vllm:num_requests_running"),
                        "waiting": metric_total(response.text, "vllm:num_requests_waiting")}

            before = await counts()
            report["before"] = before
            if before["running"] or before["waiting"]:
                raise ValueError("dedicated endpoint is not idle")
            generation = asyncio.create_task(llm.call(
                "Independent synthetic cancellation check. Output the integers from 1 through 20000, "
                "one integer per line, without abbreviating or stopping early."))
            try:
                for _ in range(200):
                    snapshot = await counts()
                    if snapshot["running"] >= 1:
                        report["observed_in_flight"] = snapshot
                        break
                    if generation.done():
                        await generation
                        raise ValueError("synthetic generation completed before cancellation")
                    await asyncio.sleep(0.1)
                else:
                    raise TimeoutError("generation never reached engine")
                generation.cancel()
                try:
                    await generation
                    raise AssertionError("cancellation was swallowed")
                except asyncio.CancelledError:
                    report["client_cancelled"] = True
                cancelled_at = time.monotonic()
                for _ in range(200):
                    snapshot = await counts()
                    if snapshot == {"running": 0, "waiting": 0}:
                        report["after"] = snapshot
                        report["engine_quiesced_after_cancel_seconds"] = round(time.monotonic() - cancelled_at, 4)
                        break
                    await asyncio.sleep(0.1)
                else:
                    raise TimeoutError("engine still busy after client disconnected")
                report["status"] = "passed"
            finally:
                if not generation.done():
                    generation.cancel()
                    try:
                        await generation
                    except asyncio.CancelledError:
                        pass
    except BaseException as exc:
        report.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 4)
        (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
