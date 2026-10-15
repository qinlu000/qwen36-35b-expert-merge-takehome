# 实验要求与 API 依赖核对稿

日期：2026-10-15。需求依据是用户粘贴的多专家训练与模型合版题面；当前模板 README 的 SFT→第二阶段优化路线不替代该题面。本稿用于用户审核理解，不代表方案已定稿或实验已完成。

## 1. 总目标与执行条件

- 实际完成自建数据、多专家训练、参数合版和四项全量评测，研究专家划分与合版带来的收益、冲突及退化。
- 题目指定 Qwen/Qwen3.6-35B-A3B，目标单一 35B 级模型；算力不足可使用同系列约 7B 级基座，例如 Qwen3-8B，并在 README 披露理由。
- 专家数量、每个专家大小、目标划分、数据和训练方法由候选人设计；题目没有强制四个专家。
- 用户最初给出的剩余窗口为 71h，最后预留 12h，核心窗口为 59h；前期准备也计入该窗口，不随对话重新起算。
- 本任务可额外申请最多 4 张 H100，通过 hpc3 使用 Slurm。评测任务自身的 GPU 计算也计入本任务四卡资源安排。
- 记录主动工作时长、训练/评测耗时、GPU-hours、CPU/沙箱资源及费用或估算方法。

## 2. 模型与专家设计

- 固定基座 revision、tokenizer、chat template、依赖与代码版本。
- 论证专家数量、模型大小、按 benchmark 或任务类型/数据域划分的依据。
- 记录每个专家 LoRA/QLoRA/全参方式、目标模块、rank、量化、学习率、batch、步数、上下文和随机种子。
- MoE 的内部 routed experts 不等于本题训练的专精模型；显存必须考虑约 35B 总权重，不能按约 3B 激活参数计算完整权重显存。

## 3. 训练数据与防污染

- 每个专家需要面向目标任务的自建训练集，可使用公开 issue/commit/补丁/测试或独立合成任务。
- 说明来源、许可、清洗、去重、难度分层、防 benchmark contamination 方法，以及各专家数据量和配比差异的理由。
- 训练集、独立开发集与正式评测分开。独立开发集用于训练强度、checkpoint 和合版配方选择。
- 四项 benchmark 的题目答案、参考补丁、隐藏测试及测试反馈不得用于训练或选择 checkpoint；不能根据正式评测结果反复挑合版系数或最终模型。
- 最终权重与配方冻结后评测。评分器可在评分阶段使用参考材料，但不能将它们流入训练和调参数据。

## 4. 真实训练与对照

- 实际完成所有专家的训练，说明训练方式选择理由。
- 至少一个可解释训练对照，例如专家划分、数据量、rank、训练强度，或多专家合版与单模型混合数据训练的比较。
- 对每个专家保存训练与验证 loss 曲线、原始数据和绘图脚本，标注坐标、实验名及 checkpoint。
- 报告时间、峰值显存、吞吐、checkpoint 大小、学习率和保存策略；保留配置快照、命令、种子和完整日志。

## 5. 参数合版

- 将专家权重或 adapter 合成一个模型；运行时路由、投票或调用多个专家不等于本题要求的参数合版。
- 解释方法原理、适用前提、选择理由和参数冲突处理。
- 至少比较两种合版方法，或对合并系数、层范围、是否保留基座等关键配置做消融；有消融则提供指标图及源数据。
- 最终配方用独立开发集选择，再固定后做正式全量评测；报告各 benchmark 的收益和损失。

## 6. 正式评测范围

| 模型 | SWE Pro v2-hard | HLE | ASI-Bench | Terminal-Bench 2.0 |
| --- | --- | --- | --- | --- |
| Base | 全量必做 | 全量必做 | 全量必做 | 全量五次必做 |
| 每个专家 | 目标项全量必做；其他鼓励 | 同左 | 同左 | 若为目标项，须全量五次 |
| 最终合版模型 | 全量必做 | 全量必做 | 全量必做 | 全量五次必做 |

- 训练前固定各项官方来源、版本/commit、split、完整任务 ID、主指标、聚合、容器与评测配置。指定版本不可获取时先联系面试方，不能擅自替换。
- 每个 benchmark 内，各模型使用相同任务、容器、Agent/prompt、工具权限、thinking、preserve_thinking、量化、上下文和推理预算。
- 保存逐题/逐任务输出、判分、状态、错误与超时、耗时、token 和成本；环境失败单列并按预先固定规则处理，不能删除失败后提高得分。
- 报 resolved/pass/accuracy 等主指标、运行失败率、平均耗时/成本，以及 bootstrap 置信区间或其他不确定性估计。
- 四项百分制主指标等权宏平均，与本次实测 Base 比较；使用同任务的配对 bootstrap 估计提升区间，报告重复运行波动和所有退化。
- 宏平均提升 3 个百分点是挑战目标，5 个百分点是优秀参考，不是已验证的必达门槛；官方成绩只能作背景。

### 四项协议

- **SWE Pro v2-hard**：完整指定 hard 任务集，官方 resolved rate；记录 hard 依据、任务 ID、镜像、评测器和 Agent commit、prompt、工具、步数、token 和超时。目前核验到官方 V2 HARD-51（51 项），必须用 V2 对应流程，不用 V1 管线替代。[官方 V2 协议](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)
- **Terminal-Bench 2.0**：Harbor/Terminus-2；3h 超时、32 CPU、48 GB RAM、temperature=1.0、top_p=0.95、top_k=20、max_tokens=80K、256K context；相同五组种子，报告五次均值和标准差。目前注册表固定版本含 89 项，每模型为 445 trials。[官方注册表](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)
- **HLE**：固定版本/split 的准确率；提前说明图像题、工具、答案抽取和 judge 版本，text-only 与多模态不能混报。目前官方完整 test 是 2500 题；具体采用哪种模态协议尚未确定。[官方数据卡](https://huggingface.co/datasets/cais/hle)
- **ASI**：固定官方版本、完整任务集、模式/seed、工具预算、主指标与聚合，保留分项、原始输出和评分凭据。目前公开 seed31415 有 60 项 × B1–B4=240 组合，可本地评分；protected seed42 依赖官方 Portal。选择 open split 是候选方案，不能将其称为 protected 官方榜单成绩。[官方评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)

## 7. 哪些地方需要 API

| 环节 | 调用对象与用途 | 外部模型 API 的性质 |
| --- | --- | --- |
| 训练 | H100 上训练 Qwen 权重/adapter | 本身不需要外部 LLM API |
| 合版 | 本地权重/adapter 运算 | 本身不需要外部 LLM API |
| 评测作答 | Base、专家、合版 Qwen 的本地推理服务 | 可用 HTTP API 接入框架，属于自部署推理；不能让 DeepSeek/GPT 代替被测 Qwen 做题 |
| SWE 判分 | 官方容器/测试验证修复 | 核心流程不依赖外部 LLM judge；仍有镜像、环境和计算成本 |
| TB 判分 | 每个任务的官方 verifier | 没有统一强制购买某个商业 LLM 的要求；尚未逐项证明全部任务没有外部依赖 |
| HLE 判分 | 模型回答与参考答案的抽取/匹配 | 官方脚本默认 o3-mini；可研究采用固定、披露并校准的 DeepSeek judge，属于本实验设置，尚未定稿 |
| ASI 判分 | 文本/图像 judge 与程序 scorer | 已核验版本的 13 个任务显式指定 openai/gpt-5.5；保留原始评分契约需要能调用该模型的接口，DeepSeek key 不覆盖这一请求 |
| 合成数据 | 外部 teacher 生成独立训练任务/答案/轨迹 | 可选；也可使用公开数据或本地模型生成，不是题目强制项 |
| HF/GitHub | 下载、上传与仓库鉴权 | 仓库网络接口与 token，区别于付费 LLM 推理/判分 API |
| 云沙箱 | 按需要创建任务容器 | 若本地 HPC 可满足则不必购买；若另选云后端，需单独计成本，当前未决定或租用 |

题面没有逐字要求某个商业模型或供应商；GPT-5.5 来自当前核验的 ASI 评分配置。HLE 与 ASI 的 API 是给被测回答/产物判分，不替代 Qwen 作答。[HLE judge](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)、[ASI judge 配置示例](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/biology/calcium_ip3_dyk_oscillations/task_eval.yaml)、[ASI 路由](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py)

工作量示例仅用于核对，不是定稿：若每项恰有一个目标专家、HLE 采用完整 2500 题、ASI 采用公开四层，Base/目标专家/合版三个对象分别需要 SWE 153 次任务、HLE 7500 次生成和对应判分、ASI 720 个任务条件、TB 1335 trials。ASI 13 个 judge 任务对应 156 个任务条件结果，实际 judge 调用可能因多个评分项、图像、重试而更多。TB 的 1335 trials 主要是本地模型/沙箱工作量，不能直接当作 1335 次付费外部 LLM 调用。

## 8. 分析与交付

- 合版模型至少 20 个失败案例，按定位、补丁、测试理解、合版退化、工具/环境、超时等归因，给出至少三个下一步实验。
- 按指定模板建立独立候选人 GitHub 仓库，包含环境/安装命令、数据构建清洗、训练、合版、四项评测、汇总绘图脚本与固定配置。
- README 写明研究问题、实验矩阵、硬件时间预算、benchmark 版本/split、限制、复现步骤、GitHub/HF 链接及 revision。
- 保存配置快照、依赖锁、启动命令、种子、代码版本、硬件、资源、训练/评测/错误/超时日志，以及所有模型版本的逐任务结果和失败清单；可由原始日志重新生成表格与图。
- 各专家和最终合版 checkpoint 上传本人 HF，必须 Public，可交完整 LoRA adapter 或合并权重；附基座 revision、merge recipe、加载方法、模型卡、许可证，并验证公众无需额外授权可下载。原始 Base 引用官方链接。
- `report.pdf` 不超过一页，固定摘要（150–200 个中文字符）、过程、结果；结果含四项 × 模型分数矩阵、专家评测范围、宏平均提升、失败率和成本。详细日志、曲线、失败分析和区间另存仓库。
- 模型链接/revision 按面试通知发送指定邮箱。
- 不接受只有 dry run、没有合版、没有全量评测的交付。

## 9. 当前状态与未定事项

- 已完成：需求与官方来源核验、SSH 入口检查、HF/HLE 权限与 DeepSeek 鉴权；小型基座配置快照；ASI 显式 judge 模型字段审计。
- 未完成：正式 benchmark manifest/协议冻结、训练数据构建、专家方案定稿、环境运行与吞吐验证、训练、合版、正式评测和模型发布。
- 专家数量/划分、rank、数据量、训练对照、merge 配方、HLE judge/模态、ASI split/重复数仍属待设计项，不应描述为题目已经指定。
- 用户已允许必要 API 合理使用，无需逐次确认；最新要求先讨论数据/工程/算法/评测方案再执行，当前停止新增代码、模型 API 调用和实验。讨论稿见 `PROJECT_PLAN.md`，尚未定稿。
- 核心资源风险是全量评测的 CPU/RAM 沙箱并发、任务计算、镜像/隔离兼容性和推理吞吐；四张 H100 不能独立证明可在窗口内完成。

更细的版本证据见 `analysis/benchmark_sources.md`、`analysis/terminal_hle_feasibility.md`、`analysis/model_feasibility.md`、`analysis/judge_requirements.md`。
