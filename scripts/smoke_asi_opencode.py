#!/usr/bin/env python3
"""Exercise the pinned CLI against a local fake model, without benchmark input."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai4sci_bench.adapters.opencode_cli import OpenCodeCLIAdapter


root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
receipts = root / "artifacts/preflight/asi"
run = Path(tempfile.mkdtemp(prefix="synthetic-opencode-", dir=receipts))
workspace = run / "workspace"
workspace.mkdir()
requests = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append({"path": self.path, "body": body})
        tool_names = {tool["function"]["name"] for tool in body.get("tools", [])}
        tool_result_seen = any(message.get("role") == "tool" for message in body.get("messages", []))
        call_tool = "bash" in tool_names and not tool_result_seen
        tool_call = {"id": "synthetic_bash_1", "type": "function", "function": {
            "name": "bash",
            "arguments": json.dumps({
                "command": "printf 'synthetic-openai-tool-loop\\n' > synthetic_artifact.txt",
                "description": "Create the self-authored smoke artifact",
            }),
        }}
        text = "Synthetic artifact written." if tool_result_seen else "Synthetic environment smoke"
        usage = {"prompt_tokens": 30, "completion_tokens": 12, "total_tokens": 42}
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            deltas = [{"role": "assistant"}]
            deltas += [{"tool_calls": [{"index": 0, **tool_call}]}] if call_tool else [{"content": text}]
            for delta in deltas:
                chunk = {"id": "synthetic-completion", "object": "chat.completion.chunk",
                         "created": int(time.time()), "model": "synthetic-model",
                         "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            chunk["choices"] = [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if call_tool else "stop"}]
            chunk["usage"] = usage
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
            self.wfile.flush()
        else:
            message = {"role": "assistant", "content": None if call_tool else text}
            if call_tool:
                message["tool_calls"] = [tool_call]
            payload = {"id": "synthetic-completion", "object": "chat.completion", "model": "synthetic-model",
                       "created": int(time.time()), "choices": [{"index": 0, "message": message,
                       "finish_reason": "tool_calls" if call_tool else "stop"}], "usage": usage}
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
adapter = OpenCodeCLIAdapter(
    model="synthetic-model", api_base=f"http://127.0.0.1:{server.server_port}/v1",
    api_key="synthetic-placeholder-only", api_protocol="openai", tool_mode="restricted",
)
config = json.loads((root / "configs/asi/opencode.json").read_text())
config.update({"model": "bench/synthetic-model", "small_model": "bench/synthetic-model"})
native = json.loads(adapter._build_config_content())
config["provider"]["bench"]["options"] = native["provider"]["bench"]["options"]
model = config["provider"]["bench"]["models"].pop("apex-qwen")
model["name"] = "synthetic-model"
config["provider"]["bench"]["models"]["synthetic-model"] = model
for name in ("title", "summary", "compaction"):
    config["agent"][name] = {"model": "bench/synthetic-model", "temperature": 0.7, "top_p": 0.8}
env = {
    "PATH": str(root / "artifacts/tools/opencode-1.17.15/node_modules/.bin") + ":/usr/bin:/bin",
    "HOME": str(run / "home"), "XDG_CONFIG_HOME": str(run / "config"),
    "XDG_DATA_HOME": str(run / "data"), "XDG_STATE_HOME": str(run / "state"),
    "XDG_CACHE_HOME": str(run / "cache"), "TMPDIR": str(run / "tmp"), "LANG": "C.UTF-8",
    "OPENCODE_CONFIG_CONTENT": json.dumps(config), "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
    "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_AUTOUPDATE": "1", "CUDA_VISIBLE_DEVICES": "",
}
for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "TMPDIR"):
    Path(env[key]).mkdir(parents=True, exist_ok=True)
try:
    result = subprocess.run(adapter._base_command(), input="Create synthetic_artifact.txt using the bash tool, then finish. This is a self-authored environment check.",
                            cwd=workspace, env=env, capture_output=True, text=True, timeout=90)
    (run / "stdout.jsonl").write_text(result.stdout)
    (run / "stderr.log").write_text(result.stderr)
    (run / "requests.json").write_text(json.dumps(requests, indent=2) + "\n")
    summary = {"returncode": result.returncode, "request_count": len(requests),
               "artifact_exists": (workspace / "synthetic_artifact.txt").exists(),
               "tool_feedback_seen": any(m.get("role") == "tool" for r in requests for m in r["body"].get("messages", [])),
               "paid_api_calls": 0, "benchmark_tasks_executed": 0, "run_dir": str(run),
               "tools_sent": sorted({t["function"]["name"] for r in requests for t in r["body"].get("tools", [])}),
               "request_parameters": [{k: r["body"].get(k) for k in ("model", "temperature", "top_p", "max_tokens", "max_completion_tokens")} for r in requests]}
    (receipts / "opencode_smoke.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if result.returncode or not summary["artifact_exists"] or not summary["tool_feedback_seen"]:
        raise SystemExit(1)
finally:
    server.shutdown()
