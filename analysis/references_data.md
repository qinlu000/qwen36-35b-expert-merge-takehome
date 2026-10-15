# 数据与训练轨迹参考：五项一手资源核验

访问日期：2026-10-15（Asia/Shanghai）。范围仅为公开数据卡、README、论文与元数据；没有下载大型数据、读取本题评测答案/参考补丁/隐藏测试、编写实验代码、训练、评测或调用模型 API。以下将**已核事实、项目建议、尚未核实的事项**分开；任何数据都还没有完成本项目的许可与污染审计，不能将“候选”写成“已清洗可用”。

## 筛选结论

| 资源 | 对应用途 | 已声明许可 | 当前判断 |
| --- | --- | --- | --- |
| SWE-Gym / OpenHands-SFT-Trajectories | 修复与工具交互的短程起点 | 两张数据卡均为 MIT | 现成 491 条成功训练轨迹，适合小规模参考；仅 messages 的公开 schema 不利于来源追溯 |
| SWE-smith / SWE-smith-trajectories | 修复专家的主要候选池；原创 bug 构造 recipe | 数据卡与代码为 MIT | 有任务 ID、resolved 和模型字段，可分组筛选；三种 action 格式不能当三个独立数据集堆叠 |
| NVIDIA Terminal-Corpus / Skill-based Synthetic Tasks | 终端专家；科学计算工具轨迹的候选池 | CC BY 4.0 | 优先核 skill-based 分区；不能不经审计使用完整 adapters 大合集 |
| OpenR1-Math-220k | 科学推理专家中的数学部分 | Apache 2.0；上游 NuminaMath 1.5 同样声明 Apache 2.0 | 有验证状态与完整性字段，适合按 token 抽取；不能代表科学工具训练 |
| ScienceAgentBench | 科学工作流、自调试和程序化验证的构造方法 | 代码 MIT；多数任务 CC BY 4.0，存在原许可例外 | 推荐借鉴流程、另造独立任务；不建议将其受限制的整包数据直接当可公开再分发训练集 |

三个关键边界：数据卡的总许可不自动替代原始仓库/题目/论文材料的许可；未在 README 看到本题 benchmark 名称不等于无污染；在其他 Qwen 32B 上的结果只证明方法值得参考，不证明 Qwen3.6-35B-A3B 小预算 SFT 或合版一定受益。

## 1. SWE-Gym 与 OpenHands 成功轨迹

**事实。**`SWE-Gym/SWE-Gym` 数据卡说明其按 SWE-bench 的采集方式，从 11 个 Python 仓库构造 2,438 个训练任务，提供问题、仓库/commit、补丁与测试相关字段。这里仅核验 schema 与行数，没有读取这些字段的任务内容。固定 HF revision 为 `bb94ed9e39bbeb96a7fcbfb533b80f25a7fd59cb`（最后修改 `2025-05-10T03:27:03Z`），数据卡许可 MIT。[数据卡](https://huggingface.co/datasets/SWE-Gym/SWE-Gym/blob/bb94ed9e39bbeb96a7fcbfb533b80f25a7fd59cb/README.md)、[元数据](https://huggingface.co/api/datasets/SWE-Gym/SWE-Gym)

**事实。**现成 `SWE-Gym/OpenHands-SFT-Trajectories` 的 split 是 `train.success.oss`，491 条，公开 schema 为 `messages[{role,content}]`，数据卡 MIT；revision 为 `4aaa5a4a4b5861f4799d2336908760c190ac3b17`（`2025-05-10T03:26:28Z`）。官方复现文档确实用这些轨迹微调 Qwen2.5-Coder-32B-Instruct，但其主配置是 8 GPU 的全参训练和 32K 配置，不能将这套硬件与效果直接转述为四卡 LoRA 的已验证方案。[轨迹卡](https://huggingface.co/datasets/SWE-Gym/OpenHands-SFT-Trajectories/blob/4aaa5a4a4b5861f4799d2336908760c190ac3b17/README.md)、[固定代码中的复现流程](https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/docs/OpenHands.md)

**建议。**借鉴其“独立训练任务→真实 agent rollout→执行验证→SFT 消息”的路径；本项目优先抽取少量完整成功轨迹，而非先重新生成成千上万条。保留成功轨迹内部的定位、失败命令与恢复过程，不能只留下最终补丁。训练采用的 action 格式需与本项目固定 agent 对齐。

**未知/污染风险。**卡片没有证明它已针对本题 SWE Pro V2 HARD-51、HLE、ASI、TB2.0 逐项去污染。它来自经典 SWE-bench 采集体系，不等同于 SWE Pro 评测集；但必须再核 repo、issue、commit、文本与衍生关系。轨迹消息卡没有显式 `instance_id`，若无法从原始日志或可靠映射恢复来源，不宜把这491条作为“全部可追溯”的主数据。11个上游仓库的逐文件许可未在本次审计。

## 2. SWE-smith：可验证 bug 构造与现成轨迹

**事实。**工具的路径是为仓库建立可执行环境，合成任务，只保留能使至少一个测试失败的变更，再生成问题说明；README 许可 MIT。代码 pin 为 `9b74ac08118a85c39c356802f7961893af73e07f`（`2026-03-21T23:39:59Z`）。[固定 README](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/README.md)、[论文：SWE-smith: Scaling Data for Software Engineering Agents](https://arxiv.org/abs/2504.21798)

**事实。**任务数据卡 revision `ea6d7173829c7ec8fa16c22055699ff2e9188091`（`2025-12-14T19:30:19Z`）声明 MIT，元数据 train=59,136。正文仍写50,137，仓库 README 也有52K口径，因此复现应以固定 revision 的实际 manifest 为准，不抄营销概数。该单库已停止更新，作者建议使用 language-specific 发布；本次没有进一步审计各语言新库。[任务卡](https://huggingface.co/datasets/SWE-bench/SWE-smith/blob/ea6d7173829c7ec8fa16c22055699ff2e9188091/README.md)、[元数据](https://huggingface.co/api/datasets/SWE-bench/SWE-smith)

**事实。**轨迹卡 `SWE-bench/SWE-smith-trajectories` 声明 MIT，revision `08e109b4a59eaeebf80e4675cd125d42e7ac99a4`（`2025-07-19T01:18:16Z`）。schema 有 `instance_id`、`resolved`、`model`、`traj_id`、messages；元数据分别为 tool=24,100、xml=26,076、ticks=25,826，正文提到实际微调 Qwen2.5-Coder 的5,017条轨迹。它们是不同 action 形式与发布范围，不能将三份规模直接相加称为独立任务数。[轨迹卡](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/blob/08e109b4a59eaeebf80e4675cd125d42e7ac99a4/README.md)、[元数据](https://huggingface.co/api/datasets/SWE-bench/SWE-smith-trajectories)

**建议。**优先从一个 action 形式、可追溯任务 ID 的已完成轨迹构造修复池；按仓库与变更家族切 dev，再按实际 token、语言、修改范围及工具轮数抽样。若另外自造任务，可借鉴“先有可验证行为变化，再写任务说明”，在排除评测来源的许可明确仓库上生成，不能以 HARD-51 的补丁或隐藏测试作变更种子。

**未知/污染风险。**工具作者也是经典 SWE-bench 的作者，并不自动意味着任务是本题 SWE Pro 评测数据。反过来，MIT 数据卡也不证明每段上游代码均可忽略原许可；需要逐 repo 许可和四项 benchmark 来源去重。本次未读取 Parquet、任务补丁或测试，也未证明当前发布的去污染覆盖本题四项。

## 3. NVIDIA Terminal-Corpus / Terminal-Task-Gen

**事实。**完整 Corpus 数据卡许可 CC BY 4.0，revision `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`（`2026-02-27T22:37:57Z`）。作者报告约366K轨迹，分为约226K dataset adapters 和约140K skill-based synthetic；可分别选择 `dataset_adapters`、`skill_based_easy`、`skill_based_medium`、`skill_based_mixed`。[数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)、[分区元数据](https://huggingface.co/api/datasets/nvidia/Nemotron-Terminal-Corpus)

**事实。**独立任务环境发布为 `nvidia/Nemotron-Terminal-Synthetic-Tasks`，CC BY 4.0，revision `7e53648e183cee7bcb0aed623cc91a121d37fa38`（`2026-02-23T22:28:36Z`）。卡片描述 instruction、9种领域的共享 Docker 环境、pytest 检验，可检查文件、格式和数值结果；这张卡本身不是现成 rollout 卡，不应把任务包与轨迹包混称。[任务卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/blob/7e53648e183cee7bcb0aed623cc91a121d37fa38/README.md)

**事实。**论文 *On Data Engineering for Scaling LLM Terminal Capabilities*，arXiv `2602.21193v1`，`2026-02-24`，区分 seed-based 与 skill-based 生成；后者由技能分类组合原创任务，使用 Terminus 2 生成轨迹。作者明确先排除与 TB2.0 测试 prompt 有14-gram重叠的训练 prompt。adapters 的 SWE 上游包括 SWE-bench-Train、SWE-reBench、SWE-smith、SWE-Fixer-Train；不是单一、来源完全相同的数据集。论文并未把这些上游统称为本题的 SWE Pro V2-hard。[固定论文 v1](https://arxiv.org/html/2602.21193v1)

**事实。**论文在 Qwen3 8B/14B/32B 上报告 SFT 结果，并比较过滤、混合、上下文与规模。其设置中，success-only 或 complete-only 过滤差于 no-filter，单阶段混合也不差于两阶段课程。因此“成功轨迹才有训练价值”及“必须做复杂课程”都不能当作既定结论；这些是该论文条件下的自报结果。[同一论文的数据与消融章节](https://arxiv.org/html/2602.21193v1)

**建议。**终端专家优先审计并抽取公开 skill-based 轨迹，不直接使用整个 Corpus；科学专家可从其中 scientific_computing/data_science 补工具交互。独立开发集按技能组合模板与任务来源留出，不随机拆同一任务的重复rollout。若自造任务，只用独立技能组合和原创输入，不以TB题面、答案或隐藏测试作seed。四卡小预算可借鉴其共享基础镜像和简单混合设计；重新运行完整的大规模数据生成流程不适合作为当前短窗口的前置条件。

**未知/污染风险。**没有找到它公开声明将TB2.0题目答案直接混入训练；不能据benchmark名称相同就认定污染。其14-gram去重声明也不能证明语义改写、上游衍生或本题其他三项无污染。原始 prompt、论文来源、任务 ID 与 near-duplicate 仍需本项目检查；adapters 的上游许可没有在本次逐源审完。CC BY 4.0 分发需保留相应归属信息，不宜只写“开放数据”。

## 4. OpenR1-Math-220k 与上游 NuminaMath 1.5

**事实。**OpenR1 卡片许可 Apache 2.0，revision `e4e141ec9dea9f8326f4d347be56105859b2bd68`（`2025-02-18T11:45:27Z`）。其问题来自 NuminaMath 1.5，由 DeepSeek R1 生成2–4条推理；多数用 Math-Verify 验证，约12%用 Llama judge。每题至少有一条被判正确的轨迹，不代表每条 generation 都正确。元数据 default=93,733，extended=131,396，all=225,129；这是 configs 下的 train split，不能把default/extended误称为独立验证集。[固定数据卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)、[元数据](https://huggingface.co/api/datasets/open-r1/OpenR1-Math-220k)

**事实。**作者称 default 在其 SFT 设置下优于加入较简单 `cn_k12` 等来源的 extended；生成使用16K上限，卡片称不少问题超过8K。schema 提供 source、uuid、正确性、推理完整性和 finish_reasons 等信息，可在未来用于可复核筛选。[同一数据卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)

**事实。**上游 NuminaMath 1.5 卡片也声明 Apache 2.0，revision `1b05109f9e5c1ad06c0663519502416c30b300f8`；其来源包括竞赛官网、考试PDF、数学论坛，以及其他合成数学集合。上游卡片提供 source breakdown，但没有逐原始题目网站列出授权依据。[上游固定数据卡](https://huggingface.co/datasets/AI-MO/NuminaMath-1.5/blob/1b05109f9e5c1ad06c0663519502416c30b300f8/README.md)

**建议。**小预算优先核default中的可符号验证、完整、来源可追溯轨迹；每道题只选择明确正确的候选，避免同题多轨迹跨入train/dev。按数学领域、难度proxy与实际 token 分层，不强行截掉长推理尾部。用于科学专家的数学部分，不能把纯数学CoT当成已覆盖HLE全部学科或ASI科研工具。

**未知/污染风险。**两级卡片的Apache声明不证明所有原始论坛/PDF题目已逐题获得相同许可；需要保留来源并进一步审计。卡片没有针对HLE或其他本题任务提供可核验的完整去污染清单。即便发布日期较早，也不能排除共同上游题目；需按来源、题面精确/近似匹配筛查。没有证据支持“这批数据一定给Qwen3.6 MoE带来多少提升”。

## 5. ScienceAgentBench：仅借鉴科学工具数据的构造方法

**事实。**代码 commit `c26e151ed601ba109dc4d35e057ff8e73fec469d`（`2026-07-18T05:25:41Z`）的 README 描述102任务、44篇论文、四学科，输出为自包含Python程序；支持direct prompting、self-debug、OpenHands，以及执行结果/图表的检查。2026-04-30发布过verified版本。本次只读README，没有下载其benchmark包或读取gold程序与测试。[固定README](https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/c26e151ed601ba109dc4d35e057ff8e73fec469d/README.md)、[论文](https://arxiv.org/abs/2410.05080)

**事实。**代码MIT；大部分任务CC BY 4.0，来自rasterio与matminer的部分任务保留原许可。作者同时要求不要在线再分发解压的benchmark文件，并说明上游版权需尊重。因此不能把代码MIT写成整个数据包都可随意公开再分发，也不能直接将gold程序搬入公开训练仓库。[README的Licensing与Benchmark Access](https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/c26e151ed601ba109dc4d35e057ff8e73fec469d/README.md#licensing-information)

**建议。**借鉴“从可引用科学问题出发→明确输入和输出工件→数值/格式验证→保存自调试轨迹”的流程，在可再分发的小型科学数据或原创仿真数据上另造独立任务。这个来源提供方法参考，不作为本项目默认现成SFT训练池，也不能增加为本题的第五项正式评测。

**未知/污染风险。**它不是本题ASI-Bench，但是否共享原始论文、仓库或任务需要关联比对，不能用名称不同判定独立。没有在本次找到经过四项本题去污染、并可直接复用的该项目SFT轨迹发布。科学工具训练仍需从终端科学计算子集与独立新任务补齐，不能宣称现成数据已覆盖全部需求。

## 应用于当前方案的边界

- **优先级建议，不是最终选数决定：**修复优先审计有ID的SWE-smith轨迹，SWE-Gym作小型补充；终端优先skill-based；数学优先OpenR1 default；科学工具借鉴独立任务recipe并审计终端scientific_computing来源。不能直接把五个资源全部混合。
- **按token定预算：**先审计来源、格式、质量，再按固定tokenizer计算输入、监督输出和实际累计训练token；控制同题多rollout、跨格式复制和过长轨迹，不用原始样本数假定训练规模。
- **独立dev：**先按repo/issue/commit、题目uuid/来源、任务模板家族分组划分，再做变体与抽样；dev不从四项正式集抽取。合版和checkpoint选择只使用独立dev。
- **污染审计不使用答案：**可依据任务ID、来源、允许使用的题面指纹和近重复检查；本题参考答案、参考补丁、隐藏测试和正式评分反馈不进入训练数据、数据筛选或选checkpoint链路。执行验证仅针对独立训练任务。
- **尚未完成：**上述来源的逐行内容/上游许可证、完整污染检查、真实token统计、格式适配、当前机器可运行性和质量抽检。本文件不能替代未来的数据manifest与数据卡。
