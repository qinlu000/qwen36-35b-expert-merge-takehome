# 30分钟、最多4 CPU与仅SFT：题面及协议核验

更新：2026-10-15。仅阅读用户提供的题面与固定官方资料；没有修改配置、安装环境、运行任务、申请GPU或调用付费API。

## 结论

可以把独立开发任务的工程预算统一设为30分钟、最多4 CPU；正式结果应分别遵守每项benchmark的明确要求。所有模型使用相同配置是公平比较的必要条件，不能自动替代Terminal-Bench题面明确规定的配置。原题没有RL要求，仅SFT可以完成训练部分的交付。

| Benchmark | 30分钟、最多4 CPU的边界 | 建议 |
|---|---|---|
| Terminal-Bench 2.0 | 原题明确要求3小时、32 CPU、48 GB RAM，改为30分钟/4 CPU与题定配置不同；不能只披露差异便宣称满足该项正式要求 | 开发冒烟可短预算；正式保留原配置、完整89项×5次，利用有效并发、预拉镜像及提前完成提速。若要以自定义预算替代正式结果，须由面试方确认可接受 |
| SWE Pro V2 HARD-51 | 原题没有直接写死50分钟，要求记录并固定Agent、最大步数、token预算和超时；50分钟来自所选官方v2 locked protocol | 默认保留1 CPU/50分钟及fresh replay。30分钟可称同HARD-51和官方判分器下的自定义预算实验，不能称遵循该locked protocol；若作唯一正式结果，须先厘清面试方是否接受 |
| ASI-Bench | 3小时是框架默认，CLI公开支持自定义timeout；题面未写死该数值。Docker默认4 CPU/8GiB | 可以在训练前统一冻结30分钟，全部模型相同、披露与默认差异，仍运行完整任务条件和官方评分。linux_ns并不自动施加同样的4 CPU隔离，须外层真实落实 |
| HLE | 没有逐题独立CPU沙箱；共享客户端CPU和每题资源配额不是同一概念 | 可给共享请求/答案处理客户端4 CPU；主要冻结输出token、thinking、多模态/工具、答案抽取与判分协议。30分钟若采用应说明是题级保护超时，不表示每题需要30分钟或4 CPU |

## 题面依据与更正

用户原附件：`/Users/caoqinlu/.codex/attachments/20b2f4c3-6e03-4746-a389-d488086d7780/Pasted text.txt`。其Terminal段写明：“对齐模型卡：3 小时超时、32 CPU、48 GB RAM”。SWE段则要求“记录……Agent 框架、prompt、工具权限、最大步数、token 预算与超时”，并要求各评测对象相同配置，未直接给出50分钟数字。

因此，此前把SWE的50分钟与Terminal的题面硬值同等表述过严：前者是当前选定官方locked protocol的一部分，后者由题面直接明确。改变SWE预算必须准确披露协议变化，不能声称仍是该locked protocol；此处没有自行认定自定义SWE预算必然被面试方接受，也没有更改正式配置。

训练要求写明“完成所有专家模型的训练（LoRA/QLoRA 或全参均可，需论证选择）”，没有规定必须采用强化学习。仅SFT仍需完成数据来源/许可/去重/防污染、专家训练日志、可解释对照、至少两种合版方法或合版消融、最终完整评测及误差分析等交付。RL可作为后续实验，不属于当前训练交付的必要条件。

## 固定一手来源

- [SWE Pro V2 locked protocol](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)：50分钟、离线agent、patch捕获、全新镜像重评分；HARD-51划分也是依据该协议构造。原有1 CPU已满足“最多4 CPU”，无需增加为4 CPU。
- [ASI CLI timeout/parallel](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L1469)：`--timeout`为公开选项，task metadata不能覆盖；这支持在实验前选定统一预算。
- [ASI Docker资源默认值](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py)：默认4 CPU/8GiB；[linux_ns实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/linux_ns_sandbox.py)不提供相同CPU quota保证。
- [HLE生成客户端](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)：共享异步请求；默认num_workers为10，HTTP请求timeout600秒、max_retries1，仅是客户端请求保护参数，不是官方逐题CPU/计算预算。
- [固定Harbor Docker资源实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/docker.py#L483)：默认CPU为limit而非独占预留。保留题定32 CPU上限仍可以在有实测支持时共享并发；实际是否拥塞需由CPU、内存、I/O、模型队列遥测判断。

30分钟超时或4 CPU上限不能直接推算API费用按比例下降：token用量、多轮输入重复、缓存命中和任务提前完成决定实际费用。任务阶段超时也未必覆盖构建、评分和清理，不能把30分钟当成完整端到端时间保证。

## 仅SFT的研究判断与排期

本轮训练主线保持ms-swift+PEFT BF16 LoRA：三个专家SFT，保留同数据混训dev对照，AVG/TIES两个预设合版候选，经独立dev选择唯一权重后完成最低正式矩阵。当前总6M processed token和8h训练段仍是需真实吞吐验证的预算，不因不做RL就成为保证。

在线GRPO包含多组rollout生成、奖励计算和策略更新；工具型rollout还要运行独立任务环境、编译/科学计算和验证。ms-swift同置模式训练与采样共享GPU，分离模式则另占推理资源，还需权重同步。四卡在本题中还要承担SFT、开发与全量推理，因此本轮优先把时间用于可审计SFT与完整评测，不增加在线RL适配、奖励或超参分支。这是当前资源与交付窗口下的工程判断，不能泛化为72h内任何RL都不可能；小规模RL smoke不等于足够迭代、稳定收益及完整交付。

来源：[ms-swift GRPO流程与同置/分离模式](https://swift.readthedocs.io/en/latest/Instruction/GRPO/GetStarted/GRPO.html)、[TRL GRPO](https://huggingface.co/docs/trl/grpo_trainer)。

反事实排期算例：如果最低三模型矩阵的SWE153、TB1335、ASI720共2208次agent全部限定30分钟且每次都跑满，共1104 task-hours；有效并发16约69h，32约34.5h。HLE7500题、环境构建、验证/replay、评分和长尾仍另计。此算例仅说明缩timeout本身不保证72h交付，不代表已修改配置、实际平均时长或实际32路吞吐。减少CPU quota还可能拖慢编译/数值计算，需要独立任务实测。

如需向面试方确认的具体事项（仅留档，未发送）：“本题可用4张H100，是否允许Terminal主结果采用每trial 30分钟、4 CPU的资源受限设置？我们将对所有模型固定相同配置，保持完整89项×5组种子及官方评分，并在报告明确披露与题定3h/32CPU的差异。”SWE若选30min也应明确披露不使用原50min locked预算，不更换HARD-51任务或官方评分器。
