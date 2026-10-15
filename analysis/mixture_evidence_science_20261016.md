# HLE 与 ASI：数据配比及提分经验的证据边界

核验日期：2026-10-16（北京时间）。本轮联网读取作者论文、官方训练 recipe、数据卡和 benchmark README；没有读取正式题目的答案、运行任务、调用模型或下载训练数据。本文只提供调研证据，不冻结比例或修改训练配置。

**结论：HLE 的数学文本子集有可量化的来源配比消融；HLE 全量图文与 ASI 尚未查到可直接照搬的最优 SFT 配比。** 更强的数学／科学 QA 成绩，不保证全量 HLE 或科研项目执行提高。当前方案以 [预算重设计](sft_budget_redesign_20261016.md) 为准，旧 15M 不是默认目标。

## 1. 证据对照表

| 来源 | 真实训练／比较 | 真实结果 | 不能据此推出 |
| --- | --- | --- | --- |
| Nemotron-Math §4.1 | AoPS-only 对比等例数 AoPS:StackExchange-Math=50:50 | HLE-Math high/no-Python 12.22→13.60；有 Python 22.54→24.67 | 50:50 是全量 HLE、非思考 LoRA 或三专家最佳比例 |
| OpenThoughts3 | 85万数学＋25万代码＋10万科学，完整 CoT SFT | HLE text-only MCQ 10.2，起点 12.7；其他多项显著提高 | AIME／GPQA 提高就能保证 HLE 提高 |
| OpenReasoning | 数学 CoT/TIR/GenSelect＋代码 CoT＋科学 CoT | 32B 卡片 HLE 11.9；recipe 中 HLE 排除图像 | 五池拼接证明某个配比最优，或已覆盖我们的2500图文题 |
| D3-Gym | 经执行筛选的科研推理／完整程序 SFT | Qwen3-4B-Instruct SAB平均SR 4.2→7.2；Qwen3-32B 14.7→18.9 | 已在 ASI 取得同等增益，或有终端:科研最佳比例 |
| Nemotron-SFT-Science-v2 | 三学科、四来源、无工具／Python／搜索解答 | 发布2,837,712行，卡片未给独立配比消融 | 发布行数占比就是训练最优权重 |

来源：[Nemotron-Math Table4](https://arxiv.org/html/2512.15489v1#S4.SS1)、[OpenThoughts Table1/Appendix E](https://arxiv.org/html/2506.04178v2)、[OpenReasoning模型卡](https://huggingface.co/nvidia/OpenReasoning-Nemotron-32B)、[D3-Gym Table2](https://arxiv.org/html/2604.27977v1#S4)、[Science-v2卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/main/README.md)。表内数值均为百分比，差值为百分点。

## 2. 最直接的配比消融：竞赛数学加入社区／研究数学

Nemotron-Math 同时有 AoPS 竞赛题与 Mathematics Stack Exchange／MathOverflow 题。§4.1固定训练 problem–solution **例数**，将 AoPS-only 的一半例子替换为社区数学；不是固定 token 的50:50，也不是对最终完整数据池自然占比的描述。[作者方法与Table4](https://arxiv.org/html/2512.15489v1#S4.SS1)

| HLE-Math推理配置 | AoPS-only | 50:50混合 | 差值 |
| --- | ---: | ---: | ---: |
| High，无Python | 12.22 | 13.60 | +1.38 |
| Medium，无Python | 7.22 | 8.58 | +1.36 |
| Low，无Python | 3.92 | 4.10 | +0.18 |
| High，有Python | 22.54 | 24.67 | +2.13 |
| Medium，有Python | 13.40 | 15.22 | +1.82 |
| Low，有Python | 7.91 | 7.99 | +0.08 |

这些是pass@1，四个seed平均；评测对象为**976题的text-only HLE-Math**，最大生成120K tokens，temperature=1、top_p=1，judge是Qwen2.5-32B-Instruct。它既不是全2500题，也不是无图限制解除后的全学科分数。[§3.2与Table4](https://arxiv.org/html/2512.15489v1#S3.SS2)

方法核验：§3.1明确所有实验使用 supervised fine-tuning pipeline，AdamW、lr=2e-4、global batch=2048、packing；“NeMo-RL”是软件框架名，不能据此称为RL消融。训练对象写作Qwen3-8B与Qwen3-30B-A3B，未写“-Base”。Table4位于明确讨论30B的Table3与Table5之间，但caption没有再次列尺寸，因此本文不把该表单独配置补写成完全核定。[§3.1—§4.2](https://arxiv.org/html/2512.15489v1#S3.SS1)

作者没有在该消融处披露LoRA/full-parameter细节，也未证明processed/loss tokens或GPU时间相等。等例数控制了一个主要变量，不能称为等训练成本，更不能从两个端点推出全局最佳比例。

对我们的可用经验：数学池应避免只剩奥赛格式；社区／大学／研究问题可补题型与表达覆盖。它支持“增加相关覆盖值得考虑”，不支持直接给当前Math-v4设50%来源硬配额。本文实验是旧版gpt-oss长推理数据，当前Math-v4的teacher与处理方式已不同。

## 3. 很关键的负例：更多推理数据并不保证 HLE 提分

OpenThoughts通过1000余项消融优化来源、问题过滤、多解采样、答案过滤和teacher。最终OpenThoughts3为850,000数学、250,000代码、100,000科学，即70.8%/20.8%/8.3%的**训练例数**。作者说这个跨域比例沿用OpenThoughts2；不是用HLE搜索得到的最优比。[论文§4—§5](https://arxiv.org/html/2506.04178v2)

Qwen2.5-7B-Instruct经完整CoT SFT得到OpenThinker3-7B：

| 评测 | 起点 | SFT后 |
| --- | ---: | ---: |
| GPQA-D | 24.6 | 53.7 |
| AIME25 | 8.0 | 53.3 |
| HLE MCQ | 12.7 | 10.2 |

HLE只取**512道text-only multiple-choice题**，3轮平均；统一max_new_tokens=32,768、temperature=0.7、top_p=1。HLE是pipeline选择时的held-out指标。Appendix G明确指出，该设置中的HLE没有随数据规模增长而改善。[Table1、Appendix E/G](https://arxiv.org/html/2506.04178v2)

因此，论文不能被概括为“70%数学可提升HLE”；更贴切的经验是：广义reasoning分数改善与HLE收益可能分离。这里起点是已有较强指令能力的Instruct模型，不能拿它与另一个预训练Base直接比较。

## 4. OpenReasoning 给了混合 recipe，但没给最优配比证明

官方recipe列数学CoT、数学TIR、数学GenSelect、代码CoT、科学CoT五块，要求拼接后SFT；使用Qwen2.5系列标准Base模型，49,152长度packing、30,000步、最后checkpoint。它证明这种多能力联合SFT可行，没有独立给出按token优化过的五块比例。[训练recipe](https://github.com/NVIDIA-NeMo/Skills/blob/main/docs/releases/openreasoning/training.md)

OpenReasoning-Nemotron-32B模型卡报HLE 11.9、SciCode39.6；其HLE数据准备代码显式跳过`entry["image"]`。因此此HLE是文本范围，不应和本项目全量图文分数并列作同协议数字。模型支持64K输出的长推理，亦不同于我们的预算与非思考模板。[模型卡](https://huggingface.co/nvidia/OpenReasoning-Nemotron-32B)、[HLE preparation](https://github.com/NVIDIA-NeMo/Skills/blob/main/nemo_skills/dataset/hle/prepare.py)

卡片“heavy”模式HLE 11.8→GenSelect15.5是多样本推理／选择收益，含额外推理成本；不是训练配比消融。recipe还直言所复用旧数学TIR数据效果通常不如CoT，不能因为工具轨迹更复杂就自动提高其训练权重。[模型卡](https://huggingface.co/nvidia/OpenReasoning-Nemotron-32B)、[训练recipe](https://github.com/NVIDIA-NeMo/Skills/blob/main/docs/releases/openreasoning/training.md)

OpenScienceReasoning-2数据卡称1.6M QA、覆盖STEM／法学／经济／人文，目标含HLE；这是覆盖与用途声明，不是单独“加多少科学数据使HLE提高多少”的消融。[数据卡](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md)

## 5. ASI：直接的配比提分证据仍缺失，D3是近邻证据

官方ASI论文与固定README描述60项目、11域、B1–B4与18种agent–model配置；本轮未发现作者发布独立SFT训练混合消融。其强agent配置是多轮工具执行结果，不能当作我们`direct_llm`单次生成程序的训练收益估计。[ASI论文](https://arxiv.org/abs/2608.17271)、[固定README](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md)

D3-Gym提供565任务／239科研repo／四学科；将生成程序真实执行并用silver verifier筛选后做rejection-sampling SFT。32B成功解答池2,153条；4B-Instruct只监督最终程序，不用reasoning trace，是与我们非思考方案更接近的局部证据。[§4与Appendix E](https://arxiv.org/html/2604.27977v1#S4)

| 原版ScienceAgentBench | Base平均SR | SFT平均SR | Base SR@3 | SFT SR@3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-4B-Instruct，Distill | 4.2 | 7.2 | 5.9 | 8.8 |
| Qwen3-14B，Self | 9.1 | 13.1 | 13.7 | 19.6 |
| Qwen3-32B，Self | 14.7 | 18.9 | 19.6 | 27.4 |

SR是三次独立运行的平均成功率，SR@3是best-of-three；32B的+7.8来自SR@3，平均SR增幅是+4.2，不能混报。训练1 epoch、32,768长度、默认评测16K输出。Appendix E同时写“full-parameter”与LoRA rank16，表述有冲突，本文不拿它证明明确的full／LoRA对照。[Table2、Appendix E](https://arxiv.org/html/2604.27977v1#S4)

4B-Instruct的提升提示：保留正确完整程序、验证文件产物与执行行为，比单纯补数学问答更贴近科研程序能力。但这仍是ScienceAgentBench，不是ASI；D3只有四学科，无终端:科研混合消融，尚不支持给E_exec设一个已证实的TB/ASI最佳比例。

数据也不能只按“运行无报错”筛：论文观察执行有效性提高后仍有逻辑／算法错误，API与库使用问题仍常见。对ASI的可迁移做法是监督正确数据schema、数值方法、完整输出与文件契约；有效执行和科学正确应分别记录。[D3错误分析§4](https://arxiv.org/html/2604.27977v1#S4)

## 6. 当前新数据的真实含义与处理风险

Nemotron-SFT-Science-v2含Physics/Biology/Chemistry；四池行数为synthetic MCQ96,610、vendor221,598、RQA413,519、SO2,105,985，共2,837,712。三种解答形态为无工具CoT、Python、Tavily搜索；teacher含GPT-OSS、Kimi-K2-Instruct、DeepSeek-V3.2、DeepSeek-V4-Pro。发布行数不等于其实际训练采样权重，卡片也没给四池配比对HLE/ASI的独立消融。[官方卡片](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/main/README.md)

Math-v4卡片写DeepSeek-V4-Pro high生成，并引用旧Nemotron-Math论文；这不意味着旧gpt-oss数据的50:50实验已在v4重做。[Math-v4卡片](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/main/README.md)

本项目清理显式teacher thinking后，必须检查留下的内容：若只剩一个最终数值，监督目标已经从推理蒸馏变为答案／格式监督。上面的完整长CoT收益不能照搬。保留可见完整解答与程序的合格数据，才有相对接近的学习目标；仍需独立dev验证。

图像也是独立缺口：这些Math／Science池是文本，冻结视觉模块不代表语言侧SFT后视觉能力自动保持；不能把文本数学来源配比当作HLE图文配比结论。

## 7. 可执行的解释，不增加训练搜索

1. **HLE专家内部：先保学科／题型覆盖，再扩充合格独立题。** 加社区／研究数学有受限实证；不要用HLE考试数学占比当训练最优，也不要让大量短答案数学淹没其他学科。
2. **科研程序内部：先匹配目标行为。** 对ASI direct_llm，正确完整程序与产物契约优先于不相容工具调用数量；D3是候选经验，尚需来源映射、许可、正式同源排除。
3. **只作一份受成本约束的manifest。** 同时记录独立任务N、完整token L、processed token P、loss token S；论文的按例数比例只作参照，不能直接替换成本核算。
4. **不从专家内部配比推出专家间时长或合版系数。** 三者是不同控制量；当前只保留既定四次主体SFT与AVG/TIES独立dev选择，不为搜最佳比例追加训练分支。

本轮最值得引用的两点是：**50:50社区数学的HLE-Math小幅收益，以及OpenThoughts3在HLE文本MCQ上未受益的反例。** ASI提分暂时只能给行为匹配与近邻实验依据，不能承诺收益幅度。
