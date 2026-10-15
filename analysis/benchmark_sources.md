# SWE-bench Pro v2-hard 与 ASI-Bench 官方来源核验

核验日期：2026-10-15（Asia/Shanghai）。本次仅核验官方 README、版本元数据、任务 ID 清单、配置和评测入口；没有运行评测、训练或下载大型数据。以下是来源核验，协议尚未最终冻结，尚不能代表环境已跑通，也不替代训练前最终保存的配置和完整任务 manifest。

## 结论

| 项目 | 公开来源与范围 | 本次发现的执行条件 |
| --- | --- | --- |
| SWE-bench Pro v2-hard | 官方 V2 的 `hard` 配置、`test` split，共 51 项任务，即 HARD-51；完整 V2 为 642 项，二者不能混报 | 指定的 hard 数据和评测工具已经公开。采用 V2 Harbor locked protocol，不能误用仓库保留的 V1 评测脚本 |
| ASI-Bench | 60 项目、11 学科，四种 B1–B4 条件，每个 seed 完整范围为 240 个任务与条件组合；公开 open split 为 seed31415，protected split 为 seed42 | seed31415 可公开本地完整评分；seed42 的参考材料不公开，正式评分依赖官方 Portal。必须在训练前固定 seed、层、运行协议、主指标和聚合方式 |

本题没有在 ASI-Bench 名称后指定 seed，因而可以选择官方 open split 并明确披露。若面试方另行要求 protected seed42，需要先确认 Portal 的账号权限和评分时效。当前证据不支持“指定 benchmark 不存在”或“SWE v2-hard 不公开”的说法。[SWE V2 官方说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)、[ASI 官方评分说明](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)

## SWE-bench Pro v2-hard

### 版本与任务范围

- 官方代码仓库为 `scaleapi/SWE-bench_Pro-os`。本次 `main` 与发布 tag `v2.0.0` 均指向 `66f92766bba642462d4bbe5479e83f91f9211862`，提交日期 `2026-09-22T21:00:20Z`。[提交元数据列表](https://api.github.com/repos/scaleapi/SWE-bench_Pro-os/commits?sha=main&per_page=1)、[发布标签](https://github.com/scaleapi/SWE-bench_Pro-os/tree/v2.0.0)
- 官方 HF 数据集为 `ScaleAI/SWE-bench_Pro`，核验 revision 为 `2d52cb3df914a3fcf80c7f66738b3a88ae37fc50`，最后修改时间 `2026-09-22T18:44:38Z`；API 表示 `private=false`、`gated=false`。`default/test` 是 V2 的 642 项；`hard/test` 是 51 项；`v1/test` 是旧版 731 项。本次只读取字段结构和行数，没有读取 Parquet 的题目、答案或补丁字段。[HF 元数据 API](https://huggingface.co/api/datasets/ScaleAI/SWE-bench_Pro)、[固定 revision 的数据卡](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/blob/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50/README.md)
- GitHub 的 `v2/hard51_ids.txt` 实数为 51 个 ID；文件 Git blob 为 `270aacf1f3641b2b0084e633e6508968423bd3ec`，文件长度 4,867 bytes，SHA-256 为 `6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1`。该清单可作为完整 hard 任务范围的依据。[固定版本 ID 清单](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/hard51_ids.txt)
- HARD-51 的官方划分依据是：在锁定协议下，被五个模型家族中至少两个失败的任务，排除后续发现存在歧义的三个任务。应使用该 ID 清单，而非按单个 `task.toml` 的 `metadata.difficulty` 字符串重新筛选。[HARD-51 说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#hard-51)

### 官方评测协议与入口

- V2 数据是 Harbor task 目录。官方建议 `harbor[modal]>=0.22`，Modal 至少 `1.5.1`，以支持分阶段网络策略；V2 release gate 使用 Harbor 0.22、Modal、50 并发。此处版本下界不是完整依赖锁，正式实验还需固定 Harbor 与 agent 的确切版本/commit。[运行说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#running)、[发布验证记录](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/GATE.md)
- Agent 阶段断网，仅允许模型端点；setup/verifier 阶段保留所需网络。各任务的 agent 时间上限为 50 分钟。执行后保存模型 diff，并在全新镜像中用 `patch_replay:PatchReplayAgent` 重新评分；官方要求报告重新评分后的 authoritative score，并公开两个分数。[locked protocol](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)
- 官方提供 `locked_mini_swe:LockedMiniSwe`，可指向 OpenAI-compatible endpoint，适合后续连接本地模型推理服务。主指标按官方 verifier 的任务解决情况计算 resolved rate。HARD-51 可按 ID 过滤，或用官方 `make_subset.py` 将全量 hard 清单物化为独立目录；这仍然是完整 hard 评测，不是自行抽样。[V2 工具与运行命令](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#running)、[mini agent 公共配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)
- 根目录 `swe_bench_pro_eval.py`、`run_scripts/`、`dockerfiles/`、Docker Hub `jefzda/sweap-images` 属于 V1 管线，官方明确说它们不用于 V2。[V1/V2 区别](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-v1-pipeline)

### 资源与可获得性边界

- 官方声称所有 V2 镜像均在 `ghcr.io/scaleapi/swe-bench_pro-v2:<instance_id>` 匿名公开，架构为 `linux/amd64`；发布验证记录称 642 个 manifest 均通过验证。本次没有拉取镜像，所以尚未验证目标执行主机的 registry 网络、缓存、磁盘或启动耗时。[镜像说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)、[发布验证记录](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/GATE.md)
- 核查的一个 HARD-51 样例配置声明：agent/verifier 各 `3000s`，镜像构建上限 `1800s`，环境 `1 CPU / 4096 MB RAM / 10240 MB storage`。这是一个样例，不应未经扫描推广为所有任务的统一资源需求。[该任务的公开资源配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e/task.toml)
- 按 51 项 × 50 分钟，单个模型的 agent 超时总和为 42.5 sandbox-hours；这只是预算上界计算，尚不包括 setup、verifier、重新评分和重试，也不是实测耗时。并发 CPU sandbox 与 GPU 推理服务需分别安排。

**是否需要联系面试方：**就来源可获取性而言，当前无需因为“找不到 V2-hard”联系面试方。实施时把 `v2.0.0/HARD-51`、`hard/test`、上述两项 revision 和 ID 清单明确写入实验配置；若面试方通知所指版本与此不同，再据明确差异确认。

## ASI-Bench

### 代码、数据与任务范围

- 官方仓库 `apexin-ai/ASI-Bench` 公开，Apache-2.0，默认分支 `main`；核验 commit `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`，提交日期 `2026-10-14T11:12:33Z`，Python 包版本 `0.2.0`。[仓库元数据](https://api.github.com/repos/apexin-ai/ASI-Bench)、[固定代码版本](https://github.com/apexin-ai/ASI-Bench/tree/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc)、[包配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/pyproject.toml)
- 官方范围为 60 项目、11 学科、B1–B4 四种指导条件；每 seed 完整范围是 240 个项目与条件组合。源码还含五个 opt-in sample，不能把目录数量 65 当成正式评测任务数。官方使用 open/protected evaluation split 的术语，没有常规 train/validation/test 三分法。[README](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md)、[评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)
- **seed31415/open**：HF `Apexintelligence-AI/ASI-Bench-seed31415`，revision `0fa14219cafdbab634d8b3cfbce238a8735a214f`，最后修改 `2026-10-07T15:53:54Z`；公开、无门禁。文件索引核验 60 个实例、每层 60 个根级 prompt，参考文件公开但本次未打开。其 metadata 标注两个任务的 seed override 为 2，并说明“59 final tasks plus one requested test task”；最终 manifest 应保留这些原始状态信息，不能假定每个实例内部均使用 31415。[HF 元数据](https://huggingface.co/api/datasets/Apexintelligence-AI/ASI-Bench-seed31415)、[固定版本 metadata](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed31415/blob/0fa14219cafdbab634d8b3cfbce238a8735a214f/metadata.json)
- **seed42/protected**：HF `Apexintelligence-AI/ASI-Bench-seed42`，revision `4533397770a85ef79afe31e0361cbd9c42d5b50d`，最后修改 `2026-10-07T15:53:53Z`；公开、无门禁。文件索引核验 60 个实例、每层 60 个根级 prompt，无 `reference/` 文件，metadata 声明 `task_count=60`、`contains_answers=false`。题目公开不意味着本地拥有官方评分所需的私有材料。[HF 元数据](https://huggingface.co/api/datasets/Apexintelligence-AI/ASI-Bench-seed42)、[固定版本 metadata](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed42/blob/4533397770a85ef79afe31e0361cbd9c42d5b50d/metadata.json)

### 运行与评分入口

- 公开本地路径是 `asibench task pull --repo seed31415 --revision <HF_SHA>` → `asibench run --instances-dir …` → `asibench score --repo seed31415 --results-dir … --instances-dir … --tasks-dir <checkout>/tasks`。`run` 默认覆盖四层；`run-score` 可串联执行与本地评分。拉取实现支持 revision pin，应固定仓库代码与实例数据两个版本。[CLI 源码](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py)、[数据拉取实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/hf/pull.py)
- seed42 的本地 score 被官方 CLI 拒绝；正式评分须使用 Docker `--sandbox os`、兼容内置 adapter、`login`/`submit` 并在网站确认。评分依赖私有参考内容，因此本次未能从公开来源证明 Portal 的账号审批、吞吐和返回时限。[评分协议](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)、[CLI 源码](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py)
- 官方公开 CLI 默认运行 B1–B4 四层。Portal 文档要求每个 declared instance 完整，没有发现“所有提交都必须含完整 240 组合”的独立硬规则；这不代表本题允许将单层或任务子集称作全量。为覆盖题目所称完整 benchmark，后续应明确采用完整 60 项 × 四层，并保留各层分项。[CLI](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py)、[评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)

### 主指标与聚合口径

- 官方网站显示主列 `OVERALL / Mean score (0–100)`，同时显示 B1–B4；其 Scoring Methodology 表述为按 60 个任务做 macro average，除非另有注明，再对三个独立运行聚合。网站还明确当前 published aggregate snapshot 的 exact task-set version 未核实，因此不能直接拿该榜单分数当作固定 revision 的本地复现结果。[官方榜单及方法说明，2026-10-15 核验](https://asibench.apexin.ai/leaderboard)
- 当前公开 CLI 的 `asibench score --repo seed31415` 另写 `local_score_seed31415.json`，其汇总字段 `mean_percent` 的公式是 `100 * Σfinal_score / Σmax_score`，按各结果满分加权；只有满分一致时才等价于各结果百分数的均值。通用 `RunReport.overall_mean_score` 则是所有已评分 `result.final_score` 的算术均值，LeaderboardEntry 的 overall score 取后者；完整 60 项 × 四层各一次时是 240 个结果的均值，不能改为 11 学科等权。这些字段不是凭名称即可互换的统计量，最终主指标应与官方 macro mean 定义对齐，并保留 local score 的原始字段及分项用于复查。[本地评分汇总代码](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/local_scoring.py#L1067-L1089)、[通用聚合](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/reporting/aggregator.py#L91-L138)、[LeaderboardEntry](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/reporting/leaderboard.py#L44-L51)
- scorer 首先累加加权分数；hard gate 失败通常得到 0 分，但可配置 `gate_score_sum`。任务分数和满分同时除以 `score_divisor`（默认 1）。本地评分失败会记为 null 并从分子分母排除，因此不能只读取成功评分的均值就称为完整结果。完整评分应检查 `instance_count=240`、`scored_instance_count=240`、`scorer_error_count=0`；如仍有环境/评分失败，须按训练前固定的失败处理规则完整披露，不得静默剔除。[评分变换](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/scoring.py#L163-L207)、[Scorer 配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/scorer.py#L13-L50)、[本地错误与汇总](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/local_scoring.py#L1067-L1089)
- CLI 默认运行一次，而榜单方法描述通常为三个独立运行。若本实验使用一次运行，须明确写为本实验设置并报告不确定性，不能声称完全复现榜单协议；重复次数和跨任务、跨层、跨运行的聚合都需在训练前冻结。

### 依赖、资源与待固定项

- Python 至少 3.11；基础依赖包括 click、huggingface-hub、dotenv、PyYAML；`[full]` 另含 Pillow、LiteLLM、numpy/scipy/pandas/matplotlib、openai、taichi。具体任务有独立依赖，部分 scorer 需 LLM/VLM Judge API，除了四张 H100，还需预算 API、CPU sandbox、磁盘及依赖安装。[依赖配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/pyproject.toml)
- `linux_ns` 需要 Linux 和 user namespace；正式 seed42 使用 Docker。本次未找到已证实适用于全部任务的统一最低 GPU/RAM 指标，不应据此声称四张 H100 足以在指定时间完成。[沙箱支持代码](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/sandbox_support.py)
- CLI 默认超时 10,800 秒是每个 `(task, prompt_level, attempt)` 的 agent 执行预算，不是四层共享；任务 metadata 不能覆盖传入的有效超时。默认并行数为 1、attempt 为 1（`retries=1`，没有额外重试）、`run-score` repetitions 为 1。按此计算，单模型完整 240 组合最多需要 720 agent-task-hours，一次重复再增加一整套；这不包括镜像、环境、scorer 和排队，也不是实测耗时。[CLI 默认参数](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L1457-L1485)、[逐层实例的超时设置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/orchestrator.py#L596-L655)
- Docker OS 默认每容器为 4 CPU / 8 GiB RAM（CPU 数可按主机核数下调）；仅当任务 `difficulty.requires_gpu=true` 时传 `--gpus all`，不是自动为每任务分配一张卡。并行 GPU 任务必须规划设备可见性和资源隔离；推理服务、任务计算和 Judge API 的需求也需分别计入。[OS 默认资源](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L71-L108)、[GPU 开关](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L218-L230)、[GPU Docker 参数](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L875-L876)
- 训练前仍须在实验配置固定：open/protected、完整 60 项清单、四层范围、运行 adapter、工具与 token/时间预算、评分器及 Judge 版本、主指标、跨任务及跨层聚合方式。单个任务 raw 分数不能未经固定映射直接与其他 benchmark 的百分制准确率求平均。

### 对 59 小时 / 4 张 H100 工作窗口的判断

仅依据公开来源，不能保证完成，也没有证据证明一定无法完成。完成的必要执行条件包括：任务 sandbox 有足够 CPU/RAM/磁盘并发；GPU 任务与模型服务不会互相挤占全部四卡；Judge/API 可用且吞吐足够；实际任务大多在超时前完成；提前为安装、重试、评分和产物留出时间。以一个模型 720 agent-task-hours 的默认超时总和为例，若给 ASI 评测留 24 小时，需要约 30 路始终满载的有效 agent 并发才能覆盖这一上界，资源默认值对应 120 CPU / 240 GiB RAM；还未计任何额外开销。Base、合版和目标专家分别评测会增加模型运行套数。该计算用于暴露资源条件，不是建议购买资源或承诺时长。

protected seed42 需要 Portal 账户/PAT、网站确认 draft，并由维护者 best-effort 评分，没有已核实的 SLA；在截止时间约束下，不能将等待官方返回的时间视为已知常量。open seed31415 能消除私有参考材料的访问依赖，仍需实际测量执行吞吐后才能制定可靠排期。[官方提交审核与时限](https://asibench.apexin.ai/docs/submission/official-review/)、[认证说明](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md#L604-L609)

## 题面与模板 README 差异

题面提供的模板仓库目前 `main` 为 `994e2c329c5ce3f6beaff788f5df98d686442147`（`2026-10-02T04:03:29Z`）。其 README 仍描述 LoRA SFT→第二阶段优化、提交面试方分配的私有仓库，与用户粘贴的“多专家训练与合版、自建独立仓库”不一致。本项目应以用户提供的题面为需求依据，模板只用于参考目录和记录形式，不应静默切换研究路线。[固定版本模板 README](https://github.com/apexin-ai/qwen36-35b-takehome/blob/994e2c329c5ce3f6beaff788f5df98d686442147/README.md)、[模板提交元数据](https://api.github.com/repos/apexin-ai/qwen36-35b-takehome/commits?sha=main&per_page=1)

## 核验边界与记录

本次未验证模型能力、训练吞吐、任务实际耗时、Docker 镜像下载成功率或 Portal 服务可用性。所有完成性结论仅限于来源和协议可查，不将未运行的步骤称作已复现。

核验中一次 GitHub `/commits/main` 详情请求意外返回包含文件 diff 的大响应，输出被工具截断；该接口随后停用，改为提交列表、refs、README、ID 和白名单配置元数据。上述版本、任务数量和运行协议均已独立用安全范围来源交叉核验；该响应的任务内容不得用于训练数据、prompt、方法设计或 checkpoint 选择。
