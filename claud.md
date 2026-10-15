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


## 2026-10-15：评估从零收集train与val

- 用户明确问train和val一起从零收集是否可行。本轮区分复用独立任务/环境/验证器、自采teacher轨迹，与任务/环境/评分器也全自建；前者可作为有条件的主方案候选，后者在当前窗口覆盖三专家风险高。下载完成的沉没成本不决定取舍。
- 复核SWE-smith52K任务/250+Docker环境、Endless任务环境生成/Harbor入口与D3科研任务接口等一手来源及已有固定笔记；均未下载/安装或实际恢复环境，不把任务包当现成SFT轨迹。实际采集必须由teacher动作驱动真实执行/观察，并以独立验证器检查。
- train/val按原repo/任务/模板族先切分再生成。训练需可用教师监督；task-dev只需独立任务/初态/评分器或金标准，不必全采teacher；val-loss另需少量参考输出。val教师输出不能回流训练；公开正式四benchmark及其变体不作为自采任务。
- 条件算例：目标3M专家processed token、p=.5/q=.8、每条4K/8K/16K，需750/375/188条可用，1875/938/470次attempt；C8均10min纯rollout约39.1/19.5/9.8h。全部是假设，不包括环境/验证/val/训练/全评。混训复用同一3M，不多采一套；3M非题面数据量硬下限。
- 500次attempt相同期望约200可用，平均8K仅1.6M；少量可做缩小SFT或先补科研多轮，不能承诺支持原三专家规模或提升。若采集12–16h支持3M，需约188–250K净token/h；QA和执行分别估吞吐，不机械共用每题10min。
- 22:21 CST核时，距截止约64h，保留12h后约52h常规窗口，不重置为72h。当前Docker/CPU分配/Base服务仍未ready；API可替代teacher GPU推理，不能消除真实工具CPU/环境与正式全评瓶颈。
- 保存analysis/fresh_trajectory_feasibility.md，接入当前方案和问题清单。没有启动采集/调用API/申请GPU/下载任务包/写实验代码或切换配方；只给候选与需实测的门槛。

## 2026-10-15：执行子代理真实任务解题试点

- 用户提出用任务发现与解题两个 Codex 子代理收集真实训练任务/答案。已实际派发，发现代理留下八个真实来源候选；solver 只接收剥离修复线索的 Rich cwd import 症状与固定 base，不查 gold/修复历史。发现侧接触过 issue 内修复线索，不能声称全流程盲测。
- 80 的 artifacts/agent_teacher/pilot_rich_4201 留下 manifest、15 步命令/可见说明/完整 stdout/stderr/退出码/hash、patch、测试和 fresh-base 重放。修复前五项检查3过2败，修复后5过；初次重放 Git 发现外层仓库而未应用 patch，失败与提前报告错误已保留并纠正，建立独立 .git 后5过。
- 协调者再从固定 base 只导出已审阅的两个 import 文件、应用保存 patch，另行定义七项 import 边界检查；修复前3/7、后7/7。未跑完整上游测试或正式 benchmark，不据此推断整体提升。
- 无 DeepSeek 教师调用、安装依赖、GPU/Slurm或上游消息。当前只有可观察操作日志，缺精确教师 build/token/logprob/完整原始 transport；不导出隐藏推理，不补造中间过程，不冒称原生 mini/Terminus2，扩量需先核协议与净产量。分析文件已汇总，未启动批量采集或训练。


## 2026-10-15：按用户要求优先下载现成任务包

- 用户要求先看有没有已选好的任务并直接下载。已取得固定 revision 的 SWE-smith Python/Go、NVIDIA Nemotron mixed 六类和 D3-Gym 任务元数据，共23个文件、257,332,473B，下载回执0失败；沿用已有下载函数与现有代理，仅进程内设置网络参数，没有写新实验代码、改全局配置或使用新凭据。
- SWE Python 50,908、Go 8,212 是任务记录数，尚未跨源/任务族去重；D3 565条只有任务元数据，完整环境/输入依赖仍需镜像。Nemotron以六个压缩包为首批，不拉全部 easy/medium 或完整镜像；六包按 instruction/task.toml/test.sh 一致计5,984个入口（非名义6,000）；结构计数及完整性摘要保存 analysis/ready_task_catalog.md 和 analysis/source_snapshots/task_package_download_20261015.json。
- Endless 作为备选固定2,492任务的目录清单；实际仅35完整非solution文件84,357B，Git批量下载失败后停止，状态partial_stopped，未读/拉solution，不算任务集就绪。相较2万小文件，六包Nemotron已更适合先试。
- 仅读Parquet footer/schema及tar成员名称/大小，未运行包内代码/测试、未解压或拉容器。下载完成不等于环境ready，也不证明可直接训练、许可或正式集污染筛查通过。
- 下一步先按仓库/原任务/模板族联合切分任务与既有轨迹，再选少量恢复环境。Nemotron任务可能与已下载Corpus轨迹同族，dev所对应旧教师rollout必须一并隔离；SWE patch/test清单与D3 eval只进评分侧。学术QA仍需已有OpenScience/OpenR1单独筛选，不能用GitHub修复题替代HLE类学术覆盖。

## 2026-10-15：将协议与Base诊断置于针对性训练之前

- 用户提出先定评测协议、跑baseline再针对性训练。确认该顺序更合理，当前优先级从扩充任务转向协议与真实Base链路；现成下载数据留作候选，不以已有数据倒推评测方法。
- 更新base_first_readiness：协议草案先用独立任务核验，每项正式Base开始前冻结；Base在独立task-dev诊断工具格式/完成率/超时/学科图文短板，再在SFT前锁定训练配方。公开aggregate baseline可了解难度，正式运维遥测可排期排错，不作一概禁止读取结果的要求。
- 正式逐题答案/失败派生示范不回流train，checkpoint/合版主要由独立dev选；若据正式分项成绩迭代训练则需披露适应性选择，不能声称完全独立盲测。正式Base和最终合版仍全量，各专家仍完成目标全量。
- 不将四项全量Base全部返回设为训练硬前置：按项ready即启动，与CPU清洗/容器准备并行，四卡推理与SFT按真实容量分时。尚未落实端点/容器/配额，TB题定资源、ASI评分路线/Judge、SWE预算及thinking/预算/失败规则仍需锁齐。
- 本轮仅核现有本地证据、协调独立评审并更新计划/问题记录；未写实验代码、修改正式运行配置、下载权重、调用API、申请Slurm或启动baseline/训练。

## 2026-10-15：项目概况与当前主线复核

- 用户要求了解项目大致情况。本轮阅读本地需求、方案、最新记录、readiness、任务清单与现有脚本，按最新记录理解为限时多专家LoRA SFT与参数合版实验：同一Qwen3.6-35B-A3B基座，仓库修复（SWE）、交互执行（TB+ASI）、学术推理（HLE）三专家，同数据混训作dev对照，AVG/TIES候选经独立dev选择后导出单模型。
- 当前优先级维持协议与准确Base通路优先、独立dev诊断指导训练；Base/合版四项全量及专家目标项全量仍是交付范围。主要缺口为真实模型服务、容器与CPU并发、ASI评分链，以及数据分组隔离和长轨迹适配；不把下载完成视为训练或评测已完成。
- 按仓库既有证据，80已保存候选数据与任务包，本地主要是研究记录和下载/元数据审计脚本，正式训练、合版与全量评测尚未启动。部分文档保留过时的暂停状态、专家划分和时间预算，读取时以最新日期内的后续确认及专项记录为准。
- 本轮未SSH复核远端、联网、读取原始任务答案、运行现有脚本或启动实验；远端产物状态来自已有记录。本地既有未提交logs/与check_deepseek_judge.py保留原状。

## 2026-10-15：执行Base下载与四项环境安装（进行中）

- 用户授权下载Base并配置四项benchmark环境；后续明确80无sudo权限，并提示核查HPC容器能力。沿用80未提交的更新版评测协议，保留其既有文档与配置修改；本轮不启动正式评测、正式训练或付费模型请求。
- 固定Base revision仍为995ad96eacd98c81ed38be0c5b274b04031597b0，新增model_sources.json锁40文件/71,926,865,825B及LFS SHA-256/小文件Git blob。下载脚本支持断点与完整性检查，完成后检查26片safetensors header和index。HPC代理下载真实遇HTTP/2断流和低吞吐，后改80直连CDN的aria2分段下载，已完成文件通过仅HPC登录节点10.120.48.33可读的临时rsync服务直接同步HPC。下载与同步均仍在进行，未称完整权重已就绪。
- HLE固定源码、独立Python3.12环境及44包锁已安装；完整2500题（342图像）的文件哈希/ID复核和自造图文/schema检查通过，未读取真实题面答案或作答。SWE/TB固定Harbor0.24.0、mini2.4.6、51/89任务与140镜像digest已准备；80/HPC Harbor包版本一致。ASI固定源码、full依赖、OpenCode1.17.15及自造工具回路通过，任务输入和独立任务依赖正在下载/安装，未跑正式任务。
- 默认HPC Singularity4.1.5的fakeroot实测因缺用户subuid失败；集群Apptainer1.4.5原生root-mapped模式已在自造小SIF上通过。遵守管理员对共享盘sandbox的限制，将自造rootfs放本地/tmp构建SIF，不绕过集群wrapper；完整Harbor bootstrap仍需验收，SWE phase断网与ASI隔离不能据此视为已解决。
- ACD CPU-only sbatch test被集群拒绝；为容器检查曾提交本项目1GPU/2CPU/4GB/5min作业723418，后因已有更轻量Apptainer方案仅取消此自建作业（当时刚启动于ACD1-14），未执行GPU计算，未影响原作业722434。无80 GPU使用。
- 80的rootless Docker缺uidmap且无免密sudo，用户已说明无管理员权限，未继续系统安装。HPC已查登录节点和ACD1-13无Docker/socket；当前实际采用集群提供的Apptainer能力继续配置，不把Docker与Singularity混称。

### 环境安装后续验收

- ASI的657个agent-facing输入文件与45/45组任务依赖已到齐，覆盖60项目/240条件；独立科学库、ngspice和CPU Torch自造算例通过，未下载reference或执行正式题。HPC独立Base runtime 184包已锁，图文CPU检查通过；18GB运行SIF重算SHA-256与既有回执一致。
- Harbor自造start/两次exec/stop闭环通过；官方停止流程遇到集群launcher的子服务残留，项目19行子类先调用官方/shutdown后再stop，端口关闭验收通过。Harbor原生module:Class入口和JSON import_path均已离线验证，不修改固定上游源码。
- 80已在项目目录解包官方非suid Apptainer1.4.5并校验发布SHA，无sudo。140个固定amd64 digest镜像正在缓存为SIF，TB优先，实际并发4；独立只读43874服务仅向HPC登录IP同步SIF。镜像回执持续更新，尚未把预拉进行中写成全量runtime通过。
- 新增4GPU/16CPU/192GB/30min的Base自造GPU检查脚本及项目私有模型服务key，key未输出或提交；仅prepare-only与语法/模块初始化验证已执行，尚未提交GPU检查。权重完整且HPC最终校验通过后再运行。
- 依赖、版本、脚本与阶段状态已提交并推送lab bare仓库；80原有未提交协议/文档继续保留，未reset/pull覆盖。SWE phase网络、ASI文件/网络隔离、正式资源与Judge adapter仍需独立验收，不把软件安装完成等同正式可一键跑分。

## 2026-10-15：整理四项评测协议与完整ID

- 用户要求先解决评测协议。并行核固定官方SWE/TB/ASI框架、模型卡及HLE通用预测/评分源码；保存四份protocol_*审计、主evaluation_protocol.md与configs/eval/protocol_v1.json。规范是可审阅设计，不是已验收原生runner配置，不写训练/评测实现或启动正式题。
- 完整ID已锁存SWE HARD51、TB89、ASI60×4。HLE固定test Parquet274,276,147B已在80下载并匹配上游SHA；仅读id/image两列并计算非空图像标志，实得2500唯一ID、342图像、2158文本，未读question/answer/rationale。HF密钥未输出或迁移；下载先慢速Mac再80直连签名CDN，Mac自有未完成部分在80完整校验后清理。
- 选定SWE官方locked50min/1CPU/4GB/断网+fresh replay，Harbor固定实际0.24.0 commit、mini2.4.6候选；TB题定3h/32CPU/48GiB、temp1/.95/topk20/每call81920/context262144/五独立seed0–4；ASIopen seed31415完整240、OpenCode1.17.15固定commit、30min/4CPU8GiB为本实验预算。保留原生重试与max_tokens单次/累计区别，参数透传/压缩边界/容器网络须独立smoke。
- 已问thinking偏好，建议enable_thinking=false/preserve=false，尚未收到明确回答，不冒称确认。其他项目候选单次输出SWE/HLE32768、ASI8192；完整trial不自动选最好重跑，基础设施最多额外2次、首个有效保留，invalid不能剔除后冒称全量。统计含配对任务簇bootstrap与TB五轮SD，最低矩阵9708运行。

## 2026-10-15：回应80K资源与Qwen图像能力

- 用户问80K是否能负担，若Qwen不适配图片可剔除。明确80K是TB单次输出cap，不保证实际满发，也不等于累计预算；4H100能否按预期并发与时限完成须低并发长请求验收，暂无GPU吞吐保证。静态权重71.9GB、full-attention KV理论部分约20KiB/token仅作数量级，未计TP复制/linear状态/视觉/激活/workspace。
- 固定模型卡/config明确原生vision encoder与image token，已有CPU自造processor通过，不是纯文本模型；因此保留342图像题，完整图文GPU/HTTP仍未验。若未来改text-only须在正式Base/训练前另锁2158固定scope、同模型一致且明确标签，不能后删失败题混报。

## 2026-10-15：发现80 HKUST接口并核算评分API

- 用户明确授权查看80的.env，指出HKUST可调用gpt5.6luna。项目根没有.env；只在本人projects/home有限深度找文件，定位/data/caoqinlu/projects/data-perception/.env。只输出变量名及脱敏URL/模型元数据；未复制/修改.env、未输出key、未读其他项目业务数据。
- GET /models鉴权200，12模型，列gpt-5.6-luna/terra但无gpt-5.5。核学校当前定价输入1.4662元/M、输出8.7996元/M，API默认付费且网页免费额不适用，未查询账单余额。OpenAI官方确认Luna图像输入与reasoning none，但不把低成本型号当原GPT5.5等价。
- 仅4个自造generation请求（无正式题/参考图）：文本2+3过；64px红蓝图误答blue/blue；两张512px红蓝/蓝红图均过。HTTP4/4，returned_model=luna，reasoning_tokens0；prompt755/completion56/total811，公开价估算0.0015997586元，不是账单实扣。失败完整保留；这不是科学Judge校准，原配置未改。安全usage摘要入source_snapshots/protocol/hkust_luna_preflight.json，原始合成请求/响应在ignored artifacts。
- 仅静态白名单与NNLS委托AST核ASI判分槽：每模型132=56文本+76视觉，三模型396=168文本+228视觉，420图像附件含重复；无重试输出cap291888。396非全局严格上限，gate/缺工件可能减少、外层/SDK/其他custom依赖可能增加。按总输入2/5/10/20M与该输出cap估5.50/9.90/17.23/31.89元，ASI先规划50元；HLE若另改Luna7500调用，三组假设约55/110/220元，两项含余量可规划100–350元，不是硬封顶或实测。
- 保存asi_judge_call_budget.md、hkust_judge_budget.md与价格/协议资产快照。另一代理只读复核范围/次数/资源/算术/未ready状态与小图失败保留无实质异议。没有正式评测/训练、申请GPU、安装、更改系统或发送上游消息。

## 2026-10-15：说明哪些benchmark需要评分模型

- 用户问四项中哪些要评分模型。按已固定版本/当前候选协议：SWE Pro HARD51用官方测试器及fresh patch replay，TB2用官方验证脚本，二者不需额外LLM Judge；Qwen作答调用另计。HLE官方式答案抽取/等价判定需要Judge，本项目候选DeepSeek。ASI是自动数值/工件检查与部分LLM/VLM评分组合，已核13任务配置显式Judge，本项目研究HKUST Luna替代候选，未改原GPT5.5配置。
- HLE包含图像题意味着被测Qwen需看图；固定HLE原Judge仅接问题文字/标准答案/模型回答，不自动要求视觉Judge。ASI部分scorer实际比较预测图/参考图，需要视觉评分模型，不能把两者的图文需求混为一谈。
- 本轮只澄清已有固定源码证据并更新记录，无API/任务/GPU/训练执行或协议参数变更。

## 2026-10-15：纠正DeepSeek图像支持判断并实测双图

- 用户追问能否HLE/ASI都用DeepSeek，是图片API不支持还是接口有错。重新核当前官方Vision/API/model表，deepseek-flash（当前表列V4.1-Flash）支持图像，而deepseek-v4-pro不支持；此前把已有Flash官方API笼统说成纯文本、据此认为必须Luna/GPT视觉key，是未经验证的错误，已明确向用户纠正并道歉。不是已观察到ASIj图片请求报错。
- 固定ASI multimodal scorer本就把预测/参考图编码成user.content.image_url，和DeepSeek当前OpenAI-compatible格式一致。模型名仍须显式从原GPT5.5映射至deepseek-flash，endpoint override自身不改模型；评分器解析/num_judges/cap/重试和rubric仍要验收冻结。
- 只用已有本机私有DeepSeek官方key实做一次generation，1请求两张自造512px PNG，thinking disabled/temp0/max1024/JSON/no retry；正确识别红蓝与蓝红并判different，HTTP200/stop，1.274s，prompt466/output35/total501。原始合成证据已在Mac和80ignored artifacts留存，安全summary和fingerprint入source_snapshots/protocol；无正式题/参考图、无密钥复制或输出。
- 更新协议草案推荐HLE和ASI统一现有deepseek-flash替代Judge，Luna备用；原始task_eval未改。新增凭据不再作为统一替代路线的技术阻断；保留原GPT5.5不同、需披露及独立科学图文校准的边界，不把简单颜色探针当评分质量验证。SWE/TB仍自动测试，不需LLM判分。
- 同步更正当前问题表、Judge说明、ASI审计与预算页状态；历史claud保留当时错误并以本条纠正。未做正式评测/训练、安装、GPU/Slurm或发外部消息。其他线程新建脚本保持原状。

## 2026-10-15：介绍已下载任务实例与下一步顺序

- 用户要求介绍找到的任务及后续动作。仅读80已下载的四条独立训练题面：SWE-smith webargs请求解析回归、Nemotron游戏日志清洗和N体仿真、D3-Gym分子键级计算；未读取其patch/测试内容/eval_script/gold，未执行任务或模型API。新建analysis/training_task_examples.md记录来源、输入输出、适合专家及尚未验证项。
- 候选池统计维持SWE Python/Go共59,120条记录（未去重验收）、Nemotron mixed 5,984任务、D3 565条metadata。前两者主要为合成任务，D3来自科研仓库衍生；不统称真实维护者issue。现有学术QA仍须筛来源/答案/学科覆盖。四例未被选入最终train/dev。
- 下一步维持协议/Base优先：跨新任务与旧轨迹联合分组排除、留独立dev；每类工具任务先2–3个恢复环境/核评分器；验收真实Base端点、容器及Judge链并逐项冻结协议，先看独立dev再针对性采示范与SFT。候选dev10修复+10终端+10科研+40QA仍是待运行耗时确认的小规模方案，不代替正式全量。
- 实际环境安装在另一工作流进行中，不能将包已安装/CPU探针通过称为GPU模型服务或正式评测就绪；也不将四项全量Base全部返回设为CPU准备和数据整理的硬前置。本轮未新增安装、GPU/Slurm、付费API、teacher批量采集或训练；保留其他工作流所有修改。

## 2026-10-15：区分现成轨迹与需自跑的任务

- 用户问刚介绍的题目是否有可直接训练轨迹。复核固定下载/结构审计：已下载Open-SWE 95,291条多轮、Terminal 139,841条对话、D3 2,153条静态推理/程序、OpenScience 1,600,812和OpenR1 default 93,733条问答。它们仍需筛选与适配，不是最终可训样本数；无需为复用它们重跑全部teacher。
- 上轮四个具体任务尚未逐题配上teacher轨迹。SWE-smith语言任务包本身无messages，另有轨迹发布但未关联；Nemotron Synthetic Tasks与Corpus配套来源仍需跨发布对齐；D3现成output不是ASI多轮工具反馈，不能补写虚构执行过程。更新training_task_examples.md明确这些边界。
- 当前建议优先利用现成轨迹，独立任务用于dev及少量针对性补采；自采比例仍看实际可用量/协议/吞吐。自己要运行Base/dev、新teacher及必要环境/评分器验收，不要求全量重演旧teacher。未联网、读原始答案、采新轨迹、调用API、安装或启动训练；保留并发环境准备修改。

## 2026-10-15：说明训练轨迹与评测harness的兼容边界

- 用户问是否需要对齐。题面约束是同一benchmark内Base/专家/合版固定相同评测配置，未强制所有训练轨迹来自同一harness。直接作为目标交互示范时优先检查模型可见工具参数、观察、shell状态、结束动作及上下文语义相容；不要求框架名称/版本或prompt逐字相同。存在真实差异的轨迹可保留源协议作迁移辅助，收益由独立dev验证。
- Open-SWE mini与候选LockedMini、Nemotron与Terminus2均有直接结构接近证据，仍需验收目标prompt/状态/结束/截断；新subshell和持续tmux不能只改字段混称等价。ASI当前OpenCode候选下D3静态程序SFT可辅助科研能力，但不是现成多轮示范；工具反馈须真实补采。HLE按问答/图文/thinking模板处理，无终端状态对齐问题。
- 当前优先验收已有轨迹，不要求全量重跑；只对协议缺口做必要适配或少量补采。此次只读既有协议/结构记录并记录澄清，未联网、执行任务/API、改正式配置或训练；保留其他工作流修改。

## 2026-10-16：执行训练轨迹harness兼容检查

- 用户授权继续检查。并行对固定SWEPro/Harbor/mini、Terminus2与ASI/OpenCode通用源码及现成独立训练记录取证，新增harness_compatibility总报告及三份专项报告、四个KISS审计脚本、六份不含消息正文的统计/合成检查快照。没有执行轨迹命令、模型/付费API、正式任务、容器、训练或Slurm；没有读取正式题答案、参考patch或隐藏测试。部分固定OpenCode通用源码从官方来源补读，未改共享依赖/运行配置。
- SWE检查39分片624条、9语言；37,024次均单bash(command)，36,400非终止JSON观察可唯一相邻配对，19项原生无执行检查全部为true。原嵌套记录624条模板失败、规范化后624条通过；source额外要求patch.txt/echo后cat，与目标prompt不同，不能盲换。末尾无结果提交不伪造工具输出；全量去污染/结构/长度和loss-mask仍待完成。
- Terminal检查26分片全部task列和每片前10条共260记录；2,058条assistant去显式think后1,930被目标parser接受、128仍错误，非成功率。9项已安装parser自造结果与固定源码一致；parser容错会补缺省/丢坏command，不能单靠接受标记选训练样本。
- 日志0459/N体0939已各找到mixed同ID且题面SHA256完全匹配的现成记录，4/6步动作可解析，但两例均无task_complete=true或grader结果，不能称完整成功示范。5,984个包ID虽均在Corpus某处出现，跨difficulty确有同ID不同题面；dev必须跨任务/旧轨迹联合分组。更新原实例介绍与readiness，替代此前“尚未找到”的状态。
- CPU自造6序列及生成前缀断言通过：两个false模板flag仍保留最近user后的已有teacher reasoning。若采用非思考SFT需显式处理公开推理字段，保留Terminus JSON analysis/plan和HLE可见Explanation；不以渲染成功代替真实模型/Swift监督mask验收。
- ASI D3仍只有静态程序答案，缺OpenCode工具反馈；发现现有自定义模型没声明attachment/modalities，固定OpenCode默认为无图片，最小建议配置与源码行已记录，尚未改运行配置。科研真实多轮缺口留待小量独立任务补采；不因harness版本名重采整个池。保留其他工作流setup_swe_tb_status.md、smoke_base.py等所有修改。

## 2026-10-16：清洗与重采取舍及运行环境分布差异

- 用户问已下载任务/轨迹应重采还是清洗，随后担心训练与benchmark环境不兼容导致SFT下降。明确前轮只证明接口结构较近，未证明运行环境兼容或训练收益；任务特定仓库/数据/依赖本应跨训练测试不同，不能要求同一个正式测试镜像。需核工具/观察/状态、命令权限、网络、资源/时间、图文与提交契约，排查源轨迹依赖目标禁止能力。
- 重新浏览一手Open-SWE论文4.1/表5与固定Terminal-Corpus卡；论文确有跨harness代价，但旧数据/模型/框架与本项目不同，不能外推跌幅或据此要求全部重跑。更新harness_compatibility.md补来源链接及决策原则。
- 建议先小批清洗和每类2–3个独立工具任务环境smoke并行；兼容来源扩大复用，环境不可恢复/依赖额外权限或语义不相容的部分排除或真实重采，ASI多轮优先补缺。回放不等于SFT收益，后者用独立dev比较Base/SFT；不按沉没成本或单题试点决定，不预设固定自采比例。本轮只研究/文档，无任务回放、模型API、训练或配置变更。
- 观察到另一工作流正在修改ASI配置和模型smoke脚本，保留其所有修改；当前ASI候选已补attachment/modalities声明，真实图像工具链仍须端点验证，不将前轮发现写成修复已验收。

## 2026-10-16：补查轨迹介绍中的sandbox来源与恢复路径

- 用户要求重点查sandbox及轨迹介绍。并行补读固定数据卡、论文、上游任务schema与通用Docker/采集/启动源码，新建trajectory_sandbox总报告及SWE/Terminal/ASI三份专项；读取既有51+89任务environment/Dockerfile的FROM/WORKDIR/USER和资源元数据，保存target_sandbox_metadata及Terminal纯环境聚合快照。没有运行容器/任务/模型API、读正式题答案/参考程序/hidden tests、拉镜像层或安装依赖。
- Open-SWE的hf_dataset_name+instance_id提供关联键；Scale-SWE有image_url/workdir/parent_commit/pre_commands，RebenchV2有image_name/base_commit/install_config及构建模板。固定mini发布没有完整collector配置，不能用旧论文其他agent或当前AweAgent默认网络/4CPU8Gi预算冒充。六例上游联表因远程投影延迟已停，未下整池；原镜像/<repo>与源提示/testbed等差异尚待恢复验证。
- Terminal六包5,984份task.toml同型：1CPU/2G、agent/verifier900s、build600s；顶层Ubuntu24.04/Python3.12、/app、COPY files，引用内网registry latest且依赖无锁。默认值不能当原teacher实际参数，也不替代题定TB32CPU/48GiB/3h。当前NeMo共享镜像/SIF参考路线需逐题恢复files，不能据其初始化风险指控原教师数据。
- D3论文Appendix E提供明确新依据：每模型每题采16条推理+完整程序、在对应环境执行silver evaluator后保留，32B为2,153条。区别任务构建Conda、teacher筛选、发布Docker三个阶段；可复用已有验证依据的静态程序，不要求全量重采。D3镜像含gold/eval，OpenCode自采需隔离及CLI/路径适配，现成程序没有多轮工具反馈。
- 离线SFT不执行sandbox；Docker→SIF本身不要求重采，仍需核UID/网络/挂载/资源语义。目标TB89底层也非统一Ubuntu；本轮metadata仅包默认，另列协议草案覆盖，未改正式预算。固定Harbor源码checkout干净，Apptainer当前部署另工作流仍在验收，保留其全部WIP。
- 更新harness/readiness交叉链接。当前倾向先复用可追溯SWE/Terminal小池，任务包用于恢复独立dev和明确缺口补采；最终收益仍用独立dev比较。新增审计脚本只读环境声明、不执行Dockerfile或任务内容。

## 2026-10-16：Base完整校验与无sudo环境适配

- 固定Base revision的40文件/71,926,865,825B已在80和HPC完整落盘，分别验证LFS SHA-256、小文件Git blob SHA-1，以及26个safetensors分片/1,045张量与固定index一致，failures为空。HPC最终回执00:25:55；关闭本次43873只读传输服务并清理6.66GB重复断点，保留失败日志。
- 用户说明没有sudo；不再要求系统安装。80使用项目内Apptainer1.4.5，HPC使用集群模块。140个固定digest的SWE/TB镜像继续缓存与同步；CPU/RAM实测有余量后，预取已安全提升至8worker，保留旧日志与已完成layer/SIF。大型镜像进入压缩后，后续builder的mksquashfs从2调至4CPU/1GiB，不重启在途拉取。
- ASI OpenCode模型配置原来默认无图片输入，已补attachment/modalities；断网真实OpenCode解析与官方adapter合并检查通过，无模型调用。SWE/TB真实镜像发现Python路径、apt降权/ownership、系统Python替换server解释器的问题，已用项目只读hook与官方用户态fakeroot适配；80以官方IGNORE_SUBUID选root-map模式，不改系统helper。两端真实TB镜像约52秒完成Harbor/两次exec/tmux/asciinema/停止合成闭环；另一次上游60秒冷启动超时有收尾缺口，已清理并保留失败证据。全量SIF、SWE phase网络、ASI隔离与正式资源仍待完成，不能把首例成功冒称全部ready。
- 修复GPU检查的Slurm CUDA序号/NVML物理序号混用，改用Torch设备UUID；候选TP2/4参数CPU解析通过。四卡723633在PENDING时取消、未占GPU；两卡723673被站点wrapper误判目录参数为sandbox，改--project=后同SIF CPU预检查通过；723693识别两H100/驱动610.43.02，但Triton缓存无权限，权重未加载。已将编译/模型缓存显式落项目内，保留失败日志，重提acd_ue两卡/16CPU/128GiB/30min合成作业723706等待结果。未改HOME、系统或管理员wrapper，未运行正式题或训练，详见analysis/environment_setup_status.md。

## 2026-10-16：明确重申训练—评测一致性优先

- 用户澄清核心疑问：训练轨迹sandbox应与最终四项benchmark的环境足够相近，评测harness也最好与对应轨迹一致，减少SFT学到不适用的操作习惯。承认此前过度强调可迁移/可复用，没有将此要求放在首位；不将其说成仅需格式转换或离线SFT能读入。
- 将环境/harness一致性写为主训练数据资格前提：核工具/观察/提示/状态/结束、依赖与初始化、权限/网络/资源；在题面允许范围内优先按轨迹选择同源评测agent。TB遵循题定Terminus2，其他agent在正式Base前可重审原候选，不为保留OpenCode实现强行使用不匹配轨迹。
- 同项Base/专家/合版在冻结后统一harness；四项分别对齐，不要求四项共用一个。未验兼容样本不升主数据，D3静态程序暂仅辅助候选，ASI主交互数据需匹配组合或真实补采。更新trajectory_sandbox及harness_compatibility首要结论，不改变正式任务/镜像/评分或启动训练。
- 本轮仅记录用户约束与修正方案优先级，保留另一工作流所有环境/模型smoke修改；无额外联网、任务/API/GPU调用、安装或配置变更。

## 2026-10-16：按构建方式与公开harness代码确认复用路线

- 用户进一步明确检查方法：环境主要比较轨迹sandbox如何构建及与benchmark是否相似；harness主要查有无公开代码能直接复用。分别取证，不再把NVIDIA完整批量collector未公开混同为没有标准harness，也不只重复抽象一致性要求。
- SWE已核mini v2.4.6官方tag a83fcae82d2a08f0ee0c688f9d137b3566c097f8；DefaultAgent/actions_toolcall与80已装包SHA相同。现成Agent/LiteLLM/bash/环境、HarborMini、官方LockedMiniSwe/PatchReplay可直接复用，新增仅端点/版本/任务image-base-cwd-setup适配，不重写agent。
- Terminal已核固定Harbor内置Terminus2/parser/tmux/Chat/LiteLLM/registry/CLI，公开代码完整，能复用标准主干；环境构建/文件恢复和Apptainer backend与agent层分开。缺原批量采集launcher不阻断此代码复用，仍需模型端点与环境验收。
- ASI新核官方DirectLLMAdapter：官方prompt单次生成完整Python、提取代码、在原sandbox执行并收集产物交原grader，与D3静态监督更接近。它仍执行科学程序，但无模型探索/读stderr后修复，当前仅文本prompt无图片附件；还需生成参数/总deadline接线。将D3+direct_llm列为匹配候选，与OpenCode在独立dev/工程成熟度上比较后正式前冻结；纠正‘D3无条件只能辅助/必须补多轮’的过早限制，未改变现行配置或官方任务/评分。
- 环境构建比较：SWE均为仓库Docker环境+初始checkout/项目依赖，Terminal均为Harbor Dockerfile+输入文件，D3/ASI均科学Python依赖与程序产物；结构相似与具体初始化/权限/网络待验分开。HLE复用官方生成client，图文/模板与参数接线另核。
- 新建harness_reuse总表及SWE/Terminal/ASI-HLE三份短代码清单，更新sandbox/harness主结论与ASI问题项。只读固定源码/环境资料和版本，无模型/付费API、任务/容器、GPU、安装或runtime修改；保留另一工作流全部WIP。

## 2026-10-16：解释direct_llm

- direct_llm在本项目语境指ASI官方的单次程序生成adapter：任务与数据说明送给模型一次，模型输出完整Python，runner在sandbox执行并收集文件，交原官方评分器。仍可使用本地Qwen，不表示必须调用付费API。
- 与OpenCode的读文件、运行、观察报错、修改代码多轮流程区分；direct_llm仍真实执行程序，但模型不根据执行反馈修复。D3完整程序监督与此形式更接近，效果与环境兼容仍待验证，目前只是候选，未切换配置或启动任务。
- 本轮仅解释已有源码结论并记录，无训练、模型/API调用或运行环境变更，保留其他工作流修改。

## 2026-10-16：数据、工程、算法与评测的联网方法调研

- 用户要求从网上找当前任务各方面可参考的方法。实际联网核验作者论文、数据卡、官方源码与文档，新建总报告 `analysis/research_web_methods_20261016.md`，以及 data/algorithms/engineering_eval 三份同日期专项笔记；仅研究文档，未改变配置、训练范围或正式评测协议。
- 整体路线参考同Qwen3.6底座的Occamy；T-pro共享SFT接近领域SFT的反证支持保留同数据Mixed，不预设分专家SFT合版更优。AgentTuning借鉴能力保留与held-out检查，不直接加入其旧数据或RL阶段。
- 数据侧核验Open-SWE/Nemotron包含未成功轨迹的消融，但样本数/token混杂，不能推出本项目必须no-filter；优先保留完整成功轨迹内的有效恢复。新增SWE-Prime的保留上下文/选择监督思路，局部mask仅为有条件候选，不同比节省processed token。D3完整程序与ASI direct_llm更相近，但当前adapter只给文本prompt、不附模型图片；上游许可、任务映射及评分材料隔离仍需核对。
- 合版侧明确真实更新为scaling×B@A；PEFT linear/ties是因子空间，不等价dense AVG/TIES，cat可精确表达AVG。TIES逐张量/global trim、disjoint mean权重、scale和平票语义须执行前固定；SVD重压缩与秩容量差异需披露，保持当前候选模块范围，不盲套all-linear或扩训routed参数。
- 工程侧新增固定Harbor resume可能删除旧trial的证据，建议恢复前归档attempt/usage；vLLM当前文档提供Qwen3.6 MoE LoRA例子，但2D/3D布局、parser、实际安装版本仍需验收。root-map、资源限额、网络分别核查；同项模型采用同调度政策，避免排队挤占行动预算。
- 评测侧建议保留固定分母、配对任务簇区间（TB89×5、ASI60×4）、分项退化、接口/环境失败及成本；替代Judge需独立人工可核文本/科学图文校准，图像/JSON接口成功不等于官方评分等价。主报告已做数据与工程专项交叉审阅，建议与已冻结/已完成状态分开。
- 本轮未执行模型、任务、容器、训练、正式评测或付费API，未安装/下载实验依赖；保留其他工作流正在修改的脚本、状态文档和logs，仅将本轮研究笔记与本节纳入Git。

## 2026-10-16：将Agent上下文与协议纳入资源预算

- 用户要求Agent协议、最大上下文等必须由4H100资源承受。本轮只读固定模型配置、已装runtime/协议与HPC/80资源状态，联网核官方vLLM0.20.2参数，分别核显存、Harbor/mini、ASI/HLE参数落地；新增agent_resource_protocol及三份专项记录，未修改protocol_v1或启动模型/任务/训练。
- 候选：TB保持题定256K总context/80K单次输出/3h/32CPU/48GiB/五seed；其余三项统一128K总context，SWE每次8K、HLE与ASI单次完整程序16K。保留SWE官方50min、不另加100步；ASI总30min、direct_llm仍候选。预算缩减是实验自选值，需实际验收后在正式Base前统一固定与披露，不能按低分对象加预算。
- 区分总context、单次output、累计生成、server活跃序列及sandbox并发；图片/工具定义/历史也占context。mini无原生短context硬限/历史摘要，按benchmark分时设置服务128K最省代码；OpenCode原生steps只是收尾提示，不能称硬执行次数上限。Terminus86016是剩余token触发阈值，三阶段摘要继承80K仍可能超限，需真实计数/边界恢复验收或披露薄适配。
- 固定权重约66.97GiB，10层full+30层linear；TP4 KV头复制，256K full-KV约2.5GiB/序列/卡，不可直接总量除4。HPC识别H100 80GB HBM3约79.65GiB/卡，低并发有显存容量依据但无完整长上下文HTTP通过回执；linear state、cache pool、视觉与workspace另计。建议TP4单服务，先2条活跃请求再测4，85%显存/8192chunked prefill是待验候选，训练评测分时。
- 显存可行不代表按期完成：模型队列、decode速度、CPU/RAM/I/O及TB1335次长尾另验；16K生成与600s HTTP也要匹配真实速度。训练先8K、可验16K，不等同评测256K。只读现有723706在途作业，不干预任何作业、容器、共享缓存或他人WIP；不把理论估算冒称实测。

## 2026-10-16：效率优先的64K预算讨论案

- 用户要求兼顾效率、适当降低上一案参数。将agent_resource_protocol当前优先讨论案改为非TB统一64K总context：SWE单次4K/30min、ASI direct候选8K/20min（生成与执行共享）、HLE4K/5min（队列、传输重试共享）；原128K案保留为前案，尚未改实际配置或冻结。
- 优先压长输出与超时长尾，不承诺按上限同比提速：同样短请求不会因context上限减半自动更快，提前EOS也可能使max_tokens缩减几乎无收益。保留完整图像/题干、环境与harness契约、官方判分及SWE fresh replay；64K图像输入边界、length/context失败与吞吐在独立dev核验，所有参评模型同项一致。
- 更正预算边界：SWE50min来自所选locked protocol、非题面硬值，30min作为本实验设置披露；TB题定256K/80K/3h/32CPU/48GiB和五seed保持。另列TB64K/8K/30min/4CPU/8GiB独立开发消融档，不替代题定正式结果，当前无面试方同意替代。ASI adapter仍待冻结，不能把改为单次生成的效果差异归因训练。
- 本轮仅既有资料与同伴只读复核、修订讨论文档并Git记录；未启动API、模型、任务、容器或作业，未安装依赖、改正式协议或干预其他工作流WIP。

## 2026-10-16：统一32K上下文的取舍

- 用户追问“都降到32k如何”，按总context32768理解并记录为当前资源受限候选：SWE/HLE每call4096，真实prompt至多28672；ASI direct和短预算Terminal每call8192，prompt至多24576，包含模板、图片、工具与历史。时间仍沿用SWE30min、ASI20min、HLE5min、Terminal开发30min，不据此宣称已冻结执行。
- 32K与题定TB的80K单次输出算术不兼容，若Terminal也用32K必须同步改输出并标资源受限；题定256K/80K/3h/32CPU/48GiB/五seed要求未被替代，也未获面试方认可更改。
- 明确风险：mini无原生摘要，工具历史可能提前触顶；Terminus32K需重新核摘要预留和触发，旧86016阈值不可沿用；HLE图文真实长度不能假定全部容纳，保留完整题图，ASI程序可能length截断。缩短上限不加速相同短请求，不承诺吞吐翻倍或质量不降；用独立dev再决定某项是否统一保留64K，不对正式低分题临时扩窗。
- 仅更新agent_resource_protocol与本日志并Git记录，保留其他工作流修改；没有改protocol_v1、运行模型/API/任务/GPU或安装依赖。

## 2026-10-16：提高本项目HPC调度优先级

- 用户明确授权提高HPC任务优先级。核本人账号与分区ACL后，将后续Slurm默认分区从acd_u改为emergency_acd，PriorityTier/JobFactor=300（本轮此前实际用acd_ue=200）；仍用qinlucao账号/formal-user QoS，不设置管理员专用priority/负nice。脚本已同步HPC，sbatch --test-only预检查通过，不产生真实新作业。
- 当前723727已在ACD1-7运行，不为调度优先级重启或重复申请；未操作其他项目原有722434。此前723706已经完整加载26分片，但FlashInfer首次编译耗尽私有/tmp而失败；新作业已挂项目独立/tmp并限制MAX_JOBS=4，保留失败证据，等待HTTP验收。140镜像缓存到90个、0失败，继续同步，未运行正式benchmark或训练。

## 2026-10-16：联网核实四项上下文的实际运行证据

- 用户要求上网查四项benchmark实际多大够用。使用research工作流并行读作者论文、官方源码/卡、实验作者报告；ego-browser实际核网页与SVG图表，web定位/交叉查证。新增context_evidence总报告、SWE/Terminal/HLE/ASI四份专项及无题面统计JSON，更新agent_resource_protocol首要结论，未改protocol_v1。
- SWE找到旧Pro731题/Qwen3.6-27B+mini作者自报32K约9%、64K约24%、114K约28%，成功峰值context p90约67K/max约113K；后续更新和配置差异均披露，非本题V2 HARD51/35B直接消融。真正V2官方mini中位48–85步、累计输出26–28K，不混作单turn/output或瞬时context；建议SWE64K折中、128K更稳，不再一刀切32K。
- Terminal找到AfterQuery一手报告：完整89题/五次均值/Terminus2+summary，max context32K、max output4096，GPT-OSS20B Base/SFT/RL=3.1/13.5/17.0。没有公开其P+O硬限实现，也非Qwen降窗对照。Nemotron作者Table8的32768是SFT而eval40960，13.0±2.2；64K设置10.3–11.9且训练/YaRN混杂，不说越短越好。TB32K/4K低预算有实跑依据，仍不能替代题定256K/80K要求。
- HLE官方示例8192是输出，reasoning不建议低于8192，非思考无最低规定。未找到当前Qwen3.6非思考32K/4K无损对照或冻结2500题实际图文输入分布；32K待验，输出8K较稳、4K为进一步节省候选，不据模型卡thinking至少128K断言无工具非思考必须128K。
- ASI论文百万token为多轮累计，B1/B2均时37.8/49.7min，不能推最小窗口或20min足够。仅CPU读取已下载240份官方原始prompt，加DirectLLM默认system和固定Qwen模板（thinking/preserve false，tokenizer无truncation/padding），不打印/保存正文、不读data/reference/answers：中位978.5、P95约2831、max15229；预留8192时240/240可装32K，max合计23421。只证明该文本组合输入容量，不证明8K程序足够、真实附加prompt、图片输入或多轮历史。原生单次adapter仍是候选。
- 本轮未调用模型/付费API、跑程序/正式任务、安装依赖或调度GPU；只运行上述CPU tokenizer统计并保存摘要，无题面正文入Git。关闭自己的浏览器研究space，保留其他工作流镜像脚本/logs/WIP；运行准备状态以并行工作流最新回执为准。

## 2026-10-16：实测已下载训练轨迹长度

- 用户要求查看轨迹长度。本轮仅80 CPU以固定Qwen tokenizer/template计数，未执行轨迹命令/样本程序、模型/API/GPU或正式任务。SWE/Terminal无原生token列：39片SWE每片等距128=4992（1693源resolved1）；26片Terminal每片128=3328；按N/n加权而非冒称全库精确统计。另Terminal mixed5689、D3静态程序2153全量，OpenR1十片各200共2000未加权样本；OpenScience15.7GB本轮未分词。所有统计已正常结束，无后台作业。
- 完整序列计system/user/assistant/tool定义/参数/观察/模板，raw preserve=true防自动去旧推理，clean显式去assistant公开前缀/reasoning_content并preserve=false，保留Terminus JSON analysis/plan及可见解释。clean仅长度对照，未决定删除teacher推理或生成最终SFT。模板/Tokenizer IDs合成对照通过，QA原/收紧前缀清理规则逐字等价检查通过；不平衡think记录保留并单列。
- SWE clean全体中位33418/P9559429，≤8K0.20%、16K4.54%、32K47.83%、64K97.30%；来源成功子样本中位29804/P9551814，覆盖0.12%/7.09%/61.51%/98.89%。单assistant含bash参数P991640，99.9749%≤4K。长轨迹主要为累计历史而非公开thinking；64K预留4K的保守整条覆盖成功子样本约98.04%，支持SWE不一刀切32K。
- Terminal clean全域样本中位12694/P9522537，≤8K19.88%、32K99.825%；mixed全量中位9937/P9517543/max24810，全部≤32K，整条再预留4K的保守条件也全覆盖。clean单次输出99.7998%（样本）/99.8305%（mixed全量）≤4K。小model_training域仍有约48K P95，样本最大值和来源总体覆盖不能冒充正式TB需求分布；≤32K完整序列不自动保证每次还能额外reserve8K。
- D3 raw中位8441/P9515640，clean2683/P958300/max14924；clean94.4728%整条≤8K、100%≤16K，assistant max3713全部≤4K。OpenR1 raw中位5050.5/P9514236，clean637/P95969、99.8%≤8K；4条不平衡think保留形成长尾，非HLE正式题。不能把短teacher最终目标当成ASI/HLE推理生成预算无损证据。
- 新增trajectory_lengths主报告、SWE/Terminal/QA专项、3个KISS统计脚本及3份无正文聚合JSON，readiness/资源方案加入口。关键影响：8K SFT不能对SWE完整轨迹直接截尾，需另议16K短轨迹筛选或保留状态的交互窗口；尚未改训练/评测配置。行级数字仅留ignored artifacts；保留镜像/模型smoke等其他工作流修改，单独Git记录本轮产物。

## 2026-10-16：基于长度选择单次输出上限

- 用户认可长度结论后询问输出端设置。按当前非思考候选建议SWE每次8192（64Kcontext）、Terminal资源受限每次4096（32K）、ASI direct候选每次8192（32K）、HLE每次8192（32K）；它们是每次请求上限，不是整题累计token额度或每次必生成长度，EOS提前停止。
- SWE虽99.9749%样本动作≤4K，来源成功样本最大单turn5011，故为少量大bash写文件/patch动作保留8K；Terminal约99.8%clean动作≤4K，需独立dev记录少量length截断。D3清后目标max3713不能证明所有ASI完整程序都≤4K；HLE清后训练答案短也不证明正式求解4K足够，保留可见解释空间。题定Terminal正式80K不因开发预算自动更改。
- 输入预留对应SWE57344=56K、Terminal短档28672=28K、ASI/HLE24576=24K，含模板/图片/工具/历史。只在独立dev统一修订预算，同项全部模型一致；正式个别length失败不额外加token重答。推理输出上限不拿来直接截SFT标签，训练窗口另议。
- 更新agent_resource_protocol当前表及口径，旧32K/64K讨论作为历史；未改protocol_v1/实际runner、训练、模型/API或任何作业，保留其他工作流WIP，仅文档Git记录。

## 2026-10-16：高优先级Base图文与工具GPU验收通过

- 已用本人账号/formal-user QoS在emergency_acd实际提交，作业723784、723821优先级10023（此前acd_ue为6689）；未修改其他项目722434或使用管理员priority/负nice。默认高优先级配置已用于实际作业。
- 723727挂项目临时目录后仍在首次NVCC编译阶段超过600秒；随后显式采用已安装vLLM0.20.2原生Triton GDN/MoE并放宽health至1200秒。723784虽成功启动服务/鉴权，但首个文本请求因共享盘Triton缓存文件缺失返回500；保留失败日志，不将其算成功。
- 723821把所有编译缓存和/tmp改为每作业独立的节点本地XFS临时目录，在2×H100 80GB、TP2/BF16/262144/eager/maxseq4下通过4项自造HTTP：文本标记、32px红图、add_numbers(17,25)调用和同tool ID反馈后回答42。鉴权200/无key401，startup270.19秒，每卡请求后70635MiB；Slurm COMPLETED0:0/5分07秒，服务返回0。安全聚合回执入analysis/source_snapshots/base_gpu_smoke_20261016.json。不是长上下文/吞吐/四卡正式配置验收；没有运行正式题、训练或评分。
- 用户追问镜像并发，已核实当前实际8个Apptainer pull子进程并发，99/140、0失败；四个6–9GB大TB镜像持续约2.7–2.9MB/s，未卡死，不丢弃在途下载。HPC新镜像同步循环在源全完成后额外rsync并逐个核140份SHA256与alias；全量完成前不冒称全部缓存验收成功。

## 2026-10-16：镜像无损扩到16并发与ASI隔离候选

- 用户追问并发后，在保留原8个长下载的前提下新增8-worker：仅暂停任务分配器，固定排除其打开日志对应8digest及106个final，另队列处理26项，并发上限16。独立进度/日志，supervisor1651574/helper1651575结束后恢复原coordinator，最后统一汇总；未kill或重启原Apptainer。原Future已记录前次失败，必要时待原runner结束后全缓存复扫。
- 针对实测GHCR HTTP2流中断，新prefetch子进程显式Go http2client=0；固定GHCR元数据/缓存SIF复拉通过。在线入口包装不兼容Apptainer重定位，version检查即失败并原子恢复同一ELF，安装脚本也回退，未留二进制包装、不丢缓存。新增subset/独立progress参数保证补充队列互斥。
- ASI新增可选bwrap OpenCode adapter和固定模型Unix relay，真实key留controller；四namespace、文件/进程/网络边界、SSE/tool反馈、窄路径/模型/附件限制及8.072秒timeout清理通过。原生TaskEnvironmentManager的3组缓存科学自造算例与ngspice0.5V通过，安全聚合回执入source_snapshots。无正式题/评分/付费API/GPU，未改protocol或选择OpenCode/direct_llm。CPU/RAM和真实Qwen链路仍待验收，不冒称正式就绪。
- Base完成后曾关闭本轮自建HPC反向代理38082（Mac69616）并核端口关闭；为补丁后的Harbor合成回归，临时在本轮SSH master重新开启，回归结束再关闭。用户80原代理38080保持，镜像只读同步43874仍有用途。

## 2026-10-16：Harbor启动收尾修复与DirectLLM隔离对齐

- 固定Harbor f527加显式local patch：300秒启动deadline、实例身份关闭、staging日志、有界等待/取消；项目旧stop override同步移除。两端依赖101包锁未变，幂等apply/reverse和CLI通过；实际同一SIF合成生命周期80约44秒/HPC约46秒，2exec/tmux/录屏/端口关闭通过。8项故障合成通过；监听前detach仍保留清理边界，全140 bootstrap与网络/资源能力不冒称通过。补丁及精确SHA和复现说明纳入Git。
- 对齐另一工作流已锁v2 direct_llm，新增42行候选仅替换_execute，生成/提取/collector原生，程序空间无OpenCode/relay/key。3组taskenv科学计算与ngspice、8.014秒超时4/4通过；每例生成执行各1次。共享builder后的OpenCode候选也重新通过8.066秒边界/超时。64K8K参数/共享1200秒、CPU/RAM和真实端点仍未实现或验收；无正式题或真实API。
- 下载后台已接自动收尾：等原队列恢复结束后全缓存复扫，再等HPC140项SHA/manifest完整回执，才关闭本次只读SIF rsync。HPC mirror空闲时更新为3040078，finished/failed不提前退出；Mac收尾worker状态在ignored download-pipeline.json。只读SSH/JSON有限重试，mutation不盲重试，原77回执不能触发关闭。
- Harbor回归结束后已再次关闭本轮reverse38082并核端口关闭，用户38080不动。另按新v2参数安排一次2H100的64K/8K纯自造GPU检查，不把旧262K短请求当作当前参数/长上下文通过。

## 2026-10-16：统一64K/8K并定稿Agent协议

- 用户在统一8K输出后提出所有benchmark统一64K上下文；已冻结v2实验设计，输入最多57344 token，所有policy主调用与摘要辅助调用均为65536总context／8192输出，关闭thinking与preserve_thinking。保留真实图像token计数及原生多轮格式反馈，不加预算重答或静默裁题。
- 新增configs/eval/protocol_v2_unified64k8k.json；更新analysis/evaluation_protocol.md；旧文档归档analysis/evaluation_protocol_v1.md，v1 JSON不变。analysis/agent_resource_protocol.md明确指向v2，旧表仅为讨论历史。
- SWE固定mini2.4.6、官方bash/prompt/观察/结束、30min与fresh replay；TB固定Terminus2原生JSON/tmux和提前摘要、30min/4CPU/8GiB；ASI选官方direct_llm单程序单执行、生成执行共20min；HLE完整2500含342图像、单答无工具、每题5min。传输至多两次且只允许明确未生成的失败，原生解析反馈与同请求重试分开。
- TB明确标resource_constrained_experiment，保留题定256K/80K/3h/32CPU/48GB参考配置，不冒称符合题定要求或已有面试方例外许可。HLE/ASI替代DeepSeek Judge单独披露，Judge不适用policy统一8K。
- 起始部署设计为一个TP2服务、4活跃模型序列、8准入solver，训练评测分时，总卡数不超过4。已有TP2短文本/图片/工具smoke通过，不等于64K长输入/并发/隔离验收；实际适配仍待执行。本文定稿没有运行正式题、训练、评分API或提交GPU作业。

## 2026-10-16：区分启动前必须锁定的设计与执行验收

- 用户问还有什么需要一开始确定。复核v2、dev_ablation_plan、readiness_training/readiness_data及数据建议；不把既有harness/context/output/split/Judge选择重复列为未决，也不将未验收误写成未决策。
- 正式Base前：明确资源受限TB与题定结果的提交口径；落实并验收v2真实参数/共享deadline/重试/配额。正式评分前完成Judge独立校准并冻结版本；校准不必阻塞Base生成与产物固化。若需修改已锁协议，正式比较对象使用同一修订版重跑，不逐题扩预算。
- 训练前仍需冻结最终来源资格与任务族train/val-loss/task-dev互斥manifest、去污染及去重边界；现有70题task-dev/100K token val-loss只是建议，非已构建独立集。推理关闭thinking不自动决定teacher think清洗，训练长轨迹/状态/新增assistant监督mask及训练窗口需另定。
- 训练/选择前冻结同结构LoRA与同数据混训公平预算、候选checkpoint/AVG/TIES数量及dev主指标和近似持平规则。具体LR/batch/序列长度与有效并发依小规模吞吐验收再选，不需在无实测时拍数，也不必全部阻塞Base。
- 建议沿用不加RL/偏好优化与大规模补采的SFT主线；优先必需参评对象与报告，保留10月18日14:20截止前12小时整理窗口（核心实验止于10月18日02:20，北京时间）。本轮为待讨论缺口梳理，未将这些建议擅自标成用户已确认，未启动任务、训练或API。

## 2026-10-16：专家模型、参数合版与MoE的关系

- 用户要求调研三者是否有重要关系。本轮真实联网核验论文与官方实现，保存 `analysis/expert_merge_moe_relationship_20261016.md`，经文献与架构两路交叉核对；只补研究文档，未改变已冻结v2协议、训练候选范围或执行配置。
- 区分领域专家（同底座的仓库修复/交互执行/学术推理分支）、静态参数合版（离线合并真实更新）、MoE（运行时内部模块路由）。三者有交集但互不构成必要条件；dense ΔW表示还原LoRA更新矩阵，不表示最终架构变dense。
- 五个代表方法：BTM的Merge并非仅权重平均，亦有专家集合/输出集成；BTX明确将领域整模FFN保留成MoE、其余参数平均后继续训练；Sparse Upcycling从同一MLP复制内部专家；X-LoRA/MixLoRA展示低秩模块动态混合。mergekit有免训练gate初始化，不能绝对声称构造MoE必须继续训练，也不能据此认定当前Qwen分支可直接拼接。
- 固定Qwen3.6配置为各MoE层256个routed专家、每token选8，另有shared。三个外部领域分支不会自动成为三个内部FFN；同结构AVG/TIES后仍约35B总参数，不变成105B。当前候选attention/shared-MLP LoRA可改变hidden state，所以冻结router权重不保证路由不变，此为源码函数推断。
- 新查HARC研究同底座MoE分支合版的routing breakdown；其OLMoE全参微调和另Qwen3-30B设置不能直接外推当前冻结router的Qwen3.6 LoRA。路由重叠/概率可作解释性诊断，但变化不等于错误，不新增校准阶段或把复制Base路线设成优化目标。
- 建议保持三专家SFT、同数据Mixed及AVG/TIES主线，将底座架构、领域分支训练、组合方式分别报告。动态adapter路由或重组MoE为后续独立结构实验，不替代本题静态参数合版。本轮无模型、任务、训练、评分API、容器或GPU执行，保留其他工作流WIP。

## 2026-10-16：先按benchmark类型选独立val并清除教师思考

- 用户明确先按四benchmark任务类型分布挑val，问train依据val还是正式Base选择；决定清除训练thinking与reasoning_content，LoRA rank等暂缓。本轮记录这些已确认决定，不擅定rank/alpha/训练窗口或配额，不开始清洗训练流水线。
- 路线为公开benchmark元数据→独立val→Base在独立val上的聚合短板→train配比。train与val共享分类而非题目/模板族，跨任务包和旧轨迹先联合分组、留出全部val同源记录；正式四项Base逐题成败/答案/测试反馈不参与选训练样本或配比。正式Base可并行生成；val不是无偏test，限定选择次数。
- 同伴在80仅读固定来源分类元数据：HLE id/category/raw_subject/answer_type并join已有image IDs，无question/answer/rationale/图正文；TB89份task.toml分类/难度；SWE51 ID到repo及分类字段；ASI按task ID前缀。HLE8类/数学1021(40.84%)/图像342(13.68%)，TB16类/软件工程26/89，ASI11域，SWE11repo且category/difficulty统一、无language字段，不能冒称真实bug难度分布。
- 新增analysis/validation_selection.md与metadata-only validation_target_distribution_20261016.json，保存分类/模态计数与来源；旧70题val方案中的TB10/ASI10不足覆盖全类，数量暂不冻结，需按主要类别/长尾与吞吐预算重算。没有从正式题中抽val，也没有宣称已有最终val题目或验证器验收。
- 清洗精确定义为删除assistant reasoning_content与明确教师think前缀，保留Terminus analysis/plan等必需协议、真实工具动作/反馈和可见答案。未闭合think/结构损坏隔离，空正文但有效tool_calls保留；清后重渲染、重算仅新增assistant监督mask，无目标排除，不递归删代码或工具数据中的同名字段。历史长度统计不重跑，清洗决定不等于已导出数据。
- 更新dev_ablation_plan、readiness_training与trajectory_lengths的当前决策状态；未调用模型/评分API、运行任务、申请GPU或训练，保留其他工作流WIP，仅本轮文档/聚合快照入Git。

## 2026-10-16：澄清显式think是否计入轨迹token

- 用户要求先暂停选集并确认此前token口径。已核对trajectory_lengths：raw包含公开teacher think和reasoning_content，clean去除可识别显式think前缀及reasoning_content并用非思考模板；此前资源建议主要引用clean，未把raw冒充已清理长度。clean历史统计的未闭合think少数长尾仍保留，不等于最终清洗合格。
- 整条中位raw→clean：SWE33418→33418、Terminal17246→12694、D3 8441→2683；工具观察/调用、Terminus analysis/plan、可见答案及模板开销始终计入。SWE长主要是交互历史，不能以再删think推断其可装8K。未继续选题、清洗、模型/API或训练。

## 2026-10-16：核查think与reasoning_content的区别

- 用户要求看两者区别。只读固定Qwen模板、实际数据审计文档与长度脚本，确认think是正文/序列标记，reasoning_content是独立消息字段，可承载同一段推理。SWE4992样本97非空字段且无正文think；Terminal仅role/content，D3/OpenR1配对推理为正文前缀。
- 固定模板优先字符串reasoning_content，否则解析正文闭合think；字段也渲染为think块，两处同时存在不去重。CPU自造消息实渲染：单形式各1次、双形式2次；非思考双false仍保留最近user后的assistant推理，更早轮次省略，生成前缀为空think块。故清除两种源推理内容必须显式执行，不能只关开关；模板空标记不是残留教师推理。
- 补validation_selection的模板边界，未继续val选题或导出训练数据，未访问原始题/轨迹正文、调用tokenizer/模型/API、申请GPU或训练。仅本轮文档入Git，保留其他工作流WIP。

## 2026-10-16：深入核实Qwen原生thinking、服务解析和SFT语义

- 用户记得Qwen thinking就是think tags，要求深入调查。暂停val选题/清洗，采用research与ego-browser，一手固定模型卡/词表/模板、vLLM0.20.2/LiteLLM实际安装源码、固定候选Swift源码及已有数据安全元数据并行核验；无模型推理、训练、付费API或GPU申请。
- 修正此前解释的不足：Qwen3.6原生thinking由think标记界定，独立reasoning/reasoning_content通常是同段内容的服务/客户端表示，不是两套原生思考。固定模型卡支持enable_thinking=false非思考路径，不官方支持旧Qwen3 /think软切换；不能将清理历史与控制新生成混为一谈。
- 精确服务链为模型think序列→vLLM0.20.2 reasoning/content→LiteLLM1.105.1或1.93.0 reasoning_content；mini/Harbor有保存路径。vLLM入站有reasoning→模板两字段桥，但仅旧字段回传的完整wire仍待验。8K输出包含全部生成token，隐藏返回字段不节约生成预算。
- 80固定AutoTokenizer CPU自造验证：inline与field渲染逐字等价，各35tokens；故意双写44tokens；删正文27tokens仍有模板空块。think IDs248068/248069，added-token special=false，decode skip_special_tokens=True仍保留标签；回执为source_snapshots/qwen_thinking_template_probe_20261016.json。未加载权重/读真实题面。
- 新核安全元数据：SWE95291行全为Qwen3.6-27B、thinking=false；Terminal139841行全DeepSeek-V3.2、thinking=true。SWE同4992样本97条含103个truthy reasoning字段，16仅空白、87去空白后非空（84条记录），其与非思考元数据并列、原wire归因未知；不凭有/无字段判定生成模式。D3导出器还可能补包装标签，保存格式不必等于原wire。
- 候选Swift标准messages加载会过滤额外reasoning字段，不能把HF模板支持外推到训练loader；CLI hybrid通常ignore_empty_think，仅mask空块、不忽略非空全文。删除teacher思考与保留但mask不等价，后者答案仍以teacher思考为条件并耗上下文。最终训练input_ids/labels/loss_scale仍待合成验收，不擅定rank或修改部署协议。
- 新增qwen_thinking_investigation总报告、vllm/data/training三专项与CPU聚合回执；validation_selection加暂停和最新证据入口。仅本轮文档/回执纳入Git，其他工作流环境与脚本WIP保留。浏览器只关闭本调研自己的task space。

## 2026-10-16：核对两个轨迹教师是否强于题定Base

- 用户问Qwen3.6-27B与DeepSeek-V3.2是否有Qwen3.6-35B-A3B强。本轮research/ego-browser核官方Qwen27B固定卡6a9e13bd6fc8f0983b9b99948120bc37f49c13e9及DeepSeek原论文，不拿Qwen3.5-27B或V3.2-Speciale冒充。
- Qwen3.6-27B公开存在，官方同表35BA3B→27B：SWEVerified73.4→77.2、Pro49.5→53.5、Multilingual67.2→71.3、TB2 51.5→59.3、HLE21.4→24.0。27B是dense，Base35B总/3B激活MoE，参数数字不能直接比。公开相关能力有27B更强证据；源teacher非思考且精确revision/wire未知，没有本实验非思考64K8K师生直接对照。
- 标准DeepSeekV3.2作者TB2 thinking/ClaudeCode46.4，另Terminus非思考39.3；Qwen51.5为另一预算/模式设置，不能精确排序或默认DeepSeek必强。SWEVerified73.1与73.4也跨harness；HLE模态/工具设置不同不排名。旧论文Terminus思考不兼容不代表后续Nemotron采集无效。
- 新增teacher_strength_qwen_20261016与teacher_strength_deepseek_20261016报告。教师总体分数与单条数据资格分开，成功/协议兼容/独立来源及Base-SFT dev提升才是选轨迹依据；不因教师名字更大就用全量，亦不因此更换题定Base。未运行模型、API、任务、GPU或训练，val选题/清洗仍未恢复；仅文档入Git并保留其他工作流WIP。

## 2026-10-16：剩余镜像改用代理与统一16并发队列

- 用户追问镜像是否可以并发；已从8并发尝试无损补充8-worker。随后实测GHCR直连整层在关闭HTTP2后仍反复unexpected EOF，小段测速不能证明完整镜像稳定。保持固定digest和已完成cache，改用既有38080代理；不修改或关闭用户代理。
- 代理完整单镜像验证于2026-10-15T18:05:47Z通过：先前失败的固定tutao镜像首次成功，SIF1,083,351,040B，SHA256 aec3a53ae84647c537c5e124615055a0093914eee7bdc3b560f4ef46470e4798；Apptainer连接实际指向127.0.0.1:38080。该证据支持切换路径，不承诺固定速度。
- 已精确停止本轮旧调度器/补充队列，统一单个16-worker代理队列2878546；02:09上海复扫109/140、0失败。原8个child均已退出，其中两个大TB pull退出0且SIF分区表通过，合计17,569,775,616B已保留后复扫；其他进程、系统配置、正式题与原722434均不操作。140项全量和HPC最终SHA仍待完成；新64K/8K合成GPU作业723993后续已通过，实证见下一节。
- Mac收尾进程15079已改为逐轮读取当前image-prefetch.pid，现有队列活着时不重复启动；独立只读审阅通过。HPC镜像3040078继续等待源complete并全140项SHA，达门槛后才关闭本次SIF只读rsync。旧进程/日志/进度及partial inode硬链接已归档，不碰用户代理。


## 2026-10-16：统一64K/8K两卡长输入验收通过

- 高优先级作业723993在ACD1-1完成：两H10080GB、TP2/BF16/65536/maxseq4/.85/eager、GDN与MoE Triton、chunked prefill/batched8192；Slurm主/batch/extern COMPLETED0:0、8分44秒，startup410.31秒、server返回0。没有改其他项目722434。
- 五正例HTTP200：文本、32px红图、自动工具调用、同tool ID反馈和57,280-token长输入；显式8192输出cap及v2 sampling/关闭thinking全部落wire。长输入实际usage与固定模板计数相同，标记输出8token/stop、2.560秒。自造57,408本地计数+8192超限请求得到明确400，服务安全计数下界57,345即拒绝，未重试或改cap。
- auth models200/无key401；batch已实证删除/tmp/apex-base-723993.9DtoZS，服务正常退出。当前Slurm默认改为两GPU/16CPU/128G；聚合回执另存base_gpu_smoke_v2_20261016.json，旧723821历史证据保留。未生成满8K、测4并发/持续吞吐或原生benchmark链路，没有正式题/评分/训练。

## 2026-10-16：查找近期强开放权重教师的真实公开轨迹

- 用户要求找开源最新强模型跑的轨迹。本轮research/ego-browser并行核SWE、Terminal、科研/学术一手卡/文件/schema/论文及官方权重仓库，区分数据公开、teacher开放权重、成功标签与harness相容；未下载大文件、恢复val选题/清洗、运行模型/付费API/训练或申请GPU。
- 发现同固定Open-SWE 1db674...早有未下载v1.2：mini/Qwen3.8-Flash-Next 36,577轨迹/17,807源resolved/16Parquet/3,653,370,550B；mini/Qwen3.8-27B 107,267轨迹/41,405PR/49,925源resolved/44Parquet/10,687,441,540B。两者Thinking；前者体量较小，建议先核结构/排除/长度。此前v1.1 Qwen3.6选择未优先审这批新教师，已补清单，不冒称旧长度结论适用于新池。
- 同库DSV4Flash0731 OpenHands另50,295轨迹/23,110resolved/约3.70GB，GLM5.2 Pi原卡207会话→1821累计前缀行，均真实公开但工具/状态协议不同。Qwen3.8公开同表代码/DeepSWE优于旧teacher，仍非本题HARD51/非思考64K8K同条件，不以版本名或发布分数担保迁移。
- 学术新增NVIDIA Math-v4（V4-Pro High，545431行，CoT285516/TIR259915，12Parquet约5.54GB）和Science-v2（混V4Pro/V3.2/Kimi/GPTOSS，作者称2837712，4JSONL约52.69GB，viewer partial）。来源/工具/teacher须分别筛，不能把Science全叫V4或当ASI程序交付；均无图像，未有本题HLE/ASI逐项去污染证明。Proofs-v2和EcoCoder另列备选，不把自然语言verification或质量分当执行成功。
- Terminal：OpenThoughts-Agent-SFT-100K已核准确为GLM4.7-AWQ、Terminus2/Daytona/result，不应与旧OpenHands池混称；新GLM5.2+Terminus2 open-athena仓库公开但缺文档/许可/来源/成功依据，待核不直接入主池。TMax当前真正轨迹10726/成功5795，不用论文16.5K/8K冒充公开量，且bash非Terminus。最新V4函数工具/Pi会话、正式TB/easy25/2.1评测日志都不自动成为合格终端主池。
- 新增latest_trajectories_20261016总报告与swe/terminal/science三专项、passive latest_trajectory_candidates_20261016.json；benchmark_training_data加新入口及OT100K纠正。原data_sources.json/协议/训练参数不变，尚未更换或选入任何最终样本。所有新旧teacher同PR/模板/源问题须联合分组留val、排四正式任务/保守repo/fork，保留逐行许可；不因追新放宽环境和成功资格。
- 本调研仅将上述文档/聚合候选登记入Git，保留其他工作流环境/长输入smoke和脚本修改；关闭自己浏览空间47，未操作别人的浏览器或任务。

## 2026-10-16：结合实测轨迹长度讨论SFT规模

- 用户询问大致数据量。本轮复核当前数据预算、clean完整轨迹均值与已下载数据状态，独立交叉核算，并重新联网阅读AgentTuning/SWE-smith一手资料；保存analysis/sft_data_budget_20261016.md。没有恢复已暂停的选题/清洗，没有导出数据、调用模型/API、训练或改变配置。
- 修正原6M累计预算的解释：三专家3M+同数据Mixed3M只是小预算pilot；旧SWE0.9M按31,174均长约29条记录，Terminal0.7M约53条（mixed约68），科研0.5M约152条；记录尚须按原任务去重，不能直接称独立任务。原学术0.9M含OpenScience0.6M，后者未测长度，不将整池套OpenR1均值。
- 新讨论起点是三专家合计约10–20M完整序列token，优先按15M核算；Mixed同数据再一遍后累计20–40M，15M对应约30M。可核算示例为修复8M、执行4.5M（终端4M+科研0.5M）、学术2.5M；不是用户已确认的新配额，也不是充分专长/提升的门槛。
- 建议任务覆盖量级：修复200–300；终端200–400加科研100–200；学术约2–5千题，广域长度/科研任务映射及质量验收后重算。分别记独立任务、一次性完整数据token、含epoch/窗口历史重复的processed token与新增assistant supervised token，不按切片数或重复epoch冒充新增数据。
- 保留真实训练吞吐为锁量条件：若8h训练预算仅6.4h用于前后向，累计20/30/40M需整组约868/1302/1736非padding token/s；现有vLLM长输入smoke不证明训练可达。推荐量需先与当前评测/交付资源兼容，不因本轮建议延长已定截止或挤占保留缓冲。仅本轮笔记及本节纳入Git，其他工作流修改保留。
