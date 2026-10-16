"""One CPU pool: start at16 slots, append14 only after host resources are free."""
import asyncio
from pathlib import Path
from terminal_verifier_apt_environment import TerminalVerifierAptEnvironment

ENABLE=Path(__file__).resolve().parent.parent/'ENABLE_SECOND_REPLICA'


class TerminalRollingEnvironment(TerminalVerifierAptEnvironment):
    _expanded_pools=set()

    async def _start_server(self):
        key=(self._baseline_cpu_offset,self._baseline_cpu_slots,self._effective_cpus)
        if key not in self._cpu_pools:
            pool=asyncio.Queue()
            for slot in range(16):pool.put_nowait(slot)
            self._cpu_pools[key]=pool
        if ENABLE.exists() and key not in self._expanded_pools:
            for slot in range(16,30):self._cpu_pools[key].put_nowait(slot)
            self._expanded_pools.add(key)
        await super()._start_server()
