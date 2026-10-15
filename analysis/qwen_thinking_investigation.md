# Qwen thinking：从原生序列到 API 字段与训练目标

2026-10-16。针对用户要求深入核实，暂停 val 选题与训练清洗。范围为固定 Qwen3.6-35B-A3B 模型卡/词表/模板、实际 vLLM/LiteLLM 源码、候选 ms-swift 固定源码和已有数据安全元数据；另做 CPU 自造消息的真实 tokenizer 渲染。没有模型推理、任务执行、训练、GPU 作业或付费 API 调用。本报告不改变 64K/8K 或 LoRA 参数。

## 结论与对此前解释的修正

**用户记忆正确：本模型原生 thinking 由 `<think>…</think>` 界定。`reasoning_content` 通常是同一段内容被服务/客户端解析后的结构化表示，不是 Qwen 另有一套独立思考。**此前只说“一个是标记，一个是字段”在存储层面成立，但不足以解释模型到 API 的关系；不能据字段名把它们看成两种能力或两份额外 token。

固定模型卡明确默认先输出 think 段，提供 `enable_thinking=false` 的非思考模式；Qwen3.6 不官方支持旧 Qwen3 的 `/think`、`/nothink` 软切换。此处只讨论可见显式思考段，不据字段是否出现推断全部语义推理能力。[固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#using-qwen36-via-the-chat-completions-api)、[非思考模式](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#instruct-or-non-thinking-mode)

## 一段 thinking 的处理链

```text
模型完整序列：<think>教师/模型思考</think>答案或工具动作
    ↓ Qwen reasoning parser 按 token/文本边界拆分
vLLM 0.20.2 API：reasoning = 思考，content = 答案/工具正文
    ↓ 本项目实际 LiteLLM 接收规范化
轨迹消息：reasoning_content = 思考，content = 答案/工具正文
    ↓ 保留该字段且使用支持它的 HF 模板时
下一次模型输入：重新序列化为 <think>思考</think>正文
```

框架、版本和来源不同，也可能将完整带标签文本直接保存在 content，或只保存最终正文。故“content 没有 think 标签”“不存在 reasoning_content”都不能单独证明教师没有生成过 thinking。服务返回字段可能被隐藏或采集器可能未保存。

精确 vLLM0.20.2 输出名是 `reasoning`；本项目 mini/Harbor 各自的 LiteLLM1.105.1/1.93.0 接收端会转换为 `reasoning_content`，mini/Terminus 的日志也有保存路径。vLLM 入站已有 reasoning→模板所需字段的转换；仅旧字段回传的完整往返仍待 wire 验收。这是版本及序列化差异，不能把旧官方通用部署文档中的字段名直接套进当前安装版本。[固定 parser](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L20)、[固定响应字段](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/protocol.py#L54)、[版本与客户端专项](qwen_thinking_vllm_investigation.md)。Qwen 通用部署文档的 Qwen3 示例仍写 reasoning_content，适合说明解析概念，不能覆盖精确版本源码。[官方通用说明](https://qwen.readthedocs.io/en/latest/deployment/vllm.html#parsing-thinking-content)

Qwen3.5/3.6 的 opening `<think>` 通常已在输入前缀里，模型新生成部分可能只有思考正文、`</think>`和答案。仅在 completion 中找成对 opening/closing 标签会漏判；应结合真实 prompt、有效开关、parser 及原始 usage 解释。[parser 说明与分支](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/reasoning/qwen3_reasoning_parser.py#L20)

## 三种操作不是同一件事

| 操作 | 实际作用 | 不等于 |
| --- | --- | --- |
| enable_thinking=false | 待生成前缀预填空 think 块，选择官方非思考回答路径 | 自动删除训练文件或历史消息中已经保存的教师思考 |
| preserve_thinking=false | 序列化时不保留更早用户轮次的思考；最近真实 user 之后仍保留已有 thinking | 清除全部历史 thinking；工具观察也不一定构成新的 user 问题 |
| 删除训练教师思考 | 显式从最终训练条件/目标移除思考内容，再按非思考模板和 loss 规则处理 | 仅关闭 API 返回字段，或仅将思考的训练 loss 置零 |

前两项不是另换一套权重。开启/关闭新生成，与保留/清理已知历史必须分开核验。此前合成样例里“两个开关为 false 仍能序列化最近轮教师思考”，不能推导为“关闭模式后模型通常仍会生成新的 thinking”。[固定模板](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/chat_template.jinja#L89)、[生成前缀](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/chat_template.jinja#L147)

## 真实 tokenizer 的 CPU 合成验证

在80现有CPU环境用固定revision的AutoTokenizer，不载权重、不调用模型。只用 `SYNTHETIC_QUESTION/REASONING/ANSWER` 自造内容，完整序列包含角色和模板；数字不代表真实任务成本。

| 输入保存形式 | 渲染后思考出现次数 | 完整 token 数 |
| --- | ---: | ---: |
| content 内一个 think 块 | 1 | 35 |
| 独立 reasoning_content，同一内容 | 1 | 35 |
| 同时向字段与正文重复写入 | 2 | 44 |
| 去掉思考正文，只留答案 | 0，仍有模板空块 | 27 |

前两者渲染字符串完全一致。第三行是故意制造的双写，不表示正常 API 会天然算两遍。固定模板优先读字符串 reasoning_content，不自动判重正文；字段存在但正文重复时需数据适配器处理。

固定词表中的 `<think>`/`</think>` ID 分别为248068/248069；它们在 added_tokens_decoder 中 `special=false`，真实 decode(skip_special_tokens=True)仍保留这对标签。因此不能假定“跳过 special tokens”就已清掉 thinking。开关关闭时的空块属于模板开销，不是残留的教师思考。[固定词表配置](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/tokenizer_config.json)、[合成回执](source_snapshots/qwen_thinking_template_probe_20261016.json)

**8192 上限包含本次所有生成 token，含思考、正文与动作。**API解析或隐藏 reasoning 不退还生成预算；预填在 prompt 的 think 标记计输入。不能把展示的 content 长度当全部 completion 用量。[vLLM usage 实现](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/serving.py#L1620)

## 对现有训练数据的影响

- Open-SWE 全39片95,291条安全元数据均记录教师Qwen3.6-27B、enable_thinking=false。既有4992条样本仍有97条含truthy reasoning_content；复核103个字段中16个仅空白、87个去空白后非空，涉及84条记录，原始wire归因未知。不能据此把全库叫thinking数据，也不能直接把每个非空字段判成开了thinking。
- Terminal 全26片139,841条安全元数据均为DeepSeek-V3.2、hosted_vllm、enable_thinking=true，保存的对话只有role/content、思考在正文前缀。它不是Qwen教师；缺独立reasoning_content字段不表示没有显式思考。
- D3选择的Qwen3-32B发布文件和OpenR1的DeepSeek-R1来源，也不能套用当前Qwen3.6教师开关。已存正文前缀、生成元数据和原始wire分别是不同证据。

以上是发布/记录证据，不证明每个teacher响应或完整日志都可恢复。旧raw/clean长度报告只比较**已保存、能识别的公开内容**，不是重算教师当时完整生成量；SWE清后仍长的主因判断来自该保存序列，不能外推不存在未记录思考。详见[来源专项](qwen_thinking_data_investigation.md)。

## 训练加载器还需单独验证

候选ms-swift的Qwen3.6走qwen3_5训练模板，不能用HF apply_chat_template成功代替训练验证。固定标准messages加载器会过滤额外消息字段，未默认把reasoning_content转进content；专用预处理器可有别的行为。正常CLI对混合思考模板通常追加ignore_empty_think：空块留在输入、相应loss为零；它不屏蔽非空思考全文。

“删除思考”和“保留思考、只mask其loss”不同：后者答案训练仍看到了教师思考，且仍消耗这部分上下文/前向。若部署用非思考路径，不能将两者混称相同配方。[固定训练预处理](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L83)、[训练源码专项](qwen_thinking_training_investigation.md)

当前没有执行任何批量清洗或SFT。继续前要用最终训练环境的合成样例核dataset loader前后、input_ids、labels和loss_scale；最终服务的thinking开关与字段往返也另验收。对是否删除教师思考的决定，应依据要训练的行为和独立val，不能仅根据JSON字段名称；Terminus必需analysis/plan与正常可见答案正文也不等于模型专用think通道。
