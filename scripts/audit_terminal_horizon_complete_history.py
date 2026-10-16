#!/usr/bin/env python3
"""Census complete train-pool episodes and 64K supply; does not select/export training data."""
import os
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path
import re

from tokenizers import Tokenizer
from transformers.utils.chat_template_utils import _compile_jinja_template

MODEL_REV = "995ad96eacd98c81ed38be0c5b274b04031597b0"
TOKENIZER = TEMPLATE = None


def initialize(root):
    global TOKENIZER, TEMPLATE
    TOKENIZER = Tokenizer.from_file(str(Path(root) / "artifacts/models/base_metadata" / MODEL_REV / "tokenizer.json"))
    TOKENIZER.no_truncation(); TOKENIZER.no_padding()
    TEMPLATE = _compile_jinja_template((Path(root) / "analysis/source_snapshots/model_chat_template.jinja").read_text())


def measure(row_index, messages):
    rendered = TEMPLATE.render(messages=messages, tools=None, add_generation_prompt=False,
                               enable_thinking=False, preserve_thinking=False)
    over_output, strict_errors, residual_tags = 0, 0, 0
    for msg in messages:
        if msg["role"] != "assistant": continue
        text = msg["content"]
        try: json.loads(text)
        except json.JSONDecodeError: strict_errors += 1
        residual_tags += "<think>" in text or "</think>" in text
        # UTF-8 bytes bound token count from above; tokenize only potential >8K messages.
        if len(text.encode()) > 8192:
            over_output += len(TOKENIZER.encode(text, add_special_tokens=False).ids) > 8192
    return {"row_index": row_index, "full_sequence_tokens": len(TOKENIZER.encode(rendered, add_special_tokens=False).ids),
            "assistant_outputs_over8192": over_output, "strict_json_errors": strict_errors,
            "residual_think_tag_messages": residual_tags, "assistant_turns": len(messages) // 2}


def dist(values):
    values = sorted(values)
    return {"n": len(values), "sum": sum(values), "mean": sum(values) / len(values),
            "p50": values[(len(values) - 1) // 2], "p95": values[int((len(values) - 1) * .95)],
            "max": values[-1]} if values else {"n": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    root = args.root
    base = root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    out = base / "complete_history_64k_audit"
    out.mkdir(parents=True, exist_ok=True)
    pool = {x["task_id"]: x for x in map(json.loads, (base / "proportional_candidates/train_pool.provisional.jsonl").open())}
    source_index = {x["row_index"]: x for x in map(json.loads, (base / "inspection/row_index.jsonl").open())}
    eligible = {i: row for i, row in source_index.items() if len(row["task_ids"]) == 1
                and row["task_ids"][0] in pool and row["role_chain_valid"] and row["final_task_complete_proxy"]
                and not row["native_parser_error_turns"] and not row["malformed_think_turns"] and not row["formal_exact_hits"]}
    cache_path = out / "trace_length_census.jsonl"
    metrics = {x["row_index"]: x for x in map(json.loads, cache_path.open())} if cache_path.exists() else {}
    shared = {}
    for folder in ("messages_v2", "messages_v3"):
        for row in map(json.loads, (base / folder / "length_rows.jsonl").open()):
            shared[row["source_row_index"]] = row
    cached_count = sum(i in metrics for i in eligible)
    print(json.dumps({"eligible_train_pool_episodes": len(eligible), "train_pool_task_families": len(pool),
                      "already_censused": cached_count, "affinity": sorted(os.sched_getaffinity(0))}), flush=True)
    futures = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context("spawn"),
                             initializer=initialize, initargs=(str(root),)) as executor:
        for i, line in enumerate((base / "traces/data/TerminalHorizon-3K-SFT.jsonl").open()):
            if i not in eligible or i in metrics: continue
            raw = json.loads(line)["conversations"]
            messages = []
            for msg in raw:
                text = msg["content"]
                if msg["role"] == "assistant" and text.lstrip().startswith("<think>"):
                    text = text[re.match(r"\A\s*<think>.*?</think>\s*", text, re.S).end():]
                messages.append({"role": msg["role"], "content": text})
            if i in shared:
                old = shared[i]
                strict = 0
                for msg in messages:
                    if msg["role"] == "assistant":
                        try: json.loads(msg["content"])
                        except json.JSONDecodeError: strict += 1
                result = {"row_index": i, "full_sequence_tokens": old["full_sequence_tokens"],
                          "assistant_outputs_over8192": sum(n > 8192 for n in old["assistant_message_lengths"]),
                          "strict_json_errors": strict,
                          "residual_think_tag_messages": sum(m["role"] == "assistant" and ("<think>" in m["content"] or "</think>" in m["content"]) for m in messages),
                          "assistant_turns": len(messages) // 2}
                metrics[i] = result
                with cache_path.open("a") as stream: stream.write(json.dumps(result) + "\n")
            else:
                futures.append(executor.submit(measure, i, messages))
        for future in as_completed(futures):
            result = future.result(); metrics[result["row_index"]] = result
            with cache_path.open("a") as stream: stream.write(json.dumps(result) + "\n")
            if len(metrics) % 100 == 0:
                print(json.dumps({"episodes_measured": len(metrics), "expected": len(eligible)}), flush=True)
    assert all(i in metrics for i in eligible)
    by_task = defaultdict(list)
    all_rows = []
    for i, check in eligible.items():
        task_id = check["task_ids"][0]
        record = {**metrics[i], "task_id": task_id, "category": pool[task_id]["category"],
                  "family_key": pool[task_id]["family_key"], "source_category": pool[task_id]["source_category"],
                  "source_subcategory": pool[task_id]["source_subcategory"]}
        all_rows.append(record)
        if not record["strict_json_errors"] and not record["residual_think_tag_messages"]:
            by_task[task_id].append(record)
    short = {task_id: [x for x in rows if x["full_sequence_tokens"] <= 65536] for task_id, rows in by_task.items()}
    short = {k: v for k, v in short.items() if v}
    original = list(map(json.loads, (base / "messages_v3/train.messages.jsonl").open()))
    original_by_cat = defaultdict(list)
    for row in original: original_by_cat[row["category"]].append(row)
    quotas = json.load(open(base / "proportional_candidates/summary.json"))["train_quota"]
    per_category = {}
    for category in quotas:
        families = {task_id: rows for task_id, rows in by_task.items() if pool[task_id]["category"] == category}
        available = {task_id: rows for task_id, rows in short.items() if pool[task_id]["category"] == category}
        current = original_by_cat[category]
        current_fits = sum(metrics[row["source_row_index"]]["full_sequence_tokens"] <= 65536 for row in current)
        same_task = sum(row["task_id"] in available for row in current)
        desired = len(current)
        strict_output = sum(any(x["assistant_outputs_over8192"] == 0 for x in rows) for rows in available.values())
        per_category[category] = {
            "current_v3_tasks": desired, "current_v3_selected_episodes_le64k": current_fits,
            "current_v3_tasks_with_any_valid_episode_le64k": same_task,
            "same_task_alternate_rollout_rescues": same_task - current_fits,
            "available_valid_complete64k_task_families": len(available),
            "available_complete64k_families_also_all_outputs_le8k": strict_output,
            "possible_same_category_new_family_replacements": min(desired - same_task, len(available) - same_task),
            "max_fulfillable_preserving_current_class_count": min(desired, len(available)),
            "gap_preserving_current_class_count": max(0, desired - len(available)),
            "original_500_quota": quotas[category], "max_fulfillable_original_500_quota": min(quotas[category], len(available)),
            "all_valid_family_min_episode_lengths": dist([min(x["full_sequence_tokens"] for x in rows) for rows in families.values()]),
            "short_valid_family_min_episode_lengths": dist([min(x["full_sequence_tokens"] for x in rows) for rows in available.values()]),
            "current_v3_episode_lengths": dist([metrics[x["source_row_index"]]["full_sequence_tokens"] for x in current]),
            "current_v3_assistant_turns": dist([metrics[x["source_row_index"]]["assistant_turns"] for x in current]),
            "short_pool_family_min_assistant_turns": dist([min(x["assistant_turns"] for x in rows) for rows in available.values()])}
    supply_rows = [{"task_id": task_id, "category": pool[task_id]["category"], "family_key": pool[task_id]["family_key"],
                    "source_category": pool[task_id]["source_category"], "source_subcategory": pool[task_id]["source_subcategory"],
                    "valid_source_episodes": rows, "complete64k_source_row_indices": [x["row_index"] for x in short.get(task_id, [])]}
                   for task_id, rows in sorted(by_task.items())]
    (out / "task_supply.jsonl").write_text("".join(json.dumps(x) + "\n" for x in supply_rows))
    summary = {"train_pool_families": len(pool), "native_qualified_complete_episodes_measured": len(eligible),
               "all_requested_lengths_measured": True, "whole_source_lfs_sha256": "285c8c673563cce2d7ff49367f0fb8bef429aaacaf143241181158fb87fded76",
               "strict_json_or_residual_tag_rejected_episodes": sum(bool(x["strict_json_errors"] or x["residual_think_tag_messages"]) for x in all_rows),
               "valid_train_pool_task_families": len(by_task), "families_with_valid_complete_episode_le64k": len(short),
               "per_category": per_category,
               "current_v3_tasks_with_any_valid_episode_le64k": sum(x["current_v3_tasks_with_any_valid_episode_le64k"] for x in per_category.values()),
               "same_task_alternate_rollout_rescues": sum(x["same_task_alternate_rollout_rescues"] for x in per_category.values()),
               "max_fulfillable_preserving_current_class_counts": sum(x["max_fulfillable_preserving_current_class_count"] for x in per_category.values()),
               "remaining_gap_preserving_current_class_counts": sum(x["gap_preserving_current_class_count"] for x in per_category.values()),
               "max_fulfillable_original_500_quotas": sum(x["max_fulfillable_original_500_quota"] for x in per_category.values()),
               "original_v3_source_domain_counts": dict(Counter(pool[x["task_id"]]["source_category"] for x in original)),
               "available_complete64k_source_domain_counts": dict(Counter(pool[x]["source_category"] for x in short)),
               "artifact_scope": "Availability and length-bias statistics only. Frozen val99 and messages_v3 untouched. No training samples/windows selected or emitted, no GPU/model/API use.",
               "quality_limit": "Publisher process-filtered, native parse valid and completion proxy true; no independent success label. Original source family-lineage limitations remain.",
               "length_bias": "64K threshold selects shorter executions even inside a fixed task class; alternate rollout rescues preserve task identity, cross-family substitution can change difficulty/domain/stage depth. A supply count does not establish equivalent task distribution."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_category", "original_v3_source_domain_counts", "available_complete64k_source_domain_counts")}, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
