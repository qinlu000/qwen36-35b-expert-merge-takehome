#!/usr/bin/env python3
"""Export untruncated standard messages after complete native-protocol structural checks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from candidate_selection import family_rank

REV = "45f1e98e317d3639437f0eb02f4e8bc5825732f3"
EXPECTED_SHA = "285c8c673563cce2d7ff49367f0fb8bef429aaacaf143241181158fb87fded76"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--refill-train", action="store_true")
    ap.add_argument("--output-name", default="messages_v1")
    ap.add_argument("--require-final-completion", action="store_true")
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    source = base / "traces/data/TerminalHorizon-3K-SFT.jsonl"
    assert digest(source) == EXPECTED_SHA
    rows = [json.loads(line) for line in (base / "inspection/row_index.jsonl").open()]
    by_task = defaultdict(list)
    for row in rows:
        if len(row["task_ids"]) == 1: by_task[row["task_ids"][0]].append(row)
    selection, dropped, selected_rows = {}, [], {}
    for split in ("train", "val"):
        candidate_file = ("train_pool.provisional.jsonl" if split == "train" and args.refill_train
                          else f"{split}_tasks.provisional.jsonl")
        candidates = [json.loads(line) for line in (base / "proportional_candidates" / candidate_file).open()]
        quotas = json.load(open(base / "proportional_candidates/summary.json"))[split + "_quota"]
        selected_category_counts = Counter()
        for task in candidates:
            if selected_category_counts[task["category"]] >= quotas[task["category"]]: continue
            valid = [row for row in by_task[task["task_id"]] if row["role_chain_valid"]
                     and not row["malformed_think_turns"] and not row["native_parser_error_turns"]
                     and not row["formal_exact_hits"]]
            if args.require_final_completion:
                valid = [row for row in valid if row["final_task_complete_proxy"]]
            if not valid:
                dropped.append({"split": split, "task_id": task["task_id"], "category": task["category"],
                                "reason": "no_complete_structurally_valid_source_trace",
                                "source_rows": [row["row_index"] for row in by_task[task["task_id"]]]})
                continue
            valid.sort(key=lambda row: (not row["final_task_complete_proxy"],
                                        family_rank(f"horizon-row:{row['row_index']}")))
            chosen = valid[0]
            selection[chosen["row_index"]] = (split, task, chosen)
            selected_rows[task["task_id"]] = chosen["row_index"]
            selected_category_counts[task["category"]] += 1
    assert len(selected_rows) == len(selection)
    out = base / args.output_name
    out.mkdir(parents=True, exist_ok=True)
    files = {split: (out / f"{split}.messages.jsonl").open("w") for split in ("train", "val")}
    counts, categories, contracts = Counter(), defaultdict(Counter), Counter()
    for row_index, line in enumerate(source.open()):
        if row_index not in selection: continue
        split, task, check = selection[row_index]
        raw = json.loads(line)["conversations"]
        messages = []
        for msg in raw:
            text = msg["content"]
            if msg["role"] == "assistant" and text.lstrip().startswith("<think>"):
                match = re.match(r"\A\s*<think>.*?</think>\s*", text, re.S)
                assert match is not None
                text = text[match.end():]
            messages.append({"role": msg["role"], "content": text})
        assert [m for m in raw if m["role"] == "user"] == [m for m in messages if m["role"] == "user"]
        record = {"id": "terminal_horizon:" + task["task_id"], "domain": "terminal", "messages": messages,
                  "tools": [], "task_id": task["task_id"], "category": task["category"],
                  "family_key": task["family_key"], "source_row_index": row_index,
                  "source": "shunzou05/TerminalHorizon-3K", "source_revision": REV,
                  "source_quality": "author_luna_process_filtered_not_success_only",
                  "source_reward": None, "teacher": "DeepSeek-V4-Pro-0813 (publisher declared)",
                  "harness": "Terminus2 (publisher declared; native parser compatible)",
                  "final_task_complete_proxy": check["final_task_complete_proxy"],
                  "success_verified": False, "native_environment_validated_locally": False,
                  "export_status": "complete_structurally_valid_messages_for_cpu_loader",
                  "training_window_status": "untruncated_source; root complete-turn window audit required"}
        files[split].write(json.dumps(record, ensure_ascii=False) + "\n")
        counts[split] += 1; categories[split][task["category"]] += 1
        counts[split + "_assistant_messages"] += sum(m["role"] == "assistant" for m in messages)
        counts[split + "_final_completion_proxy"] += check["final_task_complete_proxy"]
        contracts[check["initial_contract_sha256"]] += 1
    for stream in files.values(): stream.close()
    (out / "dropped_tasks.jsonl").write_text("".join(json.dumps(x) + "\n" for x in dropped))
    (out / "source_row_selection.json").write_text(json.dumps(selected_rows, indent=2) + "\n")
    summary = {"source_sha256": EXPECTED_SHA, "counts": dict(counts), "categories": {k: dict(v) for k, v in categories.items()},
               "dropped_tasks": dropped, "initial_contract_hashes": dict(contracts),
               "artifacts": {split: {"path": str(out / f"{split}.messages.jsonl"),
                                     "sha256": digest(out / f"{split}.messages.jsonl"),
                                     "bytes": (out / f"{split}.messages.jsonl").stat().st_size} for split in ("train", "val")},
               "quality_basis": "Apache-2.0 source; publisher full-trajectory process review; exact environment join, alternating roles, balanced think strip and native JSON parser pass locally. No independent task-success label.",
               "native_grader_success_verified": False, "executable_val_ready": False,
               "require_final_completion_proxy": args.require_final_completion,
               "val_note": "val messages can support held-out teacher-trace loss only; task-success val requires original environment/verifier runtime acceptance.",
               "long_sequences": "Every exported source episode is complete. No sequence/assistant truncation or short-sample selection. CPU windowing and labels still required before formal SFT.",
               "loss_contract": "Only assistant content may be supervised; user/observations masked. Hidden leading think removed, required visible Terminus JSON analysis/plan/commands preserved. No structured tool calls; tools=[] and terminal observations are user messages."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
