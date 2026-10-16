#!/usr/bin/env python3
"""One authorised grading-only recovery; preserve the frozen HLE answer."""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import shutil


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text())


def save(path, row):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def run(args):
    parent = args.output.resolve()
    recovery = parent / "single-judge-recovery-20261017"
    recovery.mkdir(exist_ok=True)
    lock = (parent / "controller.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    task = "672ecc6946f619ca9b0495c5"
    result_path = parent / "results" / (task + ".json")
    previous = load(result_path)
    assert previous["evaluation_status"] == "evaluation_invalid"
    assert not (recovery / "request.json").exists(), "A recovery request may not be sent twice"
    spec = importlib.util.spec_from_file_location("frozen_hle_scorer", parent / "scorer_rolling_source.py")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    for attempt in (1, 2):
        raw = load(parent / "responses" / f"{task}.{attempt}.json")
        body = json.loads(raw["body"])
        choice = body["choices"][0]
        assert choice["finish_reason"] == "length"
        try:
            source.parse_judge(choice["message"]["content"])
        except (ValueError, AssertionError):
            pass
        else:
            raise RuntimeError("Original response is already parseable; do not issue another request")
    shutil.copy2(result_path, recovery / "original-invalid-result.json")
    shutil.copy2(parent / "summary.json", recovery / "original-incomplete-summary.json")
    item = load(parent / "inputs" / (task + ".json"))
    payload = load(parent / "requests" / f"{task}.1.json")
    original_system = payload["messages"][0]["content"]
    payload["messages"][0]["content"] += (
        " Serialize keys in this order: correct, confidence, strict, extracted_final_answer, reasoning."
        " Keep reasoning to one short sentence of at most 40 words; do not repeat the response or solve the problem."
        " Finish the JSON object immediately after that sentence."
    )
    assert payload["max_tokens"] == 4096 and payload["seed"] == 0 and payload["temperature"] == 0
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["messages"][1] == load(parent / "requests" / f"{task}.2.json")["messages"][1]
    ledger = load(parent / "budget.json")
    original_spend = sum(x["charged_cny"] for x in ledger["calls"].values())
    bound = sum(len(m["content"].encode()) for m in payload["messages"]) + 1024
    reserved = (bound * source.INPUT_PRICE + 4096 * source.OUTPUT_PRICE) / 1e6
    assert original_spend + reserved <= 10 and len(ledger["calls"]) + 1 <= 5000
    row = {"call": task + ".authorised-recovery1", "status": "reserved", "charged_cny": reserved,
        "reserved_cny": reserved, "original_accounted_cost_cny": original_spend,
        "combined_max_cny": 10, "max_calls_this_recovery": 1, "started_at_utc": now(),
        "reason": "User authorised completing the one invalid grader result; no solver regeneration",
        "input_token_bound": bound, "output_token_cap": 4096}
    save(recovery / "budget.json", row)
    save(recovery / "request.json", payload)
    save(recovery / "protocol.json", {"task_id": task, "original_system": original_system,
        "wrapper_change": "Same five-key schema; short reasoning, verdict fields serialized first",
        "question_gold_answer_criteria_and_solver_response_unchanged": True,
        "original_attempts_parseable": False, "original_attempts_preserved": True,
        "original_failed_requests_share_same_provider_request_id": True})
    credentials = {}
    for line in args.credentials.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            credentials[key.strip()] = value.strip().strip("\"'")
    assert credentials["OPENAI_BASE_URL"].rstrip("/") == "https://" + source.HOST + "/v1"
    connection = source.SchoolTLS(args.tls_tunnel_port)
    try:
        connection.request("POST", "/v1/chat/completions", json.dumps(payload, ensure_ascii=False).encode(),
            {"Authorization": "Bearer " + credentials["OPENAI_API_KEY"], "Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read().decode("utf-8")
        save(recovery / "response.json", {"http_status": response.status, "body": raw, "at_utc": now()})
        assert response.status == 200, "Judge request failed; retained invalid"
        body = json.loads(raw)
        message = body["choices"][0]["message"]
        assert not message.get("reasoning_content") and not message.get("reasoning")
        identity = {"requested_model": source.MODEL, "reported_model": body.get("model"),
            "system_fingerprint": body.get("system_fingerprint"), "provider_revision_pinned": False}
        assert identity == load(parent / "judge_identity.json"), "Judge identity changed; retained invalid"
        parsed = source.parse_judge(message["content"])
        usage = body["usage"]
        assert 0 <= usage["prompt_tokens"] <= bound and 0 <= usage["completion_tokens"] <= 4096
        row.update(status="completed", charged_cny=(usage["prompt_tokens"] * source.INPUT_PRICE
            + usage["completion_tokens"] * source.OUTPUT_PRICE) / 1e6, usage=usage, finished_at_utc=now())
        save(recovery / "budget.json", row)
        result = {"id": task, "evaluation_status": "judged", "correct": parsed["correct"] == "yes",
            "judge_response": parsed, "judge_calls": 3, "source_result": item["source_result"],
            "is_image": item["is_image"], "reported_identity": identity, "usage": usage,
            "finished_at_utc": now(), "grader_only_recovery": str(recovery),
            "original_invalid_result": str(recovery / "original-invalid-result.json")}
        save(recovery / "result.json", result)
        save(result_path, result)
        results = [load(f) for f in (parent / "results").glob("*.json")]
        valid = [r for r in results if r["evaluation_status"] in ("judged", "native_no_answer")]
        assert len(valid) == 2500
        summary = load(recovery / "original-incomplete-summary.json")
        correct = sum(r["correct"] for r in valid)
        summary.update(complete=True, judged_answers=sum(r["evaluation_status"] == "judged" for r in results),
            evaluation_invalid=0, scored=2500, pending=0, correct=correct, accuracy_percent=round(100 * correct / 2500, 2),
            score=100 * correct / 2500, partial_correct_over_full_denominator_percent=100 * correct / 2500,
            judge_generation_calls=len(ledger["calls"]) + 1, accounted_cost_cny=original_spend + row["charged_cny"],
            updated_at_utc=now(), grader_only_recovery=str(recovery), recovery_judge_calls=1,
            original_budget_ledger_unchanged=True, recovery_budget=str(recovery / "budget.json"))
        for name, image in (("text", False), ("image", True)):
            group = [r for r in valid if r["is_image"] == image]
            summary["subgroups"][name].update(scored=len(group), correct=sum(r["correct"] for r in group),
                accuracy_percent=round(100 * sum(r["correct"] for r in group) / summary["subgroups"][name]["denominator"], 2))
        save(parent / "summary.json", summary)
        save(recovery / "completed-summary.json", summary)
        print(json.dumps(summary), flush=True)
    except Exception as error:
        row.update(status="failed_full_reservation", error_type=type(error).__name__, error=str(error), finished_at_utc=now())
        save(recovery / "budget.json", row)
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, default=Path("/data/caoqinlu/projects/data-perception/.env"))
    parser.add_argument("--tls-tunnel-port", type=int, default=28443)
    run(parser.parse_args())
