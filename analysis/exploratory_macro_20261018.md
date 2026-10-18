# AVG64 exploratory 四项宏平均

用户确认将 Terminal 的完整 seed2 single-run 写入汇总，但要求显式标注 exploratory。这里给出独立补充视图，不覆盖 strict aggregation。

| 模型 | SWE | HLE | ASI | Terminal seed2 | exploratory macro |
|---|---:|---:|---:|---:|---:|
| Base | 19.607843% | 3.96% | 1.570988% | 19.101124% | **11.059989%** |
| AVG64 | 7.843137% | 4.68% | 0.460702% | 12.359551% | **6.335847%** |

AVG64 相对 Base 的这个补充视图差值为 **−4.724141 个百分点**。Terminal 列使用固定 seed=2、每题一次的 single-run exploratory 结果；它没有题面要求的五次均值/标准差，也使用了本实验的 30 分钟/4 CPU/8 GiB/64K/8K 配置，因此该宏平均不能称为官方 Terminal-Bench 四项正式宏平均。

原始 strict 视图仍保留：Base Terminal 三条 native invalid，正式 AVG64 四项 macro 不覆盖写入。该文件只用于报告中“补充 exploratory 结果”小节。
