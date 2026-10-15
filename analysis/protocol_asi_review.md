# ASI-Bench 评测协议核验与本实验选择

> 当前执行选择（2026-10-16）：以[评测协议v2](evaluation_protocol.md)为准，ASI使用官方asibench 0.2.0的`direct_llm`，单次程序生成与执行，共享1200s、64K/8K。下文OpenCode/1800s/262K/steps100属于此前候选审计，保留作历史，不是当前正式路线；范围与官方评分规则仍可参考。

更新：2026-10-15。只读核对固定官方框架、公开实例索引和 task_eval 的白名单元数据；未打开正式题面、答案、参考图、隐藏评分内容或任务执行代码，未安装依赖、运行任务、调用模型/API 或申请 GPU。原始框架文件与安全派生审计在 ignored `artifacts/protocol_sources/`。本文件由主协议合并后生效，执行可用性须另做独立自造任务验收。

## 选定范围及其名称

采用 **官方 open evaluation split seed31415 + 同版本官方本地评分实现**，完整 **60 个任务 × B1–B4 = 240 个条件，每模型各一次**。对外标注为 **ASI-Bench seed31415 / open / local / single run**；结果是官方公开实现算出的本地分数，不能写为 Portal 认证官方成绩或官网榜单复现。

- 框架：`apexin-ai/ASI-Bench@cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`（包版本 0.2.0）。
- 数据：`Apexintelligence-AI/ASI-Bench-seed31415@0fa14219cafdbab634d8b3cfbce238a8735a214f`。
- 完整任务与条件清单见 [asi_task_ids.json](source_snapshots/protocol/asi_task_ids.json)。本次按 HF 文件索引只统计每个实例根级 prompt：每层均 60 个。递归数所有同名文件会误计 reference 内的一个 prompt，不可据此变成 61 项。
- 源 metadata 写明 `59 final tasks plus one requested test task`，且 `computer_science.deployment_prediction_sets`、`math.ucb_q_learning_regret` 内部生成 seed override 为 2。两者仍在固定 60 项数据清单中，目录仍以 seed31415 命名；完整保留源状态，不自行过滤、不重新生成。
- 五个 opt-in sample 不计入正式清单。正式实例是评测集；不得将其公开 reference、失败作答及派生解法用于训练或选模。

题面未指定 protected seed，选择官方 open split 本身无须假设额外批准；必须披露上述口径。若交付方后续明确要 Portal 官方认证，则需另固定 protected seed42，不能用 open 分数替代。官网现有聚合榜单也明确 exact scored task-set version 未核实，不适合作为本次固定版本的直接可比分数。

来源：[官方两套评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md#L3-L44)、[默认范围、公开/私有边界](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md#L684-L736)、[固定 open metadata](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed31415/blob/0fa14219cafdbab634d8b3cfbce238a8735a214f/metadata.json)、[官网聚合说明](https://asibench.apexin.ai/leaderboard#scoring-methodology)。

## 主指标和完整性

**主列直接报告原生 `local_score_seed31415.json.mean_percent`，展示名为 “Mean score (0–100), open/local”。** 同时保留官方逐结果 `final_score`、`max_score`、gates/scorer 明细、B1–B4 均值和按学科分项，不把科学任务简单改成二元成功率。

官方公式为：

`mean_percent = 100 × Σ final_score / Σ max_score`，其中求和仅包含 `evaluation_status == completed` 的结果。

本次重新扫描 60 个 task_eval 的**顶层** scoring 权重和 score_divisor，并按官方 `scoring_max_score/normalize_task_score` 计算：**60 项有效 max_score 都是 100**。其中 Ising 权重和 105，经 divisor=1.05 归一。注意不能把 scorer 内层 config.weight 再加一遍。因此在完整、有效的 240 条结果上：

- 每任务每层权重均为 1/240；B1–B4 各占 25%。
- 每层是 60 任务算术均值；overall 是四层均值的算术均值。
- 等价于 60 任务分别对四层取平均、再对任务做 macro mean。
- 学科仅做分项；不能将 11 学科等权后冒充该主指标。
- 原生 mean_percent、上述 macro mean 及 normalized final_score 的算术均值此时相等；这是本版本 60 项有效满分一致的核验结果，不是对任意 ASI 版本的假设。

**完整主结果验收**：240 个预期组合各有且只有一条 agent 结果；`instance_count=240`、`scored_instance_count=240`、`scorer_error_count=0`，组合覆盖与 manifest 一致。Agent 的错误、超时、缺产物按官方 scorer 得分，可能为有效零分；评分器/API/缺评测输入异常属于 `evaluation_invalid`，保留 null 和 failure_kind。官方脚本会排除 invalid，因此未解决时只报告“完成 x/240 的条件均值”和缺失数，不能以被剔除后的均值宣称全量主成绩。重跑评分可使用相同已固化产物，不能因分数低重新作答或多结果取最高。

使用单次重复是本实验设置；官网多数行采用三个独立轮次，不声称复现其三轮均值。保留逐任务/逐层分数及单次运行局限。

来源：[权重满分和归一化](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/scorer.py#L13-L51)、[local 原生聚合](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/local_scoring.py#L1067-L1089)、[按任务/层/学科通用聚合](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/reporting/aggregator.py#L28-L97)、[错误处理说明](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md#L180-L208)。安全派生满分/模型清单已写入任务 manifest，不包含 rubric 或参考内容。

## 执行协议：具体可选参数与验收边界

| 字段 | 本实验选择 | 是否已能由官方字段落实 |
|---|---|---|
| Agent | 内置 `opencode_cli`；OpenCode 1.17.15，tag 当前解析为 commit `5fb0d1cdb363ecafd55402c451c6634ed15b74b1` | adapter 验证版本及命令已核；尚未安装/实跑 |
| 运行模式 | produce-only `asibench run`，完成后独立 `asibench score --repo seed31415` | 现有官方命令；不把评分凭据暴露给 agent |
| 层与次数 | b1,b2,b3,b4；retries=1（含义是一次 attempt）；一次完整重复 | CLI 原生字段 |
| 时间 | **1800 秒/条件**，为本实验固定预算 | CLI 原生 timeout；官方默认是10800秒，可调整；不声称3小时设置复现 |
| CPU/RAM | Docker `os` 默认 4 CPU / 8 GiB / 条件；任务不使用训练/服务 GPU | 原生 OSSandbox 限额；当前60项 metadata 均未声明 requires_gpu，未实测任务 |
| 工具 | 固定 build agent 的本地 shell/read/write/edit/search；关闭 webfetch/websearch、MCP、子代理；所有模型同配置 | restricted 原生只关闭两个 web 工具；额外禁 MCP/task 工具要冻结配置并验收 |
| 网络 | 预装任务依赖；作答期仅允许模型端点，禁止外部信息检索 | **restricted 不等于 bash 断网**，Docker 默认让 OpenCode 保留网络；须由执行环境端点白名单验收，不能假称已隔离 |
| context / 单次输出 | 建议 context=262144、每次 max output=8192；按通用模型服务协议一致 | OpenCode provider model 的 limit 字段支持；需自造任务核对真实请求、服务 tokenizer 与显存 |
| 步数 | 建议 build.steps=100；是 agentic iterations 上限，不是 shell 命令数量 | 固定 OpenCode schema 原生支持；ASI adapter constructor 不接 steps |
| 总 token | 如不另建预算代理，设为“无独立总 token 硬上限”，以1800秒、100步、8192单次限制并记录实际 usage | 不虚构已有80K总预算；辅助 title/compaction 调用需另计 |
| 采样/thinking | 与总评测协议相同；明确 temperature/top_p/top_k、enable_thinking、preserve_thinking | temperature/top_p 可由 OpenCode agent 配置；top_k、Qwen thinking 模板及服务端覆盖须抓真实请求验收 |
| 辅助模型 | title/summary/compaction 如保留，必须指向同一受测模型；small_model 同一模型，禁止外部小模型；辅助调用也记成本 | 需要隔离配置；OpenCode 确有额外 title/compaction 生成，不能只数主 trajectory 的 step |
| 环境 | 每条件独立工作目录、HOME/XDG、固定镜像 digest；agent 只拿 prompt/data/产物目录，不挂 reference/scorer/凭据 | 官方隔离结构可复用；具体主机目前未证明 Docker 就绪 |

不存在“一张模型共用的 ASI 官方 token/步数标准值”可自动沿用。上述 context/输出/步数是可落地的推荐设计值，需主协议选择和工程烟测验收后写进实际冻结配置。CLI 的 `--seed` 在读取 pregenerated instances 时不重新生成题目，也不能当作 inference 请求已传 seed 的证据；dataset seed、runner seed、模型 sampling seed 分开记录。正式 Base 不承担协议调参任务。

本次对固定 OpenCode v1.17.15 一手代码补查，确认 `agent.steps/temperature/top_p`、provider `limit.context/input/output` 都有 schema，不能再概括为框架完全无法配置；但 ASI adapter 自己生成的 inline config 仅填模型 name 和 web 工具开关，仍须用隔离的 OpenCode 配置合并这些设计值。固定配置、provider npm/AI SDK 依赖、system prompt、工具 schema、压缩策略和真实请求样本 hash 一并保存。

来源：[ASI adapter 构造器与原生配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/opencode_cli.py#L108-L228)、[CLI 时间/attempt/seed](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L1457-L1485)、[资源限额](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L71-L108)、[OpenCode 网络特例](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L844-L873)、[固定 agent schema](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/core/src/v1/config/agent.ts#L18-L37)、[固定 provider limit](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/core/src/v1/config/provider.ts#L41-L62)、[真实步数控制](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/prompt.ts#L1170-L1179)、[title 辅助调用](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/prompt.ts#L193-L236)、[token/采样请求准备](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/llm/request.ts#L80-L130)。

## 原始 Judge 与本实验替代协议

本次对 60 项配置仅提取 scorer/model/weight/num_judges 等白名单字段。**13 项显式模型全部是 `openai/gpt-5.5`**，其余47项没有显式 model，不据此声称47项所有 custom scorer 传递依赖已证明完全无 API。

| 类型 | task_id |
|---|---|
| 明确 multimodal scorer（9项，至少需要图像输入） | biology.calcium_ip3_dyk_oscillations；biology.contextual_dna_regime_mapping；biology.protein_folding_go_model；chemistry.vtst_tunneling_corrections；earth_science.2_e_soil_carbon_nitrogen_cycling；materials.ising_domain_growth；physics.ag_strip_dielectric_inference；physics.ks_2d_anisotropic；physics.paired_nanorod_negative_index_retrieval |
| 明确 llm_judge（3项） | chemistry.metadynamics_for_dipeptide_in_vacuum；chemistry.sapt_water_dimer；electrical_engineering.cmos_opamp_design |
| 自定义 scorer 配置显式同模型（1项） | math.nnls_modulus_deblur |

公共 Judge 路由默认也为 `openai/gpt-5.5`。运行时 endpoint/key/protocol override **不替换 model**；multimodal 会将预测图和参考图作为 `image_url: data:image/...;base64` 送给模型。DeepSeek endpoint不能在保留GPT5.5模型名时调用该原模型，但这不等于DeepSeek不支持图像。当前deepseek-flash原生支持图片，已有官方key双图实测成功；显式替换模型/服务并适配输出解析后，可作为需披露的本实验替代Judge，原GPT5.5配置则保留作来源记录。

**原GPT5.5完全复现所需条件（非替代路线前置）**：提供能真实调用 `gpt-5.5` 且支持图像输入的 OpenAI API 凭据配置位置，或同一模型的兼容网关地址、模型 ID 映射与凭据环境变量。只需配置位置/变量名，不需在聊天粘贴 key。冻结源码指定的 rubric、模型、温度、num_judges 和重试；不为省 API 降级视觉评分或把 evaluator_unavailable 填零。

来源：[唯一默认与模型映射](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py#L87-L102)、[override 保留配置 model](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py#L197-L204)、[明确 GPT-5.5 图像评分配置第79–82行](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/biology/calcium_ip3_dyk_oscillations/task_eval.yaml#L79-L82)、[图像请求构造](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L129-L193)。这里仅核查配置与通用传输，未读取实际参考图或题面。

## seed42 与交付差异，以及最小剩余事项

保护集 seed42 数据 revision `4533397770a85ef79afe31e0361cbd9c42d5b50d` 有同样 60 个任务ID和四层，但输入不同、无公开 reference。官网认证要求 Docker `os` 运行证明、Portal 登录/PAT、上传 draft、网页确认、排队私有判分；`score --repo seed42` 被 CLI 拒绝。此路线不是只替换 seed 参数，亦不能将 seed31415 的本地数值上传成官方分数。目前本实验选择 open/local，所以无需为当前协议索要 Portal 账号；若交付要求改变，再落实账号与时效。

若要求原GPT5.5模型完全复现，仍缺原Judge凭据；本实验替代路线已有deepseek-flash图文接口实测，缺新key不再是技术阻断，仍需独立校准和实现验收。Docker执行主机、endpoint网络、隔离配置及Qwen工具/生成参数透传属于工程验收事项，可以先在自造任务推进；不能因为尚未验收就宣称已完成 Base 测评。无需再向用户询问“是否所有四项必须统一harness”或让用户决定OpenCode低层字段。

来源：[官网评分工作流及差异](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md#L21-L44)、[seed42 固定索引](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed42/tree/4533397770a85ef79afe31e0361cbd9c42d5b50d)。
