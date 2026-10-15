# 科学推理与科研执行数据：来源核验及专家分工建议

核验日期：2026-10-15（Asia/Shanghai）。本次仅查作者论文、代码、数据卡、文件索引与 schema 元数据；未下载 Parquet、任务包或模型权重，未读取本题 HLE／ASI 参考答案、SWE 参考补丁或隐藏测试，未调用模型 API、训练或评测。本文是候选与方案，尚未执行逐行许可、去污染、质量检查或 token 统计。

## 建议先按行为分专家

**建议用三份 LoRA 分别学习“仓库修复、交互执行、广域推理”，不要把 HLE 和 ASI 因为都与科学有关就全塞进一个科学专家。** 三者保持同一底座、target modules、rank 和训练模板，便于后续合版；名称不代表能独占某个 benchmark 的能力。

| 专家 | 主要学习行为 | 主数据方向 | 首要目标评测 |
| --- | --- | --- | --- |
| E_code | 理解仓库、定位、修改、测试与恢复 | 另行核验的 SWE-smith／SWE-Gym 修复轨迹 | SWE Pro V2 HARD-51 |
| E_exec | 操作终端、编程处理数据、科学计算、检查输出工件与自调试 | Terminal-Corpus skill-based；有意覆盖 scientific_computing／data_science | TB2.0 + ASI |
| E_reason | 跨学科长推理、数学检验、明确最终答案 | OpenScienceReasoning-2 为主，OpenR1 数学为补充 | HLE |

这是对原“E_science 同时承担 HLE+ASI”的修订建议，尚待讨论。ASI 的科研工作流依赖工具执行，HLE 是广域专家级问答；两者有共享推理能力，但纯 CoT 不等于科研 agent 轨迹。将 ASI 主要归入 E_exec 不增加训练份数，也不需要宣称三份专家严格互不重叠。项目内已有 ASI 任务运行与工具条件核验，见 `analysis/benchmark_sources.md`。

## 五项候选的优先级

| 候选 | 实际训练内容 | 许可声明 | 建议 |
| --- | --- | --- | --- |
| NVIDIA OpenScienceReasoning-2 | 广域合成长推理 QA；含 STEM、法律、经济、人文 | CC BY 4.0 | E_reason 首选；必须补来源家族／主题标签及去污染审计 |
| OpenThoughts3-1.2M 的 science 部分 | QwQ-32B 长推理对话；science 为 100K 条 | Apache 2.0 数据卡；上游另有 CC BY-SA／版权边界 | 备选科学推理补充；不作为“1.2M 个独立科学问题”使用 |
| NVIDIA Terminal-Corpus 的科学与数据子池 | 真实 assistant—环境交互轨迹 | CC BY 4.0 | E_exec 科研执行主候选；可直接按固定文件路径选，非独立 HF config |
| NVIDIA OpenMathReasoning 的 TIR | 带 Python 执行的数学推理文本 | CC BY 4.0；原问题来自 AoPS 等 | 备选工具推理补充；不是通用科研工作流，先核工具协议适配 |
| MegaScience／TextbookReasoning | 多学科 QA 与较短分步答案 | CC BY-NC-SA 4.0 | 本次主线排除；保留学科覆盖与数据选择方法参考 |

OpenR1-Math-220k 已在 `analysis/references_data.md` 核验，不另算新来源。仍建议它承担小比例、可符号验证的数学推理，而非将整份科学专家缩成数学专家。本表不表示任何来源已经完成本题全部去污染。

## 1. OpenScienceReasoning-2：广域推理主候选

**已核事实。** 固定 HF revision 为 `174b02c9cdf231f220765b2a1d5ece4550921894`（2025-07-31）。作者声明 CC BY 4.0，记录为带详细推理的多选／开放问答，范围超出自然科学。当前公开 schema 仅 `expected_answer`、`input`、`output`，没有逐条 source URL、question_id、topic、difficulty、正确性标签或 teacher 字段。数据卡称 1.6M QA；viewer/info 明示 `partial=true`，其 307,862 行仅是已转换部分，不能据此反驳数据卡，也不能当全量规模。实际可用行数、唯一题数必须以未来固定版本 manifest 为准。[固定数据卡](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md)、[HF 元数据](https://huggingface.co/api/datasets/nvidia/OpenScienceReasoning-2)、[schema／partial 元数据](https://datasets-server.huggingface.co/info?dataset=nvidia%2FOpenScienceReasoning-2)

**作者构造链。** NeMo-Skills 固定 commit `bcf059af55c20a89f797724598f9908d126153e6` 的 recipe 说明：按难度、主题、子主题用 Qwen 系列造题并扩写，用 DeepSeek-R1-0528 生成解答，最后多数投票。生成 prompt 接收 `{examples}`；本次未查明所有 few-shot 示例来源。多数投票是模型共识信号，不能写成独立事实验证或每段推理都正确。[构造文档](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/docs/releases/openreasoning/dataset.md#science-data)、[造题 prompt](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/recipes/openreasoning/prompts/science_question_generation_prompt.yaml)、[扩写 prompt](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/recipes/openreasoning/prompts/science_question_augmentation_prompt.yaml)

**适用判断。** 相比纯数学，这是 E_reason 更合适的主池。现成 `output` 有长推理，不必把 API 用在重复生成大批同类解答。但它没有 tool-call／tool-result 或科研环境执行轨迹，不应作为 ASI 执行能力已覆盖的证据。卡片提到 HLE 是目标评测不等于把 HLE 放入训练；同样，合成标签也不能证明没有评测记忆或 few-shot 衍生。需排除四项正式题目及其衍生，保留 input hash、固定分片与行号；主题标签若由本项目添加，注明为新增推断，不能伪装成上游原生字段。

## 2. OpenThoughts3：可追溯性有限的备选

**已核事实。** 固定 revision `61bcf9d4eb38b30295efc2021227a63cc5bb34c8`（2025-06-09），Apache 2.0 数据卡，schema 为 `difficulty`、`source`、`domain`、`conversations[{from,value}]`。完整发布是 850K 数学、250K 编程、100K 科学“答案样本”；作者先抽约 75K 问题，再每题生成 16 个 QwQ-32B 答案，因此 1.2M 不是独立题数。仅按科学样本数除以 16 得到约 6.25K 问题是推算，实际应聚合题面 hash 核实。[固定数据卡](https://huggingface.co/datasets/open-thoughts/OpenThoughts3-1.2M/blob/61bcf9d4eb38b30295efc2021227a63cc5bb34c8/README.md)

**方法与边界。** 作者论文表明 science 有物理论坛／化学等候选来源；论文声明上游论坛为 CC BY-SA，一些化学教材保留版权，不能用总卡 Apache 替代逐来源审计。论文采用 75% Indel 相似度及 13-gram 去污染，HLE 是其 512 道文本多选 held-out 评测；这不覆盖本题完整 HLE、多模态、ASI、SWE 或 TB 的独立性。论文未证明增加数据规模可改善 HLE。其最终 recipe 不要求逐答案验证，公开 schema 无 correctness 标志。[作者论文，来源／许可／去污染章节](https://arxiv.org/html/2506.04178v2)

**建议。** 只在 OpenScience 主池质量或覆盖不足时补入可追溯 source 的 science 小池。优先可以保留原问题来源与许可的子集；同题 16 答案必须一起分组切 train/dev，再每题抽 1–2 条，不能将同题不同答案拆到两边。没有题目 URL／ID 的条目需保留固定分片行号及题面 hash，并核验是否能恢复上游映射。此处不是要求上来重新实现上千次数据消融。

## 3. Terminal-Corpus：科研执行的现成主池

**已核事实。** 固定 revision `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`，CC BY 4.0。easy／medium／mixed 是 HF config；其中 schema 是 `conversations` 及 `agent`、`model`、`model_provider`、`date`、`task`、`episode`、`run_id`、`trial_name`、`enable_thinking`。**没有原生 domain/category/resolved/result 字段。** 不应写 `filter(domain == ...)` 或假定可现成 success-only。[固定数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)、[完整 schema 元数据](https://datasets-server.huggingface.co/info?dataset=nvidia%2FNemotron-Terminal-Corpus)

**实际可选路径。** HF 固定文件索引中，easy／medium／mixed 下均有 `scientific_computing/data_filtered.parquet` 与 `data_science/data_filtered.parquet`。未来可以精确指定 `data_files` 选这些分片，并将路径衍生的 `source_domain` 写入 manifest，无需先下载整个 366K Corpus，也不需要臆造 category 字段。这是文件目录的类别，不能据此断言每条任务标签都经过独立验证。[固定 medium 科学计算目录](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/tree/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/synthetic_tasks/skill_based/medium/scientific_computing)、[固定完整文件索引 API](https://huggingface.co/api/datasets/nvidia/Nemotron-Terminal-Corpus/tree/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9?recursive=true&limit=1000)

**验证与可迁移性。** 配套 synthetic task 发布提供 instruction、环境与 pytest，检查输出工件和数值结果；任务包不是 rollout。现成 Corpus 是 assistant 与环境多轮轨迹，其执行工具表达仍需与本项目固定 agent 协议核对。论文去重针对 TB2.0 的 14-gram 声明不等价于四项评测已完全去污染。[独立任务包说明](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/blob/7e53648e183cee7bcb0aed623cc91a121d37fa38/README.md)、[作者论文](https://arxiv.org/html/2602.21193v1)

**建议。** E_exec 的科研部分优先用这些科学计算／数据科学分片，再配一般文件操作、数据处理、依赖／调试。如果需要验证成功标记，先核配套任务和原始 run 记录能否可靠映射；没有映射就不得宣称“全部执行通过”。不把原始失败命令全部删除：完整轨迹中的报错、检查、纠正，是所需学习行为。具体终局失败轨迹的混入比例在独立 dev 上决定，不能用 ASI／TB 正式分数决定。

## 4. OpenMathReasoning TIR：小比例备选

**已核事实。** 固定 revision `d3d08664755704f422af97d43a7ff0ded4bd95df`，CC BY 4.0。作者修正后的口径为 306K 唯一问题，发布约 3.20M CoT、1.72M TIR、0.566M GenSelect；另有无解答的问题集。schema 含 `problem`、`generated_solution`、`expected_answer`、`problem_source`、`problem_type`、`generation_model`、`pass_rate_72b_tir`、`inference_mode` 等。大部分题来自 AoPS，少部分 MATH train；expected_answer 可能来自原答案，也可能是模型多数投票，pass_rate 字段仅部分问题存在。[固定数据卡和 schema](https://huggingface.co/datasets/nvidia/OpenMathReasoning/blob/d3d08664755704f422af97d43a7ff0ded4bd95df/README.md)

**判断。** TIR 可以补“思考→运行 Python→读结果→继续思考”，但属于数学工具推理，不能替代文件／科学数据工作流。解答是 `generated_solution` 字符串，不是本项目原生 OpenAI tool-call 消息；未来必须核执行分隔符、工具输出 mask 和协议转换。作者 pipeline 及执行环境可借鉴，但当前没有验证其模板可无损映射本项目 agent。[作者复现项目](https://github.com/NVIDIA-NeMo/Skills/tree/bcf059af55c20a89f797724598f9908d126153e6/recipes/openmathreasoning)

**建议。** 主线已有 OpenR1 数学与 Terminal 科研轨迹时，可先不加第四个训练来源。只有出现明确数学工具短板才少量加入 TIR，并将同题 CoT/TIR/GenSelect 统一分组，避免跨 expert／dev 重复计算。若原始问题 URL／许可证无法追溯，不能只凭 NVIDIA 卡片总许可宣布上游逐题无条件可公开再分发。

## 5. MegaScience：方法参考，当前主线排除

**已核事实。** MegaScience revision `8df5586005374acba25aecc4f5469ce30fec605c`，元数据 train=1,253,230；TextbookReasoning revision `ca7ecbec76d01bff2e99f3dc17735b02f87d4e96`，train=651,840。两者数据卡均为 CC BY-NC-SA 4.0。前者融合 NaturalReasoning、Nemotron-Science、TextbookReasoning，为前两者生成 DeepSeek-V3 分步解答；后者来自 12K 大学科学教材，提供 question、answer、subject、reference_answer，不能将每条 answer 自动写成详细长 CoT。[MegaScience 固定卡](https://huggingface.co/datasets/MegaScience/MegaScience/blob/8df5586005374acba25aecc4f5469ce30fec605c/README.md)、[TextbookReasoning 固定卡](https://huggingface.co/datasets/MegaScience/TextbookReasoning/blob/ca7ecbec76d01bff2e99f3dc17735b02f87d4e96/README.md)

**建议。** 其按学科做覆盖、从有 reference 的问题出发、对来源池做简单消融值得参考。当前项目需公开专家／合版 adapter 并用于企业笔试，短窗口内不增加非商业／相同方式共享的使用与发布解释负担；这是工程选源判断，不是对训练权重许可证适用性的法律结论，也不是说整个数据必然不能用于研究。先不用此池，无需为它额外请求许可。[作者仓库与许可表](https://github.com/GAIR-NLP/MegaScience)

## 最小落地配方（讨论建议，尚未执行）

1. **主线最多三种数据家族。** SWE 轨迹、Terminal skill-based、OpenScienceReasoning-2；OpenR1 只补少量数学。OpenThoughts／OpenMath TIR 作为替补，不把所有候选混合。避免重复收集同一上游衍生数据。
2. **在原三专家总量约 3M processed token 下调整分配。** 可讨论 E_code 0.9M、E_exec 1.2M、E_reason 0.9M；E_exec 科研相关占其约 1/3–1/2，其余一般终端；E_reason 可先讨论 70% 广域推理、30% 可验证数学。这些是待验证起点，比例不是论文给本题的已验证最优值。mixed control 使用完全相同的样本、出现次数、监督 mask 与累计 token，不能另加科学数据。
3. **长 CoT 与轨迹分开处理。** 普通 CoT 优先选完整且放得进上下文的样本，不将一句长推理硬切成互相缺上下文的“多轮工具轨迹”，也不截掉最终答案。超长样本暂不选时记录长度筛选偏差；多轮工具轨迹可按工具轮分段并只监督新增 assistant 输出，工具观察／题目及重复前缀不计 loss。8K 只是当前工程起点，长度分布尚未测量。
4. **分组 dev。** OpenScience 按规范化题面近重复／合成家族分组，OpenThoughts 按题面聚合全部 16 答案，数学按来源题目，Terminal 按任务 ID 和任务模板家族。若拿不到 source family，就用保守聚类后切分，并明确局限。不同标签或不同输出模板不代表独立题目。
5. **清洗只用允许的信息。** 以四项评测的 ID、来源及允许使用的题面指纹做 exact／near-duplicate 检查；排除题目衍生重写与相同参考来源家族。不得读取答案／参考补丁／隐藏测试用于筛选，不用正式分数给数据挑比例。合成时间较早、数据卡没写 benchmark 名称、作者声称做过 n-gram 去重，都不足以单独证明本项目无污染。
6. **独立验证行为。** E_reason dev 保留广域学科与答案格式分层；E_exec dev 保留数值正确、文件完整、图表／结果工件和恢复能力等独立任务。构造新科研任务可借 ScienceAgentBench 的 recipe，但不直接搬其 benchmark 解答或本题 ASI 任务。冻结 dev 后再训练、选 checkpoint 和合版。

未核实的核心项：实际 Qwen tokenizer 长度与训练吞吐；逐行来源 URL／上游许可；OpenScience few-shot 来源及完整 domain 元数据；跨四项的污染审计；Terminal 终局验证状态可映射性；各工具格式在 Qwen3.6/ms-swift 下的无损适配。这里给出的是可优先审计的现成池，不是已经通过验收的训练集。
