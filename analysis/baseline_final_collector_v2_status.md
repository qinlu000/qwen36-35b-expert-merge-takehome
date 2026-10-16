# 四 benchmark 持续最终汇总

独立入口：`scripts/collect_baseline_final_v2.py`。只读四位owner维护的现成summary，每30秒更新80上的 `artifacts/results/base_baseline_final_20261016/{summary.json,report.md}`；四项全部完整有效后退出，不运行模型／Judge／测试／hash，不扫描trial或修改生产流程。

| Benchmark | 固定分母 | 权威源 |
|---|---:|---|
| HLE | 2500 | `artifacts/runs/hle_judge_v2_20261016/summary.json` |
| ASI | 240 | `artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json` |
| SWE | 51 | `artifacts/eval/base_swe_v2_20261016_final/final_summary.json` |
| TB | 445（89×5） | `artifacts/results/base-terminal-v2-recovery-20261016/final_summary.json` |

SWE和TB路径／字段已直接由owner确认。各项未完整有效评分时主`primary_score_percent=null`，infra-invalid不是有效零分；源尚未写出或schema暂不满足时也保留null并记录原因，不猜分数。SWE `task_scores.csv`只作为原始明细链接。ASI完整240分数1.5709884069%，soil b2定点gate修复独立披露，原invalid保留。

TB每seed固定89题，只有该seed89个有效结果齐全才给seed分；五seed全齐后按未四舍五入的`100*correct_count/89`计算mean及`statistics.stdev`样本标准差ddof=1（单位百分点）。不将四种不同指标平均为一个未经定义的总分。

报告保存源文件绝对路径、mtime、覆盖、费用与必要环境修复说明：HLE校内Judge预算／实际usage和失败在途预留，ASI正式API0及自造校准保守预留，SWE native PATH／verifier工具和精确Go缓存修复，TB harness／verifier transport修复与owner accepted chronology。GPU／HPC资源费用没有价格依据，明确不包含。旧data writer并未与此汇总器共享全局事务锁，不声称总账原子统一。

部署采用80独立systemd user scope `apex-baseline-final-collector-20261016`，CPU86、内存256MiB、swap0，脱离本机运行。PID和精确启动参数在输出`launch.json`，轻量更新日志`collector.log`。源码快照`collector_source.py`，固定源清单`sources.json`；本地启动回执`analysis/source_snapshots/baseline_final_collector_v2_launch_20261016.json`。

重放单次只读汇总（不与正在运行的同目录collector重叠；flock拒绝重复实例）：

```bash
artifacts/envs/hle/bin/python scripts/collect_baseline_final_v2.py \
  --project /data/caoqinlu/projects/apex-takehome \
  --output /data/caoqinlu/projects/apex-takehome/artifacts/results/base_baseline_final_20261016 \
  --once
```

省略`--once`即30秒持续更新至全部完成。生产脚本／稳定源清单／本说明均独立维护；未改claud或根索引，未stage／commit。

Latest CPU allocation is recorded in analysis/source_snapshots/baseline_cpu_rebalance_20261016.json: HLE Judge125, final collector126, cache/enable guard127, future SWE grading124, Terminal archive grading120-123. HTTP concurrency and scoring budgets remain unchanged.
