# 独立专家模型、参数合版与 MoE 的关系

调研日期：2026-10-16（北京时间）。本轮实际联网阅读一手论文和官方实现，区分概念及其对当前三领域 LoRA 方案的意义。仅研究与文档，不运行模型、训练或评测，不改变已有协议和配置。

## 结论

三者有明确且重要的研究联系，但不是同一个概念，也不存在必须绑定使用的关系。
“专家模型”描述能力分工；“参数合版”描述把多个模型的参数变化整合成一组权重的操作；“MoE”描述运行时保留多个模块并按输入混合/选择的模型结构。
当前方案是在一个本来就采用 MoE 架构的底座上，训练三份领域 LoRA，再做静态参数合版；合版前后仍可保持同一种 MoE 架构。
它既不是把三份 LoRA 自动变成底座的三个 FFN 专家，也不因最终只有一个 checkpoint 就变成 dense 模型。
这里 dense ΔW 仅表示把低秩增量还原为普通权重矩阵；它不表示把 MoE 模型转为 dense 模型。

## 先分清两个层级的“专家”

| 维度 | 外部领域专家 | 模型内部 MoE 专家 |
| --- | --- | --- |
| 对象 | 一套可独立运行的模型；LoRA 版本需与其底座共同运行 | 通常是某层的一个 FFN/MLP 模块 |
| 当前例子 | 仓库修复、交互执行（TB+ASI）、学术推理三个 LoRA 分支 | Qwen 底座各个 MoE 层中已经存在的 FFN 专家 |
| 能力来源 | 明确的数据划分与独立微调 | 预训练目标、路由机制及训练数据共同决定 |
| 选择粒度 | 可整次请求选一个分支，也可静态合成单套参数 | 通常每层、每 token 路由 |
| 是否必须一对一对应领域 | 由我们命名和训练划分决定 | 没有普遍保证，不应默认“一个专家等于一个领域” |

两个层级可以同时存在：三份领域 LoRA 的每一份都可以作用于一个内部已含很多 MoE 专家的模型。
同源分支使原参数槽位可对齐；因此按相同 tensor/槽位合版，不等于重新发明一个领域路由器。
即使不修改 router 参数，合版引起的上游 hidden state 变化也可能改变实际路由分布，因此“router 冻结”不等于“路由行为完全不变”。此条是机制推断。

**不依赖关系同样重要：** dense 底座也可以分域微调再合版；MoE 可以从头联合训练，也可以从一个 dense 模型复制模块后训练，不需要先有独立领域模型。两者共享能力分工与整合问题，但一个是参数操作，一个是计算结构。[Task Arithmetic](https://arxiv.org/abs/2212.04089)、[Switch Transformers](https://arxiv.org/abs/2101.03961)。

用式子区分：静态合版先得到 `W* = W0 + Merge(Δ_code, Δ_exec, Δ_reason)`，所有输入使用这套固定权重；Qwen式 MoE 的 routed 分支在运行时计算 `Σ_{j∈TopK(g(h))} g_j(h) E_j(h)`。前者的外部分支选择已经结束，后者的内部路由仍会随输入变化。一般而言，`f(x, Σw_iW_i)` 也不等于多个完整模型输出的 `Σw_if(x,W_i)`，因为神经网络是非线性的。

## 五个代表方法及其连接方式

### 1. Branch-Train-Merge，BTM，2022

一手来源：[论文摘要](https://arxiv.org/abs/2208.03306)、[全文 §2.3、§2.4、§3](https://arxiv.org/html/2208.03306v1)。

- 从共享 seed LM 分出多个完整 LM，在不同文本域独立继续训练。
- 论文的 “Merge” 步骤原义是把训练好的新 LM 加入 ELMforest 集合，不是只指权重平均。
- 推理有两条路线：混合多个完整 LM 的输出概率；或对模型参数做平均，压回一个 LM。
- 参数平均路线只保留一套同尺寸参数，推理成本不随原分支数线性增加；输出集成路线需要多个模型计算。
- 参数平均不需要凭空增加一个内部 FFN router；该论文也不要求平均后再训练一个新 MoE。

与我们关系：当前“同底座分域训练再静态合版”最接近它的参数平均路线；不能据此声称我们的方案就是一个新 MoE。

### 2. Branch-Train-MiX，BTX，2024

一手来源：[论文](https://arxiv.org/abs/2403.07816)、[全文 §3.2](https://arxiv.org/html/2403.07816)。

- 从 dense seed LM 分域训练多个完整领域专家。
- 把各专家对应层的 FFN 保留下来，组成新的 MoE 层；attention、embedding 等其余参数使用平均。
- 增加 token 级 router，然后对组合后的整个模型继续训练，让原本独立训练的模块协同。
- 最终是一张统一计算图，但包含多套 FFN；总参数比单个 seed 多。
- 稀疏选取部分 FFN 控制激活计算；实际 FLOPs 取决于 top-k、专家宽度、替换层数，不能直接说“与原模型完全相同”。

与我们关系：这是“完整领域专家 → 内部 MoE 专家”的直接桥梁；桥梁需要明确的结构转换和路由学习，而不是靠名词自动成立。
论文起点是 dense Llama-2，不能无验证地把相同配方套到已经是 MoE 的 Qwen 分支上。

### 3. Sparse Upcycling，2022 / ICLR 2023

一手来源：[论文](https://arxiv.org/abs/2212.05055)、[全文 §3](https://arxiv.org/html/2212.05055)。

- 只需要一个已经训练好的 dense checkpoint，不要求先训练多个领域专家。
- 将部分 MLP 层复制成多个专家；同一层专家最初可完全相同，新增 router 随机初始化。
- 保留/复制原 attention、normalization 等参数，然后继续训练得到分化和协作。
- 增加总参数，激活计算由路由、capacity factor 等决定；不是“不增加存储的免费扩容”。

与我们关系：反证“MoE 专家必须是先单独训练好的领域模型”；它们可以从同一个 MLP 副本开始。
BTX 可以看作在这种结构构造前，先加入领域专家独立训练阶段；这也是 BTX 论文明确讨论的连接。

### 4. X-LoRA，2024

一手来源：[论文](https://arxiv.org/abs/2402.07148)、[全文 §4.2—§4.2.2](https://arxiv.org/html/2402.07148)。

- 起点是一组已经训练好的 LoRA adapters，很接近我们拥有领域 LoRA 的状态。
- 保留多个 adapter，用 hidden state 预测各层、各 token 的动态系数，再混合 adapter 贡献。
- 论文标准配方冻结底座及已训练 LoRA，只训练 scaling head；代码也允许放开更多参数。
- 最终保留底座、多个 LoRA 及 scaling head；不是先静态平均成一个 adapter。
- 原论文采用双次 forward：先生成 gating 所需 hidden state，再执行带动态系数的 forward，因此不能泛称与单 LoRA 一样的延迟。

与我们关系：若未来确需运行时动态使用现有领域 LoRA，这是更直接的扩展方向；仍需新增训练数据、路由模块和推理实现。
X-LoRA 的动态软混合也提醒我们，“mixture” 不总是“只计算少数 top-k 模块”。

### 5. MixLoRA，2024

一手来源：[论文](https://arxiv.org/abs/2404.15159)、[全文 §3.2、§3.3](https://arxiv.org/html/2404.15159)。

- 在冻结 dense 底座的 FFN 中构建多个 LoRA 专家，基础 FFN 权重共享。
- 训练 top-k router 和 LoRA 专家，并使用辅助负载均衡 loss；attention 也加入 LoRA。
- 专家是训练过程中的多个低秩参数模块，不要求先有若干完整的独立领域 LM。
- 存储是共享底座加多套低秩增量，计算含 routing 及选中专家；共享底座权重不表示所有计算都可共享。
- 原文专门优化共享投影计算；说明真实速度需要考虑非线性、kernel 和 serving，不能只看可训练参数数量。

与我们关系：说明 LoRA 与 MoE 可以结合，但“共同训练多个 LoRA 专家”与“事后组合三个已训练 LoRA”是不同实验。

## 工程反例：构造 MoE 不一定逻辑上必须继续训练

[mergekit 官方 MoE 文档](https://github.com/arcee-ai/mergekit/blob/main/docs/moe.md)把完整模型的 MLP 作为 expert donor，attention/norm 来自 base donor。
其 `hidden` / `cheap_embed` gate 模式用示例 prompts 初始化路由，文档称产物可直接使用；`random` gate 模式适用于之后继续训练。
所以准确说法是：“BTX、Sparse Upcycling 的论文配方包含继续训练；也有免训练的启发式构造，但可构造不等于在我们任务上有收益。”
文档列出可输出 Mixtral、Deepseek MoE、Qwen MoE 架构，不能从输出格式推导“已经支持本项目底座的三份 LoRA 直接拼接”。
当前页属于持续更新的 `main` 文档，只用于核验工具能力与限制，不作为受控精度比较证据。

## 当前底座与合版风险

1. **Qwen本来就是MoE。** 固定[官方 config](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/config.json)与[模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)表明：语言侧40层，各MoE层有256个routed experts、每token选择8个，另有shared expert。这里的256是每层routed FFN数量，不是256个可独立聊天的完整LLM，也不对应我们三个领域的标签。
2. **同结构参数合版保持架构。** 三个分支从同一revision出发、不增删/重排模块，在对应坐标合并更新，最终仍是约35B总参数的Qwen MoE，不是105B，也不把MoE变成dense。35B总/约3B激活不代表只存约3B权重；MoE的计算稀疏与权重存储是不同资源项。
3. **当前候选范围不直接训练routed FFN。** 计划主要覆盖attention投影与shared MLP，冻结routed experts/router/视觉，实际模块白名单仍需执行前固定。因此三个领域分支的差异主要是这些适配模块的更新，不是各自新增或指定三个内部专家。是否真的形成领域专长须由独立任务验证。
4. **冻结router不保证冻结路由。** [Transformers官方实现](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py)以`F.linear(hidden_states, router_weight)`得到logits，再softmax/top-k。即使router权重不变，attention或前层更新改变hidden state，也可能换选中专家；shared expert更新也会影响后续层。此为源码函数推断，不是本项目实测退化。
5. **已有直接研究MoE合版路由风险的论文。** [HARC：When Model Merging Breaks Routing](https://arxiv.org/html/2606.03391v1)在同一OLMoE底座的数学/代码分支上，通过交换router等对照发现路由失配可能造成合版退化，并提出校准。其[训练脚本](https://github.com/huangcb01/HARC/blob/main/scripts/train/sft_olmoe.sh)为全参微调；这不证明我们冻结router的Qwen3.6 LoRA会同样退化，也不构成立刻增加校准阶段的理由。
6. **坐标与功能不要混淆。** 同一checkpoint分支且未重排时，expert索引有共同起点；独立预训练或重排后的模型则不能仅凭相同编号认定专家功能对齐。同步置换expert张量与router相应输出行可保持函数，这一代数对称性说明为何需要保留原映射。一般参数置换与合版问题可参考[Git Re-Basin](https://arxiv.org/abs/2209.04836)，不据此给当前同源LoRA额外增加匹配算法。

若后续需要解释合版退化，可在同一独立prompt、固定相同teacher-forced token下，比较逐层top-k重叠和路由概率，再结合任务结果分析。路由变化本身不代表错误，不能要求新模型完全复制Base路线。这是诊断建议，不作为新选模目标或当前必做实验。

## 对当前研究方案的判断

1. 继续保留“共享底座 → 三领域 LoRA → 对真实 ΔW 做 AVG/TIES 等静态合版”的主线；底座本来是 MoE 不构成改路线的理由。
2. 固定结构时，合版不会新增三套领域 FFN，也不会把总参数扩为三个底座；底座原有 MoE 路由仍在。
3. 单独报告“底座架构”“分支训练方式”“组合方式”三个因素，避免把 MoE 底座带来的能力归因为分域合版。
4. 先比较同数据混训、各领域单支、静态合版；只有静态合版存在可复现的跨领域干扰时，再研究动态 adapter 路由的增益是否覆盖成本。
5. 若加动态路由，先做请求级选 LoRA 的小基线，再考虑 token 级 mixture；它比直接改造已有 MoE FFN 更容易定位收益来源。此条是研究建议。
6. 现有 MoE 的原 expert index、router 与其他层共同训练；拼接/替换专家会改变容量、路由语义及运行实现，应视为新的结构实验，而非合版的自然优化。此条是机制判断。

评测需同时看三领域任务成功率、最差域退化、跨领域混合任务，以及真实显存、prefill/decode 延迟和任务总费用；动态方法还要看错路由与专家利用率。
这些文献证明“关系存在、路径可实现”，并不证明把当前 MoE 底座再做一层领域 MoE 就更优。
