# SWE249显式审计汇总（2026-10-17）

**后续更新**：独立核审OpenLibrary／Qutebrowser两份原native0后，manifest现为6个批准项；04:05纯读刷新为原生42＋批准6＝48/51有效，0 resolved、主分仍null。Vuls OOM归因未决、NodeBB reward1不足以覆盖timeout、Teleport未决，详见[剩余审计](swe_remaining_scoring_audit_20261017.md)。此外已支持严格校验 `swe_source_cpu_handoff_v1` 的逐CPU历史空scope及AVG准入时序，真实交接已通过；19组人工文件算例通过。以下4项/41条/旧全池proof说明保留为初次历史快照，不能当最新计数或完整现行规则。

主线程独立核审并明确批准4个专家原生0后，新增独立只读collector；不改原队列/collector、原始result/summary、Base、模型或final_results指向。输出为80 `artifacts/eval/swe249_audited_hard51_20261017/summary.json`，现为一次快照，无后台循环。

本次源快照`2026-10-16T19:20:33.491575+00:00`：原37/51有效＋4个明确审计native0＝**41/51有效，0 resolved**；43 terminal、8 active、0 pending。`complete=false`、`primary_score_percent=null`，NodeBB仍null，未完成项不补0。该coverage不代表正式队列已结束，后续刷新需显式再运行一次，不能把本收据当作最终状态。

## 显式来源与规则

[manifest](../configs/eval/swe249_audited_hard51_20261017.json)只列四个exact task、original/accepted result路径与小result SHA、固定patch SHA/字节数、原invalid原因和人工证据理由：

- Ansible c1f2、d33、Flipt524：接受各自原fresh-replay native reward0。
- Teleport7744：只接受独立网络修复后的同patch新result；原网络超时result继续作为previous invalid保留，不拿它填0。

collector检查原summary所指exact result、固定task目录、PatchReplayAgent/source_job、同源patch及apply状态、accepted native reward确为数字0且无Harbor异常、reward.txt为0。结果/patch身份不符立即拒绝，不搜索其他reward、不自动增加条目。每个审计行保留`previous_invalid`、`previous_invalid_result`、`audit_source`与原native reward；未审计行继承原native有效性，invalid的输出reward为null并另存raw native_reward。原始文件完全不写。

输出tasks/status/reward/accepted_result/invalid_reason与[最终swe_tasks adapter](../scripts/summarize_experiment.py)兼容，保留expected/complete/primary等owner字段。只有全部51有效、原51attempt全部terminal、active/pending空、原`model-consumer-finished.json`明确`model_consumer_finished:true`且`scoring_may_still_be_running:false`，再加下述CPU排空证据，才允许complete与正式主指标。原marker名/字段未改，不伪造新资源完成回执；本次实际快照中这些条件尚未齐。

CPU排空证据接受当前CPU0–9无任务scope，或manifest明确指定的唯一历史交接文件`artifacts/eval/avg64_swe_hard51_20261017/admission-opened.json`。后者由[merged SWE admission producer](../scripts/run_swe_merged_benchmark.py:121)在检查排空后写入；collector只接受该精确路径、与源CPU集合完全相同的`cpu_ids`、`swe_expert_all_cpu_and_model_consumers_finished:true`、`base_scopes_on_target_cpus:[]`，且带时区的`at`不得早于原最终model marker的`at`。缺失或不符合即不构成历史证据；原51终态及model/scoring条件始终独立检查。当前scope仍保存为快照，新消费者在已证实的交接之后使用这些CPU，不会阻止专家评分完整性。输出gate相应为`source_cpu_drain_proven`，另存交接原文与校验布尔值。

## 人工文件算例与实际执行

[人工算例](../scripts/check_swe249_audited_examples.py)只构造临时JSON/patch文件，7项在本地与80均通过：未审计invalid原生0不计0、错误result来源拒绝、即使更新digest原生reward非0仍拒绝、外来generation拒绝、缺资源marker不complete、全部有效/terminal/排空可complete、有active则不complete。无模型/容器/任务/测试执行，不是正式评测重跑。

随后按主线程审阅仅修正历史交接gate，新增两组本地人工算例，现共9组通过：非空foreign scope＋有效精确handoff可complete；错误CPU集合或交接早于最终原marker均不可complete（两种拒绝分支分别断言）。不再运行80实际collector，不占CPU10、不读取或改写当前队列。上文41/51实际summary和其SHA保持原样；收据分别保留最初80的7项执行记录与本次本地9项gate修订检查，不能把后者当作新一次正式coverage快照。

80执行前确认CPU10无apex-baseline/ai4sci任务scope；人工算例和一次真实collector依次在`apex-baseline-swe249-audit-metadata` scope、taskset CPU10、1GiB metadata内存限额运行。完成后再次扫CPU10为空，已通知Terminal agent与root释放槽。原CPU0–9评分仍在运行，summary如实记录，不占其执行池。

单次入口（已有精确source/config/manifest在80的前提）：
```bash
python3 scripts/collect_swe249_audited.py --project=/data/caoqinlu/projects/apex-takehome
```

本轮未自动修改final_results；主线程另行显式决定其来源。执行细节、最初7算例及修订后本地9算例、原source/manifest/output SHA及4 accepted来源在[小收据](source_snapshots/swe249_audited_summary_execution_20261017.json)。忽略目录保留原manual_examples.json、collector_execution.json和一次summary。没有新模型/API/GPU/容器/评分调用；Git与共享claud由主线程统一处理。

主线程随后已将[final_results配置](../configs/eval/final_results_20261017.json)的SWE专家来源显式改为该独立summary；每次最终统计前先运行上面的纯读命令刷新。原队列summary与正式答卷不变。

本轮owned文件共5个：
- `scripts/collect_swe249_audited.py`
- `scripts/check_swe249_audited_examples.py`
- `configs/eval/swe249_audited_hard51_20261017.json`
- `analysis/swe249_audited_summary_20261017.md`
- `analysis/source_snapshots/swe249_audited_summary_execution_20261017.json`
