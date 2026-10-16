#!/usr/bin/env python3
"""Recover recorded file payloads and document required-output absence; no commands run."""
import argparse
import json
from pathlib import Path
import re

TRIALS = {
    "extract-moves-from-video": ("extract-moves-from-video__seed0__first", "/app/solution.txt"),
    "crack-7z-hash": ("crack-7z-hash__seed0__manual1", "/app/solution.txt"),
    "dna-assembly": ("dna-assembly__seed0__manual1", "/app/primers.fasta"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    for task, (trial, required) in TRIALS.items():
        original = root / "artifacts/results/base-terminal-v2-recovery-20261016/trials" / trial / "result.json"
        result = json.loads(original.read_text())
        out = root / "artifacts/recovery/terminal-v2" / (task + "__seed0")
        out.mkdir(parents=True, exist_ok=True)
        messages = result["agent_result"]["metadata"]["all_messages"]
        commands = json.loads((out / "assistant_commands.json").read_text())
        assert result["exception_info"]["exception_type"] == "AgentTimeoutError"
        assert all(Path(required).name not in item.get("keystrokes", "") for item in commands)
        latest, unconfirmed = {}, []
        for item in commands:
            text = item.get("keystrokes", "")
            match = re.match(r"cat\s*>\s*(/tmp/\S+)\s*<<\s*'([^']+)'\n", text)
            if not match:
                continue
            target, delimiter = match.groups()
            body, ending = text[match.end():].split("\n" + delimiter + "\n", 1)
            evidence = str(original) + "#/agent_result/metadata/all_messages/" + str(item["message_index"])
            if not any(message["role"] == "user" for message in messages[item["message_index"] + 1:]):
                unconfirmed.append({"target": target, "source_evidence": evidence})
                continue
            latest[target] = (body + "\n", evidence)
        files = []
        for target, (body, evidence) in latest.items():
            source = out / "files" / target.lstrip("/")
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(body.encode())
            files.append({"source": str(source), "target": target, "source_evidence": evidence,
                          "exact_recorded_here_doc_payload": True})
        manifest = {"files": files, "commands": [], "reconstructed_from_transcript": True,
            "byte_identical": False, "recorded_file_payloads_exact": True,
            "full_filesystem_snapshot_recovered": False, "verifier_relevant_state": "Required answer file was never written",
            "required_output": required, "required_output_recovered": False,
            "required_output_name_appears_in_any_recorded_command": False,
            "original_result": str(original), "original_exception": result["exception_info"]["exception_type"],
            "original_solver_end_reason": result["agent_result"]["metadata"].get("v2_end_reason"),
            "evidence": {"all_recorded_commands": str(out / "assistant_commands.json"),
                "terminal_history": str(out / "terminal_history.txt"), "command_count": len(commands),
                "official_task": str(root / "artifacts/results/base-terminal-v2-724242-r2/tasks" / task),
                "unconfirmed_final_here_docs_not_replayed": unconfirmed},
            "reason": "Fresh original SIF plus confirmed literal analysis files. No solution file or primers file was created by any recorded command; do not invent one. Do not re-run searches/analysis/install commands.",
            "new_model_calls": 0, "searches_or_solver_commands_reexecuted": 0}
        (out / "restore.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"task": task, "manifest": str(out / "restore.json"),
            "confirmed_analysis_files": len(files), "required_output": required, "required_output_written": False}))


if __name__ == "__main__":
    main()
