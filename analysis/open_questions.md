# 待集中讨论的问题

更新：2026-10-15。用户已授权按当前方向推进，问题先记录、之后集中讨论。本表只列真实缺口及建议，不把工程偏好写成题面新增硬要求；不因这些问题停止可独立开展的数据/工程准备。

## 优先处理

| 优先级 | 问题与已核事实 | 影响 | 建议与待讨论点 |
| --- | --- | --- | --- |
| P0 | Base四项尚无正式运行；80只有13MB元数据，HPC常见缓存未发现准确完整checkpoint，真实Qwen图文/tool端点、容器与最终协议均未ready | 当前不能直接宣称已启动或可一键全量；正式Base若用未冻结设置可能重跑 | 优先协议草案+独立任务通路，启动前冻结；独立dev的Base诊断指导训练配方，正式Base按项ready尽早全量，不等四项全完；CPU准备并行，四卡分时，详见base_first_readiness.md |
| P0 | 用户提出所有任务30min、最多4CPU；TB原题明确3h/32CPU，所有模型同配置也不能自动覆盖该条。SWE题面未写死50min，但所选官方locked protocol为50min | ASI可预冻30min/4CPU；SWE30min是自定义预算实验；TB30min/4CPU偏离题定配置 | 开发可用短预算；正式TB保留题定配置，若要替代需先确认面试方接受。SWE现有1CPU已满足最多4CPU；HLE资源为共享客户端，详见budget_30min_4cpu_review.md |
| P0 | TB有效并发未落实：HPC formal-user192CPU、现有作业占12；80可见128逻辑CPU且共享。9路仅为满额容量情景且未获保障；Docker limit不独占，但仅填32CPU也不足以证明共享争用下实际资源一致 | 若均值30min/trial，1335次在9路约74.2h，36h需约19路有效并发；均非实测，不能由CPU除法断定最大并发 | 完成后端，独立dev测4/8/16路CPU/RSS/I/O/模型队列；各模型固定政策、合法配额，保留32CPU/48GB、任务与五次 |
| P0 | 80未找到可用Docker/Podman/Apptainer等后端；HPC有Singularity4.1.5和可读SIF，但尚未验证官方任务语义 | 正式容器与隔离链路未ready；ASI seed42官网要求Docker os来源 | 决定已有组内容器服务、项目rootless路径或HPC合规后端；先做自造CPU环境验证。暂不擅改官方环境或用户系统 |
| P0 | ASI固定评分需要GPT-5.5并含视觉判分；已发现80 HKUST key且Luna图文小探针可调用，当前模型列表无GPT5.5 | Luna是可用替代候选，原GPT5.5仍未提供；图像探针2/3，需独立科学校准，不能称原Judge等价 | 原scorer暂不改；固定/校准并披露替代Judge或落实原模型；已核三模型396槽、ASI初始预算50元，详见hkust_judge_budget.md |
| P0 | ms-swift已明确注册准确模型，但完整项目训练栈和4H100加载/反向/导出尚未跑通 | 8h训练/6M processed token仍是预算，不是实测保证 | 用项目独立环境复用可用依赖，再以自造数据做短smoke和真实8K吞吐检查；不修改其他项目环境 |
| P1 | ASI seed31415本地score被官方文档称non-official，seed42官网路线需Docker os/Portal。当前暂定公开60×4 | 题目“官方主指标”可指官方实现指标，但不得混称官网榜单成绩 | 集中确认可复现本地官方实现是否满足提交口径；若要求Portal再切换明确路线，不擅自替换split |

## 数据与协议

| 优先级 | 问题与已核事实 | 影响 | 建议与待讨论点 |
| --- | --- | --- | --- |
| P1 | 现成独立任务包已下载，Rich单题子代理操作记录已通过窄范围重放；包内环境与目标harness未恢复，批量真实CPU吞吐/净产量未测 | 净数据产量可能远少于attempts，不能用API便宜或已下载沉没成本决定路线 | 先按源任务分组留val，小批自采测净token/h；优先现成任务并联合隔离既有同族轨迹；SWE/D3 gold仅评分侧，Nemotron与Corpus不能独立随机切；详见ready_task_catalog.md、fresh_trajectory_feasibility.md |
| P1 | 消融用独立dev尚未构建；轨迹留出只有loss用途，有初始环境/独立验证器才能测执行。Terminal无统一success，OpenScience/D3有来源/金标准映射缺口 | 不能直接将随机轨迹行当可执行评测集，也不应反复抽正式benchmark调参 | 建议val-loss100K processed token+独立task-dev10修复/10终端/10科研/40QA；先按原任务家族隔离，优先复用独立可执行任务、补少量原创，冻结候选/预算/指标，详见dev_ablation_plan.md |
| P1 | 真实tokenizer下两条Terminal完整轨迹21,174/29,685 token；两条Open-SWE规范化后40,320/18,933 token | 原8K整轨迹方案不能直接截尾，可能丢观察、状态或最终提交；样本仅各2条，不能外推分布 | 讨论完整短轨迹与逐assistant回合窗口的组合、必要历史和loss mask；真实长度分布后再锁长度/token配额，不重采整池 |
| P1 | Terminal没有逐行resolved/result，2条结构样本未见task_complete=true；Open-SWE有成功/失败/未知标签 | 不能把全部轨迹写成验证成功，也不能从2条推断整库失败 | 按可追溯元数据定义质量选择，保留有用纠错过程；先明确终局未知如何标注，不伪造success |
| P1 | Open-SWE同repo/instance多轨迹重复；全39片95,291行对应39,540个不同(repo,instance_id)组合；详情见artifacts/data/audits/swe_metadata.json | 随机按行切dev会泄漏同任务；exact repo排除不覆盖fork、改名、PR同源 | 按canonical repo+instance/PR任务族联合分组去重；11个SWE Pro repo排除规则已保存，后续补fork/lineage |
| P1 | D3实际仅instruction/input/output，没有task_id、repo、逐行license或成功字段；OpenScience仅input/output/expected_answer | 无法仅凭总数据卡许可完成逐条来源过滤；现成D3不是OpenCode多轮数据 | D3暂作科研程序候选，来源映射前不宣称完成许可/ASI同源清洗；OpenScience保留固定行/hash及recipe，说明溯源局限 |
| P1 | ASI推荐内置opencode_cli可接自部署Qwen；采样/总token/步数、thinking replay、host HOME隔离未实际核实 | 同一benchmark预算与多轮协议不能只靠CLI默认值保证 | 固定OpenCode版本后用自造文件任务检查调用和产物；明确预算与隔离，不为D3静态数据选择单次生成替代主agent |
| P1 | HLE自造图文processor已过；DeepSeek判分JSON mode第一版漏strict，明确完整例子后8/8通过 | processor成功不等于模型图文服务；合成8例不等于科学题校准或官方Judge等价 | 仍需真实模型HTTP图文/usage检查；DeepSeek若用于主结果，明确为本实验Judge并扩展独立样例校准，不能依据正式HLE反馈改prompt |

## 已解决或已有明确路径

- 原四组候选数据全部81文件/约25GB完成下载与完整性校验，失败0；D3 32B额外小池也完成。最终文件完整性以download_receipts.json为准，不把落盘部分或格式检查当成训练质量通过。
- Open-SWE和Terminal有限实际样本的关键动作/观察协议与mini/Terminus2方向吻合，不必为框架名称重采全部轨迹；真实状态语义仍按数据规范处理。
- 80→Mac双SSH→HPC已知计算节点的TCP桥接实际通过，临时隧道全部清理；尚未证明模型HTTP、流式响应或长期稳定。
- 固定基座的本地tokenizer及图文processor可加载，HPC Torch/Transformers/PEFT及准确架构config的CPU导入也已通过；未使用GPU或下载模型权重。
- 新增SWE元数据审计脚本，只读repo/license/instance_id/resolved；不读messages、patch或测试，不产生训练集。

专项证据：[数据结构与长度](readiness_data.md)、[ASI agent](readiness_asi_agent.md)、[基础设施](readiness_infrastructure.md)、[训练栈](readiness_training.md)、[HLE/Judge](readiness_hle_judge.md)。
