# 训练轨迹与目标 harness：实际兼容性检查

> 后续决策（2026-10-16）：ASI已在[协议v2](evaluation_protocol.md)选择官方`direct_llm`，不再处于OpenCode/direct_llm待选状态；下文两路线比较与旧数据统计保留为当时证据。正式harness清单和接线状态见[对齐记录](protocol_alignment_20261016.md)。

日期：2026-10-16（上海）。本轮检查固定版本源码、已下载独立训练记录和自造解析/模板样例；没有执行轨迹中的命令、启动模型或正式任务，也没有读取正式题答案、参考补丁或隐藏测试。结论是数据使用建议，不是训练验收或正式协议冻结。

## 结论与当前取舍

用户明确以训练—评测环境及harness一致性为主训练数据资格前提，详见[sandbox方案约束](trajectory_sandbox.md)。SWE和Terminal现有行为协议接近证据，只支持优先核验；还须通过sandbox和交互协议验收才进入主训练清单。题面允许范围内优先按轨迹选择同源评测harness，不固守此前候选实现；该项正式Base前确定并冻结。D3尚不能充当OpenCode多轮示范，但已有更接近其静态程序监督的官方direct_llm可复用候选，故不预先限定其只能辅助。仍没有最终可直接开训的manifest，清洗/重采取舍以一致性要求为先。[环境构建与代码复用盘点](harness_reuse.md)

| 方向 | 实际检查得到什么 | 可复用方式 | 仍需处理 |
| --- | --- | --- | --- |
| SWE / Open-SWE → LockedMiniSwe | 39分片分层检查624条，37,024次调用均为单个bash(command)，观察为JSON，与目标同族 | 规范化JSON arguments与空字段；非终止单调用可根据严格相邻顺序恢复返回关联；保留源任务上下文训练 | 源提示额外要求patch.txt及echo后cat补丁，不能盲换目标prompt；末尾提交无工具结果不应伪造结果；分组去污染、长度/监督mask与目标端点仍待验 |
| Terminal / Corpus → Terminus-2 | 26分片共139,841行元数据；260条有界结构样本，动作、持续终端和观察模板同族 | 将额外teacher think与实际动作JSON分开；使用原生parser标注动作可解析性，保留协议字段 | 2,058条采样assistant消息去显式think后1,930条可解析，128条仍报错；不能整池不筛选直接监督，也不能将可解析率当成功率 |
| ASI / D3 → 待选生成/执行harness | D3是静态程序；官方direct_llm为一次生成后真实执行，OpenCode为多轮工具 | 优先比较D3+direct_llm的匹配路线与OpenCode路线；选择OpenCode时D3仍作程序辅助 | direct_llm需生成参数/总deadline接线且无多轮与模型图片观察；OpenCode需工具过程数据。图片能力声明已由环境工作流补齐，真实端点仍未验 |
| HLE / 学术QA → 固定问答客户端 | 无终端状态协议；自造Explanation/Answer/Confidence和图片占位符可渲染 | 保留可见解释与答案，按选定thinking配置处理发布的teacher推理 | 文本QA不自动补齐图像能力；原题来源/答案质量与真实图片HTTP通路仍待验 |

SWE样本按分片、语言和上游resolved标签确定性选择，Terminal为每片前10条；二者都不是随机质量抽样，不能外推整库错误率或模型成绩。源码与统计详见[SWE](harness_compatibility_swe.md)、[Terminal](harness_compatibility_terminal.md)、[ASI/HLE](harness_compatibility_asi_hle.md)。

目标原生逻辑另做了mini解析/观察/完成检测19项和Terminus parser 9个独立合成检查。Terminus parser有容错：缺duration可补默认值，完成=true时坏command也可能被丢弃后接受；因此“parser无error”不能单独充当严格数据资格规则，需要同时核warning和实际保留动作。

## 两道具体 Terminal 题已有同题记录，但不代表成功示范

上次介绍的游戏日志 `data_processing_task_0459` 和N体仿真 `scientific_computing_task_0939`，均在mixed相应分片找到同ID记录；剥离明确固定的首轮提示wrapper后，题面SHA256与任务包完全一致。它们分别有4、6条assistant消息，去显式think后的动作均能被目标parser解析，但都没有task_complete=true，不能作为已经验证成功的完整轨迹。

全量task列中，任务包5,984个ID都在Corpus某处出现，匹配18,778行；这个数量不是完成的逐题环境映射。不同difficulty存在ID复用：260样本中84条ID命中，只有60条题面一致，且这60条均来自mixed。因此不能只按task_id跨difficulty拼任务和轨迹，更不能将任务包与Corpus分开随机划分train/dev。

## Qwen非思考模板的确定性问题

用固定Qwen tokenizer/template在CPU运行了6个完全自造序列（mini工具、Terminus JSON、学术问答，各原样/显式移除外层推理两版）及生成前缀检查。全部断言通过，模板SHA256为 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。

**enable_thinking=false和preserve_thinking=false不会自动移除训练样本中的全部推理。** 固定模板仍会保留最近真实user请求之后assistant的reasoning_content或外层think内容；enable_thinking=false控制追加生成前缀。若最终选择非思考SFT，必须显式处理数据发布的teacher推理字段，不能只依赖模板开关。

同时必须区分：Terminus JSON的analysis/plan是模型可见动作协议字段；HLE的Explanation是可见回答要求。显式移除额外think时应保留这些内容。自造序列中已确认JSON的analysis/plan两次均保留，不需要把非思考模式解释成“只保留答案”。缺失/不平衡think分隔符和实际数据变体仍需按格式单独标注，不能用自造样例转换器宣称全库可安全转换。

脚本：[check_trajectory_template.py](../scripts/check_trajectory_template.py)；无正文结果：[trajectory_template_20261016.json](source_snapshots/harness/trajectory_template_20261016.json)。这只是HF模板证据，不代替ms-swift训练模板/监督mask或vLLM工具端点的端到端验收。

## 接下来按什么规则筛选

1. 先按原任务/仓库/模板族跨任务包和轨迹联合分组，排除正式评测同源，固定dev；Terminal同ID不同题面不能自动合并为同一个可执行环境。
2. SWE保留可核的单调用链与源上下文，完成序列化规范化；不编造末尾工具结果，也不直接覆盖源prompt。Terminal保留合法动作结构，将未解析消息和终局未知单列；错误恢复可保留为上下文，是否监督错误动作需在训练配方中明确。
3. 若采用非思考设置，显式规范化外层teacher推理；保留工具协议的analysis/plan和可见Explanation。按完整交互边界处理长度，核processed/supervised token与loss mask，不硬截断JSON动作。
4. D3不冒充OpenCode轨迹；先比较官方direct_llm与OpenCode代码复用和数据匹配，再冻结ASI路线。若选多轮执行，再恢复少量独立科研任务补真实工具过程；若选direct_llm，补生成参数/总deadline与产物接线。真实文本/图片/工具端点按所选路线验收。
5. 由实际Base独立dev和净可用数据量决定补采比例；不为了版本名全量重采，不把解析或模板通过写成执行成功。本轮未开始SFT、正式全量Base或大规模teacher采集。

## 清洗还是重采：先分清环境差异

用户进一步指出运行环境不同可能导致SFT迁移差。这一风险成立；上述格式/parser检查没有证明运行环境兼容，也不证明SFT会提升。仓库、输入数据、任务特定依赖在train/test间不同是预期的泛化问题，不要求把训练任务放进正式测试任务镜像。真正需要核的是工具动作/观察/状态、可用命令和权限、联网策略、资源与超时、图文可见性及产物/提交契约。训练时依赖联网、sudo、不可见文件或不同shell状态才能成立的轨迹，可能教会目标环境无法执行的策略。

[Open-SWE-Traces论文4.1及表5](https://arxiv.org/html/2606.16038v1#S4.SS1)确实观察到跨harness下降，支持重视交互分布差异；其旧版本数据、Qwen3-30B、OpenHands/SWE-agent与本项目mini/Qwen3.6/LoRA不同，不能将具体跌幅外推本项目。作者的跨框架迁移也表明来源框架不同不等于数据无用。当前固定Terminal数据卡把skill-based合成环境轨迹用于Terminal-Bench能力训练，不能据此认定本次下载子集均已通过项目验收：[固定数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)。

因此主路线是“小批清洗与环境验收并行，兼容来源扩大复用，确定缺口定向重采”。先选每类2–3个来源明确的独立工具任务，恢复其自身正确初态/依赖，在目标工具、权限、网络与该类预算政策下检查真实动作和产物；这只是工程smoke，不估整体成功率，不使用正式测试题。若环境不可恢复、依赖目标禁止能力或动作/观察语义无法保持，就排除该部分或在正确训练环境和目标harness下真实重采，不伪造旧观察。

实际回放只能证明任务/轨迹在受检环境下的执行性质；迁移收益还要在互斥独立dev上用相同配置比较Base与SFT checkpoint。SWE/Terminal目前优先验收现成轨迹；ASI静态程序缺真实多轮工具反馈，更优先定向补采；学术QA保留现成可核解答。清洗全池和重采全池均不是当前第一步；没有根据已下载规模或单个Rich试点承诺净数据产率，也不预设固定自采比例。

## 补查轨迹介绍与sandbox资料

后续已按用户要求查轨迹数据卡、作者论文、上游环境字段和任务构建文件，见[sandbox来源报告](trajectory_sandbox.md)。SWE上游确有镜像/commit/cwd/初始化配置可供恢复；Terminal mixed六包提供Ubuntu24.04/Python3.12及逐题输入，打包默认资源不等于教师运行覆盖；D3论文明确保留环境内silver判分通过的2,153条32B程序。不能将缺少逐条runtime字段说成完全没有环境或验证信息，也不能用上述信息声称原collector政策已复原。任务初始化、精确版本、权限/网络及目标运行器差异仍须独立验收；不需要为离线SFT先启动或全量重放所有sandbox。
