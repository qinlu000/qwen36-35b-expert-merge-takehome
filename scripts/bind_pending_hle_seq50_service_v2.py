#!/usr/bin/env python3
"""Bind the approved HLE50 allocation and publish it only after native health200."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import ProxyHandler, build_opener


def save(path, value):
    temporary = path.with_name(path.name + ".%d.tmp" % os.getpid())
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def job_status(config):
    command = ["ssh", "-F", "/dev/null", "-T", "-S", "none", "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn",
        "-o", "UserKnownHostsFile=" + config["known_hosts"], "-i", config["identity_file"],
        config["user"] + "@" + config["host"], "status 726663"]
    return json.loads(subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    root = parser.parse_args().project.resolve()
    os.umask(0o077)
    out = root / "artifacts/preflight/hle-seq50-726663-binder"
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / "binder.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shutil.copy2(__file__, out / "binder_source.py")
    tunnel_path = root / "configs/eval/direct_hpc_tunnels_20261016.json"
    route_path = root / "configs/eval/hle_seq50_route_20261016.json"
    endpoint = "http://127.0.0.1:28088"
    opener = build_opener(ProxyHandler({}))
    while True:
        state = {"at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
                 "job_id": 726663, "ready": False, "model_or_test_requests": 0}
        try:
            reply = job_status(json.loads(tunnel_path.read_text()))
            state.update(state="waiting_job_running", allocation={key: reply.get(key) for key in
                         ("job_id", "state", "node", "end_time", "returncode")})
            if str(reply.get("job_id")) == "726663" and reply.get("state") == "RUNNING" and reply.get("node"):
                end = datetime.fromisoformat(reply["end_time"])
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone(timedelta(hours=8)))
                worker = {"benchmark": "hle_seq50", "job_id": 726663, "node": reply["node"],
                          "service_port": 18003, "bridge_port": 28088}
                config = json.loads(tunnel_path.read_text())
                existing = next((row for row in config["workers"] if row.get("benchmark") == "hle_seq50"), None)
                if existing is None:
                    config["workers"].append(worker)
                    save(tunnel_path, config)
                elif any(existing.get(key) != value for key, value in worker.items()):
                    existing.update(worker)
                    save(tunnel_path, config)
                state.update(state="waiting_native_health", worker=worker)
                try:
                    with opener.open(endpoint + "/health", timeout=3) as response:
                        state["health_http_status"] = response.status
                except OSError as error:
                    state["health_http_status"] = None
                    state["health_error_type"] = type(error).__name__
                if state["health_http_status"] == 200:
                    route = json.loads(route_path.read_text())
                    route.update(job_id=726663, endpoint=endpoint, allocation_end_time=end.isoformat(),
                                 node=reply["node"], ready=True)
                    save(route_path, route)
                    state.update(state="ready", ready=True, published_route={key: route[key] for key in
                        ("job_id", "endpoint", "allocation_end_time", "node", "ready")})
                    save(out / "receipt.json", state)
                    save(out / "state.json", state)
                    return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            state.update(state="waiting_status_or_config", error_type=type(error).__name__)
        save(out / "state.json", state)
        print(json.dumps(state), flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
