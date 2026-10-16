# nginx 原答案补评分准备

2026-10-17 **05:34:31 CST** 完成同 SIF 静态比对。仅在80的metadata CPU10执行Python/unsquashfs，独立scope `apex-baseline-nginx-static-etc-20261017`，MemoryMax=1GiB；结束后 `ActiveState=inactive / SubState=dead / ControlGroup=`。没有创建求解容器、运行verifier、请求模型、安装/启动nginx、改网络或领取92–95。原result和archive等10个绑定小文件执行前后SHA一致。

## 绑定的唯一候选

- 原结果：`artifacts/eval/terminal250_full445_20261017/trials/nginx-request-logging__seed0/result.json`，model=`apex-terminal250`、seed0；task checksum=`888ac1ae711acf0400d8631e2603924d716b3bf3f02012775fb06ba29a75cc83`。
- 原result SHA256：`bc3df94fa93163edb3aef4066615771911db06fe3e5afde32f8900d58b368004`；原tar SHA256：`2d7948649da98fd89b08c0a0761cb15358e09ddc2f98a1ef1c8543e7bdd224e3`，727,040B。原snapshot JSON、config、task.toml、Dockerfile和冻结相关runtime的SHA均写入[独立配置](../configs/eval/terminal250_nginx_grade_only_20261017.json)。
- SIF tag=`artifacts/benchmarks/sif/alexgshaw_nginx-request-logging_20251031.sif`，解析到`artifacts/benchmarks/sif/sha256-693e64431a0dbf45952e8b91a298d54fd60247e501c6623fb8fa3ebc07fc3d3d.sif`。大小65,810,432B，mtime_ns=1792079077942533995，SquashFS offset=40960。本轮绑定既有digest命名路径、symlink和stat；没有重新扫描整个SIF hash。
- 原native reward仍null，verifier未开始；原错误是`Refusing public network after unconfirmed solver cleanup`，不是900秒verifier计算超时。原solver1800秒、4CPU/8192MiB、verifier900秒、65536/8192上下文/输出均由原config确认。

## 静态差分和resolver边界

使用[准备脚本](../scripts/prepare_terminal_nginx_grade_only_20261017.py)从同SIF**只解压etc到独立静态目录**，不执行镜像。逐项比较类型、mode、symlink原目标或文件字节；扫描不跟随SIF的绝对symlink到宿主。原tar仅列目录/读成员字节，未在宿主解包。

原tar483成员，其中etc480；SIF原etc478。**469项完全相同、10项差异、1项运行器resolver排除、0项确证删除**。10项差异是捕获状态与原SIF的差异，不能一概归因模型：

| 路径（均在/etc） | 静态证据 |
|---|---|
| `apt/apt.conf.d/99-apex-rootmap` | 新增27B；冻结`apex_rootmap_bootstrap.sh`本身创建该运行器配置 |
| `dpkg`、`dpkg/dpkg.cfg.d`、`dpkg/origins` | 目录mode 0755→0775 |
| `dpkg/dpkg.cfg.d/docker`、`dpkg/dpkg.cfg.d/docker-apt-speedup`、`dpkg/dpkg.cfg`、`dpkg/origins/debian` | 字节完全相同，仅mode 0644→0664 |
| `dpkg/dpkg.cfg.d/singularity-compat` | 原SIF无此项，捕获52B普通文件 |
| `dpkg/origins/default` | 原SIF为指向`debian`的symlink，捕获为83B普通文件 |

`/etc/resolv.conf`明确排除出delta。冻结`baseline_netns.py:80–81`创建namespace resolver，`baseline_singularity.py:136–137`以只读bind挂载；网络阶段由原`set_public`策略切换。不得用归档resolver覆写这个bind、另改DNS/路由或绕过原cleanup guard。候选自己写出的`/tmp/resolv.conf`仍按原字节恢复为普通文件，**不作为运行器resolver**。

非etc恢复仅3个原归档路径：空`/app`目录、`/tmp/resolv.conf`、`/var/log/apt/eipp.log.xz`。独立`restore.json`提案先移除5个需要重建的原SIF文件/链接，再恢复这3项和20,480B的`etc-delta.tar`；没有盲目解包整个etc。delta保留10项原tar metadata；不新增安装、服务启动或候选答案。原完整前缀只有app/etc，tar不是完整文件系统/进程检查点；原归档、进程记录及安装错误均未显示可恢复的nginx服务，后续不能替候选补装或启动。

80独立输出根为`/data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal250-nginx-grade-only-20261017/`。小型[准备收据](../artifacts/recovery/terminal250-nginx-grade-only-20261017/preparation.json)、[恢复命令提案](../artifacts/recovery/terminal250-nginx-grade-only-20261017/restore.json)及delta已原样取回本地ignored artifacts，供root审阅；没有评分结果。restore JSON SHA=`8307a59b2001e5d59ddc230d36152371072d3b94d47197eb64876d6ecb55cd4c`，delta SHA=`5a27ab1a1d7eef8972c0f8fe1a643b1632d516149f6f4c687ddf971b56784a84`。

## CPU92–95共享锁支持一次排它grade-only

真实锁为80项目下`artifacts/eval/direct_asi_grader_cpu92_95.lock`（device2065、inode90775088）。没有替换/截断/领取它。本轮两次`/proc/locks`观察无holder，05:34:36的native scope交集为空；这些只是瞬时观测，**不是CPU池释放或使用许可**。

现有契约直接支持这种串行消费者：

1. `scripts/run_direct_formal_pipeline.py:163–196`的expert/merged ASI scorer都先取同一`flock(LOCK_EX)`，整个评分阶段保持锁，到scorer退出且92–95的程序scope排空才写自身marker并解锁。merged另等expert的all-CPU marker。direct owner已明确确认其全部现行/拟启动ASI grader均通过此锁，没有旁路独立grader。
2. 既有`scripts/run_terminal_native_gap_queue_20261017.py:69,113–166`已经把Base Terminal grade-only作为同锁消费者：取排它锁、检查92–95交集scope、通过`pass_fds`传给子进程；子进程退出后仍持锁等待容器scope排空才解锁。它不要求整个ASI生成池先结束。
3. 因而本候选可在root批准后用相同锁串行完成一次评分。若ASI已经持锁，必须等待，不中断、不抢占、不把其scope暂空当可用。flock不承诺FIFO；等待多久未知。

## 一次parent已批准并持久等待

[一次性parent](../scripts/run_terminal_nginx_grade_only_20261017.py)已经实现，复用上述Base queue的`busy_scopes/now/save`，**不直接运行其硬编码六题main/plan**。默认只做pure checks；root逐段审核后明确批准唯一一次`--execute`。parent先重新校验绑定文件、唯一输出不存在和原4CPU/8192MiB/900秒；打开原锁文件并取LOCK_EX，随后检查所有原生`apex-baseline-`/`apex-asi-`/`ai4sci-submission-` scope是否与92–95相交。若忙，解锁等待，不影响原owner。

取得锁且实际scope清空后，parent用`pass_fds=(lease.fileno(),)`启动下面的**已审阅固定child argv**。沿用原Terminal parent的Python、PATH、XDG/DBus及冻结470 runtime的PYTHONPATH；无模型endpoint探测或调用。child Python进程affinity为92–95，环境原有资源scope仍强制4CPU/8GiB。租约parent只做metadata，不进入待排空的native92–95 scope，避免把自身误当未退出consumer；也不能把parent放进仅AllowedCPUs=10的cgroup后尝试让其child越过该限制。当前child尚未spawn：

```text
taskset -c 92-95 \
  /data/caoqinlu/projects/apex-takehome/artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12 \
  /data/caoqinlu/projects/apex-takehome/artifacts/eval/terminal250_full445_20261017/runtime/scripts/run_terminal_repair_grade_v2.py \
  --original-result /data/caoqinlu/projects/apex-takehome/artifacts/eval/terminal250_full445_20261017/trials/nginx-request-logging__seed0/result.json \
  --restore-manifest /data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal250-nginx-grade-only-20261017/restore.json \
  --output /data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal250-nginx-grade-only-20261017/native-grade \
  --cpu-offset 92
```

parent等待child退出，继续持锁直到**两次**92–95 native scope交集为空并记录child exitcode、PID/startticks、scope/cgroup证据；才释放租约。失败/孤儿scope未排空则保留锁/状态并通知，不以shell命令返回就宣告释放。不会写ASI或Terminal正式队列的CPU完成marker，也不会改96–127生成池、原queue ledger、原result或聚合来源。原生verifier首次开始后最多900秒；恢复/setup预算单独有界，不增加solver预算。只运行原冻结verifier依赖路径，不补nginx产品状态。

parent已于 **05:40:53 CST** 唯一持久启动，PID=`851972`、startticks=`868587717`，普通affinity=[10]，没有AllowedCPUs=10的cgroup限制。原子`execution-claim.json`拒绝重复尝试；独立根下保留`parent-launch.json`、`parent-state.json`、`parent-events.jsonl`、`parent-launch.log`，child启动后另有`native-child.log`。执行脚本SHA256=`7151e8bb2fcbbea5206ace027fa20ad9aef7df88b1e0b47ea4f1462b086f10fb`。

root另要求的核心截止准入门已在**等锁循环**和**锁后child spawn前**两处实现：距离北京时间2026-10-18 02:20不足1800秒则`stopped_core_runway`退出，不再启动新native；已经开始的原900秒verifier不会被该门中断。

**05:47:55 CST当前收据**见[执行快照](source_snapshots/terminal_nginx_grade_only_execution_20261017.json)：仍为同一PID/startticks、state=`waiting_shared_cpu_lease`、`lock_held=false`。共享锁实际由PID3237024的原direct pipeline持有，92–95另有真实ASI程序scope，因此没有抢占/提前宣告释放。12项原source/restore/delta绑定SHA全部仍一致；native目录、result、test stdout和reward文件均未创建，**native尝试0次、模型调用0、未接入正式summary**。没有重启第二个parent或自动重试，没有改ASI marker/96–127生成池。

这只记录上述采集时刻，不承诺锁何时可用或评分一定完成。heartbeat继续接管已有parent，不重复启动。后续即使执行成功也只产生独立native result；是否可收为有效native0/1仍须root核验同一候选恢复、restore返回码及实际测试证据。setup/依赖/恢复失败继续null，绝不根据预期失败人工填0。
