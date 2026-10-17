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

## 10:14：独立 driver 已准备，尚未准入

root 10:09 授权仅准备代码后，新增 [driver](../scripts/run_terminal_git_leak_grade_only_20261017.py) 与 [固定 manifest](../configs/eval/terminal_git_leak_grade_only_20261017.json)。上文“无 driver”描述的是 09:27 的静态阶段；**当前仍没有执行 claim/guard、取锁、native、任务服务或模型/API 调用**。没有改旧 nginx/SWE/runtime/source 或正式 summary。

80 上 10:14:55 CST 的默认 prepare 实际通过：33 个小文件来源绑定、原模型/seed/checksum/资源、同 SIF stat、原 Git 静态收据与 cache 路径均核验；当时 `priority_swe_drained=false`、`priority_asi_ready_for_grader=false`、Terminal 未接管 grader 核。默认 prepare 可在 SWE 仍在途时审核，不等待或取得租约。AST 与原词法 venv 的 frozen CLI `--help` 通过，均没有创建环境。

独立根为 `R/artifacts/recovery/terminal250-git-leak-seed1-grade-only-20261017`。`prepared/restore.json` 为 5432 bytes，SHA256 `95017a6bc858485ac831c8c21602c171e65971f4f7b0c3ddba56ffc0d9073123`；`prepared/etc-delta.tar` 为 112640 bytes，SHA256 `3031a95335ee6262b81a8184704d0365f9e1079602166422d13edaa4b64cbee0`。delta 直接保留原 tar 的 23 项 metadata，硬链成员仍指向原 app 成员，没有展开成普通副本，也没有 resolver 或未改 `/etc` 成员。

三条拟执行恢复命令合计上限 240s，仅在未来新同 SIF native 环境内运行：

1. 保存受管理 resolver 的校验值；删除新环境原 `/app`，从原 archive 完整解包 app（90s）。
2. 删除 delta 白名单中的非目录旧项以避免 symlink 写穿；解包仅 23 项 delta，复核 resolver 未变（90s）。
3. 只用挂载的 `/opt/harbor-server/bin/python3 -I -S` 对原 archive 校验全部 50 个 app 成员及 23 项 delta 的类型、mode、内容、链接目标、app 完整名单和跨路径同 inode（60s）。该校验不导入或运行候选代码、不安装、不启动任务服务；随后才由原 frozen CLI 进入原 native verifier。

一次 tiny 合成夹具在 80 使用实际 GNU tar 验证：app 先恢复、delta 后恢复可以保留硬链；普通复制会被同 inode 检查拒绝（RED）；替换旧 symlink 不改变其原目标，resolver 保持原样。该夹具没有使用候选内容，也不是官方测试/容器/native。具体夹具执行秒未单独计时，只保留其在本次 prepare 会话、最终 preflight 之前完成的事实。它证明的是解包拓扑处理，不证明原任务或 native 环境成功。

生产环境显式采用词法 `R/artifacts/envs/harbor/bin/python`（不 resolve 到底层 Python），PATH 前置原 Apptainer1.4.5/fakeroot1.25.3；PYTHONPATH 为原 `terminal250_full445_20261017/runtime/scripts`，XDG `/run/user/1012`、DBus `unix:path=/run/user/1012/bus`，BLAS 三项线程数均 1。host TMPDIR 固定 `/data/caoqinlu/tg1`；依 frozen `apex_baseline_net_` + 8 字符随机后缀构造的 control socket 为 **58 bytes <108**，未为此启动 namespace/server 或做 native smoke。child 固定 taskset 物理 92–95、相对 `--cpu-offset 0`，原 4CPU/8GiB/900s 不变。

未来只有 root 现场核定临时窗口后才可用显式 `--execute` 一次启动；无额外 root 授权文件、动态 scheduler 或自动 retry。唯一 `attempt1` 目录创建即占用一次执行机会。执行分支等待 SWE1765416 真实退出、状态中的双 native 空/guard stop/双全 scope 空及解锁；在取得 global EX 前和 spawn 前检查 ≥2400s runway、Terminal 尚未接管、AVG ASI 尚未进入评分就绪阶段。若 AVG `generation_cpu_finished.json` 已 finished 而 allCPU 尚未 finished，则让 ASI 优先并停止新 native；已准入后不缩预算。取得同 global 锁后创建可见 92–95/32MiB guard、核实际 affinity/memory/swap，再发唯一 frozen grade child。正常或 observer 异常路径都先等 child 自然结束、两次 native 空，再停 guard、两次全 scope 空，最后解锁，不写任何 CPU completion marker。

准备命令（只有独立 artifact 写入，无取锁/claim）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/data/caoqinlu/projects/apex-takehome/scripts \
taskset -c 10 /data/caoqinlu/projects/apex-takehome/artifacts/envs/harbor/bin/python \
  /data/caoqinlu/projects/apex-takehome/scripts/run_terminal_git_leak_grade_only_20261017.py
```

**本轮不得添加 `--execute`。** root 若后续准入，parent 应在普通宽 CPU cgroup 下运行（可仅 affinity10，不能 AllowedCPUs10），并另记唯一 root-launch PID/startticks/SHA 收据；正式原答案仍只有这一个独立 native 机会。native 结果保持 `pending_root_review`，不自动接 collector 或主分。

最终 driver SHA256 `e0ad3fb1a72dc5a9db597611de3cd8ac8690ab9a61c33f212a9c13c1ce71da6c`；manifest SHA256 `db12c5b04fd4815b424a467b2f78da99ed0cc5a3cf5fa987a5a5e755f337625b`。新增 [driver prepare 收据](source_snapshots/terminal_git_leak_grade_only_driver_preparation_20261017.json) 记录实际 default/CLI preflight、artifact hashes 与 attempt/native/claim 均不存在。以上尚未证明实际恢复、缓存启动或官方评分成功；发生失败必须保留原错误并交 root 审核，不能泛化重试。
