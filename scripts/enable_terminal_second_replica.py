#!/usr/bin/env python3
"""Enable the prepared second TB pool only after both permanent CPU-done markers."""
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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def live(pid):
    state = (Path("/proc") / str(pid) / "stat").read_text().rsplit(") ", 1)[1].split()[0]
    return state not in ("Z", "X")


def cpu_clear():
    forbidden = set(range(64, 120))
    listing = subprocess.check_output(["systemctl", "--user", "list-units", "--all", "--type=scope",
        "--no-legend", "--plain", "apex-baseline-*.scope"], text=True, timeout=8)
    members, errors, blockers = [], [], []
    for unit in (line.split()[0] for line in listing.splitlines() if line.strip()):
        group = subprocess.check_output(["systemctl", "--user", "show", unit, "--property=ControlGroup",
            "--value"], text=True, timeout=8).strip()
        if not group:
            continue
        directory = Path("/sys/fs/cgroup") / group.lstrip("/")
        pids = set()
        for procs in directory.rglob("cgroup.procs"):
            try:
                pids.update(int(item) for item in procs.read_text().split())
            except FileNotFoundError:
                pass
        for pid in sorted(pids):
            try:
                if not live(pid):
                    continue
                masks = set()
                for thread in (Path("/proc") / str(pid) / "task").iterdir():
                    tid = int(thread.name)
                    try:
                        if not live(tid):
                            continue
                        mask = tuple(sorted(os.sched_getaffinity(tid)))
                        masks.add(mask)
                        if forbidden.intersection(mask):
                            blockers.append({"unit": unit, "pid": pid, "tid": tid, "affinity": mask})
                    except (FileNotFoundError, ProcessLookupError):
                        pass
                members.append({"unit": unit, "pid": pid, "thread_affinities": sorted(masks)})
            except (FileNotFoundError, ProcessLookupError):
                pass
            except OSError as error:
                errors.append({"unit": unit, "pid": pid, "error_type": type(error).__name__})
    return {"clear": not blockers and not errors, "inspected_processes": len(members),
        "members": members, "blockers": blockers, "errors": errors}


def hpc_status(root):
    config = json.loads((root / "configs/eval/direct_hpc_tunnels_20261016.json").read_text())
    command = ["ssh", "-F", "/dev/null", "-T", "-S", "none", "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn", "-o", "UserKnownHostsFile=" + config["known_hosts"],
        "-i", config["identity_file"], config["user"] + "@" + config["host"], "status 725705"]
    response = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=20)
    status = json.loads(response)
    result = {key: status.get(key) for key in ("job_id", "state", "node", "end_time")}
    result["remaining_seconds"] = None
    if status.get("state") == "RUNNING":
        end = datetime.fromisoformat(status["end_time"])
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone(timedelta(hours=8)))  # Existing Slurm status contract is CST.
        result["remaining_seconds"] = (end - datetime.now(timezone.utc)).total_seconds()
    result["ready"] = status.get("state") == "RUNNING" and (result["remaining_seconds"] or 0) >= 35 * 60
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    run = root / "artifacts/runs/base-terminal-recovery-v2-20261016"
    out = run / "second-replica-enabler"
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / "guard.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shutil.copy2(__file__, out / "guard_source.py")
    flag = run / "runtime8/ENABLE_SECOND_REPLICA"
    markers = [root / "artifacts/runs/swe-base-725705/cpu-consumers-finished.json",
               run / "followon/grader-consumers-finished.json"]
    opener = build_opener(ProxyHandler({}))
    while True:
        state = {"at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "enabled": False, "markers": {}}
        if flag.exists():
            state.update(state="already_enabled", marker=str(flag))
            save(out / "state.json", state)
            return
        try:
            for marker in markers:
                done = marker.is_file() and json.loads(marker.read_text()).get("cpu_consumers_finished") is True
                state["markers"][str(marker)] = done
            state["state"] = "waiting_permanent_markers"
            if all(state["markers"].values()):
                state["cpu"] = cpu_clear()
                state["state"] = "waiting_cpu64_119_release"
                if state["cpu"]["clear"]:
                    state["health"] = {}
                    for port in (28082, 28084):
                        with opener.open("http://127.0.0.1:%d/health" % port, timeout=3) as response:
                            state["health"][str(port)] = response.status
                    state["state"] = "waiting_endpoints"
                    if all(status == 200 for status in state["health"].values()):
                        state["hpc"] = hpc_status(root)
                        state["state"] = "waiting_running_job_with35min"
                        if state["hpc"]["ready"]:
                            # Network/status checks can take seconds; inspect actual members again just before enable.
                            state["cpu"] = cpu_clear()
                            if state["cpu"]["clear"] and all(json.loads(path.read_text()).get(
                                    "cpu_consumers_finished") is True for path in markers):
                                state.update(state="enabled", enabled=True, marker=str(flag),
                                    model_or_test_calls=0, hpc_command_scope="Existing fixed status725705 only")
                                temporary = flag.with_name(".ENABLE_SECOND_REPLICA.%d.tmp" % os.getpid())
                                temporary.write_text(json.dumps(state, indent=2) + "\n")
                                os.link(temporary, flag)  # Atomic, complete content, no overwrite.
                                temporary.unlink()
                                save(out / "receipt.json", state)
                                save(out / "state.json", state)
                                return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            state.update(state="waiting_check_unavailable", error_type=type(error).__name__)
        save(out / "state.json", state)
        print(json.dumps({"at_utc": state["at_utc"], "state": state["state"],
            "permanent_markers_ready": len(state["markers"]) == 2 and all(state["markers"].values())}), flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
