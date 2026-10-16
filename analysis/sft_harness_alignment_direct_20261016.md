# HLE / ASI direct LLM 训练与评测 prompt 对齐

2026-10-16 北京时间，只读代码和当前训练/验证消息；没有 API、数据改写、队列、评测运行或 Git 操作。

**可以让训练与对应 benchmark 使用同一 system prompt，而且有必要明确统一。但只统一 system 不等于环境、用户任务、输出目标全部一致。当前 HLE 缺官方 system 且回答格式不齐；ASI 的 82 个 SAB 主任务已使用官方 system，991 条辅助数据可以统一 system，但多数仍是函数/代码补全，不能因此称为 ASI 同型完整程序任务。**

## 当前实数

读取 80 下列现成消息，不读取正式答案：

- HLE：`artifacts/data/candidates/hle_existing_2k_20261016/swift_ready/{train,val}.messages.jsonl`。
- ASI：`artifacts/data/candidates/asi_sft_expanded_20261016/{train,val}.messages.jsonl`。

| 项目 | HLE train | HLE val-loss | ASI train | ASI val-loss |
| --- | ---: | ---: | ---: | ---: |
| 条数 | 2000 | 100 | 1073 | 20 |
| roles | 全部 user → assistant | 全部 user → assistant | 全部 system → user → assistant | 同左 |
| 显式 system | 0 | 0 | 1073 | 20 |
| 与 ASI 官方默认 system 相同 | 不适用 | 不适用 | 82 | 20 |
| 仅一个 Python code block | 0 | 0 | 1073 | 20 |
| user 带 workspace、输入与产物契约 | 0 | 0 | 82 SAB | 20 SAB |

HLE 训练回答中，字面出现 `Explanation:` **0**、`Answer:` **789**、`Confidence:` **0**。100 条 val-loss 只保存数学参考最终答案或选项字母，三项格式字段均为 0。这里是字段/字符串计数，不是模型能力、答案正确率或正式格式通过率。

## HLE：同一 system 可以用，但不能只追加指令

固定 system 来自 [hle_system.txt](../configs/eval/prompts/hle_system.txt)，由 `scripts/run_hle_v2.py` 对照固定官方 `run_model_predictions.py::SYSTEM_PROMPT` 验证：

```text
Your response should be in the following format:
Explanation: {your explanation for your answer choice}
Answer: {your chosen answer}
Confidence: {your confidence score between 0% and 100% for your answer}
```

正式请求是该 system + 原始题面（必要时附图），`enable_thinking=false`、`preserve_thinking=false`、64K 总上下文、最大 8K 输出，无模型交互工具。当前训练都只有文本；数学源 user 常额外要求最终答案 boxed，其他题可能要求其他括号/标记，722 份现成教师解答多为解释 + `Answer:`，162 条参考短答没有解释；这些与官方三字段格式并不一致。

已核实际 Swift 源码：HPC 的 `artifacts/envs/sft/lib/python3.12/site-packages/swift/template/templates/qwen.py` 中 `qwen3_5` 注册 `default_system=None`。固定 Qwen Jinja 也只在 messages 有 system 时渲染 system。训练 launcher 未另传官方 system，因此不能把数据缺 system 解释成“框架自动加了 HLE system”。

可做的统一：

1. 若要统一，目标是训练显式使用这份固定 system，源 user 保留完整题目和必要的选项/条件；先解决现有回答的格式冲突和缺失字段，**不是直接给全部旧标签强加三字段 system**。只整理与统一格式冲突的源格式尾句，不改变题义。数学的 step-by-step 可见解释不等于开启隐藏 thinking；是否保留解释应与监督目标一致。
2. 若已有可靠最终答案字段，可将完整可见教师解答安排为 Explanation + Answer，保留原回答，不另生成解释。最终答案必须来自该样本已有字段，不能自动拿正式 HLE gold 或临时猜最后一句。
3. **没有教师置信度就没有真实置信度标签**。不要为了三字段齐全给所有样本补 100%。已有短答也不能凭空补解释。严格的完整三字段监督需要有依据的原始标签，或明确采用不同的训练输出约定并披露格式差异；只加 system、目标回答仍不服从格式，不能称完全对齐。

官方 `run_judge_results.py` 会从任意响应抽最终答案，缺置信度时以 100 作为提取兜底；所以当前 boxed 或短答案并不意味着无法评分。这个 scorer 规则不是训练置信度的真实性证据，也不保证模型在正式 system 下表现无差别。

100 条 `val.messages` 目前是 teacher-forced 短答 loss 代理，不是官方系统提示下的完整生成参考。后续看答案准确率时应使用同一批 `val.tasks` 题，在 HLE system 和相同采样/预算下生成、再比参考；不应把短答 val-loss 当成三字段格式或正式 HLE 表现的验证。

## ASI：system 已有主任务对齐，辅助代码的接口仍不同

固定 [DirectLLMAdapter](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py) 默认 system 为：

```text
You are an expert scientific programmer. When asked to write code, output ONLY a single Python code block. Do not include any explanation outside the code block.
```

`solve()` 只将该 system 与 workspace 的 `prompt.md` 作为两条 messages 发给模型。官方 `InstanceGenerator._prepare_workspace()` 复制所选 `prompt_b1/b2/b3/b4.md` 为 `prompt.md`，将 `data/` 放入当前工作区；文件本身不会通过 read 工具反馈给模型。返回代码块由官方提取器挑选、写入 metadata 指定代码文件（缺省 `simulation.py`），执行一次并收集指定产物。`scripts/run_asi_baseline_v2.py::BaselineDirectLLM` 继承这段 prompt 构造，仅固定请求预算和执行隔离；不改成其他 agent。

82 SAB train 和 20 SAB val 的 system 与上述默认字符串一致，user 自包含：Task / Workspace and execution / Available input files / 可选 Data preview、Scientific background / Output contract；目标为完整 Python 程序，读取 `benchmark/datasets/` 并写任务指定 `pred_results/`。来源路径与正式 ASI 的 `data/`、任务产物名可以不同，只要每条输入输出契约自洽，不能无条件替换路径后仍保留原程序称为对齐。

991 条辅助（976 DS-1000 + 15 SciCode）目前用另一个 system，明确允许 snippet / 缩进函数体，并提醒保留缩进、无工具。全部目标也包在单 Python code block 中。

- **system 可以统一为官方默认句子**：该 system 只要求一个 Python code block，并没有禁止函数或片段。DS-1000/SciCode 的具体函数、变量、补全和缩进约束仍应放在完整 user 中；旧 system 中“按原接口、允许 snippet / 缩进函数体、保留缩进、无工具”等必要要求应移入 user，不能在替换 system 时丢掉。
- **统一后仍有任务差异**：DS-1000 常依赖 user 已给出的 imports、DataFrame、变量或半开 `<code>` 上下文，回答单独不一定可运行；SciCode 多为数值函数返回值。单 code block 不等于包含 imports、入口、读实际文件和写产物的完整独立程序。
- 不应只在 user 末尾加“完整程序/写产物”却保留原片段标签。这会造成指令与标签冲突；真正改成 ASI 同型任务需要自洽包装输入、接口和代码，不能作为简单 system 替换的附带动作。

20 条 ASI val-loss 只覆盖 SAB 完整程序，因此可以检查同类程序的 loss，但不代表 991 条辅助补全的全部分布，也不是正式 ASI 成功率。

## 可直接统一与需要另议的边界

| 事项 | 可直接做的协议整理 | 不能因此声称的内容 |
| --- | --- | --- |
| ASI system | 各来源使用官方同一句；接口约束留 user | 1073 条全是完整文件产物任务 |
| HLE system | 固定官方 prompt 并在训练显式记录 | 旧标签已满足 Explanation/Answer/Confidence |
| 可见解释 / hidden reasoning | 去独立 hidden 字段，保留可见最终解答 | 原教师本来没有 thinking |
| Chat template / 模式 | 同一固定 Qwen 模板、thinking/preserve 设置 | 任务环境、难度与模态已相同 |
| 64K / 8K | 全样本完整验收，统一输出上限 | 强制所有训练答案具有相同长度 |
| 验证 | 保留任务划分，生成时使用对应 benchmark 协议 | teacher-forced val-loss 等于正式任务分数 |

正在运行/已完成的训练不能通过事后改原 JSONL 追溯变成新协议实验。若采用这些整理，应写新数据版本与运行记录，再由根任务决定是否值得重训或继续；本分支没有修改现有文件或作业。
