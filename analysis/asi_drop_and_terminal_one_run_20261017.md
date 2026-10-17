# ASI 专家退化与 Terminal 单次运行协议

更新时间：2026-10-17（Asia/Shanghai）。本记录只整理已存在的训练、生成和评分证据；没有重生 ASI 答案，也没有重跑评分。

## ASI 退化的已知事实

- Base 为 `1.5709884069%`，ASI 专家为 `0.3789913819%`，同一 public/local replacement Judge、同一 240 条条件（60 个任务 × B1–B4），差值 `-1.191997 pp`，配对 95% CI `[-2.278710, -0.303023]`。
- 逐任务方向为 3 个上升、11 个下降、46 个持平。最大下降是 `robotics.multiregime_icp_degeneracy`（-23.55）、`math.multiply_connected_conformal_mapping`（-10.38）、`biology.gene_network_timeseries`（-9.14）、`earth_science.farquhar_ballberry_photosynthesis`（-8.36）、`biology.scrna_seq_analysis`（-7.24）；前五项约占净下降 82.04%。
- 下降任务中，专家通常没有形成 ASI 要求的科学产物或未过 hard gate：最大四个下降任务均为 4/4 failed；`gene_network_timeseries` 只有 B4 保留 29.20 分。该证据支持“输出/产物契约失败”，不能单独证明是哪一种训练因素造成。
- 评分审计已核对两侧 240 条条件、最大分、score divisor 和聚合公式；不是简单的分母、单位或 collector 缩放错误。CMOS B1 的 import 修复复用了旧 cache、只产生 11/100，未改变其余条件。

## 训练侧最可信的解释

1. **数据形态和目标契约错配（一级原因）**：ASI 训练共 1073 条，其中 82 条 ScienceAgentBench 完整程序，976 条 DS-1000 函数/片段补全，15 条 SciCode 函数或主解。也就是 991/1073（92.36%）不是 ASI 工作区文件产物任务，真正带完整工作区/产物契约的 SAB 只占 7.64%。后 991 条多数依赖题面已经给出的 imports、变量或函数接口，不是 ASI 的完整工作区程序。ASI direct_llm 则要求单次输出一个完整 Python 程序，读取工作区数据并写入声明的 `.npy/.csv/.json` 等产物，再由原生执行器和 grader 检查。模型学到“写局部函数/代码片段”后，在完整文件与产物契约上可能发生负迁移。
2. **监督格式覆盖不足**：ASI direct_llm 只提取闭合 Python code fence，执行失败不会把 stderr 返回给模型修复。当前 97 个 failed 快照中，12 个是 8192 输出上限导致未闭合 fence，36 个是未声明 import，1 个是 `pyscf` 子模块路径，48 个是其他程序/API/数据/CLI 错误。这些是观察到的失败类别，不把所有失败都归咎于模型。
3. **更新幅度和遗忘（待验证因素）**：原训练为 1 epoch、`lr=1e-4`、LoRA `r=16/alpha=32/dropout=.05`、global batch 8。train loss 约 `0.966→0.309`，val loss 约 `0.731→0.583`，无 NaN 或持续梯度爆炸；因此不能用曲线说训练发散。高 LR 仍可能让原有通用科学编程能力漂移，低 LR 重训可作为控制变量。
4. **评测拓扑混杂（限制）**：Base 与专家服务的历史排队/拓扑不同，当前结果是 public/local、非 Portal 认证分数。两侧协议和 scorer 已统一，但这项混杂不能用 CI 消除，报告中继续披露。

## 改进顺序

先做低 LR 控制变量，并优先替换/增加与 ASI 完整文件和产物契约一致的样本；不要先根据 loss 选 checkpoint。训练数据仍需保持与正式 ASI 任务隔离，正式 240 条答案不回流训练。若后续只有一次训练预算，先比较 ASI 专家完整结果，再决定是否保留该专家进入合版。

## Terminal 运行次数变更

用户已明确：后续 Terminal 新评测只运行一次（单 seed/单 attempt），不再为新结果启动五次重复。已有 5-seed 原始结果、均值和标准差全部保留，不能被单次结果覆盖或混报。单次结果在报告中标记为 `single-run exploratory`；它不能声称满足题面要求的五次均值/标准差。Terminal 仍保留固定 89 个任务、原 harness、资源限制和缺失/invalid 保留为 null 的规则。当前不因这项变更重跑已存在的 Terminal 答案。
