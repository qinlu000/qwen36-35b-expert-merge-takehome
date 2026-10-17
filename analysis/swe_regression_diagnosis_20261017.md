# SWE下降：已证实的行为与尚未证实的训练原因

2026-10-17，用户要求解释SWE大幅下降。本轮仅只读检查已有轨迹、训练/评测源码与统计；没有重生成、调用模型/Judge、补评分、改变原分数/配置/权重或恢复已取消的自动化。

SWE Base10/51=19.607843%、专家0/51、AVG64 4/51=7.843137%。主要异常已经存在于SWE专家，不能把本次下降主要解释为合版或rank压缩；AVG64反而比专家多4题通过，且本身没有SVD压缩。

## 最有证据的直接表现

| 全51题已有生成记录 | Base | SWE专家 | AVG64 |
|---|---:|---:|---:|
| 保存空patch | 3 | 43 | 34 |
| 最后请求明确context_budget_exceeded | 18 | 34 | 11 |
| 日志记录patch capture failed | 0 | 0 | 0 |

在Base原通过10题中，专家8题保存空patch，剩2题非空但未通过；AVG5题保存空patch。注意非空patch不等于已完成正确产品修改，可能包含环境或生成文件变化；0字节也不能单独倒推所有生成行为。

对三项“专家空patch＋原exit_status未知”的已有完整轨迹作代表性核查：

- Ansible d624：115个assistant步骤、121个bash调用，118个rc0、2个rc1、1个rc2。
- Teleport65438：168个assistant步骤、175个bash调用，175个均rc0。
- OpenLibrary630：221个assistant步骤、232个bash调用，228个rc0、3个rc1、1个rc2。

重复计数为：d624同一条cat/ls命令106次（连续106），Teleport654同一条grep162次（最大连续160），OpenLibrary630同一条ls205次（连续205）。原工具输出进一步表明：Teleport的grep把`-r`/`--include`当文件名而报错，OpenLibrary的嵌套路径不存在；后接`| head`掩盖子命令非零退出码，所以rc0不等于子命令成功。模型重复观察相同错误而未修正。Ansible则反复读取相同目录结果。记录见[原命令与短观察](source_snapshots/swe_repeated_read_commands_20261017.json)。这三例末尾多轮重复相同只读cat/grep/ls，原日志明确model.patch bytes:0，没有patch capture failed；三例均使用/app，0条/testbed或patch.txt命令。它们支持“工作流停留于重复搜索，未形成交付修改”，不支持“模型HTTP/工具JSON接口普遍不可用”“反复进入错误/testbed”或“补丁已写好但提取报错”解释这三例。不能由3例断言其余48题完全同因。

## 上下文限制起什么作用

实际SweModelBridge.validate按精确tokenizer计数，固定65536总context并为每次输出预留8192，因此prompt最多57344；没有历史摘要/滚动压缩。专家34条明确拒绝的末prompt为57360–63207，median57698.5。通过离线提取实际validate方法、仅stub已保存的tokenizer计数重放，57344 accepted、57345 rejected、34个真实溢出计数全部重现拒绝，0网络/模型调用。命令为`python3 /tmp/apex_swe_guard_replay.py`（临时诊断工具，不是项目运行依赖）。

这能解释为什么这些任务不能继续请求，却不能独立解释模型差异：Base同样有18题触发guard，其中3题仍靠已保存的非空patch通过测试。AVGguard只有11却34空patch，也表明上下文拒绝不是空patch的唯一原因。不能简单把全部失败改标infra，或认为扩大context必然恢复成功率。

## 训练原因：已排查与待证实

[训练协议核查](swe_sft_protocol_diagnosis_20261017.md)未发现已证实的只监督尾轮、工具调用未监督或thinking开关反向错误。system/user/tool观察masked，assistant正文、工具命令与后续assistant均有监督，空think masked；实际训练249步/1993有效行、一epoch、r16alpha32/LR1e-4。loss不是任务质量证据，不用于证明专家更好或选择checkpoint。

确有残余分布差异：训练首user保留源patch.txt准备流程，训练大量命令使用/testbed，而正式harness默认/app；训练教师是Qwen3.8-Flash-Next、thinking=true/xhigh，清理后以非thinking方式监督工具轨迹。上述差异只能作为候选解释；代表性失败已显示模型使用/app且工具接口可运行，但两例没有纠正工具输出中的错误，尚未通过受控实验建立这些差异、学习率、数据量、reasoning清理或过拟合与0/51的因果关系。

当前合理结论是：SFT后的SWE专家出现严重的交互任务完成退化，反复只读搜索与空补丁是直接可见证据；训练为何产生这种行为尚未确定。历史Base与专家/AVG服务、并发及排程有已披露差异，同一预算不等于已隔离纯权重因果。

下一步如继续诊断，应先对现有同题轨迹量化重复命令、编辑发生与终止方式，再设计独立小实验隔离训练/协议因素。不能用正式测试成绩反复调参、重新生成Base或换冻结主AVG64。本轮没有开展这些新实验；原分数和自动化取消决定保持。

来源：[完整51题对照](swe_task_comparison_20261017.md)、[全153条生成诊断](swe_base_expert_context_diagnosis_20261017.md)、[训练/协议诊断](swe_sft_protocol_diagnosis_20261017.md)、`scripts/swe_baseline_v2.py:validate/DeadlineEnvironment`及原LockedMiniSwe捕获日志。
