# 面向本次多专家训练与合版任务的网上方法调研

日期：2026-10-16（北京时间）。本轮实际联网查阅一手论文、作者仓库、数据卡和官方源码；结合本项目现有方案，分别调研数据、算法、工程和评测。以下是研究建议，未修改训练或评测配置，未运行模型、任务、付费 API 或正式实验。作者报告的结果不代表本项目实测。

详细证据与实现边界分别见：[数据](research_web_data_20261016.md)、[算法](research_web_algorithms_20261016.md)、[工程与评测](research_web_engineering_eval_20261016.md)。本文负责收敛决策，不重复既有来源大全。

## 1. 最值得参考的整体组织方式

| 一手材料 | 已核内容 | 对本项目最有用的部分 | 迁移边界 |
| --- | --- | --- | --- |
| [Occamy](https://github.com/Accio-Lab/occamy#4-training-recipe) | 同为 Qwen3.6-35B-A3B；Marathon/Sprint 两分支，参数均匀合版，再训练 | 证明同底座专精分支→单模型参数合版已有近邻实例；作者还单列 tool-call grounding 数据 | 包含 HDPO/SAO，SFT union 403.3M token；不是本题三专家 LoRA 或四卡复现配方 |
| [T-pro 2.1，§4、Table 3](https://arxiv.org/html/2609.01572v1) | 作者先比较分域与混合 SFT，认为混合 SFT 已接近各域专家；之后才分三路 RL 并合版 | 为“同数据混训”提供必要的反证对照：不能预设分专家 SFT 再合版更优 | Qwen3-32B、俄语生产任务，最终专家是 RL；不预测本题四项成绩 |
| [AgentTuning](https://github.com/THUDM/AgentTuning#agentlm) | 1,866 条筛选交互轨迹，与通用对话混训，并考察 held-out 能力 | 专精收益和通用/工具能力保留应同时检查；可借鉴少量共同基础样例的思路 | 旧 Llama-2 与不同工具环境；只借设计，不直接加入其数据或照搬比例 |

**建议保持现有简化主线：三个同底座 LoRA 专家＋同数据混训对照＋dense AVG/TIES。** 近邻论文说明这个问题值得研究，也说明结果可能是“混训已足够”或“专精形成但合版有损”。本次不因找到新论文增加 RL、路由、更多专家或更多合版搜索。

## 2. 数据：先对齐行为与环境，再选规模

现有候选已经不少，收益更可能来自验收、去重、监督方式和分配，而非继续收集名称。数据是否进入主池，建议依次检查：来源与许可、与正式集独立、对应 harness 的动作/观察/结束语义、sandbox 的构建与初始化、最后才是条数和 token。

| 专家/子池 | 优先参考 | 具体借鉴 | 本项目需要补的证据 |
| --- | --- | --- | --- |
| 仓库修复 | [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces)、[SWE-smith](https://github.com/SWE-bench/SWE-smith) | 用同源 mini 接口轨迹；用独立任务包恢复 repo/commit/依赖与测试，按原任务归组 | mini 版本、cwd、setup、命令状态和退出语义相容；同题多次 rollout 不能分散到 train/dev |
| 终端执行 | [Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus)、[Harbor](https://github.com/harbor-framework/harbor) | 复用 Terminus-2 格式及 Dockerfile＋输入文件的任务构建方式 | teacher 实际预算、任务文件和验证器可恢复；任务声明的默认值不等于采集时的实际配置 |
| 科研执行 | [D3-Gym](https://github.com/OSU-NLP-Group/D3-Gym)、[ASI 官方 adapters](https://github.com/apexin-ai/ASI-Bench/tree/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters) | 若选 direct_llm，D3 的推理＋完整 Python 程序更接近目标接口；用数值/文件产物检查 | 程序与来源任务映射、依赖、许可及评分隔离；这种数据不监督“读 stderr 后多轮修复” |
| 学术推理 | [OpenScienceReasoning-2](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2)、[OpenR1-Math-220k](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k) | 多学科主池＋受控数学补充；保留可核答案和来源分组 | 题源与答案质量；数学正确不等于 HLE 多学科能力，更不证明图文能力保留 |

本轮数据侧有三点比增加数据源更重要：

1. **不要把“只留成功轨迹”当成已证实最优。** Open-SWE 与 Nemotron 的消融都提供包含未成功轨迹仍有效的证据；但数据量和训练 token 存在混杂，不能反推失败轨迹一定更好。优先保留完整成功轨迹内的有效恢复过程；未解决轨迹是否使用按来源决定，不任意剪接缺状态片段，也不监督最终失败程序为正确答案。具体表格与限制见[数据专项](research_web_data_20261016.md)。
2. **完整上下文与局部 loss mask 可以分开。** [SWE-Prime](https://arxiv.org/abs/2608.27449) 提供轨迹/语义段筛选思路。先做简单轨迹级质量筛选；仅在训练器可可靠表达、片段依据可审计时采用局部 mask，保留观察和必要状态。暂不搭建 embedding 聚类＋LLM 评分流水线。mask 不会同比减少前后向的 processed token，不能据此承诺提速。
3. **去重应先归组再切分。** 先以 repo/instance、原任务/模板族、论文/代码库、问题 source/ID 归组；再做规范化 hash 和近重复检查。[DataTrove 官方示例](https://github.com/huggingface/datatrove/blob/main/examples/minhash_deduplication.py) 可参考签名→候选匹配→聚类→过滤及保留删除清单的流程。MinHash 主要找词面近重复，不证明语义无污染；不必为当前小规模数据引入整套分布式平台。

ASI direct_llm 当前只传文本 prompt，没有模型图片附件；程序可在执行侧读图，不等于模型获得视觉输入。接口相近仍需核对任务信息是否完整，不能将此候选写成已覆盖全部模态。D3 还应先恢复源 repo 映射：轨迹卡 MIT 不覆盖上游无许可或另有条款的材料，详见数据专项。

## 3. 算法：低复杂度主线，先保证定义正确

对标准 LoRA，每层真实更新是 `Δ_i = s_i B_i A_i`；AVG 应为 `W_base + Σ_i w_i Δ_i`。分别平均 A、B 会引入交叉项。TIES 的 trim、sign election、disjoint merge 也应明确作用在哪个空间。[PEFT 官方合版说明](https://huggingface.co/docs/peft/developer_guides/model_merging)、[TIES 作者实现](https://github.com/prateeky2806/ties-merging)。

| 方法 | 本次定位 | 必须留意 |
| --- | --- | --- |
| dense AVG | 首选简单基线 | 固定权重归一化、LoRA scaling 和输出 dtype；基础权重只加一次 |
| dense TIES | 首选第二方法 | 固定 density、符号规则与全局 scale；只在独立 dev 选候选 |
| PEFT cat | AVG 的精确低秩表示备选 | 标准 LoRA 可用秩相加表示求和；它是表示方式，不是新的合版算法 |
| PEFT linear/ties | 不当作 dense AVG/TIES 的等价替代 | 官方实现处理 A/B 因子，其结果与 dense 更新空间通常不同 |
| ties_svd/KnOTS/DARE/层级搜索 | 扩展阅读 | SVD 重压缩有误差，额外搜索有预算；本轮不增必做分支 |

TIES 还要预先明确逐张量或全向量 trim：每层各保留20%与全模型保留20%不同。按 PEFT 数值核心实现时，AVG 的等权求和用 `[1/3,1/3,1/3]`，通常的 TIES disjoint mean 用 `[1,1,1]` 再乘全局 scale；两者都传1/3会额外缩小 TIES。这里是实现建议，尚未改配置，详见[固定源码核验](research_web_algorithms_20261016.md)。

还需公开两个解释边界：

- 三份 rank=r 的 AVG 可以有最高约 3r 的有效秩；逐元素 TIES 甚至可能突破这个界。同 rank 混训与合版的对照存在容量差异，不能把全部收益归为“专家划分有效”。预算内先披露，额外 rank 匹配对照留后续。[算法专项](research_web_algorithms_20261016.md)
- Qwen3.6 是混合注意力、MoE、多模态架构，不能照抄旧 Qwen 的 q/v 列表或盲用 `all-linear`。三专家和混训应使用同一完整模块白名单；沿用当前候选方案中冻结 routed experts/router/视觉的范围，执行前固定。官方 PEFT 多 adapter 合并对 `target_parameters` 另有限制。[PEFT LoRA 文档](https://huggingface.co/docs/peft/developer_guides/lora)

合版诊断可先记录各层更新范数、专家更新的余弦相似度/符号冲突、保留比例；这些只帮助解释退化，不作为保证增益的理论。任务完成率与工具行为仍以独立 dev 为准。

## 4. 工程：复用主干，验收真实接口，保住恢复证据

**推荐继续复用 mini / Terminus-2 / ASI 官方 adapter / HLE 官方 client。** 新增部分限于端点、配置、任务映射和当前无 sudo 容器后端。现有[公开 harness 核验](harness_reuse.md)已经给出代码位置；本轮没有找到必须重写 agent 的理由。

这次新增的工程核验价值在于几个容易漏掉的具体行为：

- **vLLM 的“支持 LoRA”还不够。** 当前[官方 LoRA 服务文档](https://docs.vllm.ai/en/stable/features/lora/)已有 Qwen3.6 的 MoE 示例，并明确区分 2D/3D LoRA 布局；布局声明错误可能产生错误输出。必须与实际 adapter 张量、目标层及安装版本对齐，不能由最新文档反推当前环境已兼容。
- **模型能输出工具文本，还需验证 parser 和 harness 真能执行。** 检查原始请求、模板渲染、tool-call JSON/终端动作解析、工具返回和结束动作；同时固定 thinking/preserve_thinking、上下文、单次输出上限、累计 token 限制（若有），以及墙钟和步数预算。不要只看 HTTP 200 或训练 loss。
- **恢复前先留原始 attempt。** 已锁 Harbor 的 `job resume` 在特定条件下会删除旧 trial 目录，缺少 `result.json` 的目录也可能被清理。它通常补跑 trial，不等于恢复中断的 Terminus-2 会话。保存旧失败/用量，再按预定条件重试；详细源码见[工程专项](research_web_engineering_eval_20261016.md)。
- **并发由两个瓶颈共同决定。** GPU 负责推理，CPU/RAM/镜像/网络负责 sandbox；更多 trial 并发不自动带来更高有效吞吐。按每类任务的实际运行时间、token、排队和环境失败率估剩余量，保留长任务尾部时间。未运行前不承诺某个并发数。

## 5. 评测：固定模型之外，还要固定系统和统计单位

四项题定完整评测范围不变。独立 dev 负责候选选择，正式集负责报告。参考 [AI Agents That Matter](https://arxiv.org/abs/2407.01502) 对成本、holdout 和可重复性的分析，报告不能只剩一个平均分。

建议在既有主分数之外同步保留：

| 角度 | 建议输出 | 解决什么问题 |
| --- | --- | --- |
| 能力与退化 | 四项主分数、相对 Base 变化、新解决/新失败任务、专家目标域变化 | 宏平均可能隐藏某项明显退化 |
| 接口与运行 | 格式解析失败、工具执行失败、超时、环境/评分故障、重复动作 | 区分知识/策略问题和系统问题；不把接口错归为模型完全不会 |
| 预算效率 | input/output token、完成耗时、GPU/CPU 时间、judge 调用/费用 | 合版收益可能伴随更长输出或更多尝试；固定上限不等于实际成本相同 |
| 不确定性 | 配对分差区间、TB 五次均值/标准差、任务级结果 | 小分差和少量题目的波动不能解释为稳定提升 |

统计建议是本项目设计，而非声称某篇论文已替本题证明：SWE/HLE 按同题配对；TB 以 89 个原任务为簇保留各自五次结果；ASI 以 60 个项目为簇保留 B1–B4。不能把同任务的重复或 B 层当成完全独立的新题；四项宏平均的 bootstrap 应按各项自己的采样单位计算，再等权聚合。正式结果中的失败案例可供分析，不回流本次选模。

**替换 judge 需要单独证据。** 替代模型能看图、能返回 JSON，只证明接口可用。应在独立、人工可核的样例上检查答案抽取、数值容差、错答案误接收、缺产物、图文评分一致性，并披露替代关系。若未做原 judge 对照，不能宣称与官方评分等价。严格保持评分材料只进 grader，不进被测 policy。

在线服务的 seed 也不保证 token 级复现。[vLLM 可重复性说明](https://docs.vllm.ai/en/stable/usage/reproducibility/)要求考虑调度、batch invariance、硬件与版本；其通用功能说明不自动证明当前 Qwen 架构已验证。保留运行配置与重复波动，比承诺“设了 seed 就完全一致”更准确。

## 6. 面向当前任务的优先顺序

1. **先收敛数据—harness 组合。** SWE mini、TB Terminus-2 维持主线；ASI 比较 direct_llm＋完整科研程序与 OpenCode＋多轮轨迹的接口/数据成熟度，在正式 Base 前冻结。先用与正式任务独立的小样例验收，不强行为保留现有数据选不相容 agent。
2. **冻结可追溯小数据与预算。** 先切任务家族，再统计独立任务、processed token、监督 token 和完整回合长度；保留排除原因。既有三专家、同数据混训和6M累计预算仍是讨论起点，来源论文不替代实际可用量与吞吐。
3. **完成准确模型的训练—保存—加载—工具执行闭环。** 固定模块白名单、模板和依赖；确认完整合版产物可加载。模型加载成功与正式四项 ready 分别记账。
4. **只比较预定 AVG/TIES 候选。** 少量独立 dev 上近似持平时按预定简单规则选，停止追加系数搜索；同时报告各域损失和秩/容量限制。
5. **全量评测优先保障可完成、可恢复、可追溯。** 不因资源压力静默缩题、减 TB 次数或改预算；把已存在的基础设施风险和待完成项如实列出。

本轮建议最应落实的是：**对齐真实行为接口、控制数据重复和监督质量、正确实现权重更新空间、保留失败与成本证据。** 新数据源和复杂合版方法均不应先于这四件事。
