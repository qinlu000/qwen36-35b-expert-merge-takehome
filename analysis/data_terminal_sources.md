# 终端与执行数据来源：候选与取舍

核验日期：2026-10-15（Asia/Shanghai）。仅查一手论文、数据卡、版本与schema元数据；未下载Parquet、任务环境或权重，未写实验代码、生成轨迹或运行模型。最终选择见 `data_expert_recommendation.md`，本文件记录终端侧证据。

## 1. 主候选：Nemotron-Terminal-Corpus的skill-based分区

[固定数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)，revision `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`，数据卡CC BY 4.0。作者公开的是SFT执行轨迹，而不是只有任务说明。[作者论文](https://arxiv.org/html/2602.21193v1)采用Terminus 2产生轨迹，描述TB2 prompt 14-gram排除；这不证明语义、来源及其他三项完全无污染。

[官方schema/分区元数据](https://datasets-server.huggingface.co/info?dataset=nvidia%2FNemotron-Terminal-Corpus)本轮返回：

| config | train行数 |
| --- | ---: |
| dataset_adapters | 226313 |
| skill_based_easy | 44809 |
| skill_based_medium | 89343 |
| skill_based_mixed | 5689 |

skill-based共139841行，是轨迹行数，不应直接写成同等数量的独立任务。其schema有 `conversations(role,content)`、`agent/model/model_provider`、`task`、`episode`、`run_id/trial_name/date` 和 `enable_thinking`，没有显式 `domain`、`resolved` 或 `result` 字段。不能假设可直接按成功标签过滤；科学/数据科学路径选择的核验见 `data_science_sources.md`。

**建议。** 优先skill-based，减少adapters聚合多个上游的追溯负担；以系统管理、文件/数据处理、环境排错、构建与命令工作流补足修复专家，科研执行另留明确子预算。数据卡许可与上游内容的归属仍需保留。easy/medium/mixed只是发布分区，不当作本项目已测难度或课程顺序。

## 2. 补充候选：OpenThoughts-Agent-SFT-100K

[固定卡片](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K/blob/45fb28fcc38d352133cb28a1c8a43a2f14fea97b/README.md)，revision `45fb28fcc38d352133cb28a1c8a43a2f14fea97b`，Apache 2.0。发布含SWE-smith、SuperUser、Tezos、IssueTasks四来源的Terminus 2教师轨迹；schema显式有 `trace_source`、`task/conversations`、`result` 和运行信息。不是旧v1的nl2bash/InferredBugs配方。

数据卡称100000例，但[本轮官方schema元数据](https://datasets-server.huggingface.co/info?dataset=open-thoughts%2FOpenThoughts-Agent-SFT-100K)返回default/train=94334。未下载文件核算差异，未来以固定revision实得manifest为准，不能宣称100K独立任务。相同任务可能重复rollout或改写，分割不能只按行或trial_name。

**建议。** 优先核SuperUser来源，作为真实系统操作补充；不默认加入Tezos加密货币题。SWE-smith/IssueTasks若用于修复池，需与其他SWE源统一做repo/issue/任务去重，而不是把同题的不同教师轨迹计成数据多样性。论坛材料的上游许可/归属由来源逐项核验，数据卡Apache声明不覆盖原材料的所有权利。

[OT-Agent论文](https://arxiv.org/html/2606.24855v1)显示软件修复与系统操作来源互补，多轮过滤在等token消融中仍有价值，但并非来源越多越好。这里只借鉴数据选择原则：不复刻其上百次消融、全参训练或以TB2反馈挑配方；本项目用独立dev。

## 3. 暂不作为默认

- 完整dataset_adapters：上游包括数学、代码和SWE多种集合，追溯/重复核查成本高；不因规模更大直接整包纳入。
- OpenThoughts旧v1-SFT：确有nl2bash与C#/Java InferredBugs轨迹，约15.2K，但主要作为补充候选而非再加一套主源。[作者卡片](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-v1-SFT/blob/main/README.md)
- AgentTrove/TaskTrove大全：任务环境、轨迹与不同研究实验混杂；当前窗口不整包接入。若使用只抽来源明确、与正式题无关联的小分区。
- TB2/其解题轨迹、答案、隐藏验证、评测派生改写：不纳入训练或独立dev。外部论文的benchmark成绩不能用于本项目checkpoint或合版选择。

## 4. 质量与长度处理建议

Nemotron论文的success-only过滤结果较差，不能把“每条都必须最终成功”当普遍规律；各源验证信号本来也不同。当前默认先检查消息结构、工具调用/返回配对、空输出、异常截断与重复循环，保留有用错误反馈和恢复步骤；不因某次命令exit非零就剔除整轨迹。具体失败终局的监督规则在数据审计后冻结。

OT-Agent多轮结论与[近期监督时域研究](https://arxiv.org/abs/2610.05831)共同提醒，短轨迹不一定更好，训练越长也不必然更优。本项目8K只是待验证训练上限，不是论文验证过的最优值。按完整工具回合组织片段，保留必要任务/文件状态，只监督新增assistant输出；无法在预算中保留必要状态的样例先不选，不机械截尾、不凭空补观察。分段重复上下文计入processed token。

未来先按原始任务/模板家族分train、checkpoint-dev、merge-dev，再分段与抽样；跨来源、变体和多教师rollout统一分组。dev不从TB2、HLE、ASI或SWE Pro抽取。当前没有逐行污染审计、token统计、实际格式适配或成功率测量。
