# DeepSeek 全量评测成本：计费与协议边界

核验日期：2026-10-15。仅查官方文档和已有项目记录；未调用付费 API、未运行正式 benchmark。本文件为成本估计的约束，实际 token 数由主成本表另列假设。

## 当前官方人民币价

每百万 token，人民币；输出预算包括思考输出和最终回答，不应只按最终回答文字估计。

| 模型 | 闲时输入缓存命中 | 闲时输入缓存未命中 | 闲时输出 | 高峰 |
|---|---:|---:|---:|---|
| deepseek-flash（V4.1 Flash） | 0.02 | 1 | 4 | 三项均为闲时的 2 倍 |
| deepseek-v4-pro | 0.15 | 4.5 | 13.5 | 三项均为闲时的 2 倍 |

高峰：北京时间周一至周五 09:00–12:00、14:00–18:00，不含中国法定节假日；其余及周末全天为闲时。实际跨时段请求按服务计费结果记账。来源：[官方中文价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。

历史公告与当前文档存在更新差异：9 月 10 日公告曾宣布 9 月 14 日后 Pro 路由 Flash，不能仅根据旧公告认定今天 Pro 一律按 Flash 价。当前定价页仍分别列出两档，当前入门页也列出 Pro，故本项目估算保留两个独立价格；实际运行锁定 model ID、服务响应 model/fingerprint、日期和 usage。来源：[历史公告](https://api-docs.deepseek.com/zh-cn/news/news260910/)、[当前入门](https://api-docs.deepseek.com/quick_start)。

## 输入、思考和缓存

- 成本按请求累计：闲时 Flash = `cache_miss/1M × 1 + cache_hit/1M × 0.02 + completion/1M × 4`。Pro 使用上表独立单价。高峰乘 2。多轮 agent 每次请求会再次携带历史，不能只计算每个任务的第一次输入。
- 缓存默认开启，重复前缀满足完整缓存单元匹配才可命中，且为 best effort。重写历史、重新排序消息等可能损害命中；无实测时必须同时列有缓存假设和无缓存保守估算。来源：[缓存文档](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)。
- 思考默认启用；携带 tools 的多轮调用要求回传历史 reasoning_content，它们会进入上下文；无 tools 时历史 reasoning 不拼接。usage 的 completion_tokens_details.reasoning_tokens 是 completion 的细分，成本统计不能在 completion 之外再重复加一次 reasoning。来源：[思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)、[usage 字段](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)。
- API 思考模式下 temperature 不生效；top_p 只接受 0.95–1。非思考模式 top_p 固定1.0，传入值被忽略；当前接口无 top_k 参数。因此对照题面 Terminal 采样配置不能声称完全复现，只能将 DeepSeek 作为配置差异已披露的外部参考模型。来源同上。

## 四项仍有的非 DeepSeek 费用和资源

- Flash 支持原生图像；当前价格表标记 Pro 不支持。若要求 full multimodal HLE，一个单独 Pro 模型不能直接覆盖；不能默默删掉图像题。图像输入的计费仍以 API usage 为准。来源：[视觉文档](https://api-docs.deepseek.com/guides/vision/)、[价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。
- DeepSeek 只替代受测模型推理；仓库命令、终端容器、编译测试、ASI 科研计算依然需要 CPU/RAM/磁盘（选定ASI60项metadata均未声明GPU必需），故 API 费用不等于端到端总费用，也不会自动解除环境并发瓶颈。项目证据见 [待讨论问题](open_questions.md)、[Terminal/HLE 可行性](terminal_hle_feasibility.md)。
- HLE 的 answer judge 可以另行冻结为 DeepSeek 协议，但相对官方默认 judge 属于本实验设置，必须披露，并独立计入约 2,500 次判分成本（单个受测模型）。来源：[官方 HLE judge](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)。
- ASI 固定版本存在 GPT-5.5 文本/视觉 judge；更换受测模型为 DeepSeek 不会替换这些 judge。保留官方评分契约时，其调用另付原服务费，不能算进 DeepSeek 余额，也不能擅自统一换 DeepSeek。来源：[固定默认 judge](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py)、[本项目逐项核查](judge_requirements.md)。

解释用户的“跑一遍”时，先按一个 DeepSeek 受测模型完成各项指定全量计；Terminal 仍是 89×5=445 trials，而不是只有 89。该外部模型结果不能代替题目要求的 Qwen Base、训练专家和合版模型结果。
