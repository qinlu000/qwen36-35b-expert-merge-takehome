# Base seq20 isolated service

2026-10-16 19:02 CST: submitted job **726629**, RUNNING on **ACD1-12**, two GPUs, 16 CPUs, 128G RAM, 36 hours; Slurm end time **2026-10-18 07:02:51 CST**. Endpoint port **18003**; root owns the proposed host80 28085 bridge and release/status authorization configuration.

Independent sources: `scripts/serve_base_worker_seq20.py` and `.slurm`. The inference command changes only `max_num_seqs` from the old HLE service's 4 to **20**; transport port changes to18003. Same fixed Qwen3.6-35B-A3B revision995ad96eacd98c81ed38be0c5b274b04031597b0, BF16, TP2/mp, context65536, batched tokens8192, chunked prefill, GPU memory0.85, eager, GDN/MoE triton, qwen3_coder tool parser and qwen3 reasoning parser. Existing per-question nonthinking/8K-output/300s protocol is unchanged.

The actual launcher receipt confirms its socket bind check passed before model launch. GPU key is read from the existing private file into VLLM_API_KEY only and never logged. Existing service725539, all other services, SFT jobs, SSH keys, proxies and answer-generation workers were not changed. No fixture/model inference request was sent.

**HLE ready:** native startup completed2026-10-16 19:09:22 CST; actual startup max_num_seqs20 and host80 http://127.0.0.1:28085/health200 confirmed. No additional model test was sent. HPC log: `artifacts/preflight/base-worker-seq20-726629.log`; native launch receipt: `artifacts/preflight/base-worker-seq20-726629/launch.json`. Local/80 launch snapshot: `analysis/source_snapshots/base_seq20_hle_726629_launch_20261016.json`.


Second pair explicitly authorized after the first submission: Terminal job **726635**, same seq20 profile and36h, port18002, excludes ACD1-32 where old Terminal A already owns18002. Initial state PENDING(Resources). Before submission, Mixed SFT726346 was explicitly JobHeldUser with afterok:726335(unfulfilled); running GPUs were13, so the extra pair gives15 including the unrelated1GPU evaluator. No third pair is submitted without root confirming an old pair has been released. Submission receipt: `analysis/source_snapshots/base_seq20_terminal_726635_submission_20261016.json`.


Terminal726635 became RUNNING on **ACD1-54:18002**, end time **2026-10-18 07:08:32 CST**. Its warmup is pending; root owns bridge/status-release configuration. HLE readiness was reported immediately for natural handoff; this helper does not alter either generation queue or release old jobs.


Root separately authorized the final Terminal B pair only after old HLE725539 disappeared from squeue. That condition was observed with13 GPUs running, then **726645** was submitted: same36h/seq20 profile, port18001, excludes ACD1-12 where old B owns18001. Initially PENDING(Resources); maximum running total with it15 GPUs. No further new pairs are submitted. Receipt `analysis/source_snapshots/base_seq20_terminal_726645_submission_20261016.json`.


For B726645 only, root authorized reducing pending walltime to improve possible backfill fit. At19:13 CST node16 was fully allocated8/8 GPUs; scheduler predicted19:30:49 start onACD1-16. `scontrol update JobId=726645 TimeLimit=12:00:00` succeeded, without resubmission or changes to other jobs. The resulting predicted end is2026-10-17 07:30:49 CST, still PENDING at that observation; the predicted start did not improve immediately. Prediction is not an actual start or reservation guarantee. HLE/A retain36h; inference profile and per-question budgets are unchanged.
