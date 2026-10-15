# HKUST(GZ) GPT-5.6 Luna 判分 API 预算

核验日期：2026-10-15。仅核配置与模型列表，并用4个自造请求测试文本/图像接口；未正式评分任何HLE/ASI题目或启动被测Base。

## 已找到的配置与价格

80的/data/caoqinlu/projects/data-perception/.env含OPENAI_API_KEY和OPENAI_BASE_URL=https://aigc-api.hkust-gz.edu.cn/v1。文件未复制到本项目、未改写、未输出密钥。GET /models鉴权200，12个模型，列有gpt-5.6-luna/gpt-5.6-terra，没有列gpt-5.5；不据此证明其他账户也没有原Judge。

按学校当前[模型列表及定价](https://docs.hpc.hkust-gz.edu.cn/docs/aigc/api-model-list/)及[2026-09-02服务通知](https://itdid.hkust-gz.edu.cn/cn/detail-1069)：Luna输入1.4662元/M、输出8.7996元/M。API默认收费，无免费额度；聊天网页的50万token额度不能拿来抵API。费用记学校账户/PBMS，当前未查询账户余额或剩余预算。V1自动转V2，具体字段按[校内调用文档](https://docs.hpc.hkust-gz.edu.cn/docs/aigc/api-usage/)验收；未改既有.env服务地址。

OpenAI[该模型说明](https://developers.openai.com/api/docs/models/gpt-5.6-luna)确认原生图像输入、structured output和reasoning none，但网关是否实际支持必须另验。Luna是成本优先模型，不能因5.6版本号大于5.5就推断Judge质量更高。

## 真实的极小兼容性检查

4次请求均HTTP200、returned_model=gpt-5.6-luna、reasoning_effort=none、temperature0、max_completion_tokens1024、JSON mode，没有自动重试；原始请求/响应/usage在ignored artifacts/preflight/hkust-luna-20261015/。

- 纯文本2+3：正确JSON，1/1。
- 64×64红蓝左右图：接口接受，误答为blue/blue；保留失败，不称所有图像测试通过。
- 两张512×512红蓝/蓝红图，detail=high：2/2正确。
- 合计prompt755、completion56、total811 token；按公开价估算约0.00160元，不是读取账单所得。
- 这只证明兼容性和最简单颜色识别，不是科研图表校准。不能因两个大图答对就认定可完全替代原GPT-5.5 Judge；也不根据一个小图失败推断所有视觉不可用。

## ASI：这次主要补齐的评分需求

固定60任务×四层=240条件。保留原scorer结构/num_judges、文件齐全且相关gate通过、单次请求成功时，已核为每模型132槽=56文本+76视觉；Base/交互专家/合版共396槽=168文本+228视觉。420份图像附件包含重复judge输入，原配置无重试的输出cap合计291,888 token；不是396次都要生成1024。

这是已核配置和部分custom委托的预算基数，不是全局严格上限或实际发生数。缺文件/gate失败会少调，底层和其他custom依赖可能多调；外层3attempt可使已核槽至1188尝试。详见[精确调用审计](asi_judge_call_budget.md)。

费用公式：输入M×1.4662 + 输出M×8.7996。图像按实际等效输入token计，不按PNG字节或base64字符收费量猜测；下面所有输入已经包含图像token，缓存按0折扣保守估。

| 三模型ASI情景 | 总输入假设 | 输出按已核原cap | 不含重试的费用 |
| --- | ---: | ---: | ---: |
| 较轻 | 2M | 0.291888M | 5.50元 |
| 中等 | 5M | 0.291888M | 9.90元 |
| 较重 | 10M | 0.291888M | 17.23元 |
| 大图敏感性 | 20M | 0.291888M | 31.89元 |

输入情景不是正式产物实测，cap也须核Luna网关的字段/推理token语义是否一致。建议**ASI三模型先按50元规划**，用实际usage监控；它是初始预算而非最坏上限或停止授权。只先评Base则132槽，正常约为三模型预算的三分之一。上述金额不含本地Qwen作答、CPU容器、其他自定义scorer潜在额外调用或teacher采集。

## 若连HLE也改用Luna

当前HLE候选仍是已有DeepSeek；用户这次只是问Luna预算，没有修改正式Judge。若全部改Luna，Base/学术专家/合版各2500题，共7500正常判分请求；SWE/TB官方自动测试不需要额外LLM Judge。

| 每次HLE平均token假设 | 7500次输入/输出总量 | 不含重试费用 |
| --- | --- | ---: |
| 输入2K、输出500 | 15M / 3.75M | 54.99元 |
| 输入4K、输出1K | 30M / 7.5M | 109.98元 |
| 输入8K、输出2K | 60M / 15M | 219.97元 |

问题、gold、模型答案和评分prompt都计输入，模型生成长答案会增加Judge输入；reasoning若启用还需计其输出。这里是敏感性算例，不是7500题实测或封顶。两项都用Luna时，按上述情景并加重试/校准余量，可先规划约100–350元；若只补ASI视觉评分，无需因此把HLE也切过来。

## 协议边界

原ASI配置是openai/gpt-5.5，HKUST key提供Luna解决了一个可用图文API来源，但不是原模型凭据。Luna作为替代Judge需在正式Base评分前固定真实模型/endpoint、rubric/prompt、采样/推理、num_judges、输出cap、重试与图片处理，并做独立科学图文校准；全部模型统一，结果明确披露评分模型变化，不能冒称原Judge完全复现。本轮没有修改任何原task_eval或评分模型。
