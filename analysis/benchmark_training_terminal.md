# Terminal-Bench 2.0 / Terminus2 训练数据补充核验

核验日期：2026-10-15。范围：仅公开数据卡、官方论文、通用代理及采集入口代码；没有读取数据行、任务指令、参考答案或测试内容，没有下载任务包、恢复下载、运行任务或调用模型 API。本次只补充 Nex Agent-SFT 与 Endless Terminals 两个来源；Nemotron-Terminal-Corpus、OT-Agent 沿用此前核验，本文不重新证明其格式或清洁性。

## 结论与采用建议

1. **Nex Agent-SFT 是实际多轮训练消息候选，但未证明原生 Terminus2 协议。** 它比只有任务包的来源更容易直接用于 SFT；不过公开卡未提供本次冻结 TB2 测试集的逐记录排除证据，也未锁定每条轨迹的 scaffold。不能把其 TB2 评测使用 Terminus2，推导成发布的训练轨迹也使用 Terminus2。
2. **Endless Terminals 是有价值的可执行任务池，不能计作现成、原生 Terminus2 的成功轨迹。** 约 2,500 个任务转换为 Harbor；官方示例 agent 使用 `type/command/timeout_sec`。若选它，应在目标 Terminus2 harness 下采集一小批本地/teacher 轨迹并验证，再进入 SFT；这会增加推理、容器与验证成本。
3. 现有 Nemotron-Terminal-Corpus/OT-Agent 中，只有通过目标协议和来源隔离核验的部分可以先计入可用量；Nex 作为增补，Endless 作为缺口补采来源。不要为了凑数量把一般 shell 问答、TB2 测试解题轨迹或不可还原执行状态的轨迹算作合格 Terminal 专家训练数据。

## 1. Nex Agent-SFT：已有 messages，协议与测试隔离仍需核验

### 固定来源

- [官方数据卡，固定 revision d8d4de5643f9fe9d3fc3f89b3d55b8709ddc35c9](https://huggingface.co/datasets/nex-agi/agent-sft/blob/d8d4de5643f9fe9d3fc3f89b3d55b8709ddc35c9/README.md)，HF 最后修改时间 2025-12-09 11:05:36 UTC。
- [Nex-N1 官方项目 README，固定 41049eee5e8fc467a7fa887fe7ffec853ac0bf2f](https://github.com/nex-agi/Nex-N1/blob/41049eee5e8fc467a7fa887fe7ffec853ac0bf2f/README.md)，该 commit 时间 2025-12-05 07:06:25 UTC。

### 公开卡能证明什么

- 卡称总计 **69,008** 条，从 Nex-N1 训练数据重新选 query，使用 **DeepSeek-V3.1-Nex-N1** 重新生成 responses；其中 `agentic_code` **24,796** 条。它同时包含 agent、chat、deep_research、html、tool_calling 等配置，不能将总量全部当作 terminal 轨迹。
- 公开 schema 有 `uuid`、`messages`、`tools`、`generator`。`messages` 包括 system/user/assistant/tool response；`tools` 包括工具名称、描述和参数属性。因此它是实际消息训练数据，不只是可执行任务描述。
- 卡未列出 `agentic_code` 的具体工具集合、动作 JSON、会话状态约定或每条记录的 scaffold。**目前不能确认存在 `keystrokes/duration/task_complete` 的原生 Terminus2 子集。**
- 官方项目 README 明确 TB2 使用官方 Terminus2，SWE-bench Verified 使用基于 OpenHands 的内部 scaffold；这是**评测**设置。它还提及 qwen3_coder function calling parser，均不足以证明发布训练数据的工具协议。
- 数据卡许可为 **ODC-BY**；应保留归属与数据来源记录，不能误记成 Apache-2.0。

### 进入训练前的必要条件

- 针对拟用子集核对动作、工具返回、退出码、cwd/env 状态、交互式会话及完成标记；只有等价语义的部分才可转换。状态不完整时不能只重命名工具或拼接 shell 文本。
- 目前检查的官方卡/README 没有提供针对本次冻结 TB2 89 题的逐记录去污染清单或可复核 lineage。需要排除直接测试题、公开解题轨迹、测试派生题和近重复；不能凭“重新生成 response”视为去污染。
- 定位：**已有轨迹的通用 agent 增补候选**；目标协议与来源核验通过前，不承诺它能立即提供多少合格 Terminal tokens。

## 2. Endless Terminals：可执行环境池，需要目标 harness rollout

### 固定来源

- [官方仓库，固定 99f4c74b75faacf21e53d3dc01df170902e924cb](https://github.com/kanishkg/endless-terminals/tree/99f4c74b75faacf21e53d3dc01df170902e924cb)，commit 时间 2026-03-31 23:17:55 UTC。
- [官方 README](https://github.com/kanishkg/endless-terminals/blob/99f4c74b75faacf21e53d3dc01df170902e924cb/README.md)。
- [作者论文 Scaling RL Environments for Terminal Agents，arXiv 2601.16443v3](https://arxiv.org/html/2601.16443v3)。
- [作者发布的数据卡，固定 26ecf78458e7f756e4d06780d5fbf3dd78e91815](https://huggingface.co/datasets/obiwan96/endless-terminals/blob/26ecf78458e7f756e4d06780d5fbf3dd78e91815/README.md)，HF 最后修改时间 2026-01-24 01:33:29 UTC。

### 是什么、还缺什么

- 论文称生成 **3,255** 个 Apptainer 任务，其中约 **2,500** 个转换成 Harbor 格式；HF 卡称约 2,500 个 synthetic terminal-use environments。
- 生成过程包括类别/复杂度/场景采样、指令与隐藏 GT、容器与初态检查、终态测试、o3 pass@16 可解性过滤。论文称 GT 对被测 agent 不可见。它是环境与验证任务的工程资源，不是普通 shell 问答集。
- 公开文件索引包含环境、task 配置、初态检查、终态测试、solution/solve.sh 与模型结果摘要。**本次仅观察路径，没有打开其内容；这些路径存在不等于已发布完整、原生 Terminus2 对话轨迹。**
- [官方 Harbor agent 源码](https://github.com/kanishkg/endless-terminals/blob/99f4c74b75faacf21e53d3dc01df170902e924cb/endless_harbor/endless_agent.py#L65) 的 `LLMActionDecision` 使用：
  - `type`：`command`、`done`、`invalid`；
  - `command`：shell 命令；
  - `timeout_sec`：可选时限，默认 180 秒。
- agent 使用 Echos 格式提示，并调用 Harbor 的 `environment.exec()`。**Harbor 是执行后端；它不意味着模型可见 harness 就是 Terminus2。** 上述动作不等于 stateful tmux 的 `keystrokes/duration/task_complete`。
- [官方采集入口 generate_solutions.py](https://github.com/kanishkg/endless-terminals/blob/99f4c74b75faacf21e53d3dc01df170902e924cb/generate_solutions.py) 调用多次采集，默认模型 Qwen/Qwen3-32B、max actions 16；它说明可以生成解题结果，但使用它仍要付出实际推理与任务执行成本。其默认 agent 不能直接算作目标 Terminus2 rollout。本次未运行。
- 仓库还有 SkyRL PPO 训练入口；当前同底座专家 SFT + AVG/TIES 方案无需引入这条 RL 链路。

### 许可与 TB2 风险

- **代码**：[仓库 LICENSE](https://github.com/kanishkg/endless-terminals/blob/99f4c74b75faacf21e53d3dc01df170902e924cb/LICENSE) 为 **Apache-2.0**。
- **任务数据**：固定 HF 卡正文后有 `license: mit`，即作者卡声称 **MIT**；但 YAML 位于正文之后，HF API 的结构化 cardData 没有解析出 license。代码许可与数据声明应分别记录，下载使用前确认随包许可与归属；不能把代码 Apache 当作任务数据许可。
- 论文将 TB2 用作迁移评测，生成过程是程序化类别/场景合成；这比直接拿测试解题轨迹更符合候选来源。但检查的来源没有本次冻结 89 题的逐任务排除证明，**不能宣称零污染**。仍需任务来源记录、ID/文本近重复检查和人工复核可疑项。
- 定位：**可复用的任务容器、初态和验证器，需适配与补采**。适合小规模补足目标协议训练轨迹，不宜在紧张窗口内重跑全量任务生成、pass@16 筛选或 PPO。

## 建议的最小决策顺序

1. 先冻结 TB2 正式 Terminus2 版本、提示、动作/观察协议与统一预算；训练数据向目标协议适配，正式评测不为旧轨迹改变 harness。
2. 对已有 Nemotron-Terminal-Corpus、OT-Agent 及 Nex 候选记录做来源和协议审查。没有状态语义与测试隔离证据的部分不计入已落实训练量；可保持原生消息的子集先进入独立 dev 验证。
3. 若合格现成轨迹不足，再从 Endless 的独立任务中选小批，在同一 Terminus2 配置下采集并运行验证器；仅成功且动作/观察完整的记录进入 SFT。先测每条任务的采集耗时，再决定数量。

以上仅改变候选训练来源，不替代正式 TB2 89 题 × 5 seeds 的统一评测要求，也不构成“4 H100 和剩余时间必能完成补采”的承诺。
