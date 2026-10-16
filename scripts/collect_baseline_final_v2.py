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
TB_CORRECTED_SOURCE = "artifacts/results/base-terminal-independent-repair32-20261016/corrected445_summary.json"
GAP_OUTPUT = "artifacts/results/base-gap-completion-20261017"
NOTES = {
    "HLE": "Retain all original answers and normal budget ends. At1424 outcomes, serving changed from max_num_seqs4 to20, with8 incomplete migration infrastructure retry2. User then requests server/client50; the next natural handoff transfers only never-started questions and adds no retry. Actual transitions are recorded separately. Queue time is inside the300s budget, so earlier timeouts cannot be interpreted as model ability alone. Judge uses school DeepSeek-V4-Flash and original criteria/JSONwrapper/4096/nonthinking; infrastructure-invalid outcomes are not zeros.",
    "ASI": "Public local240-condition single-shot/8K score, not Portal-certified. Of237 new answers,29 hit length8192;28 then failed with a leading code fence after native extraction fallback.49 runtime missing-import outcomes used the frozen declared-dependency task sandbox, which differs from default none/full host execution. These limits confound a broad model-ability interpretation. Soil b2 empty-array hard-gate repair and native adapters remain disclosed; formal Judge0calls.",
    "SWE": "Scoring is complete using the first environment-valid fresh replay of each frozen patch. Earlier28 generation tasks used legacy PATH/Python isolation; real agent self-tests hit missing pytest/jinja2/yaml. Repairing replay cannot restore lost agent feedback. The5/51 result is an affected historical run, not a clean model-comparison baseline. A separate outcome-independent clean rerun of all28 legacy tasks is required;23 tasks already used the corrected native runtime. Complete answers have not been regenerated within this run.",
    "TB": "Five fixed seeds×89. When available, the separate corrected445 summary reports the independent repair experiment: an outcome-independent frozen32 cohort uses3 original-answer grader-only recoveries and29 new generations. Original pending tasks transfer through natural handoff for their first admission, adding no repeated answers; later terminal unscored tasks join the same experiment without reward selection. Historical scores and their original summary remain separately traceable and are not overwritten. The legacy infrastructure_unscored field includes normal solver budget ends followed by failed verification or missing restorable state, not only network/infrastructure faults. Fixed prompts, seeds and budgets are retained; grader-only recovery requires verifier-relevant state review.",
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
    original_path = path
    recovered = project / GAP_OUTPUT / ('terminal_strict_summary.json' if name == 'TB' else 'swe51_summary.json')
    if name in ('TB', 'SWE') and recovered.exists():
        path = recovered
    elif name == "TB" and (project / TB_CORRECTED_SOURCE).exists():
        path = project / TB_CORRECTED_SOURCE
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
                task_scores_csv=str(path.with_name("task_scores.csv")),
                scoring_complete=bool(raw["complete"]), usable_as_clean_model_comparison=False,
                legacy_generation_environment_tasks=28, corrected_generation_environment_tasks=23,
                clean_generation_rerun_started=False)
            if path != original_path:
                historical = read(original_path)
                row.update(original_source=str(original_path),
                    original_primary_score_percent=historical['primary_score_percent'],
                    usable_as_clean_model_comparison=True, legacy28_replaced_as_fixed_cohort=True,
                    note='Fixed legacy28 were regenerated independently, all native23 retained; grade-only gap recovery preserves original patches and first valid zeros/ones. Historical affected5/51 remains separately available.')
                row['grade_only_replays_active'] = raw.get('grade_only_replays_active', 0)
                row['raw_native_reward_present_count'] = raw.get('raw_native_reward_present_count')
                row['complete_official_test_report_audits'] = raw.get('complete_official_test_report_audits', 0)
            clean_path = project / 'artifacts/eval/base_swe_v2_20261016_clean28/checkpoint.json'
            if clean_path.exists():
                clean = read(clean_path)
                corrected = read(clean_path.with_name('corrected51_summary.json'))
                row.update(clean_generation_rerun_started=True,
                    clean_generation_rerun_source=str(clean_path),
                    clean_generation_rerun_expected=28,
                    clean_generation_rerun_active=len(clean['active']),
                    clean_generation_rerun_pending=len(clean['pending']),
                    clean_generation_rerun_valid_scored=raw.get('clean28_valid_scored', clean['valid_scored']),
                    clean_generation_rerun_complete=(raw.get('clean28_valid_scored') == 28 if path != original_path else clean['complete']),
                    separate_corrected51_score_percent=(raw['primary_score_percent'] if path != original_path else corrected['primary_score_percent']))
            score = raw["primary_score_percent"]
        else:
            assert raw["expected_trials"] == expected
            if path != original_path:
                original = read(original_path)
                row.update(independent_repair_started=True, original_source=str(original_path),
                    original_source_mtime_utc=utc(original_path.stat().st_mtime),
                    original_valid_scored=original["valid_covered"],
                    original_primary_score_percent=original["primary_mean_percent"],
                    original_complete=original["complete"],
                    fixed_repair_cohort={"expected": 32, "grade_only": 3, "new_generation": 29},
                    later_unscored_selection="All terminal unscored outcomes, without reward selection",
                    pending_transfer_additional_answer_attempts=0)
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
            budget_path = project / GAP_OUTPUT / 'terminal_budget_summary.json'
            if budget_path.exists():
                budget = read(budget_path)
                row.update(harbor_budget_aggregation_source=str(budget_path),
                    harbor_budget_aggregation_complete=budget['complete'],
                    harbor_budget_mean_percent=budget['primary_mean_percent'],
                    harbor_budget_sample_sd_percent_ddof1=budget['sample_sd_percent_ddof1'],
                    native_reward_trials=budget['native_reward_trials'],
                    derived_candidate_compute_timeout_failures=budget['derived_timeout_failures'],
                    native_rewards_modified=False,
                    aggregation_note='Harbor default Mean maps None to zero. Only three independently audited candidate-computation900s timeouts are derived failures here; native rewards and strict coverage remain unchanged. Apply the same budget policy to every compared model.')
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
    if rows['SWE'].get('clean_generation_rerun_started'):
        result['complete'] = result['complete'] and rows['SWE']['clean_generation_rerun_complete']
    result['complete_under_disclosed_harbor_budget_aggregation'] = bool(
        all(rows[name]['complete'] for name in ('HLE', 'ASI', 'SWE'))
        and rows['TB'].get('harbor_budget_aggregation_complete'))
    migration_path = project / "artifacts/runs/base_hle_v2_724196_seq20/handoff-receipt.json"
    if migration_path.exists():
        migration = read(migration_path)
        rows["HLE"]["serving_transition"] = {"source": str(migration_path),
            "at_utc": migration["sigint_at_utc"], "retained_terminal_outcomes": migration["retained"],
            "selected_for_new_service": migration["selected"],
            "incomplete_migration_retries": len(migration["infra2_ids"]),
            "old_max_num_seqs": 4, "new_max_num_seqs": migration["route"]["engine_max_num_seqs"],
            "outer_solver_concurrency": migration["route"]["solver_concurrency"],
            "question_walltime_includes_queue": True}
        rows["HLE"]["serving_transitions"] = [rows["HLE"]["serving_transition"]]
    fifty_path = project / "artifacts/runs/base_hle_v2_724196_seq50/handoff-receipt.json"
    if fifty_path.exists():
        fifty = read(fifty_path)
        rows["HLE"]["serving_transitions"].append({"source": str(fifty_path),
            "at_utc": fifty["at_utc"], "retained_terminal_outcomes": fifty["retained"],
            "selected_for_new_service": fifty["selected"], "old_max_num_seqs": 20,
            "new_max_num_seqs": 50, "outer_solver_concurrency": 50,
            "additional_manual_retries": 0, "question_walltime_includes_queue": True})
    budget_path = project / "artifacts/runs/hle_judge_v2_20261016/budget.json"
    if budget_path.exists():
        ledger = read(budget_path)
        calls = list(ledger["calls"].values())
        result["hle_judge_cost"] = {"source": str(budget_path), "calls": len(calls),
            "settled_usage_cny": sum(item["charged_cny"] for item in calls if item["status"] == "completed"),
            "failed_or_inflight_reserved_cny": sum(item["charged_cny"] for item in calls if item["status"] != "completed"),
            "accounted_cny": sum(item["charged_cny"] for item in calls), "hard_limit_cny": ledger["max_cny"]}
        recovery_path = budget_path.parent / 'single-judge-recovery-20261017/budget.json'
        if recovery_path.exists():
            recovery = read(recovery_path)
            result['hle_judge_cost']['calls'] += 1
            result['hle_judge_cost']['accounted_cny'] += recovery['charged_cny']
            key = 'settled_usage_cny' if recovery['status'] == 'completed' else 'failed_or_inflight_reserved_cny'
            result['hle_judge_cost'][key] += recovery['charged_cny']
            result['hle_judge_cost']['recovery_ledger'] = str(recovery_path)
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
        "严格原生评分齐备：" + ("是" if result["complete"] else "否"), "",
        "按披露的Harbor固定预算聚合齐备：" + ("是" if result.get('complete_under_disclosed_harbor_budget_aggregation') else "否"), "",
        "| Benchmark | 有效评分／固定分母 | 主成绩 | 未有效评分 |", "|---|---:|---:|---:|"]
    for name, row in result["benchmarks"].items():
        covered = row["valid_scored"] if row["valid_scored"] is not None else "待源summary"
        lines.append(f"| {name} | {covered}/{row['expected']} | {number(row['primary_score_percent'])} | {row['unscored']} |")
    swe = result['benchmarks']['SWE']
    if swe.get('clean_generation_rerun_started'):
        if swe.get('legacy28_replaced_as_fixed_cohort'):
            lines += ['', f"SWE 上表为固定28整组替换并补评分后的独立51项结果；原生成环境受影响的历史成绩保留在 `{swe['original_source']}`。独立clean28已有{swe['clean_generation_rerun_valid_scored']}/28有效，当前仅补评在途{swe.get('grade_only_replays_active', 0)}。", '']
            if swe.get('complete_official_test_report_audits'):
                lines += [f"其中{swe['raw_native_reward_present_count']}项有原生reward；另1项NodeBB已完整解析311个官方测试（307通过、4失败），单独审定失败，其原始reward仍null，保留全部输出和清理记录。", '']
        else:
            lines += ['', f"SWE 上表保留受旧生成环境干扰的历史成绩。独立 clean28：{swe['clean_generation_rerun_valid_scored']}/28 有效评分，{swe['clean_generation_rerun_active']} 项在途，{swe['clean_generation_rerun_pending']} 项待准入；整组替换后的独立51项成绩：{number(swe['separate_corrected51_score_percent'])}。", '']
    tb = result["benchmarks"]["TB"]
    lines += ["", "TB 每seed固定89题；只有该seed89个有效结果齐全才给seed分。", "",
              "| Seed | 有效／89 | 正确数 | 分数 |", "|---|---:|---:|---:|"]
    for seed in tb.get("per_seed", []):
        lines.append(f"| {seed['seed']} | {seed['valid_scored']}/89 | {seed['correct']} | {number(seed['score_percent'])} |")
    lines += ["", "TB 五seed mean：" + number(tb["primary_score_percent"]),
              "TB sample SD（ddof=1，百分点）：" + str(tb.get("sample_sd_percent_ddof1")), ""]
    if 'harbor_budget_aggregation_complete' in tb:
        lines += ["TB Harbor默认固定预算mean：" + number(tb['harbor_budget_mean_percent']),
            f"原生reward覆盖{tb['native_reward_trials']}/445；另{tb['derived_candidate_compute_timeout_failures']}项已核实的候选计算超时按默认Mean规则聚合为失败，原始reward仍null。", ""]
    cost = result.get("hle_judge_cost")
    if cost:
        lines += [f"HLE Judge累计{cost['calls']}次；成功usage计费估算¥{cost['settled_usage_cny']:.8f}，失败／在途保守预留¥{cost['failed_or_inflight_reserved_cny']:.8f}，合计占用¥{cost['accounted_cny']:.8f}／硬限¥{cost['hard_limit_cny']:.2f}。校内公开价输入0.75／输出2.25元每百万token，非PBMS实账。", ""]
    shared = result.get("shared_budget_receipt")
    if shared:
        lines += [f"夜间API总限¥{shared['night_limit_cny']:.2f}；已记数据费用¥{sum(shared['data_accounted_cny'].values()):.8f}，ASI自造校准保守预留¥{shared['asi_calibration_reserved_cny']:.8f}，ASI正式Judge0次／¥0。GPU／HPC资源费用未包含。总账来源：`{shared['source']}`。", ""]
    for name, row in result["benchmarks"].items():
        lines += [f"**{name}**：{row['note']}", "", f"汇总来源：`{row['source']}`；mtime UTC：{row.get('source_mtime_utc', '尚无文件')}。", ""]
        if row.get("independent_repair_started"):
            lines += [f"TB 历史原run summary：`{row['original_source']}`；有效评分{row['original_valid_scored']}/445，历史主成绩：{number(row['original_primary_score_percent'])}。上表使用独立修复后的corrected445来源；历史评分文件保留。", ""]
        if row.get("source_unavailable_or_incompatible"):
            lines += ["源summary尚不可用／schema未满足：" + row["source_unavailable_or_incompatible"] + "，保留主score=null。", ""]
    lines += ["各benchmark独立计分，不合成未经定义的总分。此汇总器只读现成summary，每30秒更新；全部完整或已披露的固定预算口径齐备后自动退出，严格原生覆盖仍分别记录。未调用模型／API、未扫描trial、未运行测试或hash。"]
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
    sources = {name: {"expected": spec[0], "source": spec[1]} for name, spec in SOURCES.items()}
    sources["TB"].update(preferred_source=TB_CORRECTED_SOURCE, original_source=SOURCES["TB"][1])
    save(output / "sources.json", sources)
    while True:
        result = report(args.project.resolve())
        save(output / "summary.json", result)
        temporary = output / "report.md.tmp"
        temporary.write_text(markdown(result))
        temporary.replace(output / "report.md")
        print(json.dumps({"updated_at_utc": result["updated_at_utc"], "complete": result["complete"],
            "coverage": {key: row["valid_scored"] for key, row in result["benchmarks"].items()}}), flush=True)
        if result["complete"] or result['complete_under_disclosed_harbor_budget_aggregation'] or args.once:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
