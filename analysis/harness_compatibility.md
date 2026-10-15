# 训练轨迹与目标 harness：实际兼容性检查

日期：2026-10-16（上海）。本轮检查固定版本源码、已下载独立训练记录和自造解析/模板样例；没有执行轨迹中的命令、启动模型或正式任务，也没有读取正式题答案、参考补丁或隐藏测试。结论是数据使用建议，不是训练验收或正式协议冻结。

## 结论与当前取舍

不需要为了 harness 名称不同重跑全部 teacher。SWE 和 Terminal 已有较强的行为协议接近证据，经过必要规范化后可作为主训练候选；D3 现成内容适合辅助科研程序 SFT，尚不能充当 OpenCode 多轮执行示范。仍没有最终可直接开训的 manifest。

| 方向 | 实际检查得到什么 | 可复用方式 | 仍需处理 |
| --- | --- | --- | --- |
| SWE / Open-SWE → LockedMiniSwe | 39分片分层检查624条，37,024次调用均为单个bash(command)，观察为JSON，与目标同族 | 规范化JSON arguments与空字段；非终止单调用可根据严格相邻顺序恢复返回关联；保留源任务上下文训练 | 源提示额外要求patch.txt及echo后cat补丁，不能盲换目标prompt；末尾提交无工具结果不应伪造结果；分组去污染、长度/监督mask与目标端点仍待验 |
| Terminal / Corpus → Terminus-2 | 26分片共139,841行元数据；260条有界结构样本，动作、持续终端和观察模板同族 | 将额外teacher think与实际动作JSON分开；使用原生parser标注动作可解析性，保留协议字段 | 2,058条采样assistant消息去显式think后1,930条可解析，128条仍报错；不能整池不筛选直接监督，也不能将可解析率当成功率 |
| ASI / D3 → OpenCode | D3只有instruction/input/output；OpenCode实际使用多轮工具调用与返回 | D3可作为静态科研推理/程序辅助数据；真实交互缺口在独立任务上补采 | 缺少工具调用、观察、错误恢复；当前OpenCode自定义模型还未声明图片输入，需修正能力声明并验收图片工具回路 |
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
4. D3暂不冒充OpenCode轨迹；先恢复少量独立科研任务，真实记录工具调用和反馈。图片能力声明按固定OpenCode源码修正并做自造图片读工具端点检查，暂未更改当前运行配置。
5. 由实际Base独立dev和净可用数据量决定补采比例；不为了版本名全量重采，不把解析或模板通过写成执行成功。本轮未开始SFT、正式全量Base或大规模teacher采集。
