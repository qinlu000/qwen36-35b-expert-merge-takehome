#!/usr/bin/env python3
"""Measure every exported episode and complete user/assistant unit, with the real base tokenizer."""
import os
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer
from transformers.utils.chat_template_utils import _compile_jinja_template

MODEL_REV = "995ad96eacd98c81ed38be0c5b274b04031597b0"


def dist(values):
    values = sorted(values)
    return {"n": len(values), "sum": sum(values), "mean": sum(values) / len(values),
            "p50": values[(len(values) - 1) // 2], "p95": values[int((len(values) - 1) * .95)],
            "max": values[-1], "within_8192": sum(x <= 8192 for x in values),
            "within_16384": sum(x <= 16384 for x in values),
            "within_65536": sum(x <= 65536 for x in values)} if values else {"n": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--messages-dir", default="messages_v2")
    ap.add_argument("--reuse-length-rows", type=Path)
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    source = base / args.messages_dir
    tokenizer_file = args.root / "artifacts/models/base_metadata" / MODEL_REV / "tokenizer.json"
    tokenizer = Tokenizer.from_file(str(tokenizer_file)); tokenizer.no_truncation(); tokenizer.no_padding()
    template_file = args.root / "analysis/source_snapshots/model_chat_template.jinja"
    template = _compile_jinja_template(template_file.read_text())
    def length(messages):
        rendered = template.render(messages=messages, tools=None, add_generation_prompt=False,
                                   enable_thinking=False, preserve_thinking=False)
        return len(tokenizer.encode(rendered, add_special_tokens=False).ids)
    def measure(split, row):
        messages = row["messages"]
        bodies = [len(tokenizer.encode(m["content"], add_special_tokens=False).ids)
                  for m in messages if m["role"] == "assistant"]
        units = []
        for i in range(0, len(messages), 2):
            pair = messages[i:i + 2]
            assert [m["role"] for m in pair] == ["user", "assistant"]
            units.append(length(([messages[0]] if i else []) + pair))
        return {"split": split, "task_id": row["task_id"], "family_key": row["family_key"],
                "source_row_index": row["source_row_index"], "full_sequence_tokens": length(messages),
                "assistant_content_tokens": sum(bodies), "assistant_message_lengths": bodies,
                "complete_unit_with_instruction_lengths": units}
    pending, measured, reused = [], [], 0
    cache = {}
    if args.reuse_length_rows:
        prior = json.load(open(args.reuse_length_rows.parent / "length_summary.json"))
        assert prior["tokenizer_sha256"] == hashlib.sha256(tokenizer_file.read_bytes()).hexdigest()
        assert prior["template_sha256"] == hashlib.sha256(template_file.read_bytes()).hexdigest()
        cache = {x["task_id"]: x for x in map(json.loads, args.reuse_length_rows.open())}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for split in ("train", "val"):
            for row in map(json.loads, (source / f"{split}.messages.jsonl").open()):
                old = cache.get(row["task_id"])
                if old and old["split"] == split and old["source_row_index"] == row["source_row_index"]:
                    measured.append(old); reused += 1
                else:
                    pending.append(pool.submit(measure, split, row))
        for future in as_completed(pending):
            measured.append(future.result())
            if len(measured) % 50 == 0:
                print(json.dumps({"episodes_measured": len(measured), "expected": len(pending) + reused}), flush=True)
    measured.sort(key=lambda x: (x["split"], x["task_id"]))
    (source / "length_rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in measured))
    stats = {}
    for split in ("train", "val"):
        rows = [x for x in measured if x["split"] == split]
        stats[split] = {"complete_sequence": dist([x["full_sequence_tokens"] for x in rows]),
                        "assistant_content_total_by_episode": dist([x["assistant_content_tokens"] for x in rows]),
                        "assistant_message": dist([n for x in rows for n in x["assistant_message_lengths"]]),
                        "complete_unit_with_initial_instruction": dist([n for x in rows for n in x["complete_unit_with_instruction_lengths"]])}
    summary = {"all_exported_episodes_measured": True, "messages_dir": str(source), "stats": stats,
               "reused_identical_source_row_measurements": reused,
               "tokenizer_sha256": hashlib.sha256(tokenizer_file.read_bytes()).hexdigest(),
               "template_sha256": hashlib.sha256(template_file.read_bytes()).hexdigest(),
               "unit_definition": "One complete user/assistant pair, retaining the original initial instruction user as prefix for later pairs. No turn or response truncation.",
               "not_training_processed_tokens": "Actual complete-turn windows can combine units and repeat prefixes; root ms-swift labels/window audit remains authoritative.",
               "no_gpu_or_model_calls": True}
    (source / "length_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
