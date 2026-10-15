#!/usr/bin/env python3
"""Synthetic native-loop and request-boundary acceptance; never reads task text."""
import argparse
import asyncio
import json
from pathlib import Path
import time
from unittest.mock import patch

import httpx

from harbor.llms.chat import Chat
from harbor.models.agent.context import AgentContext
from harbor.agents.terminus_2.terminus_2 import Terminus2
from terminal_baseline_v2 import ContextBudgetExceeded, TerminalBaselineV2, PHASE


class SyntheticSession:
    async def get_incremental_output(self):
        return "APEX synthetic terminal; no commands executed."

    async def is_session_alive(self):
        return True

    async def capture_pane(self, **kwargs):
        return "APEX_SYNTHETIC_SCREEN"


async def no_skills(environment):
    return None


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    key = args.output / "synthetic-key"
    key.write_text("synthetic-nonsecret-key")
    report = {"scope": "native Terminus loop and helpers with fake terminal/HTTP; independent synthetic text",
              "real_model": False, "real_tmux": False, "checks": {}}
    calls = []
    mode = {"name": "native", "turn": 0}
    complete = json.dumps({"analysis": "Synthetic check", "plan": "Finish", "commands": [], "task_complete": True})

    async def handle(request):
        body = json.loads(request.content)
        calls.append({"path": request.url.path, "body": body, "phase": PHASE.get()})
        if mode["name"] == "deadline":
            await asyncio.sleep(1)
        if request.url.path == "/tokenize":
            overflow = mode["name"] == "main_overflow" or (mode["name"] == "helper_overflow" and PHASE.get() == "answers")
            count = 57345 if overflow else (57344 if mode["name"] == "exact_boundary" else 123)
            return httpx.Response(200, json={"count": count, "max_model_len": 65536})
        mode["turn"] += 1
        if mode["name"] == "read_timeout":
            raise httpx.ReadTimeout("synthetic ambiguous outcome", request=request)
        if mode["name"] == "disconnect":
            raise httpx.RemoteProtocolError("synthetic ambiguous disconnect", request=request)
        if mode["name"] == "connect_retry" and mode["turn"] == 1:
            raise httpx.ConnectError("synthetic connection not established", request=request)
        if mode["name"] == "native" and mode["turn"] == 1:
            content, finish = '{"analysis": "partial', "length"
        else:
            content, finish = complete, "stop"
        return httpx.Response(200, json={"model": "apex-qwen", "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 57344 if mode["name"] == "exact_boundary" else 123, "completion_tokens": 8}})

    transport = httpx.MockTransport(handle)
    agent = TerminalBaselineV2(logs_dir=args.output / "native", model_name="apex-qwen",
                               api_base="http://synthetic.invalid", api_key_path=str(key),
                               parser_name="json", seed=3, proactive_summarization_threshold=32768)
    agent._session = SyntheticSession()
    agent._build_skills_section = no_skills
    # Run the unmodified native loop, with fake I/O rather than a container.
    agent._llm.deadline = time.monotonic() + 30
    original_deadline = agent._llm.deadline
    async with httpx.AsyncClient(base_url="http://synthetic.invalid", transport=transport) as client:
        agent._llm.client = client
        agent._reset_per_run_state()
        agent._context = AgentContext()
        agent._chat = Chat(agent._llm)
        initial = agent._prompt_template.format(instruction="Finish this independent synthetic check.", terminal_state="APEX_SCREEN")
        await agent._run_agent_loop(initial, agent._chat, "Finish this independent synthetic check.")
        assert agent._n_episodes == 2 and mode["turn"] == 3
        assert len(agent._chat.messages) == 6
        wire = [c for c in calls if c["path"] == "/v1/chat/completions"]
        assert len(wire) == 3 and wire[0]["body"]["messages"][0]["content"] == initial
        assert wire[0]["body"] != wire[1]["body"]
        assert all(c["body"]["max_tokens"] == 8192 for c in wire)
        assert agent._llm.deadline == original_deadline
        assert "ERROR!! NONE of the actions you just requested were performed" in wire[1]["body"]["messages"][-1]["content"]
        assert "Are you sure you want to mark the task as complete?" in wire[2]["body"]["messages"][-1]["content"]
        report["checks"]["native_parser_length_feedback_and_two_step_finish"] = True

        calls.clear()
        mode.update(name="helper", turn=0)
        await agent._summarize(agent._chat, "Independent synthetic task.", agent._session)
        phases = [c["phase"] for c in calls if c["path"] == "/v1/chat/completions"]
        assert phases == ["summary", "questions", "answers"]
        assert all(c["body"]["max_tokens"] == 8192 and c["body"]["seed"] == 3 for c in calls if c["path"] == "/v1/chat/completions")
        report["checks"]["native_three_helper_prompts_same_cap_seed"] = True

        calls.clear()
        mode.update(name="helper_overflow", turn=0)
        history = list(agent._chat.messages)
        agent._count_total_tokens = lambda chat: 40000
        result = await agent._check_proactive_summarization(agent._chat, "Independent synthetic task.", agent._session)
        assert result is None and agent._chat.messages == history
        assert [c["phase"] for c in calls if c["path"] == "/v1/chat/completions"] == ["summary", "questions"]
        report["checks"]["answers_helper_overflow_best_effort_without_history_change"] = True

        calls.clear()
        mode.update(name="main_overflow", turn=0)
        try:
            await agent._query_llm(agent._chat, "Independent pending prompt")
            raise AssertionError("main overflow was sent")
        except ContextBudgetExceeded:
            pass
        assert mode["turn"] == 0 and agent._chat.messages == history
        report["checks"]["main_guard_blocks_without_native_unwind_or_retry"] = True

        calls.clear()
        mode.update(name="exact_boundary", turn=0)
        await agent._query_llm(agent._chat, "Exact 57344-token fixture")
        assert mode["turn"] == 1
        report["checks"]["exact_57344_boundary_admitted_with_full_8192_reservation"] = True

        calls.clear()
        mode.update(name="read_timeout", turn=0)
        try:
            await agent._query_llm(agent._chat, "Read timeout fixture")
            raise AssertionError("read timeout swallowed")
        except httpx.ReadTimeout:
            pass
        assert mode["turn"] == 1
        report["checks"]["read_timeout_is_not_retried"] = True

        mode.update(name="disconnect", turn=0)
        try:
            await agent._query_llm(agent._chat, "Disconnect fixture")
            raise AssertionError("disconnect swallowed")
        except httpx.RemoteProtocolError:
            pass
        assert mode["turn"] == 1
        report["checks"]["ambiguous_disconnect_is_not_retried"] = True

        calls.clear()
        mode.update(name="connect_retry", turn=0)
        await agent._query_llm(agent._chat, "Connection retry fixture")
        assert mode["turn"] == 2
        wire = [c["body"] for c in calls if c["path"] == "/v1/chat/completions"]
        assert wire[0] == wire[1]
        report["checks"]["only_connection_failure_gets_two_identical_attempts"] = True

        mode.update(name="deadline", turn=0)
        agent._llm.deadline = time.monotonic() + 0.05
        started = time.monotonic()
        try:
            await agent._query_llm(agent._chat, "Tokenization shares deadline")
            raise AssertionError("tokenizer escaped deadline")
        except TimeoutError:
            pass
        assert time.monotonic() - started < 0.5 and mode["turn"] == 0
        report["checks"]["tokenize_in_shared_deadline"] = True
    class CleanupEnvironment:
        def __init__(self):
            self.reasons = []

        async def terminate_solver_processes(self, reason):
            self.reasons.append(reason)
            return {"status": "passed", "reason": reason}

    async def fake_error(*args, **kwargs):
        raise ContextBudgetExceeded("context_budget_exceeded")

    async def fake_return(*args, **kwargs):
        return

    environment = CleanupEnvironment()
    context = AgentContext()
    with patch.object(Terminus2, "run", fake_error):
        try:
            await agent.run("Synthetic failure cleanup", environment, context)
            raise AssertionError("solver error swallowed")
        except ContextBudgetExceeded:
            pass
    assert environment.reasons == ["ContextBudgetExceeded: context_budget_exceeded"]
    assert context.metadata["v2_solver_error_cleanup"]["status"] == "passed"
    report["checks"]["solver_error_cleanup_has_explicit_reason_before_reraise"] = True
    with patch.object(Terminus2, "run", fake_return):
        await agent.run("Synthetic normal return", environment, context)
    assert len(environment.reasons) == 1 and context.metadata["v2_end_reason"] == "native_return"
    report["checks"]["normal_return_does_not_kill_task_services"] = True
    key.unlink()
    report["status"] = "passed"
    (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
