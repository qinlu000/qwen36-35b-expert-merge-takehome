# Terminal新增未决评分库存（10:28原始快照）

只读原summary/result/归档stat，无新生成、容器、测试或Judge。各项原null保留，不因1800s求解超时或背景进程就按900s评分计算超时派生0。

|模型|任务/seed|原异常/评分问题|归档字节|处理状态|
|---|---|---|---:|---|
|terminal250|nginx-request-logging/seed0|RuntimeError|727040|原raw保留；既有exact native0 overlay|
|terminal250|torch-tensor-parallelism/seed0|AgentTimeoutError|686080|未决|
|terminal250|train-fasttext/seed0|pytest wrapper returned zero reward without evidence that tests executed|305029120|未决|
|terminal250|git-leak-recovery/seed1|RuntimeError|829440|10:29原答案首次官方5/5通过，root接受native1；collector接入中|
|terminal250|reshard-c4-data/seed1|RuntimeError|1650954240|未决|
|terminal250|sanitize-git-repo/seed1|RuntimeError|missing|无最终归档，不能按原候选自动恢复；记录待讨论|
|terminal250|train-fasttext/seed1|pytest wrapper returned zero reward without evidence that tests executed|305018880|未决|
|avg64|torch-pipeline-parallelism/seed0|AgentTimeoutError|10690560|未决|
|avg64|torch-tensor-parallelism/seed0|RemoteProtocolError|686080|未决|
|avg64|train-fasttext/seed0|pytest wrapper returned zero reward without evidence that tests executed|305039360|未决|
|avg64|qemu-alpine-ssh/seed1|RuntimeError|missing|无最终归档，不能按原候选自动恢复；记录待讨论|

两项无归档为专家sanitize-git-repo/seed1及AVG qemu-alpine-ssh/seed1。没有据工具轨迹重建候选、重生旧答卷或伪造归档。reshard-c4-data/seed1原归档约1.65GB，需先核环境/外部产物/恢复完整性与真实评分CPU租约；不盲套git-leak或nginx清单。

git-leak恢复仅纠正已证明的单一硬链tar header权限校验冲突，原候选未chmod/拆链/改内容，见[实际执行](terminal_git_leak_header_mode_recovery_execution_20261017.md)。其余问题没有获得新的native准入或评分结论。

[机器快照](source_snapshots/terminal_invalid_inventory_20261017_1030.json)保留原路径、时点、来源SHA及统计，不能把该动态库存当最终coverage。
