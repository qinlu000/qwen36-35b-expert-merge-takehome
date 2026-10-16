#!/usr/bin/env python3
"""Bounded static audit of pinned new Terminal candidates; metadata reserves only."""
import os
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"):
    os.environ[name] = "1"

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from candidate_selection import family_partition, family_rank, text_hash, proportional_quotas, SPLIT_SEED

pa.set_cpu_count(1)
pa.set_io_thread_count(1)
REPO = "open-thoughts/OpenThoughts-Agent-SFT-100K"
REV = "45fb28fcc38d352133cb28a1c8a43a2f14fea97b"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strip_think(text):
    while match := re.match(r"^\s*<think>.*?</think>\s*", text, re.S):
        text = text[match.end():]
    return text


def read_range(session, url, start, end, size, counts):
    response = session.get(url, headers={"Range": f"bytes={start}-{end}"}, stream=True, timeout=60)
    if response.status_code != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{size}":
        response.close()
        raise ValueError("Expected exact bounded HTTP range")
    data = response.content
    response.close()
    if len(data) != end - start + 1:
        raise ValueError("Incomplete bounded HTTP range")
    counts["range_requests"] += 1
    counts["bytes"] += len(data)
    return data


def metadata_file(session, root, info, out, network):
    path, size = info["rfilename"], info["size"]
    target = out / (Path(path).stem + ".metadata_sparse.parquet")
    receipt = target.with_suffix(".receipt.json")
    if receipt.exists():
        return target, json.load(open(receipt))
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REV}/{path}"
    footer_start = max(0, size - 65536)
    footer = read_range(session, url, footer_start, size - 1, size, network)
    with target.open("wb") as stream:
        stream.seek(footer_start)
        stream.write(footer)
    pf = pq.ParquetFile(target)
    ranges = []
    for index in range(pf.num_row_groups):
        group = pf.metadata.row_group(index)
        columns = [group.column(i) for i in range(group.num_columns)
                   if not group.column(i).path_in_schema.startswith("conversations.")]
        for column in columns:
            start = column.dictionary_page_offset
            if start is None or start < 0:
                start = column.data_page_offset
            ranges.append([start, start + column.total_compressed_size - 1])
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1] + 4096:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    with target.open("r+b") as stream:
        for start, end in merged:
            data = read_range(session, url, start, end, size, network)
            stream.seek(start)
            stream.write(data)
    result = {"path": path, "revision": REV, "logical_size": size,
              "download_scope": "Sparse footer and non-conversation column chunks only; not a complete shard or LFS hash verification",
              "footer_sha256": sha(footer), "ranges": merged,
              "fetched_bytes": len(footer) + sum(b - a + 1 for a, b in merged),
              "rows": pf.metadata.num_rows, "schema": str(pf.schema_arrow)}
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    return target, result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--proxy", default="http://127.0.0.1:38080")
    ap.add_argument("--body-row-groups", type=int, default=3)
    args = ap.parse_args()
    root = args.root.resolve()
    base = root / "artifacts/data/candidates/new_terminal_20261016"
    raw = base / "raw"
    sparse = raw / "metadata_sparse"
    sparse.mkdir(parents=True, exist_ok=True)
    api = json.load(open(raw / "ot100k_api.json"))
    network, metadata_counts = Counter(), defaultdict(Counter)
    session = requests.Session()
    session.proxies = {"https": args.proxy, "http": args.proxy}
    records, receipts = [], []
    start_time = time.monotonic()
    # Metadata from all shards prevents an ordered first-shard census being called representative.
    for info in api["siblings"]:
        if not info["rfilename"].endswith(".parquet"):
            continue
        path, receipt = metadata_file(session, root, info, sparse, network)
        receipts.append(receipt)
        pf = pq.ParquetFile(path)
        columns = [name for name in pf.schema_arrow.names if name != "conversations"]
        for index, row in enumerate(pf.read(columns=columns, use_threads=False).to_pylist()):
            task_id = row["task"]
            base_task = re.sub(r"_copy\d+$", "", task_id)
            # Known source prefix is bookkeeping, never used to invent a TB category.
            source_prefix = re.sub(r"[-_]\d.*$", "", base_task)
            key = "ot100k-task:" + base_task
            value = row.get("result")
            try:
                reward = float(value) if value not in (None, "", "None", "null") else None
            except (ValueError, TypeError):
                reward = None
            record = {"revision": REV, "file": info["rfilename"], "row_index": index,
                      "task_id": task_id, "base_task_id": base_task, "source_prefix": source_prefix,
                      "family_key": key, "family_rank": family_rank(key),
                      "candidate_partition": family_partition(key), "result": value,
                      "source_numeric_reward": reward, "trace_source": row.get("trace_source"),
                      "model_alias": row.get("model"), "agent": row.get("agent"),
                      "target_category": "unknown", "training_released": False,
                      "hold_reasons": ["task_category_unannotated", "source_task_environment_mapping_not_restored"]}
            if reward is None:
                record["hold_reasons"].append("no_numeric_verifier_reward")
            if row.get("trace_source") is None:
                record["hold_reasons"].append("trace_role_unknown")
            elif row.get("trace_source") != "main":
                record["hold_reasons"].append("auxiliary_trace_not_full_task_episode")
            records.append(record)
            for key in ("result", "trace_source", "agent", "model", "model_provider"):
                metadata_counts[key][str(row.get(key))] += 1
            metadata_counts["source_prefix"][source_prefix] += 1
            if row.get("trace_source") is None:
                metadata_counts["unknown_trace_role_source_prefix"][source_prefix] += 1
        print(json.dumps({"metadata_file_done": info["rfilename"], "rows": receipt["rows"]}), flush=True)
    # Prefix capture may be incomplete as a full shard; footer appended to a separate sparse copy.
    # Only row groups fully within the captured contiguous prefix are read.
    first_info = next(f for f in api["siblings"] if f["rfilename"] == "data/train-00000-of-00010.parquet")
    body = raw / "ot100k-train-00000.parquet"
    body_size = body.stat().st_size
    view = raw / "ot100k-body-prefix-view.parquet"
    with body.open("rb") as source, view.open("wb") as destination:
        while chunk := source.read(1024 * 1024):
            destination.write(chunk)
        footer = (raw / "ot100k-footer-64k.bin").read_bytes()
        destination.seek(first_info["size"] - len(footer))
        destination.write(footer)
    pf = pq.ParquetFile(view)
    parser_path = root / "artifacts/benchmarks/harbor/src/harbor/agents/terminus_2/terminus_json_plain_parser.py"
    spec = importlib.util.spec_from_file_location("apex_new_terminal_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parser = module.TerminusJSONPlainParser()
    by_row = {(r["file"], r["row_index"]): r for r in records}
    formal = json.load(open(root / "artifacts/data/audits/formal_input_fingerprints_20261016/index.json"))["terminal_instruction_sha256"]
    body_counts, input_counts, groups_read = Counter(), Counter(), []
    offset = 0
    for rg_index in range(min(args.body_row_groups, pf.num_row_groups)):
        group = pf.metadata.row_group(rg_index)
        last_byte = max((c.dictionary_page_offset or c.data_page_offset) + c.total_compressed_size
                        for c in (group.column(i) for i in range(group.num_columns)))
        if last_byte > body_size:
            break
        groups_read.append(rg_index)
        for index, row in enumerate(pf.read_row_group(rg_index, use_threads=False).to_pylist(), offset):
            conv = row["conversations"]
            record = by_row[(first_info["rfilename"], index)]
            first = conv[0]["content"] if conv else ""
            instruction = None
            if "Task Description:\n" in first and "\n\nCurrent terminal state:\n" in first:
                instruction = first.split("Task Description:\n", 1)[1].rsplit("\n\nCurrent terminal state:\n", 1)[0]
            ih = text_hash(instruction) if instruction else None
            parsed, errors, complete, visible_chars, think_count = 0, 0, False, 0, 0
            for msg in conv:
                if msg["role"] != "assistant":
                    continue
                clean = strip_think(msg["content"] or "")
                think_count += clean != (msg["content"] or "")
                visible_chars += len(clean)
                result = parser.parse_response(clean)
                parsed += 1
                errors += bool(result.error)
                complete |= bool(result.is_task_complete and not result.error)
            record.update({"body_inspected": True, "instruction_sha256": ih,
                           "formal_exact_hits": formal.get(ih, []), "assistant_messages": parsed,
                           "parser_error_messages": errors, "any_completion_proxy": complete,
                           "clean_assistant_characters": visible_chars, "messages_with_leading_think": think_count})
            if ih:
                input_counts[ih] += 1
            body_counts["rows"] += 1
            body_counts["main_rows"] += record["trace_source"] == "main"
            body_counts["instruction_extracted_rows"] += ih is not None
            body_counts["formal_exact_hit_rows"] += bool(formal.get(ih))
            body_counts["all_actions_parse_rows"] += parsed > 0 and errors == 0
            body_counts["any_completion_proxy_rows"] += complete
            body_counts["assistant_messages"] += parsed
            body_counts["parser_error_messages"] += errors
            body_counts["assistant_messages_with_leading_think"] += think_count
        offset += group.num_rows
    # Small task-text review covers all four sources; labels are ours, not official.
    annotation_path = base / "manual_annotations.json"
    annotations = {a["base_task_id"]: a for a in json.load(open(annotation_path))["annotations"]}
    for line in open(base / "annotation_candidates.jsonl"):
        candidate = json.loads(line)
        record = by_row[(candidate["file"], candidate["row_index"])]
        ih = candidate["instruction_sha256"]
        record.update(input_inspected=True, instruction_sha256=ih, formal_exact_hits=formal.get(ih, []))
    parents = {r["family_key"]: r["family_key"] for r in records}
    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key
    input_families = {}
    for record in records:
        ih = record.get("instruction_sha256")
        if ih:
            other = input_families.setdefault(ih, record["family_key"])
            a, b = find(record["family_key"]), find(other)
            parents[max(a, b)] = min(a, b)
    excluded_families = {find(r["family_key"]) for r in records if r.get("formal_exact_hits")}
    for record in records:
        key = find(record["family_key"])
        record.update(family_key=key, family_rank=family_rank(key), candidate_partition=family_partition(key),
                      excluded_formal_family=key in excluded_families)
        if record["base_task_id"] in annotations:
            annotation = annotations[record["base_task_id"]]
            record["target_category"] = annotation["category"]
            record["annotation"] = annotation
            record["hold_reasons"].remove("task_category_unannotated")
            record["annotation_is_official"] = False
    family_counts = Counter(r["family_key"] for r in records)
    main_counts = Counter(r["family_key"] for r in records if r["trace_source"] == "main")
    representatives = {}
    def priority(record):
        value = record["source_numeric_reward"]
        return (not (value is not None and value > 0), record["result"] not in (None, "None", "null", ""),
                not (record.get("body_inspected") and record.get("parser_error_messages") == 0),
                not record.get("any_completion_proxy", False), record["file"], record["row_index"])
    for record in records:
        if record["trace_source"] == "main" and not record["excluded_formal_family"]:
            key = record["family_key"]
            if key not in representatives or priority(record) < priority(representatives[key]):
                representatives[key] = record
    with (base / "all_row_family_map.jsonl").open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    for partition in ("train", "val"):
        with (base / f"{partition}_candidate_hold.jsonl").open("w") as stream:
            for record in sorted(representatives.values(), key=lambda r: r["family_rank"]):
                if record["candidate_partition"] == partition:
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        with (base / f"annotated_{partition}_candidate_hold.jsonl").open("w") as stream:
            for record in sorted(representatives.values(), key=lambda r: r["family_rank"]):
                if record["candidate_partition"] == partition and record["target_category"] != "unknown":
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    target = json.load(open(root / "analysis/source_snapshots/validation_target_distribution_20261016.json"))["terminal"]["category_counts"]
    athena = json.load(open(raw / "athena_fixed_footer_audit.json"))
    result = {"as_of": "2026-10-16", "revision": REV, "license": api.get("cardData", {}).get("license"),
              "scope": "All pinned shard non-conversation metadata via verified bounded HTTP ranges; only first shard captured body prefix audited. No trajectory code/validator/container/model/API/GPU executed. No training-format export.",
              "metadata_rows": len(records), "metadata_counts": {k: dict(v) for k, v in metadata_counts.items()},
              "family_groups": len(family_counts), "main_family_groups": len(main_counts),
              "family_row_count_histogram": dict(Counter(family_counts.values())),
              "main_rows": sum(main_counts.values()), "numeric_positive_reward_main_rows": sum(r["trace_source"] == "main" and r["source_numeric_reward"] is not None and r["source_numeric_reward"] > 0 for r in records),
              "unknown_trace_role_rows": sum(r["trace_source"] is None for r in records),
              "formal_exact_excluded_family_groups": len(excluded_families),
              "candidate_reserve": {p: {"main_rows": sum(r["trace_source"] == "main" and r["candidate_partition"] == p and not r["excluded_formal_family"] for r in records),
                                          "representative_rows_in_manifest": sum(r["candidate_partition"] == p for r in representatives.values()),
                                          "main_family_groups": len({r["family_key"] for r in records if r["trace_source"] == "main" and r["candidate_partition"] == p and not r["excluded_formal_family"]})}
                                    for p in ("train", "val")},
              "split_seed": SPLIT_SEED, "split_rule": "Root shared family_partition; strip _copyNNNN and group all summaries/answers/rollouts of same base task, union identical inspected instructions. Exclude known formal-hit families; source repo/template mapping unresolved.",
              "body_capture": {"path": str(body.relative_to(root)), "bytes_captured_before_view": body_size,
                               "expected_full_size": first_info["size"], "full_LFS_sha256_verified": body_size == first_info["size"] and sha(body.read_bytes()) == first_info["lfs"]["sha256"],
                               "row_groups_read": groups_read, "counts": dict(body_counts), "unique_instruction_hashes": len(input_counts)},
              "category_coverage": {k: {"target_tasks": v,
                                          "project_annotated_family_representatives": sum(r["target_category"] == k for r in representatives.values()),
                                          "official_source_labels": 0} for k, v in target.items()},
              "unknown_category_main_rows": sum(r["trace_source"] == "main" and r["target_category"] == "unknown" for r in records),
              "manual_annotation": {"source_task_instructions": len(annotations), "method": "project_manual_task_instruction_v1",
                                    "official_labels": False, "quality_hold_retained": True,
                                    "task_labels": list(annotations.values()),
                                    "sha256": sha(annotation_path.read_bytes()),
                                    "reserve": {p: dict(Counter(r["target_category"] for r in representatives.values() if r["candidate_partition"] == p and r["target_category"] != "unknown")) for p in ("train", "val")}},
              "proportional_target_template_for_89_families": proportional_quotas(89, target),
              "training_released_rows": 0, "executable_task_dev_qualified": 0,
              "representative_rule": "One main trace per family: prefer numeric positive reward, then no recorded exception, then inspected parse consistency and completion proxy, deterministic file/row tie. No preference for shorter/easier trajectories. Held candidates, not verified successful demonstrations.",
              "blocking_gaps": ["Only 48 manually annotated task instructions; no full TB16 distribution fit or task-binary mapping", "Source repository/template families not restored", "Teacher row field is alias; exact weights revision absent", "No numeric verifier rewards; no recorded exception is not success", "Exact exclusion only covers inspected instructions, not all metadata-only rows", "No independent runtime/verifier replay"],
              "athena_footer_only": {name: {"rows": sum(x.get("rows", 0) for x in athena if x["source"] == name),
                                             "files": sum(x["source"] == name for x in athena),
                                             "range_bytes": sum(x.get("bytes_read", 0) for x in athena if x["source"] == name),
                                             "license": None, "README": False, "training_released": False}
                                      for name in ("athena_vanilla", "athena_advanced")},
              "metadata_receipts": receipts, "network_this_run": dict(network),
              "metadata_unique_range_bytes": sum(r["fetched_bytes"] for r in receipts),
              "metadata_unique_range_requests": sum(len(r["ranges"]) + 1 for r in receipts),
              "additional_body_ranges": json.load(open(base / "additional_body_range_receipts.json")),
              "seconds": round(time.monotonic() - start_time, 2), "script_sha256": sha(Path(__file__).read_bytes())}
    result["candidate_manifests"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                                     for p in base.glob("*_candidate_hold.jsonl")}
    (base / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": str(base / "summary.json"), "rows": len(records), "seconds": result["seconds"]}))


if __name__ == "__main__":
    main()
