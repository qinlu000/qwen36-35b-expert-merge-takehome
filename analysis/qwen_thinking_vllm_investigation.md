# Qwen thinking：模型 token、vLLM 字段与训练清洗

2026-10-16。只读核查已安装源码和固定模型模板；未运行模型、API、GPU或评测任务，未改配置。**用户的理解在模型层面成立：Qwen 用 `<think>…</think>` 表示专用思考段；`reasoning_content` 是服务/客户端把该段分离后存放的字段，不是模型另有一套独立的思考输出。**此前若把两者描述成两种独立机制，应予修正。

## 1. 本项目实际选用的服务解析

本项目选择 `reasoning_parser=qwen3`，见 [协议](../configs/eval/protocol_v2_unified64k8k.json)及 [启动脚本](../scripts/smoke_base.py)。HPC 安装元数据实查为 **vLLM 0.20.2**，源码根目录是 `/data/user/qinlucao/projects/apex-takehome/artifacts/envs/base-inference/lib/python3.12/site-packages/vllm/`。以下行号来自这份安装源码；公开链接固定到官方 `v0.20.2`，不以 latest 文档替代版本证据。

`Qwen3ReasoningParser` 的 start/end 是 `<think>`、`</think>`；该实现针对 Qwen3.5 类模板说明，开头 `<think>` 通常已在输入 prompt 中，所以新生成序列可能只有结束标记。非流式解析会去掉生成文本中的开头标记，再按 `</think>` 切出 `(reasoning, content)`；分离后的字段不保留这对外层标记。启用思考却没有结束标记时，会把剩余文本作为 reasoning；另有 `<tool_call>` 的隐式结束兼容分支。这些都是 token/文本边界解析，不是语义判断。[parser L20–37、L53–61](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L20)、[非流式 L115–158](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L115)、[流式 L160–231](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L160)

**精确版本的字段名是 `reasoning`。**vLLM 0.20.2 的 `ChatMessage` 和 `DeltaMessage` 定义 `reasoning`，没有为它配置 `reasoning_content` alias/serialization_alias；父类只是允许额外字段，没有自动改名。完整响应实际执行 parser 后，把结果放进 `ChatMessage(reasoning=…, content=…)`。[ChatMessage L54–64](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/protocol.py#L54)、[DeltaMessage L258–262](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/engine/protocol.py#L258)、[父类 L26–55](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/engine/protocol.py#L26)、[调用解析 L1383–1393](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1383)

## 2. 为什么轨迹里又叫 reasoning_content

80 上 mini 2.4.6 安装的 LiteLLM 为 **1.105.1**，Harbor 0.24.0 环境为 **1.93.0**。两份实际源码都把服务的 `reasoning` 规范成客户端的 `reasoning_content`：非流式 `_extract_reasoning_content` 先检查旧字段，再检查 `reasoning`；流式 handler 也直接改名。因此，正常 OpenAI-compatible 返回路径有现成兼容代码，不能说必须由我们从头桥接。

| 层次 | 已查实位置与行为 |
|---|---|
| LiteLLM 1.105.1 | `litellm_core_utils/prompt_templates/common_utils.py:1904–1921`；`llms/openai/chat/gpt_transformation.py:628–640, 838–855`。读取两种名字，产出 `reasoning_content`。[固定公开源码入口](https://github.com/BerriAI/litellm/tree/v1.105.1/litellm) |
| LiteLLM 1.93.0 | 对应 `common_utils.py:1463–1480`；`gpt_transformation.py:563–575, 767–784`。同样的兼容逻辑。[固定公开源码入口](https://github.com/BerriAI/litellm/tree/v1.93.0/litellm) |
| mini 2.4.6 | `models/litellm_model.py:99–106` 保存完整 `response.choices[0].message.model_dump()`，并保存完整响应到 extra；不只摘取 content。[固定 mini 源码](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/litellm_model.py#L99) |
| Harbor | `llms/lite_llm.py:425–445` 读取 `reasoning_content`；Terminus 轨迹 `terminus_2.py:1631–1635` 保存该字段。[模型接口](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/lite_llm.py#L425)、[轨迹记录](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1631) |

LiteLLM 还可能在上游没有独立字段时，从 content 的成对 think 标签提取 reasoning；因此，最终数据里的字段名本身不能证明当时用了哪一版服务或解析器，也不能证明它是另一种原生模型行为。上述 LiteLLM 版本/行号以80实际安装源码为依据，未将其他版本实现混入。

**入站历史另有一层：**vLLM 0.20.2 `chat_utils.py:1525` 读 `message.get("reasoning")`，随后 `1550–1554` 同时写 conversation 的 `reasoning` 和 `reasoning_content`，兼容读取旧字段的模板。因此原生 vLLM 的 `reasoning` 回包直接回传时，服务已有桥接；但该函数没有 fallback 读取仅含旧名的 `reasoning_content`。LiteLLM 发出历史时是否再次规范字段、是否按 provider 删除字段，仍须对实际配置做 wire 验收，不能只凭接收端源码保证整个往返链。[入站代码 L1516–1554](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/chat_utils.py#L1516)

## 3. enable_thinking 和 preserve_thinking 分别控制哪里

固定模型 revision 是 `995ad96eacd98c81ed38be0c5b274b04031597b0`；[模板原件](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/chat_template.jinja)，本地 [逐行快照](source_snapshots/model_chat_template.jinja)，SHA256 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。

- **`enable_thinking=false` 控制新生成前缀。**模板 L147–153 预先插入空的 `<think>\n\n</think>\n\n`，将专用思考段关闭；它不是删除历史记录字段的清洗器。vLLM 向 parser 传递有效 chat_template_kwargs（serving L244–250），parser L43–46 读取该开关。流式服务发现输入 prompt 已结束思考后，直接按 content 处理后续生成（serving L735–743、L956–984）。普通回答里仍可以有可见解释，这不等于重新启用了专用思考通道。[传参](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L244)、[流式分支](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L956)
- **`preserve_thinking=false` 控制历史序列化，但不是清空全部历史。**模板 L91–103 优先读历史 `reasoning_content`，否则尝试从 content 的结束标签拆出；只要 assistant 位于最近一次真实 user query 之后，仍会保留已有 reasoning，即便 preserve=false。工具返回并不一定开始新的真实 user query。因此六个 CPU 合成 fixture 中观察到的“关闭两开关仍可保留历史 teacher reasoning”，不能被说成“关 thinking 后模型必然仍产生新的隐式思考”。
- **两者不是自动去重。**模板有字符串 `reasoning_content`（包括空串）时优先使用它，跳过从正文拆 think 的 else 分支；若正文也含同一段 think，它不会语义判重。直接训练前显式清洗源字段/正文仍有必要，但目的是消除同一思考段的多种存储表示。

源码还能说明一个边界：非流式 parser 先检查 `</think>`，之后才检查 thinking_enabled=false，因此若异常生成仍含结束标记，它仍可能分出 reasoning；这只是可达代码分支，本轮未实际观察到这种模型输出。不能把开关当成输出字符串的强制禁用过滤器，也不能据此说正常关闭无效。[准确顺序 L136–148](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L136)

## 4. 8192 输出预算如何计数

**同一次生成的 reasoning、普通 content、工具调用及生成的边界 token 共用输出预算，不存在另送8192 reasoning再给8192 answer。**非流式 usage 用原始 `output.token_ids` 的长度求和；流式也累加生成 token IDs，再输出 completion_tokens。移除 JSON 字段中的 think 标签，不会倒扣这些已生成 token。模板预放在 prompt 中的空思考块/开头标记计入 prompt，而非本次 completion。[完整 usage L1620–1630](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1620)、[流式累加 L1033–1038](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1033)、[流式 usage L1216–1224](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1216)

请求同时存在两个上限名字时，`max_completion_tokens` 优先于 `max_tokens`；总输入输出仍受 max_model_len 限制。[预算 L424–433](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/protocol.py#L424)。该版本 Chat Completions `UsageInfo` 没有单列 reasoning_tokens；不能从普通 content 长度倒推全部输出成本。[UsageInfo L104–108](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/engine/protocol.py#L104)

`include_reasoning=false` 会在非流式解析后把待返回 reasoning 置空，不等价于 `enable_thinking=false`，也不能保证省掉生成开销；后端 usage 仍以生成 token IDs 计算。[隐藏返回字段 L1383–1390](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1383)

## 5. 本项目应怎样落地和验收

训练规范应记录为：清除 assistant 专用思考段的所有已识别表示（数据中的 `reasoning_content`、如纳入原生 vLLM 轨迹则含 `reasoning`、以及正文开头配对 think 块），保留正常答案、可见解释和工具动作；不把它说成删除两套独立思考。空字段、字段与正文重复/冲突、未闭合标签应明确记录或排除，不能盲目用全局正则删正文。Terminus JSON 的 analysis/plan 属于 harness 输出协议，不能因字段看起来像推理就一并删除。

本轮查实的是源码与模板行为，**没有完成真实 HTTP 往返验收**。后续只需用无 benchmark 正文的合成消息核验一次：实际发送的两个 template 开关；原始服务回包 `reasoning`、客户端规范后的 `reasoning_content` 与 content；回传历史字段及最终渲染；原始 token IDs/usage 与输出上限。字段为空也要同时排除“harness丢弃/只隐藏返回”的情况，才能当作专用思考未输出的证据。
