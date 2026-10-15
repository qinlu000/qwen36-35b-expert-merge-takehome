# 这道笔试可直接参考和复用的公开材料

核验日期：2026-10-15。本轮补查公开题目、相关实验模型卡和同底座工程；没有下载权重/训练数据、运行模型、读取本题逐题答案/补丁/隐藏测试。作者报告未独立复现，访问状态仅代表本次检查。

本轮没有发现同时满足“Qwen3.6-35B-A3B、自行训练多专家、参数合版、四项全量评测”的完整公开成品；这不是不存在的证明。现有材料足以复用训练、合版、评测和记录组件，但研究方案仍需本项目自行确定。

## 最直接的材料

| 材料 | 已核事实 | 可借鉴与限制 |
| --- | --- | --- |
| [官方 takehome 模板](https://github.com/apexin-ai/qwen36-35b-takehome/blob/994e2c329c5ce3f6beaff788f5df98d686442147/README.md) | 指定同底座、同四项 benchmark；README 明确目录树是示例，不代表已有这些实现文件 | 参考提交结构、运行元数据、曲线/日志/结果索引。公开 README 是 SFT→第二阶段，与本次附件多专家合版路线不同；以附件为准 |
| [公开 v6 实验模型卡](https://huggingface.co/deanoshuang/qwen3.5-9b-agent-sft-v6-lora) | 使用 Qwen3.5-9B，Base/SFT/stage2，列同四项 benchmark；有 adapter revision、训练记录与数据说明 | 可参考数据组织、loss mask、记录格式。卡片披露该 checkpoint 正式评测中止，未报告 benchmark 分数，不是完成版。模型卡声明 Apache-2.0 |
| [旧版实验模型卡](https://huggingface.co/deanoshuang/qwen3.5-9b-agent-sft-lora) | 作者只披露 TB2.0 全89题的一次种子，其他三项未评，并记录重复命令/长推理等退化 | 可参考失败类别；不把外部成绩当本项目结果或配置选择依据。两张卡链接的候选人 GitHub 本次匿名访问404，不能确认其代码公开可用，也不推断404原因 |
| [Occamy-1.0 作者仓库](https://github.com/Accio-Lab/occamy) | 从同一个 Qwen3.6-35B-A3B 分出 Marathon 与 Sprint；前者 SFT→HDPO，后者 SFT；均匀参数合版后再SAO。作者列约403M SFT union token、全参训练 | 直接支持“不同专长分支训练→单模型合版”的结构；其预算与RL阶段不能照搬到本项目。仓库声明Apache-2.0，提供训练报告而非本题四项完整成品 |
| [T-Search 论文](https://arxiv.org/html/2610.06782v1)与[作者harness](https://github.com/turbo-llm/t-search-harness) | 同底座语言分支SFT/DARE，再RL/SLERP；带必要状态的工具回合监督 | 可借鉴轨迹组织和分阶段对照，不替换题定harness，也不以检索结果预测四项成绩 |

Occamy 的底层 [Dressage](https://github.com/Accio-Lab/Dressage) 提供多harness的RL基础设施，可作为后续扩展阅读；本轮不因为它公开就引入RL平台或额外训练阶段。

另有[同35B底座的社区SLERP合版](https://huggingface.co/VladHong/Qwen3.6-KAT-BigBang-SLERP-35B-GGUF)，作者披露不同MoE张量布局的转换及流式处理。但它删除视觉侧、仅保留文本、没有系统评完本题四项；仅作工程案例，不作为本项目最终模型或多模态评测方案。模型卡中的“APEX Nano”是量化命名，不能据名称认定是本笔试解答。

## 最适合当前预算的复用组合

1. 训练入口参考 [ms-swift 同架构四卡示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/transformers.sh)，使用目标官方base与本项目数据；目标模块、模板、kernel、显存与吞吐仍须后续验证。
2. 专家组织参考 [MergeLM](https://github.com/yule-BUAA/MergeLM)，合版比较简单dense delta平均与 [TIES](https://github.com/prateeky2806/ties-merging)。外部已训练专家不能替代题面要求的本次真实专家训练。
3. 数据候选复用可追溯修复轨迹、终端skill-based、数学推理材料，再补科学工具缺口；具体来源与许可/污染边界见 `references_data.md`。
4. 评测直接沿用 [SWE Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/tree/v2.0.0/v2)、[Harbor/TB2](https://github.com/harbor-framework/harbor)、[HLE](https://github.com/centerforaisafety/hle)、[ASI-Bench](https://github.com/apexin-ai/ASI-Bench) 的固定官方入口。共享组件不等于四项可以套同一个agent或同一套预算，完整协议见此前专项笔记。

本轮只补充参考资料，不改变已讨论的轻量SFT/AVG/TIES候选主线，不以外部benchmark表现选数据、checkpoint或合版参数；没有恢复实验执行。

## Occamy代码开放到哪一层

2026-10-15补查：

- [Occamy本体](https://github.com/Accio-Lab/occamy)主要提供模型介绍、网站和[技术报告PDF](https://github.com/Accio-Lab/occamy/blob/main/report/occamy1.0.pdf)；本次report目录仅看到该PDF。
- [Dressage](https://github.com/Accio-Lab/Dressage/tree/3e3142fe8ea07e4504c3b20a936a4c201a3de44c)是真实开源的agent RL基础设施，包含训练层、轨迹采集、沙箱和启动示例，基于slime。不能将“模型说明仓库”与“底层训练代码仓库”混称。
- 找到准确目标模型的[Claw训练脚本](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/examples/scripts/run_dressage_claw_qwen3.6_35b_a3b_sync_4_node.sh)，是4节点×8GPU=32卡的GRPO配置，不是4卡配置，也不是Occamy全部阶段的复现入口。
- 本次README/目录与入口核验未找到Occamy Marathon/Sprint的SFT、HDPO、均匀合版、SAO整套专用脚本和配置；完整数据及端到端复现材料的公开程度仍未证实。结论是“有底层代码与可运行示例”，而非“完整Occamy配方已全部开放”。
- 当前仍仅作为方法与实现参考，不安装或直接运行该脚本，不将其替换为本项目已讨论的轻量SFT主线。
