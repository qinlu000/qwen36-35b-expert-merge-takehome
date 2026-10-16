# 轨迹教师相对 Base 的能力证据与准入建议

核验日期：2026-10-16。用户新增约束：轨迹生成模型不能比 Base 弱。Base 固定为 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`。本轮只读官方模型卡、数据卡及公开元信息；没有生成 API、GPU、任务执行、数据变更或提交作业。下述“可保留”是相关领域公开证据支持的教师候选，不能解读成逐题保证、相同 64K/8K 非思考预算下已测胜出，或 SFT 必然提升。

## Base 的比较基准

[固定官方卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)给出 SWE Pro 49.5、Terminal-Bench 2.0 51.5、HLE 21.4、GPQA 86.0、LiveCodeBench v6 80.4。SWE 使用内部 bash/file-edit scaffold、200K，并修订了部分 Pro 任务；Terminal 使用 Harbor/Terminus-2、256K、80K 输出、3h、32CPU/48GB、五次平均。未发现它与所有候选教师在本项目非思考、64K/8K 下的完整直接对照。不能用参数量、发布时间或名字中的 Pro 单独判断强弱。

## 每源结论

| 数据与准确教师 | 已核官方证据 | 相对 Base 的判断与建议 |
| --- | --- | --- |
| SWE：Open-SWE 的 Qwen3.8-Flash-Next / thinking | [教师官方卡](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md)报告 SWE Pro 62.5、HLE 35.9、GPQA Diamond 91.7、LCB v6 91.9；SWE Pro 用 Claude Code/256K/修订集，DeepSWE 则报告 mini 与 Claude Code 两者较高分，且本模型 mini 更好。 | **可保留为 SWE 强教师主池**。有相关编程/推理的明显优势证据，但与 Base 的 SWE scaffold 不同，62.5 对 49.5 不是严格同条件比较，更不是本题 hard-51 成绩。 |
| Terminal 现有池：DeepSeek-V4-Pro-0813 / Terminus2 | [数据卡](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K)明确教师与 Terminus2。[0813 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/72e1d3230f6c080a530b0a1d46f8eb4602340597/README.md)报告 HLE 无工具 42.7、TB2.1 87.9；代码 agent 采用 DeepSeek Harness/minimal/max。卡中同表相较 Preview 提升明显。 | **可保留为 Terminal 强教师候选，证据为间接**。TB2.1/DeepSeek Harness 的 87.9 不能直接比 Base TB2.0/Terminus-2 的 51.5。也不能把 0813 的 max 榜分自动认定为这批轨迹的实际 reasoning 设置。 |
| Terminal 新补池：GLM-5.1 | [GLM 官方卡](https://huggingface.co/zai-org/GLM-5.1/blob/26e1bd6e011feb778d25ae34b09b07074139d92d/README.md)分别报告 TB2.0 **Terminus-2 63.5** 和 Claude Code 69.0。 | **可保留为 Terminal 强教师候选**。63.5 对 Base 51.5 至少同 benchmark 与 harness 家族，优于跨 harness 排名；仍缺完全相同资源、上下文、模式和种子的直接比较。不得用 69.0 冒充 Terminus-2 成绩。最终还须来源卡确认新增轨迹的精确教师和采集模式，不能仅凭数据集名。 |
| HLE：NVIDIA Math-v4 的 DeepSeek-V4-Pro High | [固定 Math-v4 卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/README.md)明确 High，并保留参考答案匹配的解答。[V4-Pro 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/b5968e9190ef611bbf34a7229255be88a0e937c1/README.md)分模式给出 High HLE 34.5、GPQA 89.1、LCB 89.8；对应 Non-Think HLE 仅 7.7。 | **可保留 High 数学主池**，有相对 Base HLE21.4 的支持性证据，但跨发布方评测且无完全同预算对照。必须保留 High 身份，不能把教师轨迹非思考化后声称其原采集就是 Non-Think；清理隐藏思考字段与原始生成模式是两件事。 |
| ASI：EcoCoder 的 DeepSeek v4 Pro High | [固定 EcoCoder 卡](https://huggingface.co/datasets/alrobles/ecocoder-scientific-reasoning/blob/09591b2b7b261aeb37d7db464f2af31eaa24baa0/README.md)明确 `reasoning_effort=high, temperature=0.2`，与上行教师系列/模式相符，未给精确权重 revision。 | **教师能力层面可保留；数据作为科研编程候选**。没有同协议 ASI 成绩或独立程序执行证据，不能称已验证更强科研程序轨迹。用户已明确 SFT 不以可运行环境为前置，不为此阻止现成参考程序进入 SFT；需如实披露其质量证据边界。 |

## 执行门槛

1. 模型生成的新轨迹，只接受准确可追溯的教师，且有目标相关领域不弱于 Base 的公开证据。未披露/混合教师先 hold；Science-v2 不能整池按 V4-Pro 接受，应按 `metadata.generation_model` 分流，只保留获准教师。
2. 发布者卡给出的教师身份属于来源声明，不等同于逐条调用日志或权重 revision 证明。训练记录保留该不确定性，不擅自将 DeepSeek-V4-Pro 补写为 0813，或将未披露 reasoning effort 补写为 Max。
3. 严格意义上的“同模式、同预算、同环境一定不弱”目前没有完整公开证据，也不能由公开分数保证逐个样本正确。工程上合理门槛是强教师证据 + 原来源质量标签/答案依据 + 独立验证集；不额外启动昂贵的教师全量 benchmark 来证明普遍命题。
4. **人工 reference 另计**：SAB 人工参考程序、DS-1000 原始人工参考解、SciCode 原始专家参考解不属于某个弱模型生成的轨迹，不能因没有教师榜分而拒绝。对应模型生成的重解、Verified 派生轨迹则必须追溯真实教师，不能借原始人工 reference 的身份豁免。

## 版本与未决项

- 本轮模型卡固定 revision 来自 HF 公开模型元信息，不是对大数据做新 hash 审计：Qwen3.8-Flash-Next `de4b8e4d43b917e7706784d8bb445c9af86a3540`；DeepSeek-V4-Pro `b5968e9190ef611bbf34a7229255be88a0e937c1`；0813 `72e1d3230f6c080a530b0a1d46f8eb4602340597`；GLM-5.1 `26e1bd6e011feb778d25ae34b09b07074139d92d`。
- Terminal-Bench 官方榜页当前重定向到动态站点，静态读取只返回页面壳，本轮不声称从官方榜独立验证了上述卡片数字。GLM 使用明确 Terminus-2 行，不混用 Best self-reported 行。
- **当前 HLE 既有 296 条 fresh DeepSeek teacher 是明确例外**：`scripts/generate_night_hle_supplement.py` 请求 `MODEL='deepseek-v4-pro'`，显式 `thinking.type=disabled`，记录 `enable_thinking=False`，并以选项匹配 publisher gold 接受。它们不是 High 轨迹，不能引用 High HLE34.5 给其实际生成模式背书。官方该型号 Non-Think HLE7.7 也不支持泛称强于 Base。建议新约束下 **hold 这一路后续扩量**，优先补现成 High 强教师数据；已完成 HLE SFT 保留历史结果，不自动删除或启动重训。精确服务映射和采集回执另核，不能擅自认定为 0813。
- 以上门槛不要求改变 Base、thinking 清理策略、64K/8K 预算、LoRA 配方，未修改训练数据或运行状态。
