# HLE checkpoint16与OOM作业来源核对

2026-10-16 22:10 CST。用户担心第16步的checkpoint是否来自OOM中断，询问是否重训。本轮只读Slurm历史、原生日志、trainer_state和checkpoint目录；没有重训或改动已有权重。

| 作业 | 实际结果 | 第16步发生的事情 |
|---|---|---|
| 当前HLE 726664（2k） | COMPLETED，0:0，连续250步 | eval成功，loss2.00219154，正常保存checkpoint16；随后继续17–250步 |
| Terminal 726345（2k旧失败run） | FAILED，1:0，仅完成16步 | 首次eval普通CE申请21.06GiB而OOM；没有完成eval，也没有保存任何checkpoint |
| 旧HLE 725704（500条） | COMPLETED，0:0，连续63步 | 正常eval与保存checkpoint16，随后继续17–63步 |

当前HLE的训练时间19:53:32—21:28:29，250条optimizer记录从1到250连续无缺步；`resume_from_checkpoint=null`，未发现OOM或resume日志。`training.log:3418`明确记录正常保存checkpoint16，最终summary为passed=true、final_checkpoint=checkpoint250、best_model_checkpoint=checkpoint16。作业已从scontrol过期，无法再读取Restarts计数；不能把这个缺失值写成实测0，但现有连续日志、参数、完成状态共同不支持中断续训解释。

旧500条HLE也在完整正常训练时出现val loss从2.6241升至3.1547，因此不能将类似趋势归因于Terminal的中断事故。

结论：当前HLE checkpoint16是正常周期保存、且验证loss最小的权重，与Terminal OOM无关。没有因这个误会按原配方重训的理由。继续既有Base/cp16/cp250实际validation对比，若任务准确率确实变差，再以数据格式/监督目标或更新幅度为依据设计新训练；不把重复原配方当成已知修复。

证据：[逐作业原始核对](source_snapshots/hle_checkpoint16_origin_20261016.json)、[HLE数据与loss分析](hle_val_rise_data_20261016.md)。
