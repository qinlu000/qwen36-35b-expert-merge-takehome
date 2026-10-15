# HLE 的上下文与输出预算：公开证据

查阅时间：2026-10-16；真实联网查阅 HLE 官方论文、固定官方源码和固定 Qwen 模型卡。仅查方法、统计图注和通用评测代码，未读取正式题目答案、未跑题、未调用模型/API、未改变协议。

**结论：公开资料支持给 HLE 区分思考与非思考预算，但没有找到“Qwen3.6-35B-A3B 非思考，32K 总上下文＋4K 输出足够且不损失准确率”的直接实证。32K/4K 可以是资源约束下的实验设置，不能写成官方最低足够配置。此前统一 128K 的建议也不是 HLE 的强制要求。**

## 一手资料能确认什么

| 来源 | 实际数字与含义 | 对当前决策的限制 |
| --- | --- | --- |
| [HLE 官方 README，固定 commit `22ed3074…`，L31–45](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/README.md#L31-L45) | 作者评测采用模型可用的最大输出额度，并提醒 reasoning 模型的最大 completion 不宜低于 **8192**；命令示例也是 **8192 输出**。 | 不是 8192 总 context；提醒明确面向 reasoning，不能直接作为非思考模式的最低值。示例能运行不等于对所有模型无损。 |
| [HLE 官方生成代码，L13–38、L109](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py#L13-L38) | 一次系统提示＋一道题文本及可选图片；`max_completion_tokens` 传给输出限制，默认 **None**，未规定输入上下文窗口。输出仍需 Explanation、Answer、Confidence。 | HLE 的本路线没有持续增长的工具历史；非思考也不能简化成只输出答案。代码没有给出 32K context 或 4K 输出的充分性证据。 |
| [HLE 论文 Figure 5](https://arxiv.org/html/2501.14249v11#S4.F5) 与 [Appendix C.4 / Figure 6](https://arxiv.org/html/2501.14249v11#A3.SS4) | Figure 5 统计 reasoning 模型平均 completion，包含推理与最终输出；C.4 单列 non-reasoning 模型的平均输出。作者说明前者的生成量显著更多。 | 平均输出长度不是题干长度分布，也不是所有题所需的最大输出，更不是同一 Qwen3.6 的 4K/8K/16K 准确率消融。不能把历史模型统计直接移植到当前模型和冻结数据版本。 |
| [Qwen3.6 固定模型卡：context，L555–557](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#L555) | 原生总 context **262144**；为保留 thinking 能力，建议至少 **128K**。 | 后一建议带有 thinking 条件，不能据此断言关闭思考的 HLE 仍必须 128K。 |
| [Qwen3.6 固定模型卡：输出长度，L1012](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#L1012) | 多数查询建议最大输出 **32768**，复杂数学/编程基准建议 **81920**。 | 两者均是**输出**，不是总 context；该段没有提供 HLE 单独消融，也未给非思考模式单独的较短最低值。 |

以上 Qwen 模型卡同时明确总长度包含输入与输出，见 [Processing Ultra-Long Texts，L957–958](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#L957)。所以 **32K 总 context＝32768**、**4K 输出＝4096** 时，输入含模板、系统提示、题干、视觉 token 的空间最多 **28672**；这是算术预算，不是测得的全量覆盖率。

## 没有找到的关键实证

- 本次查看的 HLE 官方论文方法、图注和固定评测源码中，未找到针对本实验冻结的 2500 题、采用 Qwen tokenizer/processor 的题干输入 token 分布（中位数、p95、最大值）。不能用“短答案题”推断输入和求解输出都短。
- 未找到同一 **Qwen3.6-35B-A3B、非思考、无工具、同一 HLE 版本**在 4K/8K/16K 输出预算上的官方准确率与截断率对照。检索结果没有支持“4K 已足够”的证据。
- 模型卡给出的 HLE 分数不能证明是在 32K/4K 下得到；本次未发现该分数单独披露的 context/output 完整配置。

## 可作出的项目决策

若优先节省资源，**32K 总 context＋4K 输出可以列为待验证候选**，且应明确是本实验选择。决定前至少需要仅输出汇总的输入 token 覆盖统计，包含真实图片处理后的视觉 token；本轮未另跑数据统计。生成预算是否足够要看独立开发题上的 `finish_reason=length`、最终答案字段完成率及不同预算的表现，不能只看输入能放下。不要用正式 HLE 分数挑输出预算。

在尚无上述实证时，**不能把 4K 描述成有证据的无损阈值，也无需把 128K 描述成 HLE 的官方硬门槛**。若开启思考，官方 8192 的最低建议与 Qwen 较长输出建议构成更直接的反对压缩证据；关闭思考则仍需单独验证，保留可见 Explanation。

本报告只记录证据与条件，不修改 `protocol_v1.json`，不替项目锁定新预算。
