# 四项评测协议草案 v1

更新：2026-10-15。本文与 `configs/eval/protocol_v1.json` 是本项目评测规范草案，不是已通过执行验收的原生runner配置。完整来源、split、ID和主指标已明确；thinking偏好与ASI替代Judge尚待定，推理端点、容器、镜像digest和依赖锁也尚未验收。训练及正式Baseline均未启动。

## 范围、运行次数与主指标

| 项目 | 选定范围 | 每模型运行 | Agent与主指标 |
| --- | --- | --- | --- |
| SWE-bench Pro V2 HARD-51 | 官方hard/test完整51项 | 1次，采样seed=0 | 官方LockedMiniSwe；全新环境patch replay后的resolved rate，固定分母51；原运行分数另存 |
| Terminal-Bench 2.0 | 固定官方registry完整89项 | 5个独立完整job，seed=0,1,2,3,4 | Harbor/Terminus-2；五个成功率均值及样本标准差ddof=1，非pass@5 |
| HLE | cais/hle固定test全部2500题，含342图像题 | 1次，seed=0 | 官方单次图文/no-tools问答格式；准确率，另列2158纯文本与342图像题分项 |
| ASI-Bench | seed31415/open完整60任务×B1–B4=240条件 | 1次完整重复、每条件1 attempt | opencode_cli；官方本地mean_percent，明确标open/local/single run，非Portal认证 |

完整任务ID已保存于 `analysis/source_snapshots/protocol/` 的四份manifest，均固定来源revision；HLE由实下载的固定Parquet仅读取id/image列，image只用于非空标志。未读取正式question/answer/rationale。ASI保留源metadata的seed override与59 final+1 requested test状态，不自行剔除；五个sample不混入60项。

## 全部参评对象的共同约束

- 同一基座Qwen/Qwen3.6-35B-A3B，revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；tokenizer、processor、chat template都随此revision固定。BF16权重与KV，不量化；评测专家和合版保留完整视觉模块。
- 默认context=262144。四卡推理是候选运行方式，未证明加载/长请求吞吐；每项所有对象必须采用同一已验收推理栈、precision、prompt、工具、context、采样、重试和调度政策。
- 建议统一enable_thinking=false、preserve_thinking=false以控制时间；此偏好已向用户询问，尚未得到明确回答，不把建议当作用户已确认。固定模型模板开关，并检查真实渲染；不靠reasoning_effort名称猜开关。
- 非思考候选采样：SWE/HLE/ASI temperature=.7、top_p=.8、top_k=20、min_p=0、presence_penalty=1.5、repetition_penalty=1。TB遵题面覆盖为temperature=1、top_p=.95、top_k=20，presence_penalty=0作为本实验明确设置。
- 每次输出上限：SWE/HLE 32768；ASI 8192；TB 81920。输入+实际生成受context共同约束。未另外实现累计token硬限的工具任务明确设null，不把API max_tokens冒充整题预算。
- 官方通用prompt、工具schema和原生压缩流程固定；本地Qwen参数、额外禁网/工具范围、单次输出、种子等未公开值标为本实验设置，不声称复现模型卡未公开内部scaffold或修订题集。
- 正式评测在训练前锁完整scope/metric/protocol；仅独立dev用于配方、checkpoint与合版选择。正式逐题答案、测试反馈和派生示范不回流训练；最终权重冻结后只做评分与错误分析。

## 每项具体资源与差异

| 项目 | 作答上限 | CPU／RAM | 步数／累计输出 | 执行说明 |
| --- | --- | --- | --- | --- |
| SWE | 外层3000s；原wrapper内层2940s并留30s强杀宽限 | 1 CPU／4096MiB | native step_limit=0；无额外总token硬限 | build1800s、verifier3000s另计；作答阶段断网仅放行模型端点；fresh replay保留 |
| TB | 10800s | 32 CPU／49152MiB | native max_turns=None；无额外总token硬限 | 48GB按48GiB约定披露；资源配额未落实，不能只填limit便称已获得 |
| HLE | 每题总墙钟1800s；单次HTTP600s，最多一次传输重试 | 共享客户端，不逐题开CPU容器 | 单次答案，无工具；32768输出上限 | 完整图文；不因图像请求失败或答错临时删除题 |
| ASI | 每条件1800s | 4 CPU／8192MiB | build.steps=100；单次8192，无额外累计token硬限 | 本实验预算区别官方默认10800s；独立HOME/XDG，禁webfetch/websearch/MCP/子代理 |

SWE用Harbor固定commit `f527f8e447038fd242d08ecfa8aaa8029100da97`（实际包版本0.24.0），mini-swe-agent候选2.4.6。官方未指定此mini精确版，需独立兼容验收；模型选项中去掉不适合本地Qwen的reasoning_effort，不传导致Harbor切Responses API的agent option。prompt/bash/结束标记与观察截断保持固定官方配置。所有镜像还需在执行前记录OCI digest。

TB固定Terminus-2 2.0.0；top_k通过extra_body并核对真实请求，防止LiteLLM drop_params静默丢失。自定义模型信息明确max_input_tokens=262144/max_output_tokens=81920。启用原生summarize，提前阈值暂设86016以为长输出留空间；该值是本实验设置，近似计数、后续prompt和摘要追加仍有边界风险，必须用独立长对话验收后再锁。Harbor job完整trial重试0不等于关闭两层各3次的原生API重试。

ASI固定OpenCode1.17.15，commit `5fb0d1cdb363ecafd55402c451c6634ed15b74b1`。steps/temperature/top_p/provider limit有原生字段，ASI adapter不自动填齐；top_k、thinking和采样seed透传仍需检查。title/summary/compaction如使用，全部指向同一受测模型并计成本，不偷偷加外部强模型。restricted仅关闭web工具，不能替代bash网络隔离。

## 80K与图片的资源判断

81920是单次生成的上限，遇到EOS/工具响应自然结束不会补足；context262144包含历史与输出，不是另加262144输入再加81920输出。主协议仅TB保留80K，其他三项采用上表各自预算。4×H100低并发能否承受长上下文与实际并发，必须测显存、prefill、decode和端点队列，当前没有吞吐保证。

固定索引权重71,903,645,408B，理想四卡均分约17.98GB/卡，只是权重。配置为40层混合注意力，其中10层full attention、2 KV头、head_dim256；BF16常规full-attention KV理论未分片/未复制为20480B/token，262144 tokens约5GiB/序列。此数只说明这部分缓存的数量级，未计TP复制、linear-attention状态、分页/对齐、视觉、激活、通信workspace和框架峰值，不能当成服务实际显存。先验收低并发，再选可持续并发；若100 token/s则生成满81920约13.7分钟，仅是假设算例。

Qwen固定模型卡和config明确含vision encoder、image token和图文输入示例；CPU自造图像processor已过，实际GPU/HTTP图文尚未过。用户允许在模型确实不支持图片时另定text-only口径；本基座支持，当前保留全部2500。若未来决定text-only，须在任何正式Base/训练前版本化锁定2158题、所有模型同范围，并明确标签，不能把它与完整多模态分数混报或运行后删除失败图像题。

## Judge、失败与成本

HLE候选沿用DeepSeek官方deepseek-flash、thinking关闭、temperature0、输出4096、固定官方criteria和五字段JSON transport；prompt与hash已保存configs/eval/prompts及manifest。已做8例合成接口检查，仍需更广独立校准；它区别默认o3-mini，不冒称官方默认Judge等价。只向Judge提供评分所需输入，不向policy提供gold。

ASI原始13项配置要求openai/gpt-5.5并含视觉评分。现已发现80的HKUST网关，当前key列有gpt-5.6-luna，四次合成请求HTTP均成功，图像探针2/3符合预期；原始GPT-5.5仍未提供。Luna可作为需校准、需披露的替代Judge候选，尚未修改原scorer模型。预算详见 [HKUST Judge费用](hkust_judge_budget.md) 与 [ASI调用量](asi_judge_call_budget.md)。

- 模型超时、错误动作、缺文件按官方grader对已固化产物评分；不因低分换seed重答。ASI可能保留有效部分分，不一概手工赋零。
- 完整trial默认自动重试0；已核实基础设施故障最多人工补跑2次，同ID/seed/模型/配置，首个有效结果保留，全部失败和费用留档；不挑最好结果。各框架原生请求重试另固定并计日志。
- 评分服务失败只重判原回答/原工件，不重新生成policy答案。评分invalid/null单列，不静默剔除后报完整主成绩。可另给固定分母缺失按0的保守辅助分，但不冒称官方完成评分。
- 原生ASI mean_percent仅在240条件全部有效评分时作为完整主项，scorer_error_count=0；本版本每条件max_score=100，故等价任务/四层macro mean。图文与学科分项保留。
- 每结果记录模型artifact revision、协议/配置hash、镜像digest、ID/seed/attempt、输出/patch/评分工件、失败分类、请求usage、延迟、CPU/RSS/GPU峰值与全部成本；不记录密钥。

## 统计与最少实验矩阵

Base与最终合版均四项全量；仓库修复专家只要求SWE，交互执行专家要求TB+ASI，学术专家要求HLE。最低SWE153次、TB1335次、ASI720条件、HLE7500次问答，共9708个正式任务/问题运行。混训及落选合版只做预定独立dev，不要求额外四项全量。

四项百分制主指标等权平均；提升用合版减本次实测Base，单位百分点。配对bootstrap 10000次、seed20261015、95%区间：SWE/HLE按任务ID；TB按89任务簇保留每题五seed；ASI按60任务簇保留四层。对同一bootstrap样本保持比较模型配对；宏平均CI由四项配对差值均值形成。TB另报五轮SD，不把重复运行当445个独立任务。区间仅对固定版本/预算及已评运行解释，不用小dev证明3pp正式提升。

## 正式启动前仍需完成

1. 确定thinking偏好、ASI最终Judge路线，并完成独立文本/图像/工具/长历史验收后生成实际runner配置。
2. 固定完整依赖lock、真实请求及prompt/schema hash、各镜像OCI digest；以同一栈评所有对象。
3. 准确Base权重加载、真实<=4H100分配、容器phase网络/CPU/RAM、模型端点、评分接口与持久日志验收。
4. 按真实可用配额测有效并发，不把80可见核心数或HPC account上限当已保留资源。各项ready即启Base，CPU准备并行，四卡训练/推理按实际容量分时。

一手出处：[Qwen固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)、[SWE审计](protocol_swe_review.md)、[TB审计](protocol_terminal_review.md)、[ASI审计](protocol_asi_review.md)、[HLE审计](protocol_hle_review.md)。以上是可审阅设计和来源锁定，当前不宣称执行就绪或已有正式分数。
