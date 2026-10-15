# ASI／HLE：哪些harness代码能直接复用

更新：2026-10-16。只读固定通用源码，不读正式题、答案或隐藏scorer，不启动模型／任务，不安装或修改runtime。这里先比较可复用的生成／执行模式，不预设必须使用OpenCode。

## 结论

**可以复用现成harness，不必从零重写。ASI原生direct_llm就是与D3静态程序监督更接近的一条路线；它仍执行模型生成的科学程序，只是没有把执行反馈送回模型继续修改。** OpenCode则提供多轮探索与纠错，两者需要比较训练匹配、能力收益与剩余工程量。

题面没有写死ASI必须用OpenCode。只要正式前选定一条路线、保留同一固定60任务×四层输入和官方grader，并让Base／专家／合版采用同一配置，就可以比较。不能拿D3任务或D3 verifier替换ASI正式任务与评分，也不能看正式成绩后挑harness。

## 可复用代码清单

| 已公开代码 | 能复用什么 | 缺口／不能混称 |
| --- | --- | --- |
| D3 `workflow/engine/vllm_engine.py` | OpenAI-compatible Chat Completions客户端、静态生成、基本usage和传输重试 | 没有工具循环／执行反馈；默认采样不是本项目固定值；不是完整teacher采集launcher |
| D3 `training/convert_trajectories_to_alpaca.py` | instruction/thinking/response→静态程序SFT格式的参考实现 | 不是OpenCode轨迹转换器；自身不执行程序或重新验证成功 |
| D3 `workflow/execute_programs.py` | 任务构建时依赖准备、Conda执行和输出整理逻辑可参考 | 执行的是原始gold程序以构建任务，不是ASI被测模型runner，不能直接拿来运行正式ASI |
| D3 README的Docker入口 | `solution.py→pred_results→run_and_eval`任务环境契约 | 公开仓库没有完整镜像构建／entrypoint源码或逐条teacher采集launcher；不能凭README认定已完全还原 |
| ASI `DirectLLMAdapter` | 完整单次生成→提取代码→执行→产物收集→官方评分接入 | 生成参数／总deadline需补明确接线；没有自动看执行错误后再生成 |
| ASI `OpenCodeCLIAdapter` | 原生多轮文件／shell工具、日志、执行产物与评分接入 | 数据需覆盖工具行为；长历史、图文和参数仍需端点验收 |
| ASI `CLIAgentAdapter --agent-cmd` | 外部脚本按workspace交换输入输出，统一产物收集 | 固定版本只支持none/linux_ns，不直接支持Docker os；不能把它当已具备OS隔离 |

D3固定代码commit为`5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb`：[vLLM客户端](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/workflow/engine/vllm_engine.py)、[SFT转换](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/training/convert_trajectories_to_alpaca.py)、[任务构建执行](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/workflow/execute_programs.py)、[Docker使用契约](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)。

## ASI原生direct_llm具体做了什么

固定ASI commit `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc` 的CLI确有`--agent direct_llm`，不是需要我们新建的概念。其实际流程为：

1. 框架准备正式条件的prompt.md、agent-facing task_info.json和data/，adapter仅读prompt.md组成system/user消息。
2. 调一次`litellm.completion`，要求输出Python程序，没有传tools、没有模型工具交互循环。
3. 提取Python代码块，按语法／输出文件等启发式选择一个代码候选；这不是执行多个候选后挑最高分。写入任务声明的首个代码文件，未声明时回退simulation.py。
4. `_execute`按none/task/linux_ns/os调用现有执行路径；os复用`OSSandbox.execute_python`。因此生成的程序仍可读数据、调用科学库、做数值计算并生成表格／图像。
5. 返回AgentOutput，保存stdout/stderr、模型usage和调用记录，收集任务声明的产物；原正式scorer继续评分这些产物。执行失败不会再次调用模型修复。

这与D3“完整程序生成后执行验证”的模式近似，环境构建也可共用Python依赖／容器执行思路，不要求两个数据集拥有字节相同镜像。D3程序里的输入路径和输出约定属于D3任务；正式ASI仍使用自己的说明、数据和文件名，不能机械复制D3路径。

当前messages只包含文本prompt，没有图片附件，也没有read工具把图片反馈给模型。生成的程序仍可处理图像文件、产出图表，但模型没有OpenCode视觉工具观察；选择路线时需把这项能力差异和多轮纠错一并比较。

直接可复用的官方代码：[direct_llm.py](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py#L128)、[程序执行分支](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py#L477)、[AgentAdapter输入输出](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/agent_interface.py)、[产物收集](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/subprocess_base.py#L67)、[CLI注册](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L2559)。

### 仍需的轻量接线

- 现有构造器只接model/system_prompt/api_key/api_base/api_protocol；当前completion调用没有显式传temperature/top_p/top_k/max_tokens/seed。应在一个生成调用点增加固定generation kwargs，或由可审计端点统一强制，不能只填协议文档。
- `_execute`采用每条件执行超时，但生成请求未显式设置HTTP timeout，也没有把生成耗时从后续执行预算扣除。若总预算是30分钟，需要总deadline／剩余时间接线，不能把原生代码直接称为已落实全流程30分钟。
- 代码提取、程序输出路径、部分文件缺失、失败状态及usage需用独立合成任务验收。thinking／公开teacher推理的保存和最终程序提取也要统一。

这几项可以围绕官方adapter做小改动或薄adapter，不需要另造任务管理、科学环境、产物格式和评分器。若增加“执行后把stderr送回模型修一次”的self-debug，则是一个新的、需披露的轻量多轮harness；可以复用原生生成／执行／收集代码，但不能声称原生direct_llm已经包含该循环。

`--agent-cmd`可承载自有脚本，但固定generic adapter只支持none/linux_ns；若保留本项目os隔离路线，优先复用／扩展原生AgentAdapter和OSSandbox，不为用一条CLI命令而退化隔离。[generic adapter](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/cli_agent.py)

## 推荐怎么选

**最省工程的候选是先复用ASI原生direct_llm主干，而不是移植D3整套任务构建launcher。** 它与现成D3程序SFT目标更接近，且没有放弃程序执行与官方产物评分；代价是模型不能边看文件、试运行、读错误再修复，复杂环境下可能损失成功率。

OpenCode仍是有效候选：它已经有多轮工具循环与本项目自造烟测，但不能仅凭先前选择就反过来规定所有训练数据必须是OpenCode轨迹。静态D3也能训练其科研实现能力，工具行为可由已有合格轨迹或少量目标harness补采提供。

在正式Base和训练前，用同一组独立dev、同一预算比较两条路线的环境成功率、最终产物得分和耗时，再冻结一个ASI主harness供所有模型使用。时间不足以比较时，应按数据主形态和已经验收的工程链做选择并披露能力限制；既不为追求名字一致强行换harness，也不为保住先选的harness要求全部重新生成数据。本轮只给代码复用方案，没有执行比较或修改当前OpenCode配置。

HLE可直接复用[固定官方生成client](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)，补显式revision／采样／图文与超时接线即可；无需另建逐题代码执行harness。
