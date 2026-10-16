# HLE 后期验证 loss 升高：当前数据证据（2026-10-16）

**已确认最明显的分布差异在回答标签：训练主要监督模型 final／讲解，验证主要监督参考答案本体，其中59题仅一个字母。**这足以使“训练 loss 下降，验证 loss 上升”同时发生；它不是已证明的唯一原因，也不能据此断言真实解题准确率降低。

本轮只读当前冻结的 `artifacts/data/candidates/hle_existing_2k_20261016/swift_ready/` 下 2000 train / 100 val 的 messages、provenance、summary，以及导出代码。先核80文件结构与summary，再在本机同一冻结副本做简单文本统计；没有扫描旧数据、重新 tokenize、运行模型/API或修改数据。统计见 [独立JSON](source_snapshots/hle_val_rise_data_20261016.json)。

## 直接观察

| 项目 | Train 2000 | Val 100 |
| --- | ---: | ---: |
| assistant 回答字符中位数 | **722** | **1** |
| 回答字符均值 | **1206.69** | **27.65** |
| 回答字符 P90／最大 | 2218／12762 | 83／386 |
| 回答来源 | 1838 个模型 final；162 个参考短答 | 41 个数学 expected_answer；59 个选择题字母 |
| system 消息 | 0 | 0 |
| 消息角色 | 全部 user → assistant | 全部 user → assistant |
| reasoning/thinking独立字段／think标签 | 0／0 | 0／0 |

这里“模型 final”不表示每条都很长或每步经过独立验证；部分科学 final 很短。模型生成时使用 thinking 与否，也不能从清理后的字段反推。统计对象是**当前实际监督的文本**。

训练162个参考短答同样不是裸字母，格式为 `The answer is (E): <选项文本>`，出自 [当前组合脚本](../scripts/prepare_hle_existing_2k.py:98)。验证59个MMLU标签全部是单个 A–J 字母；数学验证41个则是最终数值/公式，例如 `42`，其中长公式最多386字符。它们由 [原验证导出逻辑](../scripts/export_night_hle_swift.py:67)直接使用 `gold_answer`，本轮2k导出保持原val不变，**没有使用完整教师讲解作为验证target**。

训练首个数学回答以“将表达式写成平方和”展开推导，首个参考短答是“答案为某选项及其文本”；验证对应类型只要求预测数值/字母。这些短例只说明格式，不用于判断具体任务正确性。

## 学科比例基本对齐，来源／回答风格仍不同

| 学科 | Train | Val |
| --- | ---: | ---: |
| Math | 817（40.85%） | 41% |
| Biology/Medicine | 224（11.2%） | 11% |
| Computer Science/AI | 193（9.65%） | 10% |
| Other | 186（9.3%） | 9% |
| Physics | 184（9.2%） | 9% |
| Humanities/Social Science | 175（8.75%） | 9% |
| Chemistry | 132（6.6%） | 7% |
| Engineering | 89（4.45%） | 4% |

因此，八大类比例没有显著失配的直接证据。细分题型、难度和子领域仍可能不同，不能由这张表保证难度一致。

训练来源为 Math-v4 817、MMLU-Pro 884、Science-v2 201、V4-Pro 8k 82、GLM5.1清理池16；验证仅 Math-v4 41、MMLU-Pro 59。训练不同来源的回答长度也很不同：Math-v4中位1383字符、MMLU-Pro为355、Science-v2为885、V4-Pro 8k为7537.5、GLM5.1为5035.5。这说明训练包含多种解释和表述习惯，验证没有同等的完整解释target；**不据字符量推断各源的梯度权重**，后者还取决于实际loss归一化和采样。

## 如何理解 loss 上升

验证交叉熵是在给定问题后，衡量参考target各token的概率。若target直接是 `J` 然后结束，而训练反复鼓励先输出解释或 `The answer is ...`，模型给“直接以J开头并很快结束”的概率可能下降，哪怕它在自由生成的讲解末尾仍能给出J。数学的“完整推导”与“仅最终公式”也存在类似问题。**这是有数据支持的机制推测，并非本轮已做的因果实验。**

小训练池上逐渐拟合教师风格或题目、学习率/训练步数偏大，也可能导致真实泛化下降；仅凭这次文本统计无法排除或量化。验证只有100题，且包含大量短target，单看总体loss难以区分格式、不同学科与能力变化。

当前最合理的解读是：**存在明显监督输出分布差异，val loss不能单独代表HLE答题能力。**这次没有看到train/val的system或thinking字段不同，也没有看到大类配额失配，因此不优先归因于这两点。

后续应比较已有检查点在冻结独立val上的实际答案正确率，并把“任务准确率”和“参考文本交叉熵”分别记录；可按数学/MCQ及来源观察变化。若要另建评估讲解风格的loss集合，应独立固定其标签政策，不在看到曲线后改写当前100题gold来追求好看的loss。本轮未启动这些评测或改动验证集。

## 原生日志曲线与指标定义

已从HPC原生logging提取250个训练点及16个验证点，生成[独立曲线](../artifacts/reports/hle_val_rise_20261016/loss_curve.png)；蓝线是训练batch loss的16步移动均值，橙线是固定100条验证loss，两者样本及聚合方式不同，不把绝对差值当作严格泛化误差估计。原始数值见[提取日志](source_snapshots/hle_val_rise_loss_history_20261016.json)，训练侧检查见[配置与采样报告](hle_val_rise_training_20261016.md)。

Hugging Face官方文档将语言模型交叉熵定义为参考token条件概率的负对数平均，并说明label=-100的token不计入；这支持“loss衡量给定参考文本的概率”的解释，不提供本项目格式失配的因果证明：[官方定义](https://huggingface.co/docs/transformers/en/perplexity)。训练与固定验证loss趋势可用于识别过度适配风险，但仍需同任务输出判断实际效果：[PyTorch训练与验证说明](https://docs.pytorch.org/tutorials/beginner/introyt/trainingyt.html)。

当前最值得补充的比较是Base、cp16、cp250在原100题上的答案抽取后准确率，并记录输出长度/格式和Math/MCQ分项。未测Base起点，cp16只代表现有检查点中的最低loss，不代表它已经优于Base。当前不根据曲线自动重训、改学习率或改写原val标签。

22:10补核：当前HLE726664连续训练250步正常完成，checkpoint16为成功eval后周期保存，并非OOM产物。16步OOM属于另一个Terminal726345且没有保存checkpoint；旧500条HLE也正常完成63步。[来源核对](hle_checkpoint16_origin_20261016.md)。
