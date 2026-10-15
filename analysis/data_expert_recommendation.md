# 数据来源与专家分工建议（v3，待讨论）

2026-10-15核验。用户已确认训练框架ms-swift；本稿仅为数据与专家划分建议，没有恢复实验实现或执行。主要变化是把原“科学专家负责HLE+ASI”改为按任务行为划分：**E-code负责SWE，E-exec负责TB+ASI，E-reason负责HLE。** 原始总训练预算暂不扩大。

专项证据：[修复数据](data_swe_sources.md)、[终端数据](data_terminal_sources.md)、[科学数据](data_science_sources.md)、[专家划分参考](expert_partition_research.md)。本稿的比例、抽样和dev方案均为工程/研究判断，不能当作论文已证实的最优配方。

## 1. 推荐三专家，按行为与产物区分

| 专家 | 学习行为与主要产物 | 主要正式目标 | 数据管道 |
| --- | --- | --- | --- |
| E-code：仓库修复 | 阅读已有仓库、定位问题、修改多个文件、执行回归、恢复错误；产出仓库补丁 | SWE Pro V2 HARD-51 | 多语言修复assistant/tool完整轨迹 |
| E-exec：终端与科研执行 | 命令/环境/文件操作，以及科学数值计算、数据分析、结果和工件检查；产出可执行程序/数据/图表 | TB2 + ASI | 通用终端与科研执行两桶，独立配额、标签和dev |
| E-reason：广域学术推理 | 无工具条件下跨学科推理、答案表达、证据与一致性检查；产出学术答案 | HLE | 广域科学/人文推理为主、可验证数学为补充 |

同一训练任务默认只归一个专家：已有仓库的修复/回归归E-code；在环境中完成工作流并交付工件归E-exec；直接给学术答案归E-reason。科学主题本身不决定专家归属。跨数据源同题、不同教师和不同框架的变体必须统一分组。不同正式benchmark仍各用冻结的官方agent和工具，不为配合训练数据改agent。

旧三分法容易把HLE和ASI的监督形式混在一起，令纯数学冒充科研执行。新划分仍只有三次专家训练；exec内显式留科研子预算，不能被普通shell任务挤掉。HLE全量含图，而本轮候选推理池主要为文本；冻结视觉只保证保留原视觉权重，不证明图像推理收益。该覆盖缺口应在独立图文dev与最终报告明确披露，不临时接入来历不明的多模态大包。

## 2. 主源、补充与明确边界

| 池 | 第一审计候选 | 补充/备选 | 首要资格条件 |
| --- | --- | --- | --- |
| 多语言修复 | [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md) v1.1 mini-swe-agent，Qwen3.6教师分区 | [SWE-smith现成轨迹](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/blob/08e109b4a59eaeebf80e4675cd125d42e7ac99a4/README.md) | CC BY 4.0 / MIT及逐repo许可；排除SWE Pro repo和同源任务；工具模板可对齐 |
| 通用执行 | [Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md) skill-based | [OT-Agent-SFT-100K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K/blob/45fb28fcc38d352133cb28a1c8a43a2f14fea97b/README.md) SuperUser来源 | CC BY 4.0 / Apache声明与上游归属；排除评测派生；多轮与工具返回完整 |
| 科研执行 | 同一Terminal Corpus的scientific_computing/data_science文件分区 | 少量独立数值/图表任务仅作后续缺口补充 | 可按固定路径抽取；不是已复现ASI的科研轨迹，缺研究复现/完整论文覆盖 |
| 广域学术推理 | [OpenScienceReasoning-2](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md) | [OpenR1-Math default](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)补数学；OpenThoughts科学部分为替补 | 前者CC BY 4.0，为文本合成推理，不是工具轨迹；保留完整答案，核对验证与来源信号 |

主源不是“已经清洗好”。Open-SWE的上游[SWE-rebench-V2作者卡](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)明确只排原始SWE-bench仓库，没有显式过滤其他benchmark。其resolved字段只表示执行结果，不能证明没有本题污染。Open-SWE mini与LockedMiniSwe同谱系也不证明工具协议相同。许可不明、已发现评测关联、或修复任务无法恢复repo/任务ID的记录排除。合成推理没有逐题URL时，保存固定分片/行号、题面hash与生成recipe，明确few-shot来源及近重复审计局限；不把这些索引冒充原题来源证明。

OpenScienceReasoning-2作者提供了[问题合成、推理生成与多数投票流程](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/docs/releases/openreasoning/dataset.md)。这比纯数学池更贴跨学科学术推理，但并非逐条正确性的保证；不能因为卡片写“面向HLE”就认定其含HLE原题，反之也不能认为已完成去污染。

## 3. 预算起点，先按token而非样本数

在既有累计6M processed token讨论预算下，建议暂分：

| 对象 | processed token起点 | 内部约束 |
| --- | ---: | --- |
| E-code | 0.9M | Go/Python/JS-TS多语言；不按语言拆更多专家 |
| E-exec | 1.2M | 通用终端约0.7M、科研/数据执行约0.5M，后者不能被前者挤占 |
| E-reason | 0.9M | 广域推理约0.6M、可验证数学约0.3M；避免整份变成数学专家 |
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
5. **dev保留四个报告桶。** 修复、通用终端、科研执行、学术推理各自报告；exec同时承担两个目标，不允许宏平均掩盖科研退化。两个dev各以每桶约10–20个独立任务家族为讨论起点，工具dev采用预先固定的短任务/轮次/时间上限，并先估算所有模型与候选的总成本，控制在既有dev预算内；这里的简短预算不用于正式评测。小dev存在大方差，不能把细小变化当可靠排序。图文保留能力另用独立许可清楚的少量样例检查，不增加正式benchmark。
6. **冻结对照与正式目标。** 三个专家与混训同base、相同LoRA target/rank和数据处理；混训的同样本/次数不代表有效更新秩完全等同，须披露。AVG/TIES仅在merge-dev选；正式阶段Base和合版仍四项全量，E-code测SWE、E-exec测TB五次及ASI全量、E-reason测HLE全量，不从正式结果反调配方。

仍未完成逐行许可/污染筛查、来源覆盖统计、工具协议适配、真实token长度/质量抽检及四卡吞吐测量；也未落实正式评测CPU容器与Judge资源。数据和专家建议不能代替这些执行条件。本轮没有安装、下载训练集/模型、写实验代码、调用模型API或启动训练/评测。
