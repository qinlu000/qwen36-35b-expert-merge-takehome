"""Recovery-only observation/circuit breaker; frozen Terminus semantics unchanged."""
import asyncio
from contextvars import ContextVar
import time

import httpx

from terminal_baseline_v2 import TerminalBaselineV2, TerminalV2LLM


ACTIVE_ENTRY = ContextVar("terminal_recovery_entry", default=None)


class CircuitBreaker:
    def __init__(self):
        self.event = asyncio.Event()
        self.reason = None
        self.owner_key = None

    def trip(self, reason):
        if not self.event.is_set():
            self.reason = reason
            self.owner_key = ACTIVE_ENTRY.get()
            self.event.set()


BREAKER = None


class RecoveryLLM(TerminalV2LLM):
    async def call(self, *args, **kwargs):
        try:
            return await super().call(*args, **kwargs)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.TimeoutException) and time.monotonic() >= self.deadline:
                raise TimeoutError("shared1800s solver deadline") from exc
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            if BREAKER and (status is None or status >= 500 or status in (401, 403, 429)):
                BREAKER.trip(f"{type(exc).__name__}: {exc}")
            raise


class RecoveryTerminalBaselineV2(TerminalBaselineV2):
    def _init_llm(self, **kwargs):
        return RecoveryLLM(self.options.api_base, kwargs["model_name"],
                           self.options.api_key_path, self.options.seed, self.logs_dir)


async def run_queue(entries, statuses, execute, healthy, breaker, save, concurrency=8):
    """Bounded admission; no queued trial futures beyond the active solver slots."""
    pending = [entry for entry in entries if statuses[entry["key"]]["state"] == "pending"]
    active = {}
    watch = asyncio.create_task(breaker.event.wait())
    async def watch_health():
        while not breaker.event.is_set():
            await asyncio.sleep(1)
            try:
                await healthy()
            except Exception as exc:
                breaker.trip(f"active_health: {type(exc).__name__}: {exc}")
    health_watch = asyncio.create_task(watch_health())
    peak = 0
    try:
        while pending or active:
            while pending and len(active) < concurrency and not breaker.event.is_set():
                try:
                    await healthy()
                except Exception as exc:
                    breaker.trip(f"pre_admission_health: {type(exc).__name__}: {exc}")
                    break
                if breaker.event.is_set():
                    break
                entry = pending.pop(0)
                statuses[entry["key"]]["state"] = "admitted"
                save()
                active[asyncio.create_task(execute(entry))] = entry
                peak = max(peak, len(active))
            if breaker.event.is_set():
                break
            if not active:
                break
            done, _ = await asyncio.wait([watch, *active], return_when=asyncio.FIRST_COMPLETED)
            if watch in done:
                break
            for task in done:
                active.pop(task)
                await task
        if breaker.event.is_set():
            # The failing owner is already unwinding native cleanup; let its
            # original transport exception survive. Cancel all other trials.
            for task, entry in active.items():
                if entry["key"] != breaker.owner_key and not task.done():
                    task.cancel()
            await asyncio.gather(*active, return_exceptions=True)
            save()
        return {"admitted_peak": peak, "halted": breaker.event.is_set(),
                "reason": breaker.reason, "pending_not_admitted": len(pending)}
    except asyncio.CancelledError:
        breaker.trip("controller_cancelled; preserve all admitted attempts")
        raise
    finally:
        watch.cancel()
        health_watch.cancel()
        await asyncio.gather(watch, health_watch, return_exceptions=True)
        for task in active:
            if not task.done():
                task.cancel()
        await asyncio.gather(*active, return_exceptions=True)
        save()
