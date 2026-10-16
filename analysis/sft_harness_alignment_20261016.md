# SFT向目标harness对齐：当前实况与修改边界

2026-10-16。用户询问能否调整轨迹使其更贴近评测harness，例如相同system prompt。本轮只读实际新数据、转换器、安装包及评测入口；未修改训练数据、Slurm作业或冻结评测协议，无模型API调用。

**可以，按各benchmark分别对齐模型看到的输入输出协议；无需四项共用system。当前SWE/Terminal已经完成主要提示与协议对齐，剩余工作不能概括成给所有样本换一条system。**

## 必要性结论：保持当前训练版本

用户追问现在还需要改什么。复核后，没有已证实必须为prompt文案重做HLE/ASI数据或重训的阻塞；上轮“优先补”指可优化方向，不是已确认故障。HLE官方judge可从任意响应抽最终答案，严格三字段不是准确率判分前提；162条有参考的短答可正常SFT，只是没有完整解释监督。ASI现1073个输出均为单Python块，991辅助system与官方system语义兼容，暂无解析错误证据。

当前必须闭环的是Terminal原验证OOM的正式GPU全量eval：CPU修复已过，不能代替真实运行。待各模型训练可用后，先在既有独立val检查答案抽取、工具动作、代码块与任务表现；发生实际协议失败再定向调整。SWE/Terminal原生提示、现有划分、162参考短答和Mixed7073保持，不因文案一致性取消训练。HLE格式、ASI991提示统一后置为可选优化，缺Confidence不补造100%。

| Benchmark | 当前实际状态 | 适合继续做的调整 |
|---|---|---|
| SWE | 新2k转换器已用目标system、原生bash schema、目标JSON观察及单独echo提交；首user仍有源PR/patch.txt约束 | 只整理不改变后续行为含义的任务包装，保留真实题目、约束、命令和观察；不机械替换工作目录 |
| Terminal | Horizon1107＋Pivot893；两源样本首user的2834字符通用前缀与目标逐字相同，没有独立system | 保留原生user/assistant JSON布局，不再额外添加system；保留analysis/plan，不伪造Pivot未公开的第二次完成确认 |
| ASI | SAB82 train＋20val已用官方system；991辅助用允许片段/函数体的另一条system，但也都输出单Python块 | 可以统一官方system，同时把辅助样本的接口/缩进/补全约束移到user；仍如实标记函数/片段，不改称完整产物程序 |
| HLE | 2000train＋100val无system；实际Swift default_system=None；训练Explanation字段0、Answer789、Confidence0 | 要同时处理输入与输出格式；已有可靠答案可规范Explanation/Answer，无真实confidence不编造数值，短参考答案不编解释 |

## 优先级与实施方式

1. 以当前冻结评测配置和实际源码为准，复用同一benchmark的角色布局、工具schema、动作字段、观察包装、提交动作及输出约定。SWE独立subshell与Terminal持久tmux不能互换；提示文字相同不改变文件系统、依赖或状态。
2. ASI的system统一可机械完成，但必须保留旧system中的具体代码接口要求到user。HLE不应直接强加官方三字段system却保留不遵从该格式的标签；完整三字段监督需要可信原字段，或明确选择较接近但不完全相同的训练输出约定。官方judge对缺confidence默认100只是评分兜底，不是100%训练标签的依据。
3. 若落实，先产新数据副本，保留划分、完整内容与出处；重算完整序列和回答长度，不因增加prompt超过64K/8K而静默截断/删样本。Mixed随后使用同一四份新分区各一次。原已运行/完成的训练不能靠改JSONL追溯变成新版本。
4. 当前不建议仅为文案逐字一致重训已完成专家或重采全部轨迹。先检查独立val的格式可解析性、工具协议遵从和实际完成问题；只有发现实质失败才补少量目标harness示范。teacher-forced短答案val-loss不能代替原生harness下的任务准确率。

详细证据：[SWE/Terminal](sft_harness_alignment_execution_20261016.md)、[HLE/ASI](sft_harness_alignment_direct_20261016.md)。本轮是核查与具体适配方案，不将尚未执行的HLE/ASI改版写成已经训练。
