# Terminal second replica one-shot guard

Deployed on host80 at 2026-10-16 16:36:36 CST. No model requests, test execution, hashes, producer changes, or HPC whitelist changes.

- Stable source: `scripts/enable_terminal_second_replica.py`.
- Remote process: PID **2517615**, user scope `apex-terminal-second-replica-enabler-20261016.scope`.
- Actual initial resource checks: affinity `[127]`, `memory.max=134217728`, `memory.swap.max=0`.
- Remote output: `artifacts/runs/base-terminal-recovery-v2-20261016/second-replica-enabler/` containing `guard_source.py`, `launch.json`, `state.json`, `guard.log`, `guard.lock`; `receipt.json` is written after enabling.
- Launch receipt: `analysis/source_snapshots/terminal_second_replica_guard_launch_20261016.json`.

The process uses flock and checks every 30 seconds. It waits for **both** permanent markers with `cpu_consumers_finished: true`:

1. `artifacts/runs/swe-base-725705/cpu-consumers-finished.json`
2. `artifacts/runs/base-terminal-recovery-v2-20261016/followon/grader-consumers-finished.json`

After both are present it inspects `/proc` affinity for every live thread in every owned `apex-baseline-*.scope` cgroup. Exited/zombie processes are ignored; CPU 64–119 must be absent from every affinity. It then requires HTTP 200 from loopback `/health` on ports 28082 and 28084, and the existing restricted direct-HPC `status 725705` command must report RUNNING with at least 35 minutes remaining. The existing Slurm status timezone contract is CST. Before activation it rechecks actual scope members and both permanent markers. It does not inspect or record process commands or environment tokens.

When all conditions hold, the guard atomically creates `artifacts/runs/base-terminal-recovery-v2-20261016/runtime8/ENABLE_SECOND_REPLICA` without replacing an existing file, writes its receipt, and exits. The existing runtime8 queue controls endpoint assignment and pool expansion. No queue source is changed.

Initial observation: Terminal grader marker true; SWE permanent marker missing. `state=waiting_permanent_markers`; enable flag absent. The process is detached under the remote user systemd manager and does not depend on the local Mac session.
