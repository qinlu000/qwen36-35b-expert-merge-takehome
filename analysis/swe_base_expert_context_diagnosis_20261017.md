# Base／SWE专家／AVG64原生成记录对照

2026-10-17，只读已有51×3条生成记录，不重生成、评分或修改服务/权重。数据见[全153条小元数据](swe_base_expert_context_diagnosis_20261017.json)。只读取轨迹info、末request metadata与trial捕获日志；后续3代表例独立读取已有messages，见[重复动作及短观察](source_snapshots/swe_repeated_read_commands_20261017.json)。

|51任务|Base|SWE专家|AVG64|
|---|---:|---:|---:|
|空patch|3|43|34|
|明确context_budget_exceeded|18|34|11|
|Submitted退出元数据|10|0|1|
|退出元数据unknown|23|17|39|
|日志patch capture failed|0|0|0|

unknown来自原空白字段，不猜测Submitted或具体超时。Base原通过10题里，Base/专家/AVG的空patch为0/8/5，上下文拒绝为3/5/2；Base有3个拒绝后仍通过，不应把guard等同有效0或评分基础设施失败。各条生成路径、request路径/精确token数、patch字节与trial异常在JSON中。

三条专家空patch＋unknown的代表已有轨迹：Ansible d624、Teleport654、OpenLibrary630，同一条只读命令分别重复106/162/205次，最大连续106/160/205；各121/175/232个bash，返回rc0为118/175/228。没有工具JSON解析失败，0条/testbed或patch.txt命令，原捕获日志明确0字节。

**rc0并不等于子命令成功。** Root独立核已有tool观察：Teleport重复grep把-r和--include当文件名报错，OpenLibrary重复ls访问不存在的嵌套路径；因接head管道仍rc0。Ansible则重复相同目录内容。模型没有根据已经返回的内容改用新动作，支持重复搜索/错误恢复失效的行为解释，而不是所有工具HTTP不可用或捕获异常。三例终止元数据依然unknown，本轮不据此自动断言全部1800秒超时。

所有模型相同固定64K/8K及SWE guard实现，不存在本轮发现的专门缩小专家context配置。服务副本、并发及排程的历史差异仍需披露，以上行为比较不隔离纯权重因果。更多训练层面边界见[协议诊断](swe_sft_protocol_diagnosis_20261017.md)，总体解释见[下降诊断](swe_regression_diagnosis_20261017.md)。

本轮未发现足以证明所有空patch都是提取问题的日志：153条capture failed计数均0，3重点例明确捕获0。不过这不是证明每份非空patch都由模型正确编辑；环境/生成文件变更仍可能进入patch。
