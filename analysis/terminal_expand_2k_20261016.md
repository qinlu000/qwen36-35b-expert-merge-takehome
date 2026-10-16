# Terminal 完整轨迹扩量：2,000 条已就绪

2026-10-16。按用户授权扩大 Terminal 训练池；**已实际导出 2,000 条训练轨迹／42 条验证轨迹，覆盖 1,303 个来源任务，完整序列共 71,660,040 token**。组成是 Horizon 1,107＋NVIDIA Pivot 893。本轮只做 CPU 数据物化和参数解析修复，没有提交 GPU 作业、重放任务或调用付费 API。没有截断长轨迹、放宽 64K／8K 上限、复制样本凑数或改动验证集。

## 已物化并同步的数据

| 项目 | 实际结果 |
| --- | ---: |
| 请求训练轨迹 | 2,000 |
| 已导出训练轨迹 | **2,000** |
| 来源任务／现有家族键 | **1,303／1,303** |
| 训练完整序列 token 总数 | **71,660,040** |
| 完整序列 token 中位数／P95／最大值 | 38,191／62,140／65,507 |
| 教师轨迹 val | **42，原文件字节一致** |
| 独立任务 val | **原 99 题清单未修改** |
| train 与冻结 val 任务／家族交集 | 0 |
| 与 2,000 条的差额 | **0** |

80 最终路径：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/terminal_sft_2k_20261016/`。

HPC 最终路径：`/data/user/qinlucao/projects/apex-takehome/artifacts/data/candidates/terminal_sft_2k_20261016/`。

最终目录包含 `train.messages.jsonl`、`val.messages.jsonl`、`provenance.jsonl`、`summary.json`。顶层字段统一为 `messages`、`tools`；来源、任务、类别、长度和质量限制在 provenance 中保留。中间产物 `terminal_sft_expanded_20261016/` 的 Horizon 1107／42 保留未改。

最终保留 Horizon 1107 条完整前缀，其中原 374 条仍按原顺序保留。Horizon 阶段复用旧池 2,162 条长度记录，只对此前未测的 **90** 条补量，没有重做其全池 tokenization 或文件哈希。完整清理 messages 按 `(role, content)` 精确去重；本轮没有发现需要移除的完全相同序列。同一训练任务可以有不同的教师执行轨迹，2,000 条不等于 2,000 个独立环境。1,303 是两来源任务标识和当前家族键的去重计数，不等于已证明不存在任何潜在同源改写。

## Horizon 全源供给与排除原因

来源为 [TerminalHorizon-3K 固定版本](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K/tree/45f1e98e317d3639437f0eb02f4e8bc5825732f3)：2,852 条原始轨迹，对应 1,535 个任务环境。教师是作者声明的 DeepSeek-V4-Pro-0813，原生 Terminus2 JSON 动作协议。原始文件和环境元信息此前已下载并审计；本轮复用。

以下为**按顺序互斥归因**，合计恰好 2,852 条：

| 归因 | 轨迹数 |
| --- | ---: |
| 无法唯一关联任务环境 | 9 |
| 属于冻结 val 家族 | 187 |
| 原生 Terminus JSON 解析不合格 | 385 |
| 最后回合未声明 task_complete | 19 |
| 与 val 近似的保守 hold | 2 |
| 完整序列超过 65,536 token | 1,133 |
| 完整序列合格但单次 assistant 超过 8,192 token | 10 |
| 最终训练集 | **1,107** |

同时保留重叠指标，不能与上表直接相加：全源原生解析问题 **419** 条，最后回合未完成 **33** 条；在非 val、任务关联和原生质量合格的长度测量池中，完整序列超 64K 共 **1,135** 条，存在单回复超 8K 共 **49** 条。近 val hold 的两条本身也超过 64K，所以解除这项自加 hold 仍不会扩大当前可用数量。

此前 1,383 个 train-family 池带有额外的人为范围限制，**不是完整来源的硬上限**。本轮把此前低分类置信度的 50 个任务和两个仅静态提取、从未运行模型的校准保留任务重新纳入候选；分类不确定只作为元信息保留，不等于轨迹质量不合格。由旧池外新增 **53 条／35 个任务**，因此从旧池内 1,054 条增加到全源 1,107 条。继续保留一个与 val TF-IDF 相似度 0.371 的任务 hold：`establish-a-defensible-multi-run-quantitative-proteomics-result`。

723 个家族沿用既有任务家族划分：原审计 1,535 个任务未形成跨任务合并，近 val 保护沿用原阈值。这能保证现有任务 ID／分组隔离，不能声称已证明所有潜在同源改写均不存在。

## Horizon 类别与长度偏差

| 任务类别 | 训练轨迹 |
| --- | ---: |
| system-administration | 273 |
| software-engineering | 206 |
| data-processing | 134 |
| security | 111 |
| scientific-computing | 109 |
| optimization | 107 |
| personal-assistant | 39 |
| machine-learning | 32 |
| file-operations | 30 |
| model-training | 26 |
| video-processing | 17 |
| data-science | 8 |
| games | 6 |
| data-querying | 5 |
| debugging | 4 |

Horizon 类别标注置信度对应轨迹数：高 623、中 433、低 51。该阶段使用所有合格的完整轨迹，没有为追求数量补重复记录，因此不再是最初每类约 500 条总额的比例抽样，稀缺类别也没有被人为补齐。新增 Pivot 没有逐题类别标注，provenance 明确为 `unclassified`，不能声称最终 2,000 条精确匹配官方 16 类比例。64K 限制使数据偏向较短执行；多轨迹任务还会使轨迹分布与独立任务分布不同。训练上限和评测上下文上限仍为 64K，单回复 8K；没有生成独立后窗或假装保存完整历史。

清理仅去掉 assistant 开头配对的隐藏 `<think>...</think>`；保留完整 user 观察及 visible JSON `analysis`、`plan`、`commands`、`task_complete`。**质量依据仍是作者过程审查＋原生协议解析＋最终完成自报，不是本地 verifier 成功认证。** `success_verified=false` 和环境未本地逐条验证的限制都保留在 provenance，扩量没有将其升级成已验成功标签。

## 补充来源的有界核查

**FACET 本轮没有可直接纳入的完整 rollout 发布。**[作者 README](https://github.com/StoKou/FACET-Terminal)报告论文实验从成功运行筛出 1.2K 完整轨迹，但公开资源只链接任务集和模型。[HF 固定版本](https://huggingface.co/datasets/FACET-Terminal/FACET-Terminal-Tasks-6k/tree/b2d02645932e3989c8332a41e57d0f0855de7002)实际为 7 个 Parquet 和任务 ZIP；实读列是 `task_id`、`instruction`、`task_toml`、`dockerfile`、`tests`、`solution`、环境文件清单等，没有 messages／trajectory 列。数据卡明确发布 6,020 个 Harbor 任务，参考 `solve.sh` 不等于有真实终端观察的教师轨迹。因此没有为补 893 条而重新运行这批任务，也没有把参考解伪造为完整执行轨迹。

**最终补源是 [NVIDIA Nemotron-RL-Agentic-Terminal-Pivot-v1 固定卡](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1/blob/eaef26944643644c8a3dbbf361ce6128142f5976/README.md)**：2026-08-28 更新，CC-BY-4.0／NVIDIA Corporation；作者声明 Terminus2 v2.0.0／Harbor，630 个 ATCB 种子任务、2,716 条通过自动 verifier 的来源轨迹，拆成 31,111 个决策点。三个自动转换 Parquet 已完整下载，合计 1,267,619,223 B，固定转换版本 `eda6fcc6b0c995066db63ebab588ab6e4e5c6257`；记录原始源版本及文件大小，未做额外大文件 hash。

实际 metadata 教师分别是 `zai-org/GLM-5.1`（11,098 个决策点）和 `zai-org/GLM-5.1-FP8`（20,013 点），均 `terminus_2`。原名完整保留，未把 FP8 改成原精度，也未推断 unsuffixed 服务的具体运算精度。[FP8 官方固定卡](https://huggingface.co/zai-org/GLM-5.1-FP8/blob/f396cf805182f4ca10fa675e1a99815b3ca384db/README.md)自身列 TB2.0／Terminus2=63.5，Base 固定卡对应 51.5，根分支据此通过候选教师门槛；仍没有本项目 64K／8K 非思考条件下的直接同预算对照，也没有量化前后零损失消融，不能声称两精度 bitwise 等同。

### 实际完成回合与完整历史

**不能机械要求 `pivot_agent_turn_index == total_source_agent_turns - 1`。**全源只有 329 条发布点满足原 metadata 末回合，但作者明确过滤完成后确认。按每个 UID 的最后发布点检查，有 **2,192 个 UID 的最后动作明确 `task_complete=true`**。对这些点，导出其原始完整 input messages＋原始 expected_answer；验证从初始任务与终端状态开始、消息角色和回合数为 `2*(index+1)`，并逐一与该 UID 其他已发布 expected_action 对照历史一致性。没有裁剪 prompt、补造观察或重复统计不同决策点。

结构例 1：UID `f29960abccd3e479`／`telemetry-pipeline-audit-2`，来源总回合 41，最后发布 index39，动作完成；原 input79 条消息＋该答复构成从初始任务到完成的 80 条消息，原 metadata 尾部另 1 回合未发布。

结构例 2：UID `c5d00a2480708e1a`／`constrained-log-aggregation`，来源总回合 13，最后发布 index11，动作完成；完整 input23 条＋该答复为 24 条消息，另 1 回合未发布。两例都没有完成之后仍已发布的非空执行动作。

全源有 **5 个 UID** 在最后一个完成尝试后仍有非空执行动作；其最后发布点未完成，因此排除，没有把较早的完成尝试当终局。对保留样本，发布者删除的原始尾部内容本身不可见；我们保留 `source_total_agent_turns`、`last_published_completion_pivot_index`、`unreleased_tail_turn_count`，明确语义是**完整到最后发布完成动作**，不是声称拿到了未发布的原始全部确认回合。最终选中 893 条中，未发布尾部间距分布为 0:94、1:797、3:2。

### Pivot 全源筛选与最终补充

| 按 UID 互斥归因 | 数量 |
| --- | ---: |
| 最后发布动作未完成 | 524 |
| 完整历史有原生 JSON 解析问题 | 206 |
| 完整序列超过 64K | 6 |
| 单回复超过 8K | 1 |
| 合格完整到完成动作的轨迹 | **1,979** |
| 合计来源 UID | **2,716** |

合格供给按教师为 unsuffixed GLM-5.1 535、GLM-5.1-FP8 1,444，覆盖 580 个 ATCB 种子任务。按任务轮转优先覆盖不同任务，任务内部优先 unsuffixed 教师，再取同题不同真实轨迹，实际补入 **893 个不同 UID／580 个任务**：unsuffixed 332、FP8 561。全部附有实际来源 UID 和完整 token 长度；没有把 31,111 个决策点当成独立轨迹。

同一 seed task 的指令存在真实变体，所以对每个 UID 的实际题面检查冻结 Horizon val99 和正式 TB89 **公开输入**，不是只查一个代表题面；标准化题面精确匹配、任务名匹配和原 TF-IDF≥0.35 的近似保护均执行，任何变体命中则整 seed task hold。本轮命中 0 个任务。未读取正式 TB 答案或结果，没有新建大文件指纹。Pivot 自动成功依据来自 NVIDIA 发布声明，未在本地复跑 ATCB 环境；环境包未在本轮重建。新增 893 条完整 token 共 **18,018,659**。

LiteCoder 的教师为 MiniMax M2／M2.1，依根分支决定不自动混入本轮优先的新强教师数据。DCAgent 只查看最近仓库列表，未新增下载或纳入来源。除已获准的 Pivot 这一条线索外，没有继续广搜，不改变数据协议或质量门槛。

## Swift 字典参数修复交接

已同步 Mac、80、HPC 的最小修复文件：

- `scripts/run_sft.py`：原 CLI 参数继续经 HfArgumentParser 做类型转换，但 `liger_kernel_config` 单独反序列化为真正的 dict；保存 `training_config.json`，用相同 world-size 的 torchrun 启动原生 Swift Python 入口。增加可配置 checkpoint 间隔，默认仍为 16。
- `scripts/swift_sft_from_config.py`：JSON 读入后调用原生 `parse_args_from_dict(SftArguments, config)` 和 `sft_main(args)`，绕过 Swift CLI 把 dict 再次序列化为 argparse 字符串的问题。
- `scripts/expand_terminal_sft.py`：本次全源完整轨迹导出脚本。
- `scripts/download_terminal_pivot.py`：三片公开 Parquet 的 32MiB 范围续传；只确认实际长度，不重新做大文件 hash。
- `scripts/prepare_terminal_pivot_sft.py`：按 UID 恢复完整到末发布完成动作的历史，保护 val／正式任务，保留实际教师精度标识，任务轮转补 893 条。重复运行复用已记录完整长度。

原生 CPU 解析回执：HPC `artifacts/runs/sft-config-cpu-20261016/receipt.json`。复用 ASI 失败命令构造配置并完成 JSON 往返；确认 Liger 五项布尔字典、max_length=65536、r16、学习率 1e-4、原 GA 值、prediction_loss_only 的类型和数值正确。刻意跳过 SftArguments 的 `__post_init__` 以隔离解析问题，没有初始化 CUDA 或加载 Base；**不代表完整训练运行已验证**。本轮再次读取回执，没有重复执行该解析链。修改脚本的 `py_compile` 通过。

此分支未修改原 374／42、合并数据、SAB 数据、baseline 或 Git 索引，也未释放 held job、重提作业或宣称产生 optimizer step。**最终 2000／42 数据已就绪**，由根分支集成 Mixed 并安排 GPU 训练；训练尚未在本分支启动。
