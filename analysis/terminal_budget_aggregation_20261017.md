# Terminal 严格与审计预算双视图

本次只增加可选的平行统计视图，不修改原始 result、Terminal controller、Base collector 或默认严格统计语义。实际执行时间为 **2026-10-17 03:25:00 CST**，下列 coverage 是该次快照，不代表后续运行进度。

## 两个视图的含义

- **strict（默认）**：仅接受有效 native 0/1；缺失、未准入、环境错误、native null 均不能成为完整主分。原有字段含义保持不变。
- **audited_terminal_budget（显式启用）**：在 strict 的基础上，仅对逐结果审计通过、耗尽固定 900 秒 verifier 计算预算的 native null 派生预算 0。每条 observation 保留 `native_status`、`native_reward`、原始 `source`、`audit`、`derived` 和派生原因；这里的 `valid_scored` 是预算已记账数量，另列 `native_valid`、`derived_timeout`、`accounted`，不能解释成 native 判分覆盖率。

冻结 Harbor 源码 `artifacts/runs/base-terminal-724242/runtime2/scripts/harbor/metrics/base.py` 的 `aggregate_reward_dicts` 将传入奖励列表中的**整个 None reward dict**映射为 0；`metrics/mean.py` 求其均值，`job.py` 在 `verifier_result is None` 时加入该 None。它不会替未返回的 trial 补行，也没有区分计算超时与环境错误；嵌套的 `{"reward": null}` 亦不能直接等同于整个 None。排除环境错误是本项目独立审计政策，不是 Harbor 提供的错误分类，也不是新造 native reward。

## 审计资格与完整性

政策文件为 [terminal_budget_policy_20261017.json](../configs/eval/terminal_budget_policy_20261017.json)。Base 的审计来源和 owner 预算汇总显式列于文件中；专家、AVG64 的 `audit_files` 目前为空，后续必须使用各自审计，不继承 Base task 白名单。

每个派生项必须同时满足：模型、task、seed、原始绝对 result 路径精确匹配；位于该模型配置的 result 根目录；原结果已结束且 verifier result 为 null；冻结 verifier timeout 为 900 秒，实际 verifier 阶段不少于 900 秒并与审计时长一致；原生 trial.log 有 900 秒 VerifierTimeoutError；官方测试已收集并进入对应测试文件；奖励文件仍不存在；verifier 前完整候选快照 receipt/archive 存在且审计记录包含候选计算证据；审计无基础设施错误证据，stdout 亦不得含已列出的安装、网络、收集等错误标记。顶层 AgentTimeoutError 既不是自动放行条件，也不是自动拒绝条件。

Base 的 3 项原路径位于 `artifacts/results/base-terminal-independent-repair32-20261016/trials/`，精确审计文件是 `analysis/source_snapshots/terminal_three_compute_timeout_audit_20261017.json`：

| task / seed | native 状态 | 预算派生 |
|---|---|---|
| feal-differential-cryptanalysis / 0 | invalid，reward null | 0 |
| feal-differential-cryptanalysis / 4 | invalid，reward null | 0 |
| model-extraction-relu-logits / 4 | invalid，reward null | 0 |

Base `artifacts/results/base-gap-completion-20261017/terminal_budget_summary.json` 仅作数量、精确路径和分数交叉核对，不作为补行或替换其他 invalid 的依据。完整预算分仍要求固定 445 个唯一键、每 seed 89 项、无未记账项、无 source issue；专家/AVG64 还必须自身队列恰有 445 个 terminal 键、active 为空、pending 为空，且模型身份与 native 计数匹配。部分 coverage 不能发布完整分。

**实际 proof 字段核验**：03:27:09 CST 对同一 Base owner 路径作薄元数据复读，`active_trials`、`pending_not_admitted` 确实存在且均为 0，`expected` / `expected_trials` 均为 445；3 个审计原 result 的 `config.agent.model_name` 原值均为 `apex-qwen`，无 `openai/` 前缀，`verifier_result` 均为 null。owner 是滚动来源，此次复读 mtime 为 03:26:57，与 03:25 汇总 capture 分开记录。03:25 预算 Terminal 已 `complete=true` 且 `source_issues=[]`，其 proof gate 已通过；strict 未完成来自 3 个 native null，预算宏平均未完成来自 SWE 50/51，均不是缺字段或错误 alias 隐藏阻塞。专家/AVG64 则确实尚有未完成 counter，不能发布主分。

SWE adapter 只透传原行已有的 `audit_source`、`audit_reason`、`original_invalid_reason`、`previous_invalid_result`、`source_patch`、`native_reward`、`score_source`、`official_test_evidence`；本脚本不额外裁定 SWE 得分。本次 strict observations 中有 8 行携带已有 SWE 审计字段。

## 统计规则

两个视图共用原 `aggregate` / `bootstrap_scores`，10000 次 percentile paired bootstrap，seed **20261015**。每项先转百分数，宏平均始终为四项各 1/4；缺任何一项完整有效分，宏平均及其 CI 均为 null。SWE 按 51 task、HLE 按 2500 question、ASI 按 60 project 保留各 4 conditions、Terminal 按 89 task 保留各 5 seeds 聚类。同 benchmark 每次抽样在模型间复用同一组 ID，差值按同 ID 配对；四项使用独立 SeedSequence 子流，再对对应 replicate 等权求宏平均。Terminal 同时给出 5 个 seed 均值与 sample SD（ddof=1，单位为百分点）。

## 本次实际结果

| 模型 / 项目 | strict native 有效 | 其他状态 | 审计预算有效 / 派生 | 完整预算分 |
|---|---:|---|---:|---:|
| Base / Terminal | 442/445 | 3 invalid | 445/445；3 派生 | 20.224719% |
| Terminal250 / Terminal | 15/445 | 430 pending | 15/445；0 派生 | null |
| AVG64 / Terminal | 14/445 | 431 pending | 14/445；0 派生 | null |
| Base / SWE | 50/51 | 1 invalid | 不变 | null |
| SWE249 / SWE | 41/51 | 2 invalid，8 pending | 不变 | null |
| Base / HLE | 2500/2500 | 完整 | 不变 | 3.96% |
| Base / ASI | 240/240 | 完整 | 不变 | 1.570988% |

HLE250、ASI128 及 AVG64 对应 HLE/ASI 评分在该快照中分别缺 2500/240 条记录；AVG64 SWE 为 51 pending。所有模型宏平均、模型间配对差值及其 CI 仍为 null。所有读取来源的 `source_issues` 均为空。

Base 预算 Terminal 为 90/445，5 seed 分别是 17.977528%、22.471910%、19.101124%、23.595506%、17.977528%；均值 **20.224719%**，sample SD **2.635065 个百分点**，89 task 聚类 bootstrap 95% CI **[13.033708%, 27.865169%]**。strict 仍为 442 native 有效、352 native wrong、3 invalid，主分和 CI 为 null；预算视图的 355 个零分包含 352 native wrong 与 3 个派生超时零，不能合称 native wrong。

这些分数仍属于已披露的 30 分钟 solver、4 CPU / 8 GiB、64K context / 8K output、nonthinking 资源受限实验；900 秒 verifier 预算也不能消除与原题 3 小时等配置的偏离。HLE replacement Judge、ASI public local 非 Portal 认证的来源限制沿用原 summary，不因本次统计而升级。

## 执行与复现

在 80 原环境、项目根目录执行（机器路径不是便携安装说明）：

```bash
cd /data/caoqinlu/projects/apex-takehome
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  taskset -c 10 artifacts/envs/asi-py312/bin/python scripts/check_experiment_aggregation.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  taskset -c 10 artifacts/envs/asi-py312/bin/python scripts/summarize_experiment.py \
  --project /data/caoqinlu/projects/apex-takehome \
  --config configs/eval/final_results_20261017.json \
  --output artifacts/eval/final_aggregation_20261017 \
  --terminal-budget-policy configs/eval/terminal_budget_policy_20261017.json
```

省略最后一个可选参数只输出 strict。根线程维护的 `final_results_20261017.json` 决定 canonical source；本次未编辑它。每个视图均输出 `summary.json`、`matrix.csv`、`observations.jsonl`、`report.md`；可选视图位于同 output 下的 `audited_terminal_budget/`，strict summary 的 `additional_views` 链接该视图。逐行绝对路径与审计来源保存在 observations/source 中，后续新正式结果可用同一命令重跑。

轻量人工算例使用合成文件，不执行题目：1 个真实形态计算超时仅派生 1 个零；infra / 未准入仍未记账；错路径或错模型不能套用审计；strict 输入 dict、source 与原始文件不变；完整 445 与空 active/pending 缺一不可；89 簇保留 5 seeds；物理行序反转的相同分数模型配对 CI 为 [0,0]；缺另一 benchmark 时 macro 为 null。原有错误/invalid、ASI native 聚合和等权宏平均算例亦通过。

执行收据：

- [CPU 人工算例](source_snapshots/terminal_budget_aggregation_cpu_20261017.json)：通过；80 Python 3.12.13、NumPy 2.5.4，CPU10。
- [实际双视图快照](source_snapshots/terminal_budget_aggregation_execution_20261017.json)：exit 0，含两视图 coverage、完整命令与来源；本次检查和汇总合计约 1.6 秒。

CPU10 已与 direct agent 协调并在执行后释放，无后台 scope/循环，无新增 API、GPU、测试容器或模型生成。未修改原始 native 结果；读取生成 observations 核验，strict 派生项为 0，预算派生项恰为上述 3 项且 `native_reward` 全为 null。
