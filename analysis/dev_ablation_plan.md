# 最小独立开发集与消融评测建议

更新：2026-10-16。用户已确定先按四项 benchmark 的公开任务类型分布构造独立 val，再决定训练数据配方。本文规模、配额和候选数仍为建议，不是已就绪的验证集；没有生成样本、执行任务或调用 API。

## 当前选集与清洗决定

实际分类计数与本轮选集路线见 [独立val分层](validation_selection.md)。下文70题配额和3小时估算是旧讨论起点；TB16类别、ASI11域已核到，终端10／科研10无法全覆盖，数量及执行预算须随新候选清单重算，当前未冻结新规模。

- 先建立共同分类框架，再从独立任务池挑选 task-dev（下文也称 val）。只用正式 benchmark 的公开语言／学科／任务类别、模态和预算层等元数据作覆盖依据；不根据正式 Base 的逐题成败、回答、测试反馈或参考解挑数据。有限 val 不能精确复制大测试集的所有交叉分布，先覆盖主要类别，比例与遗漏明确披露。
- train 与 val 共享能力分类，而非共享题目或模板族。先跨任务包与旧轨迹联合分组、排除正式集同源，再留出 val 及其全部同源记录，最后从余下合格池选 train。需要调整训练配比时，用 Base 在独立 val 上的聚合错误类别；不把 val 答案、对应轨迹或换数字变体加入 train。
- 允许用独立 val 进行有次数上限的训练配方／模型选择；记录尝试并冻结一版配方，避免围绕小 val 反复追分。正式四项 Base 的分数用于报告与最终对比，不用于选训练样本或配比。val-loss 是单独的 teacher-forced 诊断集合，不能替代真实执行 task-dev。
- 用户决定清除训练消息中 assistant 的 `reasoning_content` 与明确的教师 `<think>…</think>` 推理。保留现有 harness 要求的 Terminus `analysis/plan/commands/task_complete`、有效工具调用／反馈及正常可见答案正文；不递归删除命令／代码／工具返回中的同名文本。不清楚边界的标签、清后动作缺失或工具链损坏的样本先隔离，不猜补；空正文但有有效 tool_calls 的消息保留。
- 清理后重新渲染并计算 assistant loss mask；system/user/tool 不作目标，新增 assistant 正文与真实动作依既定 SFT 方式监督；完全无目标的样本排除。非思考模板产生的空 think 控制标记不含教师推理，不擅改固定模型模板。清洗决定已确定，尚未批量生成训练／val-loss 文件。
- LoRA rank／alpha 等参数暂缓，本文不据候选数值启动训练。训练序列长度、长轨迹策略和具体数据配额也仍待选择，不由推理 64K／8K 自动决定。

## 结论

消融不需要每个候选都跑四项官方全量。建议训练前固定两类小型独立开发数据：val-loss用于训练监控及至多两个预定checkpoint的选择；task-dev用于真实生成、工具行为与AVG/TIES/混训消融选择。最后只把预定参评对象送四项正式集。正式Base即使提前运行，其分数也不进入训练/合版选择。

这两类数据与train按来源任务家族隔离；task-dev不再另拆一套checkpoint执行集。两类开发数据可以同属一个开发manifest，但保留不同用途/任务组，两者均不回流训练。task-dev是选择集，不能把它当无偏测试或将其分数冒充四项benchmark成绩。

## 两类开发数据

| 数据 | 建议大小 | 计算方式与用途 | 不作何种结论 |
| --- | --- | --- | --- |
| val-loss | 总processed-token上限约100K；修复、终端、科研、学术各不超过25K | 固定完整消息/交互窗口；teacher-forced前向，只统计新增assistant监督token的NLL；主要看过拟合、数值异常，最多在预定50%/100%两个训练点比较 | loss不是任务完成率；不同源的绝对loss不直接横比；不能凭loss断言HLE/ASI提升 |
| task-dev | 修复10、终端10、科研10、学术QA40，共70任务；同一固定seed，一次生成起点 | 工具题真实执行且有独立验证器；QA用可核金标准；用于固定候选的小范围筛选及格式/执行回归检查 | 10个工具题每题就是10个百分点，小差异没有可靠统计精度；不能声称验证了正式benchmark总体提升 |
| 正式test | 题目冻结的四项完整指定split/任务清单 | Base及合版四项，专家各自目标；保留原定次数和预算 | 不用于挑checkpoint、训练配方、提示词或合版权重 |

100K是processed-token总上限，不是监督token；分段重复历史也计入。已检查的Open-SWE窗口长约19K–40K，Terminal约21K–30K，不能按“每域128条”直接堆一个比训练还大的val，也不能机械截断JSON。选择按完整工具回合构造、保留必要状态且符合已定训练长度的窗口；无法保留依赖的样本不进入这次val。每源若监督token太少，只作诊断并披露。

checkpoint以末步为默认；若保留中/末两个预定点，依预先约定的同域val-loss及格式完整性检查选，最多两个点，不反复跑task-dev挑步数。三个专家各看本域，交互执行专家分终端和科研两桶；混训看四桶等权及分项，不能总loss淹没科研桶。val-loss只能诊断，默认不拿它给AVG/TIES排序。

## 现有来源能提供什么，缺什么

| 来源 | 可用于留出开发数据的字段/证据 | 当前缺口与处理 |
| --- | --- | --- |
| Open-SWE mini/Qwen3.6 | 有repo、instance_id、trajectory_id、resolved；95,291行实际只有39,540个不同(repo,instance_id) | 同题重复教师rollout必须一起分组。要做task-dev还需恢复基准代码commit、依赖/镜像、agent可见问题与独立测试；只有轨迹或resolved标签不能执行新模型。若环境不可恢复，则只能进入val-loss；另找独立可执行任务或自造小仓库故障 |
| Nemotron-Terminal skill-based | 有task、episode、run_id、trial_name，含Terminus-2动作格式 | 无统一success/result；task字段能否恢复完整任务/模板、环境和验证器尚未通过。不能把assistant写了task_complete或教师轨迹当成功判据。无法复现时只做val-loss，工具dev使用独立原创任务与验证器 |
| OpenR1 default | source、uuid、problem/answer及验证字段可用于任务归组与QA金标准筛选 | messages/generations与验证字段的对应必须核实；同题多解统一归组。仅覆盖数学，不能冒充完整HLE多学科dev；正式四项及其衍生题源照常排除 |
| OpenScienceReasoning-2 | 实际只有input/output/expected_answer，可构造行号/hash索引 | 没有原题source/ID或正确性字段；hash去重不证明来源独立。未恢复原题关联/审题前不作为有金标准的多学科task-dev，不把expected_answer自动当可靠真值 |
| D3-Gym Qwen3-32B | 实际只有instruction/input/output，共2,153行 | 没有task_id、来源仓库映射、逐题success或环境关联，不能直接声称为可运行科研dev；只有恢复独立任务与验证器后才使用，否则只保留候选资格 |

一手来源：[Open-SWE固定卡](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[Terminal固定卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)、[OpenR1固定卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)、[OpenScience固定卡](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md)、[D3固定卡](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/blob/b21b5006956d7d246cf3e35277b13323780a45b2/README.md)。本地实际结构/重复计数见readiness_data.md，不把数据卡声明代替本地成功复验。

## task-dev的最小构成和可核指标

- 修复10题：优先独立训练任务的完整环境与测试，覆盖Python/Go/JS-TS；备选原创小仓库的受控故障。修复前指定测试必须失败，修复后目标与回归测试通过；测试只供评分进程访问。模型不能读取gold patch。主指标为10题中目标+回归均通过的比例，另记工具解析失败、超时和用量。
- 终端10题：原创文件变换、日志/SQL查询、依赖/权限/进程问题等任务，采用固定Terminus-2协议；使用生成的输入和保留在评分侧的输出/属性检查，环境重置。主指标为独立检查通过比例，不用LLM自评或task_complete充当成功。
- 科研10题：原创小型回归/统计检验、数值积分/微分方程、数据拟合、结果表与图表工件等，可用固定随机数据和参考数值容差评分。采用与ASI候选相同agent/文件交付协议，不拷贝ASI任务或评分材料。主指标预先写明为必要文件存在且数值/统计/工件检查通过比例；另报各子检查。不能叫ASI官方score。
- 学术QA40题：建议12数学、8物理、8化学、8生物/其他、4独立图表题；比例仅作小范围覆盖。数学优先可追溯OpenR1留出家族；其余要使用可追溯的独立来源或原创可核答案题，不因数量不足直接拿OpenScience任意40行。图表可自行生成已知数值关系图并独立验答案。主指标按规范化精确答案/数值容差判分，无法机械判分者先人工核金标准，再固定rubric及判分器；图文分项单列。简单原创题只检查能力保留，不能代表HLE难度。

可以复用benchmark的agent接口和容器模板，但必须使用独立任务内容、输入与测试。SWE使用同类bash/command及结束动作；终端用Terminus-2；科研采用锁定的ASI允许adapter。复用harness不等于用正式任务作dev。[固定SWE工具配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[ASI agent契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/agent_interface.py)、[ASI OpenCode适配器](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/opencode_cli.py)。

## 切分原则

1. 在token窗口、改写、多个teacher候选和抽样之前先固定任务组；train、val-loss、task-dev互斥。跨来源拷贝也合为一组。
2. 修复按canonical repo/PR/instance及其重复rollout分组，优先让dev仓库整体不进train；若只做到仓库内不同instance，明确这是seen-repo任务泛化而非跨仓库泛化。排除SWE Pro全部评测仓库及fork/改名关联的既定保守规则不变。
3. 终端按原始任务与生成模板族归组，不按run_id或episode随机分行；科研按论文/代码库/任务或生成recipe家族；QA按原问题/source/uuid及语义近重复归组。改数字后的模板变体不能一边train一边dev。
4. 缺可靠ID不等于可自由随机分行。保留固定revision/原始文件/行号/hash只能给可重现索引，不能证明语义或原题来源独立；未解决的候选不进入可对外声称独立的task-dev。
5. 不从SWE Pro/HLE/ASI/TB正式集随机抽一部分来反复挑模型，再把全量成绩称未见测试。不读取其答案或参考产物用于构造dev；也不把正式题改写、换数字后当原创题。[HLE官方去污染要求](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/README.md)

## 消融范围与总预算

为了保留现有3小时dev目标，建议只比较：Base、同数据混训、AVG、TIES四个全域对象；仓库专家只跑10修复，交互专家只跑10终端+10科研，学术专家只跑40QA。这里比较三专家的目标域专长、同数据混训与两个合版，暂不增加不同专家数、多个rank/LR、不同数据比例、LoRA target等额外训练分支。

工具dev建议每题5分钟、最多4 CPU、预先固定内存/上下文/步数/总生成token上限（如20轮、8K输出token）；QA每题单次生成上限约2K输出token，均按实际冻结thinking设置。这个短预算仅用于筛选，不替代正式TB的题定资源/五次或其他正式协议。所有参比较模型使用同一预算、环境、提示与种子；超时/失败计入分母，基础设施故障单列并依预定规则处理。

上述完整矩阵共150个工具trial，5分钟封顶累计12.5 agent-hours；若实际能维持8路有效并发，理想约1.56小时，不含建环境、加载/切换权重、验证与排队。QA共200次生成，2K上限累计0.4M输出tokens；这部分取决于真实模型吞吐。3小时只是需要预检的条件预算，不是完成承诺，不能把CPU并发视为等同推理吞吐。

候选按四个域的成功/准确率等权宏平均作预定主参考，同时列分域结果和相对Base退化。10题域的噪声很大，若AVG/TIES仅差一题左右，应视为近似持平并按预定简单规则（如优先AVG）选择，不能再围着dev追加多组权重扫参。科研和图文明显退化须单列，不让宏平均隐藏。所有消融结论只覆盖这套小dev；最终四项全量才说明对指定benchmark的表现。

## 下一步仅准备

先核可复用训练任务环境是否能恢复；恢复不了则准备少量原创可判分任务，而不是重造四个大benchmark。冻结manifest、金标准/验证器、配额与候选列表，再开始训练。当前没有声称这70题已经完成，更没有把现有轨迹标为可执行dev。

补充执行边界：task-dev rollout只向模型提供初始任务和允许工具，教师后续动作/观察、gold patch、标准答案及隐藏验证器不进入policy输入。教师完整messages只用于隔离的teacher-forced val-loss。

工具题的8K应理解为拟定累计生成预算，不可把每次API max_tokens=8K误当每任务总量；各adapter是否支持轮数/总token硬限额必须实际核查并记录usage，未落实前不得宣称该限额已经执行。5分钟墙钟上限同样不自动包含环境构建与判分。
