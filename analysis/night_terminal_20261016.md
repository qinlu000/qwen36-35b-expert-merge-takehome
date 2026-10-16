# 新版 Terminal 数据与环境推进记录

2026-10-16，北京时间。用户已批准持续推进、只用新版数据；旧池不回退。此文档持续追加实际进展和未决项，root 统一汇总至 `overnight_progress_20261016.md`。

## 第一轮实际结果

**发现比 OpenThoughts GLM-4.7 更合适的新主池候选：[TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K)。** 作者于 2026-10-09 发布论文，声明用 DeepSeek-V4-Pro-0813、Terminus2 生成 2,852 条轨迹；配套 [TerminalHorizon-Environment](https://huggingface.co/datasets/shunzou05/TerminalHorizon-Environment) 提供 1,535 个 Harbor 任务包。两仓均明确 Apache-2.0，第三方组件仍遵守其原许可。与只有消息的旧候选相比，这条线索同时有新教师、相近 harness 和可获取原环境。

固定版本与已取得证据：

- 轨迹 `45f1e98e317d3639437f0eb02f4e8bc5825732f3`；1,754,720,383 字节 JSONL，发布 LFS SHA256 `285c8c673563cce2d7ff49367f0fb8bef429aaacaf143241181158fb87fded76`；80 正在下载，尚未冒称完成。
- 环境 `e55b3e99927ed6b9b2e4abf2fa93e965dd0503ef`；metadata 2,963,500 字节已完整下载并核 LFS SHA256 `5c5a14d168dfe617a9da2277b4f4c3501ed8785ff08963bb812851fcd79078b4`，实际 1,535 个不同题面，25 个原始领域。索引含 task_id、instruction、Dockerfile、原分类、package_bytes、file_count。
- 全部 1,535 题面与已冻结 TB89 的 normalized exact hash 比较，命中 0。这只是本项目精确排除；作者论文另报告多种近重复及语义核查，但不能替代本项目最终排除回执。[作者去污染方法](https://arxiv.org/html/2610.13166v1#A7)
- 固定轨迹的严格 HTTP206 前 16MiB，含 26 条完整 JSONL；**26/26 均能按第一条 user 中的 Task Description 精确匹配唯一环境题面**。这是前缀连通检查，不能当全池随机估计。
- 轨迹顶层仅 `conversations`，实际 assistant 为 `<think>…</think>` 后接 Terminus JSON，含 analysis、plan、commands；不应把协议必需的 analysis、plan 当隐藏思考一并删除。精确源码 revision 与完整 collector 配置仍待核。

**质量边界：这不是“全成功轨迹池”。** [论文附录 F](https://arxiv.org/html/2610.13166v1#A6) 明确按过程有效性、基于环境证据的进展、多轮训练价值筛选，评分模型为 gpt-5.6-luna/high，且不向 reviewer 提供最终 reward；未完成但有有效探索的轨迹可以保留。公开轨迹本身没有逐行 reward。当前可称作者过程筛选的 SFT 候选，不可写成逐题 verifier 全通过。进一步可重放有限任务或用公开 reference/verifier 验证任务包可运行；无需把整个 2,852 池全部重跑才开始后续清洗。

## 目标配额和语义分类

TB89 官方 16 类固定分布按最大余数法得到：

| TB 类 | 官方任务 | val 目标 | train 目标 |
|---|---:|---:|---:|
| software-engineering | 26 | 29 | 146 |
| system-administration | 9 | 10 | 50 |
| security | 8 | 9 | 45 |
| scientific-computing | 8 | 9 | 45 |
| data-science | 8 | 9 | 45 |
| debugging | 5 | 6 | 28 |
| file-operations | 5 | 6 | 28 |
| mathematics | 4 | 5 | 22 |
| data-processing | 4 | 5 | 22 |
| model-training | 4 | 4 | 22 |
| machine-learning | 3 | 3 | 17 |
| games | 1 | 1 | 6 |
| personal-assistant | 1 | 1 | 6 |
| optimization | 1 | 1 | 6 |
| data-querying | 1 | 1 | 6 |
| video-processing | 1 | 1 | 6 |
| 合计 | 89 | 100 | 500 |

这张表是需求，尚非供给或选集。TerminalHorizon 的 25 个专业领域和 TB16 类不同，需要根据任务交付物语义标注，不能整域硬映射。root 已批准本支 DeepSeek 分类上限 ¥10，计入全夜 ¥30；仅对独立候选任务做类型分类，保留不确定度、原类别和证据，不让分类模型编造成功标签/验证器。

已核 [DeepSeek 官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)，`deepseek-flash` 当前映射 V4.1-Flash；峰值 USD 每 M token 输入 miss 0.3/hit 0.006、输出 1.2。以峰值乘 8 CNY/USD 的保守上界控制本支 ¥10；实际每请求记录返回模型、usage、清单与累计上界。尚未发出付费分类调用。

## 环境实物与部署缺口

环境仓包含 8 个约 864MB 的 tar.gz，每题完整放入某一片。第一片已开始下载。前缀实际可读第一个任务的 `instruction.md`、`environment/`、`solution/solve.sh`、`task.toml`、`tests/test.sh`，符合发布卡声称的 Harbor 格式。

首题存在 `docker-compose.yaml` 与额外 authority 服务，task.toml 声明 Linux、8 CPU、16GB RAM、18,000秒 agent 限时。**原环境可获取不等于当前 Apptainer 后端立即兼容**：多服务 Compose、Dockerfile 构建、entrypoint、权限和实际4CPU/8GB/30min协议均要检查。val 需在不改变任务内容的前提下完成本项目约束的运行适配，原资源与本实验偏差同时记录。不能挑最小最短任务冒充目标分布，也不能把已取 metadata 路径叫作已验收的可执行 val。

## 被降级的另一条新线索

`open-athena` 与 `penfever` 的 GLM5.2 vanilla 仓解析为同一个固定 revision `ef4c2f32a99b195859527d8a3a90aa3331d22aa9`，仍无 README/card/license。实际下载第 0 片（199 行）：agent 全 Terminus2，model 仅 `hosted_vllm/1502109395825196`；result=1.0 有 89 行、0.0 有 106 行、timeout 4 行。多数任务是阅读多轮 chat 后将下一回复写入 `/app/response.txt`，其 verifier 用 gpt-4o-mini checklist；该片 51 行 verifier 日志有评分额度耗尽错误。成功字符串不能消除任务分布和许可问题，故不作为 Terminal 主池放行。这部分仅为静态审阅，未调用其 judge，也未执行其任务。

## 后续动作与状态

1. 完成固定轨迹下载及 SHA，扫描全池 join、think 清理、官方 parser 与真实 tokenizer 长度；整理逐条 hold 原因。
2. 按 TB16 类标注公开 instruction，先审低置信度/歧义类，再按任务家族分组和配额形成待审 100/500 清单；演化同族及近重复不能跨 train/val。
3. 解出有限完整任务，查多服务/外网/权限/资源；选择独立校准任务验证容器、reset、reference 和 grader 链路，与最终 val/训练隔离。完成前不宣称可执行 val 已 ready。
4. 供给不足或关键环境无法适配时保留缺口，不用旧池或正式 TB 题补数。

80 证据根：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/new_terminal_horizon_20261016/`。脚本 `scripts/audit_terminal_horizon.py`。本轮至此未占 GPU，未运行正式 benchmark，未运行轨迹命令，付费模型调用 0 次。

## 03:32 追加：真实长度和分类接口

已用固定 Qwen tokenizer、固定模板及 Harbor Terminus JSON parser 静态检查上述前缀 26 条：清后完整序列均值 **83,984** token，P50 **69,979**、P95 **128,562**、最大 **212,975**，仅 **10/26 ≤64K**；清前均值 182,410。完整序列包含题面、全部 observation 和模板。清后 assistant 内容均值 27,443，不能替代完整长度；最长单次 assistant 8,684 token，也超过约定 8K。2 条含 3 次 parser 错误，0 条不闭合前缀 think，25 条至少一次完成代理。完成代理不等于 grader 成功。样本为有序前缀，后续全池 hash 抽样 128 条再估总体。

**这使长轨迹分窗成为实际待决问题**：不能为了凑 500 题只挑短任务，不能将截掉尾部的序列叫作完整任务。先完成候选选择、保留完整数据和长度证据，训练窗口/逐轮监督方式仍需按既定训练方案确定。未擅自启动训练或 GPU backward。

分类首 24 题接口预检通过，返回 `deepseek-flash`，prompt 23,656/output 1,095 token，峰值×8 成本上界 ¥0.0672864。之后按批继续；遇到一条越界类 `robotics`，保留 proposed_category、改标 uncertain/low，重用已付费响应，未重复请求。中低置信度和宽泛职业工作流不会自动进入最终选集。逐请求原输入、响应与 cost ledger 均在 ignored annotations 目录。

长下载经过代理被截断，实际接收 191,684,581 字节；未据此声称完成。现已改为严格 32MiB HTTP206/Content-Range 续传，最后仍核完整文件 LFS SHA。

已读本项目固定 Harbor Singularity 源码，`_validate_definition` 要求 `task.toml [environment].docker_image`，不会把任务原 Dockerfile 自动构建成镜像。Horizon 首包没有该字段，因此部署还需要镜像构建与多服务适配，而非只更换路径。[固定 Harbor 源码](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)

## 首版划分已落盘：99 val 候选、427 train 候选

1,535/1,535 个公开任务说明已全部分类，64 次 DeepSeek 请求，返回模型均记录在逐请求 ledger；峰值费率乘 8 汇率的总费用上界 **¥4.269956544**，低于本支 ¥10。其中 high 884、medium 601、low 50；原专业分类与标注证据保留。分类仅用于任务类型，不预测成功或执行结果。

`scripts/select_terminal_horizon.py` 已实际运行：按相同任务题面、TF-IDF近重复规则、校准任务保留、官方精确排除建立候选；先按目标挑 val，再按目标挑 train。低置信度与 uncertain 暂不选；达到 cosine .65 的任务保守归族，.35–.65 仅列候选复核且与已选 val 相近者不入 train。本池 .65 以上 0 对、.35 以上 5 对，源演化父子关系仍未公开，因此不能把这一启发式等同完整家族去重证明。

| 类别 | val 实选/目标 | train 实选/目标 |
|---|---:|---:|
| software-engineering | 29/29 | 146/146 |
| system-administration | 10/10 | 50/50 |
| security | 9/9 | 45/45 |
| scientific-computing | 9/9 | 45/45 |
| data-science | 9/9 | 20/45 |
| debugging | 6/6 | 4/28 |
| file-operations | 6/6 | 28/28 |
| mathematics | 4/5 | 0/22 |
| data-processing | 5/5 | 22/22 |
| model-training | 4/4 | 22/22 |
| machine-learning | 3/3 | 17/17 |
| games | 1/1 | 6/6 |
| personal-assistant | 1/1 | 6/6 |
| optimization | 1/1 | 6/6 |
| data-querying | 1/1 | 4/6 |
| video-processing | 1/1 | 6/6 |
| 合计 | **99/100** | **427/500** |

没有通过改标签、重复多 rollout 或挪用正式 TB 题补齐缺口。清单是任务级候选；完整轨迹下载后还须确认逐题 join、清理、协议及完整回合长度，才能导出标准 messages 训练文件。**99 val 当前仅完成题目选择，尚未完成原容器/验证器的本地运行验收。**

80 清单：`proportional_candidates/train_tasks.provisional.jsonl`、`val_tasks.provisional.jsonl`、`near_duplicate_pairs.review.jsonl`、`near_val_train_holds.jsonl`、`summary.json`。全在上述统一 evidence 根下。选样按确定性 family hash，不按长短/容易程度；两项独立校准任务不入 train/val。

工程实物更新：第 0 个环境片完整 864,092,605 字节，已核 LFS SHA `a17d18eb14481528d91fa1623486f19c0f608549fc773989c137059408fdc8a1`，含 **186 个任务，31 个带 Compose**。80 已得到两片完整核验；其余仍按 2 路后台 Range 下载，日志 `environments/download.log`，启动 PID 回执 `2151624`。校准目录 `calibration_tasks/` 解出了 seismic 与 thermal-hydraulic 两个完整原任务；尚未执行任务代码。

类型映射的不确定性：只读官方 task.toml 分类与任务 ID 后，确认官方 TB 类并非完全互斥的自然语义类别，例如 data-science 含 HF inference/MTEB retrieval，数学含 cryptanalysis，software-engineering 也含证明及 bug 修复。因此本项目语义分类只能作为公开、可复查的近似，不应声称已精准复刻官方类别边界；现有 gap 可能既反映新源供给，也反映边界差异。应在训练前复核目标缺类候选及跨类任务，不为追求配额改变原题含义。

## 完整轨迹核验及训练结构文件：以 messages_v2 为准

固定 1.75GB 文件现已完成下载和完整 LFS SHA 校验，**2,852 条全部可读**，顶层全部仅 conversations；user/assistant 各 150,634 条消息，每轨迹 18–806 条消息。

全池静态检查实际结果：2,843/2,852 条可按完整题面唯一 join 环境索引，覆盖 1,531 个任务；9 条题面没有精确 join，未猜配。419 条含 602 次 native JSON parser 错误，0 条不闭合前缀 think、0 条角色交替错误；正式 TB89 完整题面 exact 命中 0。原文件及所有失败行索引均保留；不把局部解析失误直接叫作任务失败，但首版训练导出先选择全程 parser 通过的完整轨迹。

先从427任务候选导出414条结构通过的 train，随后仅从同类别、无 val 占用且通过同样筛选的新源候选补选，**messages_v2 恢复427个训练任务**。保持原99个task-level val名单；其中91个有可用结构合格的教师轨迹，可用于 held-out teacher-trace loss，不能替代原环境 task-success val。

- 最新训练文件：80 `messages_v2/train.messages.jsonl`，**427 条完整原轨迹，106,701,187字节**；SHA256 `b22d3ef722f75bb8bf79bc58b74ba913e4efb482b98d45fb72e6cadbfe076a2f`。原 v1保留作过程回执，集成以 v2为准。
- val教师轨迹：`messages_v2/val.messages.jsonl`，91条，22,786,931字节；SHA256 `4bf27068b43b7a96d22f9d85e29f462c2a1153c642b9d22912206e3edbcda916`。
- train包含21,728条assistant消息，423/427在最后一条assistant给出native task_complete；另外4条仍是作者通过过程筛选的未完成示范，状态明确记录。该代理无论true/false都不等同独立grader标签。
- `scripts/materialize_terminal_horizon.py`只删除assistant开头闭合的think块；user/observation逐条字节保持一致，所有回合完整保留，无序列/assistant截断。JSON analysis/plan/commands保留。tools=[]，真实终端观察是user消息；root应仅监督assistant、屏蔽user和观察，并通过正式Swift CPU窗口/mask检查。

**协议对齐已取得逐字证据：**全部518条v2导出轨迹，第一user中Task Description之前的2,834字符协议前缀，与项目冻结Harbor Terminus-2 JSON模板经原生 `.format()`处理后的前缀完全相同，SHA256均为 `c115067a875398efed908dd82c3a71178205c027ea0ce88c5eb5739a576e1847`。不是只比较“Terminus2”这个名字；必填字段、tmux keystrokes、duration、完成规则均一致。publisher执行代码精确commit未公布，不能声称整个collector实现字节相同，但训练/目标的可见协议已一致。

427 train／91 val trace全部原样完整序列及完整user-assistant回合的Qwen长度审计正在2 CPU上进行；结果将写 `messages_v2/length_{rows.jsonl,summary.json}`。root已获用户正式LoRA训练授权，此分支不自行训练，交标准文件供root整合及窗口验收。质量依据是作者过程筛选＋本地结构协议验收；独立成功率、原环境构建/运行和部分来源演化谱系仍是显式未决项。

## 03:55 稳定交付：messages_v3＋全部实际长度

正式集成请用 **messages_v3**。v2那4条未完成轨迹均在有充分备用的software-engineering类，尾部仍在诊断测试失败/继续构建；同类确定性顺序替换后，v3仍是 **427个独立任务、全部最后task_complete=true、全程native parser通过**。选样没有按长度重排，原99个task-val集合不变。task_complete只作完成代理，不充当独立成功标签。

最新训练路径：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/new_terminal_horizon_20261016/messages_v3/train.messages.jsonl`，**104,679,709字节**，SHA256 **`dbe05f654a20e7d6beacba334f9ee18d106cad788fe3290838ef2857660b8f71`**。val trace仍91条，路径同目录`val.messages.jsonl`、SHA不变。所有2,852条原始轨迹的协议前缀均与冻结目标模板渲染结果逐字相同；并非仅导出518条一致。

427 train＋91 val trace的实际Qwen token测量已全部完成：

| 统计 | train | val trace |
|---|---:|---:|
| 完整序列token总和 | **33,956,071** | 7,297,217 |
| 完整序列均值 / P50 | 79,522 / 67,571 | 80,189 / 67,128 |
| 完整序列P95 / 最大 | 172,665 / 402,023 | 164,212 / 247,984 |
| 完整序列≤64K | 203/427 | 42/91 |
| assistant内容token总和 | **10,530,453** | 2,265,479 |
| assistant消息数 | 21,211 | 4,799 |
| 单assistant最大token | 14,564 | 8,481 |
| 单assistant≤8K | 21,186/21,211 | 4,797/4,799 |
| 完整回合单位＋初始题面前缀≤8K | 21,069/21,211 | 4,771/4,799 |
| 完整回合单位＋初始题面前缀≤16K | **21,209/21,211** | **4,799/4,799** |
| 完整回合单位＋题面前缀最大 | 17,009 | 12,022 |

完整回合单位定义是一个user/assistant成对回合，后续单位保留原第一user题面作为前缀。这些不是ms-swift最终processed tokens：组合多个单位和重复题面会改变训练计算量，root的窗口/labels审计才是最终训练预算。16K单位覆盖99.99%，仍有2单位不能整回合放入16K，应整单位隔离/记录，不能伪截断。25条train单次assistant超过评测8K输出上限，需记录这一源轨迹与评测预算差异。

v3所有assistant都能直接严格`json.loads`，没有依赖自动修复的无效JSON，且没有duration>60。79个train、16个val轨迹有native parser的无换行warning：大部分是空轮询、tmux控制键或交互程序`q`退出；少量其余无换行命令保持原文，逐项回执位于`protocol_warning_rows.jsonl`及`newline_warning_classification.json`，没有擅自补换行改变真实动作。

项目另对全部1,535训练候选instruction与冻结TB89的公开instruction作NFKC/casefold/Unicode词13及14-gram排除，匹配跨度 **0**；未读取正式答案、测试或结果。结合exact hash仍不能证明不存在语义或来源演化重叠，边界明确保留。

原99个val任务的包内regular files索引合计2,624,913,442字节，最大单任务约1.716GB；这不含容器基础镜像、构建下载依赖和运行产物。原环境全部8片仍按后台PID`2151624`下载，每完成一片核LFS并写`environments/download_receipts/`；root可读`environments/downloads_summary.json`获取实际完成数，不能把下载进度当native val验收。

该分支至此API分类费用上界仍 **¥4.269956544**，无后续付费调用；没有GPU作业/正式benchmark执行/训练。后续主要工作是原val环境的构建、权限/Compose支持及reference/grader运行验收，不阻塞已交付训练文件的CPU窗口检查。

## 训练容量核算：局部回合可装入，不代表历史完整

**训练窗口和评测上下文是两项独立设置。评测仍为64K总上下文／8K每次输出；以下16/32/64K只做训练容量比较，未选择训练窗、未输出训练window、未改root loader。** 上述16K覆盖99.99%的结论只说明单个局部回合加题面能放下。后段回合可能依赖前文建立的文件、变量、日志、决策或执行结果；独立局部窗缺少这些历史，不能称为保留完整轨迹，也不能以单位覆盖率声称语义可独立成立。

用全部518条实测长度进行容量核算，情景为：连续、无重叠完整user/assistant边界，后窗重复原第一user题面，不携带早期历史或摘要；一个单位单独都装不下时整单位隔离。每条完整episode的模板token加和关系均已与真实整序列长度核对一致。这只是可复查的统计基准，不是已经实施的训练方案。

| 容量 | train整episode单窗容纳 | train窗数 | train总输入token | train单位覆盖 | train assistant内容覆盖 |
|---|---:|---:|---:|---:|---:|
| 16K | **0/427** | 2,642 | 37,421,652 | 21,209/21,211 | 99.755% |
| 32K | **13/427** | 1,313 | 35,350,845 | 21,211/21,211 | 100% |
| 64K | **203/427** | 721 | 34,419,666 | 21,211/21,211 | 100% |

对应val teacher traces：16K/32K/64K单窗完整0/1/42题（总91题），需要556/280/154窗，输入token约8.02M/7.59M/7.39M。32K/64K没有单位丢失仍有886/294个train后窗缺少更早源历史；16K有2,215个这样的后窗，另有2个单位无法容纳。统计总量含重复题面和模板，未含padding、packing或carry/overlap策略的额外开销，不能代替最终ms-swift预算。

16K无法容纳的完整单位保留在源文件中：`construct-an-incremental-full-text-search-product`第5单位，16,991 token；`audit-and-calibrate-a-stochastic-general-insurance-capital-model`第5单位，17,009 token。没有截断它们或自动写入训练数据。详细回执：`messages_v3/window_capacity_audit.json`、`window_capacity_per_task.jsonl`。

另核实[作者训练细节](https://arxiv.org/html/2610.13166v1#A1.SS1)：作者使用最大序列262,144、关闭packing、全参SFT 3 epochs。若项目采用较短回合窗，必须明确这是资源约束下的独立训练设计，不能称作复现其完整训练配方。root已决定先启动HLE方向，Terminal窗策略及原环境验收继续保留待决。

## 完整历史补选可行性：已扫描整个train候选池

按root要求，进一步扫描冻结val99以外的整个train候选池，**不修改v3或val99，不生成训练窗或新训练文件**。1,383个候选家族中2,162条native合格且最后完成的完整轨迹均已用真实Qwen模板/tokenizer测长；扫描固定80 CPU0–3、3个CPU worker加主进程，未使用CPU64及以上、GPU或模型API。现有相同source-row长度直接复用，其余全部实量。

1,309个家族有合格完整轨迹；**696个家族至少一条清后完整序列≤64K**。先看同一已选任务的另一条完整rollout：原v3已有203题≤64K，另可救24题，保留原任务身份最多 **227/427**。其余200个原任务无法只换同题rollout解决。

再看同类别备用任务供给，保持原v3各类数量，理论上最多补到 **380/427**（227个原任务＋最多153个同类新家族）；仍缺47个，不能称作把全部长轨迹无损替换。若同时要求每条assistant输出≤8K，最多 **374/427**。

| 类别 | v3数量 | 全train池合格≤64K家族 | 保持当前类数量的缺口 |
|---|---:|---:|---:|
| software-engineering | 146 | 136 | 10 |
| data-science | 20 | 7 | 13 |
| debugging | 4 | 3 | 1 |
| file-operations | 28 | 18 | 10 |
| model-training | 22 | 15 | 7 |
| games | 6 | 2 | 4 |
| personal-assistant | 6 | 5 | 1 |
| data-querying | 4 | 3 | 1 |

其余当前有train配额的类别都有充分同类短episode备用；原本train缺失的mathematics仍为0。若坚持最初500题的16类配额，完整≤64K的最大可填数同样为380，距500缺120。总池696个短家族并不意味着可保持目标类比例选出500。

**长度偏差不可忽略。** 以可用家族内最短合格完整rollout作供给长度参考，Terminal软件工程类供给P50约47.7K、27轮，对比v3约67.6K、41轮；games仅2个短家族，P50约14.1K、11轮，对比v3约74.5K、46轮。保留粗任务类别仍可能降低任务深度、阶段数或难度；上述最短rollout统计不是已经选定的新训练分布，也不证明替换后等价。

可追溯证据：`complete_history_64k_audit/trace_length_census.jsonl`、`task_supply.jsonl`、`summary.json`，包含每家族可用完整row、类别、原专业域、长度和>8K输出情况。所有扫描轨迹也通过严格JSON与残留think-tag检查，无额外因此剔除。质量仍是作者过程筛选＋本地协议＋完成代理，不是独立grader通过。实际64K GPU训练是否可行继续由训练栈实测决定。

## 首夜最终交接（北京时间2026-10-16 13:22）

按root要求停止追加下载、API与扫描；没有取消其他工作流或有益现有进程。下面依据已有完成回执收口，不以旧全局进度文件代替逐文件证据。

- **数据划分和结构交付**：固定task-level val为99题；最新v3训练427个独立任务，SHA `dbe05f654a20e7d6beacba334f9ee18d106cad788fe3290838ef2857660b8f71`；val教师轨迹91条只支持trace loss。val99清单SHA `15b14f3a2fe424ce908f226a97c25b89c0972bb6c2920ffef59316f523359144`。后续完整历史供给统计没有改动这些冻结文件。
- **完整历史方案实际供给**：整个train候选池的2,162条合格完整轨迹已量完；696家族至少一条≤64K。只换同题rollout可保留227/427原任务；再换同类新家族最多380/427，缺47；加每次输出≤8K后最多374。对粗类别、长度、轮数及原专业域的偏差已有逐类回执，未据此生成新训练集或任何训练窗。
- **原环境实物**：逐文件LFS回执实际为 **7/8片**，源任务inventory为 **1,342个**；原val99中 **88个完整原任务包已解出**，11个Compose，零解包错误。已取得的88个原配置均8CPU、16GB、5小时agent上限；上限不是实测运行耗时。全部未配置预构建image。**运行环境、reference、grader验收数仍为0，不能称可执行val已ready。**
- **下载失败与恢复点**：全局`environments/downloads_summary.json`因末片异常停留6，但`download_receipts/`已有7个完整核验回执，后者是本次实际计数依据。仅剩`tasks-00007-of-00008.tar.gz`，应为864,087,916字节，LFS SHA `446ec922496dffec7b7c7332fa458ed52f080068da8a148c63364180c7e36fcf`；最后观察`.part`为0。HF和镜像经Mac/80代理均出现TLS EOF，证据不是许可或404。后台下载PID3180547已在网络异常后退出；不继续自动重试。
- **费用和资源**：本分支分类64次请求、1,535任务，总费用保守上界 **¥4.269956544**（峰值USD价格×8，不是账单），之后无新增付费调用。GPU／正式benchmark／正式训练／原任务代码执行均为0；全池长度扫描只用80 CPU0–3。

以后恢复时，先恢复网络，再由root明确启动以下既有流程；本次交接没有执行它们：

```bash
cd /data/caoqinlu/projects/apex-takehome
taskset -c 0-3 artifacts/envs/hle/bin/python scripts/download_terminal_horizon_environments.py /data/caoqinlu/projects/apex-takehome
taskset -c 0-3 artifacts/envs/hle/bin/python scripts/inspect_terminal_horizon_environments.py /data/caoqinlu/projects/apex-takehome
```

这会复核已有LFS文件、只补剩余部分，再更新原val包inventory；仍不会自动构建Dockerfile、运行reference或执行grader。原包在`val_native_tasks/`，状态在`val_environment_manifest.jsonl`／`val_environment_summary.json`。下一项需要决定的是完整历史训练策略与64K实际GPU可行性，以及Dockerfile构建、Compose和权限的原环境支持；这些都在报告中保留为未决，不伪装成已解决。
