# Terminal git-leak-recovery/seed1：仅离线评分恢复准备

2026-10-17 09:25:40–09:27:34 CST，在 80 的 metadata CPU10 完成静态检查。**原归档具备继续准备 grade-only 的证据；尚未运行 verifier、候选代码或服务，没有新 claim、driver、恢复包或成绩。** 后续必须由 root 审阅恢复清单并准备唯一 grader 租约。当前 SWE short-TMPDIR cohort（parent 1765416）优先，不能凭瞬时空闲抢占 92–95。

## 原答卷与失效边界

项目根为 `/data/caoqinlu/projects/apex-takehome`（下称 `R`）。原 trial 为 `R/artifacts/eval/terminal250_full445_20261017/trials/git-leak-recovery__seed1`，模型 `apex-terminal250`、seed 1。原 result SHA256 `cb48b18ec0d4df51783385f475970120cc3a43932afbc6e7660dfc42314440ca`；原 config SHA256 `6257eb4c685891a50ec8a627f69dcbc81447b28a9bcc75ac5c1155a2ad3c3371`。

原异常为 `Refusing public network after unconfirmed solver cleanup`，`verifier_result=null`，原 verifier 目录为空。候选在原 1800s solver 预算结束后已捕获，随后阶段交接 guard 失败；这不是已启动 verifier 的 900s 计算超时，不能作预算派生 0。

`artifacts/logs/artifacts/final-task-state.tar` 为 829440 bytes，SHA256 `1f8863211b0189c011fdd1bf39717c8ec9481a273c7e66ee45267b68c2b7dffd`；同目录 JSON SHA256 `9ccbc62dae3761a3d4a7b3f95f13b7d9497b86a1862e7404d849c100adacec8c`。快照 `return_code=0`、stderr 空、`captured_before_verifier=true`，完整前缀为 `app`、`etc`；额外路径仅 `root/.lesshst`。没有展示 secret、答案、Git blob 或原轨迹内容。

## 任务实际需要什么

原 task 为 `R/artifacts/results/base-terminal-v2-724242-r2/tasks/git-leak-recovery`。对原 `tests/test_outputs.py` 的只读 AST/路径核查表明：13–15 行读取 `/app/secret.txt`；21/40/53/68/83 行调用 Git，工作目录均为 `/app/repo`；97 行调用 shell checksum。需要完整工作树及 `.git` 的可达、不可达对象，不能只保存当前 checkout。该 verifier 未见 HTTP/socket/service/server 调用，**无需恢复或启动任务服务**。`tests/test.sh:8` 的标准 uv bootstrap 属原 verifier 工具供应；22 行运行原测试并写 CTRF，26/28 行写 reward，均尚未执行。

## 离线归档与 Git 闭包

独立临时目录为 `R/artifacts/recovery/terminal250-git-leak-seed1-preparation-20261017`。归档共 561 个成员；仅用 Python tar `filter=data` 安全提取 50 个 `app` 成员，其中 `.git` 46 个。校验拒绝绝对成员名、`..`、重复成员、特殊设备和逃逸 app 的链接；未 checkout/reset，也未执行归档中的程序。

提取后的 `/app/secret.txt`、`.git/HEAD`、`.git/config`、objects、refs 均存在。无 shallow、promisor、alternates、commondir、gitdir、grafts 等外部对象依赖。关闭系统/全局 Git 配置、hooks、fsmonitor、协议与 lazy fetch 后，对独立副本执行 `git fsck --full --no-progress`：**rc 0，stdout/stderr 均 0 bytes，missing/error/dangling 均 0**。这证明本次提取的对象闭包可被 Git 完整性检查接受，不代表原任务已通过。提取树的前后聚合哈希相同。

## 同 SIF 的 `/etc` 最小差分

原 SIF 标签 `R/artifacts/benchmarks/sif/alexgshaw_git-leak-recovery_20251031.sif` 指向 `sha256-62160e522a4238b8bcd522411ea97b5b200f811e5899d34947e66809bef7e586.sif`，92987392 bytes，mtime_ns `1792079169674202869`。只读取前 1 MiB 定位 SquashFS，并以单线程 `unsquashfs` 静态提取 `/etc`；没有启动容器，也未做大文件全哈希。

排除运行时管理的 `/etc/resolv.conf` 后，发现 **23 处**内容、类型或 mode 差分，精确名单、模式及内容哈希见 JSON。包括 apt/dpkg 配置、Python 配置及少量系统配置；不能仅凭差分将其归因于模型或 harness，更不能借恢复补装产品/依赖。只允许恢复原归档中经审阅的必要 `/etc` delta，不能覆盖整棵 `/etc`，不能改 resolver、网络、测试或候选内容。

特别需要保留的跨路径硬链为：

- `/etc/apt/apt.conf.d/01-vendor-ubuntu`
- `/app/repo/.git/info/refs`（归档 linkname 为 `app/repo/.git/info/refs`）

首次安全门因该 hardlink 拒绝提取，检查其目标确为归档内普通文件后，仅提取了无 hardlink 的 app 子树。静态 `/etc` 比较直接读取 tar 成员，没有把归档 `/etc` 提取到宿主。未来恢复必须先完整恢复 app，再按显式白名单恢复 delta 并验证两端同 inode、内容、类型与 mode；不能将 hardlink 静默改为普通副本。处理原路径类型变更时也必须避免跟随旧 symlink 写入其他目标。`/root/.lesshst` 不属于测试输入，无需恢复或披露。

## 冻结来源与后续唯一执行方案

JSON 记录 30 个小文件绑定并在准备结束统一复核不变：原 result/config/归档/快照/日志/轨迹、task instruction/tests/Dockerfile/task.toml、470 条脚本 `source_inventory.json`、相关 frozen runtime 模块及实际 Harbor 核心模块。`runtime/artifacts` 是指回 `R/artifacts` 的 symlink；Harbor 实际源码位于 `R/artifacts/benchmarks/harbor/src/harbor`，不能误称其全部包含在 470 条脚本快照中。SIF stat 身份保持不变。

原 verifier cache map 已绑定，`git-leak-recovery` 的 `ready=true`，指向 `artifacts/tools/terminal_verifier_offline_20261016/group-caches/group-00`；原 native/verifier-bin/uv-wheel/python、core-uv-cache、uv-installer 与 server/runtime Python 路径均存在。本轮没有安装、重建、递归哈希 cache 或证明其全部可执行；真正运行仍需沿原冻结供应链验收。

若 root 后续批准，只能另建一次独立 grade-only 输出，复用冻结 `runtime/scripts/run_terminal_repair_grade_v2.py` 与原 config/task/SIF、原答案 archive。使用词法 Harbor venv、原 PATH/PYTHONPATH/XDG/DBus 与已有 verifier cache；0 solver/model 调用，原 **4CPU、8192MiB、900s verifier**，原 build 上限 600s。唯一 parent 必须在 `R/artifacts/eval/direct_asi_grader_cpu92_95.lock` 的排它契约下取得 root 准备的实际租约，并用可见 guard；物理 92–95、相对 offset 0，先后检查实际 scope，不能仅看空 scope 认领，也不能改 ASI/Terminal marker。

建议新准入至少保留 **2400s** runway（600s build + 900s verifier + 至多 300s 审阅后的恢复 + 600s 排空余量），以 10/18 02:20 CST core 截止计，最晚 01:40；若实际恢复命令上限更大，应前移 gate。等待锁期间与 spawn 前均需核 gate，不截断已准入的原 900s。运行后须检查原 bytes、restore 返回、测试实际开始、native reward/异常、双 scope 排空、guard 退出及锁释放，再由 root 决定是否接受独立 native；不得自动记 0 或接正式 summary。

机器收据：[terminal_git_leak_grade_only_preparation_20261017.json](source_snapshots/terminal_git_leak_grade_only_preparation_20261017.json)。80 原始静态收据为上述独立临时目录的 `preparation.json`；fsck/unsquashfs stdout/stderr 也仅保留于该目录。无 native、service、claim、driver、API/GPU 或正式源变更。
