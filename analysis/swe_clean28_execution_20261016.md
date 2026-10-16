# Independent SWE clean28 execution

The user authorized launch after the generation-environment audit. Production started on runner80 at 2026-10-16 20:04 CST in `artifacts/eval/base_swe_v2_20261016_clean28`. Current controller PID is3045818; consumer watcher PID3043073. The original5/51 table and all original trajectories remain unchanged.

All28 IDs were selected before this run by their legacy generation environment, including the two old successes. The18glibc and10musl tasks use new native-PATH/private-tool runtime classes. The unified queue interleaves the two runtime families and admits three tasks; completion immediately admits another task. Each retains1CPU/4GiB,1800s solver,mini2.4.6,seed0,nonthinking,BF16,65536 context and8192 output per call. Each new patch receives an official fresh-sandbox replay; missing/invalid scores remain unscored.

CPU124,126,127 host the three independent task scopes; CPU0–119 remain with Terminal and120–123 with its saved-state grader. Light read-only aggregation shares125 with the HLE Judge. The two already-loaded TP2/maxseq20 services,726635/28086 and726629/28085, are shared with Terminal. No new GPU job was requested. This serving profile differs from historical generation and must be disclosed; score changes cannot be attributed solely to PATH.

The first controller hit an async queue-claim race. It was fixed before restarting the parent; the original NodeBB child3043076 continued atCPU126 with its original timer and was adopted, without cancellation or duplicate generation. The preserved controller log and launch receipt record the recovery. Subsequent production has3active/25pending, including a musl Vuls task with actual model requests. This was full-cohort production, not a separate fixture or model acceptance run.

Musl children alone prepend the established host Apptainer compatibility shim; glibc children retain the normal host PATH. Both restore each SIF's native task PATH. The managed interpreter andUV stay private. Scoring alone can use the existing official Go download cache and workspace preparation, with unchanged official tests and3000s verifier ceiling.

Logs and recovery state are in `controller.log`, `checkpoint.json`, per-task `audit/*.controller.log`, `requests/*/raw/`, `generation/`, and `replay/`. `clean28_summary.json` reports the new cohort; `corrected51_summary.json` replaces the whole fixed28 cohort and retains all23native historical entries, with no old/new reward selection. The original historical score is kept separately.

Shared GPU release now requires both Terminal's existing model-consumer marker and clean28's model-consumer marker. The resident watcher writes the combined marker only when both are finished; CPU scoring may continue afterwards. No app automation is required and the Mac may disconnect.

Receipts: `analysis/source_snapshots/swe_clean28_launch_20261016.json`, `swe_clean28_progress_20261016_2006.json`; selection is `configs/eval/swe_clean_generation28_plan_20261016.json`.
