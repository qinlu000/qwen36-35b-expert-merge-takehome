# Terminal-Bench 2.0 正式协议审计与推荐

更新：2026-10-15。按research工作流检查固定官方registry、Harbor框架源码和Qwen模型卡；未读取任务instruction、答案、solution或测试文件，未安装软件、执行任务、调用模型API或提交Slurm。本文件是可锁定的协议建议，不声称已跑通端点或复现Qwen原始成绩。

## 已确认的完整范围与来源

- 数据选择官方registry中唯一的name=terminal-bench/version=2.0条目；89项、89个唯一ID，所有name与path一致，全部指向同一任务commit `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`。registry原始git_url为 `https://github.com/laude-institute/terminal-bench-2.git`，保留来源原值，不用当前main替代。
- registry与Harbor代码固定 `f527f8e447038fd242d08ecfa8aaa8029100da97`，pyproject版本0.24.0、Python>=3.12；Terminus2.version()为2.0.0。该commit的uv.lock锁LiteLLM1.93.0、OpenAI2.24.0。框架与其依赖应共同固定。
- 已物化纯元数据清单 `analysis/source_snapshots/protocol/terminal_task_ids.json`。保留官方registry顺序与完整89个ID；没有任务正文、答案或测试。该版本以完整注册集评测，不另选子集。
- 一模型89×5=445次；本题最低Base、交互执行专家、最终合版共1335次。专家是否加测其他项不改变TB的最低完整范围。

证据：[固定registry](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)、[pyproject](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/pyproject.toml)、[依赖锁](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/uv.lock)、[Terminus版本与参数](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L470-L535)。

## 硬要求与建议锁值

题面直接要求Harbor/Terminus-2、3小时、32CPU/48GB、temperature=1、top_p=.95、top_k=20、max_tokens=80K、256K context、五次运行均值和标准差；这些同时出现在固定Qwen模型卡。其余参数的原始内部评测配置没有完整公开，因此以下默认/选择属于本实验设置，不能称完全复现模型卡成绩。

| 项目 | 推荐锁值与口径 |
|---|---|
| agent | terminus-2，LiteLLM backend，Chat Completions API |
| 完整任务 | 清单89项，task commit69671fba；每seed一遍 |
| agent执行时间 | agent.override_timeout_sec=10800；timeout_multiplier=1、agent_timeout_multiplier=1；不设更低max_timeout_sec |
| CPU / 内存 | environment.override_cpus=32；建议override_memory_mb=49152，明确采用48GiB单位约定。题面/model card写48GB而未给字节口径，此单位约定需披露 |
| 采样 | temperature=1.0、top_p=0.95、extra_body.top_k=20 |
| 单次生成上限 | max_tokens=81920，作用于每次Chat Completion；不另设trial累计80K上限 |
| context | 服务端262144总tokens；Harbor model_info.max_input_tokens=262144、max_output_tokens=81920 |
| prompt / parser | parser_name=json，固定terminus-json-plain.txt；固定timeout.txt；无额外skills/MCP/提示附加 |
| 工具 | 官方TmuxSession交互终端；JSON commands含keystrokes/duration，非原生OpenAI function calling |
| 最大轮数 | max_turns=None，沿用固定源码内部1000000的实际无约束默认；不额外砍步数 |
| 累计tokens | 无新硬上限；记录所有主循环及summary调用的输入/输出/缓存量 |
| 压缩 | enable_summarize=true；建议显式proactive_summarization_threshold=86016（81920+4096），作为本实验设置，见下文兼容边界 |
| 五次随机组 | 本实验自选seed=[0,1,2,3,4]，所有模型相同；不是官方披露原始种子 |
| 并发 | 由独立开发任务负载测量后冻结；没有官方题面指定值，不以高并发超卖冒充充分资源 |
| verifier/build/setup | 保留固定任务及框架默认时限，不用3小时agent上限覆盖所有phase；verifier不能disable |

模型卡的文本API示例明确使用max_tokens=81920，服务启动示例显式262144；这支持80K=80×1024、256K=256×1024的落实方式。没有公开Qwen TB原始脚本能证明其全部内部选项。

证据：[固定Qwen模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)、[Terminus参数默认](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L83-L178)、[时间覆盖计算](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/trial/trial.py#L1538-L1560)、[环境覆盖字段](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/models/trial/config.py#L197-L215)。

## prompt、工具与完成判定

默认JSON prompt要求analysis、plan和commands；即使关闭模型thinking，prompt中的analysis/plan仍在，不能自行改成另一套纯命令agent。keystrokes直接写入持久tmux终端，duration是等待时间，不是模型工具执行CPU预算。任务连续两次task_complete=true后正常返回，故10800秒是agent phase上限而非每题必跑3小时；环境准备、setup、verifier及清理另计。

固定prompt SHA256：`89a3dc3a15752b748a99fb907c9251ab31a464e13386583fb48476b078b54a34`；timeout模板：`32bf9aa7b157a6a0e0ba0d33b81e59dd67204276f158afc1fe6cb684ced68872`。不需要把Terminus的文本命令协议换成qwen3_coder原生工具schema。

证据：[固定JSON prompt](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/templates/terminus-json-plain.txt)、[正常结束条件](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1650-L1668)、[agent wait_for](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/trial/trial.py#L583-L670)。

## 实际参数透传与80K含义

Terminus把temperature及llm_kwargs交给LiteLLM；每次主循环与summary都传llm_call_kwargs。推荐把top_p=.95、max_tokens=81920、seed=s放标准字段，top_k=20放llm_call_kwargs.extra_body，由OpenAI兼容客户端合入实际HTTP body。不要把非标准top_k当普通OpenAI参数，因Harbor固定设置drop_params=true，可能被兼容层过滤。选定vLLM0.27.1源码明确支持top_k、seed并传入SamplingParams；SGLang若被选用还需对相应固定版本做相同验收。

自部署模型名不能依赖LiteLLM未知模型默认：get_model_context_limit失败会回退1000000，故必须注册上述model_info。保持默认生成配置的采样字段显式可见；未公开的presence/min_p/repetition等应记录选定服务实际有效值，不能用模型卡通用推荐推断TB原始设置。

max_tokens在每次acompletion参数中生效；Chat只累计usage，没有达到trial累计81920便停止的逻辑。因此多轮和压缩调用的总输出可以超过81920，不能按每trial80K估算费用或耗时上界。

证据：[LLM构造/调用参数](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/lite_llm.py#L299-L370)、[drop_params](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/lite_llm.py#L643-L654)、[context/output解析](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/lite_llm.py#L150-L202)、[累计usage](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/chat.py#L85-L132)、[vLLM0.27.1协议](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/entrypoints/openai/chat_completion/protocol.py#L210-L283)、[vLLM采样落地](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/entrypoints/openai/chat_completion/protocol.py#L695-L719)。

## 86016提前压缩：可锁候选及不能保证的部分

源码判断为free_tokens=context_limit-token_counter(chat.messages)；若free_tokens<threshold则在下一主调用前触发。86016对应历史估计tokens>176128时压缩，确实比默认8000更早为81920输出预留空间。它不是trial累计预算。

但86016不能被宣称为严格安全证明：token_counter是LiteLLM计数，未计下一prompt且可能不完全匹配Qwen模板；压缩为summary、questions、answers三阶段，均继承同一81920生成上限。第三阶段会在原history上追加summary正文，正文可能超过4096余量。vLLM会检查prompt加请求输出是否超过262144，因此仍可能触发context error。Harbor有原生context异常压缩/短摘要/最终退化恢复，但这不等于消除该兼容风险。

建议先锁86016为本实验候选，并用独立长对话对主循环及三阶段摘要做端点验收；不靠截断官方任务prompt或砍累计tokens解决。若需改压缩参数/单次请求预算计算，应在正式评测前统一冻结并披露。单一可用参数值无法在完全不改请求路径的条件下，为任意81920长摘要保证三阶段都满足总上下文。

证据：[计数实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L649-L653)、[触发公式](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1081-L1107)、[摘要三阶段及同一调用kwargs](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L785-L1080)、[上下文恢复](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1117-L1213)、[vLLM长度校验](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/renderers/params.py#L337-L365)。

## 重试不是一个max_retries开关

- 完整trial/环境级：JobConfig.retry.max_retries默认0，可显式锁0；这不会禁用下面的API重试。保留失败记录，不能通过换种子、只保留成功重跑改变分母。
- Terminus主请求：_query_llm的tenacity为最多3个attempt（包含首次），context异常被排除于该常规重试；输出过长等另有恢复路径。
- LiteLLM.call内部：另一层最多3个attempt，指数等待4至15秒；context/output/auth异常有排除。普通异常可形成3×3嵌套调用，但特殊恢复分支和底层SDK行为使其不是所有请求的全局9次硬上界。
- verifier：VerifierConfig没有独立max_retries字段；_verify_with_timeout对verify做一次wait_for。不能写一个不存在的verifier.max_retries配置。任务内部测试脚本自身逻辑不在本次正文审查范围。
- LiteLLM/SDK的额外自动重试需随固定依赖与实际调用日志记录；不能用job层max_retries=0声称零API重试。保持官方固定源码行为，不为控制预算额外改native重试。

证据：[job重试默认及排除项](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/models/job/config.py#L292-L325)、[主循环重试](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1108-L1135)、[LiteLLM内部重试](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/lite_llm.py#L257-L275)、[VerifierConfig](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/models/trial/config.py#L327-L355)、[verifier调用](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/trial/trial.py#L853-L867)。

## 五次、统计及资源公平性

推荐五个独立job，每job n_attempts=1并指定seed=0/1/2/3/4。Harbor的n_attempts=5只是五次尝试，不会自动给模型设置五个不同采样种子；固定源码没有统一job seed字段。各模型使用同样五组，每组跑完89项，先算该组successes/89，再报五个成功率的均值与样本标准差ddof=1；ddof是本实验显式约定。不是best-of-five或pass@5。超时/模型失败不能删题；环境失败单列并披露重跑政策与原始记录。

Docker每容器32CPU是quota上限而非独占预留，48GiB也不等于实际RSS。共享争用仍可能改变有效资源和wall-time失败，不能仅保持quota数值便宣称复现等价。并发只能由实际资源和独立开发吞吐确定，同一模型组间保持冻结政策；不把80可见128逻辑CPU或HPC账户理论180CPU当已获保留。

证据：[job尝试与并发字段](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/models/job/config.py#L400-L443)、[Docker资源写入](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/__init__.py#L43-L60)、[Docker CPU语义](https://docs.docker.com/engine/containers/resource_constraints/#cpu)。

## 正式开跑前最少剩余事项

1. Root统一确认thinking/preserve_thinking；本文件不替代该选择。Harbor interleaved_thinking与Qwen服务chat_template_kwargs不是同一开关，须验收实际历史与请求。
2. 选定可满足资源的后端及实际配额，测并冻结并发；固化89项task.toml引用镜像的OCI digest。任务commit固定并不使浮动image tag内容自动固定。
3. 用独立任务验收真实HTTP body的top_k/max_tokens/seed及262144上下文、三阶段摘要兼容性；记录server版本和有效生成参数。验收通过后冻结86016或统一修订值。
4. 冻结以上实验自选值及异常处理政策。无需再讨论降低CPU/时间、增加max_turns或累计token硬限来冒充题定配置。

本轮仅新增本审计文档及纯ID元数据清单，不修改正式运行配置。
