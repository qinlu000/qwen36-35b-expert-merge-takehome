# 四项benchmark：上下文与输出预算的实证汇总

2026-10-16。按用户要求真实联网查作者论文、公开运行报告、官方评测代码与模型卡，区分“实际采用过”“有长度/质量消融”“我们的预算推断”。另仅以CPU统计ASI已下载官方题面的输入长度，无模型调用或任务执行。现有32K/64K候选不等于已冻结协议。

## 对当前项目的建议

**不建议四项一刀切32K：SWE优先64K，Terminal低预算32K有实跑先例，ASI单次程序32K有输入容量依据，HLE32K仍需图文输入覆盖核查。** 下表是效率优先的工程建议，不是四项已证明无损的最低值。

| 项目 | 总context建议 | 每次输出建议 | 证据及限制 |
|---|---:|---:|---|
| SWE / mini | **64K折中；128K更稳** | 4K起步，必要时在独立dev统一比较8K | 同族旧Pro自报32K明显差于64K；精确V2 HARD-51/35B消融缺失，mini没有原生摘要 |
| Terminal / 资源受限开发 | **32K** | **4K** | 完整89×5、Terminus2有公开一手运行；不同模型，没有32K与256K受控比较 |
| ASI / direct_llm候选 | **32K** | **8K** | 240份官方题面＋默认system＋Qwen模板最长15229；预留8192全部容纳；不证明程序输出质量或多轮历史足够 |
| HLE / 无工具、非思考候选 | **32K待核图文覆盖** | **8K较稳；4K是进一步省时候选** | 官方示例8K输出，对reasoning建议不少于8K；非思考无最低规定，也无当前模型32K/4K无损实证 |

HLE将8K作为较稳建议并非把reasoning最低建议强加给非思考：它只是为困难题保留更大可见解答空间，提前EOS不强制多生成。4K/8K的取舍仍应以独立dev的length截断、完成答案率和耗时决定，不能看正式HLE分数后选择。

Terminal题定正式结果另为256K/80K、3h、32CPU/48GiB与五seed；题面没有因此次外部实例自动放宽。没有面试方认可时，32K/4K可用于独立dev/消融与明确标注的资源受限结果，不能替代题定结果。SWE30min/ASI20min/HLE5min仍是本实验自选时间预算，本文的context证据不证明这些超时足够。

## 关键来源

1. **SWE：32K不稳的直接相关报告。** [Qwen仓库issue#179实验作者](https://github.com/QwenLM/Qwen3.8/issues/179)给出Qwen3.6-27B＋mini旧731题Pro结果：32K约9%、64K约24%、81K约27%、114K约28%，成功轨迹peak-context的p90约67K、最大约113K。是作者自报、旧数据、27B、联网2h；不能冒充本题35B/V2 HARD-51消融或官方背书，后续更新也不完全保持早期近似表。[专项与真正V2统计](context_evidence_swe_20261016.md)
2. **Terminal：32K/4K确有完整评测先例。** [AfterQuery作者运行报告](https://www.afterquery.com/blog/how-we-improved-terminal-bench-2-with-tinker-and-harbor)明确89题、Terminus2、五次均值、max context32K、max output4096，GPT-OSS-20B Base/SFT/RL分别3.1/13.5/17.0%。开摘要、不限评测turn；训练20turn限制不能挪给评测。作者没有公开其32K如何精确扣输出，不能冒称审过服务器硬限实现。另[Nemotron论文Table8](https://arxiv.org/html/2602.21193v1#S5.SS5)有40,960与65,536评测窗口实验，结果不支持一律越长越好，但训练/YaRN也变化，不是本模型的单变量context消融。[专项](context_evidence_terminal_20261016.md)
3. **ASI：公开论文没有最小窗口证据，本次补实际初始输入统计。** [作者论文§3.2](https://arxiv.org/html/2608.17271v1#S3.SS2)的百万token是多轮累计，不是窗口。CPU固定tokenizer统计240份prompt＋原生DirectLLM默认system与模板：中位978.5、P95约2831、最大15229；最大输入＋8192输出预留=23421，小于32768。无题面/答案正文落报告。[统计回执](source_snapshots/protocol/asi_direct_prompt_lengths_20261016.json)、[专项与边界](context_evidence_asi_20261016.md)
4. **HLE：别把8K输出和32K上下文混为一谈。** [固定官方README](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/README.md#L31-L45)示例8192为max_completion_tokens，并对reasoning不建议低于8192；未规定非思考最低输出或总context。没有找到同Qwen3.6非思考32K/4K无损消融或冻结2500题真实图文token分布。[专项](context_evidence_hle_20261016.md)

## 可以说与不能说

可以说32K有实际运行先例、某些单次生成路径的官方输入能装下。不能把“能完整跑”“输入能装下”“得分不掉”混成一个结论，不能用不同模型或任务版本的分数相减估计context收益。SWE比其他三项更有理由为长工具历史保留64K或128K；关闭思考也不消除命令/代码/工具观察历史。

降低允许context不会使相同短请求自动加速，实际节省来自较少长历史prefill、限制长输出、调度/并发与提前终止长尾。上下文/单次输出预算在正式Base前冻结并对该项所有模型一致。此次没有改protocol_v1、选择adapter、运行训练/正式任务/模型API或操作GPU作业。
