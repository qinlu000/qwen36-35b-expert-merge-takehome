# SWE追加三项：唯一cohort执行核验

root和direct独立审核后，root于**2026-10-17 09:18:02 CST**唯一启动cohort（PID `1738438`，startticks `869890604`）。本agent仅只读核验；没有再次执行、修改冻结源码/manifest、重试或接入正式分数。[准备历史](swe_additional_grade_only_preparation_20261017.md)仍保留prepare-only事实；后续实际执行与启动失败记录在本文件和[小收据](source_snapshots/swe_additional_grade_only_execution_20261017.json)。

**三项均在环境启动阶段失败，reward为null；原答案与verifier尚未开始。** Harbor捕获异常后child返回码为0，不能将该进程返回码解释为评分成功。

| 精确项 | child PID / startticks | 启动物理CPU | 原生开始—结束（CST） | 结果 |
|---|---|---:|---|---|
| swe249/nodebb | 1738451 / 869890770 | 92 | 09:18:04.182—04.399 | RuntimeError: Namespace relay exited；null |
| swe249/teleport2b | 1738452 / 869890770 | 93 | 09:18:04.167—04.341 | 同上；null |
| avg64/teleport2b | 1738453 / 869890770 | 94 | 09:18:04.190—04.363 | 同上；null |

09:18:27只读采集时parent及三个child已不存在。实际子命令为taskset 92/93/94；过早退出使本次未能在`/proc`直接采样child affinity。原生trace在创建native systemd scope之前中断，因此**没有把配置中的每题1CPU/4GiB写成已观测native cgroup**。共同guard实际记录为`apex-baseline-swe-additional-1738438.scope`，PID1738444 affinity92–95、MemoryMax33554432、swap0。

## 启动错误证据与最小后续方向

三条原始result均显示调用链：Harbor `Trial._prepare` →环境`_start_server` →`baseline_singularity.py:134` →`baseline_netns.py:98`，后者在relay进程退出时抛出`Namespace relay exited`。`agent_execution`和`verifier`字段均为null，各自`pending-root-review.json`明确`accepted_into_formal_summary=false`、`new_model_calls=0`。该错误不能用来裁定候选正确性，也没有验证旧NodeBB/T2超时或无reward的根因是否修好。

已只读确认一个确定的路径构造错误：新脚本35行将`TMPDIR`设为包含完整taskID的每项`attempt1/host-tmp`，长度分别223、232、231字节；`baseline_singularity.py:123`在其下创建`apex_baseline_net_XXXXXXXX`，`baseline_netns.py:82,140–142`再绑定`control.sock`。所得socket路径长度分别**263、272、271字节**，而80本机`/usr/include/x86_64-linux-gnu/sys/un.h:32`明确为`char sun_path[108]`。此构造无法作为Linux pathname Unix socket使用，与全部relay在启动即退出相符。清理已删除network临时目录，原底层`network.log`不再存在，所以本记录**不虚构未保留的OSError原文**。

最小后续修复方向是独立、短且可归属的TMPDIR，保留每项scratch/native输出独立；无需改变原patch、SIF、测试、Go/依赖、网络策略或3000秒预算。当前源码和attempt1冻结，本轮未修复或重跑；是否做新的唯一启动需root另审。

## 原输入与安全释放

每项38个小文件SHA绑定均通过实际复核，原SIF路径/大小/mtime未变；冻结脚本SHA `197184f50fd10f92a46ed29bc10c50b88d4b5adfdec07f177790248d9dc38b6d`、manifest SHA `7156a584a50340c2661efe6569d0c11528b90b6d871bcf4cf0557ce7406ac151`保持。

父状态最终为`finished_pending_root_review`。09:18:08.760和09:18:10.828两次native scope为空后停止自有guard；09:18:10.895和09:18:12.973再次确认完整scope为空，于09:18:13.037释放global92–95租约。09:18:27采集时`direct_asi_grader_cpu92_95.lock` inode90775088没有内核锁条目，parent/child均已退出，剩余scope=[]。这仅证明该cohort安全退出，不替其他controller宣称永久CPU释放。

唯一root启动收据：`artifacts/recovery/swe-additional-grade-only-20261017/root-launch-20261017.json`；canonical父状态：同目录`cohort-attempt1/parent-state.json`。三个attempt1原生结果完整保留；正式canonical summary和旧source未修改。无模型/API请求，无新有效评分。
