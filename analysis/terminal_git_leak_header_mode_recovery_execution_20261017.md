# git-leak原答案：首次官方native评分通过，待root接受

root与merge审阅a130/e56b并fresh核42来源/资源后，于2026-10-17 **10:29:46 CST** 唯一启动parent **2189065/start870321012**，child **2189141/start870321142**。原冻结候选首次实际进入官方测试，**5项全通过、native reward=1.0、无Harbor异常**。本审核不修改collector或正式summary，结果仍待root独立接受；没有重复启动或新模型/API调用。

项目根 `R=/data/caoqinlu/projects/apex-takehome`，独立根 `O=R/artifacts/recovery/terminal250-git-leak-seed1-header-mode-recovery-20261017`。启动收据为 `O/root-launch-20261017.json`。冻结wrapper SHA256 `a13001baf6656973a9553d78a0b107ca36ee5035023c48992ce02dca18c5b447`、manifest SHA256 `e56b4e8327ba748d72f37e77bce1ec8c46dec1ee85b633087720f34dc90494c0`及e0ad parent保持不变。

## 恢复与严格校验实际成功

`O/attempt1/native-grade/restore-command-{0,1,2}.json` 全部rc0、stderr空。命令0/1逐字沿用原95017 restore，仅恢复原app和原23项etc delta；命令1明确 `/etc/resolv.conf: OK`。命令2实际输出：

- restored_members_verified=73，app_members=50，etc_delta_members=23。
- cross_path_hardlink_verified=true，完整app名单及全部type/hash/link检查通过。
- exact_hardlink_header_mode_normalized=true，raw_alias_mode=0644，canonical_regular_mode=0600。
- candidate_code_executed=false（指恢复校验阶段）。

唯一特殊处理是前一诊断已证明的互斥tar header：`/etc/apt/apt.conf.d/01-vendor-ubuntu`硬链header0644，而其普通target `/app/repo/.git/info/refs` header0600；实际单inode0600。新checker固定exact archive SHA/路径/mapping/raw0644/target600，只将该alias的mode预期取canonical600。没有chmod候选、拆硬链或泛忽略mode，其余72项mode原样严格校验。原header冲突及此前两个测试前停止结果都保留，不能称原tar所有metadata天然一致。

## 原测试与结果

官方原 `tests/test.sh`/`tests/test_outputs.py` 已实际运行，`verifier/ctrf.json` 为5 tests、5 passed、0 failed/skipped/pending；pytest摘要 `5 passed, 1 warning in 0.13s`，`verifier/reward.txt`为1。原候选分别通过以下官方断言：

1. flag文件存在且正确。
2. commit历史不含secret。
3. 要求保留的good commits仍存在。
4. unreachable Git对象不含secret。
5. repository内容checksum满足要求。

这说明原已归档候选满足这五项测试条件，不推断模型具体推理过程或训练因果。没有输出secret、答案、Git blob或gold/hash值。

完整结果路径为 `O/attempt1/native-grade/result.json`，SHA256 **`f7b9cd361ddaaa2d55362a501fdf43cc4adf63a4fc91ee14b4c6c5e50d5bab0b`**，finished_at **10:29:53.271721 CST**。模型 `apex-terminal250`、seed1、task checksum `da0aeda47b324bff84c67faa3d8bed3b3b5f1200e3b17cecbc7dc8f802fd366a`；`verifier_result.rewards.reward=1.0`、exception为空。原正式result中的cleanup guard/null及原archive保持不变。

## 资源、源字节与完整释放

实际child argv使用词法Harbor venv、taskset物理92–95、相对offset0和同frozen grade CLI。新result配置仍4CPU、8192MiB、GPU0、CPU/memory enforcement均limit、原verifier900s；没有新的solver执行。parent记录可见guard实际affinity92–95、32MiB/swap0，该32MiB不等于native8GiB。测试结束很快，未另外采到live native cgroup/memory.events，故这些事件计数未知，不能冒称实测OOM=0。

10:30:52 CST独立复核**44个claim绑定全部不变**，包括原答案/result/config/task/tests、原archive、冻结源码、旧失败/诊断证据及新payload。SIF resolved路径、92987392 bytes、mtime_ns1792079169674202869均匹配；未做大文件全hash。每题原资源/预算未放宽，没有安装、候选重建或任务服务。

parent记录child rc0、state `finished_pending_root_review`，完整释放顺序为：native scope双空 **10:29:55.500549、10:29:57.564530** → 停guard → 全scope双空 **10:29:57.631604、10:29:59.715160** → **10:29:59.794535解锁**。随后父子均不存在，10:30:50.732691和10:30:52.799224两次独立scope空；global锁inode90775088在capture时无holder，审核没有获取它。没有写ASI/Terminal completion marker或改变队列。

机器收据：[terminal_git_leak_header_mode_recovery_execution_20261017.json](source_snapshots/terminal_git_leak_header_mode_recovery_execution_20261017.json)，含root-launch/parent状态、三条恢复返回、原测试计数与安全test名称、44绑定和清理证据；80副本为 `O/execution-review.json`。本轮不接入正式分，交root独立审原result/tests/来源后决定exact只读overlay。

## Root独立接受与只读汇总（10:38 CST）

Root已在80独立读取actual result/config/CTRF、恢复命令2的73项证明、parent完整排空状态和execution claim；44个绑定再次逐项相等，官方5个test函数名与CTRF一致。明确接受**这一份git-leak-recovery/seed1 native1**，不是以预期通过补写reward。原SIF/答卷/原cleanup guard null均保持。新的manifest显式记录唯一key/model/seed及证据；collector保留原nginx0分支，仅追加这一条1，其他score row严格相同。

17个人工检查在root再次执行通过，包括旧manifest兼容、原null保留、native1、来源/seed/model/测试缺失拒绝和null stderr。真实helper-only验收不写原summary。10:38:31依序专家SWE→AVG SWE→Terminal collector→统一strict/预算双视图后，Terminal专家177/445有效、5invalid，AVG165/445有效、4invalid，所有source issues空，仍不报完整主分或macro。新[固定快照](source_snapshots/formal_aggregation_20261017_1039.json)保留时点；以上不回写10:30的独立执行snapshot。
