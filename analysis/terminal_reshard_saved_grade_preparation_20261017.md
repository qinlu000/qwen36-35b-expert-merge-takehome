# reshard-c4-data/seed1：原答案 grade-only 固定包（未执行）

Root 授权 prepare-only；11:23:31 CST 在80 metadata CPU10生成固定恢复包。没有 sandbox、candidate、tests、model/API、claim、flock 或 guard。只允许 root/独立review后另行唯一启动。11:10队列/invalid库存另见 [执行状态](execution_status_20261017_1110.md)。

入口为 [prepare_terminal_reshard_restore_20261017.py](../scripts/prepare_terminal_reshard_restore_20261017.py)，配置 [terminal_reshard_saved_grade_20261017.json](../configs/eval/terminal_reshard_saved_grade_20261017.json)。包根为80项目的 `artifacts/recovery/terminal250-reshard-c4-seed1-grade-only-20261017/prepared/`：`restore.json`、`etc-delta.tar`、`pid-source.json`、`preparation.json`。相同小文件副本已保存到本地 ignored 同路径，供审阅；1.65GB原归档与SIF未复制。

## 原状态及绑定

唯一来源为 `artifacts/eval/terminal250_full445_20261017/trials/reshard-c4-data__seed1/result.json`，模型apex-terminal250、seed1、task checksum00cc1fe9…14ae4，原result SHA2f9e2d33…137bb。原cleanup guard在PUBLIC verifier前拒绝，native null，未产生测试stdout/CTRF。配置保持原4CPU/8192MiB、GPU0、verifier900s、build600s、timeout multiplier1。原solver no-network不变；grade-only没有solver/model调用。

42份小文件SHA绑定原result/config/trial.log/snapshot/task/tests、原runtime全部小py/sh与cache map、prep源码/restore/delta/PID证据。原归档1,650,954,240B、SIF1,441,583,104B用已核size+mtime_ns绑定；原归档SHA ae06863c…cf19仅引用最初已采记录。本轮不重复大archive/SIF hash，遵root效率优先要求；此stat策略弱于再次全hash，接受这一明确限制，不冒充内容复核。

systemd原journal精确匹配该trial挂载，绑定旧scope `apex-baseline-af8481795ec4.scope`、4CPU/8GiB/offset20和原namespace keeper1778318；只保存journal message SHA及资源布尔，不保存token/完整argv。当前该scope及关联旧trial/net/staging进程为空，net目录已删除。staging只保留 `_hbexec.py`、`bootstrap.sh`、`server.log`，不能把日志目录残留当活namespace。原3个cleanup PID是容器namespace PID；其capture startticks870122605明确标为namespace信息，未谎称已与host PID配对。当前原namespace/scope排空是独立证据。

## 恢复内容与三条命令

归档20,311成员：app19,831、etc476、external4。没有hardlink或特殊节点。恢复整个原app，包括两份原候选脚本、venv、原数据及压缩产物；不重建任何文件。四个app symlink原样保留，唯一绝对目标 `/usr/local/bin/python3.13` 已静态证明在同SIF存在。

四份external原样恢复：`/root/.cache/uv/interpreter-v4/85046238252ff06c/`下3个msgpack（888/896/899B，mode0600）只描述原 `/usr/local` 与 `/app/.venv` 解释器发现路径；`/tmp/uv-1c83b73deef05048.lock`为0字节mode0777。它们不是任务脚本/缺失依赖，也不重建活进程或原持有锁；为了保全捕获状态仍全部恢复。

命令0记录managed resolver摘要，恢复原app和4external。命令1只提取原归档产生的10项 `/etc` delta：rootmap配置、dpkg三目录、dpkg.cfg、docker、docker-apt-speedup、singularity-compat、origins/debian、origins/default；单点先移除原SIF的 `origins/default` symlink，避免跟随链接。resolver完全排除，不恢复全etc、不装包、不执行service。

命令2用原Harbor隔离Python `-I -S`逐项核对19,845个选定成员的原权限/类型/链接及内容，并核完整app inventory和resolver未变。文件比较使用1MiB块，避免把1.63GB app读入内存；这一步未来执行时有必要读取恢复内容，未在prepare执行。无git-leak特殊header正规化或nginx恢复逻辑，无chmod放宽。

原测试所需allenai/c4固定00009输入、原group20 cache map和冻结PUBLIC verifier阶段保留。无需离线证明HF shard完整才能按原阶段运行；如原供应失败，保留infra unknown，不改数据、不加resolver/route、不升级依赖/solver工具、不据零reward自动接受。

## 独立 parent 接口与审核状态

Merge负责 `run_terminal_saved_grade_cpu124_20261017.py`。manifest提供original_result、runtime包根、restore_manifest、pid_source、output根及42小SHA/2stat。仅未来 --execute可建 `output/attempt1`，native放 `attempt1/native`。Root明确124–127已由T774双排空并释放、永久不进入Terminal扩容；该parent复核生成240/shutdown、两Terminal最大CPU123及原T774释放证据，使用独立lease和可见guard，不取92–95 ASI锁。

物理124–127、logical offset0、原4CPU8GiB/900s、词法Harbor venv、短TMPDIR不变。本包minimum_runway=3600s，考虑build、最多1260s恢复命令、900s原verifier及清理，超过root至少2400s门槛。不能缩短已准入预算。自然child退出后双native空、stop guard、双全scope空才解锁；unknown不重试，结果待root审核，不直接进summary。

实际prepare：manifest SHA `92af3fc0d2d809c168fd1177608b2ade81e2c41ab07c030f1219f4f3390e759b`；prep脚本SHA `3ed35de941195c0a248299a053d64c310584e9f9c426424d38d11bdf8972fa55`；restore5fb8f561…0f4、delta0da2b590…fc68、PID5c774e50…3572。第一次纯prepare因为staging日志目录保留而保守拒绝，随后精确区分日志保留与namespace生命期；没有发生native重试。最终prepare GREEN；本地核三命令、10delta/resolver排除及checker编译。Merge独立parent metadata defaultprepare亦GREEN，busy=[]，0claim/lock/guard/native。见 [机器收据](source_snapshots/terminal_reshard_saved_grade_preparation_20261017.json)。
