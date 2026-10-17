# 第一次训练结果汇报

更新时间：2026-10-17（Asia/Shanghai）。本稿只使用第一次 SFT、Base、专家、Mixed 和已冻结 AVG64 的结果；新 LR SWE 候选已取消，不纳入本汇报。

## 1. 实验设置

- Base：Qwen3.6-35B-A3B，revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。
- 训练：ms-swift/PEFT LoRA，BF16，`r=16`、`alpha=32`、dropout 0.05，global batch 8，1 epoch，峰值学习率 `1e-4`，cosine、warmup 0.03，关闭 thinking。
- 四个专家分别使用 SWE、Terminal、HLE、ASI 数据；Mixed 使用四份数据并集训练一次，但不进入主合版。
- 独立 task-level validation 已取消。train/held-out loss 只作训练诊断，不作为 benchmark 分数、checkpoint 优劣或合版选择依据。

## 2. 训练完成情况

| 模型 | 实际 train/held-out | steps | 固定 checkpoint | 最低/最后 val loss | 训练耗时 |
|---|---:|---:|---:|---:|---:|
| SWE 专家 | 1993 / 87 | 249 | 249 | 0.317680 / 0.317680 | 2.024 h |
| Terminal 专家 | 2000 / 42 | 250 | 250 | 0.422917 / 0.422917 | 1.994 h |
| HLE 专家 | 2000 / 100 | 250 | 250 | 2.002192 / 3.497519 | 1.548 h |
| ASI 专家 | 1073 / 20 | 134 | 128 | 0.582683 / 0.582879 | 0.818 h |
| Mixed | 7066 / 249 | 883 | 883 | 1.218496 / 1.672463 | 6.434 h |

HLE 的 checkpoint 250 是第一次训练的固定产物；ASI 的 checkpoint 128 是历史冻结身份，不能把最低 loss 解释成任务级最优。HLE 的 val loss 后期升高，也只能说明监督留出交叉熵变差，不能直接等同于 benchmark 准确率下降。

## 3. Base、专家和合版任务结果

以下是最新可审计的 strict 视图；缺失或 invalid 不填 0。

| 模型 | SWE | HLE | ASI | Terminal |
|---|---:|---:|---:|---:|
| Base | **10/51 = 19.6078%** | **99/2500 = 3.96%** | **1.570988%**，240/240 | **442/445 native**，3 invalid，strict 主分 null |
| SWE 专家 | **0/51 = 0%** | — | — | — |
| Terminal 专家 | — | — | — | **285/445 有效**，7 invalid，153 pending，主分 null |
| HLE 专家 | — | **173/2500 = 6.92%** | — | — |
| ASI 专家 | — | — | **0.378991%**，240/240 | — |
| Mixed | — | **146/2500 = 5.84%** | — | — |
| AVG64 | **4/51 = 7.8431%** | **117/2500 = 4.68%** | **94/240 有效，主分 null** | **263/445 有效**，6 invalid，176 pending，主分 null |

ASI 分数是归一化科学评分，不是任务通过率。ASI 专家相对 Base 为 `-1.191997pp`，配对区间 `[-2.278710, -0.303023]`；逐任务为 3 升、11 降、46 平。主要问题是训练集中 92.36% 为 DS-1000/SciCode 函数或片段，和 ASI 完整工作区程序/产物契约不一致。

HLE 是第一次训练中最明确的正向结果：专家比 Base 高 **2.96pp**；Mixed 比 Base 高 **1.88pp**。但 HLE 使用替代 Judge，Base 与专家存在历史服务/排队差异，不能把差值完全解释为权重因果提升。

SWE 专家比 Base 低 **19.6078pp**；AVG64 比 Base 低 **11.7647pp**。SWE 专家 51 题均已完成审计，0 题通过；AVG64 为 4/51。现有证据显示专家存在空 patch、重复命令和上下文耗尽等行为问题，不能只归因于 LoRA rank 或 loss。

Terminal 两个专家队列均未完成 445 条 native coverage，因此不能发布五 seed 均值、标准差或四项宏平均。用户已决定后续新 Terminal 只跑单次 89 题；已有 445-trial 历史结果保留，不与新口径混报。

## 4. 当前可以汇报的结论

1. 第一次 SFT 已完成，训练产物和曲线齐全；训练 loss 只能作为诊断记录。
2. HLE 专家是唯一在目标 benchmark 上显示明确正向差值的专家。
3. SWE 专家和 ASI 专家都低于 Base；它们不能被描述为成功的专项专家。
4. Terminal 专家与 AVG64 Terminal coverage 不完整，最终 Terminal 分数和四项 macro 仍为 null。
5. AVG64 已冻结，但其完整四 benchmark macro 不能计算，因为 ASI、Terminal 仍缺完整有效结果。不能用 HLE/SWE 的部分结果替代完整 macro。
6. 最终报告必须披露 Terminal 实验使用 30 分钟/4 CPU/8 GiB/64K/8K 且 solver 额外禁网，和题面 3 小时/32 CPU/48 GiB/256K/80K 的差异；ASI/HLE 使用 public/local replacement Judge，非官方 Portal 认证分数。

## 5. 复现实验资产

- 训练矩阵：[configs/train/four_experts_v1.json](../configs/train/four_experts_v1.json)
- 共享 LoRA 配方：[configs/train/lora_r16_shared_v1.json](../configs/train/lora_r16_shared_v1.json)
- 训练曲线：[analysis/training_curves_20261017.md](training_curves_20261017.md)
- 最新 strict/预算双视图：[analysis/source_snapshots/formal_aggregation_20261017_1447.json](source_snapshots/formal_aggregation_20261017_1447.json)
- 原专家结果：[analysis/original_experts_status_20261017_1447.md](original_experts_status_20261017_1447.md)
- ASI 配对对照：[analysis/asi_base_expert_task_comparison_20261017.md](asi_base_expert_task_comparison_20261017.md)
- 20 个 AVG64 失败案例：[analysis/avg64_failure_cases_20261017.md](avg64_failure_cases_20261017.md)
