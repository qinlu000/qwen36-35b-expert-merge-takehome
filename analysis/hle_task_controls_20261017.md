# HLE 实际任务对照与 loss 使用边界

2026-10-17 用户明确要求：loss 不能作为 validation 的判断标准。后续模型比较使用真实任务分数；已有原生 train/held-out loss 只保留为训练诊断，不算任务级对照、消融效果或 checkpoint 最优证据。独立 task-val 继续取消，正式结果不回流选择已冻结 AVG64 的系数、rank 或专家 checkpoint。

ASI128 曾按原生 loss 选择，而训练结束于134。这是需要披露的历史局限；当前服务、公开 adapter 和 AVG64 已统一使用128，不能把其解释为任务最优，也不能在运行中悄悄更换模型。HLE250 沿用之前已完成的真实任务比较；本轮不恢复 HLE100 或 SWE/SAB 的独立 val。

## 实际任务对照

使用已固定 HLE 全2500题（含342图像题）比较 Mixed883、固定压缩 AVG16、主模型 AVG64；另报告 HLE 专家与 Base。Mixed 和 AVG16 是 HLE 范围内的任务对照，不声称其四项 benchmark 均完成。二者的四项宏平均保持空。

- Mixed883 是既有混合数据训练的一轮最终 checkpoint；不采用其最低 loss checkpoint。
- AVG16 是已固定的等权合版后 rank16 SVD 压缩，不按正式答案或成绩重新调参。
- AVG64 是先前已冻结的主模型，rank64/alpha64；其 adapter 容量是 rank16 对照的四倍，实际分差也必须披露容量差异。

固定协议完全复用 `run_direct_hle_formal.py` 与 `score_direct_hle_formal.py`：同2500 ID、图片、system prompt、65536总上下文、8192输出、nonthinking、原采样参数、每题连续300秒、50并发，以及相同外部 judge 与判分规则。使用每题唯一终态结果，不因分数重新生成。最小合成图片验收不含正式或 val 题。每模型 judge 上限¥20/5000 calls，2个评分worker；实际费用另按账本统计。

## 已提交执行

配置为 [hle_task_controls_20261017.json](../configs/eval/hle_task_controls_20261017.json)，持久入口为 [run_hle_task_controls.py](../scripts/run_hle_task_controls.py)。Slurm **727831**，ACD1-30，TP2，18006→80的28096，2026-10-17 **03:40:21 CST** 开始，20小时期限。80上的 tunnel PID3243419、controller PID3243420于03:41:12启动。服务加载完成并通过验收后，按 Mixed883→AVG16 顺序运行，避免 max_loras1 下两个 alias 相互争用。上一模型生成退出且保存2500结果后才切换 alias；外部评分可继续并行。

输出分别为 `artifacts/eval/mixed883_hle2500_20261017` 与 `artifacts/eval/avg16_hle2500_20261017`，调度收据与日志在 `artifacts/eval/hle_task_controls_20261017`。每个输出保存固定ID选择表、实际命令、模型路径与生成/评分PID。模型消费者结束标记只证明生成请求排空，不证明评分完成或分数有效；最终统计仍逐题核验2500份评分及其来源。

两个主 HLE 服务727821/727822分别使用自己的2H100，和本对照服务合计新增6卡；已有五个TP2服务10卡，项目当前共16卡。专家 ASI 原PID、SWE与两个Terminal队列保持运行。没有新增训练或 loss-only GPU 作业。

启动后的资源更新：03:47核实SWE专家全51终态、消费者退出和原生模型running/waiting均0，已释放其727113服务2卡，项目降至14卡。新增三个端口的精确SSH PermitOpen已补齐，并只重连对应隧道子进程；没有重启模型、求解worker或已有作答。

**真实准入已确认**：03:46:46 Mixed883合成图片验收通过（prompt87与usage精确相等、nonthinking），随即启动generator3268682和grader3268683。03:47:49已有70生成终态、50 active、共120准入；AVG16尚未准入，按既定顺序接续。主HLE专家与AVG64同一时点分别192/13生成终态，各50 active，均已实际运行。详见[小型执行收据](source_snapshots/formal_evaluation_unblocked_20261017.json)。没有把这些回答数当作正确率。

最终汇总配置增加 `avg64_vs_mixed883` 和 `avg64_vs_avg16` 的 HLE 配对差值及固定ID bootstrap CI，主比较仍是 AVG64 对 Base 的四项结果。只有完整有效结果才能产生分数/区间；启动进程、程序执行结束或已保存回答数都不等于正确率。
