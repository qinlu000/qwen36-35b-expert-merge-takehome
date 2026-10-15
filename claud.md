# 项目记录

## 协作约定

- 代码保持 KISS，以 research 为导向，不做过度工程化或防御性编程。
- 使用 Git 版本管理；提交信息不添加 Codex coauthor 信息。
- 每次工作更新本文件。

## 2026-10-15：题意确认

- 当前仅理解题目和澄清执行条件，尚未启动训练、评测、租用算力或公开发布。
- 任务是可复现的多专家训练与权重/adapter 合版实验。指定基座为 Qwen/Qwen3.6-35B-A3B；算力不足时允许使用同系列约 7B 级模型，例如 Qwen3-8B，并说明原因。
- 训练前固定模型 revision、tokenizer、chat template、依赖，以及四项 benchmark 的官方来源、版本、split、完整任务清单、主指标和评测配置。
- 四项为 SWE-bench Pro v2-hard、HLE、ASI-Bench、Terminal-Bench 2.0；指定版本不可获取时须先联系面试方，不能自行替换。
- 专家数量、划分、数据、训练方法自行设计；须真实训练所有专家，设置至少一个可解释对照，并比较至少两种合版方法或做关键配置消融。
- 训练数据须披露来源、许可、清洗、去重、难度与防污染措施；使用独立开发集调参，冻结权重后才做最终评测。评测答案、参考补丁、隐藏测试及测试反馈不得用于训练或选择 checkpoint。
- Base 与最终合版模型必须完成全部四项全量评测；各专家至少完成目标 benchmark 的全量评测。每项内配置与预算一致。
- Terminal-Bench 2.0 使用 Harbor/Terminus-2，按题定资源、采样、上下文与超时设置，报告五次运行的均值和标准差。
- 以本次实测 Base 为基线，四项百分制主指标等权宏平均提升目标为 3 个百分点、优秀参考为 5 个百分点；须报告退化、配对 bootstrap 置信区间、重复运行波动和环境失败。
- 至少分析合版模型 20 个失败案例，并提出至少三个下一步实验。
- 提交独立 GitHub 仓库、所有专家与合版模型的公开 Hugging Face checkpoint/revision、完整配置/脚本/日志/逐任务结果/曲线及源数据，并提交不超过一页的 report.pdf（摘要 150–200 个中文字符、过程、结果）。模型链接按面试通知发送至指定邮箱。
- 用户已确认：剩余 2 天 23 小时（71h），预留半天（12h），核心执行窗口为 59h；本题可额外申请最多 4 张 H100；没有其他附件。

## 2026-10-15：来源与资源预核验

- 用户提供本地 SSH alias `hpc3`。已只读连接；这是 Slurm 集群入口，Singularity 可用，GPU 计算需调度。额外四卡额度已明确，不修改用户现有作业。
- 运行过一次 `sbatch --test-only` 估计四卡调度条件，未提交实际作业；没有启动训练、评测、租用或公开发布。
- 已应用 research 技能，分工核验官方元数据、文档与通用评测实现；没有主动读取 benchmark 参考答案或隐藏测试。来源和边界记录在 `analysis/benchmark_sources.md`、`analysis/terminal_hle_feasibility.md`、`analysis/model_feasibility.md`。
- 基座公开且可访问；候选固定 revision 为 `995ad96eacd98c81ed38be0c5b274b04031597b0`，权重张量总量约 71.90 GB。保存了小型模型配置与模板快照，未下载权重。
- SWE-bench Pro V2 HARD-51 与官方 hard/test 均公开；Terminal-Bench 2.0 有 89 项任务，五次为 445 trials/模型；ASI 有 open seed31415 可本地评分，完整四层为 240 组合/模型。
- 当前模板 README 是 SFT→第二阶段优化路线，与附件多专家合版题面不同；以用户附件为需求依据，不静默切换实验路线。
- HLE 为 gated 数据，需要确认账号权限；官方判分还需可用 Judge API。已检查本机与 hpc3 常用 HF 凭据位置和环境变量，尚未找到；结果仅限已检查范围，不排除用户另存配置。未输出任何密钥。
- 正式协议和完整任务 manifest 尚未冻结；环境兼容性、CPU sandbox 并发、实际吞吐和 API 费用尚未验证，暂不承诺 59h 内可完成全部实验。

## 2026-10-15：待提供的账号配置与入口

- 用户要求列出需要准备的内容并给出链接。当前最小准备项为同一 HF 账号的 HLE 访问授权、HF token，以及可用的判分 API 与费用上限。
- HLE 访问条件需要用户本人查看并接受：<https://huggingface.co/datasets/cais/hle>。创建 token 本身不会自动获得 gated 数据权限。
- HF token 创建入口：<https://huggingface.co/settings/tokens>。当前下载需要读权限，最终在本人账号公开上传模型还需要写权限；权限说明：<https://huggingface.co/docs/hub/security-tokens>。
- OpenAI API key 入口：<https://platform.openai.com/api-keys>；API 计费入口：<https://platform.openai.com/settings/organization/billing/overview>。已使用 OpenAI Docs 核验官方 quickstart 的密钥与计费入口：<https://developers.openai.com/api/docs/quickstart>。
- 凭据由用户存入本机的非 Git 配置文件，聊天中只提供路径及允许的 API 费用上限；不要求粘贴密钥。后续验证 HLE 访问和选定 Judge 的实际可调用性。
- 未替用户接受条款、创建密钥、充值或调用收费 API。

## 2026-10-15：用户凭据鉴权通过

- 用户提供 HF token 与 DeepSeek 官方 API key。已保存到项目之外的 `/Users/caoqinlu/.config/apex-takehome/credentials.env`，目录权限 0700、文件权限 0600。仓库只记录配置位置与验证状态，不记录凭据值。
- HF `whoami-v2` 返回 200，账号 `csminion`、token role 为 write；`cais/hle/auth-check` 返回 200，已获得 HLE 文件访问权限。
- DeepSeek 官方 `/models` 与 `/user/balance` 均返回 200，可用模型为 `deepseek-flash` 和 `deepseek-v4-pro`，余额状态可用；没有测试付费生成、执行正式判分或把账号余额视为授权预算。API 总费用上限已向用户询问，等待回复。
- DeepSeek 配置使用独立变量 `DEEPSEEK_API_KEY` 与 `DEEPSEEK_BASE_URL=https://api.deepseek.com`，避免把该密钥当作 OpenAI 官方凭据。接口依据：<https://api-docs.deepseek.com/>、<https://api-docs.deepseek.com/api/list-models>、<https://api-docs.deepseek.com/api/get-user-balance>。
- 判分器需区分 API 兼容与评分协议兼容：HLE 自定义 judge 需要固定、披露并验证实现；ASI 的 transport override 仍保留任务声明的判分模型，不能直接将 DeepSeek 官方接口当作所有指定 judge 的替代。
- 添加 `.env` / `.env.*` 的 Git 忽略规则（保留 `.env.example`），避免后续将实际凭据文件提交到仓库；提交前已用真实凭据匹配检查暂存差异，未发现密钥值。
- 已完成 ASI 正式 60 项 task_eval 配置的模型字段审计：13 项显式指定 `openai/gpt-5.5`（包括视觉判分），47 项未声明模型；通用默认也为 GPT-5.5。因此保留官方评分配置还需可调用 GPT-5.5 的 OpenAI API 或兼容网关；不能把 README Gemini 示例当成实际需求。证据与边界见 `analysis/judge_requirements.md`。

## 2026-10-15：用户审核完整实验理解

- 用户暂未给 API 预算，要求先整理完整实验要求及 API 用途，供其核对理解。当前不重复催要密钥或执行批量付费请求。
- 完整核对稿为 `EXPERIMENT_REQUIREMENTS.md`，区分题面硬要求、官方实现依赖和候选人设计项，并列出评测矩阵、API 用途、交付物与当前状态。
- 训练与合版本身不要求外部 LLM API；benchmark 作答由被测 Qwen 完成，本地 HTTP 推理接口与商业模型调用是两回事。外部模型主要用于 HLE/ASI 判分，或可选的训练数据合成；仓库鉴权及可选云沙箱另计。
- DeepSeek 不是已选定的被测模型，也尚未正式选为 HLE judge；GPT-5.5 来自核验版本的 ASI 评分配置，并非题面逐字指定。专家数、划分与实验配方尚未定稿。
- 初始 59h 核心窗口包含已经发生的准备时间，不随对话重新起算。当前仍未训练、合版或正式评测。

## 2026-10-15：方案讨论阶段，按用户要求停止执行

- 用户先授权必要 API 正常使用、无需逐次确认；随后最新明确要求：先不写代码，从数据/工程/算法/评测规划，双方讨论方案后再执行。最新指令覆盖当前执行节奏；暂停新增实验代码、模型 API 调用和实验执行，凭据使用授权不等于方案已定稿。
- 在暂停指令到达前，已新增但尚未提交 `scripts/check_deepseek_judge.py`，并完成一次 DeepSeek 生成请求，六个自造样例的 JSON/基础判分检查均通过；392 输入+325 输出=717 token。日志位于 `logs/preflight-deepseek-20261015T093220Z/`。这不是正式 benchmark 或完整 judge 校准；观察到的余额变化为0.00，不代表请求免费。
- 暂停时没有已提交的训练/评测 GPU 作业；没有开始训练、合版或正式 benchmark 评测。既有未提交脚本/日志本轮保留原状，不纳入规划提交。
- 新讨论稿为 `PROJECT_PLAN.md`：推荐先讨论3能力专家（修复/SWE、终端/TB、科学/HLE+ASI）+1混训对照，初始合计6M专家训练token，混训另6M；BF16 LoRA，dense delta平均与TIES，独立dev选配方后正式冻结。
- 正式主矩阵仍强制 Base/最终合版四项全量、专家目标项全量；混训及其他合版候选先在独立dev比较。3专家并不会降低最低四项正式任务总量。
- 核心待讨论条件为专家划分、混训对照范围、CPU/沙箱并发；还没有证明少于57h核心余量可完成所有任务，时间预算只是条件性目标。

## 2026-10-15：按用户要求联网查找可参考方案

- 使用 research 与 ego-browser 技能，只查阅一手论文、作者仓库和官方文档；分工核验数据、精确模型训练支持、合版方法，主线核验完整 Agent 训练配方。
- 同底座参考包括 T-Search（独立语言分支 SFT、DARE 合版、后续 RL/SLERP）、CompoWorld（可执行工具环境与 SFT 规模消融）、QuantCode（领域训练后的工具格式退化）。它们均不能直接证明本题四项提升或四卡排期。
- T-pro 2.1 提供共享 SFT→三个能力 GRPO 专家→SLERP 的完整配方，但基座为 Qwen3-32B、使用32张H100；其 shared SFT 与 domain SFT 接近的结果反而支持本项目保留混训对照。当前没有据此引入 RL。
- 新增 `analysis/references_agent_recipes.md` 与数据/训练/合版专项研究笔记；`PROJECT_PLAN.md` 补充公开数据/训练实现候选及研究依据，专家数、token/rank 和超参没有定稿。
- 数据候选收敛为可追溯 SWE-smith 轨迹、Nemotron skill-based、OpenR1 数学部分；均未完成本项目逐行来源/许可/污染审计，科学工具覆盖仍有缺口。训练实现讨论首选 ms-swift BF16 LoRA/ZeRO-3，备选 Unsloth；明确区分目标模型注册与近邻四卡示例，不将其当作本项目吞吐实测。
- 继续遵守用户暂停执行要求：未新增实验代码、未安装依赖、未下载数据/权重、未调用模型 API、未提交实际 GPU 作业或执行正式评测；既有未提交脚本/日志保留。
- 初始59h核心窗口继续消耗，讨论和联网准备没有重置计时。尚未证明沙箱兼容、CPU并发或完整评测吞吐满足截止时间。

## 2026-10-15：比较本机开发与组内服务器开发

- 用户询问本机开发/HPC训练与组内开发/HPC训练的选择，并指定“80”；按用户进一步指示检查SSH配置，实际Host为`10.123.4.80`和`10.123.4.80-proxy`，没有`80`这个Host条目。已通过实际Host只读连接，未改SSH配置。
- 本机`Darwin arm64`；80为Linux x86_64，整机可见128逻辑CPU、约2TiB RAM，`/data`余约2.8TiB，根分区余约64GiB；`/data/caoqinlu`归本账户且可用于后续规划。整机资源不等于本项目配额。另只读查询可见8张A800 80GB，没有运行其GPU任务；主方案仍按本题四H100预算。
- 80当前PATH未发现Docker/Podman/Singularity/Apptainer/Enroot/nerdctl，本账户无docker组，尚未确认容器运行能力。更正讨论稿此前“本地没有Docker”的歧义：既有检查针对hpc3登录节点，不代表Mac上的安装状态。
- 80无hpc3别名且不能解析HPC域名；使用本机解析出的入口IP可收到SSH banner，TCP路径可达，但鉴权、HPC计算节点模型端点及容器链路未验证。
- 80直连HF超时，经已有远端38080 HTTP代理访问返回200；该端口对应SSH配置中转发到本机7897的路径，长任务联网会依赖本机/隧道持续在线。未建立新转发或移动凭据。
- 工程建议已补入`PROJECT_PLAN.md`：80主开发/CPU处理，本机编辑查看，HPC计算节点训练/推理；固定Git commit，权重就近HPC，80缓存放/data。正式CPU评测需另核容器、配额和网络；128CPU按TB每trial32CPU至多保障4路，不能据此宣称解决全量排期。
- 仅读官方Docker多平台与Slurm批作业说明；两种开发方式均可提交不依赖交互SSH会话的批作业。未新增实验代码、迁移仓库、安装依赖或启动实验。

## 2026-10-15：工程分工确认，工作区落到80的projects

- 用户确认80主开发/HPC训练推理/本机编辑查看，并进一步要求项目放在`projects`。确认80已有`/data/caoqinlu/projects`后，开发目录最终为`/data/caoqinlu/projects/apex-takehome`。
- 用主分支Git bundle保留已提交历史，建立`/data/caoqinlu/repos/apex-takehome.git`同步入口与80普通checkout；本机配置`lab`远端，80的`origin`使用该bare仓库。仅迁移项目主分支历史，没有迁移应用内部refs。
- 数据/缓存/运行产物目录为项目下`artifacts/data`、`artifacts/cache`、`artifacts/runs`，添加`/artifacts/`忽略规则。最初建立的`/data/caoqinlu/apex-takehome`和`/data/caoqinlu/apex-artifacts`已移动到最终位置，未留下第二套开发目录。
- 未提交的`scripts/`与`logs/`、仓库外凭据保留在本机；没有安装依赖、修改SSH/代理配置、使用80 GPU或启动训练/合版/正式评测。
- 工程位置确认不等于全部实验设计已确认；数据/算法/评测讨论继续。HPC按冻结commit执行，HPC到80 Git入口鉴权、正式沙箱与稳定外网仍待处理。

## 题目来源

- 用户附件：`/Users/caoqinlu/.codex/attachments/20b2f4c3-6e03-4746-a389-d488086d7780/Pasted text.txt`。
- 初次理解记录以附件为准；后续官方来源和可用性核验见 `analysis/`，各记录明确区分文档证据与实际运行结果。

## 2026-10-15：补查与笔试直接相关的公开实现

- 用户再次询问网上思路与已有可参考材料。补做针对原题/四项组合的搜索，新增 `analysis/references_takehome_reuse.md`，本次直接在80主开发目录写文档。
- 官方模板直接相关，但目录树只是示例，且README为SFT→第二阶段路线，不能覆盖附件多专家合版要求。
- 找到公开9B实验模型卡，明确同四项benchmark并有真实训练记录；其v6披露正式评测中止、无该checkpoint benchmark分数，旧卡只有TB89题单次。配套候选人代码本次公开访问404，不能称为可复现完整解答。
- 新核同底座Occamy双专家训练→均匀参数合版→后续优化结构；其约403M token全参SFT和RL预算不直接适配本题。社区同底座SLERP案例丢弃视觉侧，仅作张量布局工程参考。
- 本轮未发现本题35B多专家合版与四项全量的完整公开成品，不据此断言不存在。建议复用ms-swift、MergeLM/TIES、官方四项runner，研究设计和独立数据仍自行完成。
- 未写实验代码、安装依赖、下载权重/训练数据、读取本题逐题答案或运行模型/API；实验方案仍在讨论阶段。

## 2026-10-15：核验Occamy是否有代码

- 用户追问Occamy代码。已核Occamy本体主要提供介绍/网站/report PDF，真正公开的agent RL实现位于其链接的Dressage，具有训练层和启动示例。
- Dressage固定代码3e3142fe8ea07e4504c3b20a936a4c201a3de44c含准确Qwen3.6-35B-A3B的Claw训练脚本，但为4节点×8GPU=32卡的GRPO，不是Occamy全阶段复现或本项目四卡配置。
- 未核到Occamy两个专家的SFT/HDPO/merge/SAO整套专用脚本与配置，不能将底层框架开源写成完整配方开源。补充证据到直接参考清单。
- 本轮只读公开代码/目录，未安装、下载权重/训练数据、执行脚本或改变实验方案。

## 2026-10-15：四H100的Dressage简化方案v2，仅规划

- 用户明确要求参考Occamy/Dressage代码，列清可复用/自实现并适配四卡和剩余时间，继续不写实验代码。完成 `analysis/dressage_reuse_plan.md`，PROJECT_PLAN顶端标明最新建议与旧预算差别。
- Dressage按固定3e3142f逐模块核验：轨迹schema、Qwen36 tokenizer辅助、mask一致性和产物字段可小范围借用；multi_segment、convert_samples、Harbor在线DataSource/rollout含Slime/RL语义，不直接搬入离线SFT/正式评测。mask默认只注册qwen3_5，不能假定现成覆盖Qwen3.6全部assistant轮。
- 拟用ms-swift BF16 LoRA、三个独立专家+同数据混训对照；默认专家processed token共3M（0.9/0.9/1.2M），混训3M，累计6M，替换初稿12M默认。该规模不是充分训练或提升保证，冻结前需按真实吞吐与长度分布统一缩放。
- 合版从六候选收敛至AVG与固定density0.2的TIES两个起点（scale1），有余量双方各加scale0.5，最多四候选；独立dev选唯一结果，保留视觉侧。混训只做dev时不声称四项正式优于混训，并披露有效秩差异。
- 自实现拟限数据适配/manifest/mask、dense delta合版适配、官方评测薄封装、统计与交付；不写新trainer/agent平台，不引入HDPO/SAO/GRPO或在线rollout。
- 约18:32按最初起算估计核心余55–56h，提出3h环境数据协议+8h训练+3h合版dev+36h正式评测+5h交付的条件预算，保留最后12h。专家目标全评、Base/合版四项全评和TB五次均不缩减。
- 强制资源门槛仍为容器与额外CPU、四卡计算节点及稳定模型端点/外网、数据与judge。TB若均30分钟，36h理想最低需19路/608CPU/912GB RAM；80即使128CPU全归本项目仍不足。ASIGPT-5.5图文评分未落实，DeepSeek接口测试不能替代。
- 仅读公开源码并更新方案文档；没有创建实验脚本、安装依赖、下载权重/训练数据、调用模型API或启动GPU/benchmark任务。

## 2026-10-15：直接使用Dressage/Slime的补充核验

- 用户继续问能否直接用Dressage。已修正此前仅从agentRL示例判断的范围：其固定Slime aaf5c2092b01219fa0d5c2d323741d409086ca32已有35B MoE离线SFT入口及本地messages/mask读取，不需要自写SFT loss/训练循环或在线agent生成答案。
- 近邻SFT脚本为Qwen3.5-35B-A3B、单节点8GPU/EP8且含CPU optimizer offload；框架支持colocate/小卡数，但不是目标3.6四卡LoRA实测。LoRA接线/保存恢复/HF导出仍未核实，不写成不支持。32卡不是框架最低要求。
- Docker在quickstart中是可选，不能将无Docker视为框架绝对障碍。Dressage的Harbor extra0.18与SWE V2新版协议应分环境处理。
- 简化方案追加直接采用框架的候选路线与未来2h兼容验证门槛；如果需要改Megatron核心再回到ms-swift。当前没有擅自切换主训练方案、写实验代码、安装或跑任务。

## 2026-10-15：用户重点为LoRA，收窄Dressage采用建议

- 用户澄清主要需要LoRA。分工核验固定provider/optimizer/checkpoint/HF转换及当前官方main、未合并PR；SFT入口与LoRA闭环区分记录在 `analysis/dressage_reuse_plan.md` 第10节。
- Dressage仍固定3e3142f及Slime aaf5c209；默认provider没有核到LoRA transform，冻结扩展点不是adapter注入证据。Megatron的q-lora-rank/kv-lora-rank为MLA架构参数。Bridge浮动依赖不能当作当前能力已在固定组合接线的证明。
- 找到实际MoE LoRA代码Slime PR #2440（Open，头a988346413582c1567330675592286387168b9a9）；支持注入/冻结/保存/merged HF设计，但adapter是自定义Megatron分片且无PEFT转换器，示例Qwen3-30B八卡GRPO，尚无准确模型四H100离线SFT验证。PR #1865 dense-only，#1140也仍Open，不能代替本题证据。
- 结论收敛：LoRA为重点时维持ms-swift/PEFT BF16 SFT主线建议，Occamy供多专家合版思路，Dressage供轨迹参考；不把更新Slime main写成即用LoRA，不为截止窗口加入未合并Megatron适配工作。训练/合版/评测方案尚待共同讨论确认。
- 仅更新文档；未写实验代码、安装依赖、下载权重/训练数据、调用模型API、提交GPU任务或执行评测；本机既有未提交scripts/logs保持不动。


## 2026-10-15：用户确认采用ms-swift

- 用户明确选择ms-swift，已将PROJECT_PLAN与简化方案状态更新为框架已确认，训练按ms-swift + PEFT / BF16 LoRA路线规划。Dressage不作为训练运行依赖，Unsloth不再与主线并列待选。
- 此选择仅确认训练框架；专家分工、数据清单与预算、LoRA目标/rank、合版候选和正式评测资源仍待整体讨论定稿，具体版本与ZeRO-3配置尚未实测锁定。
- 保持先规划不写实验代码的既有要求。仅修改方案与本记录，未安装依赖、下载模型/训练数据、调用模型API或启动训练/评测。80主开发、HPC四H100计算、本机编辑查看的分工保持。


## 2026-10-15：调研数据来源并修订专家划分建议

- 按用户要求使用research流程，三路并行核验修复数据、科学推理/执行池和专家训练参考，主线核终端数据并综合为 `analysis/data_expert_recommendation.md`（v3）。新增三份数据专项及专家划分笔记，PROJECT_PLAN/旧v2顶端注明新旧优先级。
- 新建议按行为划三专家：E-code→SWE，E-exec→TB+ASI，E-reason→HLE，替换早期E-science兼顾HLE+ASI；exec内保留科研子预算与独立dev。三专家+一次混训、累计6M processed token预算暂不扩大，拟分0.9/1.2/0.9M，混训3M；只是待讨论起点。目标全评总量不因划分改变。
- 修复主审计候选升级为NVIDIA Open-SWE-Traces v1.1 mini/Qwen3.6轨迹，具有repo/license/language/instance/messages/tools/resolved；上游SWE-rebench-V2明确仅排旧SWE-bench，Scale-SWE也仅声明排Verified，故本题Pro关联需自行排除。SWE-smith新多语言发布只有任务环境，不是现成轨迹；旧traj只作补充。
- 执行主候选为Terminal Corpus skill-based；scientific_computing/data_science可按固定文件目录选择，但不是独立config，也没有原生domain/resolved字段。OT-Agent-SFT-100K SuperUser为可选补充，实际API当前返回94334行而卡称100K，未下载核差异。
- 推理主候选为OpenScienceReasoning-2（CC BY4，跨STEM/人文等，有长CoT），数学沿用少量OpenR1。OpenScience缺逐题来源/正确性标签，作者多数投票不是独立证明；文本训练不代表已覆盖HLE图像。OpenThoughts/OpenMath TIR留备选，MegaScience暂不作主源。
- 参考Occamy互补分支、OT-Agent来源/多轮消融、T-pro shared/domain SFT对照与Nemotron过滤/混合结果；不把论文大规模全参或RL结果外推成本项目LoRA收益。保持同数据混训、任务组切分、四类独立dev和正式结果不选参。
- 仅查询公开论文、数据卡、文件索引和schema/版本元数据，未读取正式答案/补丁/隐藏测试、下载Parquet或权重、写实验代码、安装、调用模型API或启动训练/评测；全部候选尚未做逐行污染/许可审核、格式转换或实际token统计。


## 2026-10-15：说明终端与科研执行共同分组的依据和局限

- 用户追问TB与ASI为何合为E-exec。补充到数据方案v3：共享的是环境状态、工具执行、反馈纠错及产物核验，不代表科学方法/数值验证可由shell替代，也不代表官方工具协议相同。科研数据与独立dev继续单列。
- 明确SWE也共享执行行为，所以三分法不是唯一或已验证最优；单列修复为集中仓库/补丁/回归专长。固定总token时三对四专家主要省启动/保存/加载/管理，不能宣称显著节省训练计算或正式评测量。科研池成熟、重视归因时四专家仍是合理备选。
- 只补充方案解释和本记录，没有改变待讨论状态、下载、写实验代码、安装或执行训练/评测。

## 2026-10-15：评估当前三专家划分是否合适

- 用户问当前三分法是否合适。当前判断维持E-code（仓库修复）、E-exec（终端/科研执行）、E-reason（广域学术推理）作为首轮推荐，理由是行为/产物边界与现有数据池可以对应，而非四卡显存或固定总token节省。
- E-exec中的科研覆盖与终端/科研干扰仍是最弱假设，保留两桶数据配额、独立dev和分项结果；四专家主要在科研数据成熟且出现稳定冲突时有价值。目前无证据证明四份更优，也不宣称三份已验证最佳。
- 这是对待讨论方案的判断，尚非用户批准恢复实现或执行；本轮仅更新此记录，没有下载、写实验代码、安装、API调用或训练/评测。


## 2026-10-15：用户确认三专家分工与直观名称

- 用户确认当前三个划分，并反馈直观名称更清楚。当前名称统一为仓库修复专家（SWE）、交互执行专家（TB+ASI）、学术推理专家（HLE），替代对用户展示的E-code/E-exec/E-reason。交互执行专家仍保留终端/科研两桶数据和独立dev。
- 更新PROJECT_PLAN、数据方案v3和旧v2入口，区分已确认的框架/专家分工与待讨论的数据来源/配比、训练超参和评测执行条件；历史研究笔记的旧称保留作来源记录。
- 此确认不代表恢复实验执行。仅更新文档，未下载数据/权重、编写实验代码、安装、调用模型API或启动训练/评测。


## 2026-10-15：确认截止并编排55h核心与12h缓冲

- 用户要求规划时间，并通过异步问题确认截止10月18日14:20北京时间；目标10月18日02:20完成，最后12h保留。时钟实查19:08:33、19:10:40 CST，名义开工19:20，后续讨论延迟须从核心窗口扣除。
- 方案写入PROJECT_PLAN当前时间计划，代替旧v2时间预算：5h环境/数据/薄工程到10/16 00:20，8h三专家+混训到08:20，3h合版/dev到11:20，36h正式全评到10/17 23:20，3h交付核对到10/18 02:20；报告草稿、上传与分析前移并行。
- 今晚22:20设资源判断点，四卡LoRA闭环/吞吐、容器与CPU配额、端点网络、HLE/ASI评分及数据路径需成立；未成立则重估资源/工期，不把表格当承诺。
- 6M processed token在8h、20%非训练开销下要求四卡整体260.4 tok/s；低速时训练前同比缩放专家和混训，不能只砍对照。合版仅两预设候选，额外网格不纳入核心。
- 正式矩阵和所有预算保留。TB36h最低37.1 trials/h，若30min平均理想至少19路608CPU，80即使独占128CPU也未证明可行。四卡推理与ASI任务共用144 GPU-hours。10/17 17:20后不启动新的3h agent，预留执行与评分长尾；正式运行6h后只按队列/耗时更新完工预测，不按成绩调参。
- 仅并行审计既有要求与算术、更新文档；没有安装、下载、写实验代码、调用模型API、启动GPU或评测任务。此排程尚不代表恢复执行的授权。


## 2026-10-15：解释训练与评测预算为何相差较大

- 用户问8h训练与36h全评的差别。解释当前训练人为限制为四次累计6M processed token，SFT直接学习已有轨迹、可并行算序列loss；评测需自回归生成、多轮工具执行与验证/评分，且各项比较Base、对应专家、合版三对象及TB五次。LoRA小不等于底座计算可以忽略。
- 用条件算例说明：HLE7500题若平均输出2000 token，仅输出15M；TB1335次若均30min，共667.5任务小时，四路约166.9h，36h理想至少19路/608CPU，未含长尾和其他项。明确两项都是倒排预算，不是实测；8h不保证训练充分，36h可能仍偏紧，资源条件未成立。
- 补充解释到PROJECT_PLAN，未改变专家/正式题量或恢复实验执行。仅更新文档，没有下载、安装、API调用、编写实验代码或训练/评测。


## 2026-10-15：明确先验收数据，现成轨迹为主、自跑补缺口

- 用户问是否应先找数据、是否需要自己收集任务自己跑。说明目前只有来源/schema核验，下一步应在准备时段优先验收实际代表样本、统计可用独立任务/token/覆盖并做来源分组，和资源验证并行，再锁训练量。
- 三专家主线均优先现成轨迹/推理解答，不重生成整池；任务环境无assistant过程则需要另跑教师。自己执行集中于可映射训练样本的抽样复现、独立dev任务/评分验证及明确覆盖缺口的小量原创任务。新增轨迹执行验证，计入原预算；不从正式题派生。
- 补充到数据方案v3和PROJECT_PLAN，区分上游验证、项目抽样复现及未知状态，不把抽样通过写成全量已验证。仍未下载数据/权重、写实验代码、调用API、启动训练或评测；本轮只更新方案。


## 2026-10-15：按用户指示先下载候选数据，暂不抽样复验

- 用户明确“先不用抽样复验，先把数据弄下来”。执行范围恢复为候选数据下载和必要下载辅助脚本，尚未授权启动训练；本次不读样本、执行复验、生成教师轨迹或评测。
- 80的/data实查可用约2.9TiB。四组来源固定：Open-SWE 1db674…的v1.1 mini/Qwen3.6；Terminal a1667…全部skill-based（不含adapters）；OpenScience 174b02…全train；OpenR1 e4e141…仅default data/train-*（不含all/extended）。共81文件24,982,461,699字节，包含README/分布说明。
- 写入 `data_sources.json` 和 `scripts/download_data.py`；四线程curl断点续传，核字节数及上游LFS SHA-256，原文件在80 `artifacts/data/raw/`，日志/回执在 `artifacts/data/`，不入Git。数据文件不解码、不执行；无额外Python依赖安装。
- 下载经80现有127.0.0.1:38080 HTTP代理，公开数据未使用/迁移HF凭据；进程独立会话运行、PID写download.pid，仍依赖已有Mac代理/SSH转发在线。当前已启动，完成情况以后续回执为准，不能把已启动写成已完成。
- PROJECT_PLAN和数据方案v3标明此次优先级覆盖旧“先抽样验收再下载”的建议。没有使用GPU或调用模型API；Mac既有未提交scripts/logs不动。

- 下载路径优化：HF元数据仍经现有代理，已确认官方us.aws.cdn.hf.co可由80直连，数据本体改为官方CDN直传。为单个15.7GB文件启用分段续传，将Ubuntu aria2/libaria2/libssh2/libc-ares包仅解压到artifacts/tools/aria2，不修改系统或训练环境；Python依赖仍未安装。全文件继续以固定revision/LFS SHA校验，不使用第三方数据副本。此前仅探测hf-mirror速率，未用其下载实际候选文件。


## 2026-10-15：暂停下载并澄清各benchmark的harness规则

- 用户先说“等一下”质疑跨harness轨迹复用，已于19:39:51 CST前暂停自己创建的下载进程组540141；仅停止该组，未删数据。6文件/1,769,702,489B完成校验，实际落盘约8.18GB含分段；其余未完成，最终全量回执未生成，状态存artifacts/data/download_state.json。没有恢复下载。
- 用户随后提供题面截图，明确无需四个benchmark同harness，只需同一benchmark的Base/专家/合版保持同配置。已确认该理解，补入PROJECT_PLAN与数据方案v3；交互执行专家可分别保留TB/ASI两套原生协议条件训练，不必统一成一种工具接口。匹配的是协议，训练任务仍需独立。
- 只查官方工具代码确认：Terminus2是持续tmux+JSON keystrokes/duration/task_complete；SWE固定配置bash(command)每次新subshell，状态与结束/观察规则不同；Open-SWE只有mini谱系证明，未证实际协议完全相同。跨harness旧轨迹可保原协议作辅助，但不能直接冒充目标原生示范。
- ASI具体adapter尚未锁定：direct_llm单次completion后框架执行，无模型工具反馈；CLI adapter另有协议。先固定ASI入口再定科研轨迹资格，不改正式协议迎合数据。上述源码核查不读取任何任务答案或样本，不执行复验/训练/评测。
- 当前将此前授权产生的下载清单/辅助脚本纳入Git，原始文件仍在gitignored artifacts；本机先前未提交check_deepseek_judge脚本和日志保持不动。


## 2026-10-15：说明合版模型如何接各benchmark的harness

- 用户问合版模型的harness。明确合的是参数，不合agent框架：同一固定合版权重分别接SWE LockedMiniSwe、TB Terminus2、待锁ASI adapter与HLE协议；每项与Base/目标专家配置预算一致，只替换模型权重/标识。
- 训练样本保留原协议上下文与工具定义，多协议遵循和合版后的格式/执行退化由独立dev验证；正式阶段不切专家adapter、不做任务路由、不为合版增加特殊补救prompt。已补充数据方案v3。
- 下载继续保持用户“等一下”后的暂停状态，已下载和分段文件保留；本轮只更新解释文档，没有恢复下载、读取样本、训练或评测。


## 2026-10-15：按四项benchmark补查训练数据

- 用户要求联网查面向四项的训练来源。并行核作者数据卡、论文、代码与HF文件/schema；新增综合清单analysis/benchmark_training_data.md和SWE/ASI/Terminal专项证据，链接至PROJECT_PLAN及数据方案v3。
- SWE新增SI2CA standard（10,780同题Python轨迹，明确bash(command)）及Orchard备选；不据mini框架同名宣称观察/结束协议匹配，也不自动替换已固定Open-SWE版本。Terminal主线仍是skill-based；新增Nex Agent-SFT的agentic_code多轮消息备选（ODC-BY，未证Terminus原生），Endless约2500个Harbor任务环境需目标协议补采，代码与数据许可分开记录。
- ASI新发现D3-Gym及其现成32B科研推理/程序SFT（2,153条、约72MB），是值得补充的候选；公开instruction/input/output不证明多轮工具反馈，训练到repo映射/上游许可/ASI同源仍待核。AutoSDT备选，SciForge仅方法/环境，不把未核发布写成已获训练池。
- HLE维持OpenScience跨学科推理为主、OpenR1补数学；补查Nemotron-Science-v1和仅50条公开图文题的Multimodal-STEM-HLE++，不自动采用或据营销宣称效果。现有文本主线仍有图像训练覆盖缺口，HLE正式test及其重标注/解题轨迹不作训练。
- 保留三专家与原token预算。本轮只提供来源/协议证据与建议，未读数据行/参考答案/隐藏测试、未恢复暂停下载、未下载新池、调用模型API、安装或启动采集/训练/评测；新候选没有进入data_sources.json。


## 2026-10-15：澄清候选轨迹尚未确认与目标harness完全一致

- 用户追问是否一致。重新对照既有一手证据并独立复核，明确此前清单是能力相关候选，不是已通过目标协议验收的训练池。
- SWE只确认mini谱系及部分bash字段，未核齐版本/状态/观察/提交；TB确认同属Terminus2但未核齐具体版本/模板/观察/结束；ASI adapter未锁，D3静态推理+程序不能称原生多轮轨迹；HLE静态问答应适配模板/thinking/答案格式，仍有图像覆盖缺口。
- 综合清单增加明确的匹配状态表；主源资格需模型可见动作、状态、观察和结束语义相容。仅序列化差异可无损转换，真实协议差异保原上下文作辅助或在独立任务上另采，不能改字段冒充。
- 本轮仅公开源码回查和文档更新，未读数据行、恢复下载、安装、写实验代码、调用模型API或执行采集/训练/评测。


## 2026-10-15：区分题面指定的评测流程与可选择的agent

- 用户问四项是否都未规定harness。回读原题及固定官方README：TB明确Harbor（Terminus-2）；SWE题面未强制唯一mini，V2官方同时给LockedClaudeCode、LockedMiniSwe、LockedCodex；ASI支持官方契约下agent/adapter选择；HLE需固定披露工具/模态/抽取/判分，无唯一题面agent。
- 修正此前可能过严的表述：LockedMini是当前候选方案，并非题面唯一规定；冻结前可以参考已有数据选择合规agent。官方任务/环境/评分及V2 locked protocol仍须遵守，同一benchmark全部模型使用同配置，训练前冻结。
- 训练数据与目标harness匹配是工程偏好，不是题面硬性要求。可保留原协议辅助迁移；不能伪造工具反馈或将不同状态语义机械改名。此澄清没有更换已固定版本、实际选定新agent或授权恢复执行。
- 更新综合数据清单、专家方案与SWE专项措辞；只读公开入口和原题，无数据行读取、新下载、API生成、安装、代码实现或实验执行。


## 2026-10-15：确认按数据兼容性简化agent选择的边界

- 用户提出Terminal轨迹对齐指定harness、其他项沿用源轨迹harness的理解。确认可作为工程方向，进一步说明Terminal的硬性指定针对评测，训练只优先Terminus2轨迹，并非禁止其他协议辅助数据。
- SWE/ASI可优先复用源agent/工具协议，但须接官方目标任务环境、权限/预算与评分/产物契约；不能直接搬源benchmark替代目标，也不能从D3静态程序数据推断已有完整多轮agent。HLE按静态问答协议。训练前冻结，同项全部模型一致，无需为同源重采全部数据。
- 补入综合方案；本轮仅解释与文档记录，下载继续暂停，没有代码、采集、API生成、训练或评测执行。


## 2026-10-15：解释benchmark split与全量评测不矛盾

- 用户问split是否与全量矛盾。明确split决定官方评测分区，全量要求该指定范围完整，不是train/dev/test全部混评，也不是允许自行抽样。任务清单训练前冻结，同项全部模型一致。
- 当前范围精确区分：SWE hard为config、test为split，完整51项；HLE完整test2500；TB2固定2.0全部89项并五次；ASI候选open seed31415全部60项目×四个B条件，open/protected、seed、B层分别记录，不用split名义缩减。
- 补入需求文档，未变更既有评测范围、恢复下载、写实验代码或执行任何训练/评测。


## 2026-10-15：收敛执行前真正需要考虑的事项

- 用户问“所以哪些地方需要考虑”。将近几轮split/harness/来源讨论收敛为六项：完整评测范围、各项agent、数据兼容性与覆盖、独立性/许可、训练配额、全量评测资源链。
- 三专家和ms-swift不重开；优先未决为ASI adapter/科研监督定位，以及容器/CPU并发/本地模型服务/HLE图文/ASI Judge链。SWE mini与Terminal skill-based继续为候选优先方向，精确配额待实际可用量统计。
- 提醒同项所有模型公平一致、合版固定权重；不要求四harness统一、不要求全部轨迹重采、不据正式题调参，不扩大训练分支。21:10 CST实查时钟，仅用于识别排期仍在流逝，未把旧55h窗口当剩余时间。
- 写入PROJECT_PLAN当前决定清单并更新本记录；下载继续暂停，没有新增数据读取/下载、API生成、代码或实验执行。


## 2026-10-15：按用户授权推进数据与工程准备，问题集中留档

- 用户明确“按这个方向推进，有问题先记录，之后一起讨论”。本轮恢复并完成原四源81文件/24,982,461,699B下载，失败0；另下载固定D3-32B候选2文件/72,176,365B。全部原文件在80 ignored artifacts/data/raw，最终回执已生成；没有把原始数据或密钥提交Git。原暂停状态已被此次授权覆盖。
- 完整Parquet metadata行数：Open-SWE95,291，Terminal139,841，OpenScience1,600,812，OpenR1 default93,733；D3 JSON2,153。各源最多2条真实训练样本做结构检查和固定tokenizer长度检查，不执行样本命令/代码/测试，不读取正式benchmark答案或隐藏测试。
- 实际确认Open-SWE bash(command)/returncode-output/提交及subshell提示、Terminal Terminus2 JSON动作族；原消息需规范化，现拟8K无法直接容纳所查完整交互轨迹（Terminal21,174/29,685，SWE40,320/18,933 token）。这些是有限样本，不外推质量/长度分布。OpenScience/D3缺逐行来源映射，Terminal缺统一成功标签，问题保留。
- 新增configs/data_exclusions.json与scripts/audit_swe_metadata.py，只读SWE repo/license/instance_id/resolved。全39片95,291行有39,540种repo-instance组合，重复组合55,751行；resolved1为32,231行。对固定Pro全部11repo精确匹配为0、缺repo0，但fork/改名/PR/其他benchmark关联仍未查完，不宣称已去污染。脚本已实际运行；新增忽略Python cache。
- ASI入口方案明确：优先官方opencode_cli，备选pi_cli，提供版本/命令/预算与产物契约草案，不先自写agent。seed31415本地non-official与seed42官网/Docker路线差异留讨论；没有擅自换split或启动正式任务。
- 基础设施实查H10080GB、HPC QoS每用户192CPU且已有12CPU，80共享128logicalCPU，TB乐观最多9路尚未扣其他任务；若平均30min仅TB约74.2h，原36h假设未获资源支持。80缺容器后端、CPU-only政策和正式模型端点仍待验证。未提交Slurm、占本题GPU或修改既有作业。
- 实际建立仅loopback的临时Mac双SSH桥接，80经Mac/hpc3收到本人已知节点SSH banner，完成后精准关闭自建隧道并核端口释放；只证明短时TCP路径，未证明模型HTTP/流式/长期稳定。
- 精确ms-swift注册model_type=qwen3_5_moe/template=qwen3_5与r16目标regex有源码依据，310权重键/估算21,166,080 LoRA参数未实测；HPC现成Torch2.11/Transformers5.15.1/PEFT0.20及准确架构config CPU导入成功。完整项目训练栈、模型加载反向/导出和四卡吞吐仍未验证；未下载基座权重或安装/修改用户环境。
- 固定基座5个tokenizer/processor元数据文件已下载校验；80现成环境在禁GPU、离线模式下处理32x32自造图像成功。仅证明图文预处理，不等于模型多模态评测。
- 本轮DeepSeek合成Judge接口检查共16次（8例初版+8例字段提示修正），prompt6066/completion951共7017token。初版yes/no与confidence8/8、完整strict schema仅2/8；明确五字段JSON例子后8/8通过。保留两版请求/响应与失败记录并同步80，未用正式题校准、不声称官方Judge等价。ASI GPT-5.5图文评分凭据仍缺；未将DeepSeek偷偷替代。
- 问题统一写analysis/open_questions.md，数据/ASI/基础设施/训练/HLE五份readiness证据与source_snapshots/preparation_checks_20261015.json链接进入当前方案。正式训练和全量评测尚未启动；准备进展不代表全部数据合格、环境ready或原排程可达。Mac既有未提交logs/和check_deepseek_judge.py保持原状。


## 2026-10-15：向用户解释四类待讨论项

- 用户标注上一轮“CPU/容器、ASI判分、长轨迹、来源映射”并要求解释。本轮仅解释与记录，不启动新实验。
- CPU/容器：GPU推理以外还需独立任务环境；上轮9路仅乐观资源上限，若1335trial平均30min则约74h是假设算例。80无已用容器后端、HPC Singularity需实际任务语义检查，不能把有SIF等同全评ready。
- ASI Judge：固定版本部分任务需GPT-5.5且含图片；缺的是对应服务可用性/凭据与协议确认。DeepSeek可研究用于明确披露的其他文本Judge，不等于可替换ASI原配置。
- 长轨迹：实际所查交互轨迹约19K–40K，原8K只是假定。直接截尾会丢状态/后续修复/提交；方案在完整短轨迹、保留必要上下文的完整回合窗口及提高长度间选择，需真实吞吐与长度分布，不重采整池。
- 来源映射：把发布行对应到原任务/仓库/论文/协议与许可，按任务族划分和排除评测同源；D3/OpenScience字段不足是核查盲区，不代表已发现污染或全部不可用。可恢复映射的优先，其余记录局限或换可溯源候选，不伪造来源ID。
- 前两项主要影响正式全评能否完成，后两项影响训练数据如何组织与结果可解释性。本轮没有下载、API调用、训练或评测。


## 2026-10-15：估算用DeepSeek API做四项一轮的费用

- 用户问四个benchmark全部DeepSeek API跑一遍多少钱。本轮只查官方价格/协议和计算，不发起付费API或benchmark执行。按单外部受测模型SWE51/HLE2500/ASI240/TB445，另列TB89一次口径，不混作本题Qwen多模型矩阵。
- 核当前CNY闲时Flash hit0.02/miss1/out4，Pro0.15/4.5/13.5，单位每百万token；工作日09–12、14–18高峰2倍。未沿用9/10旧路由公告推断所有Pro请求都按Flash价。
- 透明中情景累计输入SWE1M、TB/ASI0.5M每trial，输出50K/30K/30K；HLE输入2K输出8K；三agent输入70%cache、HLE无cache。Flash作答闲时300.96/全高峰601.92元，完全无缓存闲时570.90；TB仅89次则202.35/404.69。均为预算假设、非实测或封顶，另给低/高敏感性。
- Pro当前表不支持图像；Pro三agent+Flash全部HLE的混合中情景969.39/1938.78元。HLE Judge假设另10.5–35元闲时，ASI指定Judge和CPU/容器/任务GPU费用另计，无法凭DeepSeek API消除环境瓶颈；DeepSeek参考结果不能替代题面Qwen训练/合版结果。
- 保存analysis/deepseek_cost_estimate.md、计费约束和source_snapshots/deepseek_cost_assumptions_20261015.json；未更改正式方案或自动开始全量跑分。


## 2026-10-15：核对单任务CPU/时间，纠正并发推算

- 用户问每任务CPU与时间、能否缩短。本轮仅核固定公开代码和资源metadata，没有正式任务、API、容器或GPU运行。SWE HARD51全51项一致1CPU/4096MB，agent50min、verifier另50min、build30min，fresh replay保持；均为上限，非平均。
- ASI Docker os默认4CPU/8GiB、每(task,B层,attempt)默认3h。追加只读60项task_meta.yaml确认requires_gpu=false 60/60、services=0 60/60，纠正此前把部分任务必须用GPU当事实。linux_ns虽声明内存常量，执行未用，无CPU quota/cgroup/rlimit；外层资源隔离仍需落实。HLE无逐题固定CPU沙箱或统一墙钟要求。
- 固定Harbor Docker默认ResourceMode.LIMIT：32CPU为容器上限，非独占reservation/cpuset；48GB也非实际常驻内存。此前80四路+HPC五路约九路仅为各路同时用满的保守容量情景，不能称最大并发。同步修正当前方案、问题清单和基础设施文档；历史日志由本条纠正。Slurm allocation/父cgroup与共享主机约束仍有效。
- TB3h是agent wait_for上限，Terminus2完成确认即提前返回，环境/判分另计。正式固定预算和五次不砍；SWE50min/replay同理。ASI3h可在训练前统一配置并披露，但可能降分，未擅自调整。
- 建议独立dev测4/8/16并发、CPU核秒/RSS/I/O/throttling/API等待，固定所有模型资源/调度政策；预热镜像、轻CPU填空和异步评分。单DeepSeek TB445次假设16有效并发、15/30min均值约7.0/13.9h，题定三个模型1335次约20.9/41.7h，均为情景非实测。
- 新增analysis/task_resource_budget.md与两份固定源码/metadata证据，未编写实验代码、安装软件、启动后端、占GPU或更改正式配置。


## 2026-10-15：估算统一关闭DeepSeek思考的费用

- 用户问统一关闭思考后成本。本轮只核官方最新价格/思考参数并计算，没有API付费调用、正式题执行或改动已冻结/待定协议。
- 思考与非思考同价；Chat Completion可用thinking.type=disabled关闭。省费来自实际token减少，不能把关闭开关当作固定折扣；普通content仍会有计划/解释/代码。携带tools时历史reasoning可能减少后续输入，但轮数/重试也可能增加。
- 沿用一个外部Flash模型SWE51/TB445/ASI240/HLE2500，中情景累计输入398.5M、agent70%cache/HLE0，闲时输入128.559元。只将输出43.1M变为原预算25%/50%/75%，得作答闲时171.659/214.759/257.859、全高峰343.318/429.518/515.718元；是假设敏感性，非实测范围或封顶。
- 同情景完全无cache时闲时441.6/484.7/527.8、高峰883.2/969.4/1055.6元。HLE Judge此前占位闲时10.5–35元及ASI原Judge/环境另计，未擅自统一改变评分模型的thinking。
- 官方另确认非思考top_p固定1，忽略传入0.95；DeepSeek仍只是有配置差异的外部参考，不能替代题定Qwen权重结果。新增analysis/deepseek_non_thinking_cost.md并接入原成本表。


## 2026-10-15：讨论30分钟/4CPU与纯SFT范围

- 用户提议各任务30min、CPU最多4，并问72h内是否只SFT更现实。本轮将CPU理解为每个任务上限；只做文档/公开代码核验，没有写训练/评测代码、调配置、提交作业或API调用。
- 明确纯LoRA SFT符合题面，原主线本已是三专家SFT+同数据混训dev对照+AVG/TIES；本次不引入在线RL。4卡要承担训练、生成和正式全评，长工具rollout/环境奖励/权重同步会扩展运行链；小RL smoke在72h内可能，不能据此保证可交付有意义的多专家RL与全评。
- 原题TB明确“3小时超时、32 CPU、48 GB RAM”，30min/4CPU偏离题定配置；同项各模型一致不自动满足该要求。开发短预算可做，替代题面主结果需面试方认可，未代发任何消息。
- 修正此前SWE50min一概不能改的过严说法：题面要求记录并固定Agent/预算，未直接写死50min；50min来自当前固定v2官方locked protocol。30min同HARD51+官方评分器可作明确披露的自定义预算实验，不能称遵循原locked protocol。现有1CPU已满足最多4CPU，无需升4。
- ASI默认Docker4CPU/8GiB，timeout可在训练前统一冻结30min；目前只记录候选、不擅改。HLE无逐题独立4CPU沙箱，30min可作题级保护上限，仍需单独固定生成token/thinking/图文/Judge与客户端并发。
- 预算缩短不保证得分或API费按比例缩短。反事实算例：最低三模型SWE153+TB1335+ASI720共2208 agent runs，若全满30min为1104 task-hours，16路69h、32路34.5h，尚不含HLE7500/构建/验证/replay/Judge；非实际吞吐预测。
- 新增analysis/budget_30min_4cpu_review.md，当前方案/问题/资源表加入此澄清；训练与正式评测仍未启动。


## 2026-10-15：讨论先做Base四项评测的执行顺序

- 用户问现在是否应先把Base四项benchmark跑完。明确优先打通真实Base链路、协议冻结后尽早启动正式全量；无需把四项全部完成设为CPU数据处理/训练环境/报告准备的前置条件。四张H100的模型推理与SFT需分时或在实际证明资源可分后安排，不重复承诺四卡并行；GPU块切换前结束在途任务，未开始的队列可后续恢复。
- Base指固定Qwen3.6-35B-A3B原始checkpoint，不用DeepSeek分数替代。独立任务先验证文本/图文、tool往返、评分和完整日志；正式结果不用于选择训练数据、超参/提示预算或合版权重。工程错误允许记录后按最终协议补跑，不能把正式集当dev。
- 80实际只见data_exclusions配置、下载/审计脚本，以及13MB Base元数据，无完整权重或已通过服务。HPC常见用户缓存只读检查：.cache/huggingface/hub不存在、cache/huggingface为空、models顶层无准确Base，projects不存在、research顶层无对应模型；范围非穷尽，不排除其他共享缓存。未扫描他人目录/权重tensor或读取凭据。
- 四项均未具备完整正式启动条件：Qwen端点与模型权重、容器后端/真实配额、thinking/timeout/CPU/任务清单的最终冻结；ASI另有split/评分路线/原Judge问题。HLE已有processor与合成Judge接口证据，但不能写成正式推理服务ready。
- 复核准确官方模型卡，enable_thinking=False有正式API支持，preserve_thinking与tokenizer/processor仍需统一；前面的DeepSeek费用情景不等于已冻结Qwen thinking设置。
- 新增analysis/base_first_readiness.md并更新当前方案顺序与问题清单。本轮没有下载权重、安装、运行容器/API/正式任务、分配GPU或修改正式配置；仅只读核查和文档记录。


## 2026-10-15：回应题定TB资源是否足够

- 用户标注题定3h/32CPU/48GB并问CPU不够。明确其担心成立：当前已落实CPU/后端不足以保障最低题定矩阵按期完成；能运行单任务与能按期完成1335次是两件事。未测平均负载/时长，因此不虚构“一定不能完成”的结论。
- 80可见128逻辑CPU对应4路同时满额容量，宿主共享未保留；HPC剩180CPU仅account理论上界，需扣训练/服务，CPU-only政策与容器仍未验证。不能把4+5写成已保障9路，更不能承诺16路。
- 进一步明确此前limit解释的边界：每容器配置32CPU不是实际获得32CPU的证据；不独占不等于可以任意超卖并称复现模型卡。争用会增加运行时间/超时，需测实际资源和公平调度，不以填quota字段解决不足。
- 理想36h完成TB1335次，C4/8/9/16要求平均每trial不超过6.47/12.94/14.56/25.89min，均未实测；若均值30min，C4约166.9h、C9约74.2h、C16约41.7h。Base单445次，不能混作全部模型数量。
- 实际方向为落实兼容额外CPU/容器与独立dev负载测量，或由面试方接受30min/4CPU资源受限协议；不默改题定配置、不自行租用或发消息。较轻的Base链路可独立准备，不把GPU模型缩小/SFT替代RL当作CPU问题的解决。
- 本轮仅原题/固定源码核对、算术和文档；没有任务/API/Slurm/容器运行、付费、安装或更改资源。保存analysis/tb_cpu_capacity_risk.md并补当前资源/问题清单。


## 2026-10-15：讨论消融所用验证集与最小开发预算

- 用户问消融是否需要自己构造val、是否每候选都要全量四benchmark。明确需要独立dev，但优先从公开训练来源按源任务家族留出，不重造四个大benchmark；必要时补小量原创可执行任务，正式test不用于选择。
- 建议最小两类独立开发数据：val-loss总100K processed-token上限（修复/终端/科研/学术各≤25K）用于teacher-forced assistant NLL、监控及预定中/末最多两个checkpoint；task-dev候选为10修复+10终端+10科研+40QA，兼AVG/TIES/混训与专家目标域比较。不机械再加第三套checkpoint执行集；两个dev用途区分、任务组互斥，均不回流训练。
- 先对原任务/仓库/PR/生成模板/QA家族分组再分段和抽样，同题多教师rollout、改数字或跨源副本不能跨train/dev。SWE全池95,291行只有39,540 repo-instance组，不能随机按行。来源缺失的hash/行号只给索引，不证明语义独立或许可通过。
- 轨迹留出可算loss，不自动能测执行成功率。Open-SWE要环境/commit/tests；Terminal无统一success且未验证环境映射；D3缺task_id/环境映射；OpenScience expected_answer未自动构成可靠多学科金标准。工具dev需初始环境和独立评分，不能把teacher完成声明当通过；QA需可核答案，图表分项单列。
- 开发可另设短预算（如工具5min/≤4CPU，QA2K输出），所有参比较模型固定一致；不替代正式TB题定资源/五次。当前矩阵4个全域对象Base/混训/AVG/TIES+三专家目标域共150工具trial与200QA，工具满5min计12.5agent-hours，8路理想1.56h，QA上限0.4M输出；加载/构建/判分另算，3h是待实测条件预算。
- 70题尚未构造执行或冻结。小样本仅能粗筛/回归；10题域每题10pp，不能据一两题声称正式benchmark有稳定提升。预先固定简易持平选择规则，不围绕dev扫参。正式仍是Base/唯一合版四项全量、专家目标全量，混训和落选合版只报dev范围。
- 保存analysis/dev_ablation_plan.md并更新当前计划和问题。仅查公开资料/现有数据结构证据，无正式题读取、新数据生成、任务/API/Slurm或训练执行；没有扩大专家数/训练框架或在线RL范围。
