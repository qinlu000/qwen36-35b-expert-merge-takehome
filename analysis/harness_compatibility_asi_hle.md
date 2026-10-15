# ASI／HLE数据与目标harness兼容检查

更新：2026-10-16。检查固定ASI adapter、固定OpenCode通用源码、现有D3结构审计、Qwen模板及已有自造烟测；新增的实际运行仅为CPU tokenizer渲染。没有读取正式题面、答案、reference或隐藏测试，没有调用API／模型、执行训练数据中的命令、拉镜像、修改runtime或正式配置。

## 结论

| 数据／目标 | 当前能支持什么 | 不能据此声称什么 |
| --- | --- | --- |
| D3静态程序 → ASI/OpenCode | 可作为科研实现能力的静态SFT辅料候选 | 不含OpenCode原生多轮工具轨迹，不能改字段后称同harness |
| OpenCode → Qwen模板 | 已有假端点两轮工具烟测；本轮规范化后CPU渲染通过 | 未验证真实Qwen工具生成、长上下文、压缩和实际科研任务成功率 |
| 静态QA → HLE | 题目／回答监督形式相近，可补学术知识和推理 | 不自动满足HLE最终格式、置信度或342道图像题的覆盖 |
| HLE图文 | 固定基座支持视觉；CPU预处理和图像占位符已有证据 | 尚未验证GPU／HTTP图文链路、图像理解或完整HLE得分 |

不必要求所有训练样本都采用目标工具harness。静态程序与QA可以迁移领域能力；但要训练多轮执行、观察后的纠错和停止行为，必须有真实动作／反馈，静态答案不能补造这些记录。

## D3：如何辅助SFT，以及缺少什么

现成发布为`osunlp/D3-Gym-Trajectories@b21b5006956d7d246cf3e35277b13323780a45b2`，32B文件2,153条。复用已有结构审计`artifacts/data/audits/readiness_structure_20261015.json`，本轮没有重新打开程序答案。其schema只有`instruction/input/output`；没有`messages/tools/task_id/instance_id/repo/license/resolved/result`。先前小样本检测到公开teacher输出带`<think>`与Python代码围栏，但这不是整库质量证明。[固定发布](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/tree/b21b5006956d7d246cf3e35277b13323780a45b2)

在完成来源与内容审核后，可以把任务说明和允许提供的输入／数据预览放在user侧，把该发布的最终程序放在assistant监督侧。这是一条静态程序生成记录，不增加假工具轮次。不能把`expected_answer`、gold、参考输出、eval_script或评分器信息放入policy输入；这些字段如存在，只供隔离的清洗／验证流程使用。未审完的`input`也不能仅因字段叫input就认定没有评分特权内容。

如果采用non-thinking训练配方，应按已发布teacher推理的明确边界处理`reasoning_content`或完整平衡的`<think>…</think>`，保留最终程序与必要的可见说明。不能用任意字符串截断丢掉程序，也不能靠`preserve_thinking=false`假定已有teacher推理会自动消失。若最终选择thinking配方，则保留哪些公开推理字段也应统一记录；当前全局偏好仍待确认。

D3缺失的关键内容包括：

- OpenCode的system prompt、工具定义、assistant工具名／参数／call ID。
- 实际命令／读写编辑动作、工具返回内容、退出状态、错误及后续修复。
- 多轮因果顺序、终止原因、原生压缩后的真实上下文。
- 环境／输入／产物版本、实际验证结果与单条任务来源映射。

因此不能把Python答案包装成一次`write`或`bash`再填“成功”反馈，称为原生执行轨迹。若使用D3任务环境另行采集，需在目标OpenCode里真实执行，再由隔离的verifier判分；这是一份新轨迹，而非现有SFT JSON的无损转换。D3任务metadata有`task_id/original_repo`，现成trajectory却没有这些字段，任务和轨迹的可靠关联、许可与train/dev联合分组仍未完成。[D3任务metadata](https://huggingface.co/datasets/osunlp/D3-Gym/tree/8499689ac98882a7cac9b5ef9e93365cc37df57e)、[环境契约](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)

## ASI：OpenCode实际消息与工具边界

固定ASI源码为`cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`，OpenCode 1.17.15对应commit`5fb0d1cdb363ecafd55402c451c6634ed15b74b1`。官方adapter使用`opencode run --format json --auto`，把workspace的prompt.md送stdin；自定义provider以`@ai-sdk/openai-compatible`走Chat Completions。正式产物是workspace内指定文件，而不是最后一条文本说“完成”。[ASI adapter](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/opencode_cli.py)

80现有自造烟测的真实工具schema为：

| 工具 | 参数 |
| --- | --- |
| bash | command；可选timeout、workdir |
| read | filePath；可选offset、limit |
| write | content、filePath |
| edit | filePath、oldString、newString；可选replaceAll |
| glob | pattern；可选path |
| grep | pattern；可选path、include |

这里的search是本地glob/grep，webfetch/websearch、MCP与子代理另行禁用。不能把这些工具统称为同一个bash协议：read输出有路径／行号封装，write/edit还涉及文件状态与诊断；参数名和语义应保持原样。[read](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/tool/read.ts)、[write](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/tool/write.ts)、[edit](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/tool/edit.ts)、[glob](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/tool/glob.ts)、[grep](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/tool/grep.ts)

原生JSONL包含`step_start/text/reasoning/tool_use/step_finish/error`。工具事件有`part.tool/callID/state.status/input/output/metadata/time`，实际OpenAI请求转成assistant的`tool_calls`和对应`role=tool, tool_call_id, content`；arguments在wire上是JSON字符串。`step_finish`另带tokens/cost/结束原因。session/message ID与成本留在provenance，不直接当policy文字监督。

ASI adapter的可读log摘要会截短工具参数，且工具摘要不保留完整返回内容；它不能单独用于重建SFT。应保留原始JSONL及真实请求／响应，按call ID和时间重建，不能把多次请求中重复的完整历史连续拼接而重复训练。工具观察作为上下文，assistant动作和回答作为监督；不要把工具结果误标为assistant生成。

固定OpenCode会将completed工具结果变成model messages；错误、中断和pending/running有不同处理。原生压缩还可能：保留最近turn、生成summary、移除早期tool result内容、在摘要请求中stripMedia，并把工具结果限制到2,000字符。**2,000是压缩请求路径，不是所有read/bash正常输出的统一上限。** 要训练与部署一致的长轨迹，应保存当时实际送入模型的上下文和压缩边界，而不是假定完整原始日志始终全部可见。短烟测未验证长历史分支。[消息转换](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/message-v2.ts)、[压缩实现](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/compaction.ts)

### 新发现：ASI配置尚未声明图像输入能力

当前`configs/asi/opencode.json`的自定义`bench/apex-qwen`声明了tool_call/temperature和context/output，但没有`attachment/modalities`。固定OpenCode对无已知模型记录的新模型，默认attachment=false、input.image=false。Qwen本身支持视觉，不代表这份OpenCode配置已声明支持。

OpenAI-compatible工具结果不直接承载图片；OpenCode源码会在模型声明支持时提取附件并另插user媒体消息。因此后续若要求ASI agent通过read查看图像，应显式声明所支持的attachment及text/image输入，并做独立图片工具端点测试。本轮没有修改配置；这与HLE独立客户端直接发送图片是两条链路。[provider能力默认](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/provider/provider.ts#L1434)、[modalities配置](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/core/src/v1/config/provider.ts#L48)、[工具媒体转换](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/message-v2.ts#L138)

最小建议是把下面三个字段合并到现有`provider.bench.models.apex-qwen`对象，其他已选模型参数不变；这里只记录待讨论差异，没有修改候选运行配置：

```json
{
  "attachment": true,
  "modalities": {
    "input": ["text", "image"],
    "output": ["text"]
  }
}
```

精确依据均来自commit`5fb0d1cdb363ecafd55402c451c6634ed15b74b1`：`packages/core/src/v1/config/provider.ts:13`允许attachment，`:48`允许modalities；`packages/opencode/src/provider/provider.ts:1437`给attachment默认false，`:1442`给新模型image默认false；`packages/opencode/src/session/message-v2.ts:138`之后说明并实现工具媒体拆分，其中`:300`之后提取媒体，`:385`之后插入user媒体消息。该片段只改变agent层声明，不会为不支持图片的实际HTTP服务自动增加视觉能力。

## HLE：静态QA相近，但格式／thinking／图片分开检查

当前候选协议是固定test全2,500题，含342图像题、2,158纯文本题；no-tools、单次生成。仅复用已锁manifest和协议，本轮不读取任何正式问题或答案。政策侧只收到问题和必要图片，不接收参考答案或Judge输入。

现有OpenScience/OpenR1可提供静态user→assistant监督，不要求自己补一套终端harness；但其输出不自动符合HLE的`Explanation / Answer / Confidence`格式。non-thinking不等于只输出答案：HLE要求的可见Explanation应保留，不能随teacher的`<think>`一并删掉；也不能为现成答案捏造100%置信度。`expected_answer`等评分字段不放入user/policy上下文，正式HLE的任何gold不进入训练。

Qwen固定模板识别`reasoning_content`和content中的`<think>`，并将工具动作渲染为自己的XML格式、工具返回渲染为`<tool_response>`。`enable_thinking=false`主要给新assistant生成前缀插入空think块；`preserve_thinking=false`仍可能保留最近真实user之后assistant中已有的teacher推理。root已有六个自造fixture的CPU断言通过，证明显式规范化和模板开关是两个步骤，且不应删除Terminus JSON的analysis/plan字段。[固定模型与模板](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0)、[本地模板检查脚本](../scripts/check_trajectory_template.py)

只有文本训练数据不等于模型不能评图像；保留基座视觉模块可以继续作为图文候选，但不能据此保证视觉能力完全不退化。当前CPU自造图像processor已有通过记录，实际GPU／HTTP图文链路尚未通过。342题应保持在固定评测范围，不能因图像接口失败临时删除。

## 本轮CPU渲染结果与证据等级

本轮复用既有**自造**OpenCode请求，不执行其中命令；另外只造简单算术格式与图像占位符。使用80现有Transformers4.55.0／Qwen2TokenizerFast，全部local_files_only、CUDA不可见，未加载模型权重。

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| 既有OpenCode自造wire消息，arguments保留JSON字符串，直接进HF模板 | TypeError | 训练导入时不能假定wire对象可以不处理直接渲染 |
| 同消息仅将function.arguments解析为dict | 通过，5,365 tokens；含bash函数、1个tool_response、空think生成前缀 | 结构规范化后可表示该两轮上下文 |
| 自造HLE算术回答，带Explanation/Answer/Confidence | 通过，106 tokens，三段均保留 | 证明格式可渲染，不证明学术答题或置信度质量 |
| 自造image占位符＋文本 | 1个vision标记 | 没有处理实际图片，不证明多模态服务或视觉理解 |

模板SHA256=`e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。原始wire的TypeError是直接调用HF模板的结果，**不证明vLLM服务一定报错**：服务可能已经规范化arguments，需真实端点验收。模板render通过也不证明模型会生成合法tool_calls、执行正确、遵守预算或通过评分。

复用证据位于80的`artifacts/preflight/asi/opencode_smoke.json`及其中自造run的requests.json/stdout.jsonl、`artifacts/data/audits/trajectory_template_20261016.json`、`artifacts/models/hle_processor_preflight.json`。本轮无消息正文的可提交摘要见[ASI／HLE模板检查摘要](source_snapshots/harness/asi_hle_template_20261016.json)，没有新增共享runtime文件。

## 后续最小动作

1. 先决定thinking训练／评测配方，明确teacher推理、可见Explanation和各harness结构字段的处理；不靠模板flags自动清理已有输出。
2. D3先作为静态程序候选做来源映射、许可和train/dev隔离；若需要科研多轮能力，从独立任务用目标OpenCode真实采集，不补造工具反馈。
3. 保存并验证OpenCode实际tools、原生JSONL与request映射；图像能力声明、工具图片、压缩、参数透传用独立小任务验收。
4. HLE独立做真实服务的文本／图片格式验收；完整保留2,500题范围，Judge与gold保持评分侧隔离。

本报告记录数据与接口证据，不改变正式benchmark配置；本轮没有开始采集、训练或评测。
