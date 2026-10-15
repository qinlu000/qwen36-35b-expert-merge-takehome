# SWE-bench Pro V2 HARD-51 正式评测协议审计

核验：2026-10-15。按 research 工作流核对固定官方 README、ID清单、task.toml白名单资源字段、通用agent/runner代码和PyPI包元数据。没有读取正式题面、参考patch、solution、hidden tests或逐题测试配置内容；没有安装/执行任务、模型API、GPU或Slurm。本文是冻结协议的依据，不等于环境已经验收或正式Base已经运行。

## 可以直接锁定的范围与主指标

| 项目 | 可锁值 | 依据 |
| --- | --- | --- |
| benchmark | SWE-bench Pro V2 HARD-51 | 官方v2.0.0，不用V1脚本/镜像 |
| 官方代码 | scaleapi/SWE-bench_Pro-os@66f92766bba642462d4bbe5479e83f91f9211862 | v2.0.0发布树 |
| HF对应范围 | ScaleAI/SWE-bench_Pro@2d52cb3df914a3fcf80c7f66738b3a88ae37fc50，config hard，split test | 完整51项；642为V2全集，非本题hard计数 |
| 完整ID | v2/hard51_ids.txt的51个唯一ID，保持原顺序 | SHA256 6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1，4,867B |
| 主指标 | fresh-sandbox replay后官方verifier的resolved rate，固定分母51 | 同时保留原作答运行得分与重评分得分；authoritative为后者 |
| 最少模型矩阵 | Base、仓库修复专家、最终合版各完整51项 | 题面目标专家至少完成目标项；其他专家全测属于额外预算 |
| 默认正式路线 | 官方locked协议，50分钟，不切成自行设定30分钟 | 50分钟来自所选官方协议，题面没单独写死；选用后固定用于全部模型 |

完整ID及来源revision/hash已保存 `analysis/source_snapshots/protocol/swe_hard_task_ids.json`。该文件只有来源、版本、hash与ID，不含题面或gold。应从固定ID物化完整hard目录；不可按task.toml中的difficulty另筛，也不能只下载/完成51项中的容易部分称全量。[官方范围及HARD-51](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#hard-51)、[固定ID](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/hard51_ids.txt)、[HF卡](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/blob/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50/README.md)

## locked资源、时间与评分边界

本轮按51个ID重新读取各自task.toml的agent/verifier/environment白名单字段，与先前资源扫描一致。51/51均为：

| 阶段/资源 | 固定配置 | 解释 |
| --- | --- | --- |
| agent | timeout_sec=3000，network_mode=no-network | 50分钟墙钟上限，可自然提前结束；禁止外网，仅放行模型端点 |
| verifier | timeout_sec=3000，network_mode=public | 额外的评分预算，不与agent共享50分钟 |
| environment build | build_timeout_sec=1800 | 构建/环境准备额外预算 |
| CPU/RAM/storage | 1 CPU / 4096MB / 10240MB | 不需要TB的32CPU/48GB；不擅自扩大后称原协议 |
| image | ghcr.io/scaleapi/swe-bench_pro-v2:<instance_id> | linux/amd64，官方公开tag；运行前还需固定每个manifest digest |

官方 `LockedMiniSwe.exec_as_agent()` 还会给真正的mini命令套GNU timeout：`budget=int(_timeout_sec or 3000)-60`，默认2940秒，超时后30秒强杀；它为结束与patch capture留余量，不是把正式任务预算另改成49分钟的自定义实验。外层Harbor仍按3000秒控制agent。安装、构建、verifier、fresh replay、基础设施重试均不应塞进“每题最多50分钟就全部完成”的承诺。[资源目录](https://github.com/scaleapi/SWE-bench_Pro-os/tree/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks)、[LockedMiniSwe](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py)

锁定评分链：原任务环境执行模型 → wrapper捕获 `agent/model.patch` → 丢弃被模型改动的环境 → 官方 `patch_replay:PatchReplayAgent` 在原始新镜像应用diff → 不修改的官方verifier评分。正式主表报告regrade；原始分数和二者差异也保存。缺失/空patch在replay阶段应用空改动，不得从分母删除。[locked协议](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)、[PatchReplayAgent](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/patch_replay.py)

题面要求同一benchmark内所有对象使用相同配置、完整任务和官方判定。50分钟、断网、fresh replay、1CPU/4GB来自选定官方版本及locked路线，不应说成题面逐字指定，也不因题面未写死就忽略官方协议。若另用30分钟，应明确标为自定义预算，不能继续声称完整复现此locked设置；当前默认建议保留50分钟，不为节约耗时另造这一偏离。

## agent、prompt与工具契约

选用官方 `v2/tooling/locked_mini_swe.py:LockedMiniSwe`，配置为官方 `v2/tooling/configs/mini_toolcall.yaml`。SWE题面没有唯一强制mini；这是本项目选择，后续所有模型必须一致。

2026-10-16补充层次说明：`LockedMiniSwe`继承Harbor的`MiniSweAgent`适配器，后者安装并启动实际mini-swe-agent包。mini负责模型→bash→观察的解题循环；LockedMiniSwe补Python3.12安装适配、内部timeout与结束后`model.patch`捕获，不是第二套解题算法。新环境重放由独立`PatchReplayAgent`和verifier完成，分阶段网络/资源由Harbor及backend负责。当前固定mini2.4.6与30min/64K8K见[v2](evaluation_protocol.md)，下文官方原预算审计不覆盖后续实验设置。

- system与instance prompt直接使用固定官方yaml，不新增基于正式失败结果的提示。任务内容是正式instruction.md，仅运行时送给模型，审计阶段未打开。
- 单一 `bash` 工具，参数 `command`；每次响应至少一次bash调用。模型可以读/改仓库、运行仓库已有测试和自己的复现程序。
- 每次action在新subshell，cd/环境变量不跨action自动持续；观察为returncode/output JSON。
- 观察长度达到10,000字符时只保留前5,000与后5,000字符及省略长度。保留原模板的实际分支条件，不擅自换截断策略。
- 结束动作是独立命令 `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`，不能和其他命令拼在一起；不是靠最后自然语言说“完成”判结束。
- 未添加MCP、WebFetch、WebSearch或额外工具。mini本身只有bash，但bash可以联网，因此仍必须有环境出网限制，不能只在prompt写“不要联网”。

这些是通用交互格式，不含任何正式题目答案。[固定配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[mini2.4.6源码包元数据](https://pypi.org/pypi/mini-swe-agent/2.4.6/json)

文件hash：mini_toolcall.yaml=`7275afa9920a6fb1b9ec66ab74cee44121db9b0276bb9fa90f5ec0597e523a45`；locked_mini_swe.py=`b6b187505067840338f3a825b96edc49ca4599b31e8388816e05d9a5e42885af`；patch_replay.py=`5c8b344de37164e9723f1724c2573013957fb644c3913a64c12c1718c737d876`。

## 版本：官方没有把mini精确版锁死

官方README要求 `harbor[modal]>=0.22`、Modal>=1.5.1；release gate记录Harbor0.22、Modal、50并发。它是可接受版本下界与该次发布验收记录，不是mini全依赖的精确lockfile。[运行方法](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#running)、[GATE](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/GATE.md)

本项目先前已审计的Harbor commit `f527f8e447038fd242d08ecfa8aaa8029100da97`，pyproject实际版本为**0.24.0**；不要将它写成0.22。该commit的Modal extra是 `modal>=1.5.4`。可以继续以此固定commit作为实现候选，符合官方>=0.22要求，并披露与gate精确软件版本不同；正式运行必须先验收wrapper/API/网络策略兼容。

官方wrapper install通过 `self._version` 拼 `mini-swe-agent==VERSION`，不传则拉当时最新版；另用managed Python3.12安装litellm/orjson/fastapi，后几项未锁精确版。不能留“latest”跨三模型变化。

本轮从官方PyPI元数据确认mini当前候选为**2.4.6**，wheel SHA256 `a35463c553ac825c7773b03cfa69cd44958e3af20155dcc5711fdf9e4c67cd54`；仅在内存读取wheel中的通用runner/model/environment源码，未安装。它不是SWE官方指定版本；建议在独立合成任务兼容验收后固定`version=2.4.6`及完整运行环境。若有其他已验收版本，优先沿用已验收固定版，不能为追新重开工具链。

来源：[固定Harbor包版本](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/pyproject.toml)、[MiniSweAgent](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/installed/mini_swe_agent.py)、[mini2.4.6元数据](https://pypi.org/pypi/mini-swe-agent/2.4.6/json)

## step、token、采样：必须区分yaml与实际生效值

| 字段 | 固定官方yaml/当前候选runner事实 | 正式记录要求 |
| --- | --- | --- |
| step_limit | yaml=0，mini解释为不设步数上限 | 不随意写成100/200步；以50分钟墙钟与模型上下文约束为主要限制 |
| cost_limit | yaml=3.0，但Harbor0.24 option默认cost_limit="0"，CLI传--cost-limit 0，覆盖yaml；mini0表示禁用 | 最终应显式锁cost_limit=0；不能把yaml的3美元当实际停止预算 |
| mode | yaml=confirm，但Harbor命令传--yolo、--exit-immediately覆盖为非交互运行 | 不需要人工逐命令确认；保持所有模型一致 |
| reasoning_effort | yaml=high，drop_params=true | 对本地Qwen不等价于已开启thinking，参数可能被LiteLLM丢弃；要锁实际模板/服务开关 |
| temperature/top_p/top_k | 官方这份yaml未设；mini model_kwargs默认也无这些项 | 需要按本实验模型服务明确设置并披露，不能冒称官方固定默认 |
| max_tokens/每轮输出 | 官方yaml未设；Harbor option默认None | 需固定实际服务输出上限，区分单轮输出与整题累计token |
| 整题累计token预算 | 未发现官方locked yaml中的显式总token上限 | 如新增，属于本实验预算，应预先固定、所有模型一致；不把累计输入重复计作上下文长度 |
| context/history | 未在官方yaml锁定context数值或历史压缩；观察截断已明确 | 需锁服务context上限和超长失败规则；不静默压缩或截断正式任务历史 |
| 单条bash命令timeout | mini2.4.6 LocalEnvironmentConfig默认30秒，官方yaml未覆写 | 这是该mini版本默认，不是agent整题30分钟；切版本要重新核对 |
| HTTP timeout | Harbor0.24给model.model_kwargs.timeout=3600 | 请求安全超时不替代50分钟agent上限 |
| seed/重复 | 官方SWE locked README/yaml未指定随机种子或强制5次 | 本实验固定一次/任务及预定seed（服务支持时），与TB五次不能混为一谈；不得挑最好一次 |

CLI覆盖顺序已在mini2.4.6通用runner中核对：文件/dotted config先合并，`--yolo`和`--cost-limit`等CLI选项再覆盖。上述实际值依赖固定Harbor0.24＋mini2.4.6组合；不能把版本未固定时的推断当成任何版本都相同。[Harbor runner](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/installed/mini_swe_agent.py)、[mini包](https://pypi.org/pypi/mini-swe-agent/2.4.6/json)

本地Qwen接入另有一处注意：Harbor0.24若传agent option `reasoning_effort`且model_name以`openai/`开头，会切mini model_class到litellm_response并走Responses API。单独保留官方yaml的model_kwargs.reasoning_effort并不触发这个option分支。若拟统一关闭thinking，应明确服务端`enable_thinking=false`、模板与preserve_thinking规则，并记录覆盖官方yaml的方式；不能只传`reasoning_effort=none`就宣称开关已生效。具体采样/token值应服从总协议统一冻结，本审计不猜一个未披露官方值。

## 出网、权限与backend验收

官方例子用Modal；setup和verifier保留网络，agent阶段no-network，仅模型endpoint加入allow-agent-host。只给API端点白名单，不放行GitHub/搜索/包索引/公共网页。先预装依赖与固定仓库代码；模型不能通过联网找参考修复。题面没有强制Modal品牌，但替换backend必须证明同样的分阶段网络、资源与fresh环境语义。

固定Harbor0.24的Docker后端有egress sidecar和phase network policy实现，可以作为本地候选；当前80无就绪Docker runtime，HPC Singularity路线也未验收这一安全边界。不能以“已下载任务包”或“linux namespace”替代locked运行环境。正式启动前用独立network/history probe确认出网被阻断、模型端点可达、git不含修复历史和额外refs；无需读取正式patch来做这些检查。[官方probe说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)、[固定Docker网络实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/docker.py)、[phase runner](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/trial/trial.py)

## 最少剩余冻结项

不需要再讨论SWE是否测完整51、是否换30分钟、是否省fresh replay：建议直接按上述完整locked协议固定。真正剩余只有三组：

1. **运行栈**：已审计Harbor0.24 commit、mini精确版（候选2.4.6）、LiteLLM/Modal或Docker后端依赖锁定；通过独立任务兼容验收。不得训练中或三模型之间更新latest。
2. **本地Qwen生成设置**：thinking/preserve_thinking、temperature/top_p/top_k、每轮输出与context、seed/一次运行；这些不是官方已披露统一值，应在总实验协议中给明确数值并存最终实际request配置。
3. **可运行backend与镜像digest**：网络分阶段隔离和endpoint白名单、CPU/RAM/storage落实、完整51镜像digest、fresh replay闭环及基础设施失败规则。受资源限制不能改完再仍标原协议。

基础设施错误可以按预先冻结的有限重试规则重跑同ID、同模型、同配置，但保留全部失败/重试和成本；未解决错误必须单列并保持完整分母。模型自身超时、错误补丁和无效输出不能挑种子重跑直至成功。官方GATE记录过基础设施错误重试，但没有提供本项目应照抄的统一最大重试数，因此该数由总协议明确冻结。


## 总协议给定的生成候选与实际透传验收

主线给定如下本实验候选；这不是官方mini内部默认或Qwen模型卡“refined harness”复现值：

| 参数 | 本实验候选设计值 | 写入位置/待验条件 |
| --- | --- | --- |
| thinking | false | 聊天服务强制 `chat_template_kwargs.enable_thinking=false`，并移除官方yaml中的reasoning_effort=high；不能仅依靠drop_params忽略 |
| preserve_thinking | 总协议统一冻结 | 关闭thinking仍记录该模板/历史设置，不自行猜测服务默认 |
| temperature | 0.7 | mini `model.model_kwargs.temperature`，最终请求必须可见 |
| top_p | 0.8 | mini `model.model_kwargs.top_p` |
| top_k | 20 | 对OpenAI-compatible/vLLM通常放 `model.model_kwargs.extra_body.top_k`；不可放未知顶层字段后被drop_params静默丢弃 |
| 单次max_tokens | 32768 | 可用Harbor `--ak max_tokens=32768`，最终是每次completion上限，不是每题累计上限 |
| context | 262144 | 模型服务总上下文上限，输入与此次输出共享；不是允许262144输入另加32768输出 |
| step_limit / cost_limit | 0 / 0 | 保留无限步和无价格硬上限，受官方墙钟3000秒限制；不新增整题累计token硬限 |
| seed | 尚需在总协议给出明确整数或预定映射 | 写 `model.model_kwargs.seed`；不能把Harbor n_attempts索引当作已传给采样器的seed |

固定mini2.4.6的LitellmModel `_query()` 把 `self.config.model_kwargs | kwargs` 直接传给 `litellm.completion(model=..., messages=..., tools=[BASH_TOOL], ...)`。因此源码支持配置temperature/top_p/seed/max_tokens与extra_body的传递路径；Harbor0.24的mini options没有独立temperature/top_p/top_k/seed字段，必须通过固定的配置文件送入。此处是可实现设计，不是已经验证实际wire request或vLLM取值。

必须用独立自造聊天/工具任务检查最终请求与服务生效值：仍走Chat Completions、enable_thinking=false确实生效、top_k/seed未丢失、32768输出上限和262144context落实，所有模型一致。`reasoning_effort` agent option保持None，避免openai/前缀自动切到Responses API。验收前不得把“yaml写了”说成实际端点已经支持；配置覆盖官方生成参数的差异要随报告保存。

## 重试与seed补查

重试有三个不同层级，不能把它们当作同一概念：

1. **独立作答次数**：固定Harbor0.24 `JobConfig.n_attempts=1`，即每题默认一次，不是pass@k；官方SWE README未要求TB式五次种子。建议正式固定一次，保留完整51结果。
2. **整任务基础设施重试**：`RetryConfig.max_retries=0`默认不自动重跑，`include_exceptions=None`；默认排除AgentTimeoutError、VerifierTimeoutError、RewardFileNotFound/Empty、VerifierOutputParseError、ApiUsageLimitError、AgentSafetyRefusalError、AgentAuthenticationError、ModelNotFoundError、UnsupportedModelParametersError。若把max_retries调高却不设include，范围会覆盖其余任意异常，不能称为只重试基础设施。建议总协议显式列允许的环境启动/连接临时异常及有限次数；模型超时/错误答案不重跑挑成功。官方GATE曾重跑环境错误，但未锁统一重试次数。
3. **同一次模型请求的传输重试**：mini2.4.6通用retry默认最多10次attempt（含初次），环境变量 `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT` 可覆写；退避4–60秒。UnsupportedParams/NotFound/PermissionDenied/ContextWindowExceeded/Authentication及KeyboardInterrupt直接中止。它是同一轨迹内的请求重试，消耗agent墙钟，不新增独立任务样本；LiteLLM/SDK若另有重试仍需随依赖锁定和日志记录，不能把10当作所有层合计。

Harbor0.24的mini runner未见自动把job attempt编号写入seed；mini模型则把显式model_kwargs.seed传给LiteLLM。要报告可复现随机种子，须在总协议给明确值并验收最终HTTP请求/服务采样器，而不是只在任务manifest写一个seed。即使传入seed，GPU后端并发/内核也不自动保证bitwise一致，报告保存请求配置和实际输出即可。

来源：[JobConfig/RetryConfig](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/models/job/config.py)、[Harbor CLI重试参数](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/cli/jobs.py)、[mini2.4.6 wheel，通用models/litellm_model.py与models/utils/retry.py](https://pypi.org/pypi/mini-swe-agent/2.4.6/json)。
