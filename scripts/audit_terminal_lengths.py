#!/usr/bin/env python3
"""CPU-only token counts. Output numeric lengths, never conversation content."""
import os

for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"):
    os.environ[name] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path
import re
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

TOKENIZER = None
THRESHOLDS = [4096, 8192, 16384, 24576, 28672, 32768, 65536, 131072]


def init_worker(path):
    global TOKENIZER
    from transformers import AutoTokenizer
    TOKENIZER = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    TOKENIZER.model_max_length = 10**12  # Counting only; never truncate long records.


def clean_assistant(text):
    # Only explicit leading paired wrappers; do not alter tags inside action JSON.
    removed = 0
    while match := re.match(r"^\s*<think>.*?</think>\s*", text, re.S):
        text = text[match.end():]
        removed += 1
    return text, removed


def audit_file(job):
    path, source_root, output_dir, sample_size = job
    path = Path(path)
    pf = pq.ParquetFile(path)
    nrows = pf.metadata.num_rows
    wanted = set(range(nrows)) if not sample_size else set(np.linspace(0, nrows - 1, min(nrows, sample_size), dtype=int).tolist())
    relative = str(path.relative_to(source_root))
    result_path = Path(output_dir) / (relative.replace("/", "__") + ".jsonl")
    started = time.monotonic()
    done = 0
    flags = Counter()
    offset = 0
    raw_chars = 0
    with result_path.open("w") as stream:
        for batch in pf.iter_batches(batch_size=64, columns=["conversations"], use_threads=False):
            indices = [i - offset for i in wanted if offset <= i < offset + batch.num_rows]
            if indices:
                rows = batch.take(pa.array(sorted(indices), type=pa.int64())).to_pylist()
                for in_batch, row in zip(sorted(indices), rows):
                    messages = [{"role": m["role"], "content": m["content"] or ""} for m in row["conversations"]]
                    clean = []
                    assistant_indices = []
                    clean_assistant_texts = []
                    for index, message in enumerate(messages):
                        content = message["content"]
                        if message["role"] == "assistant":
                            assistant_indices.append(index)
                            content, removed = clean_assistant(content)
                            flags["paired_leading_think_blocks_removed"] += removed
                            flags["assistant_messages_with_removal"] += bool(removed)
                            flags["assistant_unclosed_leading_think_retained"] += content.lstrip().startswith("<think>")
                            clean_assistant_texts.append(content)
                        clean.append(dict(message, content=content))
                    raw_rendered = TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=False,
                                                                  enable_thinking=True, preserve_thinking=True)
                    clean_rendered = TOKENIZER.apply_chat_template(clean, tokenize=False, add_generation_prompt=False,
                                                                    enable_thinking=False, preserve_thinking=False)
                    texts = [m["content"] for m in messages] + clean_assistant_texts + [raw_rendered, clean_rendered]
                    encoded = TOKENIZER(texts, add_special_tokens=False, truncation=False,
                                        return_attention_mask=False, return_token_type_ids=False)["input_ids"]
                    lengths = [len(ids) for ids in encoded]
                    raw_messages = lengths[:len(messages)]
                    raw_assistant = [raw_messages[i] for i in assistant_indices]
                    clean_assistant_lengths = lengths[len(messages):len(messages) + len(assistant_indices)]
                    raw_content = sum(raw_messages)
                    clean_content = raw_content - sum(raw_assistant) + sum(clean_assistant_lengths)
                    record = {"row_index": offset + in_batch,
                              "raw_content_sum": raw_content, "clean_content_sum": clean_content,
                              "raw_chat_total": lengths[-2], "clean_chat_total": lengths[-1],
                              "raw_assistant_sum": sum(raw_assistant), "clean_assistant_sum": sum(clean_assistant_lengths),
                              "raw_assistant_max": max(raw_assistant, default=0),
                              "clean_assistant_max": max(clean_assistant_lengths, default=0),
                              "raw_assistant_outputs": raw_assistant, "clean_assistant_outputs": clean_assistant_lengths,
                              "message_count": len(messages)}
                    stream.write(json.dumps(record) + "\n")
                    raw_chars += sum(len(m["content"]) for m in messages)
                    done += 1
            offset += batch.num_rows
    return {"source_file": relative, "population_n": nrows, "sample_n": done,
            "numeric_rows": str(result_path), "seconds": time.monotonic() - started,
            "source_characters_read": raw_chars, "flags": dict(flags)}


def stats(values, weights):
    values = np.asarray(values, dtype=np.int64)
    weights = np.asarray(weights, dtype=np.float64)
    order = np.argsort(values)
    ordered = values[order]
    cumulative = np.cumsum(weights[order])
    total = cumulative[-1]
    def quantile(q):
        return int(ordered[min(np.searchsorted(cumulative, q * total, side="left"), len(ordered) - 1)])
    return {"observed_n": len(values), "weighted_n": float(total),
            "mean": float(np.average(values, weights=weights)), "median": quantile(.5),
            "p90": quantile(.9), "p95": quantile(.95), "p99": quantile(.99),
            "max_observed": int(values.max()),
            "coverage_le": {str(t): float(weights[values <= t].sum() / total) for t in THRESHOLDS}}


def aggregate(files):
    metrics = ["raw_content_sum", "clean_content_sum", "raw_chat_total", "clean_chat_total",
               "raw_assistant_sum", "clean_assistant_sum", "raw_assistant_max", "clean_assistant_max"]
    groups = {}
    for file in files:
        parts = Path(file["source_file"]).parts
        difficulty, domain = parts[-3], parts[-2]
        rows = [json.loads(line) for line in Path(file["numeric_rows"]).read_text().splitlines()]
        weight = file["population_n"] / file["sample_n"]
        keys = ["all", f"difficulty/{difficulty}", f"domain/{domain}", f"file/{difficulty}/{domain}"]
        for key in keys:
            group = groups.setdefault(key, {"population_rows": 0, "sample_rows": 0,
                                           "metrics": {k: [[], []] for k in metrics + ["raw_per_assistant", "clean_per_assistant"]}})
            group["population_rows"] += file["population_n"]
            group["sample_rows"] += file["sample_n"]
            for row in rows:
                for metric in metrics:
                    group["metrics"][metric][0].append(row[metric])
                    group["metrics"][metric][1].append(weight)
                for mode in ("raw", "clean"):
                    outputs = row[f"{mode}_assistant_outputs"]
                    group["metrics"][f"{mode}_per_assistant"][0].extend(outputs)
                    group["metrics"][f"{mode}_per_assistant"][1].extend([weight] * len(outputs))
    return {key: {**{k: v for k, v in group.items() if k != "metrics"},
                  "metrics": {metric: stats(*data) for metric, data in group["metrics"].items()}}
            for key, group in groups.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--samples-per-file", type=int, default=128, help="0 for all rows")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--difficulty", choices=["easy", "medium", "mixed"])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    assert 1 <= args.workers <= 8
    root = args.root
    source_root = root / "artifacts/data/raw/terminal_corpus/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9"
    tokenizer = root / "artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0"
    suffix = "_" + args.difficulty if args.difficulty else ""
    numeric_dir = root / f"artifacts/data/audits/terminal_lengths_20261016_sample{args.samples_per_file}{suffix}"
    numeric_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(source_root.rglob("*.parquet"), key=lambda p: ("mixed" not in p.parts, str(p)))
    if args.difficulty:
        paths = [p for p in paths if args.difficulty in p.parts]
    started = time.monotonic()
    files = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context("spawn"),
                             initializer=init_worker, initargs=(str(tokenizer),)) as pool:
        pending = [pool.submit(audit_file, (str(p), source_root, str(numeric_dir), args.samples_per_file)) for p in paths]
        for future in as_completed(pending):
            file = future.result()
            files.append(file)
            print(json.dumps({"progress_files": len(files), "sample_n": file["sample_n"],
                              "source_file": file["source_file"], "seconds": round(file["seconds"], 2)}), flush=True)
    groups = aggregate(files)
    import importlib.metadata
    result = {"source_revision": "a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9",
              "tokenizer_revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
              "chat_template_sha256": hashlib.sha256((tokenizer / "chat_template.jinja").read_bytes()).hexdigest(),
              "packages": {k: importlib.metadata.version(k) for k in ("transformers", "tokenizers", "pyarrow")},
              "sampling": "all rows" if not args.samples_per_file else "deterministic evenly spaced rows including file endpoints; N/n weighting per file",
              "samples_per_file": args.samples_per_file, "workers": args.workers,
              "difficulty_filter": args.difficulty,
              "seconds_total": time.monotonic() - started,
              "modes": {"raw": "source content and Qwen chat: enable_thinking=true,preserve_thinking=true",
                        "clean": "remove explicit leading paired assistant think blocks; preserve Terminus JSON analysis/plan; Qwen chat enable_thinking=false,preserve_thinking=false"},
              "conservative_headroom": {"32768_context_4096_output": "clean_chat_total <= 28672",
                                        "32768_context_8192_output": "clean_chat_total <= 24576",
                                        "caveat": "Sufficient conservative whole-record proxy, not exact prefix peak: includes the stored final assistant output and then reserves the full next output again."},
              "caveat": "Counts concatenate complete stored record, not maximum real prompt window after context compaction. Sample max_observed is not population maximum. Weighted estimates are not confidence intervals or accepted training samples.",
              "groups": groups, "files": sorted(files, key=lambda x: x["source_file"])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": True, "output": str(args.output), "seconds": result["seconds_total"],
                      "all_sample_n": groups["all"]["sample_rows"]}), flush=True)


if __name__ == "__main__":
    main()
