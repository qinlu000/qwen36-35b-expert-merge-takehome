# Base 缺口收尾

用户授权补齐 Base 的 15 个评分缺口：Terminal 9、SWE 5、HLE 1。保留现有答案、patch、失败尝试和正式测试，不增加 Base 求解调用；补评仍沿用原每题资源与评分时限。

## 最终结果（2026-10-17 03:29 CST）

15个缺口现均有明确计分结论，所有补评进程与资源租约已退出。四项等权宏平均为 **11.3408876613%**，对应下表披露的固定预算口径；严格原生结果仍单独保存。

| Benchmark | 完整计分范围 | 成绩 |
|---|---:|---:|
| HLE | 2500/2500，99正确 | 3.96% |
| ASI公开本地 | 240/240 | 1.5709884069% |
| SWE | 51/51结论，10通过；50原生+1完整报告审计 | 19.6078431373% |
| Terminal | 445/445计入，90正确；442原生+3真实计算超时 | 20.2247191011% ± 2.6350650336个百分点 |

Terminal误差为五个固定seed的样本标准差（ddof=1），不是置信区间。完整小型收据见 [最终汇总](source_snapshots/base_gap_completion_20261017.json)，SWE逐项来源见 [51项CSV](source_snapshots/base_swe_task_scores_20261017.csv)。

- HLE：2500/2500 有效、99 正确，完整分数 **3.96%**。只新增一次 grader 调用；原两次截断 JSON 保留。原 criteria、question、gold、solver 答案、4096 输出上限与 nonthinking 不变，仅调整 JSON 键顺序并缩短解释。累计 1057 次评分调用，费用估计 ¥1.6010295。
- SWE：51/51计分结论、10通过。两项已保存的原生0经逐结果审计恢复：Protonmail候选组件引用不存在的useConfig；Flipt候选新增错误go.sum，原安全校验和官方checksum数据库一致地拒绝它。Vuls原patch补评已得到有效0（Go unused import）。NodeBB完整解析311个官方测试，307通过、4失败；进程在测试完成后仍不退出，清理前已保存完整官方parser输出，单独审定0，原生reward仍为空。Teleport于03:28:43完成：23测试通过、2失败，原生0、无exception；原命令的race检测命中候选代码的数据竞争，属于答案失败。首次bootstrap漏加既有musl shim、正式测试前失败的旧尝试完整保留，后续脚本已固化相同shim前置条件。
- Terminal：03:19六项全部补完，原生有效覆盖442/445。PyTorch CLI seed3在预置官方MNIST后6项全过为1，其余五项正式测试得0：两个fastText答案缺model.bin，CLI seed4预测错误，Doom缺frame.bmp，SAM把OrderedDict误传为checkpoint。固定预算汇总445项，正确数90，5seed均值 **20.2247191011%**，样本标准差 **2.6350650336个百分点**。另三项为已进入测试的计算超时，原生reward仍为空。
- ASI：既有本地公开评分240/240完整，**1.5709884069%**，本轮没有重跑。

远端纯读汇总在 `artifacts/results/base-gap-completion-20261017/`：`summary.json`、`report.md`、`swe51_summary.json`、`terminal_strict_summary.json`、`terminal_budget_summary.json`。只读取已保存评分和审计，不调用模型或测试；收齐后已自动退出。原生reward为空的4项（3个Terminal超时、1个NodeBB）没有被伪造为原生0；`strict_native_complete=false` 与 `complete_under_disclosed_harbor_budget_aggregation=true` 同时保留。

## 三个真实计算超时的口径

FEAL seed0/4与model-extraction seed4已经进入官方pytest并耗尽原900秒。它们的原生reward仍为空，不能伪造3条原生0，也不通过增加求解时间修改原答案。

实际冻结的Harbor `aggregate_reward_dicts()` 与 `Mean.compute()`将空reward按0聚合。因此同时保留：

1. 严格原生评分覆盖：其余6项补齐后最多442/445；五seed严格均值/SD仍未齐。
2. Harbor默认固定预算聚合：仅这3个独立审查的候选计算超时按失败计入，完整分母仍445。需要同样处理全部比较模型，并单独披露原生覆盖和基础设施错误。

逐项真实测试入口、900秒计时、快照、无reward证据与Harbor源码见 [独立审计](terminal_three_compute_timeout_audit_20261017.md) 和 [JSON证据](source_snapshots/terminal_three_compute_timeout_audit_20261017.json)。依赖、磁盘、传输故障不会因这个规则静默变0。

## 执行与资源

Terminal六项只评分使用同一个 `direct_asi_grader_cpu92_95.lock`，4CPU/8GiB、900秒；03:19完成后所有scope退出、锁已释放。SWE1CPU/4GiB、3000秒；Vuls/NodeBB退出后Teleport复用CPU11，03:28:43真实容器与sleep guard均退出、lease标记完成。没有新增Base GPU占用或ENOSPC；清理本轮四个私有SWE scratch目录，释放约4.99GiB，原始答案、评分日志及共享缓存全部保留。已有专家、合版与训练任务不被取消。

SWE将编译临时目录与后续Go缓存原样迁到 `/data`；保持依赖内容、版本解析、go.sum安全校验和官方测试。真实stdout/stderr增量留存，避免只有超时结果却丢失Mocha/Go输出。

Terminal恢复时发现两个基础设施问题：整份`/etc`解包会在FUSE copy-up阻塞；GNU tar的目录unlink/覆盖选项也不能直接复用。现在完整恢复app/实际外部产物，按同一SIF的差异逐叶恢复etc并保留删除、type、权限与网络resolver例外记录。`setup_dpkg_for_overlay()`本身会把dpkg目录重建而丢失symlink/mode，这些不是模型更改。全部失败setup保留，没有将它们当成真实测试或再次求解。

HLE [补评记录](hle_last_judge_recovery_20261017.md)、SWE [收尾记录](base_swe_gap_repair_20261017.md) 与 Terminal `configs/eval/terminal_native_gaps_grade_plan_20261017.json` 可复核各原答案来源和新评分路径。
