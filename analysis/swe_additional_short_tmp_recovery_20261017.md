# SWE追加三项：短TMPDIR启动恢复准备

本轮只修复09:18唯一cohort的环境启动边界。旧三项attempt1、全部原source和正式summary保留；这不是按reward重试，旧启动结果均为null且agent/verifier尚未开始。[原执行记录](swe_additional_grade_only_execution_20261017.md)不改。本轮**未执行恢复native**，等待root审阅后的唯一启动决定。

## 先归档失败源码，再最小修改

09:22:08 CST在80先核旧parent1738438、children1738451/52/53均退出，92–95相关scope=[]、global锁无内核holder，guard已停止。其后才将实际失败的script和manifest写入：

`artifacts/recovery/swe-additional-grade-only-20261017/cohort-attempt1/frozen-source/`

归档文件SHA同时匹配原`root-launch-20261017.json`和`cohort-attempt1/execution-claim.json`，归档后重新校验一致。索引和准确路径保存在[本轮小收据](source_snapshots/swe_additional_short_tmp_recovery_20261017.json)的`source_archive`，80原位还有`archive-receipt.json`。不重复把360行旧源码加入Git；归档目录未覆盖。

| 身份 | SHA256 |
|---|---|
| 归档失败script | `197184f50fd10f92a46ed29bc10c50b88d4b5adfdec07f177790248d9dc38b6d` |
| 归档/原manifest（未改） | `7156a584a50340c2661efe6569d0c11528b90b6d871bcf4cf0557ce7406ac151` |
| 新冻结script | `7da575a63c408d49727ff52493a0b8b203cd139456db8bdd17bae32b32ea8ace` |
| 新恢复manifest | `b6dcd8442b336e9916d443e4ca7afe80fce2b3252723b00e8c2bc65c1fe2a138` |

[源码](../scripts/run_swe_additional_grade_only_20261017.py)与归档逐字比较，**恰好两行修改**：

```diff
-    env['TMPDIR'] = str(ROOT / item['output'] / 'host-tmp')
+    env['TMPDIR'] = item['host_tmp']
-    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/swe_additional_grade_only_20261017.json')
+    parser.add_argument('--manifest', type=Path, default=ROOT / 'configs/eval/swe_additional_short_tmp_recovery_20261017.json')
```

[新manifest](../configs/eval/swe_additional_short_tmp_recovery_20261017.json)只改变顶层及三item的输出根，并增加三个`host_tmp`。实际反向还原这些字段后与旧manifest JSON完全相同；`code_sha256`和所有原source绑定均不动。新输出根为`artifacts/recovery/swe-additional-short-tmp-20261017`，三项仍各自保留原taskID/attempt1及独立claim、scratch、native namespace。原manifest字节仍与归档一致。

## 真实socket反馈与default prepare

09:23:12 CST在80 taskset CPU10执行metadata/socket检查，未设cgroup AllowedCPUs10。三个固定短目录各创建一个独立`apex_baseline_net_<随机8字符>`子目录，执行真实`socket(AF_UNIX).bind(control.sock)`，随后close、unlink并仅删除本次子目录；短base目录保留，不删除任何旧source/attempt。未启namespace、container或测试。

| item | child TMPDIR | control.sock字节 | model.sock字节 | 真实bind |
|---|---|---:|---:|---|
| swe249/nodebb | /data/caoqinlu/apex-grade-tmp/e-nodebb | 78 | 76 | GREEN |
| swe249/teleport2b | /data/caoqinlu/apex-grade-tmp/e-teleport2b | 82 | 80 | GREEN |
| avg64/teleport2b | /data/caoqinlu/apex-grade-tmp/a-teleport2b | 82 | 80 | GREEN |

control.sock实测均小于Linux `sun_path[108]`；model.sock在同一真实子目录按其实际路径字节计算，也小于108。修复通过child Popen的`production_env`传入TMPDIR，真实网络临时目录会沿该位置创建；仅缩容器scratch不能解决原错误。本次未改变scratch逻辑。

随后实际运行词法`artifacts/envs/harbor/bin/python scripts/run_swe_additional_grade_only_20261017.py`默认入口，返回0、stderr空、mode=prepare_only；三项各38个绑定、named环境scratch/schema、CPU92/93/94、logical0、1CPU/4096MiB/3000秒检查通过。原PatchReplay1800秒、Go prep计入原verifier总预算、musl shim、DBus/PATH、网络策略及全部候选/测试保持。完整机器侧preflight收据位于`artifacts/preflight/swe_additional_short_tmp_recovery_20261017.json`。

preflight核新输出均不存在；没有创建execution claim、guard或取得global锁，没有native、模型/API调用。进程扫描只排除本次metadata命令自身祖先，未发现任何旧/新cohort残留进程。AF_UNIX bind的GREEN证明这条短路径可绑定，**不证明原NodeBB/T2超时或无reward已修复，也没有产生新的有效分数**。

本轮owned变更为上述script、新manifest、本文件和小JSON；两文件SHA二次冻结后不再编辑。root另审是否唯一execute。Git/claud由root统一处理。

## Root后续唯一执行：09:24:49启动，尚无恢复分数

以上prepare-only历史保持。root/direct PASS后，root于09:24:49 CST唯一启动恢复cohort：PID **1765416**、startticks **869931371**。机器侧启动收据为`artifacts/recovery/swe-additional-short-tmp-20261017/root-launch-20261017.json`，其小元数据已嵌入本轮JSON的`root_execution.launch_receipt_small`。本agent未execute或重启，冻结script `7da575a6…ea8ace`、manifest `b6dcd844…e2a138`未修改。

09:25:08实际核验parent仍在，affinity92–95，状态native_running；内核FLOCK WRITE holder确为1765416。共同guard实际scope为`apex-baseline-swe-additional-1765416.scope`，affinity92–95、MemoryMax33554432、swap0。三个Harbor child controller仍在login session cgroup，**每题4GiB限制实际施加于各自native scope**，没有把controller的session memory.max误称为每题限制。

| item | child PID / startticks | child实际affinity | 实际native scope | 09:25:31阶段 |
|---|---|---|---|---|
| swe249/nodebb | 1765421 / 869931534 | 92 | apex-baseline-649dae5c3168.scope | 原patch apply_rc=0；原test.sh/npm mocha/node verifier在途 |
| swe249/teleport2b | 1765422 / 869931534 | 93 | apex-baseline-994fbdaf2bb2.scope | 环境启动内原Go module cache复制在途；未观察到replay/verifier |
| avg64/teleport2b | 1765423 / 869931535 | 94 | apex-baseline-3212acbece62.scope | 同上 |

09:25:51遍历各native scope实际进程，CPU union分别92、93、94；三者`memory.max=4294967296`、`memory.swap.max=0`。两T2实见`cp -a /go/pkg/mod/. /tmp/apex-native-go-module-cache`，分别运行于93/94，沿原cache复制逻辑执行。各自`repair-runtime.json`均return_code0、/tmp位于/data盘，原namespace relay/server启动边界已通过。NodeBB已有原replay和verifier日志；当时三个native result均未终态，因此**不声称有效评分或分数已恢复**。

T2该次采样memory.current分别4293332992B（专家）、4292927488B（AVG），接近固定4GiB；memory.events.max分别8467/8611，但oom、oom_kill均0。这说明有内存回收压力，不能凭此提前判失败，更未放宽预算。NodeBB该次memory.current840646656B、max事件0。小JSON仅保留scope/count/CPU union/少量pid样例与实际cgroup计数，不收整棵进程树。

三项各38个原输入SHA及SIF大小/mtime再次一致，旧失败attempt1与原source保持。未修改正式summary，没有新模型/API请求。本段只是启动与在途资源核验，后续是否完成仍需原生终态证据。

09:28:12 root再次独立只读核验：parent1765416/start869931371仍为native_running且持锁，三个child实际affinity仍分别92/93/94；池内只有上述三个native scope与自有guard，三个result均尚未终态。没有重复启动或提前接分。
