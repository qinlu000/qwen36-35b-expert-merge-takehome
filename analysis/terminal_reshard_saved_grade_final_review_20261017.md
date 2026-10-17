# reshard/seed1 终态独立审核：保持 infra null

12:08:50 CST只读核验；已读最新claud/current_status及Git HEAD c90add1，未改原文件、collector、summary、冻结代码/manifest或其他WIP。没有重跑prepare、native、API/模型、网络探测或大archive/SIF hash。机器证据见 [终态收据](source_snapshots/terminal_reshard_saved_grade_final_review_20261017.json)。

**没有足够证据将本项接受为有效native0。** 原答案确已恢复并进入官方测试，但失败发生于输入准备，未到达压缩/解压测试主体，继续invalid/null。

- Canonical output：80项目 `artifacts/recovery/terminal250-reshard-c4-seed1-grade-only-20261017/attempt1/native/result.json`。11:33:21 CST结束，raw reward0、Harbor exception null、child returncode0；原result/答案不变。
- 三条restore均rc0；第三条确认19845成员（app19831、etc10、external4）严格内容/权限/类型/链接及app inventory一致，resolver未变、没有执行候选。保留原4CPU/8GiB/900s与冻结PUBLIC verifier/UV group20/固定HF输入。
- 官方pytest collected1，但 `/tests/test_outputs.py:34` 的session fixture `generate_test_data` 请求allenai/c4固定 `en/c4-train.00009-of-01024.json.gz` 失败。原日志记录HF HEAD `[Errno 101] Network is unreachable`及五次退避，fallback缺 `default-c33333bd6ac7ada4`，仅有 `default-b04fc8a0b8562884`。pytest为 **1 error in421.44s**；CTRF将setup error编码为1failed/0passed，不能将其当候选断言失败。原测试主体未进入。
- 原42份小source SHA及2份archive/SIF size/mtime_ns全部一致；冻结parent与manifest亦一致。本轮没有重新全hash大文件。原任务、候选、测试、依赖和HF输入均未修补。

原11:27独立live收据证明native scope `apex-baseline-bee473b7e72b.scope` 实际affinity124–127、MemoryMax8GiB/swap0、采样OOM0。终态parent没有持久保存全程native memory.events/peak，因此不冒称全程峰值或全程OOM0；这里的明确失败证据是数据fixture供应错误，非预算900s耗尽。

完整清理链来自 `attempt1/parent-state.json`：11:33:23.819/25.934两次native空；随后guard停止；11:33:26.059/28.190两次全池scope空；11:33:28.190解锁。parent2394544/start870656591、child2394547/start870656770当前均gone。12:08:48.662与12:08:50.894再次只读观察124–127无相关scope，private lock inode90780234在 `/proc/locks` 无owner。当前空闲不等同本审核授予新租约。

结论：恢复与清理工程链完成，原native raw0保存；评分意义仍为 **infra unknown/null**。不接入正式summary、不自动重试、不更换HF输入或放宽网络。本轮用户已取消小时自动化，后续由root按用户指示处理。
