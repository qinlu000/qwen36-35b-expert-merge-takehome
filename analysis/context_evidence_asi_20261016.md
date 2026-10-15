# ASI-Bench：上下文与输出预算的公开依据

2026-10-16，实际联网阅读作者论文、固定官方README/PROGRESS和DirectLLM源码。补充一次CPU输入长度统计；未调用模型/付费API、执行科学程序/正式任务、读答案/参考结果或改运行配置。

## 公开证据能说明什么

- [作者论文§3.2](https://arxiv.org/html/2608.17271v1#S3.SS2)报告多轮agent平均每任务B1累计4.35M tokens、37.8min，B2累计6.91M、49.7min。这是多次输入/输出累积，不是瞬时context，也不是单次输出。论文没有给32K/64K/128K同模型降窗消融、prompt长度百分位或direct_llm固定输出足够的结论。20min只是本实验节约预算，不能称已证明覆盖官方任务的实际时长。
- [固定官方PROGRESS](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/PROGRESS.md)有一个seed31415/B1接口验收实例：Pi 5turn/22tools/74157累计tokens，OpenCode11turn/21tools/95728，均本地93.02。它是有限验收例，不能代表240条件全量，更不能拿累计95K判定32K窗口一定不够。
- [固定DirectLLMAdapter](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py)读取准备后的prompt.md，只发默认system＋单条user文本，生成完整Python再执行。它没有多轮工具历史；completion没显式给context/max_tokens，因此没有可直接抄的“官方32K/8K够用配置”。图片不作为模型附件发送，与OpenCode多轮观察不可混同。

## 本地固定官方输入：32K是否放得下

为补公开论文未提供的初始长度统计，只读取已下载的240份`prompt_b[1-4].md`文本送入固定tokenizer，**不打印或持久化题面正文，不读data/reference/answer，不生成答案**。

- 数据revision：`0fa14219cafdbab634d8b3cfbce238a8735a214f`，seed31415/open，60×4。
- 模型/tokenizer/template revision：`995ad96eacd98c81ed38be0c5b274b04031597b0`。
- 计数口径：官方原始条件prompt＋DirectLLM默认system，按固定Qwen Jinja模板渲染；generation prefix开启，enable_thinking=false、preserve_thinking=false，encode不额外加special tokens。
- 已只读确认该tokenizer的truncation和padding均为None；长度没有先被tokenizer静默截短。
- 这是上述文本消息组合的计数；真实运行若附加框架说明或改变prompt生成方式需再核实际请求。不包括程序运行读取的数据文件，不推导多轮agent的峰值context。

| 输入组成 | 样本数 | 中位tokens | P95 | 最大tokens |
|---|---:|---:|---:|---:|
| 四层全部 | 240 | 978.5 | 2830.6 | **15229** |
| B1 | 60 | 1877.5 | 4413.1 | 15229 |
| B2 | 60 | 812.5 | 2043.1 | 3291 |
| B3 | 60 | 681.5 | 1574.8 | 2704 |
| B4 | 60 | 1077.5 | 2339.2 | 3961 |

预留8192输出时，32K总context允许24576输入；**240/240上述文本输入均能容纳，最大输入＋预留输出=23421**。这是支持“direct_llm的32K窗口在初始文本容纳上足够”的实测，不证明8K输出能完成每道程序，也不证明单次生成能达到多轮agent效果。[无题面正文的统计回执](source_snapshots/protocol/asi_direct_prompt_lengths_20261016.json)

## 对本项目的选择

若正式选择direct_llm，**32K总context＋8K输出有明确初始输入容量依据**，可用独立科学dev验证length截断与程序质量。若正式选择OpenCode等多轮harness，本统计不再能证明32K足够，需看工具观察、模型历史和摘要策略。保留同项所有模型相同的adapter和预算；本轮没有冻结或实施。
