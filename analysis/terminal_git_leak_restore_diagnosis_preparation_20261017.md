# git-leak restore：metadata-only 原生诊断准备

2026-10-17 **10:23:37 CST** 完成默认 prepare，尚未执行诊断、取锁或创建 claim/guard/native。原 e0ad driver、db12 manifest、旧 attempt 及正式 source 不变。root 必须另作 fresh 资源检查并决定是否唯一 `--execute`；本轮不准入。

新 [85行 wrapper](../scripts/diagnose_terminal_git_leak_restore_20261017.py) 直接导入冻结 `run_terminal_git_leak_grade_only_20261017` 的 `validate`、`run` 和纯辅助函数，复用其同global92–95 EX/可见guard、SWE drain、ASI优先、Terminal交接拒绝、≥2400s runway及自然双排空顺序，没有复制parent或新增scheduler。新 [manifest](../configs/eval/terminal_git_leak_restore_diagnosis_20261017.json) 固定原33来源，额外绑定wrapper/旧parent/原restore/delta/旧attempt证据，共40个小文件，实际全部通过。

## 结构上禁止进入官方测试

独立根为 `R/artifacts/recovery/terminal250-git-leak-seed1-restore-diagnosis-20261017`，其中 `R=/data/caoqinlu/projects/apex-takehome`。仅生成新 `prepared/restore.json`，SHA256 `36fabc6d72167eac0469e1570bf1857e4c8d006c9e3774451f0c95e327905fe5`。原 archive、delta tar及恢复命令0/1对象（含command字符串和timeout）与旧95017 restore逐字相同；没有重建候选、改23项delta、安装或启动任务服务。

命令2只调用隔离 harness Python `-I -S`，枚举原app50+etc23共73个成员，记录路径、expected/actual type与mode、内容hash是否相同、symlink目标是否相同、hardlink是否samefile，以及app名单的缺失/额外路径。只输出metadata和布尔，不打印文件bytes、secret、答案、Git blob、实际内容hash或题面。遇到单项OSError也记录类型并继续；其他异常只输出error type及已得metadata。

该payload的最外层 `finally: sys.exit(86)` 保证正常、存在差异及payload异常都非0退出。原frozen `run_terminal_repair_grade_v2.py` 在每条恢复命令后检查return_code，非0立即抛错，且该循环位于切换评分phase及 `Verifier(...).verify()` 之前。因此诊断在restore2处必停；不能把它当一次正式评分或原题失败。即使未来出现bootstrap/timeout等更早错误，也不得将其解释为测试开始或成绩。

原4CPU/8192MiB保持，物理92–95/相对offset0、词法venv、原PATH/PYTHONPATH/XDG/DBus、短TMPDIR `/data/caoqinlu/tg1`（control socket58B）均沿用。虽然原config仍含900s verifier以保持来源，**本wrapper不允许进入该verifier**。唯一新 `attempt1` 与原输出隔离；无自动重试、补评分或collector变更。

## 静态检查与可证伪假说

原native的唯一持久错误是 `restore mode mismatch`，没有path。已只读核实际Harbor `environments/singularity/singularity.py:763–819`、实际cache server `server.py:116–165`、frozen `TerminalRepairEnvironment.exec:25–32` 与 native exec wrapper：未发现“每次exec都chmod原app”的直接代码。Singularity启动时chmod staging/bootstrap，server启动时创建工作目录/工具/系统目录，verifier工具有自身chmod；这些与每次恢复exec后递归chmod app是不同事实。尚未证明镜像shell环境或fakeroot行为完全不影响mode，不能排除未定位的钩子。

本次诊断的假说及判别为：

1. **tar/fakeroot未保留部分mode。** 预测相应成员type和内容hash相同，但mode不同；全部差异名单能区分局部路径与全局归一化。
2. **链接mode表示差异。** 预测mode差异集中在symlink/hardlink，链接目标/同inode和内容仍一致；若普通文件/目录也差异则不能仅用链接解释。
3. **exec入口或shell环境改变权限。** 目前静态未找到直接证据；若目录/文件出现一致的chmod形态而归档解包语义正常，才值得进一步检查。单次metadata快照只能显示结果，不能凭形态断言因果。

不预先修改mode、不移除完整性门、不把某类差异当可忽略。root需先看真实metadata，再决定是否有可验证的工程修复，不能盲目再跑正式grade。

## 已运行的最小CPU检查

10:23:36.855–10:23:36.979 CST 在metadata CPU10运行三成员**合成**归档夹具，执行同一payload（仅将绝对路径重定向至独立临时树）：全匹配仍exit86；刻意改mode后完整记录两个mode差异，内容/硬链布尔仍正确且exit86；故意缺归档也exit86。夹具没有原候选、测试、容器、模型或API。它验证诊断不会首错即丢失其他差异，并证明“全匹配也不能进入Verifier”。AST编译通过。

实际default prepare随后通过，SWE已drain、ASI尚未评分就绪、Terminal未接管；新attempt目录不存在，0claim/guard/取锁/native。机器收据：[terminal_git_leak_restore_diagnosis_preparation_20261017.json](source_snapshots/terminal_git_leak_restore_diagnosis_preparation_20261017.json)，80副本为独立根的 `driver-preparation.json`。

仅准备的命令为：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/data/caoqinlu/projects/apex-takehome/scripts \
taskset -c 10 /data/caoqinlu/projects/apex-takehome/artifacts/envs/harbor/bin/python \
  /data/caoqinlu/projects/apex-takehome/scripts/diagnose_terminal_git_leak_restore_20261017.py
```

本轮**没有添加 `--execute`**。未来root若决定唯一诊断，仍需fresh核global锁/CPU所有权、SWE/ASI优先状态、截止余量及旧新attempt隔离，并另存root-launch/PID/startticks；保持宽session cgroup，不能将parent设AllowedCPUs10。

wrapper SHA256 `83fcadb53a7c9a3724e3c152b456bb23579075440860dafa9cd61515d1c41cfa`；manifest SHA256 `2831649f1b86f03be013ad5c602f2528ff8e70c1436fadde6c256df0a062aff7`；复用parent仍为 `e0ad3fb1a72dc5a9db597611de3cd8ac8690ab9a61c33f212a9c13c1ce71da6c`。尚无真实mode差异诊断结果，不改正式null。
