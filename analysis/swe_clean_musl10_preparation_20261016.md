# Clean SWE musl10 source prepared

Production update: the unified clean28 controller started at20:04CST and the first musl task has real model requests. The text below preserves the preparation receipt. See `analysis/swe_clean28_execution_20261016.md` for the current execution.

New implementation is `scripts/swe_clean_musl_runtime.py` with `scripts/swe_clean_musl_bootstrap.sh`, deployed to80. No old runtime was changed and no fixture/model call was started. The user authorized the separate clean28 experiment; the production controller still needs root's CPU/endpoint coordination.

Generation import: `swe_clean_musl_runtime:SweCleanMuslRuntimeEnvironment`. Agent: existing `swe_baseline_native_v2:SweBaselineNativeV2`. Authoritative fresh replay import: `swe_clean_musl_runtime:SweCleanMuslScoreEnvironment`. The10predeterminedIDs are `configs/eval/swe_clean_musl10_task_ids_20261016.json`.

The proven private musl ABI loader/glibc assets and absolute managed Python wrapper remain available for mini and the Harbor server. UV now mounts only at `/opt/apex-swe-tools/uv`; no helper mounts target task `/usr/local/bin`. The original image PATH is read from its SIF and explicitly restored on every task exec. The new bootstrap preserves original setup and handles dash-leading instance tokens with `--instance-token=value`. Root user calls keep the existing musl UID0/no-su behavior.

Replay alone mounts the existing official Go module cache, pre-seeds native cache downloads and prepares declared go.work/go.mod dependencies before unchanged test.sh. HTTP exec carries the original3000s verifier budget. Non-Go repositories skip the Go preparation. Native prompts, mini2.4.6, seed0, nonthinking64K/8K,1800s/1740s and1CPU/4GiB remain unchanged.

Host PATH must prepend the existing `artifacts/preflight/swe_v2/musl_compat/shim` so Apptainer keeps its already-established `--ignore-fakeroot-command` compatibility behavior. Use a short/data TMPDIR for staging and Unix sockets, not the full project path or full root partition. The controller/source must freeze before production; this preparation does not claim a newly tested runtime.

The full clean28 model-consumer marker belongs to root's combined controller and must wait for both18glibc and10musl generation groups. This implementation does not write Terminal completion markers or release GPUs.
