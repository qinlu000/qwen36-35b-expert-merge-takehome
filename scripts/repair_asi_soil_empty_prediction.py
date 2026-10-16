#!/usr/bin/env python3
"""Re-score only the frozen soil b2 empty-array case; never call a model."""
import argparse
import difflib
import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import numpy as np

TASK = "earth_science.2_e_soil_carbon_nitrogen_cycling"
CONDITION = TASK + "__seed31415__b2"
FILES = ("results/carbon_pools.npy", "results/nitrogen_pools.npy")


def run(project, output):
    runtime = output / "runtime"
    sys.path[:0] = [str(runtime), str(runtime / "scripts")]
    from ai4sci_bench.local_scoring import (
        _prepare_score_jobs, _prepare_score_runtimes, _evaluate_score_job)
    from ai4sci_bench.scorers.file_match import FileMatchScorer
    from score_asi_baseline_v2 import build_report
    from asi_score_transport import write_json

    lock = (output / ".run.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    repair = output / "soil_empty_prediction_repair"
    repair.mkdir(mode=0o700, exist_ok=True)
    receipt_path = repair / "receipt.json"
    if receipt_path.exists():
        print(receipt_path.read_text())
        return

    report_path = output / "local_score_seed31415.json"
    condition_path = output / "conditions" / (CONDITION + ".json")
    report = json.loads(report_path.read_text())
    old = json.loads(condition_path.read_text())
    assert report["scored_instance_count"] == 239 and report["scorer_error_count"] == 1
    assert len(report["results"]) == 240 and report["pending_count"] == 0
    assert old["evaluation_status"] == "evaluation_invalid"
    assert old["gate_results"][2]["details"]["exception_type"] == "ValueError"
    assert "zero-size array" in old["gate_results"][2]["message"]
    shutil.copy2(report_path, repair / "report_before.json")
    shutil.copy2(condition_path, repair / "condition_before.json")

    config = json.loads((output / "scoring_config.json").read_text())
    selection_path = project / "artifacts/eval/base_asi_v2_20261016_infra1/first_valid_selection.json"
    selection = json.loads(selection_path.read_text())
    result_path = Path(next(row["result"] for row in selection["entries"]
                            if row["condition"] == CONDITION))
    raw = json.loads(result_path.read_text())
    metadata = project / "artifacts/asi/instances_seed31415" / (TASK + "__seed31415")
    if not raw.get("parameters"):
        raw = dict(raw, parameters=json.loads((metadata / "framework_task_info.json").read_text())["parameters"])
    prompt = metadata / "prompt_b2.md"
    prompt_lines = prompt.read_text().splitlines()
    assert all(any(name in line and "(n_days, 5)" in line for line in prompt_lines)
               for name in FILES)
    job = _prepare_score_jobs([(result_path, raw)], results_root=Path(config["results"]),
        instances_root=Path(config["instances"]), tasks_root=Path(config["tasks"]))[0]
    assert job.task_id == TASK and job.prompt_level == "b2"
    job = _prepare_score_runtimes([job], tasks_root=Path(config["tasks"]))[0]
    checks = []
    original = FileMatchScorer._check_value_range

    def soil_empty_gate(self, pred_dir, check):
        name = check.get("file")
        if name in FILES and check == {"check": "value_range", "file": name, "min": 0.0}:
            arr = np.load(pred_dir / name)
            if arr.size == 0:
                evidence = {"passed": False, "check": "value_range", "file": name,
                    "actual_shape": list(arr.shape), "required_pool_columns": 5,
                    "failure_kind": "empty_prediction_contract_violation",
                    "message": "Empty prediction violates public prompt required shape (n_days, 5)"}
                checks.append(evidence)
                return evidence
        return original(self, pred_dir, check)

    with (patch.object(FileMatchScorer, "_check_value_range", soil_empty_gate),
          patch("litellm.completion", side_effect=RuntimeError("This repair prohibits Judge API calls")) as api):
        native = _evaluate_score_job(job, None)
    assert api.call_count == 0 and len(checks) == 2
    assert native["evaluation_status"] == "completed" and not native["hard_gates_passed"]
    assert native["final_score"] == 0.0 and not native["score_results"]
    row = dict(old)
    row.update(native)
    row.update(condition=CONDITION, attempt=old["attempt"] + 1,
               local_gate_repair="soil_empty_prediction_repair/receipt.json")
    row.pop("native_final_score", None)
    row.pop("failure_kind", None)
    results = [row if item["condition"] == CONDITION else item for item in report["results"]]
    expected = [(item["task_id"], item["prompt_level"], item["condition"]) for item in results]
    updated = build_report(results, expected, report["mode"])
    updated["synthetic_calibration"] = report["synthetic_calibration"]
    updated["local_gate_repairs"] = ["soil_empty_prediction_repair/receipt.json"]
    assert updated["complete"] and updated["scored_instance_count"] == 240
    assert updated["total_score"] == report["total_score"]
    unchanged = sum(a == b for a, b in zip(report["results"], results))
    assert unchanged == 239
    source = Path(__file__).read_text()
    (repair / "source_patch.diff").write_text("".join(difflib.unified_diff(
        [], source.splitlines(keepends=True), fromfile="/dev/null",
        tofile="scripts/repair_asi_soil_empty_prediction.py")))
    shutil.copy2(__file__, repair / "repair_adapter.py")
    receipt = {"status": "completed", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "condition": CONDITION, "repair_scope": "Only this condition, two named prediction files, size==0",
        "original_exception": old["gate_results"][2]["message"],
        "public_contract": {"prompt": str(prompt), "lines": [43, 44], "shape": "(n_days, 5)",
            "gate": str(Path(job.task_dir) / "task_eval.yaml") + ":21-30",
            "crash": "ai4sci_bench/scorers/file_match.py:137-146",
            "hard_fail_zero": "ai4sci_bench/core/scoring.py:158-167"},
        "empty_prediction_checks": checks, "final_score": native["final_score"],
        "official_source_modified": False, "rubric_threshold_gold_modified": False,
        "unrelated_evaluator_exceptions_mapped_to_zero": False,
        "other_condition_records_preserved": unchanged, "generation_calls": 0,
        "judge_api_calls": api.call_count, "judge_api_cost_cny": 0, "new_hash_walks": 0,
        "original_invalid": str(repair / "condition_before.json"),
        "original_report": str(repair / "report_before.json"),
        "source_patch": str(repair / "source_patch.diff"),
        "report": str(report_path), "score_status": "Complete public local score with documented gate crash repair"}
    write_json(repair / "condition_after.json", row)
    write_json(repair / "report_after.json", updated)
    write_json(condition_path, row)
    write_json(report_path, updated)
    write_json(receipt_path, receipt)
    print(json.dumps({key: updated[key] for key in ("complete", "scored_instance_count",
        "scorer_error_count", "pending_count", "mean_percent", "total_score")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.project.resolve(), args.output.resolve())
