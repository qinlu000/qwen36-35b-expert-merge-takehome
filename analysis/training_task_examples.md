# 已下载训练任务：四个真实题面示例

更新：2026-10-15。本文用于介绍已下载候选池，**四个例子均未选入train或val**。只读取了4条独立训练任务的题面及指定来源字段；没有读取参考patch、测试内容、solution、eval_script或答案，没有运行任务、模型API、训练或拉取镜像，也没有开始构造训练数据。

读取范围：SWE只检查instance_id/repo/problem_statement；Nemotron只枚举tar成员并在内存读取两份instruction.md，没有解压整包；D3只检查task_id/task_instruction/original_repo/discipline。评分器状态均应区分“发布/结构存在”和“实际运行通过”。

## 1. 仓库修复：修复webargs的Tornado请求解析

- 来源：[SWE-smith-py固定发布](https://huggingface.co/datasets/SWE-bench/SWE-smith-py/tree/77cab9055d42ab4a5c25c89a8f937096db13558e)，revision `77cab9055d42ab4a5c25c89a8f937096db13558e`。
- 文件：`data/train-00002-of-00011.parquet`。
- instance_id：`marshmallow-code__webargs.dbde72fe.combine_module__sx939qbe`。
- 原始repo字段：`swesmith/marshmallow-code__webargs.dbde72fe`；字段和instance_id中的原仓库名为`marshmallow-code/webargs`，不在本题SWE Pro的11仓库排除表。完整fork/改名映射尚未审计。

**给模型什么：** 一个已经出现回归的webargs代码仓库初态，以及Tornado解析器读取HTTP请求参数时出错的说明。题面覆盖query、form、JSON、headers、cookies，并给出最小复现示例。

**要产出什么：** 定位并修改解析实现，在仓库中留下代码修复；最终评估对象是修改diff及其测试行为。训练若要目标mini轨迹，还需真实记录读文件、复现、编辑和验证的动作/返回结果，不能把参考patch直接变成假对话。

**任务性质与评分证据：** 真实开源仓库上的合成bug修复，不应称作直接采来的真实GitHub issue。Parquet结构有FAIL_TO_PASS/PASS_TO_PASS与image_name字段，SWE-smith发布环境profile；本次没有读测试列表值或patch，也没有启动镜像或实跑验证，尚未证明该例可恢复且验证有效。

## 2. 终端数据处理：游戏事件日志清洗与行为汇总

- 来源：[Nemotron Synthetic Tasks固定发布](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/tree/7e53648e183cee7bcb0aed623cc91a121d37fa38)，revision `7e53648e183cee7bcb0aed623cc91a121d37fa38`。
- 包：`skill_based/mixed/data_processing.tar.gz`。
- task_id：`data_processing_task_0459`。
- 读取成员：`./data_processing/data_processing_task_0459/instruction.md`。

**给模型什么：** 一个终端环境及游戏事件JSONL文件，事件含玩家、时间、事件类型、武器和地图。要求过滤缺失玩家、无效时间与非法事件类型，并处理部分字段缺失。

**要产出什么：** 玩家session汇总JSON与武器统计CSV。相邻事件间隔超过5分钟时划分新session；统计击杀、使用武器、地图与单位时间指标，并满足指定路径、schema和排序要求。

**能力对应：** 从任务说明读取数据格式，写清洗/聚合脚本，检查结果文件与边界条件，适合交互执行专家的终端工作流。这是合成应用场景，不声称输入来自真实游戏生产日志。

**评分证据：** 该任务包已有Harbor形态instruction/task.toml/environment/tests目录，先前结构审计确认有test.sh/test_outputs.py；本次没有读取或运行测试。题面列出的成功标准只是题面要求，不代表评分器已经被我们验证。

## 3. 科研执行：多进程N体引力仿真

- 来源：同上固定Nemotron发布。
- 包：`skill_based/mixed/scientific_computing.tar.gz`。
- task_id：`scientific_computing_task_0939`。
- 读取成员：`./scientific_computing/scientific_computing_task_0939/instruction.md`。

**给模型什么：** 仿真参数JSON，指定粒子数、时间步数、时间间隔、引力常数、软化参数和随机种子。题面还规定初始化、数值更新与multiprocessing分工方式。

**要产出什么：** 定期粒子状态和能量统计的trajectory.json、能量曲线PNG，以及包含守恒误差、墙钟时间和性能指标的摘要文本。

**能力对应：** 将数值方法写为可执行程序，读配置、并行计算、保存数据和图像、检查数值性质。它比普通shell文件操作更接近科研执行，但不等于覆盖ASI全部研究任务。

**评分证据及待审问题：** 包内有环境和测试结构，尚未运行。题面同时要求特定力公式/积分、能量误差阈值与优于朴素串行的性能；后续需检查数值定义与判据是否一致、性能门槛是否依赖机器。这是候选质量审计问题，不能未经执行就断言该例可靠、可解或适合有限CPU预算。

## 4. 科研数据分析：分子键级计算与可视化

- 来源：[D3-Gym固定metadata](https://huggingface.co/datasets/osunlp/D3-Gym/tree/8499689ac98882a7cac9b5ef9e93365cc37df57e)，revision `8499689ac98882a7cac9b5ef9e93365cc37df57e`。
- 文件：`data/train-00000-of-00001.parquet`。
- task_id：`task_1`。
- original_repo：`fenggo/I-ReaxFF`；discipline：Chemistry。

**给模型什么：** 题面要求基于IRFF方法分析分子结构；实际分子输入和预装依赖位于另行发布的任务环境，当前只下载metadata，未读取/恢复镜像内容。

**要产出什么：** 计算原子对键级，按阈值识别化学键；输出分子结构PNG/SVG、包含原子索引/元素/键级的CSV，以及坐标、元素组成和晶胞向量等结构信息文本。

**能力对应：** 使用现成科学代码和输入数据，产出可检查的数值表与科研图像。任务由真实科研仓库衍生，不应将自动构造的任务说明说成该仓库维护者真实提出的issue。

**评分证据：** D3 metadata schema有eval_script字段，发布README描述Docker内置参考输出与run_and_eval；本次没有读取eval_script、gold或程序答案，没有拉镜像、实跑评分。原仓库许可仍待筛查，未据数据卡MIT自动批准它进入train/val。

## 本轮做了哪些排除，尚未证明什么

读取前先检查 `configs/data_exclusions.json` 的SWE Pro全部11个正式来源仓库；SWE例子的原始镜像repo名及明显的原仓库标识均未命中。随后与 `analysis/source_snapshots/protocol/` 四份正式manifest中的2700个唯一task/question ID逐一做exact比较，以上4个例子均未命中。

这个检查只排除同ID和可见来源名，**不证明语义去污染、fork/改名、共同上游任务或模板族隔离已经完成**。Nemotron任务池可能和已下载Corpus轨迹同源；D3现有trajectory又缺task_id映射。后续train/val必须跨这些资产联合分组与排除，不能简单按文件或行随机切分。

这些例子说明已有任务内容、输入输出契约和验证入口候选，不再需要先从零大规模造题。接下来应先做来源/许可和联合分组，留出dev，再选择少量独立任务恢复环境并验收评分器；通过后才决定teacher采集和正式SFT配方。此处没有选最终任务、采示范或改变正式评测集。

## 下一步顺序

1. 停止扩充大任务池，先按来源仓库、原任务和模板族跨任务包/旧轨迹联合分组，排除正式评测同源并预留独立dev。候选小dev为仓库修复10、终端10、科研10、学术问答40；规模待实际耗时确认，不修改正式全量测试集。学术问答另从已有OpenR1/OpenScienceReasoning候选中审来源、答案与学科覆盖，不能用软件任务替代HLE训练。
2. 每类工具任务先取2–3个低依赖、可机械验证的独立任务，恢复输入和环境、核验评分器；上述四例只用于介绍，不自动入选。N体性能门槛和D3化学环境/许可尚未核准，不优先承诺它们可跑。工程核验不另建一套大选模集。
3. 优先完成实际Base服务的GPU加载、HTTP工具/图片回路，以及容器资源/隔离与HLE、ASI Judge链；依实际运行版本对齐并冻结各项协议。已安装环境和CPU自造检查通过不等于真实模型端到端已验收。先取得独立dev的Base诊断结果，各正式benchmark就绪后分别启动全量Base，不把四项全量全部返回设为所有准备工作的硬前置。
4. 按独立dev发现的能力缺口采teacher：SWE走选定mini工具协议、终端走Harbor/Terminus-2、科研走选定ASI执行工具协议。保留真实动作、工具观察和独立判分，按净可用token吞吐、成功率、长度和覆盖率决定自采与旧轨迹比例；不将参考patch/答案改写成虚构工具对话。训练集和dev对应的所有旧轨迹共同排除；正式题答案和失败派生示范不回流训练。
5. 数据配方锁定后做ms-swift LoRA SFT的三个专家及同预算混训对照；独立dev比较AVG/TIES候选并选单一合版，随后完成题定最终评测。四卡推理和SFT按真实吞吐分时，不先承诺尚未测出的训练/全量评测耗时。

近期可验收产物是：一份隔离后的独立dev清单、真实Base服务及首批dev结果、少量目标工具协议下经验证的示范。当前没有开始大规模teacher采集、正式SFT或正式全量Base。

## 是否已有训练轨迹

任务包和现成轨迹是两批资产。2026-10-15介绍时四个例子尚未逐题匹配；2026-10-16的[实际兼容检查](harness_compatibility.md)已找到日志和N体两例题面SHA256完全相同的Corpus记录，但它们没有完成标记或grader结果，不能称为完整成功示范。SWE和D3具体例子仍未关联。无需因此将整个训练池重新运行。

| 已下载内容 | 原始条数 | 实际监督形态 | 是否必须重跑全部teacher |
| --- | ---: | --- | --- |
| Open-SWE mini/Qwen3.6 | 95,291 | assistant/tool多轮修复消息，含bash调用和返回；这不是上文SWE-smith任务包的逐题配套证明 | 不需要；先筛来源、标签、消息完整性并适配目标协议 |
| Nemotron Terminal-Corpus skill-based | 139,841 | Terminus-2谱系的持续终端JSON动作及观察对话 | 不需要；日志/N体两例现有同题过程记录但终局未知，全量跨发布映射及dev排除仍未完成 |
| D3-Gym-Trajectories Qwen3-32B | 2,153 | instruction/input/output，含推理与最终程序；没有独立多轮工具返回 | 静态程序SFT可复用；若需要ASI执行协议下的多轮示范，需选任务真实补采 |
| OpenScienceReasoning-2 / OpenR1 default | 1,600,812 / 93,733 | 学术/数学问答及推理解答 | 不需要重新生成全部答案；先做来源、质量与模板筛选 |

SWE-smith Python/Go任务包本身无messages；作者另有SWE-smith-trajectories发布，但未核准上述具体例子与该发布的关联，不把它报作本次已下载的修复主源。上述数量均为固定文件的原始记录数，不是已去重合格样本；没有一批已通过本项目完整训练验收。

在当前时限下，优先验收并复用现成轨迹，独立任务用于dev和明确短板的少量补采。自己必须执行的是Base/dev评测、新增teacher轨迹及选中环境/评分器的验证；使用现成SFT数据不要求全量重演其teacher过程。最终自采比例仍取决于可用量、协议适配和真实产出速度。
