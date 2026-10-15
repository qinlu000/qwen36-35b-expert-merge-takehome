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
- 判分器需区分 API 兼容与评分协议兼容：HLE 自定义 judge 需要固定、披露并验证实现；ASI 的 transport override 仍保留任务声明的判分模型，不能直接将 DeepSeek 官方接口当作所有指定 judge 的替代。仍在核验所需模型清单。
- 添加 `.env` / `.env.*` 的 Git 忽略规则（保留 `.env.example`），避免后续将实际凭据文件提交到仓库；提交前已用真实凭据匹配检查暂存差异，未发现密钥值。

## 题目来源

- 用户附件：`/Users/caoqinlu/.codex/attachments/20b2f4c3-6e03-4746-a389-d488086d7780/Pasted text.txt`。
- 初次理解记录以附件为准；后续官方来源和可用性核验见 `analysis/`，各记录明确区分文档证据与实际运行结果。
