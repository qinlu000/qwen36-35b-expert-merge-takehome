# Terminal 执行状态：2026-10-17 11:16 CST

本轮仅只读队列、进程、scope、原生结果和静态归档；未生成、评分、重试、修改网络或 CPU 租约。机器收据见 [execution_status_20261017_1110.json](source_snapshots/execution_status_20261017_1110.json)，采集时间 11:16:42。计数来自原 owner summary，未运行 audited collector。

|队列|终态/445|原始有效|原始 invalid|active|pending|唯一 parent|
|---|---:|---:|---:|---:|---:|---|
|Terminal 专家|199|192|7|12|234|489933 / start868194930|
|AVG64 Terminal|183|178|5|11|251|489934 / start868194945|

专家 raw 的 nginx/seed0、git-leak/seed1 已分别获 root 批准独立 native0/native1，原 raw 保留不变。因此本轮未决为专家5、AVG5；192 不能冒充刷新后的 canonical 有效数，也不能将7项全部称为新增失败。

当前专家12槽 offsets=0,4,12..48；AVG11槽=8,52..88。23个实际 Terminal scope 均在0–91。唯一 admission guard1508852/start869510981 正常等待明日01:10截止，两 output 无 STOP_ADMISSION。没有重复 parent 或已就绪却未采用的 stage2：AVG ASI generation 已240/240、worker pool shutdown，但 all_cpu_consumers_finished 仍缺；科学 grader scope 在92，阻止该池交接是合法等待。两 Terminal 未来 stage 均止123。

11:12:54 direct agent 独立核 global ASI flock inode90775088 由 coordinator1126014持有、grader2282159唯一，科学85/240/error0；727856已10:54:16释放。这是同团队只读证据，未重复 claim/扫描。Root 独立核 T774 已双排空、10:55:39解锁，Mac route 已关闭，124–127永久脱离AVG生成；未来 reshard 可另获此独立4CPU租约，不能据瞬空自行认领。

最近60分钟 owner ledger 终态速率：专家26、AVG23。距离明日02:20约15.055小时，尚需246/262个终态，描述性所需均速约16.34/17.40题每小时。当前观察速率高于此均值，但任务长尾、任务组合、stage2等待与 invalid 缺口仍有风险；这里没有线性 ETA 或完整445保证。即使445全部attempt，未决invalid也不能自动变为有效主分。

## 未决库存

|模型|key|证据/状态|
|---|---|---|
|专家|torch-tensor-parallelism/seed0|AgentTimeout、native null；archive有；不能当900s verifier compute timeout|
|专家|train-fasttext/seed0、seed1|native0但无测试执行证据/CTRF，owner明确invalid；不能当有效判错|
|专家|reshard-c4-data/seed1|cleanup guard在原verifier前拒绝；完整archive，见下|
|专家|sanitize-git-repo/seed1|cleanup guard；archive/snapshot皆无，保留null、不重建候选|
|AVG|torch-pipeline-parallelism/seed0|AgentTimeout/null；archive有，但external changed743需另审|
|AVG|torch-tensor-parallelism/seed0|RemoteProtocolError/null；archive有|
|AVG|train-fasttext/seed0、seed1|同上无测试执行证据；seed1是相对10:30库存唯一新增键|
|AVG|qemu-alpine-ssh/seed1|cleanup guard；archive/snapshot皆无，保留null|

## reshard/seed1 静态可恢复性

原 trial 为 `artifacts/eval/terminal250_full445_20261017/trials/reshard-c4-data__seed1`，模型apex-terminal250；result SHA `2f9e2d3309329c6bb26d6c0dbc9116e365b9990f822df562967c7d74834137bb`，原verifier未开始。Snapshot为returncode0、stderr空、complete_prefixes app/etc、captured_before_verifier=true。归档1,650,954,240B，20,311成员：app19,831、etc476、external4，无hardlink/特殊节点。app两份候选脚本与全部原数据/产物均已封存；未执行候选。

同SIF静态/etc比对只有10项差分、0删除；resolver必须排除。`/etc/dpkg/origins/default` 从原SIF symlink变为普通文件，恢复时必须先安全移除该单点，不能跟随原链接。四个app symlink均可解释，唯一绝对目标 `/usr/local/bin/python3.13` 在同SIF存在。外部三份uv解释器发现msgpack和空uv锁不是缺失的产品代码；后续固定包会原样保存。没有需要重启的任务service。

原测试通过datasets读取allenai/c4固定00009 shard，执行原uv/compress/decompress流程；原task cache map group20 ready、原PUBLIC verifier阶段必须保留。未证明该HF shard完整离线存在不构成改输入/放宽网络的理由；若原供应失败应保留infra unknown。不得升级依赖或新增solver工具。归档只在最初读取时完整hash过一次，后续按已核stat及小源绑定，不重复1.65GB/SIF hash。

Root随后授权prepare-only固定恢复包，独立124–127、4CPU8GiB/900s；本收据不代表执行许可或已补评分。准备包/精确恢复校验另见 terminal_reshard_saved_grade_preparation 文档；评分需root与独立review后唯一启动。
