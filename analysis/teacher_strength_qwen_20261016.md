# Open-SWE 的 Qwen3.6-27B 教师与 Qwen3.6-35B-A3B 比较

2026-10-16。按 research 工作流真实联网查阅 Qwen 官方 Hugging Face 模型卡、官方发布博客、HF 官方仓库元数据，并结合本项目已核验的 NVIDIA 固定数据来源。仅研究；未下载权重、安装、运行任务、模型/API 推理或修改模型／协议。

**结论：Qwen3.6-27B 确实公开，而且 Qwen 官方同一张比较表中，它的修复、终端和 HLE 分数都高于我们的 Qwen3.6-35B-A3B。因此有证据把它视为能力更强的教师候选。但没有找到两者在本项目“非思考、64K／8K、相同 harness”下的直接对照，不能把公开榜分差当成我们当前设置的已测差距。**

## 精确型号已确认，没有用 Qwen3.5-27B 代替

- [官方 Qwen3.6-27B 仓库](https://huggingface.co/Qwen/Qwen3.6-27B)实际可访问。[HF 官方 API](https://huggingface.co/api/models/Qwen/Qwen3.6-27B)本轮返回 private=false、gated=false；本次固定 revision 为 `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`。
- [Qwen 官方发布博客](https://qwen.ai/blog?id=qwen3.6-27b)，发布日期 **2026-04-22**，明确它是27B **dense** 多模态模型，同时支持 thinking／non-thinking。这次已取得精确型号的一手架构依据，不是从3.5同名尺寸推断。
- [固定27B配置](https://huggingface.co/Qwen/Qwen3.6-27B/blob/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/config.json)为 `Qwen3_5ForConditionalGeneration`，64层常规 FFN；我们的[固定35B-A3B模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)明确35B总参数、3B激活的 MoE。**总参数大小、每token激活量和模型能力不是同一指标，不能只凭35>27或27>3决定强弱。**

## 官方同表结果

下表直接取自[固定 Qwen3.6-27B 模型卡的 Language 比较表](https://huggingface.co/Qwen/Qwen3.6-27B/blob/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/README.md)，同时由上述官方发布博客复核。表头明确分别列出 **Qwen3.6-35B-A3B** 和 **Qwen3.6-27B**；另有 Qwen3.5-27B 列，未混用。

| 公开评测 | Qwen3.6-35B-A3B | Qwen3.6-27B | 27B 差值／百分点 |
| --- | ---: | ---: | ---: |
| SWE-bench Verified | 73.4 | 77.2 | +3.8 |
| SWE-bench Pro | 49.5 | 53.5 | +4.0 |
| SWE-bench Multilingual | 67.2 | 71.3 | +4.1 |
| Terminal-Bench 2.0 | 51.5 | 59.3 | +7.8 |
| HLE | 21.4 | 24.0 | +2.6 |
| LiveCodeBench v6 | 80.4 | 83.9 | +3.5 |

这支持“官方报告的这几项能力上27B更强”，不支持“27B所有任务、所有模式都更强”。未发现 ASI-Bench 的两者同条件分数。

## 哪些条件可比，哪些不能移植

1. **官方同表可比性较强。** 同一发布方、明确的两款模型列和统一表注，优于将不同第三方 harness 的榜分拼在一起。但这仍是作者报告结果，不是本项目重现。
2. **SWE Pro 不是本题 HARD-51 的直接成绩。** 模型卡 L270说明使用内部 bash＋file-edit scaffold、temperature1.0／top_p0.95／200K context，并修订部分公开 Pro 任务后统一评估。不能把53.5或49.5称作本题固定 hard/test51 与 LockedMiniSwe 的分数。[固定表注](https://huggingface.co/Qwen/Qwen3.6-27B/blob/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/README.md#L270)
3. **Terminal 表注与本实验预算不同。** L271写 Harbor／Terminus-2、3h、32CPU／48GB、temperature1.0／top_p0.95／top_k20、80K输出、256K context、五次平均。我们当前实验预算更短，不能直接预期仍有7.8个百分点差距。[固定表注](https://huggingface.co/Qwen/Qwen3.6-27B/blob/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/README.md#L271)
4. **模式不能默认一致。** 两卡都说明 Qwen3.6 默认启用 thinking，也提供非思考开关；本次没有找到上述比较表按 non-thinking 单独报告的27B／35B结果，不能擅自认定表中每项采用了 enable_thinking=false，也不能将默认模式说明当作每项实际请求的日志。[27B 模式说明 L642](https://huggingface.co/Qwen/Qwen3.6-27B/blob/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/README.md#L642)
5. **源教师的精确服务未完整披露。** Open-SWE [固定分布表](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)将 v1.1 mini/Qwen3.6-27B 标为 Non-Thinking；本项目全95291行 `metadata.teacher_model` 也全部记录 name=Qwen3.6-27B、enable_thinking=false、reasoning_effort=null。但名称不提供教师服务的完整权重 revision、原始请求、输出额度和服务栈，因此无法声称该教师采集与公开模型卡的评测配置完全一致。具体保存字段证据见[thinking 数据调查](qwen_thinking_data_investigation.md)。

## 对本项目的含义

使用它的成功修复轨迹有合理依据：公开同表显示27B的修复能力更强，来源也提供执行结果标签。但**教师更强不等于所有教师答案正确，也不保证 SFT 后我们的模型提升**；最终仍需按成功／结构／独立性／来源规则选数据，再由独立 dev 和冻结正式协议检验。不能用教师公开榜分替代数据质量检查，或为增强说服力把非思考采集说成思考采集。

这里不建议因此更换题定 base，也未触发换模型、补跑或训练。准确表述是：**27B在官方报告的相关基准上领先；当前两者非思考同预算下谁强、领先多少，尚无本项目实证。**

## 来源指纹

- Qwen3.6-27B README：revision `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`，本轮读取 UTF-8 内容 SHA256 `bb936d6da51014f1edc9aa4cf9abf28d98695b7616ad56adfeeebfa752051d3d`。
- Qwen3.6-35B-A3B README：项目固定 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，本轮读取内容 SHA256 `c4ddaa065649ff6352648f64747a16eda31726f3e34add94ce04abb461c77b75`；表中73.4／49.5／51.5／21.4与27B卡的对应列一致。
- NVIDIA 来源固定 revision `1db674173119d71df45c22007af99e214600711a`；本轮未重新读取轨迹正文或正式 benchmark 题目。

本轮仅新增本报告，未改 claud／Git／主协议。
