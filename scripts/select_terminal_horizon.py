#!/usr/bin/env python3
"""Build reviewable proportional task candidates, retaining explicit quality/runtime holds."""
import os
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from candidate_selection import family_rank, proportional_quotas, text_hash

CALIBRATION_TASKS = {"adapt-a-seismic-acquisition-geometry-from-in-field-qc",
                     "blind-transient-thermal-hydraulic-model-validation"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    out = base / "proportional_candidates"
    out.mkdir(parents=True, exist_ok=True)
    tasks = [json.loads(line) for line in (base / "environment_metadata.jsonl").open()]
    labels = {x["id"]: x for x in map(json.loads, (base / "annotations/labels.jsonl").open())}
    weights = json.load(open(args.root / "configs/data/new_candidate_selection_v1.json"))["target_distributions"]["terminal"]["category_counts"]
    formal = json.load(open(args.root / "artifacts/data/audits/formal_input_fingerprints_20261016/index.json"))["terminal_instruction_sha256"]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2,
                               max_df=.9, stop_words="english", dtype=np.float32)
    features = vectorizer.fit_transform([x["instruction"] for x in tasks])
    similarities = (features @ features.T).toarray()
    parents = list(range(len(tasks)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    pairs = []
    for i in range(len(tasks)):
        for j in np.flatnonzero(similarities[i, i + 1:] >= .35) + i + 1:
            score = float(similarities[i, j])
            if score >= .65:
                a, b = find(i), find(int(j)); parents[max(a, b)] = min(a, b)
            pairs.append({"left": tasks[i]["task_id"], "right": tasks[j]["task_id"],
                          "score": score, "grouped_conservatively": score >= .65,
                          "semantic_review_pending": True})
    groups = defaultdict(list)
    for i, task in enumerate(tasks): groups[find(i)].append(i)
    candidates = []
    for indices in groups.values():
        ordered = sorted(indices, key=lambda i: family_rank("horizon-task:" + tasks[i]["task_id"]))
        i = ordered[0]; task = tasks[i]; label = labels.get(task["task_id"])
        family_ids = sorted(tasks[j]["task_id"] for j in indices)
        family_key = "horizon-family:" + min(family_ids)
        distinct_categories = {labels[t]["category"] for t in family_ids if t in labels}
        if not label or label["category"] not in weights or label["confidence"] == "low": continue
        if len(distinct_categories) > 1: continue
        if any(t in CALIBRATION_TASKS for t in family_ids): continue
        if any(text_hash(tasks[j]["instruction"]) in formal for j in indices): continue
        candidates.append({"task_id": task["task_id"], "family_key": family_key,
                           "family_task_ids": family_ids, "family_rank": family_rank(family_key),
                           "category": label["category"], "annotation": label,
                           "instruction_sha256": text_hash(task["instruction"]), "row_index_in_environment_metadata": i,
                           "source_category": task["category"], "source_subcategory": task["subcategory"],
                           "training_released": False, "executable_val_ready": False,
                           "hold_reasons": ["source_process_filtered_not_verified_success_only",
                                            "family_lineage_semantic_review_pending",
                                            "category_annotation_review_pending", "container_runtime_not_validated"]})
    candidates.sort(key=lambda x: x["family_rank"])
    val_quota, train_quota = proportional_quotas(100, weights), proportional_quotas(500, weights)
    val, train = [], []
    for category, count in val_quota.items():
        val.extend([x for x in candidates if x["category"] == category][:count])
    val_families = {x["family_key"] for x in val}
    val_indices = [i for family in val for i, task in enumerate(tasks) if task["task_id"] in family["family_task_ids"]]
    excluded_near_val, train_pool = [], []
    for task in candidates:
        if task["family_key"] in val_families: continue
        closest = max((float(similarities[task["row_index_in_environment_metadata"], i]) for i in val_indices), default=0)
        if closest >= .35:
            excluded_near_val.append({"task_id": task["task_id"], "closest_val_tfidf": closest,
                                      "reason": "conservative_near_val_hold_before_semantic_review"})
        else:
            train_pool.append(task)
    for category, count in train_quota.items():
        train.extend([x for x in train_pool if x["category"] == category][:count])
    for name, rows in [("val_tasks.provisional.jsonl", val), ("train_tasks.provisional.jsonl", train),
                       ("train_pool.provisional.jsonl", train_pool),
                       ("near_duplicate_pairs.review.jsonl", pairs), ("near_val_train_holds.jsonl", excluded_near_val)]:
        with (out / name).open("w") as stream:
            for row in rows: stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    val_counts, train_counts = Counter(x["category"] for x in val), Counter(x["category"] for x in train)
    summary = {"source_tasks": len(tasks), "annotated_tasks": len(labels),
               "annotation_categories": dict(Counter(x["category"] for x in labels.values())),
               "annotation_confidence": dict(Counter(x["confidence"] for x in labels.values())),
               "conservative_families": len(groups), "families_with_multiple_tasks": sum(len(x) > 1 for x in groups.values()),
               "source_genealogy_complete": False, "tfidf_pairs_at_least_035": len(pairs),
               "tfidf_group_threshold": .65, "train_val_near_hold_threshold": .35,
               "calibration_reserved_task_ids": sorted(CALIBRATION_TASKS),
               "eligible_provisional_family_candidates": len(candidates),
               "val_requested": 100, "train_requested": 500, "val_selected_provisional": len(val),
               "train_selected_provisional": len(train), "near_val_train_held": len(excluded_near_val),
               "val_quota": val_quota, "train_quota": train_quota,
               "val_counts": dict(val_counts), "train_counts": dict(train_counts),
               "val_gaps": {k: val_quota[k] - val_counts[k] for k in weights if val_quota[k] > val_counts[k]},
               "train_gaps": {k: train_quota[k] - train_counts[k] for k in weights if train_quota[k] > train_counts[k]},
               "training_released": False, "executable_val_ready": False,
               "note": "Proportional review candidates only. Source lineage, semantics, trajectory join/success and native runtime are unresolved; no short-trace selection or old-data fallback."}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
