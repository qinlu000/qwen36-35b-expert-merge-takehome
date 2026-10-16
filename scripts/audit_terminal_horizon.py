#!/usr/bin/env python3
"""Fetch pinned TerminalHorizon evidence and statically inspect its task/trace join."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import time

import pyarrow.parquet as pq
import requests

SOURCES = {
    "traces": ("shunzou05/TerminalHorizon-3K", "45f1e98e317d3639437f0eb02f4e8bc5825732f3"),
    "environments": ("shunzou05/TerminalHorizon-Environment", "e55b3e99927ed6b9b2e4abf2fa93e965dd0503ef"),
}


def fetch(session, url, dest, expected_size=None, expected_sha=None):
    if not dest.exists() or (expected_size is not None and dest.stat().st_size != expected_size):
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(dest.suffix + ".part")
        if expected_size and expected_size > 64 * 1024 * 1024:
            # The proxy truncated the long response. Resume by exact 32MiB ranges.
            start = temp.stat().st_size if temp.exists() else 0
            with temp.open("ab") as output:
                while start < expected_size:
                    end = min(start + 32 * 1024 * 1024, expected_size) - 1
                    for attempt in range(3):
                        try:
                            response = session.get(url, headers={"Range": f"bytes={start}-{end}"}, timeout=(30, 90))
                            response.raise_for_status()
                            break
                        except requests.RequestException:
                            print(json.dumps({"range_retry": attempt + 1, "start": start, "file": dest.name}), flush=True)
                            if attempt == 2: raise
                            time.sleep(2 ** attempt)
                    assert response.status_code == 206
                    assert response.headers["Content-Range"] == f"bytes {start}-{end}/{expected_size}"
                    assert len(response.content) == end - start + 1
                    output.write(response.content); output.flush()
                    start = end + 1
                    print(json.dumps({"range_download_bytes": start, "expected_bytes": expected_size}), flush=True)
        else:
            with session.get(url, stream=True, timeout=(30, 90)) as response:
                response.raise_for_status()
                with temp.open("wb") as output:
                    for block in response.iter_content(4 * 1024 * 1024):
                        output.write(block)
        temp.rename(dest)
    digest = hashlib.sha256()
    with dest.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if expected_size is not None and dest.stat().st_size != expected_size:
        raise ValueError(f"Size mismatch: {dest.name}")
    if expected_sha and actual != expected_sha:
        raise ValueError(f"SHA256 mismatch: {dest.name}")
    receipt = {"url": url, "path": str(dest), "bytes": dest.stat().st_size,
               "sha256": actual, "expected_sha256": expected_sha,
               "verified_lfs": bool(expected_sha)}
    print(json.dumps({"file_verified": dest.name, "bytes": receipt["bytes"]}), flush=True)
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--proxy", default="http://127.0.0.1:38080")
    ap.add_argument("--download-traces", action="store_true")
    args = ap.parse_args()
    out = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.proxies = {"http": args.proxy, "https": args.proxy}
    receipts, sources = [], {}
    start = time.monotonic()
    for kind, (repo, rev) in SOURCES.items():
        response = session.get(f"https://huggingface.co/api/datasets/{repo}/revision/{rev}?blobs=true", timeout=30)
        response.raise_for_status()
        api = response.json()
        (out / f"{kind}_api.json").write_text(json.dumps(api, indent=2) + "\n")
        sources[kind] = {"repo": repo, "revision": rev, "card": api.get("cardData")}
        for info in api["siblings"]:
            file = info["rfilename"]
            if file != "README.md" and file != "metadata/tasks.parquet" and not (
                    args.download_traces and kind == "traces" and file.endswith(".jsonl")):
                continue
            receipts.append(fetch(session, f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{file}",
                                  out / kind / file, info.get("size"), (info.get("lfs") or {}).get("sha256")))
    envs = pq.read_table(out / "environments/metadata/tasks.parquet").to_pylist()
    summary = {"sources": sources, "receipts": receipts, "environment_rows": len(envs),
               "environment_schema": str(pq.read_schema(out / "environments/metadata/tasks.parquet")),
               "category_counts": dict(Counter(x["category"] for x in envs)),
               "note": "Static evidence only; no trajectory commands, verifiers, containers, API models or GPU executed."}
    with (out / "environment_metadata.jsonl").open("w") as stream:
        for row in envs:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    trace_path = out / "traces/data/TerminalHorizon-3K-SFT.jsonl"
    if trace_path.exists() and any(x["path"] == str(trace_path) for x in receipts):
        lengths, roles, field_counts = [], Counter(), Counter()
        first_inputs = []
        with trace_path.open() as stream, (out / "trace_index.jsonl").open("w") as index:
            for row_index, line in enumerate(stream):
                row = json.loads(line)
                field_counts.update(row.keys())
                conv = row.get("conversations", [])
                roles.update(m.get("role") for m in conv)
                lengths.append(len(conv))
                first = conv[0].get("content", "") if conv else ""
                instruction = first.split("Task Description:\n", 1)[-1].rsplit("\n\nCurrent terminal state:\n", 1)[0]
                first_inputs.append({"row_index": row_index, "first_input": first,
                                     "instruction_extracted": instruction,
                                     "assistant_turns": sum(m.get("role") == "assistant" for m in conv)})
                index.write(json.dumps({"row_index": row_index, "fields": list(row),
                                        "turns": len(conv), "instruction": instruction,
                                        "assistant_turns": first_inputs[-1]["assistant_turns"]}, ensure_ascii=False) + "\n")
        summary.update(trace_rows=len(lengths), trace_field_counts=dict(field_counts), role_counts=dict(roles),
                       turns_min=min(lengths), turns_max=max(lengths))
        (out / "first_inputs.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in first_inputs))
    summary["seconds"] = round(time.monotonic() - start, 2)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
