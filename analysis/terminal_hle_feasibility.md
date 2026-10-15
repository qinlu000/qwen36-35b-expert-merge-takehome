# Terminal-Bench 2.0 / HLE 可行性核验

核验日期：2026-10-15。约束：总窗口 71 小时，预留 12 小时，实际执行窗口 59 小时；最多 4 张 H100。本记录只核验官方元数据、文档及通用评测实现，没有运行 benchmark、读取参考答案或隐藏测试、下载大型数据，也没有验证服务器上的实际吞吐。

## 结论

- Terminal-Bench 2.0 官方注册表固定了 **89 个任务**，五次全量为 **445 个 trial / 模型**。只做 Base、负责 Terminal 的一个专家、最终合版模型，也至少需要 **1,335 个 trial**。题面要求的 3 小时是每个 trial 的 agent 时间上限；它不是整个评测作业的总时限。正式配置必须明确覆盖旧任务自身较短的 agent timeout。来源：[官方注册表快照](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)、[任务配置定义](https://docs.harborframework.com/tasks/configuration)。
- CPU 沙箱并发、镜像兼容性和推理吞吐共同决定能否赶上截止时间；**4 张 H100 本身不能证明四项评测能按时完成**。32 CPU / 48 GB 应按每个任务环境核算；Harbor 的并发单位是 trial，每个 trial 具有自己的隔离环境及资源配置。来源：[运行作业](https://docs.harborframework.com/jobs/run-a-job)、[沙箱与并发](https://docs.harborframework.com/sandboxes/pre-integrated-sandboxes)、[environment 资源定义](https://docs.harborframework.com/tasks/configuration)。32 CPU / 48 GB / 3 小时的具体数值来自题面，本记录没有独立核验模型卡上的同一组数值。
- **缺少 Docker 不自动意味着不可运行**：当前官方 Harbor 已有面向 HPC 的 Singularity 后端，直接把公开 Docker registry 镜像拉成 SIF；仍须实际验证 `fakeroot`、可写临时层、命名空间、镜像网络访问与任务兼容性。来源：[官方后端实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)。
- HLE 官方 `cais/hle` 是 **2,500 题、test split、单一 default config**，没有独立官方 text-only split。可以从冻结版本按 `image` 为空筛出所有纯文本题并保存 ID，但必须明确标成该版本的 text-only 子集，不能把其准确率称为完整多模态 HLE 准确率。当前公开元数据还标记 `gated: auto`，实际访问需要账号接受条件。来源：[HF 元数据 API](https://huggingface.co/api/datasets/cais/hle)、[官方数据卡](https://huggingface.co/datasets/cais/hle)、[官方预测脚本的图像处理](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)。
- 官方 HLE 简单评测依赖外部 judge，默认是 `o3-mini-2025-01-31`，每个有效回答进行一次结构化判分调用。需确认可用 judge 凭证、模型可用性、额度、速率限制及费用；这些目前都未验证。来源：[官方 judge 实现](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)。

## 应冻结的版本

| 对象 | 已核实快照 | 使用注意 |
| --- | --- | --- |
| Terminal-Bench 2.0 数据 | 官方 registry 的 `name=terminal-bench, version=2.0`；89 个 task；任务仓库 commit `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c` | 该 commit 来自注册表，不能用当前 `main` 替代；后者在本次查询时为 `2fd12b88aafdd04a52c298e3940bcb189f9766d6`。 |
| Harbor 通用代码/注册表 | `f527f8e447038fd242d08ecfa8aaa8029100da97` | 此快照的 pyproject 版本为 `0.24.0`，要求 Python `>=3.12`。它是本次检查快照，不代表已验证为本项目最后选定的可运行版本。 |
| HLE 数据 | `cais/hle@5a81a4c7271a2a2a312b9a690f0c2fde837e4c29` | HF 元数据 `test=2500`，default config；需冻结数据 revision、过滤规则和 ID 清单。 |
| HLE 评测代码 | `centerforaisafety/hle@22ed3074b1e7b134bcbc09028d0ba320839b0655` | 代码没有命令行 dataset revision 参数；使用时需做最小且披露的 revision 注入，不能直接随 `main` 漂移。 |

来源：[Harbor registry](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)、[TB 仓库当前 commit API](https://api.github.com/repos/harbor-framework/terminal-bench-2/commits/main)、[Harbor pyproject](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/pyproject.toml)、[HLE 数据元数据](https://huggingface.co/api/datasets/cais/hle)、[HLE 评测 commit](https://github.com/centerforaisafety/hle/commit/22ed3074b1e7b134bcbc09028d0ba320839b0655)。

版本警示：Terminal-Bench 官方网站目前默认展示更新的 4.0，而 2.0 仍在官方 benchmarks 页面单独列出。不能运行网站当前默认命令后将结果标成 2.0。HLE 官网另有 HLE-Rolling 与 HLE-Diamond；本题的普通 HLE 不应自行换成这些版本。来源：[TB 版本列表](https://www.tbench.ai/benchmarks)、[TB 当前运行页](https://www.tbench.ai/run)、[HLE 官方站点](https://lastexam.ai/)。

## Harbor / Terminus-2 与 HPC

官方 TB 2.0 README 明确使用 Harbor，支持 `--dataset terminal-bench@2.0 --agent terminus-2`；默认本地环境是 Docker，`--n-concurrent` 控制同时运行的 trial。Harbor 的 job config 同时具有 `n_attempts` 和 `n_concurrent_trials`，可表达五次尝试和沙箱并发。**五个 attempt 不自动等价于题面要求的五组显式固定种子**，还需记录种子如何传给采样 endpoint。来源：[TB 2.0 README](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/README.md)、[Harbor 作业配置说明](https://docs.harborframework.com/jobs/run-a-job)。

Terminus-2 当前实现可显式传 `temperature`、`api_base`、`llm_kwargs`，并使用 LiteLLM backend；默认 temperature 为 `None`，表示后端默认值。因此题面 temperature=1.0 等采样要求必须显式配置并保存实际请求，不能依赖默认值。`top_p`、`top_k`、80K 生成预算、256K context、thinking 与 preserve_thinking 的完整透传链路尚未在本次只读检查中验证。来源：[Terminus-2 实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py)。

官方 Singularity 后端的重要条件如下：

1. 任务需要 `task.toml [environment].docker_image`；后端执行 `singularity pull ... docker://<image>`，或接受已有 `.sif` 路径，不需要本地 Docker daemon。抽查注册表冻结版本的 `adaptive-rejection-sampler/task.toml` 配有预构建镜像 `alexgshaw/adaptive-rejection-sampler:20251031`。没有在本次检查中证明 89 个任务的所有镜像均可访问、均兼容 Singularity。来源：[Singularity 后端](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)、[抽查的任务元数据](https://github.com/harbor-framework/terminal-bench-2/blob/69671fbaac6d67a7ef0dfec016cc38a64ef7a77c/adaptive-rejection-sampler/task.toml)。
2. 后端运行使用 `singularity exec --writable-tmpfs --fakeroot --containall --pid`，并在容器内启动服务；HPC 管理策略是否允许这些参数尚未验证。来源：[同一后端实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)。
3. 实现注释明确 CPU / 内存资源应由 SLURM 的 `--mem`、`--cpus-per-task` 约束；后端声明的 resource capabilities 全为默认 False，另有进程树内存 watchdog。不能把 job 的总资源直接当作每个并发 trial 的独立上限。来源：[后端资源实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)、[capabilities 定义](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/capabilities.py)。
4. 该后端只返回 `EnvironmentCapabilities(mounted=True)`，未声明 Docker Compose、GPU 分配、网络隔离等能力。需针对冻结任务配置做兼容性检查；如任务不兼容，应使用可满足官方配置的受支持后端。没有已获证据支持默认修改官方 harness 或改任务。来源：[后端 capabilities](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)、[支持的后端列表](https://docs.harborframework.com/sandboxes/pre-integrated-sandboxes)。

Harbor 的通用 verifier 入口是在 agent 运行后才注入并执行的 `tests/test.sh`，写出 reward；框架允许程序化或 LLM 判分。本次没有读取 89 项任务隐藏测试，因此**不声称所有 TB 任务均无外部 API / judge 依赖**；需要通过官方元数据、运行依赖与实际 harness 错误日志确认。来源：[官方 verifier 文档](https://docs.harborframework.com/tasks/verifier)。

## TB 2.0 的时间与 CPU 预算

以下为算术估计，**不是吞吐实测或完成承诺**。假定仅有 Base、一个 Terminal 专家、最终合版三个评测对象，共 `89 × 5 × 3 = 1,335` trials；每个 trial 请求 32 CPU / 48 GB；平均 trial 时长相同，暂不计镜像拉取、排队、verifier、重试与模型切换。设有效并发为 C，平均时间为 t 小时，理想时间约为 `1335 × t / C`。

| 有效 trial 并发 C | CPU / RAM 容量 | 平均每 trial 30 分钟 | 平均 60 分钟 | 全部用满 3 小时 |
| --- | --- | ---: | ---: | ---: |
| 8 | 256 CPU / 384 GB | 83.4 h | 166.9 h | 500.6 h |
| 16 | 512 CPU / 768 GB | 41.7 h | 83.4 h | 250.3 h |
| 32 | 1,024 CPU / 1,536 GB | 20.9 h | 41.7 h | 125.2 h |
| 64 | 2,048 CPU / 3,072 GB | 10.4 h | 20.9 h | 62.6 h |

这些是理想连续调度值；真实整波调度、模型先后训练以及上述开销只会增加完成时间。如果只允许共 32 CPU / 48 GB，总容量仅相当于严格资源保障下的 C=1；如果 CPU 可超卖，该差异必须披露且不能声称每 trial 保证 32 CPU。最坏 agent 时间总量为 `4005 environment-hours`；按满额请求核算为 `128160 CPU-hours`、`192240 GB-hours`，实际金额需乘真实资源单价。GPU 推理是另一条资源链：context/KV cache、批处理、长回答吞吐都可能让有效 C 低于沙箱并发。

3 小时为 agent 上限时，verifier、环境构建和调度可使总 trial 时间超过 3 小时，所以上表最后一列也不是端到端严格上界。HPC 队列最大 walltime、可分配 CPU / RAM、实际节点数量、镜像存储、网络与模型推理吞吐均待核实。不得为了赶时间压缩题面固定超时、上下文或五次运行数。

## HLE 协议和成本

官方预测脚本支持图像 URL；纯文本模型不具备原生完整多模态评测能力。若采用 text-only，应固定过滤规则 `image` 为空，并把所有满足条件的题纳入评测；纯文本题的确切数量本次未读取受限数据核验。官方主页也明确把非多模态模型的 text-only 成绩单独标注。来源：[预测脚本](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)、[HLE 官方站点](https://lastexam.ai/)。

官方 README 称 temperature 默认 0，建议推理模型不要将 max completion tokens 设在 8192 以下；但所核代码中实际 API 调用的 temperature 行被注释，因此复现时要显式锁定并披露修正。模型调用为 OpenAI 兼容接口，timeout=600s、max_retries=1；通过 `num_workers` 控制请求并发并缓存已完成回答。该脚本不自动为本地模型开放工具或浏览环境。来源：[官方 README](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/README.md)、[预测实现](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)。

judge 脚本把问题、标准答案和模型回答发给指定 judge，由结构化输出抽取最终答案、判断 yes/no 并提取 confidence；默认 judge=`o3-mini-2025-01-31`、max_completion_tokens=4096、timeout=300s、max_retries=1、num_workers=100。主准确率分母为完整题目总数；缺失 judge 结果会提示重跑，不能只以已成功请求为分母。来源：[judge 实现](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)。

以完整 2,500 题和 Base / 一个 HLE 专家 / 合版三对象为例，需要 7,500 次生成及约 7,500 次有效 judge 调用。若生成上限为每题 8192 token，则生成 token 上限为 61.44M；judge 每题 4096 上限对应最多 30.72M 输出 token，实际常低于上限。输入费用受题目、参考答案及完整模型回答长度影响，重试会增加调用；本次没有访问账号余额、价格、judge 模型可用性或速率限制，不能给出可靠美元金额或运行小时数。text-only 情况应将 2,500 换成冻结 manifest 的实际题数。

数据卡要求不要公开重传 benchmark 数据；交付仓库应保存 revision、ID manifest、评分凭据与被许可的结果，而不是公开答案或完整评测数据。来源：[官方 HF 数据卡](https://huggingface.co/datasets/cais/hle)。

## 开始正式训练前必须补齐的证据

- 冻结 TB 2.0 的 89 task ID 与镜像 tag/digest；确认选定 Harbor commit 与依赖可在实际 HPC Python 环境运行。
- 用不含 benchmark 答案的无害示例验证 Singularity backend 的 fakeroot、可写层、tmux、请求端点与资源限制；不能据“存在 singularity 命令”直接判定全套任务可运行。
- 确认可同时使用的 CPU / RAM / 节点数、Slurm 排队与 walltime，以及是否允许额外受支持沙箱资源；本次未租用任何资源。
- 确认 HLE 数据访问、text-only 或多模态协议、固定 dataset revision、ID manifest、judge model revision 与 API 可用性。
- 保留五组显式种子和采样请求记录；明确 80K 是单次 completion 还是整任务预算，不能未经实现核验就把它作为整个任务的总 token 成本上限。

以上只是进入正式实验的证据条件，没有在本次核验中执行正式评测或选择 checkpoint。
