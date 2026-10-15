# Agent 上下文预算：可落地参数与实现边界

2026-10-16，只读核 `protocol_v1.json`、80 固定 Harbor 0.24.0/f527f8e、mini-swe-agent 2.4.6 和 vLLM 0.20.2 源码。未改配置、未运行任务/API/GPU。

**可实施方向：按 benchmark 分时运行同一 TP4 服务；TB 保留题定 262,144 context / 81,920 每次输出；SWE 可采用 131,072 context / 8,192 每次输出作为明确披露的实验预算，保留官方不限 steps 与 50 分钟外层期限。TB 现有 86,016 摘要阈值不构成上下文安全保证。**

| 项目 | 建议/明确含义 | 原生实现与限制 |
| --- | --- | --- |
| TP4 服务 | `tensor_parallel_size=4`；TB `max_model_len=262144`；SWE 分时改为 `131072`；`max_num_seqs=2` 起步 | seqs=2 限同时调度序列，不保证两个256K请求一定有足够KV或吞吐；排队请求仍需限制，避免耗尽agent墙钟。实际显存/并发待GPU验收。 |
| TB 正常动作请求 | `max_tokens=81920`，context=262144 | 单次实际渲染 prompt 必须 ≤180224 tokens，**输入+本次输出共享256K**；80K不是整题累计输出额度。 |
| TB 摘要 | 保留原生摘要时，86,016 仅作未验证候选，不能宣称防溢出；不因风险降低题定256K/80K | 原生三阶段没有单独的辅助输出限额，须额外明确失败政策或做薄适配；见下。 |
| SWE | 服务 `max_model_len=131072`、Harbor Mini `max_tokens=8192`；`step_limit=0`、外层3000s | 服务硬限含输出，所以实际 prompt≤122880。改变此前草案256K/32K预算，须在首次Base前冻结并对同项所有模型一致。 |
| SWE 累计/步骤 | 不新增100步；保留官方配置不限step，由50分钟与context约束 | mini的step是model query次数，不等于bash命令数。8K/32K都是每次completion上限，均不是整题累计额度。 |

vLLM 的 `TokenizeParams.max_input_tokens = max_total_tokens - max_output_tokens`，超限默认报错。不要设置 `truncate_prompt_tokens` 静默丢历史；注册模型元数据也不能替代服务的硬限。`max_num_batched_tokens` 是调度/预填充预算，不能误作每请求context；若将它设为小值，需要启用并验收 chunked prefill。[vLLM0.20.2请求参数](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/entrypoints/openai/chat_completion/protocol.py)、[长度验证](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/renderers/params.py)、[调度参数](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/config/scheduler.py)

## TB 的 86,016 到底是什么

Terminus2 通过 LiteLLM `token_counter(model, chat.messages)` 估计历史长度 H，计算 `free_tokens=C-H`；当 free_tokens **小于** threshold 时在下一主调用前摘要。`C=262144,T=86016` 意味着 **H>176128** 时触发，不是“上下文限86K”，也不是累计输出限制。默认原生 threshold 是8,000，本项目86,016是提前触发的实验设置。[计数/输出截取](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L649)、[触发实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1081)

其不保证安全有三个具体原因：

1. 计数只看历史，**不含待发送的下一条 prompt/观察**，而且不是固定 Qwen 模板实际计数。原生终端输出常规截为首尾合计10,000 **bytes** 加标记；确认/解析反馈等还有包装，不能按“2.5K tokens固定观察”推断。
2. `_run_subagent` 对 summary、questions、answers 三次调用均传同一个 `llm_call_kwargs`，因此若主调用设置81,920，辅助调用也继承它。answers 输入还追加 summary response 和 questions。推导：极端情况下需 `H + 3×81920 + 包装 ≤262144`，仅调threshold不能保证该式。即使把threshold增至98,304，只多留16K余量，仍非三阶段安全证明。[辅助调用与三阶段](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L785)
3. proactive摘要失败会记录错误并继续；reactive溢出先 `_unwind_messages_to_free_tokens(...,4000)`，这个4,000空余不是81,920的生成预留。完整摘要失败后的短摘要/最终fallback，可能仍被原历史+输出预算挤出。原生存在恢复代码，不能据此承诺所有长度都能恢复。[超限恢复](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1117)

**可实施的两种选择应在正式Base前择一冻结：**

- **完全复用原生、实现最少**：主请求仍256K/80K，选择 `enable_summarize=false`，达到真实context上限即保留轨迹/工件并作为受测agent的预算失败结束。原生将 context exception 抛出而不做相同请求重试。关闭摘要是不同于现有草案/原生默认的实验设置，可能降低长程任务表现；不是“精确复现模型卡内部配置”。也可保留原生best-effort摘要，但必须接受并记录其超限失败，不宣称强保证。
- **希望摘要更可控**：在既有Terminus2上做薄适配，分别限制辅助summary/questions/answers，例如4096/1024/4096；每个主请求和辅助请求都以实际Qwen模板计数，含pending prompt/工具定义，保证 `P+O≤C`。主动作仍81,920，不能为通过长度验证悄悄降它；辅助请求超限时显式、确定性地缩减其摘要输入或终止，且记录。原生没有独立 `summary_max_tokens` 配置项，不能只写一个不存在的参数。可用98,304作为提前触发的候选余量，但安全来自逐请求校验与明确缩减规则，**不是该阈值本身**。这些辅助预算/历史规则也须披露并统一给所有模型。

后一选择不需要重写agent/planner，但确实超出了“只填原生配置”。本报告未替用户选择，也未实现该适配；若保持86,016原生路线，至少先用独立合成长历史验证主调用、三阶段与fallback，再开始正式Base。不存在通过降低并发就自动修好请求token算术的办法。

## SWE 的128K/8K怎样真正生效

mini2.4.6的 `DefaultAgent` 只原生检查 step/cost/wall-time；`LitellmModel` 保留消息历史并把 `model_kwargs` 传给 completion，没有原生history压缩或逐请求context硬限。ContextWindowExceededError列为不重试的abort exception。**共享服务仍262K时，仅给mini registry填128K不能证明硬限128K。** 最省代码的落实是按benchmark分时以131072重启同权重服务；若坚持共享262K服务，需另外在请求入口做真实token计数/拒绝的薄guard，不能用静默历史截断替代。[mini agent](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/agents/default.py)、[mini model](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/models/litellm_model.py)

Harbor Mini 的原生 `--ak max_tokens=8192` 会写入 `model.model_kwargs.max_tokens`；其他生成字段通过派生官方YAML传递，system/instance/observation模板保持固定。它没有独立step_limit option；若将来需要限制步骤，应改派生YAML的agent.step_limit，不能照其他agent的参数猜。本轮建议仍用官方0。[Harbor Mini options/启动](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/installed/mini_swe_agent.py#L475)

官方 `mini_toolcall.yaml` 的观察截断是输出长度10,000 **字符**，头尾各5,000并JSON转义；每轮可以有多条bash调用/观察，所以不是每轮固定10K tokens。保留这个官方规则，不另造“累计观察10K”限制。官方 step_limit=0；外层3000s，locked wrapper 内2940s+30s kill宽限。131072context、8192输出是本实验追加的统一生成预算，需要明确披露；50分钟和官方prompt/tool/观察契约保留。[官方mini配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[locked wrapper](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py)

最终验收需覆盖真实HTTP参数、Qwen渲染后长度、两并发长历史、超限保存/判分规则及任务墙钟；不要把配置存在、CPU源码检查或单个token算例称为GPU容量和正式评测已就绪。服务并发与每项请求预算、helper调用均应在各模型间保持一致并保存版本/hash。
