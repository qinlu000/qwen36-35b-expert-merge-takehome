# 专家划分的证据与本题建议

核验日期：2026-10-15。状态：方案研究，未启动训练或评测。用户已经选择 ms-swift + PEFT/BF16 LoRA；本文件不将数据配方、专家划分、超参数或实验执行视为已经批准。只读少量一手论文、作者仓库及 benchmark 说明，未下载训练数据/权重、调用模型 API、读取测试答案、安装环境或提交 Git。

参考已有 `references_agent_recipes.md`、`references_merging.md` 和 `dressage_reuse_plan.md`；本文件只重新审查专家分工，不修改这些文件。下面明确区分来源事实和本项目推断，不预设合版优于混训。

## 1. 主建议：按输出与交互方式分三专家

**建议采用 E-code（仓库修复）+ E-exec（终端与科研执行）+ E-reason（广域学术推理）。** 相比旧稿“修复/终端/科学 HLE+ASI”，把 ASI 移入执行专家，把 HLE 独立为推理专家。仍是三个真实独立训练的 LoRA 加一个同数据混训对照，不新增第四专家或 RL 阶段。

| 对象 | 训练能力和数据形态 | 必须保留的独立 dev | 预先指定目标全评 |
| --- | --- | --- | --- |
| E-code | 仓库问题定位、代码编辑、测试反馈、最终补丁；真实修复 messages/tools 轨迹 | 修复任务；工具格式与必要能力保留 | SWE Pro V2 HARD-51 全量，并按正式协议 replay |
| E-exec | 通用终端操作、环境排错、文件与数据处理；另含科研计算、方法实现、结果验证与产物生成 | TB 类终端执行和 ASI 类科研工作流分开，不用一项替代另一项 | TB89 全量×5；ASI60×B1–B4 全量 |
| E-reason | 数学、自然科学、人文等广域学术知识与推理；选择题/简答及可用的图文问答 | HLE 类广域学术问答；若正式含图，dev 也保留图文能力检查 | HLE2500 全量，模态与工具协议按冻结配置 |
| Mixed | 上述所有训练样本及相同出现次数混合；与专家累计 processed token 匹配 | 四个 benchmark 对应的独立 dev | 若仅做 dev，结论限定于 dev；正式四项全评为另计预算的扩展 |

这里的领域专家是三份从同一 base/revision 独立训练的 adapter，不是修改底座内部 256 个 routed MoE experts 的分工，也不引入推理时路由。最终仍导出单份合版权重。

**这是一项待检验的任务分解假设。** 它的优点是解释清楚、数据接口较一致；并没有文献直接验证这个三分法在 Qwen3.6-35B-A3B 的本题四项评测上最优。

## 2. 一手实证究竟支持哪些划分

### Occamy：两个互补 agent 分支，不是“推理/agent”划分

一手来源：[作者仓库固定版本 f46297e，2026-09-21](https://github.com/Accio-Lab/occamy/tree/f46297e161587bf5d856ca1c8d5ca2db56b773b7)，本次读取其模型说明和训练配方。

**来源事实：** Occamy 从同一 Qwen3.6-35B-A3B 出发，Marathon 走 SFT→HDPO，学习持续执行和准确性约束下的效率；Sprint 走 SFT，保留更广泛的 agent 能力。二者均匀参数合版，再做 SAO。作者报告全参数训练、131K SFT 长度，两个专家去重后的 SFT union 为约 403M token，覆盖 general agentic、long-horizon、terminal/software engineering、tool-call grounding；视觉 encoder/projector 在 SFT 冻结。

**本题推断与限制：** 可借鉴“分支专长由能力瓶颈决定，再合成单模型”，不能将 Marathon 直接改称 HLE 推理专家、Sprint 改称 SWE/TB 专家。二者原本都是 agent 方向，并非一 benchmark 一专家。不能仅据名称断定两支所有训练样本的长短分配，也不能用包含 HDPO/SAO 的最终收益证明本题纯 LoRA SFT 合版有效。其数据与计算规模不可照搬。

### T-pro2.1：三个 RL 专家，同时提供共享 SFT 的反证

一手来源：[论文 v1，§4、§5 Table 3/5/8，附录 F/G](https://arxiv.org/html/2609.01572v1)，[作者模型卡](https://huggingface.co/t-tech/T-pro-it-2.1)。

**来源事实：** 作者从 Qwen3-32B 做共享 SFT，再按 general、instruction-following、function-calling 三个目标训练 GRPO 专家，两阶段 SLERP 合版。划分依据来自生产失败类型及不同 reward，而非 benchmark 名称。Table 3 的 shared SFT 接近各 domain SFT；作者因此不采用分域 SFT 再合版，随后才用 RL 分支处理不同 reward 的干扰。文中验证集用于合版选择。

**本题推断与限制：** 这是保留混训对照的直接理由。它支持“用可观察的错误机制定义专家”，不支持“多份 SFT 一定好于一份混训”。本题没有其 RL reward 冲突机制，也不复刻其资源规模；共享 SFT 若更好，应如实报告。

### T-Search：同一目标底座的真实分支训练与合版

一手来源：[论文 v1，§5 与附录 B](https://arxiv.org/html/2610.06782v1)，[作者 harness](https://github.com/turbo-llm/t-search-harness)。

**来源事实：** Qwen3.6-35B-A3B 分别训练英语、俄语检索分支，SFT 分支经 DARE 合并；共同的 merged SFT 再初始化两支 GSPO，最后经 SLERP 合并。每种语言约 8K SFT 问题；教师轨迹切为带起始状态的独立回合。该模型输出证据排名，回答生成交给下游模型。

**本题推断与限制：** 证明“输入分布/交互机制不同”可以成为分支依据，也说明专家无需与 benchmark 数量一致。但这是双语检索而非仓库修复/科研执行/学术问答的比较；含 RL，文中总训练约 3K GPU-hours，不能外推本题四卡时间或提升。

### KnOTS：确有独立 LoRA 训练与合版，任务边界和本题仍不同

一手来源：[论文 v1，§3–5、附录 C](https://arxiv.org/html/2410.19735v1)，[作者仓库 baa35e8](https://github.com/gstoica27/KnOTS/tree/baa35e85768b8841820d35edc3e41b25304248c5)。

**来源事实：** 作者从共同初始化训练不同任务 LoRA，再进行参数合版。语言例子是 Llama-3-8B 的六个 NLI 分类任务、rank 16 attention LoRA；论文分析普通合版在 LoRA 上的对齐困难。作者有真实训练脚本及 held-out validation 选择。语言 per-task 评测会使用对应任务 classification head；另设 vision joint-evaluation 检查统一模型能力。

**本题推断与限制：** 可作为“真实训练 LoRA 专家后合版”的依据，但不能把分类任务的结果当成统一 agent 生成模型的证明。它也不提供选择 2/3/4 专家的普遍定律。本轮不因此增加 KnOTS 方法，仍保持 dense AVG/TIES。

## 3. SWE/TB：有共享工具技能，也有数据来源差异

**来源事实：** SWE Pro V2 要求在指定仓库解决问题、保存补丁并用全新环境 replay 验证，见[官方 V2 locked protocol](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)。两者的本题完整协议沿用已有 `benchmark_sources.md`、`terminal_hle_feasibility.md`，本研究不变更任务清单或运行预算。

另一个与数据选择有关的实证是 [OT-Agent v1，§3.1–3.2](https://arxiv.org/html/2606.24855v1)：作者报告 SWE-Smith 等 coding 来源更偏向提升 SWE-Bench，StackExchange SuperUser 等基础设施问题更偏向提升 TerminalBench；Top-4/Top-8 混合相较单一 Top-1 来源更均衡，进一步加源不保证变好。该文是数据混合证据，不是参数合版胜过混训的证据，也不是本题 HARD-51 的直接实验结果。

**本题推断：** shell、文件读写、编辑、错误反馈与多轮状态有共享部分；仓库修复的稳定产物是补丁与测试通过，而 TB 类任务还涉及环境、系统和工具操作。因而：

- 不能把静态函数题或刷题代码全部称为修复/终端轨迹；它们缺少交互与状态。
- 可以在两个专家中保留少量共同工具格式/纠错样本，但每次出现都计入专家累计 token，并在混训对照保留相同次数。
- 3 专家保留 E-code/E-exec 的边界，便于观察修复与一般执行是否形成可合的互补更新；2 专家将它们混合也有合理性，需数据与独立 dev 决定，不预设拆开获胜。

## 4. HLE/ASI：主题有交集，行为和产物差别更大

**来源事实：** [HLE 官方说明](https://github.com/centerforaisafety/hle)定义的是多模态、广域、closed-ended 学术 benchmark，共 2,500 道选择题/短答题，含数学、人文与自然科学。它不是纯数学或纯自然科学集合。

[ASI 官方说明，固定 cf07cb8](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md)定义 60 个项目、11 个学科、B1–B4 四种指导条件，要求选择/实现方法、执行工作流并产生可验证科研产物。B1 提供完整方法与步骤，B3 只给目标/数据/约束/输出，B4 加入干扰；四层不是四个独立科学领域。

**本题推断：** 共同科学知识不代表训练监督等价。HLE 风格的答案推理不能单独训练科研环境操作；普通终端成功轨迹也不能自动覆盖科学方法选择、数值检查和研究产物质量。

- HLE 管道：广域学术问答，题目/推理/答案与必要图像，保持原视觉能力；不能只用数学题宣称覆盖 HLE。
- ASI 管道：非测试项目的研究目标、数据、工具调用、执行反馈、方法/结果检查、最终文件与解释；不能用 ASI 正式题目、参考答案或公开参考产物训练。
- 在推荐分工中，ASI 进入 E-exec，但仍单独采样、单独 dev、单独报告；通用 shell 数据不能填补缺失的科研工作流数据。
- 即便选择旧分工把 HLE+ASI 留在同一专家，也必须维持两个内容管道和独立 dev；“科学专家”这个名称不能替代数据覆盖证据。

## 5. 两种三分法与 2/4 专家比较

| 划分 | 训练对象（含混训） | 优点 | 局限与判断 |
| --- | ---: | --- | --- |
| 2：推理 / agent | 3 次 | 最少启动、保存和检查点管理；agent 混合可利用 SWE/TB/ASI 的执行共性 | agent 桶同时承载修复、终端与科研执行；数据形态跨度大，局部退化不易归因。可作来源或启动开销不足时的备选，但不是 Occamy 两分法的直接复现 |
| 3A 旧稿：修复 / 终端 / 科学(HLE+ASI) | 4 次 | 名称直观，科学内容可共用学科知识 | HLE 闭合答案与 ASI 长程执行的监督不同；主题边界强于行为边界。可以实验，但不再作为主建议 |
| 3B 推荐：修复 / 执行(TB+ASI) / 学术推理(HLE) | 4 次 | 三份 LoRA、接口差异清楚；HLE 不挤占执行轨迹，ASI 与 TB 共用执行/状态/产物技能 | E-exec 仍有两个分布，须防止短终端数据压过科研轨迹；没有直接文献证明此分法最佳 |
| 4：一 benchmark 一专家 | 5 次 | 各自数据/监督最纯，目标评测归属简单 | benchmark 名称不是能力分解；固定总 token 时每支可能更欠训练，多一个初始化/保存与合版干扰方向。只在四桶数据都成熟且三分法 dev 明确暴露冲突时才值得后续研究，本轮不默认采用 |

推荐不是“专家越少越省一切”。如果每个 benchmark 恰好归属一个专家，则 2、3、4 专家的目标项全评总量基本相同；主要变化是模型加载顺序、启动/保存管理及每支数据规模。固定总 token 时，训练计算也不会因从 4 支改成 3 支就自动按 3/4 缩减。TB 五次的 CPU/沙箱瓶颈照旧。

## 6. 预算、训练对照和合版选择

沿用原讨论的“专家累计约 3M processed token + 同量混训”作为待实测缩放的起点，不因重分专家扩大总量，也不把该数字当作足够训练或按时完成的承诺。先保留四个内容桶的预算：

- b_code：仓库修复；b_terminal：通用终端；b_science_exec：科研执行；b_reason：广域学术问答。
- 旧分工为 code=b_code、terminal=b_terminal、science=b_science_exec+b_reason。
- 推荐分工为 code=b_code、exec=b_terminal+b_science_exec、reason=b_reason。
- 三专家累计 T=b_code+b_terminal+b_science_exec+b_reason；Mixed 同样 T。具体桶权重仍待来源审计、长度分布和独立 dev 确定，不能把“换归属”变成重复训练同一批数据两遍。

匹配相同数据、出现次数、chat template、工具格式、loss mask、截断/分段规则、processed token 与有效 batch；另记录 supervised token、padding、样本/轨迹数和 GPU 时间。processed token 包括不计算 loss 的工具观测，不能只对齐有标签 token 就称等计算量。

保持相同 base/revision、LoRA rank 与目标布局，分别真实训练三专家和混训。相同 rank 的 Mixed 与合版的有效更新秩仍不同：N 份 rank-r 更新的和秩至多 Nr；因此这个对照不能完全隔离专业化与容量因素，也不能当成严格等 FLOPs 的证明。若后续扩展 rank 匹配对照，需要另计训练预算。

合版仍只做 dense Δ AVG 与 TIES：包含实际 LoRA scaling，不分别平均 A/B；独立 dev 选唯一配方，最终没有 adapter 路由或模型投票。先用两固定候选，只有预算允许才两法各加一个全局 scale，不因新文献扩大方法网格。

## 7. 目标评测归属变化与不可压缩的要求

与旧稿相比，仅把 ASI 的目标全评从旧 E-science 转给 E-exec；HLE 由 E-reason 负责。SWE、TB 归属与四项完整范围不变，三个专家的目标项全评总量不变。Base 和最终合版仍各做全部四项；其他合版候选和 Mixed 可只做独立 dev，但报告相应结论边界。

最低矩阵是：Base 四项全评；E-code 的 SWE 全评；E-exec 的 TB 全量×5 与 ASI60×四层；E-reason 的 HLE2500；最终合版四项全评。不能通过减题、减少 TB 五次或把专家目标项全评替换成 dev 来消化训练预算。

在最终结果可见前冻结专家数据/配方、各任务归属、dev 选择规则、合版权重与正式推理协议。若提前启动某个专家的正式评测以重叠调度，结果不得用于调整其他分支或合版选择。合版可以失败、Mixed 可以获胜；都属于本题应保留的研究结果。

## 8. 当前待确定内容

最先需要落实的是四个内容桶的可用数据、许可、污染隔离和完整轨迹覆盖，尤其科研执行桶；不是再增加专家或更复杂算法。训练范围、rank/学习率/长度、分桶比例、最终 dev 和正式协议仍为讨论项。若数据不足以形成一个真实专长，应缩小结论并讨论重组，而不是靠专家命名宣称覆盖。

本文件只给数据形态与专家分工建议，不授权采集、下载、再生成或训练。没有保证合版提升、没有把同模型文献的结果直接外推本题，也没有变更已选择的 ms-swift 主线。
