# 三个已完成专家的验证结果（2026-10-16）

这里是原生Swift训练时在保留轨迹上计算的交叉熵val loss，越低越好；不是SWE任务成功率、ASI程序得分或HLE准确率。不同验证集不能横向比较loss高低来判断哪个专家更强。

| 专家 / run | SFT val条数 | 首次验证（step16） | 最佳loss / checkpoint | 最后一步loss / checkpoint |
|---|---:|---:|---|---|
| SWE / 726335 | 87 | 0.38588187 | 0.31768048 / 249 | 0.31768048 / 249 |
| ASI / 726336 | 20 | 0.73078740 | 0.58268344 / 128 | 0.58287901 / 134 |
| HLE / 726664 | 100 | 2.00219154 | 2.00219154 / 16 | 3.49751949 / 250 |

SWE、ASI从首次验证到最佳值总体下降；ASI最终与最佳非常接近。HLE在step16之后的验证loss明显变差，原生best记录仍是checkpoint16，不能自动选择最后checkpoint250，也不能声称HLE已经通过SFT提升了准确率。过拟合或训练/验证监督分布差异是待检验解释，不是已经查明的唯一原因。

三个run都设置eval_on_start=false，没有step0同val的Base loss，因此首测step16也不是Base起点。实际任务提升需在同一独立验证任务集上比较Base与候选checkpoint的生成、执行和评分，不能用上述loss或官方benchmark的Base分数替代。

本轮只读HPC的SFT run及80现有eval/run目录，未发现这三个专家已经产出的独立val生成准确率/任务成功率文件；现有正式benchmark结果属于Base。没有为查询额外运行模型或评分API。

证据：[三个run的原生验证快照](source_snapshots/three_expert_val_scores_20261016.json)。完整训练输入、provenance与运行配置见[训练数据汇报](training_data_report_20261016.md)。
