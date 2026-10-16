# ASI manual infrastructure repair, attempt1

最新现场核实（2026-10-16 13:27 CST）：infra1在09:32:57完成237/237，237份response/result齐；加保留旧3答卷共240。原始执行status为37 completed/203 failed，尚未做完整失败原因审计或Judge评分，不能将执行状态当科学正确率。原控制PID3334671已退出，GPU724241现TIMEOUT。下文启动/验收为历史事实。

LAUNCHED after root's restored-tunnel generation/reconnection acceptance and explicit green light: PID3334671 on80, separate attempt directory. Initial evidence is exactly8 active futures/8 actual start journals and229 unsubmitted entries, rather than prequeueing237. All240 original physical workspaces and240 workspace symlink targets/inodes remained unchanged.

The immutable original run remains artifacts/eval/base_asi_v2_20261016. A separate attempt directory artifacts/eval/base_asi_v2_20261016_infra1 contains an explicit manual_retry_manifest.json:229 failures before any generation plus8 sent/disconnected requests are selected, with the8 explicitly disclosed as manual whole-trial infrastructure retries rather than safe same-request HTTP retries. The3 original received answers, including failed executions, always remain selected from the original run. All original results, response/program/workspace artifacts and token/cost evidence remain. Selection is the first received answer in chronological attempt order, without comparing quality or scores.

The new repair_asi_infrastructure_v2.py imports the original frozen condition_worker and execution hooks. It does not modify the five original production source files, sampling, context/output budgets, seed, task IDs or per-condition resource limits. Preparation checks original runner/helper SHA, creates237 selected entries and3 frozen original-answer entries, and issues zero model requests.

Admission is bounded to at most8 outstanding futures, submitted incrementally instead of enqueueing the full237 list. The driver checks /health before each admission and while waiting. A failed health check, model/tokenizer transport error, or worker infrastructure failure immediately pauses admission and writes infrastructure_checkpoint.json. It freezes its own worker tree, identifies only its own apex-asi scopes via descendants/cgroup receipts, kills those scopes/processes, closes model TCP sockets, and verifies no owned worker/scope remains. There is no automated whole-trial retry loop. Existing failed results are skipped; previously interrupted started conditions are materialized by the original no-regeneration resume path. Unsubmitted conditions remain untouched and can continue after explicit restart.

A complete response persisted before execution remains frozen even when cancellation prevents the original worker's finally audit/result from being written. first_valid_selection.json records references to preserved original/new responses and results for the complete240-condition reporting scope.

Independent HTTP outage/recovery acceptance passed: out of237 synthetic entries, exactly8 were admitted at the outage and229 were untouched; after simulated restoration only those229 unsubmitted entries ran, without regenerating any of the8 failed attempts. Starting offline admitted0. Maximum outstanding futures was8.

Actual frozen-worker cleanup acceptance also passed: two independent ASI processes used self-authored inputs and a local HTTP stub. One executed a generated program in an8GiB scope and spawned a detached child; the second simulated a disconnect after the first heartbeat existed. The breaker paused admission, killed both workers and the exact owned scope, stopped the heartbeat, and left no process in the PID namespace. No benchmark questions or answers were used.

Evidence: analysis/source_snapshots/asi_repair_v2_acceptance_20261016.json and asi_manual_retry_manifest_20261016.json. The original infrastructure incident inventory is kept separately.

After root confirms tunnel restart/health acceptance, run on80:

```sh
artifacts/envs/asi-py312/bin/python scripts/repair_asi_infrastructure_v2.py --source-run artifacts/eval/base_asi_v2_20261016 --attempt-dir artifacts/eval/base_asi_v2_20261016_infra1 --endpoint http://127.0.0.1:18071 --key-file artifacts/private/base_smoke_api_key --parallel 8 --cpu-offset 0
```

The frozen original5-file implementation and source run metadata are unchanged. No automatic second manual repair is authorized by this program.

Final classification fixtures also passed: complete responses with parse/program failure remain frozen; genuine1200s budget failure and context overflow do not trip an infrastructure retry label; transport/unknown states merely pause for audit. Python fcntl flock prevents a duplicate repair controller.
