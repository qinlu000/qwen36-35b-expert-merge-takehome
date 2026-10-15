#!/usr/bin/env python3
"""DirectLLM execution-isolation candidate; no model-call policy changes.

Native solve/extraction/collector run unchanged on the controller. Only its
single _execute hook is replaced. Use sandbox="task" for native task envs.
64K/8K request guards, sampling and shared1200s deadline are NOT implemented
here; execution uses the native independent timeout. CPU/RAM are not capped.
"""

from pathlib import Path
import subprocess

from ai4sci_bench.adapters.direct_llm import DirectLLMAdapter
from ai4sci_bench.runner.proc_util import run_subprocess_with_graceful_timeout
from asi_bwrap import namespace_prefix, program_env


class BwrapDirectLLMAdapter(DirectLLMAdapter):
    def __init__(self, *, ngspice_root=None, **kwargs):
        super().__init__(**kwargs)
        self.ngspice_root = Path(ngspice_root).resolve(strict=True) if ngspice_root else None
        self.last_mounts = []
        self.execution_count = 0

    def setup(self, config):
        if config.get("sandbox") != "task":
            raise ValueError("This candidate requires native task-env resolution via sandbox=task")
        super().setup(config)

    def _execute(self, task_instance, code_file):
        task_env = self._get_task_environment(task_instance)
        timeout = self._get_effective_timeout(task_instance)
        prefix, self.last_mounts, _ = namespace_prefix(
            task_instance.workspace_dir, task_env.env_dir, self.ngspice_root)
        command = prefix + ["--chdir", "/workspace", "--", str(task_env.python_executable), Path(code_file).name]
        self.execution_count += 1
        try:
            result = run_subprocess_with_graceful_timeout(command, cwd=task_instance.workspace_dir,
                env=program_env(task_env.env_dir, self.ngspice_root), timeout=timeout)
            return result.returncode == 0, result.stdout + "\n" + result.stderr, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            return False, f"Execution timed out ({timeout}s)", error.stdout or "", error.stderr or ""
