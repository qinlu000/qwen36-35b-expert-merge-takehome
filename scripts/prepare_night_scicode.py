"""Freeze a two-main-problem SciCode scientific-Python transfer calibration.

Only public formal ASI prompts are read for exclusion. No ASI gold is loaded.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

REVISION = "eea11a866be6860725258702b39ef8651ed26abd"
SELECTED = {"5": "mathematics/numerical_linear_algebra", "8": "physics/fourier_optics"}
SYSTEM = ("You are an expert scientific programmer. When asked to write code, output ONLY "
          "a single Python code block. Do not include any explanation outside the code block.")


def words(text):
    return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).lower())


def grams(text):
    tokens = words(text)
    return {hashlib.sha256(" ".join(tokens[i:i+13]).encode()).digest()[:16]
            for i in range(len(tokens)-12)}


def task_text(row):
    return "\n".join([row["problem_description_main"], row["problem_background_main"],
                       row["problem_io"]] + [s["step_description_prompt"] + "\n" + s["step_background"]
                                              for s in row["sub_steps"]])


def make_prompt(row):
    sections = ["Implement the complete self-contained Python solution for this scientific task.",
                row["problem_description_main"], row["problem_background_main"],
                "Input/output specification:\n" + row["problem_io"],
                "Available scientific dependencies:\n" + row["required_dependencies"]]
    for step in row["sub_steps"]:
        sections += [step["step_description_prompt"], step["step_background"],
                     "Required function interface:\n" + step["function_header"], step["return_line"]]
    sections += ["Provide all required functions and imports in one Python code block. "
                 "Do not call the functions at import time. No network or shell access is needed."]
    return "\n\n".join(part for part in sections if part)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--formal-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.source.read_text().splitlines() if line]
    args.output.mkdir(parents=True, exist_ok=True)
    files = sorted(args.formal_inputs.glob("*/prompt_b*.md"))
    assert len(files) == 240
    formal = {str(path.relative_to(args.formal_inputs)): path.read_text() for path in files}
    formal_hashes = {hashlib.sha256(" ".join(words(text)).encode()).hexdigest() for text in formal.values()}
    index = defaultdict(set)
    for path, text in formal.items():
        for gram in grams(text):
            index[gram].add(path.split("/")[0])
    exclusions, candidates = [], []
    for row in rows:
        text = task_text(row)
        exact = hashlib.sha256(" ".join(words(text)).encode()).hexdigest() in formal_hashes
        overlap = sorted({path for gram in grams(text) for path in index.get(gram, set())})
        record = {"problem_id": row["problem_id"], "problem_name": row["problem_name"],
                  "exact_overlap": exact, "shared_13gram_formal_families": overlap,
                  "main_family": "scicode_verified:" + row["problem_id"],
                  "substeps": len(row["sub_steps"])}
        exclusions.append(record)
        if row["problem_id"] in SELECTED:
            assert not exact and not overlap
            prompt = make_prompt(row)
            candidates.append({**record, "domain": SELECTED[row["problem_id"]],
                "dataset": "shhu2001/SciCode-Verified", "dataset_revision": REVISION,
                "split": "train_calibration", "source_split": "test", "system": SYSTEM,
                "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "prompt_utf8_bytes_with_system": len((SYSTEM + prompt).encode()),
                "references_sent_to_teacher": False, "test_cases_sent_to_teacher": False,
                "row": row})
    assert len(candidates) == 2 and {r["substeps"] for r in candidates} == {1}
    patterns = {"5": r"scicode|lanczos|krylov", "8": r"scicode|cross.shaped|spatial.filter|fourier.optic"}
    family_hits = {pid: sorted(path for path, text in formal.items() if re.search(pattern, text, re.I))
                   for pid, pattern in patterns.items()}
    assert not any(family_hits.values())
    total_bytes = sum(r["prompt_utf8_bytes_with_system"] + 1024 for r in candidates)
    worst = (total_bytes * 1.32 + 2 * 8192 * 3.96) / 1e6
    summary = {"source_revision": REVISION, "source_main_families": len(rows),
        "source_substep_descriptors": sum(len(r["sub_steps"]) for r in rows),
        "formal_input_files_read": len(files), "formal_gold_read": False,
        "all_source_exact_hits": sum(r["exact_overlap"] for r in exclusions),
        "all_source_13gram_flagged_main_families": [r["problem_id"] for r in exclusions if r["shared_13gram_formal_families"]],
        "selected": [{k:v for k,v in r.items() if k not in {"row", "prompt", "system"}} for r in candidates],
        "selected_named_method_family_hits": family_hits,
        "sourcefamily_limit": "No per-task paper/author identifiers in SciCode JSONL; main problem IDs and named-method search are the available family guards. No absence-of-overlap proof beyond these checks.",
        "api_bound": {"model": "deepseek-v4-pro", "thinking": False, "calls": 2,
                      "max_output_tokens_per_call": 8192, "input_token_upper_bound": total_bytes,
                      "maximum_usd": worst, "budget_factor": 8, "maximum_budget_cny": worst*8,
                      "branch_previous_budget_cny": 2.58201072,
                      "maximum_branch_cny_after_two_calls": 2.58201072+worst*8},
        "not_formal_asi_score": True, "not_500_100_ready": True}
    for name, value in [("selection_summary.json", summary), ("formal_input_exclusion.json", exclusions)]:
        (args.output/name).write_text(json.dumps(value, indent=2)+"\n")
    (args.output/"two_task_candidates.jsonl").write_text("".join(json.dumps(r)+"\n" for r in candidates))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
