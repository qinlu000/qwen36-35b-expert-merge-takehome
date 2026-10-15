# 四项 benchmark 对应训练数据：当前可复用清单

核验：2026-10-15。只查一手论文、作者仓库、数据卡、文件和 schema 元数据。未读取数据行、参考答案或隐藏测试；未恢复此前暂停的下载，未新增数据下载或执行实验。所有来源仍是候选，不等于已完成格式、去污染和许可筛选。

## 结论与选择

SWE 与 Terminal 有目标行为很接近的公开交互轨迹；HLE 有作者明确面向该类学术推理能力的数据；ASI 新找到小型现成科研程序 SFT 集及配套可执行任务。四项不需要共用一个 harness，但同一项的所有参评模型必须使用相同冻结配置。**本次尚未核到一套可直接完整覆盖 ASI、且与待选 ASI adapter 一致的现成多轮轨迹。**

| 目标 | 优先候选 | 已有内容 | 对当前方案的作用与边界 |
| --- | --- | --- | --- |
| SWE Pro V2 HARD-51 | [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces) v1.1 mini/Qwen3.6；补充 [SI2CA standard](https://huggingface.co/datasets/Self-Improving-Coding-Agents/SI2CA-Training-Trajectories) | 仓库修复 assistant/tool 消息；前者多语言，后者10,780条Python任务轨迹，明确bash(command) | 仓库修复专家主线；mini同谱系不证明观察/结束/状态完全一致，仍需核协议和排除Pro同源 |
| Terminal-Bench 2.0 | [Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus) skill-based；[OpenThoughts-Agent-SFT-100K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K) 作备选 | 前者约140K合成技能轨迹，论文采用持续tmux与JSON动作的Terminus2；后者包含SuperUser/OpenHands来源 | 交互执行专家的终端子池；前者更贴目标，后者不得混称Terminus原生轨迹 |
| ASI-Bench | [D3-Gym-Trajectories](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories)；[D3-Gym环境](https://github.com/OSU-NLP-Group/D3-Gym)；[AutoSDT-5K](https://huggingface.co/datasets/osunlp/AutoSDT-5K)备选 | D3有565科研任务/239repo及verifier，32B现成SFT为2,153条、约72MB；公开schema为instruction/input/output | 补科研推理与程序实现；不能写成现成多轮工具反馈。仍需锁ASI adapter、建立SFT到原repo映射，才决定是否少量同协议采集 |
| HLE | [OpenScienceReasoning-2](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2)；[OpenR1-Math-220k default](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k)补数学 | 前者合成多学科题与推理，作者明确目标含HLE；后者数学推理解答 | 学术推理专家主线；均为文本，不能据此声称覆盖HLE图像推理；HLE本身为评测，不作训练 |

各项更完整的候选、固定revision与协议证据：[SWE](benchmark_training_swe.md)、[ASI](benchmark_training_asi.md)、[Terminal](benchmark_training_terminal.md)。已有四组下载版本仍以根目录data_sources.json为准；本次不自动加候选或更换版本。



## 题面固定什么，哪些agent可以选择

需要区分评测环境/评分流程与模型用于解题的agent。题面不是要求四项都绑定唯一agent，也没有要求所有训练数据由目标harness生成。

| 项目 | 约束与选择空间 |
| --- | --- |
| TB2 | 题面明确Harbor（Terminus-2），不能为数据兼容性另换agent |
| SWE Pro V2-hard | 题面要求官方评测器、披露并统一Agent配置；V2 README给LockedClaudeCode、LockedMiniSwe、LockedCodex等入口，不是唯一mini。所选版本的locked protocol、官方环境/判分和fresh replay仍遵守 |
| ASI | 按所选官方版本流程运行；可在官方支持/允许的adapter或agent-cmd契约内选择，任务/评分/必要隔离与产物契约不变 |
| HLE | 没有题面指定的唯一agent；工具/模态/抽取与判分协议需训练前确定、披露，同项所有模型相同 |

因此，冻结前可以把现有数据兼容性作为选择合规agent的依据；之前的SWE LockedMini是候选方案，不是题面唯一指定。ASI也不必对齐一个尚未选定的唯一接口。训练和评测harness匹配是减少协议差异的工程偏好，不是题面硬性要求；真实语义差异仍不能靠改字段冒充原生轨迹。正式配置须训练前冻结，不能不同模型各选agent或据正式分数再改。

一手依据：[SWE V2允许入口及locked protocol](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#running)、[ASI官方agent-cmd与运行流程](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md#3-run-an-agent)；TB/HLE题面约束见EXPERIMENT_REQUIREMENTS.md及用户原附件。

## 与目标harness是否一致：尚未完成完全匹配验收

当前不能将本清单称为“已经匹配目标harness的训练集”。框架同名、工具名称相同或研究目标相关，都不足以证明模型可见协议一致。

| 项目 | 当前证据等级 | 未解决的问题 |
| --- | --- | --- |
| SWE | mini同谱系；SI2CA明确bash(command) | 精确mini版本、system prompt、shell状态、观察模板/截断、提交动作未逐项核齐 |
| TB | Nemotron采集与目标同属Terminus2，匹配证据最强 | 未确认同版本、同模板、同观察/结束规则；未读实际消息完成核对 |
| ASI | D3是科研推理与最终程序，尚非同协议多轮轨迹 | 目标adapter未锁；若选多轮CLI，静态程序解答不能替代工具交互 |
| HLE | 静态无工具问答，不涉及终端动作协议 | 需适配目标模板/thinking/答案表达；文本池仍缺图像覆盖 |

直接模仿的主训练轨迹应优先验证动作、观察、状态与结束语义相容；只有序列化差异且不改变这些语义时才机械转换。存在真实协议差异的数据可保留原上下文作辅助迁移，但不能冒充目标原生示范。不同版本不自动代表不可用，同框架也不自动代表匹配。正式评测始终在同一benchmark内对所有模型锁定同一harness。

## SWE：新增备选的取舍

SI2CA standard的工具字段比Open-SWE卡片更明确，可作为Python补充；另两个self-judgement配置共享相同任务，且筛选judge使用训练gold patch，不能相加当独立题，也不能把judge材料拼进policy监督。三源跨配置/教师/数据集需要按repo、PR、任务族去重。

[Microsoft Orchard](https://huggingface.co/datasets/microsoft/Orchard)另有107,185条SWE轨迹，其中94,972条mini；但卡片说明路径和标识符已匿名化，执行语义是否保留未核。暂列备选，不为了规模立即替换现有主线。Open-SWE、SI2CA、Orchard均未证明已排除SWE Pro；优先按Pro全11repo及同源fork/PR保守排除。

## ASI：这轮最值得补充的发现

D3-Gym比只用普通shell或纯数学更贴科研程序产物，也不要求为拿到现成SFT先重生成整个池。论文中的成功轨迹是推理加最终程序，再由silver verifier执行筛选；公开schema不能证明带逐轮工具结果。若ASI最终用direct_llm单次生成后框架执行，这类监督在行为形式上更接近；若用多轮CLI agent，则程序SFT只补实现能力，多轮反馈仍需相应独立任务数据。

D3数据卡MIT不替代原科研repo许可。原任务有无许可及GPL家族，训练schema没有原repo字段；建立可靠映射后才能按许可和ASI同源白名单筛选。AutoSDT有逐条repository_url/license，便于筛来源，但缺稳定闭环环境。SciAgentGym/SciForge有真实环境和tool-call生成方法，尚未核到固定可下载的作者SFT池，本轮不算现成训练数据。

本次官方ASI公开入口仅核到两seed的正式评测任务等资源，没发现独立训练池。正式60项目、参考产物、评测反馈和同源改写不用于训练或dev。

## HLE：文本主线与图像缺口

[HLE官方README](https://github.com/centerforaisafety/hle/blob/main/README.md)将cais/hle按test加载，并要求过滤出训练语料。不能搜索名含HLE的数据就拿来训练，尤其重标注HLE、同题推理轨迹和评测报告。

OpenScienceReasoning-2固定revision为174b02c9cdf231f220765b2a1d5ece4550921894，CC BY 4.0。包含STEM及法学、经济、人文学科合成问答与详细推理；[作者recipe](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/docs/releases/openreasoning/dataset.md)公开了问题合成、DeepSeek-R1-0528解答与多数投票流程。卡片写面向HLE不代表含HLE原题，也不证明已对本项目完成去污染或每条解答正确。OpenR1仅补数学，不能替代广域学科。

本轮另核两个来源，但不加入默认下载：

- [Nemotron-Science-v1固定卡](https://huggingface.co/datasets/nvidia/Nemotron-Science-v1/blob/82e1af468197076b4f0f392c239274eac032adc7/README.md)：CC BY 4.0，226,334条文本合成科学题；MCQA含GPT-OSS-120B推理，RQA偏化学。可作STEM备选，不自动优于已有跨学科主线。
- [Multimodal-STEM-HLE++固定卡](https://huggingface.co/datasets/TuringEnterprises/Multimodal-STEM-HLE-plus-plus/blob/56ad2ebe384a952687e46f0672e89035be81f85b/README.md)：MIT，公开仅50条图文任务；卡片宣传含逐步理由，但公开schema只列Prompt/GTFA/Image等，没有独立rationale字段。只说明确有小型图文候选；尚不能称可用的完整CoT SFT池，原题来源和HLE独立性也未核。本轮不采用其效果宣传作为证据。

HLE正式全量包含图像，文本SFT的收益不能外推到图像题。冻结视觉参数仍会更新语言侧能力，不等于图像推理已被补齐；保留该限制并用独立图文dev检查。


## Terminal：新增消息池与任务环境的区别

[Nex Agent-SFT](https://huggingface.co/datasets/nex-agi/agent-sft/blob/d8d4de5643f9fe9d3fc3f89b3d55b8709ddc35c9/README.md)是实际多轮messages数据，69,008条总量中agentic_code为24,796条，卡片ODC-BY；并非总量都是terminal，也未核到原生Terminus2子池。其论文用Terminus2评测不能证明训练轨迹采用相同协议，当前仅作通用agent备选。

[Endless Terminals](https://github.com/kanishkg/endless-terminals/tree/99f4c74b75faacf21e53d3dc01df170902e924cb)有约2,500个Harbor可执行终端任务；代码Apache-2.0、数据卡声明MIT，需分别核归属。作者agent动作type/command/timeout_sec与Terminus2不同；任务环境可复用，但本次未核到现成原生Terminus2成功对话池。若现成轨迹有明确缺口，才考虑在独立任务上小量用目标harness采集，不重跑全池造题、pass@16或PPO。

## 建议的数据组合

维持三个专家，不增加训练次数：仓库修复用Open-SWE mini为主、SI2CA standard补充候选；交互执行用Terminal skill-based为终端主线，D3科研程序作为新科研候选，保留两桶独立配额/dev；学术推理仍以OpenScience为主、OpenR1补数学。比例需在最终可用量和token统计后定，本轮没有改写原预算。

不需要从零为四项各造一个大训练集。现成数据优先；是否需要自采主要取决于ASI选定adapter后的多轮协议缺口。任何自采都只在独立训练任务上进行，保留执行反馈和许可来源；不能把目标评测任务改写后生成训练轨迹。
