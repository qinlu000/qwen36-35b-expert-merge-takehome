# Base优先评测：执行条件与最短依赖

更新：2026-10-15。仅只读检查80当前Git文件、现有readiness证据与artifacts目录结构；本轮没有安装、模型/API/任务执行、容器、Slurm申请或广泛环境扫描。本文不会把此前工程检查当成正式Base成绩。

## 判断

当前主线调整为：评测协议草案与独立任务通路验证 → 启动前冻结每项协议 → Base独立dev诊断并尽早启动正式全量基线 → 根据独立dev冻结训练配方并SFT → dev选模 → 最终全评。这样先确认测量可靠，再针对真实短板训练。方法候选范围、dev划分规则先定，最终训练配比可依据独立dev的Base诊断在SFT前锁定，不要求在Base之前凭经验一次选死。数据已下载只是准备成果，批量自采和训练调参后移；CPU来源整理与环境准备仍可并行。

不必等四项Base全量及全部Judge返回才开始SFT；每项协议和链路就绪即按项启动，真实四卡排程决定训练与推理先后。正式Base结果仍必须按题面全量交付，不能拿小dev成绩替代。

这里的Base是固定Qwen/Qwen3.6-35B-A3B revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，不是DeepSeek参考模型。DeepSeek可用于已确定的评分服务或单独标明的外部参考，不能替代Base四项结果。

## 如何用Baseline做针对性训练

- 独立task-dev：先固定来源/任务族隔离、评测预算和可比较指标，再让Base诊断工具动作格式、完成/执行率、超时、长上下文、学科与图文能力。按错误类型调整训练数据和样本组织；不能先看到每题失败再把对应题或答案转进train。
- val-loss：少量独立参考输出用于assistant NLL、监控和预定的有限checkpoint选择，不替代任务执行率。
- 正式四benchmark Base：用于最终同协议比较、了解总体难度和真实运行吞吐。公开汇总成绩和运维排错可以看；不应将本次正式集逐题失败、gold/补丁或派生示范回流训练。训练配比、checkpoint、合版选择优先依据独立dev，避免围绕正式结果反复迭代。
- 若实际依据正式分项成绩改变训练/算法，需记录并在报告披露该适应性选择，不能再声称该测试是完全独立的盲测。这不是禁止了解baseline，而是区分开发证据与最终泛化证据。

现阶段最需要Baseline回答的是“Base是否能正确使用目标工具协议、在哪类独立任务上失败、真正耗时与吞吐是多少”。当前仅有元数据与局部工程证据，尚无真实Base endpoint、GPU分配或四项正式成绩，不将上述顺序写成已开跑。

## 当前正式执行ready矩阵

| 项目 | 已有证据 | 尚缺的最短环节 | 现状 |
| --- | --- | --- | --- |
| 所有Base任务共用 | 固定基座config、权重index、tokenizer/processor；准确架构CPU导入；Mac双SSH短TCP桥接通过 | 71.9GB权重缓存、本题实际GPU分配、可加载的推理环境；真实HTTP文本/图文/多轮工具调用/usage；评测主机到端点的持续连通 | 未有Base endpoint，不具备正式运行条件 |
| HLE | 已查cais/hle@5a81a4c7271a2a2a312b9a690f0c2fde837e4c29、test2500；自造图像processor通过；DeepSeek合成Judge JSON修正后8/8接口检查通过 | 将已查HF revision实际注入运行入口并物化逐题ID清单；真实Qwen图文请求；thinking/preserve_thinking、输出预算、图文/工具、答案抽取/Judge版本及失败规则冻结；判分协议校准 | 最接近打通，仍未ready |
| SWE HARD-51 | 指定51任务清单和官方代码revision可查；全部task.toml资源元数据已核；mini兼容轨迹方向明确 | 正式容器后端/镜像缓存、固定Harbor/mini入口、模型allowlist与分阶段断网、实际任务生命周期与fresh-image replay；50min或30min自定义预算需先决定 | 无可用容器后端，未ready |
| Terminal-Bench2 | 官方89项、Terminus2、五次要求及Harbor资源语义已核 | 可运行的官方Harbor后端/镜像、端点、五组种子与采样/context/thinking冻结、独立任务有效并发验证；题定3h/32CPU/48GB不能默改30min/4CPU | 无可用容器后端，未ready |
| ASI-Bench | 固定代码与完整60×B1–B4范围可查；推荐opencode_cli/OpenCode1.17.15；60项元数据无任务GPU要求 | 先选open seed31415本地或protected seed42官网路线；落实相应sandbox/任务依赖、agent隔离与真实预算；原Judge/视觉判分服务及评分聚合/失败处理 | split/正式评分路线与服务未定，未ready |

上述“缺”基于项目当前证据，不等于断言其他主机或用户全部目录均不存在相关软件。80受检repo只有数据下载与审计脚本，未有正式运行配置或eval runner；`artifacts/models`下仅有`base_metadata`。之前的“数据已下完”指候选训练数据，不能据此称四项正式benchmark已完成物化/镜像预拉。

## 最短先后依赖

1. 先形成协议草案，以独立任务确认可执行后，在每项正式Base启动前固定版本/split/完整ID、模型与precision、thinking/preserve_thinking、agent/tool、采样/context/token/步数/时间/CPU/RAM、重复/种子、评分器/聚合/失败处理。未定项目明确标pending；30min/4CPU和关闭思考目前仍是讨论候选，不能在Base先用一套、专家/合版另用一套。TB先按题定3h/32CPU/48GB规划；资源不足需落实兼容资源或明确可接受的偏离，不能静默降配。ASI评分路线/Judge及SWE预算需在该项正式启动前确定。
2. 同时准备两个工程分支：HPC基座权重/推理栈/真实分配/端点；CPU主机容器后端、各benchmark固定源码与任务环境/镜像，以及HLE/ASI评分链。HLE无需等待容器后端才做接口验证；数据清洗、分组dev和SFT环境准备也可同时推进。
3. 用自造或独立开发任务做短工程smoke：文本、图文、工具往返、任务完成、timeout、评分产物、模型usage及资源遥测；不用正式Benchmark子集调prompt或选协议。从已获实际配额的低并发测资源和模型队列，再定可持续并发，不以32CPU除法当软件上限。
4. 协议与通路ready即按项启动Base完整评测：不用等四项同时ready；CPU验证/replay和外部judge可随结果异步进行。每项均保存配置hash、权重revision和逐任务日志，禁止运行中改预算或排除失败。
5. 训练时机按四卡实测排程：CPU清洗/环境/文档准备可与Base推理并行。若Base占满本题4H100，则正式SFT与其分时；不得假设2卡服务+2卡SFT可行。若真实支持较小资源服务与训练并行，须核算总计仍≤4卡、服务吞吐和同benchmark公平政策。无需为了等待尚未返回的外部judge阻塞已冻结SFT。

首轮最有价值的产物是“可跑通的冻结协议＋Base真实吞吐/逐任务结果”，不是先用便宜API跑一套与Qwen不同的结果再作为Base。正式运行的运维遥测可用于资源安排和排错；正式逐题答案/派生示范不回流训练；训练及合版优先以独立dev选择，正式成绩若参与迭代须披露。

## 本地证据与固定官方来源

- 本地：[基础设施](readiness_infrastructure.md)、[训练/模型依赖](readiness_training.md)、[HLE/Judge检查](readiness_hle_judge.md)、[ASI接入](readiness_asi_agent.md)、[30min/4CPU讨论边界](budget_30min_4cpu_review.md)、[来源与完整范围](benchmark_sources.md)、[当前待办](open_questions.md)。
- [固定基座模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)。
- [SWE V2 locked protocol](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)：保留官方判分与fresh replay；30min不是原50min locked预算。
- [固定Harbor Docker实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/docker.py)：CPU默认limit，不是独占reservation；不保证多开线性提速。
- [固定HLE生成客户端](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)、[评分代码](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)：模型预测和Judge是两个阶段，可异步安排但协议需锁定。
- [ASI评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)、[OpenCode官方适配器](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/opencode_cli.py)：open本地结果与protected官网成绩需区分；数据公开不意味着正式评分服务已可用。

补充同轮只读证据：另一并行核查在HPC发现`/data/user/qinlucao/.cache/huggingface/hub`不存在、`cache/huggingface`为空，`models`顶层没有准确基座，`projects`不存在，`research`顶层未见该模型。这是已查目录的有限证据，不能排除其他共享缓存；下一步可确认共享缓存后再决定是否下载。root另核官方基座支持`enable_thinking=False`；这证明开关可用，不代表此前DeepSeek关闭思考的成本讨论已冻结Qwen正式配置。Qwen的thinking和preserve_thinking仍需同项跨模型明确固定。
