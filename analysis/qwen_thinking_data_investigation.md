# 四个训练来源怎样保存 thinking 与 reasoning_content

2026-10-16。按 research 技能只读固定来源 README、既有结构／长度审计和必要的安全元数据列；没有输出原始题面、推理、答案、命令或 patch，没有执行任务、API、GPU、下载或训练。本轮暂停 val 选题，仅新增本报告。

**结论：生成时的 thinking 开关、API／数据文件怎样保存文本、文本是否具有推理语义，是三个不同问题。缺少 reasoning_content 不能证明未开启 thinking；有 reasoning_content 也不能单凭字段名证明开启了专用 thinking 模式。四个来源中，只有 Open-SWE 的选定教师是 Qwen3.6；Terminal 和 OpenR1 的教师是 DeepSeek，D3 是 Qwen3。**

## 一、四源的实际证据

| 来源 | 实际存储结构 | 教师与开关证据 | 已实测的公开推理保存范围 |
| --- | --- | --- | --- |
| Open-SWE mini/Qwen3.6 | messages 含 role/content/**reasoning_content**/tool_calls；tools 单列；另有 **metadata.teacher_model** | 本轮全39片、95291行仅投影 teacher_model：全部 name=`Qwen3.6-27B`、enable_thinking=`false`、reasoning_effort=`null`。固定分布表也标为 Non-Thinking。 | 既有每片128条、共4992条：content 内 think 标签为0；97条含 truthy reasoning_content。本轮进一步复核见下一节，97条并非全部空白。 |
| Nemotron-Terminal-Corpus skill-based | conversations 只有 role/content；无独立 reasoning_content。另有 agent/model/model_provider/enable_thinking 等标量元数据 | 本轮全26片、139841行仅读4个安全标量列：全部 model=`deepseek-ai/DeepSeek-V3.2`、provider=`hosted_vllm`、enable_thinking=`true`、agent=`terminus-2`。 | 既有3328条分层样本含26159个可配对的 assistant 开头 think 前缀；mixed 六片另有5689条全量、34697个前缀。不是全139841行的正文普查。 |
| D3-Gym 32B | JSON 仅 instruction/input/output 三个字符串；无 reasoning_content、工具调用、逐行教师配置 | 固定数据卡的 Qwen3_32B split，即 Qwen3-32B。没有逐行 enable_thinking、reasoning_effort 或原始 HTTP 配置。 | 已下载2153条全量：每条 output 均有一个开头配对 think 前缀，后面保留程序候选；移除前缀后 Python 代码仍在。 |
| OpenR1 default | messages 仅 role/content；另有 problem/solution/answer/generations/is_reasoning_complete/finish_reasons 等；无独立 reasoning_content | 固定数据卡说明教师是 **DeepSeek R1**，通过 SGLang 生成；不是 Qwen teacher。卡片称每次生成上限16K；无逐行 enable_thinking 开关。 | 10片各随机200条，共2000条：1996条有开头配对 think 前缀；4条标签不平衡。不能把这4条自动当作没有推理。 |

一手来源：

- [Open-SWE 固定 README](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)；[固定 data_distribution.md，v1.1 mini/Qwen3.6 行](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)。实际仅使用 `data/minisweagent/qwen36_27b/{scale-swe,swe-rebench-v2}`，没有将卡片其他模型／版本混入。
- [Terminal 固定数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)。教师名称和开关来自本轮实际 Parquet 元数据，不是根据卡片的下游 Qwen 微调结果猜测。
- [D3 固定训练卡](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/blob/b21b5006956d7d246cf3e35277b13323780a45b2/README.md)；[固定作者转换器](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/training/convert_trajectories_to_alpaca.py)。转换器把输入记录的 thinking 与 response 包成带 think 前缀的 output，因此标签也可能是保存格式的一部分，不能证明原始 API 就返回了同样的标签。论文的全推理＋程序采集声明及版本边界见[既有 D3 来源核验](trajectory_sandbox_asi.md#1-已有轨迹怎样产生有验证依据但不是已发布多轮执行日志)。
- [OpenR1 固定数据卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)，L145–167 的生成说明。本项目 default 实际下载93733行，卡片220k名称与多个 config 的规模不能混报。is_reasoning_complete 是多候选相关标记，不是生成开关；其与 messages 中候选的对应关系仍须独立核实。

## 二、Open-SWE 的97条非空字段：不是全部空白

这是本轮新增核查。复用此前**完全相同的4992条索引**：39片各128个端点包含的等距行，`round(i*(N−1)/(128−1))`。只投影物理叶子列 `messages.list.element.role` 和 `messages.list.element.reasoning_content`，没有投影 content、tools、reference_patch 或 model_patch；不调用 tokenizer。

| 指标 | 实测值 |
| --- | ---: |
| 样本记录／总消息 | 4992／587993 |
| reasoning_content 为 null 的消息 | 296523 |
| 非 null 的字段 | 291470 |
| 空字符串 | 291367 |
| truthy 字符串 | 103个，全部在 assistant；涉及97条记录 |
| truthy 但 strip 后仅空白 | 16个 |
| strip 后非空白 | 87个，涉及84条记录 |
| 103个 truthy 值的字符数 | min2、中位9、max33104、合计35187 |
| 87个非空白值的字符数 | min3、max33104、合计35155 |
| 字段内含 think 起／止标签 | 0个 |
| strip 后为 null／none／nil 字面占位 | 0个 |

所以不能用“它们都只是空的 think wrapper”解释97条。至少有很长的非空字段文本；但本次不做正文语义判读，**非空白不等于每个短值都是真实展开的推理**。也没有源原始请求／响应回执来解释：为什么来源全量标 enable_thinking=false，部分保存字段仍非空。现有证据只支持并列报告两件事，不能擅自把整池改称 Thinking 数据。

反过来，绝大部分字段为空也不能仅凭保存结果证明教师完全没有进行问题分析：非思考模式可以直接生成有解释或规划的普通 content；专用通道是否保存，还受服务端 parser、客户端和导出转换影响。这里没有证据证明本来源具体经历了哪一种转换，不能补猜。

## 三、Terminus 的 analysis／plan 不能与 think 前缀混删

固定 Terminus-2 将 **analysis、plan、commands** 定义为动作 JSON 的可见字段；前两项确实可能承载状态分析和下一步推理语义，但它们属于目标协议的正式输出。关闭专用 thinking 模式，仍然需要模型产出这些字段。原生 parser 对缺少 analysis／plan 的合成输入报错，证据见[既有 parser 检查](harness_compatibility_terminal.md#原生-parser-的独立合成验证)。

另一个层次是 `LLMResponse.reasoning_content` 或存入 content 开头的 think wrapper。固定 Harbor 的 parser 使用 content 解析动作；独立 reasoning 是否带回历史还由 interleaved_thinking 等配置控制。当前 Corpus 没有独立 reasoning_content，不能因此说它没有 thinking——全量 enable_thinking=true 与样本内的显式前缀已经提供相反证据。[固定主循环](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py)、[固定 Chat](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/chat.py)。

相同区分适用于普通回答中的可见解释、代码注释、错误诊断，以及 HLE 要求的 Explanation：它们有推理语义，但不是按字段／标签可以识别的专用 thinking 通道。不能以“清推理”为由全部删除。

## 四、对用户已选“清除 teacher thinking／reasoning_content”的具体影响

1. **按可核边界清理。** 独立 reasoning_content 整个去除；assistant 开头配对的 think 推理前缀去除。保留普通回答、程序、工具参数、真实观察与 Terminus JSON 的 analysis／plan。仅删除 reasoning_content 字段会漏掉 Terminal、D3、OpenR1 的 inline 推理。
2. **不能依赖两个模板开关自动清完。** 既有 CPU 合成检查及 Open-SWE 样本已证明：false/false 仍可能把最近 user 后已提供的 reasoning 渲染进去；生成开关与数据清理是独立步骤。见[模板证据](source_snapshots/harness/trajectory_template_20261016.json)及[实际源结构](harness_compatibility_swe.md)。
3. **异常边界单列。** OpenR1 样本4条标签不平衡；若无法从可靠原始结构确定结束边界，应隔离／排除非思考主训练池，不能在“全部清除”的名义下留下未知前缀，也不能靠任意截尾丢掉答案。代码／题内的字面标签不能由全局正则删除。
4. **保留来源事实。** 清理后样本是本项目构造的非思考监督版本，不把教师原 enable_thinking=true 改写为原始 false，也不声称教师推理不存在。报告清理前后长度、保留标签和异常数；移除推理可能改变监督信息，长度减少不是效果提升证据。
5. **不把清理等同于消除推理能力。** 它删除的是可识别的已发布推理文本，不是模型计算或所有有推理语义的文本。训练与部署仍需验收实际模板、loss mask 和新生成字段；本轮没有导出训练集或修改这些设置。

## 五、可复查范围与尚未知项

- 本轮新增全量**安全配置元数据**：Open-SWE95291行 teacher_model；Terminal139841行 model/model_provider/enable_thinking/agent。不是全量正文或全量质量验证。
- 本轮新增**同样本字段结构**：Open-SWE4992行 reasoning_content 的空白、字符长度与标签统计；没有阅读正式 benchmark 内容，没有输出字段正文。
- 复用正文结构审计：SWE4992、Terminal3328及 mixed5689全量、D3全2153、OpenR1跨10片2000；具体采样和聚合见[长度汇总](trajectory_lengths.md)、[科研／QA专项](trajectory_lengths_qa.md)。不能把样本未见标签外推成来源全库无标签。
- 未取得：各来源完整原始 wire、准确教师服务／reasoning parser 版本和采集参数日志；SWE 残留字段的具体来源；D3 每条是否走同一个转换器；所有上游推理与最终答案的语义关系。对于这些问题，本报告保留未知，不用数据字段缺失推断生成过程。

本轮只写本报告，未修改旧审计、训练脚本、配置、claud 或 Git；未决定 LoRA rank。
