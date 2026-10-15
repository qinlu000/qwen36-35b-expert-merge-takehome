# 与“整体推进”会话的协议核对

2026-10-16。只读核对该会话的人类消息、最终答复及项目文件，未给另一个会话发送消息。核对目标会话：`01a13e6b-484b-7992-bf92-5a61eccf9d69`。

## 已对齐的评测语义

- Base固定Qwen3.6-35B-A3B及既有revision，BF16；统一65536总context、8192单次policy主／辅助输出，prompt最多57344；关闭thinking和preserve_thinking，Judge预算单列。
- SWE为mini-swe-agent 2.4.6／官方工具与fresh replay，51项、30min；Terminal为Terminus2原生JSON／tmux／主动摘要，89项×5、30min；ASI为direct_llm单程序生成与执行，60×4条件、共享20min；HLE为完整2500题含342图像，无工具单次回答、5min。
- 原生Agent格式反馈、至多两次安全HTTP尝试、共享deadline、失败保留分母、替代Judge及固定产物重判规则一致。Terminal继续明确标注资源受限实验，不冒称满足题定256K／80K／3h／32CPU／48GB。
- 最新每项val100、train约500是独立数据建设目标；不能把正式测试改成每项100题。训练清除显式teacher think／reasoning_content，保留正常解释及Terminus analysis／plan；rank、训练窗口等尚未冻结。

## 找到并更正的过期记录

1. v2 JSON的deployment／server resource scope与协议文档仍写项目总上限4卡。已按该会话最新用户原话改为最多16H100、可能零散、同组最多4卡；空闲不足可用现账户已授权能力提高本题优先级。新增记录修订`2026-10-16-resource-alignment-1`，解题语义未改。
2. 协议只提723821短smoke，漏记723993的真实65536／8192参数、57280-token长输入、32px图像、工具往返和越界400。已补证据，仍保留整体verified=false；完整8K解码、精确输入／视觉guard、长摘要、4活跃序列／8solver及原生链路仍待验收。
3. 同步前Mac与80的v2 JSON／文档SHA完全相同；HPC项目下这两份文件不存在。本轮将修订后的规范副本同步到两端并核SHA。这不构成可执行runner或正式启动。

## 当前起点与扩容计划

单TP2、每服务4活跃模型序列／8准入solver、单benchmark／模型块、训练评测分时，仍是当前起点；并发吞吐本身尚未验收。最新16卡授权允许规划独立TP2分片与跨组训练／推理，但这些排期仍需真实资源、CPU／RAM、队列与持续吞吐验收，以及正式使用前的调度修订。不能将资源上限直接当成8个副本、已验证并行或已分配16卡。

“整体推进”的夜间方案仍在待用户审阅状态，最新资源消息没有单独确认夜间续跑或正式SFT。本轮只核对和修正文档／规范副本，没有提交GPU作业、改变作业优先级、调用模型API、启动正式评测、训练或自动任务。
