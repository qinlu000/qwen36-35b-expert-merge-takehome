# git-leak-recovery/seed1：唯一 grade-only 执行审核

**本次未进入官方测试，reward 仍为 null。** root 与 merge 独立代码审阅通过、fresh 资源检查后，于 2026-10-17 **10:18:17 CST** 唯一启动 parent **2152787/startticks 870252110**。该 parent 于 **10:18:27** 自然完成清理并解锁。没有重试、补候选、安装、任务服务或模型/API 调用；没有接 collector/正式 summary。

80 项目根为 `/data/caoqinlu/projects/apex-takehome`（`R`）。独立输出根为 `R/artifacts/recovery/terminal250-git-leak-seed1-grade-only-20261017`（`O`）。root 启动收据为 `O/root-launch-20261017.json`，记录 SWE1765416 已排空、ASI 尚未评分就绪、pool scope 空及明确 `--execute`。live driver SHA256 `e0ad3fb1a72dc5a9db597611de3cd8ac8690ab9a61c33f212a9c13c1ce71da6c`、manifest SHA256 `db12c5b04fd4815b424a467b2f78da99ed0cc5a3cf5fa987a5a5e755f337625b` 均未修改。

## 实际阶段与停止原因

唯一 child 为 **2152806/startticks 870252243**，原词法 Harbor venv，taskset 物理92–95、相对 offset0，复用原 frozen `run_terminal_repair_grade_v2.py`。原配置保持4CPU/8192MiB、900s verifier、600s build，0新 solver/model 调用。parent 记录 guard 实际 affinity92–95、MemoryMax32MiB、swap0；该32MiB仅是可见租约 guard，**不是 native 限额**。本次快速退出前未另外采到 live native cgroup/affinity，不能将配置值冒充独立实测。

`O/attempt1/native-grade/restore-command-{0,1,2}.json` 的实际结果为：

| 命令 | 返回码 | 可确认的事实 |
|---|---:|---|
| 0：原app解包 | 0 | tar 命令成功；尚未独立证明全部成员逐项一致 |
| 1：23项etc delta解包与resolver核验 | 0 | stdout明确 `/etc/resolv.conf: OK`，stderr空 |
| 2：隔离harness Python完整性校验 | 1 | stdout报告 `AssertionError: restore mode mismatch`，stderr空 |

第三条校验在首个 mode 不一致处停止，原 checker 没有记录具体 path。因此**无法从本次持久证据定位哪个路径/mode不符，也不能宣称完整app、全部23项或跨路径hardlink的live校验已通过**。先前 tiny 合成硬链夹具通过，只说明合成拓扑处理正确，不能代替这次检查。不能移除 mode 门或据解包 rc0 放行评分。

独立 native 文件为 `O/attempt1/native-grade/result.json`，SHA256 **`3cbbd7c9f3d3dec49c5b46a3b0805ccae43820ece6be7943896ccf0b549b3dbe`**，finished_at为 **10:18:20.823955 CST**。模型 `apex-terminal250`、seed1、task checksum `da0aeda47b324bff84c67faa3d8bed3b3b5f1200e3b17cecbc7dc8f802fd366a` 保持；`verifier_result=null`，异常 `RuntimeError: Original restore command 2 returned 1`。verifier目录为空，冻结CLI在恢复循环抛错后没有调用原Verifier，故没有test stdout、CTRF或native reward。这是**评分前恢复一致性门失败**，不是900s verifier计算超时、任务判错或可派生预算0。

## 原字节与资源释放

10:19:26 CST 独立只读复核全部 **37个 claim 绑定**（33个来源加restore/delta/新manifest/driver）均不变。同SIF resolved路径、92987392 bytes与mtime_ns `1792079169674202869` 均匹配原manifest；未做SIF大哈希。原答卷archive、原result/config/task/tests、frozen源码及原raw null保留。

parent持久状态为 `finished_pending_root_review`、child rc0、`original_and_restore_unchanged=true`、`lock_held=false`、`guard_stopped=true`，记录了完整释放顺序：

1. native scope空：10:18:23.043619、10:18:25.105003。
2. 停止自身guard。
3. 全pool scope空：10:18:25.165435、10:18:27.225153。
4. 10:18:27.277241 解锁。

独立复核又在 **10:19:23.913888、10:19:25.981480** 两次看到pool scope空；parent/child均已不存在，global锁inode90775088在capture时无kernel holder，未为检查获取该锁。没有写ASI/Terminal CPU marker，没有改变既有租约或队列。

完整机器收据为 [terminal_git_leak_grade_only_execution_20261017.json](source_snapshots/terminal_git_leak_grade_only_execution_20261017.json)，80副本为 `O/execution-review.json`。本轮只观察该已结束的唯一attempt并保存审核；**不重启、不改冻结driver/manifest，不接受成绩**。后续若需进一步定位 mode 差异或显式工程恢复，须由 root 独立决定，保留本次失败证据与原预算边界。
