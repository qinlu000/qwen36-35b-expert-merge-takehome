#!/usr/bin/env python3
"""Read four owner summaries every30s; stop only when all fixed scopes are scored."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
import statistics
import time

SOURCES = {
    "HLE": (2500, "artifacts/runs/hle_judge_v2_20261016/summary.json"),
    "ASI": (240, "artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json"),
    "SWE": (51, "artifacts/eval/base_swe_v2_20261016_final/final_summary.json"),
    "TB": (445, "artifacts/results/base-terminal-v2-recovery-20261016/final_summary.json"),
}
NOTES = {
    "HLE": "First-valid original821+infra1 selected1679; genuine solver-budget no-answer counts as zero. Judge uses school DeepSeek-V4-Flash, original criteria/JSONwrapper/4096/nonthinking; pending or invalid Judge is not a zero.",
    "ASI": "Public local240-condition score. Only soil b2 empty (3650,0) arrays violate public required(n_days,5): targeted hard-gate fail repair; original invalid retained, other239 unchanged. CMOS ngspice44.2 and native submission bwrap mappings documented; formal Judge0calls.",
    "SWE": "First environment-valid fresh replay of frozen patches. Restore native SIF PATH/private mini runtime; missing pytest/pip scores retained as infrastructure-invalid until repaired replay. Go uses exact verified official modules in native cache. Already complete answers are not regenerated.",
    "TB": "Five fixed seeds×89. Owner excludes verifier/bootstrap/tmux infrastructure failures from valid scores; private harness tools/native PATH/transport-deadline repairs preserve original prompts/tests/budget and old attempts. See owner source summary for accepted chronology and restoration disclosures.",
}


def utc(timestamp=None):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp is not None else datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def benchmark(project, name, expected, source):
    path = project / source
    row = {"expected": expected, "valid_scored": None, "unscored": None, "complete": False,
        "primary_score_percent": None, "source": str(path), "note": NOTES[name]}
    try:
        raw = read(path)
        row["source_mtime_utc"] = utc(path.stat().st_mtime)
        if name == "HLE":
            assert raw["expected"] == expected
            row.update(valid_scored=raw["scored"], unscored=raw["pending"],
                infrastructure_or_evaluator_invalid=raw["evaluation_invalid"],
                generation_terminal=raw["frozen_terminal_results"], judged_answers=raw["judged_answers"],
                native_no_answer=raw["native_no_answer"], correct=raw["correct"],
                subgroups=raw["subgroups"], budget_halted=raw["budget_halted"],
                judge_calls=raw["judge_generation_calls"], accounted_cny=raw["accounted_cost_cny"],
                cost_cap_cny=raw["max_cny"], source_updated_at=raw["updated_at_utc"])
            score = raw["score"]
        elif name == "ASI":
            assert raw["expected_instance_count"] == expected
            row.update(valid_scored=raw["scored_instance_count"],
                unscored=expected - raw["scored_instance_count"],
                infrastructure_or_evaluator_invalid=raw["scorer_error_count"],
                total_score=raw["total_score"], total_max_score=raw["total_max_score"],
                judge_calls=0, accounted_cny=0,
                repair_receipt=str(path.parent / "soil_empty_prediction_repair/receipt.json"))
            score = raw["mean_percent"]
        elif name == "SWE":
            assert raw["expected"] == expected
            row.update(valid_scored=raw["valid_scored"], unscored=raw["unscored"],
                infrastructure_or_evaluator_invalid=raw["invalid_pending"],
                awaiting_generation_or_replay=raw["awaiting_generation_or_replay"],
                resolved=raw["resolved"], source_updated_at=raw["as_of"],
                manual_retry_task_count=raw["manual_retry_task_count"],
                manual_retry_planned_task_count=raw["manual_retry_planned_task_count"],
                task_scores_csv=str(path.with_name("task_scores.csv")))
            score = raw["primary_score_percent"]
        else:
            assert raw["expected_trials"] == expected
            row.update(valid_scored=raw["valid_covered"], unscored=expected - raw["valid_covered"],
                infrastructure_or_evaluator_invalid=raw["infrastructure_unscored"],
                active_trials=raw["active_trials"], pending_not_admitted=raw["pending_not_admitted"],
                sample_sd_percent_ddof1=None, per_seed=[])
            for seed in sorted(raw["per_seed"], key=lambda item: item["seed"]):
                row["per_seed"].append({"seed": seed["seed"], "expected": 89,
                    "valid_scored": seed["valid_covered"], "correct": seed["correct_count"],
                    "score_percent": 100 * seed["correct_count"] / 89 if seed["valid_covered"] == 89 else None})
            assert [item["seed"] for item in row["per_seed"]] == list(range(5))
            ready = raw["complete"] and row["valid_scored"] == expected and all(
                seed["score_percent"] is not None for seed in row["per_seed"])
            values = [seed["score_percent"] for seed in row["per_seed"]]
            score = statistics.mean(values) if ready else None
            row["sample_sd_percent_ddof1"] = statistics.stdev(values) if ready else None
            row["owner_primary_mean_percent"] = raw["primary_mean_percent"]
            row["owner_sample_sd_percent_ddof1"] = raw["sample_sd_percent_ddof1"]
            row["first_valid_chronology"] = raw.get("first_valid_chronology")
        row["complete"] = bool(raw["complete"] and row["valid_scored"] == expected and score is not None)
        row["primary_score_percent"] = score if row["complete"] else None
    except (OSError, ValueError, KeyError, AssertionError) as error:
        row.update(complete=False, primary_score_percent=None,
                   source_unavailable_or_incompatible=type(error).__name__)
    return row


def report(project):
    rows = {name: benchmark(project, name, *spec) for name, spec in SOURCES.items()}
    result = {"updated_at_utc": utc(), "complete": all(row["complete"] for row in rows.values()),
        "benchmarks": rows, "combined_score": None,
        "combined_score_note": "Four different benchmark metrics are not averaged into one score.",
        "method": "Read owner summaries only; missing/infrastructure-invalid values never become scored zeros."}
    budget_path = project / "artifacts/runs/hle_judge_v2_20261016/budget.json"
    if budget_path.exists():
        ledger = read(budget_path)
        calls = list(ledger["calls"].values())
        result["hle_judge_cost"] = {"source": str(budget_path), "calls": len(calls),
            "settled_usage_cny": sum(item["charged_cny"] for item in calls if item["status"] == "completed"),
            "failed_or_inflight_reserved_cny": sum(item["charged_cny"] for item in calls if item["status"] != "completed"),
            "accounted_cny": sum(item["charged_cny"] for item in calls), "hard_limit_cny": ledger["max_cny"]}
    shared_path = project / "analysis/source_snapshots/night_api_budget_20261016.json"
    if shared_path.exists():
        shared = read(shared_path)
        result["shared_budget_receipt"] = {"source": str(shared_path),
            "night_limit_cny": shared["budget_cny"], "data_accounted_cny": shared["data_accounted_cny"],
            "asi_calibration_reserved_cny": shared["reservations_cny"]["asi_synthetic_judge_calibration"],
            "note": "Parent-maintained historical receipt; other writers do not share this collector's lock. GPU/resource fees are not priced here."}
    return result


def markdown(result):
    def number(value):
        return f"{value:.8f}%" if value is not None else "null（未完整有效评分）"
    lines = ["# Base baseline 持续最终汇总", "", "更新时间（UTC）：" + result["updated_at_utc"], "",
        "四项全部完成：" + ("是" if result["complete"] else "否"), "",
        "| Benchmark | 有效评分／固定分母 | 主成绩 | 未有效评分 |", "|---|---:|---:|---:|"]
    for name, row in result["benchmarks"].items():
        covered = row["valid_scored"] if row["valid_scored"] is not None else "待源summary"
        lines.append(f"| {name} | {covered}/{row['expected']} | {number(row['primary_score_percent'])} | {row['unscored']} |")
    tb = result["benchmarks"]["TB"]
    lines += ["", "TB 每seed固定89题；只有该seed89个有效结果齐全才给seed分。", "",
              "| Seed | 有效／89 | 正确数 | 分数 |", "|---|---:|---:|---:|"]
    for seed in tb.get("per_seed", []):
        lines.append(f"| {seed['seed']} | {seed['valid_scored']}/89 | {seed['correct']} | {number(seed['score_percent'])} |")
    lines += ["", "TB 五seed mean：" + number(tb["primary_score_percent"]),
              "TB sample SD（ddof=1，百分点）：" + str(tb.get("sample_sd_percent_ddof1")), ""]
    cost = result.get("hle_judge_cost")
    if cost:
        lines += [f"HLE Judge累计{cost['calls']}次；成功usage计费估算¥{cost['settled_usage_cny']:.8f}，失败／在途保守预留¥{cost['failed_or_inflight_reserved_cny']:.8f}，合计占用¥{cost['accounted_cny']:.8f}／硬限¥{cost['hard_limit_cny']:.2f}。校内公开价输入0.75／输出2.25元每百万token，非PBMS实账。", ""]
    shared = result.get("shared_budget_receipt")
    if shared:
        lines += [f"夜间API总限¥{shared['night_limit_cny']:.2f}；已记数据费用¥{sum(shared['data_accounted_cny'].values()):.8f}，ASI自造校准保守预留¥{shared['asi_calibration_reserved_cny']:.8f}，ASI正式Judge0次／¥0。GPU／HPC资源费用未包含。总账来源：`{shared['source']}`。", ""]
    for name, row in result["benchmarks"].items():
        lines += [f"**{name}**：{row['note']}", "", f"原始summary：`{row['source']}`；mtime UTC：{row.get('source_mtime_utc', '尚无文件')}。", ""]
        if row.get("source_unavailable_or_incompatible"):
            lines += ["源summary尚不可用／schema未满足：" + row["source_unavailable_or_incompatible"] + "，保留主score=null。", ""]
    lines += ["各benchmark独立计分，不合成未经定义的总分。此汇总器只读现成summary，每30秒更新；全部完整有效后自动退出。未调用模型／API、未扫描trial、未运行测试或hash。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / "collector.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shutil.copy2(__file__, output / "collector_source.py")
    save(output / "sources.json", {name: {"expected": spec[0], "source": spec[1]} for name, spec in SOURCES.items()})
    while True:
        result = report(args.project.resolve())
        save(output / "summary.json", result)
        temporary = output / "report.md.tmp"
        temporary.write_text(markdown(result))
        temporary.replace(output / "report.md")
        print(json.dumps({"updated_at_utc": result["updated_at_utc"], "complete": result["complete"],
            "coverage": {key: row["valid_scored"] for key, row in result["benchmarks"].items()}}), flush=True)
        if result["complete"] or args.once:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
