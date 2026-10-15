# 数据来源与专家分工方案（v3，部分已确认）

2026-10-15核验。用户已确认ms-swift训练框架、三专家划分与直观名称；数据来源/配比、训练超参数和评测执行条件仍待锁定；用户现已授权推进数据与工程准备，问题集中记录后讨论，正式训练/全评尚未启动。主要变化是把原“科学专家负责HLE+ASI”改为按任务行为划分：**仓库修复专家负责SWE，交互执行专家负责TB+ASI，学术推理专家负责HLE。** 原始总训练预算暂不扩大。

本轮按四项目标新增来源与取舍见[训练数据清单](benchmark_training_data.md)，其中D3科研程序SFT是新候选，尚未加入下载或通过资格检查。原四源81文件/约25GB已完整下载校验，D3小池也已下载；实际数据格式/token统计、工程验证和未决事项见[问题清单](open_questions.md)。

专项证据：[修复数据](data_swe_sources.md)、[终端数据](data_terminal_sources.md)、[科学数据](data_science_sources.md)、[专家划分参考](expert_partition_research.md)。本稿的比例、抽样和dev方案均为工程/研究判断，不能当作论文已证实的最优配方。

2026-10-16补充：近期教师候选见[新轨迹调查](latest_trajectories_20261016.md)，小规模选样与修正后的量级建议见[训练数据预算](sft_data_budget_20261016.md)。下文6M累计配额保留为旧pilot方案；当前讨论起点为约15M一次性完整序列token、专家与同数据Mixed各一遍约30M累计processed token，窗口重复另计。尚未冻结新配额或切换实际数据源。

## 1. 已确认的三专家，按行为与产物区分

| 专家 | 学习行为与主要产物 | 主要正式目标 | 数据管道 |
| --- | --- | --- | --- |
| 仓库修复专家 | 阅读已有仓库、定位问题、修改多个文件、执行回归、恢复错误；产出仓库补丁 | SWE Pro V2 HARD-51 | 多语言修复assistant/tool完整轨迹 |
| 交互执行专家 | 命令/环境/文件操作，以及科学数值计算、数据分析、结果和工件检查；产出可执行程序/数据/图表 | TB2 + ASI | 通用终端与科研执行两桶，独立配额、标签和dev |
| 学术推理专家 | 无工具条件下跨学科推理、答案表达、证据与一致性检查；产出学术答案 | HLE | 广域科学/人文推理为主、可验证数学为补充 |

同一训练任务默认只归一个专家：已有仓库的修复/回归归仓库修复专家；在环境中完成工作流并交付工件归交互执行专家；直接给学术答案归学术推理专家。科学主题本身不决定专家归属。跨数据源同题、不同教师和不同框架的变体必须统一分组。不同正式benchmark分别使用合规的agent和工具；TB题面指定Terminus2，其他项可在官方允许范围内结合数据兼容性选择，随后在训练前冻结。同一benchmark不得因模型不同更换agent。

旧三分法容易把HLE和ASI的监督形式混在一起，令纯数学冒充科研执行。新划分仍只有三次专家训练；交互执行专家内显式留科研子预算，不能被普通shell任务挤掉。HLE全量含图，而本轮候选推理池主要为文本；冻结视觉只保证保留原视觉权重，不证明图像推理收益。该覆盖缺口应在独立图文dev与最终报告明确披露，不临时接入来历不明的多模态大包。

### 为什么暂把TB与ASI放入执行专家

这里按交互行为提出假设：两者都需要理解目标、操作环境、读取错误/数值反馈、调整程序并检查最终工件。因此可能共享多轮状态、工具调用、执行纠错及结果核验能力；共享能力不代表两项官方agent的工具协议相同。科研执行还要求方法选择、领域约束、数值稳定性、统计有效性和科研产物质量，普通shell成功不能替代这些监督，科研数据/独立dev必须单列。

这一边界并不唯一，SWE同样含执行反馈；单列修复是为了保留仓库理解、补丁与回归测试的集中专长，而非证明它与终端天然互斥。当前三专家是数据/行为共享与工程简化的候选折中，没有直接实验证明优于四专家。固定总训练token时少一个专家主要省初始化、保存、加载和管理，训练计算不会自动显著减少，正式评测量也不减少。若科研数据成熟且更重视专长归因，四专家是更清楚的备选，不应仅以“省算力”强行合并。

## Harness规则：各benchmark独立，同一benchmark内公平一致

用户提供的题面截图明确要求“在每个benchmark内”所有评测对象保持相同配置，没有要求四个benchmark共用同一harness。采用各benchmark原生/官方允许的harness，并让对应训练轨迹优先匹配目标协议，是本项目的数据组织原则。

| benchmark | 对应专家与训练协议方向 | 同项正式评测的要求 |
| --- | --- | --- |
| SWE Pro V2 HARD-51 | 仓库修复专家，优先匹配LockedMiniSwe的bash/command、观察与结束规则 | Base、仓库修复专家、合版及任何额外参评模型使用同一固定SWE配置 |
| TB2 | 交互执行专家的终端子池，匹配Terminus2 | 同一Terminus2配置、资源与五组种子 |
| ASI | 交互执行专家的科研子池，匹配待锁定的官方允许adapter | 同一ASI adapter、prompt/工具/预算/评分，不能为不同模型换工具 |
| HLE | 学术推理专家，按冻结的问答/图文/thinking协议组织数据 | 所有参评模型保持同一模态、工具、提取/判分和生成配置 |

训练harness与目标harness匹配是直接行为模仿的首选，并非题面要求训练过程也只能使用一个harness。交互执行专家可以混合TB、ASI两种原生协议，逐样本保留各自system prompt、工具定义及观察/结束动作，用协议上下文区分；合版模型在不同benchmark下分别接收对应配置。训练任务必须独立，不能因为harness一致就使用正式评测任务或解答。

### 合版模型的接入方式

参数合版只产生一份固定权重，不合并四个agent框架。正式评测时，这同一份权重分别接入SWE的LockedMiniSwe、TB的Terminus2、已锁定的ASI adapter和HLE问答协议；各harness提供自身prompt、工具和观察/执行/评分流程。同一benchmark内与Base、目标专家使用完全相同配置，替换的只有模型权重/模型标识。

例如SWE从Base改测合版时保留SWE工具与预算；TB从Base改测合版时保留Terminus2工具与预算。四项之间可以不同，合版权重本身始终不变，也不切换专家adapter或路由。多协议由对应system prompt和工具定义作为上下文区分；能否保持每套协议的格式与执行能力，在独立dev检验，不能假定合版必然保留，也不为合版临时增加专用提示补救。

跨harness的旧轨迹可作为保留原协议的辅助迁移数据，但不能写成目标协议的原生示范。仅工具拼写/序列化差异且动作、观察、状态和结束语义均可无损对应时才做机械转换。Terminus2的持续tmux与SWE新subshell存在真实状态差异；不能只把keystrokes改名为command。[Terminus2说明](https://arxiv.org/html/2602.21193v1#S3.SS2)、[SWE固定工具配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)

当前ASI adapter尚未选定，不能称Terminal科学子池已经匹配ASI。官方direct_llm只是单次生成后框架执行，不是Terminus2式多轮工具反馈；其他CLI adapter又有自己的工具协议。可结合现有数据在官方允许范围内选择ASI入口，并于训练前冻结，再判断科研轨迹的主源资格；不得修改官方任务/评分契约或在冻结后据正式结果换agent。[官方direct_llm](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py)、[adapter契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/agent_interface.py)

## 2. 主源、补充与明确边界

| 池 | 第一审计候选 | 补充/备选 | 首要资格条件 |
| --- | --- | --- | --- |
| 多语言修复 | [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md) v1.1 mini-swe-agent，Qwen3.6教师分区 | [SWE-smith现成轨迹](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/blob/08e109b4a59eaeebf80e4675cd125d42e7ac99a4/README.md) | CC BY 4.0 / MIT及逐repo许可；排除SWE Pro repo和同源任务；工具模板可对齐 |
| 通用执行 | [Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md) skill-based | [OT-Agent-SFT-100K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K/blob/45fb28fcc38d352133cb28a1c8a43a2f14fea97b/README.md) SuperUser来源 | CC BY 4.0 / Apache声明与上游归属；排除评测派生；多轮与工具返回完整 |
| 科研执行 | 新候选[D3-Gym-Trajectories](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories)科研推理/程序SFT；Terminal科学子池作终端行为辅助 | AutoSDT静态程序备选；独立环境少量补采仅待明确缺口后考虑 | D3为instruction/input/output，未证多轮工具消息；需原repo映射、许可与ASI同源筛选，尚未纳入下载或锁定主配方 |
| 广域学术推理 | [OpenScienceReasoning-2](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md) | [OpenR1-Math default](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)补数学；OpenThoughts科学部分为替补 | 前者CC BY 4.0，为文本合成推理，不是工具轨迹；保留完整答案，核对验证与来源信号 |

主源不是“已经清洗好”。Open-SWE的上游[SWE-rebench-V2作者卡](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)明确只排原始SWE-bench仓库，没有显式过滤其他benchmark。其resolved字段只表示执行结果，不能证明没有本题污染。Open-SWE mini与LockedMiniSwe同谱系也不证明工具协议相同。许可不明、已发现评测关联、或修复任务无法恢复repo/任务ID的记录排除。合成推理没有逐题URL时，保存固定分片/行号、题面hash与生成recipe，明确few-shot来源及近重复审计局限；不把这些索引冒充原题来源证明。

OpenScienceReasoning-2作者提供了[问题合成、推理生成与多数投票流程](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/docs/releases/openreasoning/dataset.md)。这比纯数学池更贴跨学科学术推理，但并非逐条正确性的保证；不能因为卡片写“面向HLE”就认定其含HLE原题，反之也不能认为已完成去污染。

## 当前优先动作：先下载，不抽样复验

用户已明确指示先把数据下载下来，本阶段跳过抽样复验。已固定Open-SWE v1.1 mini/Qwen3.6、Terminal skill-based、OpenScience全train、OpenR1 default四组来源与原始文件清单，见仓库根目录 `data_sources.json`。数据放80 `artifacts/data/raw/<来源>/<revision>/`；下载只做字节数和SHA-256校验，不读取样本、改写任务、重跑教师或启动训练。后续筛选/分组/格式适配另行开展，下节旧验收建议不再是下载的前置步骤。

### 已固定的原始下载范围

| 来源 | revision前缀 | 文件数（含说明） | 原始文件字节 |
| --- | --- | ---: | ---: |
| Open-SWE mini/Qwen3.6 | 1db67417 | 41 | 3,986,366,120 |
| Terminal skill-based | a1667c4f | 27 | 3,139,375,074 |
| OpenScience全train | 174b02c9 | 2 | 15,706,817,460 |
| OpenR1 default | e4e141ec | 11 | 2,149,903,045 |
| 合计 | 固定四个版本 | 81 | 24,982,461,699 |

数据不入Git，固定文件路径/大小/上游hash入 `data_sources.json`。19:39 CST已按用户“等一下”暂停下载，6个文件（1,769,702,489字节）已完成校验，已落盘约8.18GB含未完成分段；保留断点，尚未完成全量，也未生成最终全量回执；“文件完整性校验”不包含样本质量、去污染或执行复验。

## 数据准备优先级：先验收现成轨迹，再决定是否补任务

当前已经找到的是候选来源、许可声明和schema，尚未拿实际样本完成验收。因此下一步优先级是**数据可用性与资源验证并行推进，先有可用训练池，再锁训练量**。6M累计processed token是时间预算，不反过来要求用重复或低质量样本凑满。

| 专家 | 首选的现成内容 | 默认是否需要重新生成 |
| --- | --- | --- |
| 仓库修复专家 | Open-SWE mini的messages/tools/观察与执行标签；补充SWE-smith已有轨迹 | 不需要重跑整个训练池，先核来源隔离、工具协议及消息完整性 |
| 交互执行专家 | Terminal skill-based的多轮轨迹，含科学计算/数据科学分片 | 不需要全部重新rollout；科研方法/工件覆盖存在明确缺口时才补独立任务 |
| 学术推理专家 | OpenScience的input/output推理和答案；少量OpenR1验证数学 | 不需要为现成答案重复调用教师API，先审完整性、正确性信号与来源 |

不能将“任务包”与“训练轨迹”混用。只有instruction/环境/tests而无assistant过程的发布，若要做agent SFT，确实还需教师在环境中执行并记录完整过程；已有多轮消息的发布只需必要适配和审计。前者可作为缺口补充与独立dev，不作为本轮大规模生成主线。

准备阶段先对各主源少量代表性样本检查来源、工具/思考格式、最终答案或工件、长度与重复，再统计符合条件的独立任务、processed/supervised token和语言/技能覆盖。抽样检查通过不等于所有记录已验证成功；来源筛查与结构/重复规则仍应覆盖最终选用manifest。先按原任务/仓库/模板家族分train与两类dev，再分段或生成变体。

**自己需要跑的部分：** 对能可靠匹配原任务、环境的代表性训练样本做抽样复现；独立dev的任务环境和评分逻辑必须验证，后续实际比较模型；任何新增训练轨迹都需执行并检查结果。无需为使用现成SFT轨迹而全量重演每个教师解题过程；未复现样本只标上游/未知验证状态，不宣称本项目全部执行通过。

只有当验收发现明确短板（例如科研执行缺数值检查、图表工件或错误恢复）时，才补少量与正式题无关联的原创任务：先做输入和可验证目标/数值容差/产物检查，再让教师执行并保存assistant/tool过程，保留经验证内容。DeepSeek API主要用于这些小规模缺口，而不是重新生成整池。自建数据计入原训练token和准备时段，不能另占隐形GPU/时间预算；不从ASI/TB/SWE/HLE正式任务改写。

## 3. 预算起点，先按token而非样本数

以下为旧累计6M processed token的pilot配额；最新规模建议与吞吐条件见[训练数据预算](sft_data_budget_20261016.md)，不能将此表视为已确定的充分训练量：

| 对象 | processed token起点 | 内部约束 |
| --- | ---: | --- |
| 仓库修复专家 | 0.9M | Go/Python/JS-TS多语言；不按语言拆更多专家 |
| 交互执行专家 | 1.2M | 通用终端约0.7M、科研/数据执行约0.5M，后者不能被前者挤占 |
| 学术推理专家 | 0.9M | 广域推理约0.6M、可验证数学约0.3M；避免整份变成数学专家 |
| 混训对照 | 3.0M | 使用上述三个最终manifest的并集，样本/出现次数/分段/mask相同 |
| 累计 | 6.0M | 三专家+一次混训，均从同一base独立训练 |

这只是适配时间的起点，不表示3M足以塑造专长或达到成绩目标。没有实际tokenizer统计和四卡吞吐前，不将其换算成精确任务条数。processed token包含必要历史及工具观察，supervised token只计新增assistant输出，另记padding与GPU时间。数据不足时缩放总量或调配经过同等审核的主备源，不复制同题刷规模；冻结前同比调整混训对照。暂不为共同通用数据额外增加第五次训练或隐藏预算。

## 4. 借鉴哪些配方，舍弃哪些负担

- [Occamy](https://github.com/Accio-Lab/occamy)：借同底座、互补分支再合版的实验结构。其Marathon/Sprint并非本题按benchmark分组；不复制全参、偏好优化、RL或原大规模数据量。
- [OT-Agent](https://arxiv.org/html/2606.24855v1)：软件修复与系统操作源具有不同收益，多轮与来源组合值得保留；不把相同任务的重复rollout当多样性，也不照搬其按TB反馈选配方的研究过程。本项目选择仅用独立dev。
- [T-pro 2.1](https://arxiv.org/html/2609.01572v1)：shared SFT接近domain SFT，说明分专再合不必然赢。保留同数据混训是必要的研究对照；其RL专家合版不作为LoRA SFT提升保证。
- [Nemotron-Terminal](https://arxiv.org/html/2602.21193v1)：不同来源互补、success-only并非普遍最优、复杂两阶段课程未必更好。先用简单数据混合与来源特定质量规则，不搭建新的任务生成平台。

两专家可合并全部执行任务再加推理，维护最省但修复会被泛化终端覆盖；四专家可把科研执行单列，归因清楚但增加训练/保存/加载与管理。固定总token时，专家数减少不自动同比减少计算；若四项各归属一个专家，其专家目标全评总量也基本不变。本轮推荐三专家，不同时跑2/3/4种分组消融。

## 5. 数据处理与独立dev

1. **先资格与分组，后抽样。** 固定源revision及许可/归属，规范repo/issue/任务族；四项正式题、答案、参考补丁、隐藏测试、其改写和衍生轨迹全部排除。本项目选择保守排除SWE Pro全体评测repo及fork映射，论文/科研来源还需任务/论文/仓库关联检查。此为建议规则，尚未实际运行。
2. **分割在任务级。** train、checkpoint-dev、merge-dev三者互斥；跨来源、教师、改写与分段统一归组。终端按原始任务/技能模板，修复按repo与issue家族，学术问答按原始问题/近重复家族。dev不从四项正式集截取。
3. **质量规则依来源。** 修复起点优先可验证完整成功轨迹，明确这是小预算审计选择而非普遍最优。终端数据缺统一成功字段，不强套success-only；剔除结构损坏、空输出、异常截断或无意义循环，保留有价值的错误与恢复。推理保留可核验完整回答，不把教师多数票当真值证明。
4. **工具和thinking保持原语义。** 用固定Qwen模板表示assistant/tool边界；不把观察改成assistant，不伪造missing tool result，不把纯文本命令输出当成工具调用。长轨迹按完整工具回合保留必要状态，只监督新增assistant内容；无法保留依赖的片段先不选。8K是待实测训练上限，不是已验证最优。
5. **dev保留四个报告桶。** 修复、通用终端、科研执行、学术推理各自报告；交互执行专家同时承担两个目标，不允许宏平均掩盖科研退化。两个dev各以每桶约10–20个独立任务家族为讨论起点，工具dev采用预先固定的短任务/轮次/时间上限，并先估算所有模型与候选的总成本，控制在既有dev预算内；这里的简短预算不用于正式评测。小dev存在大方差，不能把细小变化当可靠排序。图文保留能力另用独立许可清楚的少量样例检查，不增加正式benchmark。
6. **冻结对照与正式目标。** 三个专家与混训同base、相同LoRA target/rank和数据处理；混训的同样本/次数不代表有效更新秩完全等同，须披露。AVG/TIES仅在merge-dev选；正式阶段Base和合版仍四项全量，仓库修复专家测SWE、交互执行专家测TB五次及ASI全量、学术推理专家测HLE全量，不从正式结果反调配方。

仍未完成逐行许可/污染筛查、来源覆盖统计、工具协议适配、真实token长度/质量抽检及四卡吞吐测量；也未落实正式评测CPU容器与Judge资源。数据和专家建议不能代替这些执行条件。本轮没有安装、下载训练集/模型、写实验代码、调用模型API或启动训练/评测。
