# 资源与 API 账本：2026-10-17 快照

## 06:09 CST 新快照（历史记录见下）

[只读账本](source_snapshots/resource_ledger_20261017_0611/snapshot.json)实际采集于06:09:49 CST；目录0611仅为标签。70个本项目顶层作业，已结束 **219.743889 GPUh**，五个普通服务共 **10 H100** 在跑暂计 **16.582778 GPUh**。五个最终trainer46.541425 GPUh已包含，不能重复相加。新增TIES pilot/导出按merge计，728016的HLE推理服务归inference_service；只修用途分类，总GPUh与原采集时点不变。

现存CNY账本9243次调用，usage估计12.629796894、失败/未知reservation0.476025，合计预算核算 **13.105821894 CNY**；USD376次仍 **0.328327020 USD**，不混币种、不当发票。ASI实际账本位置仍在核查，缺失不填0。本次仅读元数据，未额外调用模型/Judge或申请GPU。

## 05:17 CST 新快照（历史记录见下）

[新账本](source_snapshots/resource_ledger_20261017_0518/snapshot.json)于05:17:14 CST保存；目录名0518是采集标签，实际时点以JSON为准。当前67个本项目顶层作业、排除9个其他WorkDir作业。已结束allocation **216.721389 GPUh**，5个普通分区在跑服务合计**10张H100**，暂计另**10.406111 GPUh**。成功trainer子集仍46.541425 GPUh，已在总量内，不重复相加。TIES首次pilot727948在CPU tiny自检阶段失败，29秒/0.008056 GPUh已如实计入，未完成任何真实层合版；后续修正和重提不回写本快照。

账本补齐了Base单项Judge恢复、HLE专家、Mixed、AVG64、AVG16及专家/Mixed八项compact恢复。独立恢复ledger与原budget分别计一次，不把summary合计再次相加。现存CNY账本7332calls：usage计价估计10.911754644，失败/未知reservation0.280551，合计预算核算量**11.192305644 CNY**；USD三份teacher/review账本376calls合计**0.328327020 USD**，不混合币种。部分正式grader仍运行，此数会增长。不是实际支付发票，HPC单位价格仍未知。

BaseASI和两份新ASI Judge逐调用账本仍不存在，维持unknown；不能由缺失断言所有历史请求为零。新增恢复ledger没有重复写prices字段，collector保留其原budget指纹和已记录charged_cny，计价沿用冻结scorer；不将缺失元数据补造为当前价格。逐行来源见同目录[GPU表](source_snapshots/resource_ledger_20261017_0518/slurm_jobs.csv)和[API表](source_snapshots/resource_ledger_20261017_0518/api_ledgers.csv)。

以下02:38内容是历史固定快照，其中当时尚未开始的grader、GPU数量和评分缺口不代表当前状态。

本题已结束 Slurm allocation 合计 **183.098889 GPU 小时**；另有 6 个在跑 allocation、共 **14 GPU**，截至采集时暂计 **14.111111 GPU 小时**。后者还会增长，不能作为最终成本。学校 HPC 单价、API 实际发票金额、人工主动工作时长和 host80 总 CPU 使用时长均为 **unknown / 未计时**。

采集时间：Slurm `2026-10-17T02:38:19.869041+08:00`；host80 API/结果元数据见 [snapshot.json](source_snapshots/resource_ledger_20261017/snapshot.json) 的 `runner_captured_at`。这是固定时点记录，之后的 Terminal 调度调整不回写这份快照。服务等待准入、空闲和 kernel warmup 都已占用 allocation，照常计入 ElapsedRaw。

## 计量与范围

只读运行 `sacct/squeue`、读取现有小型日志和账本；未启动 GPU/API、未改 Base、队列或服务。HPC 通过现有 `/tmp/apex-baseline-hpc-ctl` 控制连接访问 `hpc3`；只请求账号 `qinlucao` 的 accounting，再按项目 WorkDir `/data/user/qinlucao/projects/apex-takehome` 验证归属。57 个保留作业均为 `apex*`；9 个同账号但其他 WorkDir 的任务已排除，绝不汇入本题总量。

时间窗口从 `2026-10-15T00:00:00` 起。日期查询与配置中的明确 job ID 查询取并集，按顶层 JobID 去重。使用 `sacct -X` 排除 `.batch/.extern` 等重复步骤。四个从未启动的取消作业 `726344/726346/726648/726649` 只在显式 ID 查询返回，已补入；57 个作业中共有 11 个从未分配资源的取消作业，GPU 小时为 0。已知配置 ID 无缺失回执。没有把全账号的任务都当作本题，也没有把日期查询漏行当作作业不存在。

逐作业公式为 `实际 AllocTRES 的 gres/gpu 数 × ElapsedRaw / 3600`；若同时有总 GPU 和型号 GPU 字段，仅用总数，避免重复。所有保留行的 GPU 数均可确定。这里是分配资源时长，包含加载、评测、保存、等待和失败开销；没有实测 GPU 利用率、功耗或能源。`TIMEOUT` 单列，不能归为成功。

原始字段、归属依据与逐行计算见 [slurm_jobs.csv](source_snapshots/resource_ledger_20261017/slurm_jobs.csv)。名字分类只用于解释 allocation 用途，不改变实际计量。

| Slurm 状态 | 作业数 | 已结束 GPU 小时 | 在跑暂计 GPU 小时 |
|---|---:|---:|---:|
| COMPLETED | 9 | 48.203889 | — |
| FAILED | 17 | 4.317222 | — |
| CANCELLED | 21 | 66.565000 | — |
| TIMEOUT | 4 | 64.012778 | — |
| RUNNING | 6 | — | 14.111111 |
| 合计 | 57 | **183.098889** | **14.111111** |

| 用途 | 作业数 | 已结束 GPU 小时 | 在跑暂计 GPU 小时 |
|---|---:|---:|---:|
| 训练，包括失败、取消和较早 HLE 成功训练 | 25 | 50.548889 | 0 |
| 推理服务，包括 Base/专家/AVG64 | 18 | 130.570556 | 13.380000 |
| 各类 smoke/环境验收 | 12 | 1.979444 | 0 |
| 原生 249 条 loss-only 对比 | 1 | 0 | 0.731111 |
| CPU 环境准备 `724276` | 1 | 0 | 0 |

在跑服务也包含尚未进行正式 benchmark 的等待时间。下面的时长均截至同一快照，不能继续沿用为后续最终值。

| Job ID | 名称 | GPU 数 | ElapsedRaw 秒 | 暂计 GPU 小时 |
|---|---|---:|---:|---:|
| 727113 | apex-validation-lora | 2 | 16368 | 9.093333 |
| 727640 | apex-terminal250 | 2 | 2203 | 1.223889 |
| 727643 | apex-direct-experts | 2 | 2029 | 1.127222 |
| 727654 | apex-merged-direct | 2 | 1772 | 0.984444 |
| 727660 | apex-avg64-execution | 2 | 1712 | 0.951111 |
| 727689 | apex-sft-loss249-only | 4 | 658 | 0.731111 |

没有单独的合并 GPU 作业。合并导出实际在 host80 CPU `10–13`、4 Torch threads 上用时 **8.437 秒、GPU 0**。来源：[merge_export_20261017.json](source_snapshots/merge_export_20261017.json)，以及 host80 `/data/caoqinlu/projects/apex-takehome/artifacts/merges/four-experts-avg-v1-20261017/{execution.log,merge_report.json}`。未将曾经计划但实际未分配的“临时 1 GPU”计入。

## 五个最终成功 trainer：已包含于上表的子集

原生 `summary.json` 的 `wall_seconds × world_size` 精确合计 **46.541425 GPU 小时**；先前表逐行四舍五入后相加约 46.542。相应五个完整 Slurm allocation 合计 **47.016111 GPU 小时**。二者测量边界不同，都已经包含于 183.098889，不能再累加。差额包含 trainer 子进程之外的 allocation 开销，不应编造成某一种单独活动的耗时。

| Run | GPU | run wall 秒 | run GPU 小时 | 原生 train_runtime 秒 | samples/s | steps/s | rank0 peak_reserved GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| SWE 726335 | 4 | 7286.074 | 8.095638 | 6939.165 | 0.287 | 0.036 | 61.42 |
| Terminal 726665 | 4 | 7178.446 | 7.976051 | 6845.742 | 0.292 | 0.037 | 55.35 |
| HLE 726664 | 2 | 5571.416 | 3.095231 | 5400.291 | 0.370 | 0.046 | 42.38 |
| ASI 726336 | 2 | 2945.786 | 1.636548 | 2803.136 | 0.383 | 0.048 | 43.26 |
| Mixed 726666 | 4 | 23164.161 | 25.737957 | 22623.342 | 0.312 | 0.039 | 55.34 |

吞吐是框架末尾报告的原始值，保留其精度；没有用样本数/平均序列长度推算 token/s。`train_runtime`、run wall 和 Slurm ElapsedRaw 不同，不相互替换。日志里的 `total_flos` 也只保留为框架估计，未当作实测硬件 FLOPS。

显存语义由 [training_curves_20261017.md](training_curves_20261017.md) 的源码核验限定：Swift 仅 rank0 写出当前 CUDA device 的 PyTorch `max_memory_reserved`，是 reset 以来的 reserved 峰值，四舍五入到 2 位。**不是**跨卡最大值、各卡总量、`max_memory_allocated` 或 nvidia-smi 整卡峰值，不能据此宣称全作业显存上限。

完整字段见 [training_runs.csv](source_snapshots/resource_ledger_20261017/training_runs.csv)。HPC 原始根目录为 `/data/user/qinlucao/projects/apex-takehome/`，每个 run 均读取 `<run>/summary.json` 与 `<run>/training/logging.jsonl` 的原生训练结束行：

- `artifacts/runs/swe2k-sft-r16-726335`
- `artifacts/runs/terminal-retry-sft-r16-726665`
- `artifacts/runs/hle-existing2k-sft-r16-726664`
- `artifacts/runs/asi-expanded-sft-r16-726336`
- `artifacts/runs/mixed-existing2k-sft-r16-726666`

## API：现有 usage 账目，不是发票

存在的 8 份逐调用账本共记录 **1765 次调用**，合计 prompt **3,711,205**、completion **225,526**、total **3,936,731** tokens。失败或协议错误但已返回 usage 的请求保留，不按结果对错筛除。这里只汇总三个实际 usage 计数；不把 reasoning/cache 子项重复加到 total，缺失的 usage 字段也不解释为 0。

数据教师三份账本记录的保守 USD 估计合计 **USD 0.32832702**。其他五份 CNY 账本合计 **6.116477394**，其中已返回 usage 对应的记录估计/上界为 **6.087459894**，另有 **0.029017500** 失败 reservation。这些 CNY 数值混合了学校接口的记录单价估计与外部接口的预算上界，只能称为已记录的预算核算量。没有支付发票、余额扣款流水或真实汇率证据，**不能称为已支付人民币总额**；USD 也不再乘 8 后和 CNY 总量相加。

| 账本 | 调用数 | 币种 | usage 估计/上界 | 失败或未结 reservation |
|---|---:|---|---:|---:|
| HLE teacher data | 362 | USD | 0.316967640 | 0 |
| SciCode teacher data | 2 | USD | 0.005575680 | 0 |
| Science quality review | 12 | USD | 0.005783700 | 0 |
| Terminal data classification | 64 | CNY | 4.269956544 | 0 |
| Base formal HLE Judge | 1056 | CNY | 1.570785750 | 0.029017500 |
| 已取消独立 HLE 验证 Judge | 252 | CNY | 0.196908000 | 0 |
| 已取消独立 SAB 验证 Judge | 3 | CNY | 0.019936800 | 0 |
| ASI Judge calibration | 14 | CNY | 0.029872800 | 0 |

逐账本来源、mtime、字节数、usage、状态和定价来源保存在 [api_ledgers.csv](source_snapshots/resource_ledger_20261017/api_ledgers.csv) 与 JSON 中。所有 API 原始相对路径都以 host80 `/data/caoqinlu/projects/apex-takehome/` 为根；完整清单在 [configs/resource_ledger_20261017.json](../configs/resource_ledger_20261017.json)，改路径无需改算法：

- `artifacts/data/candidates/night_hle_20261016/teacher_api_ledger.jsonl`
- `artifacts/data/candidates/night_scicode_20261016/scicode_api_ledger.jsonl`
- `artifacts/data/candidates/night_hle_20261016/science_quality_review.jsonl`
- `artifacts/data/candidates/new_terminal_horizon_20261016/annotations/ledger.jsonl`
- `artifacts/runs/hle_judge_v2_20261016/budget.json`
- `artifacts/eval/validation_direct_20261016/hle_scores/budget.json`
- `artifacts/eval/validation_direct_20261016/sab_scores/judge_calls.jsonl`
- `artifacts/preflight/asi-real-calibration-20261016/judge_calls.jsonl`

计量规则直接遵循原生产者，未重新查询当前价格替换历史单价：

- HLE/SciCode teacher：保留每行 `conservative_cost_usd`，记录价为 USD 1.32/M input miss、3.96/M output。Science review 记录价为 USD 0.3/M input、1.2/M output。只加逐行金额，不加 `cumulative_*`。
- Terminal 分类：保留每行 `cost_upper_cny`；原账本价为 USD 0.3/M miss、0.006/M hit、1.2/M output，再乘预算安全系数 8。8 不是已证实的支付汇率。
- HLE Budget：[score_hle_baseline_v2_rolling.py](../scripts/score_hle_baseline_v2_rolling.py:48) 用账本记载 CNY 0.75/M input、2.25/M output。Base 为 1054 completed 加 2 `failed_full_reservation`。失败行即使有 usage，也按原 `charged_cny` 保留全 reservation，不能再额外加一次 usage 估计。
- ASI transport：[asi_score_transport.py](../scripts/asi_score_transport.py) 按 call ID 配对 `started/completed/failed`，完成后只计一次；`cache_reused` 不新增调用。calibration 的 29 行是 14 次调用加 1 次缓存复用。完成后又有 failed 事件的同 ID 也不会被重复收取 reservation。
- SAB：[run_sab_validation_queue.py](../scripts/run_sab_validation_queue.py:48) 的三个 completed 事件没有金额字段，按同一源码冻结的 `(prompt×0.3 + completion×1.2)/1e6×8` 重算预算上界，不扣缓存折扣。6 行事件只对应 3 次调用。

旧 `night_api_budget_20261016.json` 是预算/汇总快照，含 reservation，与上述逐调用记录重叠，**没有另加**。HLE/SAB `summary.json` 中的 accounted cost 仅核对，也没有重复加。取消独立验证不撤销已经发生的 252+3 次调用。

下列 5 个显式路径在采集时不存在，金额字段保留 null/unknown：Base ASI `artifacts/asi/scoring_v2_formal_params_20261016/judge_calls.jsonl`；四个新正式专家/AVG64 的 `artifacts/eval/{hle250_hle2500_20261017,avg64_hle2500_20261017}/scoring/budget.json` 和 `artifacts/eval/{asi128_asi240_20261017,avg64_asi240_20261017}/scoring/judge_calls.jsonl`。direct owner 确认四个新 grader 尚未开始；Base 本地 native ASI 已完整产出但未走到 paid Judge 的历史说明与“账本缺失”分开记录，缺失文件本身不证明所有历史 API 开销为 0。兼容性探针等未找到规范逐调用账本的部分仍为 unknown，本表不宣称覆盖所有真实付款。

## 完成状态与复跑

已只读保留 Base corrected445/corrected51、Base HLE/ASI，以及专家和 AVG64 正式输出的顶层 scalar 元数据。Base TB 436/445 valid、SWE 仍有无效条目、HLE 2499/2500 valid；相应 `complete=false` 和主分 null 均原样保留。专家/AVG64 仍在执行或等待，部分 scoring summary 尚未生成。本账本不更改答案选择，不把未完成结果当成完整主分，也不重新评分。

标准库脚本只做一次捕获，远端只有只读命令，未来运行会产生新的当前状态；若要保留此时点，应指定新目录：

```bash
python3 scripts/collect_resource_ledger.py \
  --config configs/resource_ledger_20261017.json \
  --output analysis/source_snapshots/resource_ledger_NEW_CAPTURE
```

脚本：[collect_resource_ledger.py](../scripts/collect_resource_ledger.py)。本次人工算例回执：[manual_checks.json](source_snapshots/resource_ledger_20261017/manual_checks.json)。离线核验包括 GPUh 逐行公式、57 个唯一顶层 ID、排除集合无交集、Budget 成功/失败分账、journal 重复事件与缓存复用、3/14 次真实 Judge 调用计数。无额外 GPU/API 测试。

人工主动分析、编程、等待期间是否离席等没有计时记录，标为 **未计时**，不会将两日项目跨度、Slurm wall 或 agent elapsed 冒充 active work。host80 的任务声明 CPU/RAM 限制也不能替代进程级实测；全机 CPU 小时、峰值 RSS、磁盘 I/O、HPC 能耗和人民币单价均未核实，不补造数值。
