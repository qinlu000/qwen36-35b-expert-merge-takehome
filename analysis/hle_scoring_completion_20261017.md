# HLE正式评分完成核验

**2026-10-17 07:27–07:29 CST**只读核验80保存的逐题结果、原预算、独立恢复账本、原文件备份和两条ReadTimeout收据。没有调用生成/评分/恢复生产脚本、发送solver/Judge请求、启停进程/GPU或修改任何原配置/结果。本轮只新增本文和[小JSON收据](source_snapshots/hle_scoring_completion_20261017.json)。

|模型|有效/2500|正确|原预算无答案|最终accuracy|Judge API调用|账面CNY|
|---|---:|---:|---:|---:|---:|---:|
|Base|2500|99|1445|3.96%|1057|1.60102950|
|HLE专家250|2500|173|30|6.92%|2475|1.95277050|
|Mixed883|2500|146|41|5.84%|2473|2.07888300|
|AVG64|2500|117|1196|4.68%|1309|1.42656225|
|AVG16|2500|101|1302|4.04%|1200|1.25377050|
|TIES-Dense|2499|131|68|**null，尚未完整**|2445|2.16141450|

逐模型全部2500份保存结果已独立重算valid/correct/status，并与summary一致。TIES的第2500项仍evaluation_invalid，不能删题、补0或给完整accuracy；其他五组complete=true。固定分母仍2500，完整图像目标342。此表只报告HLE，不构成四项macro或仅权重造成差异的因果结论；原预算无答案及既有部署差异仍须随比较披露。

本次新恢复三组共**9次已完成调用、0.00827325 CNY**：AVG64 2次/0.003009；TIES 6次/0.00472125；AVG16 1次/0.000543。全部completed，无unknown或未结算reservation，未重发。它们各自原账本仍为1307/2439/1199次；新增费用仅记独立compact账本。

六组累计Judge为**10959次、10.47443025 CNY**，其中原账10941次/10.45740450，全部显式格式恢复18次/0.01702575（含Base1、专家2、Mixed6、AVG2、AVG16 1、TIES6）。summary已经含恢复费用，不能再把其recovery ledger重复加一次。费用按冻结校内价计算，包含失败请求保留的保守预留额，不是PBMS实账；Base cap为10CNY，其他各20CNY，每组5000调用，均未触及上限。

五组compact合计17题的161份原备份hash均通过；其中139份应保持原样的当前文件与备份一致，包括budget、scoring config、identity、frozen source、inputs、原requests/responses/errors。22份summary/results是恢复预期替换的文件，旧版仍保留。17份solver原record均与发送前source_identity SHA一致。每次新request与原request比较，唯一变化是既定system wrapper后缀；原user message（question/gold/solver response/criteria）逐字保持，原两次请求和响应未变。Base本轮只读引用其已完成结果及既有独立账本。

**2+1格式例外已明确扩展原两次上限**：只对固定名单、原双HTTP200/length4096且原parse失败的项，追加至多1次相同Judge请求；将verdict字段先序列化、reasoning限制一短句最多40词。相同DeepSeek-V4-Flash身份/fingerprint、TLS校验、seed0、temperature0、4096、nonthinking、五字段schema及frozen parser保持。未知结果不重发，不按correct挑选、重答或追加名单；新有效结果允许yes或no，均用原schema判定。不能称这仍是原两次上限。

AVG64与AVG16各1条恰300秒的ReadTimeout已按统一原预算无答案政策收集，**新增solver/Judge调用均0**。两份正式收据均在80的各自`scoring/readtimeout-budget-audit-20261017/receipt.json`，对应输出为`avg64_hle2500_20261017`及`avg16_hle2500_20261017`。本轮独立核两条原record SHA、各6份原备份、当前budget/config/identity/frozen source一致，以及原grader已退出、结果为native_no_answer/judge_calls0。原record SHA分别为`4e88459275458420fd7885ab0b84af3cf4b7ccf336947a9d2efae839cfeb1953`、`c1a81d103a5497677ce638bbc9052726b2e20cba085aad0874d79c775db40c97`。统一兼容仍先拒显式infra，要求>=299且无raw；未将其他环境故障填0。原frozen source保持148721d6…，只有root审核的live classifier一行兼容为608c5d6a…。完整路径及hash在JSON。

TIES剩余`672d8b9b504a98f0e4799ae0`两次均HTTP200/stop/79completion，JSON缺`correct`；当前judge_calls仍2、correct=null、无额外recovery目录。它不符合length资格，本轮不扩规则或推断标签，保留待讨论。正式分数、方法/系数/checkpoint没有据此重新选择。
