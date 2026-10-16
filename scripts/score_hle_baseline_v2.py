#!/usr/bin/env python3
"""Stream the frozen HLE first-valid selection through the fixed local Judge."""
import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import threading
import time

HOST = "aigc-api.hkust-gz.edu.cn"
MODEL = "DeepSeek-V4-Flash"
INPUT_PRICE, OUTPUT_PRICE = 0.75, 2.25  # CNY per million tokens, HKUST(GZ).


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def load(path):
    return json.loads(path.read_text())


class SchoolTLS(http.client.HTTPSConnection):
    def __init__(self, port):
        super().__init__(HOST, 443, timeout=300, context=ssl.create_default_context())
        self.forward_port = port

    def connect(self):
        sock = socket.create_connection(("127.0.0.1", self.forward_port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=HOST)


class Budget:
    def __init__(self, output, maximum, calls):
        self.output, self.maximum, self.calls = output, maximum, calls
        self.thread_lock = threading.Lock()

    def transaction(self, change=None):
        with self.thread_lock, (self.output / "budget.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = self.output / "budget.json"
            ledger = load(path) if path.exists() else {"calls": {}, "max_cny": self.maximum,
                "max_calls": self.calls, "prices_cny_per_million": {"input": INPUT_PRICE, "output": OUTPUT_PRICE}}
            assert ledger["max_cny"] == self.maximum and ledger["max_calls"] == self.calls
            if change:
                change(ledger)
                save(path, ledger)
            return ledger

    def reserve(self, call, bound):
        def change(ledger):
            cost = (bound * INPUT_PRICE + 4096 * OUTPUT_PRICE) / 1e6
            accounted = sum(row["charged_cny"] for row in ledger["calls"].values())
            if call in ledger["calls"]:
                raise RuntimeError("A started Judge request cannot be sent twice")
            if len(ledger["calls"]) >= self.calls or accounted + cost > self.maximum:
                raise BudgetExhausted()
            ledger["calls"][call] = {"status": "reserved", "input_token_bound": bound,
                "output_token_cap": 4096, "reserved_cny": cost, "charged_cny": cost, "started_at": now()}
        self.transaction(change)

    def finish(self, call, success, usage):
        def change(ledger):
            row = ledger["calls"][call]
            row.update(status="completed" if success else "failed_full_reservation", finished_at=now(), usage=usage)
            if success and usage:
                prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
                if isinstance(prompt, int) and isinstance(completion, int):
                    if prompt > row["input_token_bound"] or completion > 4096:
                        save(self.output / "stop.json", {"reason": "usage_exceeded_reserved_bound", "call": call})
                        raise RuntimeError("Provider usage exceeded the pre-reserved bound")
                    row["charged_cny"] = (prompt * INPUT_PRICE + completion * OUTPUT_PRICE) / 1e6
        self.transaction(change)


class BudgetExhausted(Exception):
    pass


def parse_judge(content):
    row = json.loads(content)
    assert set(row) == {"extracted_final_answer", "reasoning", "correct", "confidence", "strict"}
    assert isinstance(row["extracted_final_answer"], str) and isinstance(row["reasoning"], str)
    assert row["correct"] in ("yes", "no") and row["strict"] is True
    assert type(row["confidence"]) is int and 0 <= row["confidence"] <= 100
    return row


def run(args):
    project, output = args.project.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (output / "controller.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for name in ("inputs", "results", "requests", "responses"):
        (output / name).mkdir(exist_ok=True)
    protocol = load(project / "configs/eval/protocol_v2_unified64k8k.json")
    cfg = protocol["benchmarks"]["hle"]
    criteria = (project / cfg["judge"]["criteria_prompt"]).read_text().rstrip("\n")
    system = (project / cfg["judge"]["json_system_prompt"]).read_text().rstrip("\n")
    official = project / "artifacts/benchmarks/hle/source/hle_eval/run_judge_results.py"
    original = next(ast.literal_eval(node.value) for node in ast.parse(official.read_text()).body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "JUDGE_PROMPT"
                                               for target in node.targets))
    assert criteria == original and cfg["judge"]["max_tokens"] == 4096
    manifest = load(args.retry / "manual_retry_manifest.json")
    order = load(project / cfg["task_manifest"])["task_ids"]
    entries = {row["id"]: row for row in manifest["retained"] + manifest["selected"]}
    assert len(entries) == len(order) == 2500 and set(entries) == set(order)
    import pyarrow.parquet as pq
    data = project / "artifacts/benchmarks/hle" / cfg["dataset_revision"] / "test-00000-of-00001.parquet"
    questions = {row["id"]: row for row in pq.read_table(data, columns=["id", "question", "answer", "image"]).to_pylist()}
    assert set(questions) == set(order)
    config = {"model": MODEL, "endpoint": "https://" + HOST + "/v1/chat/completions",
        "tls_tunnel_port": args.tls_tunnel_port, "tls_sni_and_host": HOST, "verify_ca": True,
        "temperature": 0, "seed": 0, "thinking": False, "max_tokens": 4096,
        "criteria": criteria, "json_wrapper": system, "max_attempts_per_answer": 2,
        "source_revision": cfg["code_revision"], "dataset_revision": cfg["dataset_revision"],
        "selection_rule": manifest["selection_rule"], "gold_policy": "grader only; never passed to the solver",
        "judge_change": "HKUST(GZ) DeepSeek-V4-Flash; separate provider from the earlier external deepseek-flash alias",
        "price_cny_per_million": {"input": INPUT_PRICE, "output": OUTPUT_PRICE},
        "price_source": "https://docs.hpc.hkust-gz.edu.cn/docs/aigc/api-model-list/",
        "max_cny": args.max_cny, "max_calls": args.max_calls, "workers": args.workers,
        "budget_rule": "Pre-reserve UTF8 text bytes+1024 framing and4096 output; successful validated usage settles; failed requests retain full reservation"}
    config_path = output / "scoring_config.json"
    if config_path.exists():
        assert load(config_path) == config
    else:
        save(config_path, config)
        shutil.copy2(__file__, output / "scorer_source.py")
    frozen = {path.stem: load(path) for path in (output / "inputs").glob("*.json")}
    results = {path.stem: load(path) for path in (output / "results").glob("*.json")}
    selections = {}
    budget = Budget(output, args.max_cny, args.max_calls)
    key = None
    identity_lock = threading.Lock()
    budget_halted = threading.Event()

    def collect():
        for task_id in order:
            entry = entries[task_id]
            path = (args.retry / "questions" / (task_id + ".json")
                    if entry["manual_retry_index"] else Path(entry["original_result"]))
            selections[task_id] = {"id": task_id, "path": str(path),
                "manual_retry_index": entry["manual_retry_index"], "state": "pending_generation"}
            if task_id in frozen:
                selections[task_id]["state"] = frozen[task_id]["kind"]
                continue
            if not path.is_file():
                continue
            record = load(path)
            if not record.get("finished_at_utc"):
                continue  # A received-answer checkpoint is not a final terminal record.
            if record.get("infrastructure_failure"):
                selections[task_id]["state"] = "generation_infrastructure_invalid"
                continue
            is_timeout = (record.get("error_type") in ("TimeoutError", "ReadTimeout") and not record.get("raw_response")
                          and record.get("elapsed_seconds", 0) >= 299)
            if record.get("status") == "completed" and isinstance(record.get("response"), str):
                kind = "answer"
            elif is_timeout or record.get("status") == "context_overflow":
                kind = "native_no_answer"
            else:
                selections[task_id]["state"] = "generation_protocol_invalid"
                continue
            question = questions[task_id]
            item = {"id": task_id, "source_result": str(path), "manual_retry_index": entry["manual_retry_index"],
                "kind": kind, "is_image": bool(question["image"]), "question": question["question"],
                "correct_answer": question["answer"], "response": record.get("response"),
                "generation_status": record["status"], "generation_error_type": record.get("error_type"),
                "frozen_at": now()}
            save(output / "inputs" / (task_id + ".json"), item)
            frozen[task_id] = item
            selections[task_id]["state"] = kind
            if kind == "native_no_answer":
                row = {"id": task_id, "evaluation_status": "native_no_answer", "correct": False,
                    "reason": "No valid prediction within the original solver budget; retained in2500 denominator",
                    "judge_calls": 0, "source_result": str(path), "is_image": item["is_image"]}
                results[task_id] = row
                save(output / "results" / (task_id + ".json"), row)
        save(output / "first_valid_selection.json", {"expected": 2500, "selection_rule": manifest["selection_rule"],
            "entries": [selections[i] for i in order]})

    def summary():
        valid = [row for row in results.values() if row["evaluation_status"] in ("judged", "native_no_answer")]
        correct = sum(row["correct"] for row in valid)
        ledger = budget.transaction()
        charges = sum(row["charged_cny"] for row in ledger["calls"].values())
        complete = len(valid) == 2500
        groups = {}
        for name, image, total in (("text", False, 2158), ("image", True, 342)):
            rows = [row for row in valid if row["is_image"] == image]
            groups[name] = {"denominator": total, "scored": len(rows), "correct": sum(row["correct"] for row in rows),
                "accuracy_percent": round(100 * sum(row["correct"] for row in rows) / total, 2) if len(rows) == total else None}
        result = {"complete": complete, "expected": 2500, "frozen_terminal_results": len(frozen),
            "judged_answers": sum(row["evaluation_status"] == "judged" for row in results.values()),
            "native_no_answer": sum(row["evaluation_status"] == "native_no_answer" for row in results.values()),
            "evaluation_invalid": sum(row["evaluation_status"] == "evaluation_invalid" for row in results.values()),
            "scored": len(valid), "pending": 2500 - len(valid), "correct": correct,
            "accuracy_percent": round(100 * correct / 2500, 2) if complete else None,
            "score": 100 * correct / 2500 if complete else None,
            "partial_correct_over_full_denominator_percent": 100 * correct / 2500,
            "subgroups": groups, "selection_states": dict(Counter(row["state"] for row in selections.values())),
            "judge_generation_calls": len(ledger["calls"]), "accounted_cost_cny": charges,
            "budget_halted": budget_halted.is_set(),
            "max_cny": args.max_cny, "max_calls": args.max_calls, "updated_at_utc": now(),
            "provider": MODEL, "official": False, "metric": "Official HLE fixed2500 denominator accuracy; replacement Judge disclosed"}
        save(output / "summary.json", result)
        print(json.dumps(result), flush=True)
        return result

    def grade(task_id):
        item = frozen[task_id]
        prompt = criteria.format(question=item["question"], correct_answer=item["correct_answer"], response=item["response"])
        payload = {"model": MODEL, "messages": [{"role": "system", "content": system},
            {"role": "user", "content": prompt}], "temperature": 0, "seed": 0, "max_tokens": 4096,
            "thinking": {"type": "disabled"}, "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_object"}}
        body = json.dumps(payload, ensure_ascii=False).encode()
        bound = len(system.encode()) + len(prompt.encode()) + 1024
        attempts = [row for call, row in budget.transaction()["calls"].items() if call.startswith(task_id + ".")]
        for attempt in range(len(attempts) + 1, 3):
            if budget_halted.is_set() or (output / "stop.json").exists():
                return None
            call = task_id + "." + str(attempt)
            try:
                budget.reserve(call, bound)
            except BudgetExhausted:
                budget_halted.set()
                return None
            save(output / "requests" / (call + ".json"), payload)
            usage, success = None, False
            connection = SchoolTLS(args.tls_tunnel_port)
            try:
                connection.request("POST", "/v1/chat/completions", body,
                    {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
                response = connection.getresponse()
                raw = response.read()
                saved = {"http_status": response.status, "body": raw.decode("utf-8", errors="replace"), "at_utc": now()}
                save(output / "responses" / (call + ".json"), saved)
                if response.status in (401, 403):
                    save(output / "stop.json", {"reason": "credential_or_permission_error", "http_status": response.status})
                if response.status != 200:
                    raise RuntimeError("Judge HTTP" + str(response.status))
                data = json.loads(raw)
                usage = data.get("usage")
                message = data["choices"][0]["message"]
                if message.get("reasoning_content") or message.get("reasoning"):
                    save(output / "stop.json", {"reason": "nonthinking_protocol_not_honored", "call": call})
                    raise RuntimeError("Nonthinking protocol not honored")
                identity = {"requested_model": MODEL, "reported_model": data.get("model"),
                    "system_fingerprint": data.get("system_fingerprint"), "provider_revision_pinned": False}
                with identity_lock:
                    identity_path = output / "judge_identity.json"
                    if identity_path.exists() and load(identity_path) != identity:
                        save(output / "stop.json", {"reason": "judge_identity_drift", "call": call, "observed": identity})
                        raise RuntimeError("Judge identity drift")
                    save(identity_path, identity)
                parsed = parse_judge(message["content"])
                row = {"id": task_id, "evaluation_status": "judged", "correct": parsed["correct"] == "yes",
                    "judge_response": parsed, "judge_calls": attempt, "source_result": item["source_result"],
                    "is_image": item["is_image"], "reported_identity": identity, "usage": usage, "finished_at_utc": now()}
                success = True
                save(output / "results" / (task_id + ".json"), row)
                return row
            except Exception as error:
                save(output / "responses" / (call + ".error.json"), {"error_type": type(error).__name__, "at_utc": now()})
            finally:
                connection.close()
                budget.finish(call, success, usage)
        row = {"id": task_id, "evaluation_status": "evaluation_invalid", "correct": None,
            "reason": "Both allowed Judge attempts failed; never a scored zero", "is_image": item["is_image"],
            "source_result": item["source_result"], "judge_calls": len(attempts) if len(attempts) >= 2 else 2}
        save(output / "results" / (task_id + ".json"), row)
        return row

    collect()
    summary()
    if args.collect_only:
        return
    credentials = {}
    for line in args.credentials.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            credentials[name.strip()] = value.strip().strip("\"'")
    key = credentials["OPENAI_API_KEY"]
    assert credentials["OPENAI_BASE_URL"].rstrip("/") == "https://" + HOST + "/v1"
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        while True:
            todo = [] if budget_halted.is_set() else [task_id for task_id in order if task_id in frozen and task_id not in results]
            futures = {pool.submit(grade, task_id): task_id for task_id in todo}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results[result["id"]] = result
                summary()
            state = summary()
            if state["complete"] or args.once or (output / "stop.json").exists():
                break
            if len(frozen) == 2500 and (not todo or budget_halted.is_set()):
                break
            time.sleep(args.poll_seconds)
            collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--retry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, default=Path("/data/caoqinlu/projects/data-perception/.env"))
    parser.add_argument("--tls-tunnel-port", type=int, default=28443)
    parser.add_argument("--max-cny", type=float, default=10)
    parser.add_argument("--max-calls", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    assert 0 < args.max_cny <= 10 and 0 < args.max_calls <= 5000 and 1 <= args.workers <= 4
    os.umask(0o077)
    run(args)
