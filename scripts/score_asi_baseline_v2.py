#!/usr/bin/env python3
"""Resume official local ASI scoring on frozen produce-only files; never runs the policy."""
import argparse
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
from unittest.mock import patch
from urllib.parse import urlsplit

from ai4sci_bench.core.judge_api import JudgeAPIOverride
from ai4sci_bench.local_scoring import (_prepare_score_jobs, _prepare_score_runtimes,
    _evaluate_score_job, _worker_failure_result)
from ai4sci_bench.scorers import _judge_common

from asi_score_transport import DeepSeekJudgeTransport, digest, write_json

HASHES_ENABLED = True


class FrozenInputsChanged(RuntimeError):
    pass


def tree_hash(path):
    if not HASHES_ENABLED:
        return None
    path = Path(path)
    if not path.exists():
        return None
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return digest([(str(p.relative_to(path)), hashlib.sha256(p.read_bytes()).hexdigest())
                   for p in sorted(path.rglob("*")) if p.is_file()])


def worker(connection, job, settings, condition):
    os.setsid()
    try:
        transport = DeepSeekJudgeTransport(settings, condition)
        override = JudgeAPIOverride(api_base=settings["endpoint"], api_protocol="openai",
                                    api_key_env="APEX_ASI_SCORING_KEY")
        mapping = {"gpt-5.5": "openai/deepseek-flash", "openai/gpt-5.5": "openai/deepseek-flash"}
        prepared = _prepare_score_runtimes([job], tasks_root=Path(settings["tasks"]))[0]
        runtime_scope = nullcontext()
        from asi_score_submission import mapped_submission_runtime
        if job.task_id == 'electrical_engineering.cmos_opamp_design':
            from asi_score_ngspice import mapped_cmos_runtime
            runtime_scope=mapped_cmos_runtime(settings['ngspice_runtime'],
                Path(settings['output'])/'ngspice_calls'/condition)
        with (patch.dict(_judge_common.SUPPORTED_MODELS, mapping),
              patch.object(JudgeAPIOverride, "resolve_api_key", lambda self, environ=None: transport.key),
              patch("litellm.completion", transport),runtime_scope,
              mapped_submission_runtime(Path(settings['output'])/'submission_sandbox')):
            result = _evaluate_score_job(prepared, override)
        connection.send(result)
    except BaseException as error:
        connection.send(_worker_failure_result(job, error_type=type(error).__name__,
                                              error="Scoring worker failed; inspect restricted local logs"))
    finally:
        connection.close()


def evaluate(job, settings, condition):
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(send, job, settings, condition))
    process.start()
    send.close()
    try:
        if receive.poll(settings["condition_timeout"]):
            try:
                result = receive.recv()
            except EOFError:
                result = _worker_failure_result(job, error_type="WorkerExit", error="Worker exited without result")
        else:
            result = _worker_failure_result(job, error_type="ScorerTimeout", error="Scoring deadline exceeded")
    finally:
        if process.is_alive():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.join(timeout=5)
        receive.close()
    return result


def evaluator_error(value):
    if isinstance(value, dict):
        if (value.get("scorer_internal_error") or value.get("evaluator_unavailable")
                or (value.get("parse_failures", 0) and value.get("valid_judge_count") == 0)
                or ("parsed_responses" in value and value.get("raw_responses") and not value["parsed_responses"])):
            return True
        return any(evaluator_error(child) for child in value.values())
    return isinstance(value, list) and any(evaluator_error(child) for child in value)


def check_declared_references(value, reference):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("ref_file", "ref_image", "extra_ref_files") and child:
                names = [child] if isinstance(child, str) else child
                for name in names:
                    if not (Path(reference) / name).is_file():
                        raise FileNotFoundError("Declared evaluator reference is missing")
            else:
                check_declared_references(child, reference)
    elif isinstance(value, list):
        for child in value:
            check_declared_references(child, reference)


def build_report(results, expected, mode):
    valid = [r for r in results if r["evaluation_status"] == "completed"]
    complete = len(valid) == len(expected)
    score = sum(float(r["final_score"]) for r in valid)
    maximum = sum(float(r["max_score"]) for r in valid)
    return {"schema_version": 2, "repo": "seed31415", "official": False,
        "score_scope": "public_local_replacement_judge", "mode": mode,
        "expected_instance_count": len(expected), "instance_count": len(results),
        "scored_instance_count": len(valid), "complete": complete,
        "prepared_instance_count": sum(r["evaluation_status"] == "prepared" for r in results),
        "scorer_error_count": sum(r["evaluation_status"] == "evaluation_invalid" for r in results),
        "pending_count": len(expected) - len(results) + sum(r["evaluation_status"] in ("pending", "prepared") for r in results),
        "total_score": score, "total_max_score": maximum,
        "mean_percent": 100 * score / maximum if complete and maximum else None,
        "native_valid_subset_mean_percent": 100 * score / maximum if maximum else None,
        "expected_total_max_score": 100 * len(expected),
        "auxiliary_zero_fill_mean_percent": score / len(expected) if expected else None,
        "results": results}


def call_budget_exhausted(settings):
    journal = Path(settings["output"]) / "judge_calls.jsonl"
    used = (sum(json.loads(line).get("event") == "started" for line in journal.read_text().splitlines() if line.strip())
            if journal.exists() else 0)
    return used >= settings["max_generation_calls"]


def run(args):
    global HASHES_ENABLED
    HASHES_ENABLED = not args.skip_hashes
    root = args.project.resolve()
    protocol_path = root / "configs/eval/protocol_v2_unified64k8k.json"
    protocol = json.loads(protocol_path.read_text())
    source = root / "artifacts/benchmarks/asi"
    source_revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    assert source_revision == protocol["benchmarks"]["asi"]["code_revision"]
    manifest_path = args.manifest or root / protocol["benchmarks"]["asi"]["task_manifest"]
    manifest = json.loads(manifest_path.read_text())
    if not args.stub_url:
        if args.synthetic_calibration:
            assert args.manifest and args.tasks and len(manifest["task_ids"]) <= 8
            assert all(name.startswith("synthetic.") for name in manifest["task_ids"])
        else:
            assert len(manifest["task_ids"]) == 60 and manifest["prompt_levels"] == ["b1", "b2", "b3", "b4"]
        if not args.prepare_only and not args.allow_paid_api:
            raise ValueError("Paid Judge calls require explicit --allow-paid-api and a generation-call budget")
        if not args.prepare_only and not args.credentials.is_file():
            raise FileNotFoundError("Provide the existing private Judge credentials file before paid scoring")
    elif urlsplit(args.stub_url).hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Synthetic stub must be loopback")
    if not args.prepare_only and args.max_generation_calls <= 0:
        raise ValueError("Set a positive explicit Judge generation-call budget")
    if not args.prepare_only and not args.stub_url and (args.max_cny is None or args.max_cny <= 0):
        raise ValueError('Paid scoring requires a positive --max-cny hard cap')
    if not args.prepare_only and not args.stub_url and not args.judge_identity:
        raise ValueError('Paid scoring requires --judge-identity from successful scientific calibration')
    if not args.prepare_only and not args.stub_url and not args.synthetic_calibration and not args.ngspice_runtime:
        raise ValueError('Formal CMOS scoring requires the accepted --ngspice-runtime')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    run_lock=(output/'.run.lock').open('a')
    fcntl.flock(run_lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    settings = {"output": str(output), "endpoint": (args.stub_url or "https://api.deepseek.com").rstrip("/"),
        "mode": "stub" if args.stub_url else "paid", "credentials": str(args.credentials),
        "max_generation_calls": args.max_generation_calls, "http_timeout": args.http_timeout,
        "max_cny": args.max_cny, "input_bound_mode": 'utf8_plus_image_ceiling',
        "ngspice_runtime": str(args.ngspice_runtime.resolve()) if args.ngspice_runtime else None,
        "condition_timeout": args.condition_timeout,
        "tasks": str((args.tasks or source / "tasks").resolve())}
    identity = json.loads(args.judge_identity.read_text()) if args.judge_identity else None
    if identity:
        settings['expected_reported_model'] = identity['reported_model']
        identity_path = output/'judge_identity.json'
        if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
            raise RuntimeError('Configured Judge identity differs from previous scoring responses')
        write_json(identity_path, identity)
    metadata = {"judge_requested_model": "deepseek-flash", "thinking": "disabled", "temperature": 0,
        "mode": settings["mode"], "endpoint": settings["endpoint"], "official": False,
        "synthetic_calibration": args.synthetic_calibration,
        "hashes_skipped_at_user_request": args.skip_hashes,
        "empty_result_parameters_source": 'Original solver instance framework_task_info.json; metadata only, no answer changes',
        "calibrated_identity": identity,
        "hard_budget": {'max_generation_calls':args.max_generation_calls,'max_cny':args.max_cny},
        "ngspice_runtime_receipt_sha256": tree_hash(args.ngspice_runtime.parent/'runtime_receipt.json') if args.ngspice_runtime else None,
        "ngspice_mapping_sha256": tree_hash(Path(__file__).with_name('asi_score_ngspice.py')),
        "selection_sha256": tree_hash(args.selection) if args.selection else None,
        "input_cost_bound": '256 framing + UTF-8 text bytes + 1024 per image; native output cap',
        "price_ceiling_usd_per_million": {'input': .3, 'output': 1.2},
        "cny_budget_multiplier": 8,
        "provider_revision_pinned": False, "provider_identity_rule": "freeze first response model/fingerprint; stop on drift",
        "source_revision": source_revision, "protocol_sha256": tree_hash(protocol_path),
        "manifest_sha256": tree_hash(manifest_path), "results": str(args.results.resolve()),
        "instances": str(args.instances.resolve()), "tasks": settings["tasks"],
        "script_sha256": tree_hash(Path(__file__)),
        "transport_sha256": tree_hash(Path(__file__).with_name("asi_score_transport.py")),
        "http_timeout_seconds": settings["http_timeout"],
        "condition_timeout_seconds": settings["condition_timeout"],
        "judge_retry_policy": "Native per-scorer retries/repeats; direct HTTP has zero SDK retries; all calls consume the explicit call budget",
        "all_parse_failed_policy": "Retain native detail but mark evaluator invalid, never a valid scored zero",
        "source_sha256": {str(p.relative_to(source)): tree_hash(p) for p in [
            source / "ai4sci_bench/local_scoring.py", source / "ai4sci_bench/core/scoring.py",
            source / "ai4sci_bench/scorers/_judge_common.py", source / "ai4sci_bench/scorers/llm_judge.py",
            source / "ai4sci_bench/scorers/multimodal.py"]}}
    config_path = output / "scoring_config.json"
    if config_path.exists() and json.loads(config_path.read_text()) != metadata:
        raise RuntimeError("Scoring configuration changed; choose a separately versioned scoring output")
    write_json(config_path, metadata)
    with (output / "invocations.jsonl").open("a") as stream:
        stream.write(json.dumps({"max_generation_calls": args.max_generation_calls,
            "max_cny": args.max_cny,
            "prepare_only": args.prepare_only, "retry_invalid": args.retry_invalid,
            "allow_paid_api": args.allow_paid_api, "mode": settings["mode"], "workers":args.workers}) + "\n")
    results = []
    expected = [(task, level, f"{task}__seed31415__{level}")
                for task in manifest["task_ids"] for level in manifest["prompt_levels"]]
    selection = None
    if args.selection:
        chosen = json.loads(args.selection.read_text())
        selection = {entry['condition']: Path(entry['result']) for entry in chosen['entries']}
        if len(selection) != len(chosen['entries']) or set(selection) != {r[2] for r in expected}:
            raise ValueError('Frozen first-valid selection does not match the complete manifest')
    def score_condition(item):
        task, level, condition = item
        result_path = selection[condition] if selection else args.results.resolve() / task / (condition + ".json")
        record_path = output / "conditions" / (condition + ".json")
        row = {"task_id": task, "prompt_level": level, "condition": condition,
               "evaluation_status": "pending", "final_score": None, "max_score": 100}
        if result_path.exists():
            try:
                raw = json.loads(result_path.read_text())
                if not raw.get('parameters') and not args.synthetic_calibration and not args.stub_url:
                    original_metadata=root/'artifacts/asi/instances_seed31415'/(task+'__seed31415')/'framework_task_info.json'
                    if original_metadata.exists():
                        parameters=json.loads(original_metadata.read_text())['parameters']
                        raw=dict(raw,parameters=parameters)
                        row['parameters_source']=str(original_metadata)
                job = _prepare_score_jobs([(result_path, raw)], results_root=args.results.resolve(),
                    instances_root=args.instances.resolve(), tasks_root=Path(settings["tasks"]))[0]
                check_declared_references(job.evaluation, job.reference_dir)
                hashes = {"source_result": tree_hash(result_path), "outputs": tree_hash(job.output_dir),
                          "reference": tree_hash(job.reference_dir), "data": tree_hash(job.data_dir),
                          "task_contract": tree_hash(Path(job.task_dir) / "task_eval.yaml"),
                          "custom_scorer": tree_hash(Path(job.task_dir) / "custom_scorer.py")}
                if record_path.exists():
                    previous = json.loads(record_path.read_text())
                    if previous["frozen_inputs"] != hashes:
                        raise FrozenInputsChanged("Frozen scoring inputs changed")
                    if previous["evaluation_status"] == "completed" or (previous['evaluation_status'] != 'prepared' and not args.retry_invalid):
                        return previous
                    write_json(record_path.with_suffix(f".attempt{previous.get('attempt', 1)}.json"), previous)
                if args.prepare_only:
                    row.update(evaluation_status="prepared", frozen_inputs=hashes)
                elif call_budget_exhausted(settings):
                    row.update(frozen_inputs=hashes, pending_reason="generation_call_budget_exhausted")
                else:
                    attempt = previous.get("attempt", 1) + 1 if record_path.exists() else 1
                    native = evaluate(job, settings, condition + f".grading{attempt}")
                    row.update(native)
                    row.update(condition=condition, frozen_inputs=hashes,
                               attempt=attempt)
                    if evaluator_error([native["gate_results"], native["score_results"]]):
                        row.update(native_final_score=native["final_score"], final_score=None,
                                   evaluation_status="evaluation_invalid", scorer_internal_error=True)
                    if (tree_hash(result_path) != hashes["source_result"]
                            or tree_hash(job.output_dir) != hashes["outputs"]
                            or tree_hash(job.reference_dir) != hashes["reference"]):
                        raise FrozenInputsChanged("Scorer changed frozen inputs")
                    write_json(record_path, row)
            except FrozenInputsChanged:
                raise
            except Exception as error:
                row.update(evaluation_status="evaluation_invalid", error_class=type(error).__name__)
            if args.prepare_only:
                write_json(record_path, row)
        return row
    order = {condition:index for index,(_task,_level,condition) in enumerate(expected)}
    work_items=[]
    for item in expected:
        cached=output/'conditions'/(item[2]+'.json')
        if args.skip_hashes and cached.exists():
            previous=json.loads(cached.read_text())
            if previous['evaluation_status']=='completed':
                results.append(previous)
                continue
        work_items.append(item)
    initial=build_report(results,expected,settings['mode'])
    initial['synthetic_calibration']=args.synthetic_calibration
    write_json(output/'local_score_seed31415.json',initial)
    pool = ThreadPoolExecutor(max_workers=args.workers)
    try:
        futures = [pool.submit(score_condition, item) for item in work_items]
        for future in as_completed(futures):
            results.append(future.result())
            results.sort(key=lambda row:order[row['condition']])
            report = build_report(results, expected, settings["mode"])
            report["synthetic_calibration"] = args.synthetic_calibration
            write_json(output / "local_score_seed31415.json", report)
            if (output/"judge_identity_drift.json").exists() or (output/'token_bound_exceeded.json').exists():
                raise RuntimeError("Judge identity drift; stopped without mixing providers")
    finally:
        pool.shutdown(wait=True,cancel_futures=True)
    report = build_report(results, expected, settings["mode"])
    report["synthetic_calibration"] = args.synthetic_calibration
    write_json(output / "local_score_seed31415.json", report)
    print(json.dumps({key: report[key] for key in ("mode", "complete", "expected_instance_count",
                     "scored_instance_count", "scorer_error_count", "pending_count", "mean_percent")}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, default=Path.home() / ".config/apex-takehome/credentials.env")
    parser.add_argument("--allow-paid-api", action="store_true")
    parser.add_argument("--max-generation-calls", type=int, default=0)
    parser.add_argument('--max-cny', type=float)
    parser.add_argument('--judge-identity', type=Path)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--ngspice-runtime',type=Path)
    parser.add_argument('--skip-hashes',action='store_true')
    parser.add_argument('--workers',type=int,choices=range(1,5),default=1)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--retry-invalid", action="store_true")
    parser.add_argument("--http-timeout", type=float, default=90)
    parser.add_argument("--condition-timeout", type=float, default=1800)
    parser.add_argument("--stub-url")
    parser.add_argument("--synthetic-calibration", action="store_true")
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--manifest", type=Path)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
