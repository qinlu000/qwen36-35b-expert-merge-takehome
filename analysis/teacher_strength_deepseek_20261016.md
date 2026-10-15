# Terminal 教师 DeepSeek-V3.2 与本项目 Qwen Base

2026-10-16。一手联网核查使用 ego-browser；未运行模型、任务、GPU或付费 API。对照的是**标准 DeepSeek-V3.2**，不混入 V3.2-Exp、V3.2-Speciale，也不采用 Hugging Face 页底用户上传的第三方 Evaluation Results。

**结论：没有依据把 DeepSeek-V3.2 当成一定强于 Qwen3.6-35B-A3B 的终端教师。作者公开 TB2 数字中 Qwen 更高，但框架、预算和模式不同，不能据此给出严格的模型强弱排序。**现成成功轨迹仍可作为工具操作示范候选；它是否让本项目 Base 提升，需要同协议的独立 dev 对照。

## 一手数字与可比性

| 指标 | 标准 DeepSeek-V3.2 作者结果 | 固定 Qwen3.6-35B-A3B 模型卡 | 能得出的结论 |
|---|---|---|---|
| Terminal-Bench 2.0 | **46.4% thinking / Claude Code**；另报 **39.3% non-thinking / Terminus**；附录同 Claude Code 对照是 **37.1% non-thinking vs 46.4% thinking** | **51.5%**，Harbor/Terminus-2，256K context、80K max_tokens、3h、32 CPU/48GB，5次均值 | 公开数字不支持“教师在终端任务上明显强于 Base”；不能把51.5−46.4或51.5−39.3当相同设置下的净模型差距。 |
| SWE-bench Verified | **73.1% thinking**，内部框架；作者称其他框架及非思考结果约72–74%；附录 non-thinking 为72.1% | **73.4%**，内部 bash+file-edit scaffold、200K context | 公开结果接近；不是本题 SWE Pro V2 HARD-51，也不是同 harness 的复测。 |
| SWE-bench Multilingual | **70.2% thinking**，附录 non-thinking 68.9% | **67.2%** | DeepSeek的发布数值较高，仍不能据此断言其Terminal能力更强。 |
| HLE 无工具 | **25.1% text-only thinking**；换官方 prompt 后另得 **23.9%** | **21.4%**，卡中该行未给出足以复现同一HLE口径的全部细节 | 仅是另一任务方向的证据；prompt、模态范围和模式均应核齐，不能用于Terminal教师强弱定论。 |
| 本题 SWE Pro V2 HARD-51 / ASI-Bench | 本轮未找到作者报告的对应版本结果 | Qwen的SWE Pro **49.5%** 来自修订公开集；不是本题指定版本 | 不能用其他 SWE Pro 版本或 Verified 结果冒充本题证据。 |

DeepSeek 数字及设置来自 [原论文 §4.1 / Table 2](https://arxiv.org/html/2512.02556v1#S4.SS1)、[附录 C / Table 9](https://arxiv.org/html/2512.02556v1#A3)。Qwen 来自固定 revision `995ad96eacd98c81ed38be0c5b274b04031597b0` 的[官方模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#L69)及 [SWE/TB设置脚注 L307–308](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md#L307)，本地对应 [固定快照](source_snapshots/model_card.md)。Qwen HLE 数字在 L248–253。

## 最容易误读的设置差异

DeepSeek 论文 §4.1 说明 tool-use 配置为 thinking，通用评测 temperature=1.0、128K context；TB2 的46.4使用 Claude Code。作者特意解释，当时其 thinking 上下文管理与 Terminus 不兼容，故另测 Terminus non-thinking=39.3。论文在该处未给出足以对齐 Qwen TB2 全部资源/输出/重复次数的配置，不能自行补成相同预算。**这是2025-12-02论文所述实现限制，不能倒推出后来 Nemotron 教师采集的 thinking+Terminus 记录无效**，也不能用旧论文的 Claude Code 代替已下载数据的真实采集 harness。[原文 §4.1](https://arxiv.org/html/2512.02556v1#S4.SS1)

Qwen 的51.5也不是本项目已经测得的 Base 成绩。本项目目前锁定 [资源受限协议](../configs/eval/protocol_v2_unified64k8k.json)：**non-thinking、64K context、每次输出8192**，并使用当前固定 agent/环境/预算。现成 Terminal 教师记录为 DeepSeek-V3.2、enable_thinking=true；因此“教师开思考而学生关闭”的差异真实存在，但我们尚无在相同任务、同一资源受限协议下测出的师生结果。

DeepSeek HLE 的 **40.8%** 在 Table 2 的 Search Agent 区域，是有工具方向，不能与无工具25.1或Qwen HLE21.4混为一列；**30.6%** 是 Speciale 的 HLE 数字，不属于标准V3.2。[Table 2](https://arxiv.org/html/2512.02556v1#S4.T2)、[Table 3](https://arxiv.org/html/2512.02556v1#S4.T3)

## 对当前训练池的判断

1. **应降低“强教师蒸馏必有收益”的预期。**目前适合把 Terminal-Corpus 定位为同类环境与工具协议的成功行为示范候选，而不是已证明强于Base的教师答案。源文件名含 filtered、轨迹写 task_complete 或教师名更大，都不自动证明逐条正确。
2. **教师总体分数不是样本资格的唯一标准。**即使总体通过率不如学生，经过独立验证、解决了不同训练任务的轨迹仍可能提供有效操作序列；这只是可检验的训练假设，不能保证SFT正收益。优先已有可恢复环境、工具/提交契约兼容、结果有可核依据的独立训练任务，避免把全池未经筛选地都当正例。
3. **去显式思考不是把教师变成其non-thinking版本。**记录是thinking策略采样出的行为；删外层think后，保留的commands、观察与Terminus JSON analysis/plan仍由该策略产生。清洗后的SFT收益不能用作者39.3%的non-thinking成绩预测，也不能用46.4%直接担保。
4. **先做小规模 Base/SFT 独立dev对照，再决定扩池。**固定同一协议和训练任务来源分割，比较完成率、无效动作/格式错误、长度/时间失败及成本；正式benchmark不用于选数据或反复调参。如果SFT没有提高目标能力，收缩或替换该来源，而不是仅凭教师名继续堆量。

当前长度与协议审计见 [Terminal 实测](trajectory_lengths_terminal.md)、[环境来源审计](trajectory_sandbox_terminal.md)。它们证明了可检查的结构/长度范围，不能替代成功验证或Base/SFT收益实验。
