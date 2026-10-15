# ASI／HLE容量预算：可实施值与剩余接线

更新：2026-10-16。只读固定通用代码、现有协议和processor配置；未读正式题／答案，未运行任务、模型API或GPU，未修改配置、依赖或runtime。

## 建议收敛的预算

按主线当前建议，**非TB统一采用128K总上下文**，避免为每项再建多套长度分支。ASI主候选为原生direct_llm完整程序生成，HLE为静态图文问答：

| 项目 | 总context候选 | 单次输出上限 | 迭代／墙钟 |
| --- | ---: | ---: | --- |
| HLE | 131072 | 16384 | 每题一次生成；总墙钟1800秒，HTTP600秒与最多一次传输重试仍需统一落实 |
| ASI direct_llm | 131072 | 16384 | 一次完整程序生成＋执行；每条件1800秒总墙钟，生成与执行共享 |
| ASI OpenCode替代候选 | 131072 | 8192 | 当前steps=100只是收尾提示；缩到50也不自动变成硬限；真正约束仍需1800秒总墙钟 |

HLE／ASI direct理论输入容量均为`131072−16384=114688`，包括system、任务文本、图片、模板标记等；实际还要留服务序列化与计数误差的安全余量。OpenCode每次8192输出时理论输入容量122880，但历史、工具返回、图片和压缩调用也要计入。

64K在工程上也可实现，但无需保留为本轮另一条默认路线；较短context／输出会增加超长输入或完整程序被截断的风险，不能仅凭省显存推断成绩不变。128K／16K也是实验选择，尚未证明覆盖全部正式输入或保证所有程序生成完整。

题面对HLE／ASI没有写死统一context、输出token或迭代数字；要求固定版本与范围、同一benchmark所有模型同协议并披露差异。因此上述可作为正式前统一冻结的本实验预算，不能称官方已披露原始模型卡harness。TB题定256K／80K属于另一项，不随此处缩减。[ASI既有协议核验](protocol_asi_review.md)、[HLE既有协议核验](protocol_hle_review.md)

## 如何真正落实

### HLE：输出有现成字段，较短context没有自动开关

固定官方client `centerforaisafety/hle@22ed3074b1e7b134bcbc09028d0ba320839b0655`使用`max_completion_tokens`限制一次输出，默认None；HTTP客户端为600秒、max_retries=1。它没有逐题128K输入检查，也没有有效的temperature传参（该行被注释），没有1800秒外层deadline。

可复用client，只在请求构造／调度侧接入：固定16384输出、完整图文消息的真实token计数与128K预算检查、固定采样和总deadline。`max_tokens`或`max_completion_tokens`只限制生成，不是上下文上限。保持Explanation／Answer／Confidence格式、2500题完整范围及342图像题；不因图片或超长请求失败删题。[固定生成client](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py#L9)

### ASI direct_llm：复用主干，补生成与总时限

固定框架 `apexin-ai/ASI-Bench@cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`原生adapter已经实现prompt→一次完整Python生成→代码提取→官方sandbox执行→产物收集，保留正式任务和grader。

但其构造器没有context/max_tokens等预算字段，completion调用也没有显式生成参数或HTTP timeout；`_execute`才取每条件timeout。若直接填timeout=1800，不能据此说生成加执行已共同限制1800秒。

最小接线是给生成调用显式传16384输出等参数，检查实际输入加输出预留不超过131072，并用统一deadline把生成、传输重试、代码提取和执行纳入同一1800秒；执行只用剩余时间。独立评分耗时另计。任务产物与grader保持原样，不新增伪工具循环。[DirectLLM生成](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py#L128)、[执行timeout](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py#L477)

### OpenCode：context字段能配，steps不能冒充硬停止

固定OpenCode1.17.15／commit `5fb0d1cdb363ecafd55402c451c6634ed15b74b1`支持provider model的`limit.context/input/output`。替代候选可以声明context131072、input122880、output8192，主／title／summary／compaction使用同一受测模型，所有请求计预算。

原生自动压缩会根据模型声明计算可用窗口；有input字段时还会减去reserved，默认reserved为min(20000,有效输出上限)。例如input122880、output8192时，原生usable约114688，不能把配置字段简单当成恰好到128K才压缩。原生计数／摘要对图片和新增工具输出仍有误差，需真实序列化后的请求守卫与长历史验收，不能靠填一个数字保证任意输入安全。[limit schema](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/core/src/v1/config/provider.ts#L41)、[overflow计算](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/overflow.ts#L10)

**steps=100并未在已核路径强制100次停止。** `prompt.ts:1178`计算isLastStep，`:1281`追加MAX_STEPS_PROMPT，但`:1283`仍传tools，`:1285`未因步数设置toolChoice=none；提示正文虽说工具已禁用，调用路径本身并没有因此清空工具。检查相邻processor/tools代码也未找到另一个按该值硬停止的分支。故应称“第100次迭代起要求文本收尾”，不是100条命令、100次总API硬限。若改50，结论相同；辅助title／summary／compaction也不等于这一个计数。若要真实请求数硬限，需要外层计数／终止或调用层禁工具，并单独验收。[步数判断与请求](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/opencode/src/session/prompt.ts#L1178)、[收尾提示正文](https://github.com/anomalyco/opencode/blob/5fb0d1cdb363ecafd55402c451c6634ed15b74b1/packages/core/src/session/runner/max-steps.ts)

## 图像与服务端256K的关系

图片不是一个固定token。固定Qwen processor配置为patch_size16、merge_size2，size最小65536、最大16777216像素量级；现有Transformers Qwen3VLProcessor按`prod(image_grid_thw)/merge_size²`展开image token。单张静态图在最大像素附近，视觉token可达约16384，另有模板边界；应以真实processor结果计数，不能拿base64字符长度或图像占位符的一个token估预算。[固定processor配置](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/preprocessor_config.json)

HLE client发送题目图片；OpenCode还可能从read结果带入图片并积累历史。128K输入预算必须包含视觉展开和待生成输出。不得为塞入较短窗口静默删图、截断题面或临时降低图片处理规格；如决定固定图片规格，应在正式前统一披露并用于所有模型。

服务器仍可保持全局max_model_len=262144以服务TB，HLE／ASI客户端采用较短131072。但这两者是不同层：服务器允许256K，并不会替客户端执行128K上限；仅在协议JSON写context也不会生效。短预算要由客户端真实计数、agent原生窗口和必要请求守卫落实。

缩短请求上限主要控制活跃序列长度、KV与单次等待；不减少模型权重，也不意味着固定显存或吞吐按比例下降。实际用量还受图片编码、线性注意力状态、prefill、并发及服务调度影响，不能从128K直接算出可多开几路。

## 正式前必要验收

只需围绕上述一套候选做独立文本／大图／完整程序／长工具历史边界检查：确认真实HTTP输出上限与thinking参数、实际多模态token计数、临界context拒绝或原生压缩行为、length截断记录，以及生成与执行合计1800秒的取消和产物保留。若启用OpenCode，还要测试模型不遵循收尾提示时，外层时限是否真正终止。

本轮没有实施这些检查或修改旧配置。当前文档中的262144／100steps／HLE32768等旧候选仍需主线统一修订后生成实际runner配置；不能把本文建议记成已经落实。
