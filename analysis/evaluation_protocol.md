# 四项 Agent 评测协议 v2：统一 64K / 8K

2026-10-16。当前有效的**实验设计**为 [protocol_v2_unified64k8k.json](../configs/eval/protocol_v2_unified64k8k.json)，记录修订 `2026-10-16-resource-alignment-1`。参数已确定；合成64K长输入已通过，原生 runner、长摘要及并发仍待验收。本次只同步最新资源授权与验收证据，未改变解题协议或启用扩容调度；本文件不代表已开始正式评测。旧版保存在 [v1 文档](evaluation_protocol_v1.md) 与 `configs/eval/protocol_v1.json`，仅供历史参照。

## 范围与资源

所有受测模型的主调用及辅助调用统一 **65536 总上下文、8192 单次输出上限**，关闭 thinking 和 preserve_thinking。K=1024；8K 是每次调用的上限，不是整题累计上限，也不要求生成满额。评分模型另定预算。

| Benchmark | 固定 harness | 完整范围／每模型重复 | 解题墙钟 | 任务 CPU／RAM |
| --- | --- | --- | --- | --- |
| SWE-bench Pro V2 HARD-51 | 官方 LockedMiniSwe + mini-swe-agent 2.4.6 | hard/test 51 项，seed=0 | 30min；内层 1740s，强杀宽限 30s | 1 CPU／4GiB |
| Terminal-Bench 2.0 | Harbor 0.24.0 / Terminus-2 2.0.0 | 完整 89 项 × 五组 seed=0–4 | 30min，含摘要和命令 | 4 CPU／8GiB |
| ASI-Bench | 官方 direct_llm，单程序生成与执行 | seed31415/open 60 任务 × B1–B4=240 条件，各一次 | 20min，生成与执行共享 | 4 CPU／8GiB |
| HLE | 官方单次图文问答，无工具 | test 全部 2500 题，含 342 图像题，seed=0 | 5min／题 | 共享客户端 4 CPU／8GiB，非每题独占 |

模型服务的 GPU／CPU／RAM 单独计入调度。镜像构建、输入准备、SWE verifier 与 fresh replay、独立判分不在解题墙钟内，分别记录耗时。所有来源 revision、任务 ID、主指标和依赖指纹见 JSON 与 `analysis/source_snapshots/protocol/`，不改用其他 split，不删除失败题。

另一会话“整体推进”最新的数据建设目标为每benchmark独立val100、train约500，先按类型分层与任务族隔离。该目标不缩减本表的正式测试范围，也不等于训练数量及rank／窗口已经最终冻结。

**Terminal 的本版本属于资源受限实验。** 题定要求为 256K context、80K 单次输出、3 小时、32 CPU、48GB、五组种子。本版本只保留完整任务集与五次重复，未满足前述资源配置，也未获得面试方例外许可，不能作为完全符合题定设置的成绩。SWE 的 30min 也区别所选上游 locked 配置的 50min；HLE／ASI 替换 Judge 的差异须一并报告。

## 模型与请求

- 基座固定 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`；tokenizer、processor、chat template 固定同一 revision。BF16 权重及 full-attention KV，不做权重量化，保留原生视觉模块与 linear-attention 状态精度。
- Base、目标专家、合版在每个 benchmark 内使用相同 harness、prompt、工具、精度、上下文、输出、种子、采样、超时与调度。跨 benchmark 保留各自原生 Agent 接口。
- SWE／HLE／ASI：temperature=0.7、top_p=0.8、top_k=20、min_p=0、presence_penalty=0、repetition_penalty=1、seed=0。Terminal：temperature=1、top_p=0.95、top_k=20、presence_penalty=0、repetition_penalty=1，分别运行五组种子。这些未由上游强制的值是本实验设置。
- 使用 Chat Completions；top_k 经 extra_body 传入，thinking 两开关经 chat_template_kwargs 传入，验收真实请求和模板。保留原生 EOS／工具结束，不新增 stop 字符串。
- 每个主调用与摘要辅助调用发送前，以固定 Qwen 模板及 processor 计算实际输入 P，要求 **P + 8192 ≤ 65536**，即最多 **57344（56K）输入 tokens**。计入 system、工具定义、待加入消息、历史、真实展开的视觉 tokens。图片占位符估算不能代替视觉计数。
- 输入超限不发送，不静默裁题、删图、裁历史或减少输出预留。`finish_reason=length` 保存部分输出，不加预算重答。原生多轮 Agent 可把解析／工具错误作为下一轮观察继续修复，仍计入同一 trial 和墙钟；HLE／ASI 单次作答不生成第二份答案。

## 各 Agent 的交互契约

**SWE。** 保留官方 prompt、`bash(command)` 工具 schema、每动作新 subshell、JSON 观察，以及 10000 字符的头尾截断；不误写为 tokens。保留官方提交标记、patch 捕获和全新初始 sandbox 的 patch replay，主分数取 replay resolved rate／51，原运行分数另存。无限 step，无额外总 token 上限，无新增摘要或滚动历史。移除不适用于本地 Qwen 的 reasoning_effort；原生最多十次传输重试须改成下述共同政策，保留原生格式错误反馈。

**Terminal。** 保留原生 assistant JSON 中的 analysis／plan／commands／task_complete、tmux 持久状态、输出格式与字节截断、两次完成确认；不改造成 API function tools。启用原生 proactive best-effort 摘要，free-token 阈值 32768，即原生估算历史超过约 32K 时尝试摘要。该阈值仅提前触发，不能保证后续多阶段摘要一定容纳。主／summary／questions／answers／short_summary 均用同一受测模型、8K 上限，逐次做实际输入检查；辅助超限则不发送、记录摘要失败，之后主请求合法才继续。主请求超限则结束并留档，不能依赖原生 reactive unwind 或隐式裁历史绕过限制。所有调用共同计入 30min；不新增 max_turns 或累计 token 硬限。

**ASI。** 采用官方 direct_llm：模型仅收到官方默认 system 与该条件的完整文本 prompt，一次生成完整 Python 程序，按原生提取规则执行一次并收集声明文件，由官方 scorer 判分。程序可读取 sandbox 中的任务数据和图片；该模式没有把图片发给模型的工具回路，也没有 stderr 反馈后的二次生成。生成、排队、重试、提取写入和执行共享 1200s，执行只获剩余时间。每条件使用全新任务工作区及官方依赖，reference 和 scorer 对 policy 隔离，任务程序不可用 GPU 或外网。具体隔离实现尚待验收，不能仅因原生接口名为 os 就称已隔离。

**HLE。** 一题一次回答，保留官方 Explanation／Answer／Confidence 格式，完整题面及原图，固定 processor，不按失败题临时缩图或删题。无 shell、搜索、代码执行工具。2500 全量准确率为主，另报 2158 纯文本与 342 图像题分项；评分参考答案只交 Judge。300s 包含已准入后的输入处理、端点等待、传输和生成，每次 HTTP timeout 不超过剩余墙钟；不保留独立 600s 的旧 HTTP 默认。

## 时间、重试、失败与评分

环境／输入就绪且任务获 solver slot 后开始计时；未获准入的全局队列另计。计时包括端点排队、全部主／辅助调用及任务命令／程序。到期取消实际生成、停止 solver 进程组，保留产物；清理阶段不能继续解题。

每个 policy 主／辅助逻辑 HTTP 至多两次尝试，只在一层重试，禁用 SDK／LiteLLM 的叠加重试；Judge 的固化产物重判按独立评分规则执行。仅明确请求尚未发送的连接失败，或明确未生成的 429，可携相同 payload／seed 在原 deadline 内重试。发送后断链、读超时、length 不重答。原生解析反馈进入下一 Agent turn 与传输重试分别记录。

整题自动重跑为零。经核实的基础设施失败最多人工补跑两次，同 ID／seed／模型／配置，保留首个有效结果及全部日志和成本。模型超时、缺文件、错误动作按官方 grader 对现有产物给分，保留部分分；基础设施／判分失败单列，不删失败题提高分数。

HLE／ASI 选已有 DeepSeek 官方 deepseek-flash 作**本实验替代 Judge**，不声称等价官方默认模型。HLE 使用固定原 criteria、JSON 包装、非思考、temperature=0、4096 输出；ASI 保留原 rubric、权重、num_judges、图像、输出额度及聚合，只适配模型和响应接口。图像接口已通过合成检查，科学评分校准仍待做。备用 Judge 不混入同一结果批次；更换须版本化并对所有模型的同批固化产物重判。Judge 失败只重判原答案／文件，不触发 policy 重答；统一 8K 不覆盖 Judge。

主指标保留：SWE fresh-replay resolved rate；TB 五次成功率均值及样本标准差 ddof=1；HLE 准确率；ASI 官方 local mean_percent，240 条件判分完整且 scorer_error_count=0 后才报完整主分。四项百分制等权 macro。配对 task-cluster percentile bootstrap 10000 次、PCG64 seed20261015、95% 区间，TB 保留每题五 seed，ASI 保留每任务四层。正式输出／反馈不回流训练或独立 dev。

最低完整范围矩阵仍为 Base 与合版四项、仓库专家 SWE、交互执行专家 TB+ASI、学术专家 HLE，共 SWE153、TB1335、HLE7500、ASI720，总9708次；完整范围不等于 Terminal 已满足题定资源。

## 部署与执行状态

当前起点仍为单个 TP2 服务：vLLM0.20.2、Torch2.11.0+cu130、Transformers5.15.1、eager、Triton GDN／MoE、max_num_seqs=4、gpu_memory_utilization=0.85、chunked prefill、max_num_batched_tokens=8192。后者是调度分块额度，不是输入长度上限。服务单独申请 2×H100／16 CPU／128GiB，最多准入 8 个 solver；一次运行一个 benchmark／模型块，各比较模型相同；此起点保留训练与评测分时。

用户最新授权为**项目总计最多16张H100，可能零散，同组最多4张**；这不是已获得的分配。空闲不足时可使用现账户已授权的队列／QoS等能力提高本题优先级。独立TP2服务分片、其他卡组训练与Base并行属于[扩容计划](overnight_execution_plan_20261016.md)，须核资源、CPU／RAM、排队与持续吞吐，并在正式使用前冻结调度修订；16卡授权不自动把副本数改为8，也不证明单卡TP1或跨节点TP可用。

作业723993已按 TP2/BF16／65536 context／8192输出上限通过合成文本、32px图片、工具往返、57280-token长输入及越界HTTP400，见[验收回执](source_snapshots/base_gpu_smoke_v2_20261016.json)。实际输出未满8192，未覆盖精确57344输入边界、通用真实视觉计数、长摘要、四条活跃序列／八个solver的排队与峰值、持续吞吐及原生Agent。任务CPU／RAM／网络隔离还需各项端到端验收，不能将整体verified改为true。验收失败应在正式Base前修订版本，不能逐题临时改预算。

本 JSON 是协议规范，未自动实现上述适配。正式启动前需完成薄适配、冻结实际 runner／依赖／镜像与线上请求指纹、通过独立 smoke；SFT 训练窗口与推理上限分别制定，不因单次输出 8K 就把训练标签直接裁到 8K。

来源审计与容量依据：[SWE](protocol_swe_review.md)、[Terminal](protocol_terminal_review.md)、[ASI](protocol_asi_review.md)、[HLE](protocol_hle_review.md)、[上下文证据](context_evidence_20261016.md)、[轨迹长度](trajectory_lengths.md)、[Base验收状态](setup_base_runtime_status.md)。
