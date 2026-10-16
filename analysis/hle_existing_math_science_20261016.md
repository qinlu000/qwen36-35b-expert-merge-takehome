# HLE 现成 Math-v4 / Science-v2 回答核查

核验时间：2026-10-16，北京时间。本轮只读公开卡与 80 已有原始数据，没有教师 API、训练、任务执行、数据导出、队列变更、新 hash 或 Git 操作。

**有远多于 500 条的现成回答，不必重新生成 2000 份答案。Math-v4 可以直接提供强教师最终回答；Science-v2 可以补物理、化学、生物。两者都能删除独立 reasoning_content，保留非空的 assistant.content；这不等于原始教师是关闭 thinking 生成。** 但单凭这两个库不能保持 HLE 全学科比例：人文、CS、Other、工程等仍缺。

## Math-v4：优先现成来源

[NVIDIA 官方卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4)明确为 DeepSeek-V4-Pro **High**，最终答案与上游参考一致才保留。`train` 共 **545,431** 条，其中纯 CoT **285,516**，TIR **259,915**。题源 AoPS / Math StackExchange / MathOverflow；难度从竞赛到大学及研究数学。TIR 含工具过程，当前 HLE no-tools 应取纯 CoT，而非删除工具观察后拼成问答。

80 已有固定 revision `84d42ad0cb960f07f951b9baa9ed2b46a5a18c66` 的首 shard：

```
artifacts/data/raw/nemotron_sft_math_v4/
  84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/train-00000-of-00012.parquet
```

本轮只读该文件全部 **23,605** 条，结果：

| 结构检查 | 数量 |
| --- | ---: |
| subset=cot，恰好一条 assistant | 23,605 |
| assistant.content 非空 | 23,605 |
| assistant.reasoning_content 非空 | 23,605 |
| assistant.content 包含 think tag | 0 |
| 只移除 reasoning_content 后可见回答仍非空 | 23,605 |
| 可见回答含 boxed 答案标记 | 23,605 |
| 非空 expected_answer | 23,605 |

两个原始字段结构实例（只列 schema / 字符数，不复制长推理）：

```json
{
  "uuid": "ultra_dsv4_cot_aops_rs0_000000001",
  "subset": "cot",
  "assistant_keys": ["role", "content", "reasoning_content", "tool_calls", "name", "tool_call_id"],
  "content_characters": 232,
  "reasoning_content_characters": 99490,
  "tools_count": 0,
  "expected_answer_characters": 60
}
```

第二条 `ultra_dsv4_cot_aops_rs0_000000002`：`content` 1,706 字符、`reasoning_content` 11,481 字符、`expected_answer` 140 字符。说明可见解答有长短差别：删除 thinking 后仍有最终答案，有些只剩较短总结，不能称保留了原本全部逐步推理。

已有 `new_academic_20261016/aggregate.json` 给出该首 shard 经原有题族归并后 **12,739 个 train 数学族、1,463 个 holdout 数学族**；不是本轮重新划分。此前扩充脚本已从现成源整理出 817 份满足 64K 完整序列 / 8K 回答限制的数学回答。这里的 12,739 是候选量，**不是新导出的已验收训练量**，也没有证明它们都满足当前 token 上限。仅数量供给看，数学扩到 2k 不需要新 API。

质量边界：发布者验证的是最终答案参考匹配，不是逐步推理经人工证明；题族覆盖与改写泄漏仍不能从条数保证。强教师依据见 [teacher_strength_gate_20261016.md](teacher_strength_gate_20261016.md)。[DeepSeek 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/b5968e9190ef611bbf34a7229255be88a0e937c1/README.md)明确区分 Non-Think / High / Max，不能把 High 的能力证据挪给旧的 non-thinking API 生成答案。

## Science-v2：有现成回答，但必须按教师和质量分流

[NVIDIA 官方卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2)记录 **2,837,712** 条（发布者总数；HF 不完整 viewer 的实显/估算行数不同），四配置为 syn_mcq 96,610、vendor 221,598、rqa 413,519、so 2,105,985。发布者声明物理、化学、生物，存在 CoT、Python、搜索三种形式；教师混合 DeepSeek-V4-Pro / V3.2、Kimi-K2-Instruct、GPT-OSS。因此不能用总规模当“强教师、无工具、正确答案”的规模。

80 已有 revision `6536a5021222a94126968e8c92f29ee47fc8a7df`，四文件各 8 个 8MiB byte ranges，总 256MiB，不是全库。只读这些完整 JSON 行后，`metadata.generation_model == DeepSeek-V4-Pro` 的 **750** 条为：

| 类别 | 现有 byte 样本条数 |
| --- | ---: |
| Biology | 459 |
| Chemistry | 125 |
| Physics | 101 |
| Math | 65 |
| 合计 | 750 |

其中 rqa 62、vendor 688；每条恰好一条 assistant，750/750 的 `content` 与 `reasoning_content` 均非空，`content` 不含 think tag；750/750 未声明工具、没有 tool_calls。只删除独立 reasoning_content 后，750/750 仍保留可见回答。**非空不是回答正确或解释完整的证明。**

样本 `3e1c4f4e4ab7433694782ff0e0733e26`：

```json
{
  "top_keys": ["uuid", "messages", "tools", "license", "used_in", "metadata"],
  "metadata": {
    "topic": "Chemistry",
    "subtopic": "Organic Chemistry",
    "question_format": "OpenQ",
    "generation_model": "DeepSeek-V4-Pro"
  },
  "assistant_keys": ["content", "role", "tool_calls", "function_call", "reasoning_content"],
  "content_characters": 563,
  "reasoning_content_characters": 9325
}
```

该 V4 样本池的 metadata 只有 topic / subtopic / question_format / generation_model；**没有精确权重、reasoning effort、独立 gold 或正确性标签**。存在 reasoning 字段也不能擅自补写“High”或“0813”。另一条 `e2cc9e74599b45ada97743c347c068a9` 的可见回答仅 41 字符，独立推理 102,138 字符，再次说明“完整现成轨迹”和“去 thinking 后保留的最终回答”应区分。

原有归并后的 train V4 候选是 Biology 350、Chemistry 104、Physics 71、Math 48，合计 **573 个候选族**；这不是已验收新增训练量，也不是完整库上限。此前 135 条 Science 无独立 gold 被 hold 的决定未改变；本轮没有将其静默加入训练。更多 vendor 数据可从原库按需读取，不需全量 49GB 下载，但也不能承诺读到的全体都是合格强教师回答。

## 对当前选择的实际意义

1. 用户想复用更多已有回答：**完全可行**。Math-v4 的现成答案足够扩大数量；不必继续为数学或所有 2k 问题调用教师。
2. 如果“不开 thinking”指训练不监督隐藏推理：以上现成源结构可以满足，保留可见 `content`；如果特指原教师关闭 thinking 生成，则 Math-v4 High 不满足这种来源模式，不能改名冒充。
3. 物化生可按 Science-v2 的准确教师子集补充；但实际 effort 未记录、缺独立 gold，应披露并与数学参考匹配样本分开记录。
4. **现成 2k 与全学科 2k 是两件事。** 数学凑 2k 很容易，但会偏离 HLE；当前两源不能补齐 CS、人文、Other、工程，也无图像。若需要维持原领域配额，应继续寻找可追溯强教师的跨学科现成回答，而不是默认用数学填所有缺口。

未修改正式训练矩阵、旧 500 文件、Mixed、训练参数或队列。本报告提供来源与结构证据，由根任务合并讨论。
