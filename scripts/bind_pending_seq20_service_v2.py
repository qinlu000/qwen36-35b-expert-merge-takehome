#!/usr/bin/env python3
"""Bind the approved Terminal B service after its real Slurm allocation starts."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def save(path, data):
    temporary = path.with_name(path.name + ".%d.tmp" % os.getpid())
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def status(config):
    command = ["ssh", "-F", "/dev/null", "-T", "-S", "none", "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn",
        "-o", "UserKnownHostsFile=" + config["known_hosts"], "-i", config["identity_file"],
        config["user"] + "@" + config["host"], "status 726645"]
    return json.loads(subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    root = parser.parse_args().project.resolve()
    run = root / "artifacts/runs/base-terminal-recovery-v2-20261016"
    out = run / "seq20-pending-binder"
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / "binder.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shutil.copy2(__file__, out / "binder_source.py")
    tunnel_path = root / "configs/eval/direct_hpc_tunnels_20261016.json"
    target_path = run / "model-route-targets.json"
    while True:
        state = {"at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
                 "job_id": 726645, "bound": False, "model_or_test_requests": 0}
        try:
            config = json.loads(tunnel_path.read_text())
            reply = status(config)
            state.update(state="waiting_job_running", allocation={key: reply.get(key) for key in
                         ("job_id", "state", "node", "end_time", "returncode")})
            if str(reply.get("job_id")) == "726645" and reply.get("state") == "RUNNING" and reply.get("node"):
                end = datetime.fromisoformat(reply["end_time"])
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone(timedelta(hours=8)))
                worker = {"benchmark": "terminal_seq20_b", "job_id": 726645,
                          "node": reply["node"], "service_port": 18001, "bridge_port": 28087}
                existing = next((row for row in config["workers"] if row.get("benchmark") == "terminal_seq20_b"), None)
                if existing is None:
                    config["workers"].append(worker)
                else:
                    existing.update(worker)
                save(tunnel_path, config)
                targets = json.loads(target_path.read_text())
                target = {"url": "http://127.0.0.1:28087", "job_id": 726645,
                          "allocation_end_time": end.isoformat(), "max_num_seqs": 20}
                existing = next((row for row in targets["new_targets"] if row.get("job_id") == 726645), None)
                if existing is None:
                    targets["new_targets"].append(target)
                else:
                    existing.update(target)
                save(target_path, targets)
                state.update(state="bound", bound=True, worker=worker, target=target,
                             health_admission="Existing switcher waits health200 before admitting")
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
