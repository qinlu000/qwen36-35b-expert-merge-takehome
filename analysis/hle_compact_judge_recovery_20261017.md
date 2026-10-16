# Direct HLE compact Judge recovery

2026-10-17：root逐段审阅后明确批准，**固定8项一次恢复已完成并独立核验**。HLE专家最终173/2500 = **6.92%**；Mixed最终146/2500 = **5.84%**；两者均2500有效、0 invalid、0 pending。使用已披露的HKUST(GZ) DeepSeek-V4-Flash替代Judge，不是官方提供方成绩。本次固定名单为HLE专家2项及Mixed6项，见[配置](../configs/eval/hle_compact_judge_recovery_20261017.json)。未改Base脚本/结果、solver答卷或任何生成队列。

05:16:31 CST在80一次持久启动PID695805/starttime868441590，唯一claim为`artifacts/eval/direct_hle_compact_recovery_20261017/execution-claim.json`，stdout同目录`stdout.log`。执行已退出，claim更新为`completed_verified`；每模型原controller锁在整个执行期间独占。8项恰好各新增1次请求，全部HTTP200、身份/fingerprint一致、五字段JSON通过各自原frozen scorer的parse；未重发、未生成solver答案。专家2项恢复均判错；Mixed6项中1项判对、5项判错，均按原parse接受，没有依reward挑选结果。

8项原两次尝试均HTTP200、`finish_reason=length`、4096 completion tokens，且均未通过原frozen scorer的`parse_judge`。它们属于Judge输出截断，原状态是invalid/null；不是原生判错0分。此前Mixed的4项是较早快照，最终原scorer退出时共有6项。

这是**显式增加一次Judge恢复机会的统一例外**，不能称原两次上限未变。沿用[Base既有恢复](../scripts/recover_hle_last_judge_20261017.py)逐字相同的追加system文本：先序列化correct/confidence/strict等verdict字段，reasoning最多40词、一短句，不重述答案或重新解题。原question、gold、solver response及完整官方criteria/user message逐字不变；模型身份及fingerprint、学校TLS证书/SNI/Host校验、seed0、temperature0、4096、nonthinking、五字段schema均保持。solver的300秒/64K8K预算未改变。

统一适用规则是：仅对两次原Judge请求均200+length且原parse失败的invalid，按显式审阅名单提供最多一次相同compact-wrapper恢复；不依correct/reward挑选或补跑。后续任何模型出现相同问题，应先审阅并固定其名单及源证据，再按相同规则处理；本脚本不自动发现或追加任务。第三次仍失败则保留invalid/null；HTTP故障、身份漂移、已有可解析结果等不属于本名单的准入条件。

[脚本](../scripts/recover_direct_hle_truncated_judges_20261017.py)默认只读prepare，执行需显式`--execute`。操作前要求原grader退出，并独占原`scoring/controller.lock`。它核对原request1=request2、原user message由冻结criteria及原input重建后一致、原input与solver JSON的response一致、两次失败身份及token上限；执行时再次核solver原文件字节hash。未出现正确性选择分支，yes/no均只经过原parse校验。

执行时先把old invalid、inputs、原requests/responses/error、budget、summary、scoring config、identity及frozen scorer逐字备份至每模型`scoring/compact-recovery-20261017/original/`。原budget不修改；新增独立`compact-recovery-20261017/budget.json`，每任务先持久化reservation再联网。已有reservation/request的任务不重发，包括未知结果。失败保留全额reservation；成功仅在原parse、身份、usage及原source校验通过后，允许该invalid转为judged，并从全部2500结果重汇总。汇总仅全部2500有效时给最终score。

只读preflight于05:13:29 CST验证两个原grader已退出、两把原controller锁可独占：

|模型|原calls|原账面费用CNY|新增最多calls|合计最坏reservation CNY|
|---|---:|---:|---:|---:|
|HLE250|2473|1.95138750|2|1.97619075|
|Mixed883|2467|2.07273975|6|2.15674575|

分别低于每模型20元/5000calls，原失败尝试的full reservation仍全部计入。独立恢复台账必须同时计入后续费用汇总，不能只读取原budget；恢复后的summary会披露合计和台账路径。

实际新增及合计费用（CNY；原失败reservation未扣减）：

|模型|新增calls|新增费用|合计calls|合计费用|
|---|---:|---:|---:|---:|
|HLE250|2|0.00138300|2475|1.95277050|
|Mixed883|6|0.00614325|2473|2.07888300|

结束后逐项核对：8个solver原JSON字节hash不变；原budget hash与preflight及备份一致；原requests/responses、inputs、scoring config、Judge identity及frozen scorer逐字不变；原invalid/summary完整留在`original/`。新增request仅改变system尾部追加文本，所有其余字段及user message与原request逐字一致。canonical仅替换8个经原parse认可的invalid，并重汇总各自2500项。安全收据含每项usage、账本状态、身份/parse及字节核验，不包含题面、gold或solver原文。

检查：Python语法、JSON解析、追加wrapper与Base源码AST中的字符串逐字一致；9个纯本地sanity覆盖合格截断、HTTP失败/nonlength/已有可解析结果拒绝、user message变化拒绝、未知结果禁止重发、费用与calls cap、yes/no同parse。80默认prepare验证了实际8项，没有读取凭据或发请求。安全小收据见[snapshot](source_snapshots/hle_compact_judge_recovery_20261017.json)。

实际执行命令如下，**不要再次发起恢复**；已有reservation会阻止同项重发。纯读复核可省略`--execute`：

```sh
artifacts/envs/hle/bin/python scripts/recover_direct_hle_truncated_judges_20261017.py \
  --project /data/caoqinlu/projects/apex-takehome \
  --config configs/eval/hle_compact_judge_recovery_20261017.json --execute
```
