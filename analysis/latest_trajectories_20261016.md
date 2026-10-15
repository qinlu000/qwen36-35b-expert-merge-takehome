# 近期强开放权重教师的公开训练轨迹：本项目候选

2026-10-16。按用户要求，联网查找比现有教师更新的真实公开轨迹，优先开放权重教师；将“数据公开”“教师开放权重”“适合本题”分别记录。仅阅读一手作者数据卡、文件索引/schema/元数据、论文和模型卡；未下载大数据、采集示范、运行模型/API/GPU、恢复val选题或执行清洗。以下是候选优先级，不修改既有data_sources.json或评测协议。

## 最值得先检查的升级

| 方向／来源 | 教师 | 公开内容与规模 | 当前判断 |
| --- | --- | --- | --- |
| Open-SWE v1.2 / mini | Qwen3.8-Flash-Next，Thinking | 36,577轨迹／PR，resolved17,807 | **修复域先审这一组**：3.65GB，体量较小；先核协议/长度/覆盖，不全量叠加 |
| Open-SWE v1.2 / mini | Qwen3.8-27B，Thinking | 107,267轨迹／41,405唯一PR，分布表resolved49,925 | 同为mini的大池补充候选；具体模板/工具/环境仍待逐项复核 |
| Open-SWE v1.1 / OpenHands | DeepSeek-V4-Flash-0731，Thinking | 50,295轨迹／32,660PR，resolved23,110 | 新教师真实多轮轨迹，但OpenHands多工具协议与当前mini不同，适配成本更高 |
| Nemotron-SFT-Math-v4 | DeepSeek-V4-Pro High | 545,431；其中CoT285,516、Python TIR259,915；参考答案匹配过滤 | **学术数学优先候选**，比旧OpenR1/R1教师更新；无工具HLE主线优先CoT，不能删tool观察后冒充原始无工具解答 |
| Nemotron-SFT-Science-v2 | 混合V4-Pro／V3.2／Kimi-K2／GPT-OSS，可按generation_model筛 | 作者卡称2,837,712；物理/化学/生物，CoT、Python、Tavily三种方式 | **科学推理优先候选**，必须筛教师及调用形态；并非全由V4-Pro生成，也不覆盖HLE全部学科/图像 |
| 新GLM5.2终端源 | GLM-5.2 | open-athena两个Terminus2命名数据仓库，文档/许可/来源与结果语义仍缺 | 有值得核查的新同harness线索，但尚未达到主训练池资格，不能只凭仓库名认证 |

Open-SWE计数来自已固定revision `1db674173119d71df45c22007af99e214600711a` 的[官方分布表](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)。**此前只下载v1.1 mini/Qwen3.6-27B，没有优先检查同revision里已公开的v1.2新教师候选。**本次纠正候选清单，不把未下载的新分区说成已经过本地审计。

已核Qwen3.8-27B与GLM-5.2均有官方公开权重仓库（Apache-2.0／MIT），DeepSeek-V4-Pro亦有官方公开权重；这不同于每条教师调用的精确权重revision已被证明。[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)、[GLM-5.2](https://huggingface.co/zai-org/GLM-5.2)、[DeepSeek-V4-Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro)。

resolved为发布方状态，不是本项目重新执行结果；多教师、多个harness的PR有交叉，轨迹数与成功轨迹数均不能直接当独立任务数或同条件教师通过率。

Math/Science的教师、数量和用法来自NVIDIA原卡：[Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4)、[Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2)。Math-v4量为完整发布计数；Science卡片总量与Hub partial viewer口径不同，未全量读取核实，不能以viewer预览行数冒充真实筛后数量。只有核到逐行teacher和模式后，才能给本次最终可用量。

## 终端与科研执行仍有缺口

- **OpenThoughts-Agent-SFT-100K**：公开100K、GLM-4.7-AWQ、Terminus-2/Daytona，带result，比此前“OpenHands备选”的概括更接近本题终端协议；但教师不是本轮最新一代，也未证明同预算强于Base。可作为透明度更高的终端候选。[原卡](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K)
- **AllenAI TMax SFT**：当前公开thinking_all为10,726条、成功子池5,795条，教师Qwen3.6-27B，任务可独立恢复的证据较好（论文描述生成阶段约16.5K／8K，不能冒充当前下载量）；采集是persistent bash，并非Terminus JSON/tmux。名字含terminus的社区重包也不自动改变动作语义。[原始训练数据](https://huggingface.co/datasets/allenai/tmax-sft)、[论文](https://arxiv.org/abs/2606.23321)
- **GLM-5.2 coding/debugging**：有作者公开的可验证新教师下一动作训练视图；Pi工具协议包含read/edit/bash等，与mini不同；派生prefix行数不能当独立完整轨迹数。只列备选，不因教师新就替换主harness。[原始数据](https://huggingface.co/datasets/greghavens/glm-5.2-coding-and-debugging-traces)
- **DeepSeek-V4-Pro agent数据**：确有公开工具/会话数据，但r0b0tlab源以自定义函数工具及单轮任务为主，TeichAI源是Pi会话，成功标签或许可信息仍不足；都不是现成Terminus-2主池。数据卡的replay声明不等于本项目已复验。[r0b0tlab](https://huggingface.co/datasets/r0b0tlab/deepseek-v4-pro-0813-agentic)、[TeichAI](https://huggingface.co/datasets/TeichAI/DeepSeek-v4-Pro-Agent)
- **ASI direct_llm**：新Science Python工具问答不等于单次完整科研程序及声明产物。当前未核到一个同时满足新强教师、公开完整程序/执行验证、来源可追溯、与ASI产物契约接近的全替代池；较小生态程序等来源只作补充候选，不能把质量分当执行成功。

## 不因新教师而降低数据资格

1. 排除本题四项正式任务、其答案/产物/重标注与同源派生。Qwen3.8在TB2 easy25的压缩研究日志、GLM5.2在TB2.1的89题日志虽然新且协议接近，但含正式终端任务，不能拿来训练。SWE Verified等其他评测日志则应按与本题Pro的ID/repo/fork/PR关联审查，不仅凭eval身份一概禁用，也不默认独立。
2. 先跨新旧教师、harness和任务包联合按任务族分组，再固定独立val，再从剩余池选train；不能把同PR换teacher的另一条放train。
3. 核动作/观察/状态/结束、环境初始化、权限和依赖；同名harness只是较强入口证据。Pi、OpenHands、Python/Tavily与mini/Terminus/direct程序不可仅改role字段冒充等价。
4. 保留上游/逐行许可与归属；Science-v2等CC BY-SA的条件不同于旧来源，不能套用一份总许可。未知来源/许可、标签冲突和模板异常单列。
5. 更新数据后先按固定Qwen3.6模板重新核长度、源教师显式thinking及监督mask。新教师多数Thinking；已有“删教师思考”决定仍处执行暂停，不能将去掉推理正文视作无损或自动匹配非思考学生。

## 建议次序

先审Open-SWE mini/Qwen3.8-Flash-Next的小份结构与安全元数据，再按覆盖需要核27B分区，优先于换OpenHands或Pi；学术侧优先审NVIDIA Math-v4与Science-v2的指定教师及无工具子池。终端保留原候选，同时核新GLM5.2/Terminus源的基本资料；科研执行不为了追新教师丢掉可执行验证与程序产物契约。

没有找到“新教师＋现成成功轨迹＋全部目标harness匹配＋四项均已去污染”的一站式替代池。现有新候选足以重新比较数据来源，不需要立刻重跑整池教师或增加训练分支。最终配方仍由独立val与资源预算决定。

专项：[SWE](latest_trajectories_swe_20261016.md)、[Terminal](latest_trajectories_terminal_20261016.md)、[科学/学术](latest_trajectories_science_20261016.md)。
