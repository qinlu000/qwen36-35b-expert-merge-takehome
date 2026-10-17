# SWE下降：已保存上下文与工具行为诊断

本次只读核对固定51题的三组来源，未重跑Base/生成/评分/训练，未访问凭据或改变服务。逐题元数据见[JSON](swe_base_expert_context_diagnosis_20261017.json)。最直接的观测差异是：专家更多停在重复只读工具行为，保存的空patch由Base的3份增至43份；上下文guard由18题增至34题。**这不是SFT根因的因果证明，也不能把空patch等同从未编辑。**

|固定范围|Base|SWE249专家|AVG64|
|---|---:|---:|---:|
|完整成绩|10/51|0/51|4/51|
|最后请求明确context_budget_exceeded|18/51|34/51|11/51|
|保存patch为0字节|3/51|43/51|34/51|
|mini记账api_calls中位数|57|62|122|
|Base通过10题中触发guard|3/10|5/10|2/10|
|Base通过10题中保存空patch|0/10|8/10|5/10|
|Base通过10题mini api_calls中位数|53.5|90.5|90|

guard为已有精确token计数满足`prompt_tokens_exact + 8192 > 65536`，不是工具执行HTTP400。Base通过的10题中也有3题最终触发guard，说明它本身不充分决定失败；此前完成并保存的有效补丁仍可能通过。AVG guard比Base少但分数仍低，亦不能把整个退化只归因于上下文拒绝。mini的api_calls是原轨迹记账字段，不冒充成功upstream调用数或累计completion tokens。

## 三个固定退化例

这三题Base均通过、专家均保存空patch且mini退出字段为空。只解析这三份既已定位的轨迹做命令计数，不扩读全部超大request bodies或大patch。

|任务短ID|assistant步/bash调用|完全相同命令最高次数|最大连续相同次数|工具returncode|
|---|---:|---:|---:|---|
|Ansible d624|115/121|106|106|0×118、1×2、2×1|
|Teleport65438|168/175|162|160|0×175|
|OpenLibrary630|221/232|205|205|0×228、1×3、2×1|

两个原样短命令例（不含题面或金标）：

```sh
cd /app && grep -rn "touchid.Register\|touchid.Login\|touchid.DeleteCredential\|touchid.ListCredentials" -- -r --include="*.go" | head -40
ls -la /app/infogami/infogami 2>&1 | head -20
```

分别完全重复162次与205次。Ansible重复的是同一组cat/head/ls检查。三者全部命令中`/testbed`及`patch.txt`计数均0，实际使用`/app`；因此这三例不支持“反复cd错目录”的具体假说。工具JSON解析失败0、额外user纠错消息0。**rc0不等于子命令成功**：Teleport把-r/--include当文件名，OpenLibrary路径不存在，后接head管道掩盖错误；原观察见[短命令证据](source_snapshots/swe_repeated_read_commands_20261017.json)。这是重复读相同内容/错误且未修正，不是所有工具HTTP失败。未据此推断所有51题都具有同一根因。

三例原generation异常均为`NonZeroAgentExitCodeError`，mini exit_status为空；本轮**未核实实际elapsed、numeric exit code或具体停止原因，均保持unknown**。源代码存在1740秒inner timeout与1800秒共享clock，不等于已证明这三例就是相应超时，不能自动写成“耗尽1800秒”。

## patch capture与协议边界

全153份trial.log都存在`model.patch bytes:`记录，未发现`patch capture failed:`警告；上述三例均明确记录bytes0。`LockedMiniSwe.run`在finally调用capture，而`DeadlineEnvironment.exec`确实会限制capture剩余时间；但现有日志**没有证明这三例因该限制提取失败**。另一方面capture shell隐藏git stderr并以true结束，因此bytes0也不能证明每个git步骤成功或从未发生编辑。非空patch也可能包含环境/模式变化，不等同有效模型修复；本轮未扩扫24–87MB大patch。

代码路径共同使用`SweBaselineV2`、固定mini2.4.6/原YAML及同64K/8K guard；专家入口复用native runner并改变模型alias。历史Base来源是clean28、manual_infra1和full_x2两组的显式保留答案，服务与排程不应宣称完全相同；本轮未发服务探针或逐run证明全部冻结代码hash一致。更深入的LoRA实际加载审计另行记录，不能仅凭0分认定服务加载损坏。

训练侧独立审计见[swe_sft_protocol_diagnosis_20261017.md](swe_sft_protocol_diagnosis_20261017.md)：system、bash schema、JSON观察和终末echo可对齐，尚无mask/think反向错误的确证；训练首user残留`/testbed`/`patch.txt`是风险，但本次三例的实际命令未体现该路径错误。学习率、过拟合、教师质量或训练目标导致循环仍待更深定位，不能把这些假说写成已证根因。

精确whole-history prompt token数来自已保存request metadata；没有新增tokenizer/API调用。三例工具正文累计字符为71,913/63,773/47,037，仅为`message.content`字符数，排除tool-call参数，不是分角色token账本或累计模型输出tokens。为遵守本轮bounded范围，未进一步扫描全部raw responses。自动化未恢复，原评分、checkpoint和主AVG64保持。

13:15补充：真实模板已发现空think壳删除差异，单样本CPU候选编码完全对齐；见[原生序列化审计](swe_serialization_parity_20261017.md)。此前“尚无mask/think反向错误”不等于模板逐token相同，旧人工fixture未覆盖本差异。没有重训或改变本页原153条结果。
