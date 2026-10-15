#!/usr/bin/env python3
"""Read-only structural audit; never execute corpus commands or show their content."""
import argparse
import collections
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--samples-per-file", type=int, default=10)
    ap.add_argument("--fixtures-only", action="store_true")
    args = ap.parse_args()
    root = args.root
    source = root / "artifacts/benchmarks/harbor/src/harbor/agents/terminus_2"
    parser_path = source / "terminus_json_plain_parser.py"
    spec = importlib.util.spec_from_file_location("apex_terminal_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parser = module.TerminusJSONPlainParser()
    template = (source / "templates/terminus-json-plain.txt").read_text()
    rendered = template.format(instruction="APEX_TASK_MARKER", terminal_state="APEX_SCREEN_MARKER")
    prefix, tail = rendered.split("APEX_TASK_MARKER")
    separator, suffix = tail.split("APEX_SCREEN_MARKER")

    # Synthetic fixtures are independent of all training/benchmark text.
    base = {"analysis": "Synthetic parser check.", "plan": "No execution.",
            "commands": [{"keystrokes": "APEX_SYNTHETIC_TOKEN\n", "duration": 0.1}]}
    fixtures = {
        "valid_action": json.dumps(base),
        "invalid_json": "{invalid}",
        "missing_required_fields": '{"commands": []}',
        "valid_completion": json.dumps(dict(base, commands=[], task_complete=True)),
        "text_wrapped_json": "Synthetic prefix\n" + json.dumps(base) + "\nSynthetic suffix",
        "missing_duration": json.dumps(dict(base, commands=[{"keystrokes": "APEX_SYNTHETIC_TOKEN\n"}])),
        "negative_duration": json.dumps(dict(base, commands=[{"keystrokes": "APEX_SYNTHETIC_TOKEN\n", "duration": -1}])),
        "over_60_duration": json.dumps(dict(base, commands=[{"keystrokes": "", "duration": 120}])),
        "completion_with_bad_command": json.dumps(dict(base, commands=[{}], task_complete=True)),
    }
    fixture_results = {}
    for name, text in fixtures.items():
        result = parser.parse_response(text)
        fixture_results[name] = {"error": bool(result.error), "warning": bool(result.warning),
                                 "n_commands": len(result.commands),
                                 "task_complete": result.is_task_complete,
                                 "durations": [x.duration for x in result.commands]}
    if args.fixtures_only:
        from importlib import metadata
        from harbor.agents.terminus_2.terminus_json_plain_parser import TerminusJSONPlainParser
        native = TerminusJSONPlainParser()
        native_results = {}
        for name, text in fixtures.items():
            result = native.parse_response(text)
            native_results[name] = {"error": bool(result.error), "warning": bool(result.warning),
                                    "n_commands": len(result.commands), "task_complete": result.is_task_complete,
                                    "durations": [x.duration for x in result.commands]}
        print(json.dumps({"harbor_version": metadata.version("harbor"),
                          "installed_environment": sys.executable,
                          "parser_file": sys.modules[TerminusJSONPlainParser.__module__].__file__,
                          "fixture_count": len(fixtures), "matches_source_file_import": native_results == fixture_results,
                          "synthetic_parser_fixtures": native_results}, indent=2))
        return

    import pyarrow.parquet as pq

    task_base = root / "artifacts/tasks/raw/nemotron_tasks/7e53648e183cee7bcb0aed623cc91a121d37fa38"
    task_ids = set()
    task_instructions = {}
    task_ids_by_domain = {}
    for path in sorted(task_base.rglob("*.tar.gz")):
        with tarfile.open(path) as archive:
            ids = {Path(m.name).parent.name for m in archive.getmembers()
                   if m.isfile() and Path(m.name).name == "instruction.md"}
            for member in archive.getmembers():
                if member.isfile() and Path(member.name).name == "instruction.md":
                    task_instructions[Path(member.name).parent.name] = archive.extractfile(member).read().decode()
        task_ids_by_domain[path.name.removesuffix(".tar.gz")] = ids
        task_ids.update(ids)

    corpus = root / "artifacts/data/raw/terminal_corpus/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9"
    totals = collections.Counter()
    roles = collections.Counter()
    metadata_agents = collections.Counter()
    metadata_thinking = collections.Counter()
    prefix_hashes = collections.Counter()
    unique_tasks = set()
    mixed_tasks = set()
    exact_matches = set()
    sample_task_pairs = set()
    prefix_diff = None
    files = []
    for path in sorted(corpus.rglob("*.parquet")):
        pf = pq.ParquetFile(path)
        columns = pf.schema_arrow.names
        nrows = pf.metadata.num_rows
        totals["rows_metadata"] += nrows
        current_tasks = pf.read(columns=["task"]).column("task").to_pylist()
        for task in current_tasks:
            if not isinstance(task, str):
                totals["task_nonstring_rows"] += 1
                continue
            unique_tasks.add(task)
            if "mixed" in path.parts:
                mixed_tasks.add(task)
            if task in task_ids:
                totals["exact_task_match_rows"] += 1
                counts_key = "all_task_id_match_rows_" + path.parts[-3]
                totals[counts_key] += 1
                exact_matches.add(task)
            if Path(task.rstrip("/")).name in task_ids:
                totals["basename_task_match_rows"] += 1
        counts = collections.Counter()
        selected = [c for c in ("conversations", "agent", "model", "model_provider", "enable_thinking", "task") if c in columns]
        batch = next(pf.iter_batches(batch_size=args.samples_per_file, columns=selected))
        for row in batch.to_pylist():
            counts["sample_rows"] += 1
            metadata_agents[str(row.get("agent"))] += 1
            metadata_thinking[str(row.get("enable_thinking"))] += 1
            conv = row["conversations"]
            counts["messages"] += len(conv)
            roles.update(m.get("role") for m in conv)
            r = [m.get("role") for m in conv]
            counts["strict_user_assistant_alternation_rows"] += int(r == ["user" if i % 2 == 0 else "assistant" for i in range(len(r))])
            first = conv[0].get("content", "") if conv else ""
            counts["initial_user_rows"] += int(bool(r) and r[0] == "user")
            counts["exact_target_initial_template_rows"] += int(first.startswith(prefix) and separator in first[len(prefix):] and first.endswith(suffix))
            before_task = first.split("Task Description:", 1)[0]
            prefix_hashes[hashlib.sha256(before_task.encode()).hexdigest()] += 1
            if prefix_diff is None:
                prefix_diff = list(difflib.unified_diff(prefix.split("Task Description:", 1)[0].splitlines(), before_task.splitlines(), fromfile="target-generic-prefix", tofile="corpus-generic-prefix", lineterm=""))
            if row.get("task") in task_instructions:
                counts["sample_task_id_in_pack_rows"] += 1
                instruction = task_instructions[row["task"]]
                if "Task Description:\n" in first and "\n\nCurrent terminal state:\n" in first:
                    actual = first.split("Task Description:\n", 1)[1].rsplit("\n\nCurrent terminal state:\n", 1)[0]
                    counts["sample_pack_instruction_exact_match_rows"] += int(actual.strip() == instruction.strip())
                    counts["sample_pack_instruction_whitespace_match_rows"] += int(re.sub(r"\s+", " ", actual).strip() == re.sub(r"\s+", " ", instruction).strip())
            counts["initial_contains_task_description_rows"] += int("Task Description:" in first)
            counts["initial_contains_current_terminal_state_rows"] += int("Current terminal state:" in first)
            counts["initial_contains_current_terminal_screen_rows"] += int("Current Terminal Screen:" in first)
            complete = []
            for idx, msg in enumerate(conv):
                content = msg.get("content") or ""
                if msg.get("role") == "assistant":
                    counts["assistant_messages"] += 1
                    counts["assistant_think_tag_messages"] += int("<think>" in content or "</think>" in content)
                    action_content = content.rsplit("</think>", 1)[-1].strip()
                    counts["assistant_explicit_think_end_messages"] += int("</think>" in content)
                    try:
                        action_result = parser.parse_response(action_content)
                        counts["after_think_parser_accepted_messages"] += int(not action_result.error)
                        counts["after_think_parser_warning_messages"] += int(bool(action_result.warning))
                        counts["after_think_parser_error_messages"] += int(bool(action_result.error))
                        counts["after_think_task_complete_messages"] += int(action_result.is_task_complete)
                        counts["after_think_commands"] += len(action_result.commands)
                        counts["after_think_empty_keystroke_entries"] += sum(not x.keystrokes for x in action_result.commands)
                        counts["after_think_duration_over_60_entries"] += sum(x.duration > 60 for x in action_result.commands)
                        counts["after_think_negative_duration_entries"] += sum(x.duration < 0 for x in action_result.commands)
                        if action_result.error:
                            category = next((c for c in ("No valid JSON", "Invalid JSON", "Missing required fields", "Field 'commands'", "Command ") if action_result.error.startswith(c)), "other")
                            counts["after_think_error_category_" + category] += 1
                    except Exception as exc:
                        counts["after_think_parser_exception_" + type(exc).__name__] += 1
                        action_result = None
                    try:
                        result = parser.parse_response(content)
                    except Exception as exc:
                        counts["parser_exception_" + type(exc).__name__] += 1
                        complete.append(False)
                        continue
                    counts["parser_accepted_assistant_messages"] += int(not result.error)
                    counts["parser_warning_assistant_messages"] += int(bool(result.warning))
                    counts["parser_error_assistant_messages"] += int(bool(result.error))
                    counts["task_complete_messages"] += int(result.is_task_complete)
                    counts["command_entries"] += len(result.commands)
                    counts["empty_keystroke_entries"] += sum(not x.keystrokes for x in result.commands)
                    counts["duration_over_60_entries"] += sum(x.duration > 60 for x in result.commands)
                    counts["negative_duration_entries"] += sum(x.duration < 0 for x in result.commands)
                    counts["task_complete_with_commands_messages"] += int(result.is_task_complete and bool(result.commands))
                    complete.append(bool(action_result and action_result.is_task_complete and not action_result.error))
                elif msg.get("role") == "user" and idx:
                    counts["observation_user_messages"] += 1
                    counts["new_terminal_output_observations"] += int(content.startswith("New Terminal Output:"))
                    counts["current_terminal_screen_observations"] += int(content.startswith("Current Terminal Screen:"))
                    counts["completion_confirmation_observations"] += int("Are you sure you want to mark the task as complete?" in content)
                    counts["parsing_error_observations"] += int("Previous response had parsing errors:" in content)
                    counts["parsing_warning_observations"] += int("Previous response had warnings:" in content)
                    counts["output_limit_observations"] += int("output limited to" in content and "interior bytes omitted" in content)
                    counts["timeout_observations"] += int("The previous command timed out after" in content)
                    counts["summary_handoff_observations"] += int("picking up work from a previous AI agent" in content or "Continue working on this task" in content)
            counts["rows_with_task_complete"] += int(any(complete))
            counts["rows_ending_two_complete_actions"] += int(len(complete) >= 2 and all(complete[-2:]))
            counts["rows_without_terminal_completion"] += int(not complete or not complete[-1])
            if row.get("task") in task_ids:
                sample_task_pairs.add(row["task"])
        totals.update(counts)
        files.append({"path": str(path.relative_to(corpus)), "rows": nrows,
                      "schema_fields": columns, "sample": dict(counts)})
    example_pairing = {}
    for task_id in ("data_processing_task_0459", "scientific_computing_task_0939"):
        domain = task_id.rsplit("_task_", 1)[0]
        path = corpus / f"synthetic_tasks/skill_based/mixed/{domain}/data_filtered.parquet"
        table = pq.read_table(path, columns=["task", "conversations"])
        instruction = task_instructions[task_id].strip()
        rows = []
        for idx, row in enumerate(table.to_pylist()):
            if row["task"] != task_id:
                continue
            first = row["conversations"][0]["content"]
            actual = first.split("Task Description:\n", 1)[-1].rsplit("\n\nCurrent terminal state:\n", 1)[0].strip()
            rows.append({"row_index": idx,
                         "instruction_exact_match": actual == instruction,
                         "instruction_whitespace_match": re.sub(r"\s+", " ", actual) == re.sub(r"\s+", " ", instruction),
                         "pack_instruction_contained_in_first_user": instruction in first,
                         "pack_instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
                         "trajectory_instruction_sha256": hashlib.sha256(actual.encode()).hexdigest()})
            stats = collections.Counter()
            for msg in row["conversations"]:
                if msg["role"] != "assistant":
                    continue
                content = msg.get("content") or ""
                stats["assistant_messages"] += 1
                stats["think_wrapped_messages"] += int("</think>" in content)
                parsed = parser.parse_response(content.rsplit("</think>", 1)[-1].strip())
                stats["action_parser_accepted_messages"] += int(not parsed.error)
                stats["action_parser_error_messages"] += int(bool(parsed.error))
                stats["task_complete_messages"] += int(parsed.is_task_complete and not parsed.error)
            rows[-1]["structure"] = dict(stats)
        example_pairing[task_id] = {"file": str(path.relative_to(corpus)), "matched_id_rows": rows}
    result = {
        "scope": "Read-only: all Parquet footer/task columns, first N records per file; no command execution, model, task instructions printed, benchmark tasks read, or correctness validation.",
        "samples_per_file": args.samples_per_file,
        "parser_path": str(parser_path),
        "parser_sha256": hashlib.sha256(parser_path.read_bytes()).hexdigest(),
        "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
        "totals": dict(totals), "sample_roles": dict(roles),
        "sample_agent_values": dict(metadata_agents),
        "sample_enable_thinking": dict(metadata_thinking),
        "sample_initial_before_task_prefix_hashes": dict(prefix_hashes),
        "generic_initial_prefix_diff": prefix_diff,
        "task_mapping": {"pack_task_ids": len(task_ids), "pack_domains": {k: len(v) for k,v in task_ids_by_domain.items()},
                         "corpus_unique_task_values": len(unique_tasks), "corpus_mixed_unique_task_values": len(mixed_tasks),
                         "exact_task_id_matches": len(exact_matches), "sample_exact_task_id_matches": len(sample_task_pairs),
                         "game_log_example_exact_id_in_corpus": "data_processing_task_0459" in unique_tasks,
                         "nbody_example_exact_id_in_corpus": "scientific_computing_task_0939" in unique_tasks},
        "two_example_pairing": example_pairing,
        "synthetic_parser_fixtures": fixture_results, "files": files,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
