#!/usr/bin/env python3
"""Opt-in ASI OpenCode adapter candidate; does not change the frozen protocol.

Use RunConfig(agent=BwrapOpenCodeAdapter(...), sandbox="task") to retain the
upstream task-env manager. Native solve, stdin, usage and JSONL parsing remain
inherited. This candidate does NOT enforce CPU/RAM cgroup limits and must not
be reported as the upstream Docker/os backend or as formally runtime-ready.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ai4sci_bench.adapters.opencode_cli import OpenCodeCLIAdapter


class BwrapOpenCodeAdapter(OpenCodeCLIAdapter):
    def __init__(self, *, model: str, config: dict, relay, opencode_binary: Path,
                 default_env: Path, ngspice_root: Path | None = None,
                 timeout_seconds: int = 10800):
        super().__init__(model=model, api_base="http://127.0.0.1:18080/v1",
                         api_key=relay.agent_token, api_protocol="openai",
                         tool_mode="restricted", timeout_seconds=timeout_seconds)
        if relay.path != "/v1/chat/completions" or relay.model != model:
            raise ValueError("This candidate expects one matching model at /v1")
        self.config = copy.deepcopy(config)
        self.relay = relay
        self.opencode_binary = Path(opencode_binary).resolve(strict=True)
        self.default_env = Path(default_env).resolve(strict=True)
        self.ngspice_root = Path(ngspice_root).resolve(strict=True) if ngspice_root else None
        if self.ngspice_root and not all((self.ngspice_root / path).is_file()
                                       for path in ("bin/ngspice", "usr/bin/ngspice")):
            raise ValueError("ngspice_root must be the installed public ngspice tool directory")
        self.relay_script = Path(__file__).with_name("asi_fixed_relay.py").resolve(strict=True)
        self.last_mounts: list[dict] = []

    def setup(self, config: dict) -> None:
        if config.get("sandbox", "none") not in ("none", "task"):
            raise ValueError("Use none/task: bwrap supplies isolation; no nested upstream backend")
        super().setup(config)

    def _runtime(self, task_env):
        env_dir = Path(task_env.env_dir if task_env else self.default_env).resolve(strict=True)
        settings = dict(line.split(" = ", 1) for line in
                        (env_dir / "pyvenv.cfg").read_text().splitlines() if " = " in line)
        interpreter = (env_dir / "bin/python").resolve(strict=True)
        base_dir = interpreter.parent.parent
        # uv venvs can name a version alias in pyvenv.cfg; expose only that same
        # public Python runtime at the alias, never its containing cache/home.
        alias_dir = Path(settings["home"]).parent
        return env_dir, interpreter, base_dir, alias_dir

    def _build_command(self, task_instance, task_env):
        workspace = task_instance.workspace_dir.resolve(strict=True)
        env_dir, interpreter, base_dir, alias_dir = self._runtime(task_env)
        cmd = ["/usr/bin/bwrap", "--unshare-all", "--new-session", "--die-with-parent",
               "--cap-drop", "ALL", "--hostname", "asi-candidate"]
        mounts = []

        def bind(source, target, readonly=True):
            cmd.extend(["--ro-bind" if readonly else "--bind", str(source), str(target)])
            mounts.append({"source": str(source), "target": str(target), "readonly": readonly})

        # Public OS binaries/libraries, plus narrowly selected runtime data.
        for directory in ("/usr/bin", "/usr/lib", "/usr/lib64", "/usr/include", "/usr/share/zoneinfo",
                          "/usr/share/fonts", "/usr/share/fontconfig", "/etc/fonts",
                          "/etc/alternatives", "/etc/ssl/certs", "/etc/ld.so.cache"):
            if Path(directory).exists():
                bind(directory, directory)
        cmd += ["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
                "--tmpfs", "/tmp", "--tmpfs", "/home", "--dir", "/home/agent",
                "--tmpfs", "/run"]
        bind(env_dir, env_dir)
        bind(base_dir, base_dir)
        if alias_dir != base_dir:
            bind(base_dir, alias_dir)
        if self.ngspice_root:
            # Keep the exact tool path: installed spinit names its code models
            # absolutely. Only this public tool directory is exposed, no parent.
            bind(self.ngspice_root, self.ngspice_root)
        bind(self.opencode_binary, "/opt/apex/bin/opencode")
        bind(self.relay_script, "/opt/apex/asi_fixed_relay.py")
        bind(self.relay.socket_path, "/run/model.sock")
        bind(workspace, "/workspace", readonly=False)
        for name in ("prompt.md", "task_info.json", "data"):
            path = workspace / name
            if path.exists():
                if not path.resolve().is_relative_to(workspace):
                    raise ValueError("Agent input overlays must stay within this workspace")
                bind(path, Path("/workspace") / name)
        cmd += ["--chdir", "/workspace", "--", str(interpreter), "-I", "-S",
                "/opt/apex/asi_fixed_relay.py", "--inside", "/run/model.sock", "18080", "--"]
        self.last_mounts = mounts
        return cmd + self._base_command()

    def _build_run_env(self, task_instance, task_env):
        env_dir, _, _, _ = self._runtime(task_env)
        config = copy.deepcopy(self.config)
        config["provider"]["bench"]["options"] = {"baseURL": self.api_base, "apiKey": self.api_key}
        # Intentionally do not inherit os.environ or task_env.build_subprocess_env:
        # neither judge/HF keys nor host proxy/control sockets enter the namespace.
        tool_path = f":{self.ngspice_root}/bin" if self.ngspice_root else ""
        return {
            "PATH": f"{env_dir}/bin:/opt/apex/bin{tool_path}:/usr/bin:/bin", "VIRTUAL_ENV": str(env_dir),
            "HOME": "/home/agent", "XDG_CONFIG_HOME": "/home/agent/.config",
            "XDG_DATA_HOME": "/home/agent/.local/share", "XDG_STATE_HOME": "/home/agent/.local/state",
            "XDG_CACHE_HOME": "/home/agent/.cache", "TMPDIR": "/tmp", "LANG": "C.UTF-8",
            "OPENCODE_CONFIG_CONTENT": json.dumps(config), "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
            "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "CUDA_VISIBLE_DEVICES": "", "MPLBACKEND": "Agg", "PYTHONNOUSERSITE": "1",
        }
