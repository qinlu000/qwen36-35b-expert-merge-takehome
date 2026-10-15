"""Thin v2 request/deadline adapter around the pinned, unmodified Terminus2."""
import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import httpx

from harbor.agents.terminus_2.terminus_2 import Terminus2, Terminus2Options
from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.llms.base import BaseLLM, LLMResponse, OutputLengthExceededError
from harbor.models.metric import UsageInfo


PHASE = ContextVar("terminal_v2_phase", default="main")
TEMPLATE = {"enable_thinking": False, "preserve_thinking": False}


class ContextBudgetExceeded(NonZeroAgentExitCodeError):
    pass


class TerminalV2Options(Terminus2Options):
    seed: int = 0
    api_key_path: str


class TerminalV2LLM(BaseLLM):
    def __init__(self, endpoint, model, key_path, seed, logs_dir):
        self.endpoint = endpoint.rstrip("/").removesuffix("/v1")
        self.model = model.removeprefix("openai/")
        self.key_path = Path(key_path)
        self.seed = seed
        self.logs_dir = Path(logs_dir) / "v2_requests"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.deadline = None
        self.counter = 0
        self.client = None

    def get_model_context_limit(self):
        return 65536

    def get_model_output_limit(self):
        return 8192

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("shared 1800s solver deadline")
        return remaining

    @staticmethod
    def save(path, record):
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)

    async def _post(self, path, payload, record, record_path):
        # No SDK/LiteLLM retries. Only a failed connection before HTTP bytes,
        # or an explicit admission rejection, permits the second attempt.
        for attempt in (1, 2):
            item = {"path": path, "attempt": attempt}
            record["http_attempts"].append(item)
            record["status"] = "tokenizing" if path == "/tokenize" else "request_in_flight"
            self.save(record_path, record)
            started = time.monotonic()
            try:
                async with asyncio.timeout(self.remaining()):
                    response = await self.client.post(
                        path, json=payload, timeout=self.remaining()
                    )
                item["status_code"] = response.status_code
                rejected = response.headers.get("x-apex-generation-started") == "false"
                if response.status_code == 429 and rejected and attempt == 1:
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                item["connection_error"] = type(exc).__name__
                if attempt == 2:
                    raise
            finally:
                item["elapsed_seconds"] = round(time.monotonic() - started, 4)
                self.save(record_path, record)

    async def call(self, prompt, message_history=None, **kwargs):
        self.counter += 1
        path = self.logs_dir / f"{self.counter:05d}-{PHASE.get()}.json"
        messages = list(message_history or []) + [{"role": "user", "content": prompt}]
        # Native Terminus is a plaintext JSON agent, with no API tool/image parts.
        if any(not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("unexpected non-text native Terminus message")
        payload = {
            "model": self.model, "messages": messages, "temperature": 1,
            "top_p": 0.95, "top_k": 20, "min_p": 0,
            "presence_penalty": 0, "repetition_penalty": 1,
            "max_tokens": 8192, "seed": self.seed,
            "chat_template_kwargs": TEMPLATE,
        }
        record = {
            "phase": PHASE.get(), "request": payload, "http_attempts": [],
            "request_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "status": "started", "started_monotonic": time.monotonic(),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.save(path, record)
        try:
            count = await self._post("/tokenize", {
                "model": self.model, "messages": messages,
                "chat_template_kwargs": TEMPLATE, "add_generation_prompt": True,
            }, record, path)
            record["prompt_tokens_exact"] = count["count"]
            if count["max_model_len"] != 65536:
                raise ValueError("server max_model_len differs from frozen 65536")
            if count["count"] + 8192 > 65536:
                raise ContextBudgetExceeded("context_budget_exceeded")
            response = await self._post("/v1/chat/completions", payload, record, path)
            record["response"] = response
            choice = response["choices"][0]
            message = choice["message"]
            usage = response["usage"]
            if usage["prompt_tokens"] != count["count"]:
                raise ValueError("server tokenize/chat prompt usage mismatch")
            if usage["completion_tokens"] > 8192:
                raise ValueError("server exceeded 8192 output cap")
            if message.get("reasoning_content") or message.get("reasoning"):
                raise ValueError("unexpected thinking output")
            if not isinstance(message.get("content"), str):
                raise ValueError("native Terminus expected assistant text")
            record["status"] = "completed"
            if choice["finish_reason"] == "length":
                raise OutputLengthExceededError("max_tokens=8192", truncated_response=message["content"])
            return LLMResponse(
                content=message["content"], model_name=response.get("model", self.model),
                usage=UsageInfo(prompt_tokens=usage["prompt_tokens"],
                                completion_tokens=usage["completion_tokens"],
                                cache_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                                cost_usd=0),
                extra={"finish_reason": choice["finish_reason"],
                       "request_sha256": record["request_sha256"]},
            )
        except OutputLengthExceededError:
            record["native_feedback"] = ("output_length" if PHASE.get() == "main"
                                         else "summary_failed/output_length")
            raise
        except BaseException as exc:
            record.update(status="failed", error_type=type(exc).__name__, error=str(exc))
            if isinstance(exc, ContextBudgetExceeded):
                record["failure_kind"] = ("context_budget_exceeded" if PHASE.get() == "main"
                                          else "summary_failed/context_budget_exceeded")
            raise
        finally:
            record["elapsed_seconds"] = round(time.monotonic() - record["started_monotonic"], 4)
            self.save(path, record)


class TerminalBaselineV2(Terminus2):
    options_model = TerminalV2Options

    def _init_llm(self, **kwargs):
        return TerminalV2LLM(
            self.options.api_base, kwargs["model_name"], self.options.api_key_path,
            self.options.seed, self.logs_dir,
        )

    async def _query_llm(self, chat, prompt, original_instruction="", session=None):
        # Remove only the native retry decorator. Preserve its original partial
        # length feedback and history. Our client raises ContextBudgetExceeded,
        # never ContextLengthExceededError, so native reactive unwind is unreachable.
        return await Terminus2._query_llm.__wrapped__(
            self, chat, prompt, original_instruction, session
        )

    async def _run_subagent(self, *args, **kwargs):
        token = PHASE.set(kwargs["filename_suffix"])
        try:
            return await super()._run_subagent(*args, **kwargs)
        finally:
            PHASE.reset(token)

    async def run(self, instruction, environment, context):
        self._llm.deadline = time.monotonic() + 1800
        headers = {"Authorization": "Bearer " + self._llm.key_path.read_text().strip()}
        async with httpx.AsyncClient(base_url=self._llm.endpoint, headers=headers,
                                    trust_env=False) as client:
            self._llm.client = client
            try:
                async with asyncio.timeout_at(self._llm.deadline):
                    await super().run(instruction, environment, context)
            except BaseException as exc:
                # Harbor restores public verifier networking after this method.
                # Stop timed-out/erroring solver children first, including setsid
                # escapees; preserve native successful-task resident services.
                reason = f"{type(exc).__name__}: {exc}"
                receipt = await environment.terminate_solver_processes(reason=reason)
                context.metadata = context.metadata or {}
                context.metadata["v2_end_reason"] = reason
                context.metadata["v2_solver_error_cleanup"] = receipt
                raise
            else:
                context.metadata = context.metadata or {}
                context.metadata["v2_end_reason"] = "native_return"
