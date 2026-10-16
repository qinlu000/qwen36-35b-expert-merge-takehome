# ASI baseline 最终结果（2026-10-16）

固定60任务×4提示条件，共240份冻结答案（237 infra1＋3旧）。公开seed31415本地评分已完成；含一项明确记录的空预测gate崩溃修复，不是Portal认证成绩。

**完整主得分：1.5709884069%（377.0372176580／24000），240有效／0评分器异常／0待处理。**

| 提示条件 | 已评分／应评分 | 平均百分分数 | 非零得分条件数 |
|---|---:|---:|---:|
| b1 | 60/60 | 2.47606058% | 7 |
| b2 | 60/60 | 0.69710004% | 4 |
| b3 | 60/60 | 1.35931484% | 5 |
| b4 | 60/60 | 1.75147817% | 7 |
| 全部 | 240/240 | 1.57098841% | 23 |

非零得分不等于任务通过率；表内为原生任务评分按每条件满分100汇总。

soil b2公开prompt第43–44行要求C、N数组均为`(n_days, 5)`；预测为`(3650, 0)`。原value_range hard gate取空数组min而异常。独立adapter只把这个条件、这两个文件的size==0返回失败，沿用原hard-gate零分聚合。其余239条评分记录完全保留；官方源码、阈值、rubric、gold及冻结答案未修改。原invalid报告与新repair记录并存。

正式Judge API共0次／¥0，本轮未新增生成、校准、测试或hash。37条pandas缺导入均未由对应官方TaskEnv声明；16个相关缓存的已声明依赖满足版本要求，没有补包重跑依据。

- 最终完整240条件JSON：[asi_scoring_final_20261016.json](source_snapshots/asi_scoring_final_20261016.json)。
- 修复依据、范围与原异常：[repair receipt](source_snapshots/asi_soil_empty_prediction_repair_20261016.json)。
- 执行入口、可重放步骤、reference与环境信息：[评分状态](baseline_asi_scoring_status.md)。
- 80原始报告：`/data/caoqinlu/projects/apex-takehome/artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json`。
- 80原invalid／sourcepatch：同目录`soil_empty_prediction_repair/`。
