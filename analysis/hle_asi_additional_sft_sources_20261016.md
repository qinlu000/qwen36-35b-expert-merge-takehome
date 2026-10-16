# HLE / ASI 可补充的 SFT 来源（2026-10-16）

**不只有当前 HLE500 / ASI82。HLE 有大量现成教师解答；ASI 有现成人工代码和科研代码辅助池，但能直接对应“读任务数据、输出完整 Python、写指定产物”的公开样本更少。** SAB verified 的102题只是我们已整理的一个来源，并不是科研编程数据的总量。本轮仅核一手数据卡、公开字段与小型文本；不扩充训练集、不调用模型API、不下载大包、不运行新环境。

先读了现有 [ASI来源决定](asi_task_sources_decision_20261016.md)、[补充核查](asi_task_sources_followup_20261016.md)和[新近科学教师报告](latest_trajectories_science_20261016.md)。当前用户已允许全部SAB参考程序用于SFT，因此**不能继续用本机是否跑得动、依赖是否齐全作现成参考代码的SFT入集条件**。这些资源要求只影响后续执行评测或新采教师的成本。

## 第一档：已有回答或人工代码，可以直接做监督样本

“直接”指已有监督目标，无需重新调用教师；并不表示全库已通过本项目的质量筛选、来源排除或长度验收。

| 来源 / 原生 split | 可取得的真实规模与教师 | 已有内容、协议与本项目用途 |
|---|---|---|
| **[NVIDIA Nemotron-SFT-Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4)**，`train` | **545,431行**：COT285,516，TIR259,915；**DeepSeek-V4-Pro High**；12个Parquet约5.16GiB | 有题、参考答案、完整messages和来源；仅保留最终答案匹配参考的轨迹。优先取**纯COT**补HLE数学；TIR含Python调用/反馈，需要保留或适配工具协议，不能直接当纯问答或ASI完整文件程序。参考一致不等于逐步推理经人工审定。纯文本，无图像字段；AoPS为CC BY4.0、SE为CC BY-SA4.0。 |
| **[NVIDIA Nemotron-SFT-Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2)**，rqa/so/syn_mcq/vendor四配置 | 作者卡合计**2,837,712行**，约49GB；DeepSeek-V4-Pro、DeepSeek-V3.2、Kimi-K2-Instruct、GPT-OSS混合 | 物/化/生题及教师解答，含纯CoT、Python、Tavily搜索。**不是全体V4，也没有逐题gold正确性保证**；不能因为规模大或教师新就将此前135条hold直接解禁。需取来源可追溯、回答完整且质量合格的部分。纯文本，不补HLE图像/全部人文学科；CC BY-SA4.0。 |
| **[EcoCoder scientific reasoning](https://huggingface.co/datasets/alrobles/ecocoder-scientific-reasoning)**，`train`1268 / val159 / test159 | 作者称DeepSeek v4 Pro，`reasoning_effort=high`；总1586，约5MB文本；**本次实数train：459 Python、807 R、2条语言缺失** | 生态论文情境→推理→R/Python代码，含paper/DOI/language元数据。459条Python均有显式推理与闭合Python代码块，可作ASI辅助；不是作者约40%的估算。只有质量分筛选，未提供逐条独立执行通过证据或完整输入/验证器；部分为模拟数据/方法演示，不等同ASI同型完整产物。Apache2.0；领域较窄。 |
| **[DS-1000](https://huggingface.co/datasets/xlangai/DS-1000)**，官方只有`test`1000 | 人工整理参考代码和执行测试；**1000题来自451个StackOverflow原题**，含改写变体，不是1000独立原题族 | `prompt`、`reference_code`、`code_context`齐全，可转“题→人工代码”辅助SFT；主要是NumPy/Pandas/SciPy等**短函数/库片段**，不是ASI同型完整科研产物。官方无train；若用于本项目训练，应明确重新用途并停止把DS-1000当独立评测。按原题族分组。CC BY-SA4.0；不需要为训练先安装七套库。[作者项目](https://ds1000-code-gen.github.io/) |
| **[原版SciCode](https://huggingface.co/datasets/SciCode1/SciCode)**，`validation`15 / `test`65 | 本次小型JSONL实核：**15份主任务general_solution + 50份子步ground_truth_code**均非空；65份test两类答案均为空 | 科学家人工科学Python与测试，涵盖数值/模拟。15主题及50子步是同一批任务的不同粒度，不能相加成65独立题。属于**函数返回值/数值辅助**，不是现成ASI文件产物。官方无train，若转辅助训练则不再当独立dev；Apache2.0。执行时才需科学依赖及外部HDF5目标，文本SFT无需先重跑。[官方仓库](https://github.com/scicode-bench/SciCode) |

## 第二档：有题/目标，但还需要生成完整教师程序

- **[SciCode-Verified](https://huggingface.co/datasets/shhu2001/SciCode-Verified)**：官方`test`64主任务；发布纠正题面、测试规格和数值目标，**没有现成模型解答**。需要新教师编程并对目标验证，函数协议仍需与ASI区分。它不是另一个64条现成gold训练池，不重复启动此前已停止的校准。
- **[DiscoveryBench](https://github.com/allenai/discoverybench)**：官方[HF库](https://huggingface.co/datasets/allenai/discoverybench)真实`train`目录当前有4个数据方向、14个metadata文件；metadata可含多个query，不能把文件数等同任务数。带输入表格、正确假说与文字workflow，但任务资产中无`.py`/`.ipynb`完整参考程序。适合后续用强教师生成数据分析代码；原生评分是**假说语义**，还需定义程序/产物目标，不是拿现成Python答案训练。

## 几个容易误判的名字

- **[OpenThoughts3-1.2M](https://huggingface.co/datasets/open-thoughts/OpenThoughts3-1.2M)**确有`train`120万回答，但来自**75k问题各16次QwQ-32B生成**；覆盖数学85万、代码25万、科学10万。可直接监督，但教师较旧、重复回答不能算新问题；本轮优先级低于Math-v4/Science-v2。
- **[DeepMath-103K](https://huggingface.co/datasets/zwhe99/DeepMath-103K)**确有`train`103,022题，带最终答案与每题3份**DeepSeek-R1**解答；是现成数学备选，不是新的V4教师池，也不补人文/图像。
- **[MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)**只有`test`12,032和`validation`70，**没有train**。存在`cot_content`字段不等于12k条新教师训练池；它是跨学科评测题，不能按训练split宣传。
- **ScienceCode同名HF池确实存在**，例如[physics22,549条train](https://huggingface.co/datasets/renjiepi/sciencecode-physics_v1_n100k1)。但本次前10条可见`agent=terminus-2`、`model=DeepSeek-V3.2`，系统要求Linux命令批次JSON；其余chem21,642、math22,610、bio24,015、matsci33,610的卡也只有schema。**这是一组终端交互记录，不是ASI单轮Python gold**；没有可核的成功标签、生成方法及许可说明，不能直接入主推荐。
- **SuperSWE**：本次精确HF检索为空，未核到这个准确名字的公开科研编程训练集；不以相似NVIDIA SWE名称补造来源，也不推断它不存在。

## 本项目可采用的下一步建议（未执行）

HLE可把**2k合格独立问题**作为下一轮抽样目标，先补Math-v4纯COT，再从Science-v2挑来源清楚、答案质量合格的科学题；不要直接拿全体Science-v2。ASI可在现有SAB82个train之上，**考虑再补约500–1000条Python函数/科学库辅助**，优先人工DS-1000、原版SciCode dev，再补EcoCoder的实际Python train子集；这个数字是配方建议，不是已落实数量，也不是新增500–1000个ASI同型科研任务。

不读取正式HLE/ASI答案选样；仅用来源、公开输入和已有隔离信息排除目标同题。不得把上游同一原题的改写、多个回答、子步和跨池重复当新增独立问题。训练现成代码不要求先搭新环境；新增教师程序才涉及额外生成、执行和产物验证。用户本轮只询问替代来源，尚未要求扩充HLE/ASI，因此本报告到建议为止。

## EcoCoder train 实数补充

本次只读官方[固定版本train.jsonl](https://huggingface.co/datasets/alrobles/ecocoder-scientific-reasoning/resolve/09591b2b7b261aeb37d7db464f2af31eaa24baa0/data/ecology/train.jsonl)，源revision为`09591b2b7b261aeb37d7db464f2af31eaa24baa0`，未做hash、代码执行或训练导出。

- 逐行解析共**1268**条，按原始`metadata.language`计数：`Python` **459**、`R` **807**、缺失 **2**。459是有明确Python标签的数量，约占train的36.2%；没有把缺失语言的两条推定为Python，也没有混入val/test。
- 这459条均含非空assistant回答、`[REASONING]`和`[CODE]`段，且均有闭合的Python代码块。消息字段仅`role/content`，角色为system/user/assistant；**没有独立`reasoning_content`、隐藏thinking或tool观察字段**。推理是发布者公开放在`assistant.content`中的文本段，并非本次取得未公开的模型隐藏推理。
- 原始记录字段为`id/domain/method/method_category/messages/metadata`；metadata含`paper_title/paper_id/doi/language/tags/quality_score/source/generated_at`，字段存在不保证逐条非空。
- 代码段已经提供，无需重新生成教师答案；“有完整闭合代码块”不等于运行正确或复现真实论文数据。例如首条Python样本是用NumPy模拟PCR引物检测结果并打印统计，说明它可教科研方法/代码，但不是ASI读取规定输入、写规定文件的同型任务。459条是**现成Python辅助候选数**，不是已验收可加入的459个独立科研任务。
