# reshard/seed1 原答案 grade-only：11:27 在途收据

本轮只读观察 root 唯一启动的执行。没有修改冻结 parent/preparer/manifest、restore、候选、HF输入、网络、原结果或正式summary；没有新claim、重启或第二次native。机器证据见 [terminal_reshard_saved_grade_execution_20261017.json](source_snapshots/terminal_reshard_saved_grade_execution_20261017.json)。

Root 在2026-10-17 11:25:41 CST启动 parent2394544/start870656591，child2394547/start870656770。Canonical launch为80项目 `artifacts/recovery/terminal250-reshard-c4-seed1-grade-only-20261017/root-launch-20261017.json`；本轮采集11:27:11，parent仍 `native_running`、独立lease持有中，native结果尚不存在。

三份 `attempt1/native/restore-command-{0,1,2}.json` 均return_code0：命令0恢复完整原app及4external；命令1恢复10项原etc delta，resolver校验OK；命令2明确报告19845个成员严格通过（app19831、external4、etc10），原内容/权限/类型/链接、完整app名单及managed resolver全同，`candidate_code_executed=false`。没有git-leak特殊模式修正、依赖/产品安装或候选重建。

实际原生scope为 `apex-baseline-bee473b7e72b.scope`，所见进程affinity均124–127，cgroup MemoryMax=8589934592、swap0；memory.events中oom/oom_kill/oom_group_kill均0。可见lease guard `apex-baseline-terminal-saved124-2394544.scope` 同124–127，32MiB。Parent元数据在CPU10；900s verifier timeout来自绑定原配置与冻结grade CLI，不是把32MiB guard误称执行内存。

冻结CLI在三条恢复成功后按原PUBLIC verifier阶段运行。`attempt1/native/verifier/test-stdout.txt` 已有真实pytest启动证据：Python3.13.9、pytest8.4.1、`collected 1 item`，进入 `/tests/test_outputs.py`。原cache map仍group20，固定allenai/c4的00009输入未替换。当前不能据此声称测试已完成或HF输入已成功获取。

本轮重新核42份小source SHA全部一致；原1.65GB archive与SIF两份size/mtime_ns均一致，未重复大文件hash。冻结parent SHA2a2f31ef…7f1df9、manifest92af3fc0…e759b、preparer3ed35de9…2fa55与root-launch一致。小source核验包含原result/config/task/tests、snapshot、runtime、cache map及恢复包。

仍在途，尚无native reward、CTRF终态、双scope空/stop guard/unlock完成证据，故本轮不宣称成功或清理完成。保留原900s预算让其自然退出；后续只读核真实结果、原source、双native空→stop guard→双全scope空→unlock，再由root独立决定是否接受。任何infra/unknown继续null，raw0不自动纳分。
