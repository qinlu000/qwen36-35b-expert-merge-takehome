# 正式评测统一汇总

UTC：2026-10-16T19:25:00.040245+00:00

| 模型 | SWE % | HLE % | ASI % | Terminal % | 四项等权宏平均 % |
|---|---:|---:|---:|---:|---:|
| Base | 未完成 50/51；invalid 1 | 3.96000000 | 1.57098841 | 未完成 442/445；invalid 3 | null |
| SWE249专家 | 未完成 41/51；invalid 2 | —（非目标未评） | —（非目标未评） | —（非目标未评） | null |
| HLE250专家 | —（非目标未评） | 未完成 0/2500；invalid 0 | —（非目标未评） | —（非目标未评） | null |
| ASI128专家 | —（非目标未评） | —（非目标未评） | 未完成 0/240；invalid 0 | —（非目标未评） | null |
| Terminal250专家 | —（非目标未评） | —（非目标未评） | —（非目标未评） | 未完成 15/445；invalid 0 | null |
| AVG64合版 | 未完成 0/51；invalid 0 | 未完成 0/2500；invalid 0 | 未完成 0/240；invalid 0 | 未完成 14/445；invalid 0 | null |

所有分母固定；有效错误/零分保留，评分 invalid、pending 和 missing 不计成错误，也不剔除后给完整主分。

专家只评目标项，不把四个不同专家拼成一个模型的宏平均。

swe249_vs_base：宏平均差值=null（四项未完整配对）
hle250_vs_base：宏平均差值=null（四项未完整配对）
asi128_vs_base：宏平均差值=null（四项未完整配对）
terminal250_vs_base：宏平均差值=null（四项未完整配对）
avg64_vs_base：宏平均差值=null（四项未完整配对）

区间：10000次paired cluster bootstrap，seed20261015。Terminal保留任务内五seed；ASI保留项目内四condition。
完整来源、逐项区间与invalid原因见summary.json；逐观测状态和原始路径见observations.jsonl。

协议限制：

- All four primary percentages have equal weight1/4; targeted experts have no four-benchmark macro score.
- Any missing/invalid/pending observation or incompatible ID/owner status blocks that benchmark primary and CI; no valid-subset mean.
- Paired CIs require full same-ID observations, not complete-case intersection after dropping invalid entries.
- Terminal1800s/4CPU/8GiB/64K/8K differs from original3h/32CPU/48GiB/256K/80K setting.
- Service replicas, global concurrency and scheduling differ between historical Base and later models; paired task resampling does not remove those confounds.
- HLE/ASI replacement Judge and public local ASI scope must remain disclosed.
