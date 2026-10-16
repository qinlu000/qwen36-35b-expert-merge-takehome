#!/usr/bin/env python3
"""Static execution-data census. Never run teacher code, tools, or validators."""
import os

for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"):
    os.environ[name] = "1"

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import time
import tomllib

import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

TERMINAL_REV = "a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9"
TERMINAL_TASK_REV = "7e53648e183cee7bcb0aed623cc91a121d37fa38"
D3_REV = "b21b5006956d7d246cf3e35277b13323780a45b2"
D3_TASK_REV = "8499689ac98882a7cac9b5ef9e93365cc37df57e"


def digest(value):
    if not isinstance(value, bytes):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def ws(text):
    return re.sub(r"\s+", " ", text).strip()


def strip_reasoning(text):
    blocks = 0
    while match := re.match(r"^\s*<think>.*?</think>\s*", text, re.S):
        text = text[match.end():]
        blocks += 1
    return text, blocks


class Groups:
    def __init__(self):
        self.parent = {}

    def find(self, key):
        self.parent.setdefault(key, key)
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def duplicate_summary(counter):
    return {"unique": len(counter), "repeated_keys": sum(n > 1 for n in counter.values()),
            "excess_rows": sum(n - 1 for n in counter.values())}


def terminal_packs(root, out):
    base = root / "artifacts/tasks/raw/nemotron_tasks" / TERMINAL_TASK_REV
    packs = {}
    for path in sorted(base.rglob("*.tar.gz")):
        difficulty, domain = path.parent.name, path.name.removesuffix(".tar.gz")
        # Streaming avoids repeated gzip decompression while hashing task input assets.
        with tarfile.open(path, "r|gz") as archive:
            for member in archive:
                parts = Path(member.name).parts
                task_id = next((p for p in parts if p.startswith(domain + "_task_")), None)
                if not member.isfile() or task_id is None:
                    continue
                key = (difficulty, domain, task_id)
                item = packs.setdefault(key, {"difficulty": difficulty, "domain": domain,
                                              "task_id": task_id, "input_files": []})
                if parts[-1] == "instruction.md":
                    text = archive.extractfile(member).read().decode().strip()
                    item["instruction_sha256"] = digest(text)
                    item["instruction_ws_sha256"] = digest(ws(text))
                elif parts[-1] == "task.toml":
                    data = archive.extractfile(member).read()
                    metadata = tomllib.loads(data.decode()).get("metadata", {})
                    item["task_toml_sha256"] = digest(data)
                    item["declared_category"] = metadata.get("category")
                    item["declared_difficulty"] = metadata.get("difficulty")
                elif "environment" in parts and "files" in parts:
                    item["input_files"].append([str(Path(*parts[parts.index("environment") + 1:])),
                                                digest(archive.extractfile(member).read())])
                elif "environment" in parts and parts[-1] == "Dockerfile":
                    item["dockerfile_sha256"] = digest(archive.extractfile(member).read())
    with (out / "terminal_task_pack_manifest.jsonl").open("w") as stream:
        for item in packs.values():
            item["input_manifest_sha256"] = digest(json.dumps(sorted(item.pop("input_files"))))
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    return packs


def audit_terminal(root, out):
    packs = terminal_packs(root, out)
    source = root / "artifacts/data/raw/terminal_corpus" / TERMINAL_REV
    parser_path = root / "artifacts/benchmarks/harbor/src/harbor/agents/terminus_2/terminus_json_plain_parser.py"
    spec = importlib.util.spec_from_file_location("apex_static_terminus_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parser = module.TerminusJSONPlainParser()
    counters = defaultdict(Counter)
    records, files = [], []
    groups = Groups()
    task_variants = defaultdict(set)
    counts = Counter()
    known_domains = set()
    for path in sorted(source.rglob("*.parquet")):
        relative = str(path.relative_to(source))
        difficulty, domain = path.parts[-3:-1]
        known_domains.add(domain)
        pf = pq.ParquetFile(path)
        file_counts = Counter()
        index = 0
        for batch in pf.iter_batches(batch_size=32, use_threads=False):
            for row in batch.to_pylist():
                conv = row.pop("conversations")
                first = conv[0].get("content") or "" if conv else ""
                instruction = None
                if "Task Description:\n" in first and "\n\nCurrent terminal state:\n" in first:
                    instruction = first.split("Task Description:\n", 1)[1].rsplit("\n\nCurrent terminal state:\n", 1)[0].strip()
                ih = digest(instruction) if instruction is not None else None
                wh = digest(ws(instruction)) if instruction is not None else None
                raw_id = domain + "/" + str(row["task"])
                id_node = "id:" + raw_id
                groups.find(id_node)
                if wh:
                    groups.join(id_node, "instruction:" + wh)
                    task_variants[raw_id].add(wh)
                pack = packs.get((difficulty, domain, row["task"]))
                exact = bool(pack and ih == pack.get("instruction_sha256"))
                normalized = bool(pack and wh == pack.get("instruction_ws_sha256"))
                flags = Counter()
                complete, last_complete = False, False
                for msg in conv:
                    if msg["role"] != "assistant":
                        continue
                    content = msg.get("content") or ""
                    clean, removed = strip_reasoning(content)
                    flags["assistant_messages"] += 1
                    flags["leading_think_blocks"] += removed
                    flags["unbalanced_leading_think_messages"] += int(clean.lstrip().startswith("<think>"))
                    result = parser.parse_response(clean)
                    flags["parser_error_messages"] += bool(result.error)
                    flags["parser_warning_messages"] += bool(result.warning)
                    flags["command_entries"] += len(result.commands)
                    last_complete = bool(result.is_task_complete and not result.error)
                    complete |= last_complete
                strict_roles = [m["role"] for m in conv] == ["user" if i % 2 == 0 else "assistant" for i in range(len(conv))]
                ch = digest(json.dumps(conv, ensure_ascii=False, separators=(",", ":")))
                record = {"file": relative, "row_index": index, **row,
                          "instruction_sha256": ih, "instruction_ws_sha256": wh,
                          "conversation_sha256": ch, "group_node": id_node,
                          "task_pack_exact_instruction": exact, "task_pack_whitespace_instruction": normalized,
                          "source_success": "unknown_no_row_result_field",
                          "strict_user_assistant_alternation": strict_roles,
                          "any_task_complete_proxy": complete, "last_action_task_complete_proxy": last_complete,
                          **flags}
                records.append(record)
                for key in ("agent", "model", "model_provider", "enable_thinking", "task", "episode", "run_id", "trial_name"):
                    counters[key][str(row[key])] += 1
                counters["conversation_sha256"][ch] += 1
                counters["instruction_ws_sha256"][wh] += 1
                counters["difficulty"][difficulty] += 1
                counters["domain"][domain] += 1
                counts.update(flags)
                for key, value in {"rows": True, "extracted_instruction_rows": ih is not None,
                                   "pack_exact_rows": exact, "pack_whitespace_rows": normalized,
                                   "strict_alternation_rows": strict_roles, "any_complete_proxy_rows": complete,
                                   "last_complete_proxy_rows": last_complete,
                                   "all_assistant_actions_parse_rows": flags["parser_error_messages"] == 0,
                                   "pack_exact_and_all_actions_parse_rows": exact and flags["parser_error_messages"] == 0}.items():
                    counts[key] += bool(value)
                    file_counts[key] += bool(value)
                index += 1
        files.append({"path": relative, "rows": pf.metadata.num_rows, "counts": dict(file_counts)})
        print(json.dumps({"terminal_file_done": relative, "rows": index}), flush=True)
    family_counts, family_domains, mapped_families = Counter(), defaultdict(set), set()
    with (out / "terminal_row_family_map.jsonl").open("w") as stream:
        for record in records:
            node = record.pop("group_node")
            group_id = digest(groups.find(node))
            record["family_group_sha256"] = group_id
            family_counts[group_id] += 1
            domain = Path(record["file"]).parts[-2]
            family_domains[domain].add(group_id)
            if record["task_pack_exact_instruction"]:
                mapped_families.add(group_id)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    target = json.load(open(root / "analysis/source_snapshots/validation_target_distribution_20261016.json"))["terminal"]["category_counts"]
    coverage = {category: {"target_tasks": n, "source_rows": counters["domain"][category.replace("-", "_")],
                           "source_family_groups": len(family_domains[category.replace("-", "_")])}
                for category, n in target.items()}
    return {"revision": TERMINAL_REV, "task_revision": TERMINAL_TASK_REV,
            "counts": dict(counts), "files": files, "pack_tasks": len(packs),
            "pack_domains": dict(Counter(item["domain"] for item in packs.values())),
            "metadata": {key: dict(counters[key]) for key in ("agent", "model", "model_provider", "enable_thinking", "difficulty", "domain")},
            "identities": {key: duplicate_summary(counters[key]) for key in ("task", "episode", "run_id", "trial_name", "conversation_sha256", "instruction_ws_sha256")},
            "family_groups": len(family_counts), "family_excess_rows": sum(n - 1 for n in family_counts.values()),
            "same_raw_id_multiple_instruction_variants": sum(len(v) > 1 for v in task_variants.values()),
            "same_raw_id_instruction_variant_histogram": dict(Counter(len(v) for v in task_variants.values())),
            "exact_pack_mapped_family_groups": len(mapped_families), "target_category_metadata_crosswalk": coverage,
            "non_target_source_domains": sorted(known_domains - {c.replace("-", "_") for c in target}),
            "source_success": {"unknown_no_row_result_field": counts["rows"]},
            "group_rule": "Union shared (source domain, bare task ID) across difficulty AND identical whitespace-normalized instruction. Conservative grouping, not proof of semantic equivalence; no template provenance field.",
            "environment_status": "Exact instruction join only; package input manifests hashed, runtime initialization/assets/permissions/validators not replayed.",
            "parser": {"path": str(parser_path.relative_to(root)), "sha256": digest(parser_path.read_bytes()),
                       "scope": "Static official parser after leading balanced think removal; errors may be recoverable intermediate actions, flags are not final exclusion or verifier success."}}


def audit_d3(root, out):
    source = root / "artifacts/data/raw/d3_gym_32b" / D3_REV / "Qwen3_32B_trajectories.json"
    taskfile = root / "artifacts/tasks/raw/d3_tasks" / D3_TASK_REV / "data/train-00000-of-00001.parquet"
    tasks = pq.read_table(taskfile, columns=["task_id", "task_instruction", "dataset_previews", "original_repo", "discipline"]).to_pylist()
    rows = json.load(open(source))
    counts, disciplines, repos, mapped_tasks = Counter(), Counter(), Counter(), Counter()
    input_counts, pair_counts, output_counts = Counter(), Counter(), Counter()
    records = []
    # No fuzzy nearest-neighbour assignment: exact instruction containment first, then preview as corroboration.
    for index, row in enumerate(rows):
        inp, answer = row["input"], row["output"]
        hits = [t for t in tasks if t["task_instruction"].strip() in inp]
        method = "exact_instruction_containment" if hits else "none"
        if not hits:
            norm_input = ws(inp)
            hits = [t for t in tasks if ws(t["task_instruction"]) in norm_input]
            method = "whitespace_instruction_containment" if hits else "none"
        mapped = hits[0] if len(hits) == 1 else None
        clean, blocks = strip_reasoning(answer)
        code_blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", clean, re.S)
        parsed = 0
        for code in code_blocks:
            try:
                ast.parse(code)
                parsed += 1
            except SyntaxError:
                pass
        ih, oh, ph = digest(ws(inp)), digest(clean), digest(ws(inp) + "\0" + clean)
        input_counts[ih] += 1
        output_counts[oh] += 1
        pair_counts[ph] += 1
        record = {"row_index": index, "input_ws_sha256": ih, "clean_output_sha256": oh,
                  "input_output_sha256": ph, "match_candidates": [t["task_id"] for t in hits],
                  "match_method": method, "leading_think_blocks": blocks,
                  "remaining_leading_think": clean.lstrip().startswith("<think>"),
                  "fenced_code_blocks": len(code_blocks), "ast_parseable_code_blocks": parsed,
                  "source_success": "publisher_reports_silver_filter_no_row_receipt"}
        if mapped:
            for key in ("task_id", "original_repo", "discipline"):
                record[key] = mapped[key]
            record["full_preview_exact_contained"] = mapped["dataset_previews"].strip() in inp
            record["full_preview_whitespace_contained"] = ws(mapped["dataset_previews"]) in ws(inp)
            record["family_group_sha256"] = digest("d3-repo:" + mapped["original_repo"].lower().rstrip("/"))
            mapped_tasks[mapped["task_id"]] += 1
            disciplines[mapped["discipline"]] += 1
            repos[mapped["original_repo"].lower().rstrip("/")] += 1
        else:
            record["family_group_sha256"] = None
        counts["rows"] += 1
        counts["uniquely_mapped_rows"] += mapped is not None
        counts["ambiguous_rows"] += len(hits) > 1
        counts["unmapped_rows"] += len(hits) == 0
        counts["exact_instruction_mapped_rows"] += mapped is not None and method == "exact_instruction_containment"
        counts["full_preview_exact_contained_rows"] += bool(record.get("full_preview_exact_contained"))
        counts["full_preview_whitespace_contained_rows"] += bool(record.get("full_preview_whitespace_contained"))
        counts["rows_with_parseable_python_fence"] += parsed > 0
        counts["rows_without_parseable_python_fence"] += parsed == 0
        counts["leading_think_removed_rows"] += blocks > 0
        counts["remaining_leading_think_rows"] += bool(record["remaining_leading_think"])
        records.append(record)
    with (out / "d3_row_task_family_map.jsonl").open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    target = json.load(open(root / "analysis/source_snapshots/validation_target_distribution_20261016.json"))["asi"]["discipline_counts"]
    # Strict exact domain labels only; adjacent disciplines are separately reported, not guessed into ASI domains.
    strict = {"chemistry": "chemistry"}
    coverage = {category: {"target_tasks": n,
                           "source_rows_strict_label": sum(v for k, v in disciplines.items() if strict.get(k.lower()) == category),
                           "source_tasks_strict_label": sum(1 for t in tasks if t["task_id"] in mapped_tasks and strict.get(t["discipline"].lower()) == category)}
                for category, n in target.items()}
    return {"revision": D3_REV, "task_revision": D3_TASK_REV, "counts": dict(counts),
            "task_metadata_rows": len(tasks), "mapped_unique_tasks": len(mapped_tasks),
            "mapped_source_repositories": len(repos), "source_repo_row_counts": dict(repos),
            "metadata_discipline_counts": dict(Counter(t["discipline"] for t in tasks)),
            "mapped_discipline_row_counts": dict(disciplines),
            "identities": {"input_ws_sha256": duplicate_summary(input_counts), "input_output_sha256": duplicate_summary(pair_counts),
                           "clean_output_sha256": duplicate_summary(output_counts)},
            "task_rollout_count_histogram": dict(Counter(mapped_tasks.values())),
            "source_success": {"publisher_reports_silver_filter_no_row_receipt": len(rows)},
            "target_discipline_strict_crosswalk": coverage,
            "adjacent_unmapped_labels": {k: v for k, v in disciplines.items() if k.lower() not in strict},
            "group_rule": "All mapped tasks from the same original_repo are one conservative family; task rollouts never split. Exact/whitespace instruction containment gives source mapping, not runtime or input equivalence.",
            "qualification": "Static single-program SFT candidate; no multi-turn tool observations. Author-reported silver selection is not local per-row validator evidence. Task images/input data/hidden verifier isolation not executed; not yet task-dev qualified.",
            "task_metadata_columns_read": ["task_id", "task_instruction", "dataset_previews", "original_repo", "discipline"],
            "excluded_columns": ["eval_script"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    out = args.output or root / "artifacts/data/audits/execution_candidates_20261016"
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = {"as_of": "2026-10-16", "scope": "CPU-only static census, training input hashes and metadata. No benchmark question/answer/test read, model/API/GPU/container/trajectory execution, training export or final train/val selection.",
              "terminal": audit_terminal(root, out), "d3": audit_d3(root, out),
              "seconds": round(time.monotonic() - started, 2), "script_sha256": digest(Path(__file__).read_bytes()),
              "limits": "One Python process, PyArrow CPU/IO threads=1. No semantic near-duplicate/template inference; exact/whitespace identity and source repo/ID group only."}
    result["artifacts"] = {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
                           for p in out.glob("*.jsonl")}
    (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": str(out / "summary.json"), "seconds": result["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
