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
