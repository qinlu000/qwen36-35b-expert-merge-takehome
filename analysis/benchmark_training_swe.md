# SWE Pro V2 HARD-51 对应训练轨迹：按工具接口筛来源

核验日期：2026-10-15（Asia/Shanghai）。范围仅限一手作者数据卡、论文、代码文档与 HF 文件/schema 元数据；没有读任何训练/正式评测逐题 messages、参考补丁、答案或隐藏测试。没有恢复下载、下载新增数据、跑实验或修改其他文件。这里的“现成”只指确实公开轨迹文件，不表示完成本项目的许可/去污染/格式资格检查。

## 建议

找到两个超出此前 Open-SWE 的真实候选：**SI2CA Training Trajectories** 明确写出 bash(command) 与消息字段，可作 Python 修复补充；**Microsoft Orchard-SWE** 也明确单 bash 与 OpenAI tool_calls，但发布文本做过匿名化，优先级需降低。现有 Open-SWE v1.1 mini 分区仍提供更广语言覆盖。当前不需要继续堆十个候选，也不应立刻替换或恢复下载。

“harness 不同”并不自动使轨迹失效；要区分框架名、工具语义与序列化协议。下面只把已能证明的匹配写成事实，不能证明的部分保留未知。

## 当前候选目标接口（并非唯一允许agent）

固定 SWE Pro 代码 `66f92766bba642462d4bbe5479e83f91f9211862` 提供多个locked agent入口，包括LockedClaudeCode、LockedMiniSwe和LockedCodex；题面没有强制唯一mini。当前候选是 Harbor `LockedMiniSwe` 加 `mini_toolcall.yaml`，接 OpenAI-compatible endpoint。配置明确每轮至少一次 `bash` 工具调用，参数含 `command`，命令运行在新 subshell；结束动作必须是独立的 `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`。观察是 returncode/output JSON，超过 10,000 字符则给头尾与省略长度。wrapper 继承 Harbor MiniSweAgent，增加安装、超时与 diff 捕获；没有自己重新实现工具协议，其 mini-swe-agent 版本由传入参数决定，仍需正式冻结。[官方入口](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#running)、[目标配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[wrapper](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py)

## 两个新增候选

| 来源 | 已核：轨迹和工具协议 | 当前可用性与限制 |
| --- | --- | --- |
| [SI2CA-Training-Trajectories](https://huggingface.co/datasets/Self-Improving-Coding-Agents/SI2CA-Training-Trajectories/blob/69931bea4c0d0ab56eba498bf21b3426f09181dc/README.md) | revision `69931bea4c0d0ab56eba498bf21b3426f09181dc`；公开、无门禁，CC BY 4.0。三个配置各 10,780 条，同一批 Python 训练任务；真实 assistant/bash/tool 轨迹，有 repo、instance_id、resolved/reward。卡片明确 tool 名 bash、arguments.command，角色含 tool，并保留 reasoning_content、tool_calls、tool_call_id。 | 文件已发布：standard 1 个 Parquet，full_self_judgement 3 个，discovered_strategy 2 个；另有 tasks 包，但本项目不能把它误当轨迹或默认下载。相较 Open-SWE 卡片，工具名及 command 参数的证据更明确；mini 的精确版本、目标观察模板/结束动作是否一致仍未核实。仅 Python，不能独自覆盖 Go/JS/TS。 |
| [Microsoft Orchard / swe](https://huggingface.co/datasets/microsoft/Orchard/blob/70c05ec1f20f823ae6adc60374922e9271bb74e2/README.md) | revision `70c05ec1f20f823ae6adc60374922e9271bb74e2`；公开无门禁，MIT 且逐 repo 许可仍生效。19 个 Parquet、107,185 条 SWE 轨迹；其中 94,972 来自 mini-swe-agent，其他为 OpenHands。卡片明确单 bash，OpenAI tool_calls/id/arguments 与 tool_call_id，有来源、任务与执行成功 metadata。 | mini 子池须按 metadata.source 过滤，不可把全包视为同 harness。**卡片说明 identifiers/paths 在消息与工具参数中已匿名化**，是否保持引用一致、代码语义及工具行为需先核实；不应直接认定比现有 Open-SWE 更适合。卡片未给 mini 精确版本、command 参数/结束动作/观察格式的完整契约。 |

上表只读取了字段说明与文件索引，没有读取数据行。SI2CA 的 tools/tool_calls 本身以 JSON 字符串保存，导入 ms-swift 需要解析与规范化；不是把字符串直接拼到 assistant content。Orchard 的 metadata/tools/arguments 也存在 JSON 字符串层，需要保留 tool-call 配对关系。

## SI2CA 为什么值得参考，以及不能照搬什么

官方作者代码仓库是 [Self-Improving-Coding-Agents/SI2CA](https://github.com/Self-Improving-Coding-Agents/SI2CA)。其训练池与正式评测入口在文档中分开：HF training release 来自 6,146 个 SWE-rebench-V2 训练任务和 4,634 个 SWE-smith 合成训练任务，不是把仓库内 Pro/Verified 正式解题轨迹作为训练包。代码仓库同时包含正式 benchmark 与 privileged assets，因此不能下载整个仓库后把 data/ 下的所有内容混入训练。[作者数据卡](https://huggingface.co/datasets/Self-Improving-Coding-Agents/SI2CA-Training-Trajectories/blob/69931bea4c0d0ab56eba498bf21b3426f09181dc/README.md)、[作者训练说明](https://github.com/Self-Improving-Coding-Agents/SI2CA#-trajectory-curation-and-sft)

三个配置是同题不同生成策略，不能相加宣称 32,340 个独立任务：standard 无分支 judge；另两种有 judge-only 的训练任务 gold patch 辅助选择。policy 上下文不含 judge 输入输出，但训练记录包含 self_judgement_log。若使用，先选一个配置，保留 provenance；不把 judge 日志、训练 gold 或奖励 metadata 直接拼进 policy 监督，也不将不同配置跨 train/dev。普通 standard 配置更便于解释纯 teacher 轨迹；self-judgement 配置可作为后续选择，必须披露 privileged curation。原作者训练是长上下文全参路线，不能据其结果承诺本项目短窗口四卡 LoRA 同样增益。

## Orchard 的复用位置

作者仓库是 [microsoft/Orchard](https://github.com/microsoft/Orchard)，论文为 [Orchard: An Open-Source Agentic Modeling Framework](https://arxiv.org/abs/2605.15040)。可参考跨 harness 数据组织、从失败轨迹提取有效进展的 credit-assignment 思路。但这不要求本项目切换训练框架或搭 Kubernetes。

当前 SWE 卡片提供轨迹级 resolved/unresolved；不能由此假设公开行含现成可训练的逐步价值标签，更不能把所有失败终局都监督成正确答复。卡片还存在“过滤超过64K”与统计最大约101K的口径差异；需要问清统计 tokenizer/处理阶段，不能据声明断言所有样本都小于64K。匿名化限制解决前，将其列为备选而非默认主源。

## 现有 Open-SWE 与三个来源的组合建议

已有 [Open-SWE-Traces 固定卡片](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md) 能证明 v1.1/minisweagent/Qwen3.6-27B 及通用 messages/tools 字段；不能仅据框架名证明与本题 bash(command)、观察截断和提交动作相同。

建议顺序是：

1. 以 Open-SWE v1.1 mini 作为多语言候选；SI2CA standard 作为工具协议文档更明确的 Python 补充，不直接按来源大小决定训练比例。
2. Orchard 暂为备选，首先解释匿名化的语义影响。只有存在可追溯、无损、少量规则即可完成的格式对齐，才进入最终训练池。
3. 保留一名修复专家即可，不再把 Python/Go 各拆专家；覆盖定位、编辑、验证与错误恢复。其他专家依旧按终端工作流、科学推理/计算分工。
4. 不把新候选自动加入下载器；本文件是调研结果，下载与最终选择等主线决定。

## 三者共同的去污染边界

Open-SWE 与 Orchard 涉及 Scale-SWE/SWE-rebench；SI2CA 涉及 SWE-rebench-V2/SWE-smith。因此可能跨数据集共享 PR、repo、教师轨迹，不能把不同发布名视作独立数据。

SWE-rebench-V2 作者卡明确只排除了原始 SWE-bench 仓库，没有显式过滤其他 benchmark；Scale-SWE 论文只声明排除 Verified repo。这些声明都不能证明排除了 SWE Pro V2 HARD-51。[SWE-rebench-V2 作者警告](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)、[Scale-SWE 论文 §2.2](https://arxiv.org/html/2602.09892v1#S2.SS2)

建议保守排除正式 Pro 全部 11 个 repo 及同源 fork/改名/PR/commit，按 canonical repo+instance/PR 聚组，跨教师/格式/数据源联合去重后再切独立 dev；不读取正式参考补丁与隐藏测试做训练或筛选。上述排除与逐行格式核验尚未执行，resolved 标签也不是去污染合格证。SI2CA/Orchard 的上游 repo 许可仍要核，不能仅靠总数据卡许可覆盖代码片段。

**当前明确未核项：**两个新增来源生成时 mini-swe-agent 版本；与本题观察/结束动作的逐字段相容性；匿名化一致性；实际训练语言与 token 配比；四项正式 benchmark 的交叉与原始许可。没有足够证据声称任何新增数据可完全不处理直接 SFT。
