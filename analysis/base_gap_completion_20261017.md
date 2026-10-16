# Base 缺口收尾

用户授权补齐 Base 的 15 个评分缺口：Terminal 9、SWE 5、HLE 1。保留现有答案、patch、失败尝试和正式测试，不增加 Base 求解调用；补评仍沿用原每题资源与评分时限。

## 当前进展

- HLE：2500/2500 有效、99 正确，完整分数 **3.96%**。只新增一次 grader 调用；原两次截断 JSON 保留。原 criteria、question、gold、solver 答案、4096 输出上限与 nonthinking 不变，仅调整 JSON 键顺序并缩短解释。累计 1057 次评分调用，费用估计 ¥1.6010295。
- SWE：截至03:13为49/51有效。两项已保存的原生0经逐结果审计恢复：Protonmail候选组件引用不存在的useConfig；Flipt候选新增错误go.sum，原安全校验和官方checksum数据库一致地拒绝它。Vuls原patch补评已得到有效0（Go unused import）。NodeBB在CPU11重放，Teleport等待Terminal共享评分槽释放后在CPU92重放；不改变任何候选文件。
- Terminal：截至03:13为439/445原生有效。两个fastText原答案没有model.bin，官方测试执行失败为0；PyTorch CLI seed3在预置官方MNIST后6项全过为1。剩余三个依赖/公共数据补评沿队列推进，另三项为已进入测试的计算超时。

远端纯读汇总在 `artifacts/results/base-gap-completion-20261017/`：`summary.json`、`report.md`、`swe51_summary.json`、`terminal_strict_summary.json`、`terminal_budget_summary.json`。只读取已保存评分和审计，不调用模型或测试。最终结果会在本报告收尾时更新。

## 三个真实计算超时的口径

FEAL seed0/4与model-extraction seed4已经进入官方pytest并耗尽原900秒。它们的原生reward仍为空，不能伪造3条原生0，也不通过增加求解时间修改原答案。

实际冻结的Harbor `aggregate_reward_dicts()` 与 `Mean.compute()`将空reward按0聚合。因此同时保留：

1. 严格原生评分覆盖：其余6项补齐后最多442/445；五seed严格均值/SD仍未齐。
2. Harbor默认固定预算聚合：仅这3个独立审查的候选计算超时按失败计入，完整分母仍445。需要同样处理全部比较模型，并单独披露原生覆盖和基础设施错误。

逐项真实测试入口、900秒计时、快照、无reward证据与Harbor源码见 [独立审计](terminal_three_compute_timeout_audit_20261017.md) 和 [JSON证据](source_snapshots/terminal_three_compute_timeout_audit_20261017.json)。依赖、磁盘、传输故障不会因这个规则静默变0。

## 执行与资源

Terminal六项只评分使用同一个 `direct_asi_grader_cpu92_95.lock`，4CPU/8GiB、900秒；每题cleanup后释放锁。SWE1CPU/4GiB、3000秒。CPU11通过零CPU消耗的sleep scope连续保留，避免任务切换间隙被另一队列接管；Teleport须等Terminal六项退出、共享锁可用和实际scope清空后才开始。已有专家、合版与训练任务不被取消。

SWE将编译临时目录与后续Go缓存原样迁到 `/data`；保持依赖内容、版本解析、go.sum安全校验和官方测试。真实stdout/stderr增量留存，避免只有超时结果却丢失Mocha/Go输出。

Terminal恢复时发现两个基础设施问题：整份`/etc`解包会在FUSE copy-up阻塞；GNU tar的目录unlink/覆盖选项也不能直接复用。现在完整恢复app/实际外部产物，按同一SIF的差异逐叶恢复etc并保留删除、type、权限与网络resolver例外记录。`setup_dpkg_for_overlay()`本身会把dpkg目录重建而丢失symlink/mode，这些不是模型更改。全部失败setup保留，没有将它们当成真实测试或再次求解。

HLE [补评记录](hle_last_judge_recovery_20261017.md)、SWE [收尾记录](base_swe_gap_repair_20261017.md) 与 Terminal `configs/eval/terminal_native_gaps_grade_plan_20261017.json` 可复核各原答案来源和新评分路径。
