# 近期公开 Terminal 训练轨迹：教师更新与实际可用性

核查日期：2026-10-16。按 research 流程用 ego-browser 实读作者数据卡、Hugging Face 仓库元信息和原论文；固定到下列 revision。未下载数据分片、运行模型/付费API/GPU或重放任务。日期是**数据仓库创建/最后修改**，不是教师训练日期；样本数来自卡片/其 dataset_info，未进行全量重数。

**最新同harness线索是8月上传的两项 GLM-5.2 + Terminus2 命名仓库，已有公开Parquet，但缺文档/许可/来源及成功证据，尚未验收。资料最清楚、最值得新增审核的是 OpenThoughts-Agent-SFT-100K：GLM-4.7-AWQ 教师、原生 Terminus-2、100K 多轮轨迹。**更强开源教师的终端示范也确实存在——AllenAI TMax 用 Qwen3.6-27B，但其动作协议是 mini-SWE-agent 风格，并不原生匹配本题 Terminus-2。更新的 DeepSeek-V4-Pro 轨迹已公开，但本轮找到的两个池分别是自定义函数工具合成、pi 编程会话，不能因教师更新就直接换成本题终端主池。

## 精选五个可下载来源

| 来源与固定版本 | 教师、时间、规模 | harness / 环境 / 结果信息 | 本项目定位与复用成本 |
|---|---|---|---|
| **[OpenThoughts-Agent-SFT-100K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K/blob/45fb28fcc38d352133cb28a1c8a43a2f14fea97b/README.md)**；`45fb28fcc38d352133cb28a1c8a43a2f14fea97b` | **GLM-4.7-AWQ**；2026-06-08；**100,000** task/trajectory对；10个Parquet | 作者卡明确 **terminus-2 + Daytona sandbox**；任务来自SWE-Smith、SuperUser、Tezos、IssueTasks；保留至少5个model turns；`conversations`、task、trace_source、agent/model/model_provider、**result**、episode等字段。Apache-2.0。 | **首选新增候选**。先核实际result语义、观察/完成协议、教师具体AWQ版本和任务环境关联；卡片中的“至少5轮”不等于成功验证。不能承诺GLM4.7强于当前Qwen Base。旧记录若将这个100K池笼统当OpenHands轨迹，应修正；不要与旧Agent-v1混淆。 |
| **[AllenAI tmax-sft](https://huggingface.co/datasets/allenai/tmax-sft/blob/9d6ab7471ffa2884b2ef0cd2b7e5e22a027ff1b4/README.md)**；`9d6ab7471ffa2884b2ef0cd2b7e5e22a027ff1b4` | **Qwen3.6-27B**；创建2026-06-18、更新06-23。当前卡dataset_info：thinking_all **10,726**；thinking_only_success **5,795**（约41MB压缩）。论文描述生成阶段16.5K、约8K成功，**不要用论文规模冒充当前发布量**。 | 原论文是 **mini-SWE-agent-inspired harness**；公开tools为bash/command，messages含reasoning_content、tool_calls和观察；metadata有source_model/task/trial等。独立约2K合成环境；Podman/Apptainer路线有代码。ODC-BY；卡另说明包含Gemini3.1Pro生成内容，需保留来源归属，不能把全部生成角色一概归成Qwen。 | **教师更贴“较强开源模型”的候选，但不是本题原生Terminus-2**。成功子池是合理的优先查看入口；has_task_complete只是自报完成，不能当reward。若坚持训练与评测agent同源，不能仅改成JSON动作就声称对齐；需另定相容策略或在独立任务补采。 |
| **[LiteCoder-Terminal-SFT](https://huggingface.co/datasets/Lite-Coder/LiteCoder-Terminal-SFT/blob/6acdbbdb29979e4b8ea717b12accc8214606d087/README.md)**；`6acdbbdb29979e4b8ea717b12accc8214606d087` | **MiniMax M2 / M2.1**（原论文明确）；卡列发布2026-04-13、仓库更新06-01；**11,255**轨迹、平均27.4轮、10类；单个litecoder-sft.json | **Terminus-2 86.6% / OpenHands 7.1% / Claude Code 6.3%**；Harbor任务，Dockerfile/输入/测试/配置路线公开。论文描述LLM行为过滤和13-gram去污染。MIT。卡未列实际逐条reward schema，本轮未读数据正文。 | **同harness补充候选**，应只挑已核Terminus子池并核环境映射/结果字段。教师版本较旧，不能当作“最新强教师升级”。行为judge过滤不自动等于每条可执行验证通过。 |
| **[r0b0tlab/DeepSeek-V4-Pro-0813-Agentic](https://huggingface.co/datasets/r0b0tlab/deepseek-v4-pro-0813-agentic/blob/2f075a280078b485be3e07b7fbf1413b88f6411a/README.md)**；`2f075a280078b485be3e07b7fbf1413b88f6411a` | 作者声明官方API **deepseek-v4-pro-0813**、thinking、2026-08-15/16采集；**19,072 train + 1,070val + 1,065test**；共21,207。 | **自定义函数工具**：fs/sqlite/json/Python subprocess，不是Terminus；只有**5,997行有工具调用**，13类中code_execution仅176；assistant轮数median1。作者声明verifier_passed均true、全量deterministic replay；公开messages/tools/verifier契约和Parquet，未独立复验其声明；采集代码只有local路径描述，无公开GitHub链接。license=other。 | **近期教师的通用工具辅助候选**，不是可直接顶替终端主池的长程终端轨迹；不能把19K全部说成终端多轮。source模型记录别名deepseek-v4-pro，0813解析依据来自作者运行声明。 |
| **[TeichAI/DeepSeek-v4-Pro-Agent](https://huggingface.co/datasets/TeichAI/DeepSeek-v4-Pro-Agent/blob/abbf7b71b145633b60beb21ddc0d158582fd80dd/README.md)**；`abbf7b71b145633b60beb21ddc0d158582fd80dd` | **deepseek/deepseek-v4-pro**；创建2026-05-09、更新05-22；**4,006 JSONL会话**（不是4,006条已验收成功任务）；未固定更细教师snapshot | **pi harness**，bash/read/edit/write等工具；/workspace会话；事件流含session/message/model_change等，有tools snapshot和teich转换代码。**无明确逐任务成功标签、无数据license元字段**；环境初始资产/镜像映射未说明。 | **原始编程会话研究候选**。工具/状态/提交协议与Terminus不同，且缺可核成功依据；不能只套Qwen模板就升级为Terminus训练主数据。 |

TMax框架和教师见[作者论文 §3.3 / §4.1](https://arxiv.org/html/2606.23321v1)与[作者代码](https://github.com/hamishivi/tmax)；LiteCoder教师与环境/过滤见[作者论文 §3](https://arxiv.org/html/2605.29559v1)。OpenThoughts采集/训练代码由[作者卡链接](https://github.com/open-thoughts/OpenThoughts-Agent)公开，精确collector参数仍需随后锁定。

现有 **[Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)** 本轮重查revision仍为 `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`，最后更新2026-02-27；卡宣称总约366K，其中skill-based约140K，本项目已下载该部分实数139,841。教师DeepSeek-V3.2、原生Terminus2的既有审计仍有效，CC-BY-4.0。它是**已审过的基线候选**，不是更新教师的新发现；新增来源不能跳过既有兼容/环境资格要求。

## 更新教师不等于可直接训练，不能混淆的线索

- **TMax“terminus”派生名不代表原生Terminus。**[第三方NiuNiu0110派生卡](https://huggingface.co/datasets/NiuNiu0110/TMax-Agent-SFT-terminus/blob/7d74fd38a3bc437bbd2c377bd8a1effba64d79ba/README.md)明确说数据仍是native bash tool+think，区别于Terminus JSON；其5,645是对5,795上游条目的清洗/去重/长度门控结果，无新采样，无重放验证。优先保存原始上游结构，不能直接信派生名称或沿用别的tokenizer监督mask。`TMax-15K`及`TMax-SFT-16.5K`是任务/环境实例，**真实assistant轨迹在tmax-sft**。
- **GLM-5.2 + Terminus2 名字确有新仓库，但还不能验收。**`open-athena/nemotron-gym-multichallenge-{vanilla,advanced}-v2-glm52-terminus2-traces` 于2026-08-23上传，各6个Parquet，revision分别 `ef4c2f32a99b195859527d8a3a90aa3331d22aa9` / `6bfd72688ec08c3eb1b88ba2bb592d45944348b0`。本轮公开元信息**没有README、license或采集/成功说明**，未读行正文；不能仅凭仓库名认定模型身份、可恢复终端环境或成功率。[vanilla固定树](https://huggingface.co/datasets/open-athena/nemotron-gym-multichallenge-vanilla-v2-glm52-terminus2-traces/tree/ef4c2f32a99b195859527d8a3a90aa3331d22aa9)、[advanced固定树](https://huggingface.co/datasets/open-athena/nemotron-gym-multichallenge-advanced-v2-glm52-terminus2-traces/tree/6bfd72688ec08c3eb1b88ba2bb592d45944348b0)
- **Qwen3.7-Max 的 Terminal-Universe 是新研究，但未确认可下载训练发布。**[2026-09-03作者论文](https://arxiv.org/html/2609.04148v1)用Qwen3.7-Max在重建环境重采，生产32K训练示范；solution rollout用Claude Code。当前论文页未给训练集下载链接，HF按名称搜索无结果；37.3K是重建环境数，不是已核下载行数，也不能列成现成Terminus2池。这是本轮“尚未找到”，不是断言作者从未发布。
- **[Nex agent-sft](https://huggingface.co/datasets/nex-agi/agent-sft/blob/d8d4de5643f9fe9d3fc3f89b3d55b8709ddc35c9/README.md)** 最后更新2025-12-09，教师DeepSeek-V3.1-Nex-N1；69,008总条中agentic_code24,796；ODC-BY。真实messages/tools/generator可下载，但没有证明为Terminus2原生，也不是更新教师，排在本轮精选之后。
- **GLM-5.3 SWE-smith数据属于代码任务而非本题终端主池。**[公开可读卡](https://huggingface.co/datasets/liangzhidanta/claude-code-glm53-swesmith-trajectories/blob/73041e4958062af2311d1ec24cced5f4a932f530/README.md)明确Claude Code2.1.258、1,003 usable V1，另有同任务compaction示范；卡又自称PRIVATE archive、license=other。不能因可读或模型新就当作已许可的正式发布，更不能当Terminus2。

## 开放轨迹与开放教师权重分别记录

DeepSeek-V4-Pro及0813本身已有[官方公开权重](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/tree/72e1d3230f6c080a530b0a1d46f8eb4602340597)（本轮核见safetensors）；不能误列为闭源教师。上表数据公开也不自动等于其license已明确。

**闭源教师、轨迹公开**的另列例子是 [InferenceBench-Trajectories](https://huggingface.co/datasets/aisa-group/InferenceBench-Trajectories/blob/ea68d73df80985099ef58b342e50c465214d6e7b/README.md)，2026-06-21、Apache-2.0、269个run，含Claude Opus/Sonnet、GPT系列，同时也有GLM/Kimi。它是**评测运行日志**：Claude/Codex/OpenCode三种harness，在H100上做2小时LLM推理服务优化；metrics可能缺失、存在invalid_or_reward_hack字段，不是预筛成功SFT，不是Terminus2，不能整包当当前终端主训练数据。对确有缺口的闭源教师数据应维持同样的环境/协议/结果资格标准。

## 当前建议

**优先补核GLM5.2+Terminus2两项新线索的元数据/授权/来源；同时新增审OpenThoughts100K的小规模实际结构和环境映射；把TMax成功子池记为更强开源教师的跨agent候选。现有Nemotron保持已审基线地位。**缺文档不是不兼容的证明，只是尚不能验收；当前没有核到同时满足“当前最新教师、明显强于本项目Base、原生Terminus2、清楚成功语义、环境可恢复、许可清晰”的一键替换池，不应为教师更新放宽主数据资格。

本轮没有查看正式TB2任务答案或评测日志正文。后续所有池都须排除本题正式TB任务及其改写/派生；按task/repo/family划分独立dev，并与Base作同协议对照。TMax作者[§5.1](https://arxiv.org/html/2606.23321v1)恰有直接反例：较老大SFT混池会降低Qwen3.5-9B表现，甚至Qwen3.6-27B生成的TMax SFT也未保证提升该学生。因此“教师强/来源新”是筛选线索，不是效果保证。
