#!/usr/bin/env python3
"""Static family join, native Terminus parser and bounded real-token audit."""
import os
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
    os.environ[name] = "false" if name == "TOKENIZERS_PARALLELISM" else "1"

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from tokenizers import Tokenizer
from transformers.utils.chat_template_utils import _compile_jinja_template

from candidate_selection import family_rank, text_hash

MODEL_REV = "995ad96eacd98c81ed38be0c5b274b04031597b0"


def distribution(values):
    values = sorted(values)
    return {"n": len(values), "mean": sum(values) / len(values),
            "p50": values[(len(values) - 1) // 2], "p95": values[int((len(values) - 1) * .95)],
            "max": values[-1], "within_65536": sum(x <= 65536 for x in values)} if values else {"n": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--input", type=Path)
    ap.add_argument("--prefix", action="store_true", help="Permit one incomplete final JSONL line; never call it full-file validation")
    ap.add_argument("--tokenize", type=int, default=128)
    args = ap.parse_args()
    root = args.root
    base = root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    source = args.input or base / "traces/data/TerminalHorizon-3K-SFT.jsonl"
    out = base / ("prefix_inspection" if args.prefix else "inspection")
    out.mkdir(parents=True, exist_ok=True)
    envs = [json.loads(line) for line in (base / "environment_metadata.jsonl").open()]
    by_hash = defaultdict(list)
    for task in envs:
        by_hash[text_hash(task["instruction"])].append(task["task_id"])
    formal = json.load(open(root / "artifacts/data/audits/formal_input_fingerprints_20261016/index.json"))["terminal_instruction_sha256"]
    parser_file = root / "artifacts/benchmarks/harbor/src/harbor/agents/terminus_2/terminus_json_plain_parser.py"
    spec = importlib.util.spec_from_file_location("horizon_native_parser", parser_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parser = module.TerminusJSONPlainParser()
    tokenizer_file = root / "artifacts/models/base_metadata" / MODEL_REV / "tokenizer.json"
    tokenizer = Tokenizer.from_file(str(tokenizer_file)); tokenizer.no_truncation(); tokenizer.no_padding()
    template_file = root / "analysis/source_snapshots/model_chat_template.jinja"
    template = _compile_jinja_template(template_file.read_text())
    records, stats, task_rows = [], Counter(), Counter()
    selected = []
    for row_index, line in enumerate(source.open()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if args.prefix:
                stats["incomplete_final_line"] += 1
                break
            raise
        conv = row["conversations"]
        first = conv[0]["content"] if conv else ""
        instruction = first.split("Task Description:\n", 1)[-1].rsplit("\n\nCurrent terminal state:\n", 1)[0]
        ih = text_hash(instruction)
        task_ids = by_hash[ih]
        task_rows.update(task_ids)
        clean, errors, complete, think_count, malformed = [], [], False, 0, []
        final_assistant_complete = False
        role_chain_valid = all(msg["role"] == ("user" if turn % 2 == 0 else "assistant")
                               for turn, msg in enumerate(conv)) and bool(conv) and conv[-1]["role"] == "assistant"
        for turn, msg in enumerate(conv):
            content = msg["content"]
            if msg["role"] == "assistant":
                if content.lstrip().startswith("<think>"):
                    match = re.match(r"\A\s*<think>.*?</think>\s*", content, re.S)
                    if match:
                        content = content[match.end():]; think_count += 1
                    else:
                        malformed.append(turn)
                parsed = parser.parse_response(content)
                if parsed.error:
                    errors.append(turn)
                complete |= bool(parsed.is_task_complete and not parsed.error)
                final_assistant_complete = bool(parsed.is_task_complete and not parsed.error)
            clean.append({"role": msg["role"], "content": content})
        record = {"row_index": row_index, "instruction_sha256": ih, "task_ids": task_ids,
                  "turns": len(conv), "assistant_turns": sum(m["role"] == "assistant" for m in conv),
                  "leading_think_cleaned": think_count, "malformed_think_turns": malformed,
                  "native_parser_error_turns": errors, "any_task_complete_proxy": complete,
                  "final_task_complete_proxy": final_assistant_complete, "role_chain_valid": role_chain_valid,
                  "initial_contract_sha256": hashlib.sha256(first.split("Task Description:\n", 1)[0].encode()).hexdigest(),
                  "formal_exact_hits": formal.get(ih, []), "source_reward_known": False,
                  "training_released": False,
                  "hold_reasons": ["per_row_success_unknown", "task_environment_not_locally_validated",
                                   "family_lineage_and_near_duplicate_review_pending", "category_review_pending"]}
        if len(task_ids) != 1: record["hold_reasons"].append("environment_join_not_unique")
        if malformed: record["hold_reasons"].append("malformed_think")
        if errors: record["hold_reasons"].append("recoverable_or_final_protocol_errors_need_review")
        if not role_chain_valid: record["hold_reasons"].append("unexpected_role_chain")
        if formal.get(ih): record["hold_reasons"].append("formal_exact_contamination")
        records.append(record)
        stats["rows"] += 1; stats["unique_environment_join_rows"] += len(task_ids) == 1
        stats["parser_error_rows"] += bool(errors); stats["parser_error_messages"] += len(errors)
        stats["malformed_think_rows"] += bool(malformed); stats["leading_think_cleaned_messages"] += think_count
        stats["any_completion_proxy_rows"] += complete
        stats["final_completion_proxy_rows"] += final_assistant_complete
        stats["invalid_role_chain_rows"] += not role_chain_valid
        stats["formal_exact_hit_rows"] += bool(formal.get(ih))
        rank = family_rank("terminal-horizon-row:" + str(row_index))
        selected.append((rank, row_index, clean, conv))
        selected.sort(key=lambda x: x[0])
        if len(selected) > args.tokenize: selected.pop()
    with (out / "row_index.jsonl").open("w") as stream:
        for row in records: stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    token_records = []
    for _, row_index, clean, raw in selected:
        rendered = template.render(messages=clean, tools=None, add_generation_prompt=False,
                                   enable_thinking=False, preserve_thinking=False)
        body_lengths = [len(tokenizer.encode(m["content"], add_special_tokens=False).ids)
                        for m in clean if m["role"] == "assistant"]
        original = template.render(messages=raw, tools=None, add_generation_prompt=False,
                                   enable_thinking=False, preserve_thinking=True)
        token_records.append({"row_index": row_index,
                              "clean_complete_sequence_tokens": len(tokenizer.encode(rendered, add_special_tokens=False).ids),
                              "raw_complete_sequence_tokens": len(tokenizer.encode(original, add_special_tokens=False).ids),
                              "clean_assistant_content_tokens": sum(body_lengths),
                              "max_assistant_message_tokens": max(body_lengths, default=0)})
    (out / "token_rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in token_records))
    summary = {"input": str(source), "prefix_only": args.prefix, "counts": dict(stats),
               "environment_task_ids_with_traces": len(task_rows), "rows_per_task": dict(Counter(task_rows.values())),
               "full_sequence_clean_tokens": distribution([x["clean_complete_sequence_tokens"] for x in token_records]),
               "full_sequence_raw_tokens": distribution([x["raw_complete_sequence_tokens"] for x in token_records]),
               "assistant_content_tokens": distribution([x["clean_assistant_content_tokens"] for x in token_records]),
               "max_per_call_tokens": distribution([x["max_assistant_message_tokens"] for x in token_records]),
               "token_sample": "Deterministic hash-ranked row sample of available complete rows; prefix inputs remain nonrepresentative",
               "tokenizer_sha256": hashlib.sha256(tokenizer_file.read_bytes()).hexdigest(),
               "template_sha256": hashlib.sha256(template_file.read_bytes()).hexdigest(),
               "native_parser_sha256": hashlib.sha256(parser_file.read_bytes()).hexdigest(),
               "length_note": "Complete sequences include instructions/tool observations/template, not just assistant bodies. Body lengths are not ms-swift labels/processed tokens. Required JSON analysis/plan preserved.",
               "execution": "Static parsing/tokenization only; no trajectory command, reference/verifier, container, GPU or formal benchmark executed."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
