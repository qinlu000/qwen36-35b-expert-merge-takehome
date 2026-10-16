#!/usr/bin/env python3
"""Capacity statistics only: never writes training windows or modifies the training loader."""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import argparse
from collections import defaultdict
import json
from pathlib import Path

from tokenizers import Tokenizer
from transformers.utils.chat_template_utils import _compile_jinja_template

MODEL_REV = "995ad96eacd98c81ed38be0c5b274b04031597b0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016/messages_v3"
    measured = {x["task_id"]: x for x in map(json.loads, (base / "length_rows.jsonl").open())}
    tokenizer = Tokenizer.from_file(str(args.root / "artifacts/models/base_metadata" / MODEL_REV / "tokenizer.json"))
    template = _compile_jinja_template((args.root / "analysis/source_snapshots/model_chat_template.jinja").read_text())
    aggregate, per_task, rejected = {}, [], []
    for split in ("train", "val"):
        aggregate[split] = {}
        for budget in (16384, 32768, 65536):
            aggregate[split][str(budget)] = defaultdict(int)
        for row in map(json.loads, (base / f"{split}.messages.jsonl").open()):
            lengths = measured[row["task_id"]]
            units = lengths["complete_unit_with_instruction_lengths"]
            bodies = lengths["assistant_message_lengths"]
            prefix = template.render(messages=[row["messages"][0]], tools=None, add_generation_prompt=False,
                                     enable_thinking=False, preserve_thinking=False)
            prefix_tokens = len(tokenizer.encode(prefix, add_special_tokens=False).ids)
            # The frozen Qwen template adds 4 empty-think wrapper tokens to the final assistant only.
            # Validate exact additivity against every already-measured full episode before counting.
            reconstructed = sum(units) - (len(units) - 1) * (prefix_tokens + 4)
            assert reconstructed == lengths["full_sequence_tokens"]
            for budget in (16384, 32768, 65536):
                stats = aggregate[split][str(budget)]
                stats["episodes"] += 1
                stats["episodes_fitting_single_window"] += lengths["full_sequence_tokens"] <= budget
                stats["source_units"] += len(units)
                stats["source_assistant_content_tokens"] += sum(bodies)
                open_tokens, chunk_count, first_unit = 0, 0, None
                task_window_tokens, kept, lost = 0, 0, 0
                def close_chunk():
                    nonlocal open_tokens, chunk_count, first_unit, task_window_tokens
                    if not open_tokens: return
                    chunk_count += 1
                    task_window_tokens += open_tokens
                    stats["windows_lacking_earlier_source_history"] += first_unit != 0
                    open_tokens, first_unit = 0, None
                for index, unit_tokens in enumerate(units):
                    if unit_tokens > budget:
                        close_chunk()
                        lost += 1
                        rejected.append({"split": split, "task_id": row["task_id"], "budget": budget,
                                         "unit_index": index, "source_user_turn": 2 * index,
                                         "unit_tokens_with_initial_instruction": unit_tokens,
                                         "assistant_content_tokens": bodies[index],
                                         "reason": "one_complete_pair_plus_retained_instruction_exceeds_capacity"})
                        continue
                    incremental = unit_tokens - prefix_tokens - 4
                    if open_tokens and open_tokens + incremental > budget: close_chunk()
                    if not open_tokens:
                        open_tokens, first_unit = unit_tokens, index
                    else:
                        open_tokens += incremental
                    kept += 1
                    stats["retained_assistant_content_tokens"] += bodies[index]
                close_chunk()
                stats["window_count"] += chunk_count
                stats["total_window_tokens"] += task_window_tokens
                stats["retained_units"] += kept
                stats["unrepresentable_complete_units"] += lost
                stats["episodes_with_no_unit_omitted"] += lost == 0
                per_task.append({"split": split, "task_id": row["task_id"], "budget": budget,
                                 "window_count": chunk_count, "total_window_tokens": task_window_tokens,
                                 "complete_units_kept": kept, "complete_units_unrepresentable": lost,
                                 "original_full_episode_tokens": lengths["full_sequence_tokens"]})
        for stats in aggregate[split].values():
            stats["unit_coverage"] = stats["retained_units"] / stats["source_units"]
            stats["assistant_content_token_coverage"] = stats["retained_assistant_content_tokens"] / stats["source_assistant_content_tokens"]
    summary = {"capacity_only_no_training_windows_emitted": True, "template_additivity_checked_all_episodes": len(measured),
               "policy_assessed": "Non-overlapping consecutive complete user/assistant pairs; repeat original initial user in later windows; no summary/history carry; omit a whole unit only if it cannot fit alone. This is an accounting scenario, not the selected training policy.",
               "history_limitation": "Any later window lacks earlier execution history and may depend on files/state/actions absent from its text. Unit coverage is not semantic sufficiency or complete trajectory preservation.",
               "evaluation_context": "Frozen evaluation remains 65536 total / 8192 per call. Training capacity scenarios do not change it.",
               "statistics": {k: {b: dict(v) for b, v in values.items()} for k, values in aggregate.items()},
               "unrepresentable_units": rejected,
               "cost_note": "Totals include repeated instruction and template; exclude padding, batch packing and alternative carry/overlap strategies. Actual root ms-swift loader accounting is authoritative."}
    (base / "window_capacity_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (base / "window_capacity_per_task.jsonl").write_text("".join(json.dumps(x) + "\n" for x in per_task))
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
