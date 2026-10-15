# 与“整体推进”会话的协议核对

2026-10-16。只读核对该会话的人类消息、最终答复及项目文件，未给另一个会话发送消息。核对目标会话：`01a13e6b-484b-7992-bf92-5a61eccf9d69`。

## 已对齐的评测语义

- Base固定Qwen3.6-35B-A3B及既有revision，BF16；统一65536总context、8192单次policy主／辅助输出，prompt最多57344；关闭thinking和preserve_thinking，Judge预算单列。
- SWE为mini-swe-agent 2.4.6／官方工具与fresh replay，51项、30min；Terminal为Terminus2原生JSON／tmux／主动摘要，89项×5、30min；ASI为direct_llm单程序生成与执行，60×4条件、共享20min；HLE为完整2500题含342图像，无工具单次回答、5min。
- 原生Agent格式反馈、至多两次安全HTTP尝试、共享deadline、失败保留分母、替代Judge及固定产物重判规则一致。Terminal继续明确标注资源受限实验，不冒称满足题定256K／80K／3h／32CPU／48GB。
- 最新每项val100、train约500是独立数据建设目标；不能把正式测试改成每项100题。训练清除显式teacher think／reasoning_content，保留正常解释及Terminus analysis／plan；rank、训练窗口等尚未冻结。

## 各benchmark的harness与实际接线

框架、Agent和sandbox分别固定，四项不共用同一个Agent；Base、对应专家和合版在同一benchmark内必须复用同一套harness。

| Benchmark | 框架与Agent | 保留的原生行为 | 当前接线状态 |
| --- | --- | --- | --- |
| SWE | Harbor0.24.0 + SWE Pro官方LockedMiniSwe + mini-swe-agent2.4.6；源码66f92766 | bash(command)、官方观察/完成标记、patch捕获与fresh sandbox replay | 固定源码及宿主import已有；容器依赖锁、phase网络、v2参数/重试与正式replay链未验 |
| Terminal | Harbor0.24.0 + Terminus2 2.0.0；Harbor源码f527f8e4 | assistant JSON、tmux持久终端、主动摘要、完成确认、官方verifier | 安装和代表镜像终端生命周期已验；主/辅助请求、预算guard、资源/网络、真实端点链仍待验 |
| HLE | centerforaisafety/hle源码22ed3074；官方run_model_predictions.py及run_judge_results.py | 完整图文输入、单次Explanation/Answer/Confidence、无工具；DeepSeek替代Judge单独披露 | 44包和数据已安装；需薄runner固定revision/生成参数、视觉guard、300s及逐题保存 |
| ASI | apexin-ai/ASI-Bench源码cf07cb89、asibench0.2.0 + 官方direct_llm；官方collector/scorer | 一次完整Python程序生成、执行一次、收集声明产物；不把stderr反馈给模型再答 | 45组任务依赖/执行隔离已有合成回执；正式入口、生成guard/参数、共享1200s与资源限额仍待补 |

SWE/Terminal当前站点backend是Apptainer/Singularity配合项目ApexSingularityEnvironment及留痕启动补丁；它只解决启动/执行基础设施，不能冒充网络phase与CPU/RAM边界已经实现。`run_harbor_singularity.sh`只指定backend，不自动加载v2 Agent及请求配置。ASI的`BwrapDirectLLMAdapter`只替换执行hook，原生CLI也不会自动加载它。

旧ASI审计、兼容性比较及OpenCode安装记录仍在，已加当前路线提示；HLE安装回执的v1指针已改为v2。已安装OpenCode不等于正式ASI用OpenCode，宿主mini已安装也不等于任务容器内依赖锁已落实。

## 找到并更正的过期记录

1. v2 JSON的deployment／server resource scope与协议文档仍写项目总上限4卡。已按该会话最新用户原话改为最多16H100、可能零散、同组最多4卡；空闲不足可用现账户已授权能力提高本题优先级。新增记录修订`2026-10-16-resource-alignment-1`，解题语义未改。
2. 协议只提723821短smoke，漏记723993的真实65536／8192参数、57280-token长输入、32px图像、工具往返和越界400。已补证据，仍保留整体verified=false；完整8K解码、精确输入／视觉guard、长摘要、4活跃序列／8solver及原生链路仍待验收。
3. 同步前Mac与80的v2 JSON／文档SHA完全相同；HPC项目下这两份文件不存在。本轮将修订后的规范副本同步到两端并核SHA。这不构成可执行runner或正式启动。

## 当前起点与扩容计划

单TP2、每服务4活跃模型序列／8准入solver、单benchmark／模型块、训练评测分时，仍是当前起点；并发吞吐本身尚未验收。最新16卡授权允许规划独立TP2分片与跨组训练／推理，但这些排期仍需真实资源、CPU／RAM、队列与持续吞吐验收，以及正式使用前的调度修订。不能将资源上限直接当成8个副本、已验证并行或已分配16卡。

上轮核对时，“整体推进”的夜间方案仍待审阅。随后该会话已收到用户“全都用新版的……帮我持续推进……新进展和不确定的全都记录到一个文档中”的新指令，当前由该会话推进；不能再把夜间持续推进描述为始终未授权。该消息未冻结LoRA rank/训练窗口，本会话不接管其数据删除或队列。本轮仅核harness与文档，没有提交GPU作业、变更优先级、调用模型API、启动正式评测、训练或自动任务。
