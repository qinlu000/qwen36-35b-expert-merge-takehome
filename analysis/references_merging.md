# 同一 base 的领域专家训练与参数合版：可复用配方核验

核验日期：2026-10-15。范围：六个主资源，优先原论文及作者实现；使用 research、ego-browser 技能只读访问公开页面与源码。没有运行训练、合版、评测或模型 API，没有读取 benchmark 题目或答案。下文将来源事实与本题推断分开。代码链接尽量固定到本次看到的提交；论文版本日期与仓库提交日期不等同于方法发布日期。

## 结论与两条路线

**路线 A，优先采用：同一 base 独立训练三个领域 LoRA，恢复 dense ΔW，比较均匀平均与 TIES。** 它组合了 Task Arithmetic/TIES 的更新空间定义、MergeLM 的 instruct/math/code 专精组织方式，以及 mergekit 的逐张量处理思路。三类可按代码、推理、工具任务组织；专家数由已经准备好的训练数据决定，不必机械地对应四个 benchmark。

**路线 B，有剩余时间再采用：复用同一批 LoRA，比较 dense TIES 与 KnOTS-TIES。** KnOTS 先为各层更新建立共同 SVD 基，再在对齐空间执行 TIES，最后重建完整更新；不需要重训专家。但它引入 SVD 的时间、内存及模型适配成本，作者的语言实验又是 NLI 分类，故本题只能视为需要验证的扩展，不能承诺收益。线性求和下 KnOTS-TA 与 TA 等价，不值得将二者作为不同有效算法比较。

以上是**本题建议**，不是已有论文对 Qwen3.6-35B-A3B 的实证结论。最小主方案保留 AVG 与 TIES 两种合版；DARE 和 WIDEN 不同时加进必做矩阵。

## 1. Task Arithmetic：最清楚的更新空间定义及混训对照参考

- 原论文：[Editing Models with Task Arithmetic，arXiv v3，2023-03-31](https://arxiv.org/html/2212.04089v3)，初稿 2022-12-08，ICLR 2023。
- 作者实现：[mlfoundations/task_vectors，826a64c，2023-03-08](https://github.com/mlfoundations/task_vectors/tree/826a64c67082fab0f40628233287948f0f8d7fa3)。

**核验事实。** 作者定义任务向量为同一预训练模型微调前后的权重差，按坐标相加并加回 base；缩放系数由 held-out validation 选择。公开仓库主要提供 CLIP ViT 的八任务 checkpoint 和向量运算，论文也有 T5/GLUE 实验。[论文 §2、§4](https://arxiv.org/html/2212.04089v3)、[TaskVector 源码](https://github.com/mlfoundations/task_vectors/blob/826a64c67082fab0f40628233287948f0f8d7fa3/src/task_vectors.py)

论文附录包含八任务 joint fine-tuning 对照，并报告该设置下混训优于向量合版；不能据此假定合版必定优于混训。该对照沿用微调超参数，但本次没有确认其与所有专家训练总量严格等 token/等算力。[论文附录 D](https://arxiv.org/html/2212.04089v3)

**本题推断。** 最适合作为 AVG/TA 的定义与 dev 选全局 scale 的依据，不能直接作为 35B MoE LoRA 训练脚本。预算对照需要本题重新规定。

## 2. TIES：推荐的第二种合版方法

- 原论文：[TIES-Merging，arXiv v2，2023-10-27](https://arxiv.org/abs/2306.01708v2)，初稿 2023-06-02，NeurIPS 2023。
- 作者实现：[prateeky2806/ties-merging，44e7891，2024-02-03](https://github.com/prateeky2806/ties-merging/tree/44e7891fc84f3de7e4caa52664cd864ca3715e91)。

**核验事实。** 方法在任务更新上依次去除小幅变化、确定符号、合并符号一致的更新。仓库有 T5 训练入口以及 T5-Large、IA3 的平均/TA/TIES 例子；README 明确设置 validation，并搜索 scale。其演示包含 top-k 保留比例、按数值质量选符号和 disjoint mean。[原论文](https://arxiv.org/abs/2306.01708v2)、[固定版本 README](https://github.com/prateeky2806/ties-merging/blob/44e7891fc84f3de7e4caa52664cd864ca3715e91/README.md)

这些例子不是现代 causal-LM LoRA 的通用训练配方。README 的训练演示甚至设置 `num_batches=2`，只能证明入口，不能照搬为充分训练预算。未从这一演示确认相同总 token 的混训对照。

**本题推断。** 对已经训练好的三份专家 dense Δ 做 TIES，不增加训练侧变量；只保留一个全局 scale 和少量 density，最适合本题的低复杂度消融。它是否比平均更好仍需要 dev 与最终评测证据。

## 3. DARE / MergeLM：与本题领域拆分最接近的先例

- 原论文：[Language Models are Super Mario，arXiv v3，2024-06-13](https://arxiv.org/html/2311.03099v3)，初稿 2023-11-06，ICML 2024。
- 作者实现：[yule-BUAA/MergeLM，6d49ad9，2024-05-05](https://github.com/yule-BUAA/MergeLM/tree/6d49ad96fd69c92013654b837041b868aa806564)。

**核验事实。** DARE 随机丢弃更新参数，再按保留概率的倒数重缩放，可接入其他合版算法。论文的 decoder 合版选用共同 Llama-2-13B 来源的 WizardLM、WizardMath、llama-2-13b-code-alpaca；作者特意排除基于 CodeLlama 的 WizardCoder，不能把同架构误当成同一 base。[论文实验设置](https://arxiv.org/html/2311.03099v3)

仓库对 BERT/RoBERTa 的 GLUE 任务提供真实单任务与多任务微调脚本；decoder 专精模型则采用已经微调好的外部 checkpoint，故它不证明作者重新按统一预算训练了 instruct/math/code 三专家。[README](https://github.com/yule-BUAA/MergeLM/blob/6d49ad96fd69c92013654b837041b868aa806564/README.md)

论文对 encoder 将原 train 按 90/10 分为训练/验证，并把原 validation 当测试；另报告多任务 oracle。decoder 合版搜索 scale、TIES retain ratio；本次核对段落未明确找到 decoder 的独立 dev 选择流程，因此不把其最优结果作为严格 test 隔离的证据。[论文 §4、附录 A](https://arxiv.org/html/2311.03099v3)

**本题推断。** 最值得复用的是领域专家、同源核验、单专家/合版能力保留表格的组织。DARE 的随机种子与稀疏率增加候选数，暂不列必做；论文中高丢弃率的成功不能外推到本题 LoRA 更新。

## 4. WIDEN / MergeLLM：完整合版与评测管线参考

- 原论文：[Extend Model Merging from Fine-Tuned to Pre-Trained Large Language Models via Weight Disentanglement，arXiv v1，2024-08-06](https://arxiv.org/html/2408.03092v1)。
- 作者实现：[yule-BUAA/MergeLLM，9178ef9，2024-08-07](https://github.com/yule-BUAA/MergeLLM/tree/9178ef93846aa1df9a3a2c28886a346184edfa79)。注意它与前节的 `MergeLM` 是两个仓库。

**核验事实。** WIDEN 将权重分解为幅度与方向后自适应融合，主要处理 FT/PT 更新尺度不同的情况。实验包括 Qwen1.5-Chat 与 Sailor，以及 Llama-2 来源的 instruct/math/code 专精模型。仓库实现八种合版方法，分别组织保存完整模型、生成各领域输出和评分；入口直接加载完整模型，不是 LoRA 因子合版。[论文](https://arxiv.org/html/2408.03092v1)、[README](https://github.com/yule-BUAA/MergeLLM/blob/9178ef93846aa1df9a3a2c28886a346184edfa79/README.md)、[merge_llms.py](https://github.com/yule-BUAA/MergeLLM/blob/9178ef93846aa1df9a3a2c28886a346184edfa79/merge_llms.py)

论文说明做超参数网格搜索；本次核对的正文及入口未确认独立 dev 和统一专家训练预算。它采用外部已有专精 checkpoint，不能据此宣称本题的三次 SFT 已有现成训练时间保证。

**本题推断。** 应借鉴其专家能力表、不同方法统一评测和产物命名，避免照搬旧版本环境。若本题专家全部同一 base、同训练设置、较小 LoRA 更新，FT/PT 大幅尺度错配不是首要问题，故不优先增加 WIDEN。

## 5. mergekit：合版执行工具，不能替代训练或选择协议

- 工具论文：[Arcee's MergeKit，EMNLP Industry 2024](https://aclanthology.org/2024.emnlp-industry.36/)。
- 官方实现：[arcee-ai/mergekit，9eeb539，2026-09-12](https://github.com/arcee-ai/mergekit/tree/9eeb539892c6753b032ea164e818b44a8c7a401b)。本次查看的是已更新 API 的版本，不应与旧教程混用。

**核验事实。** 工具提供线性平均、TA、TIES、DARE 等方法，支持 CPU/GPU 与延迟加载。方法配置区分 base、权重、density、全局 lambda 及输出 dtype；不同算法的归一化与 scale 定义需固定。[README](https://github.com/arcee-ai/mergekit/blob/9eeb539892c6753b032ea164e818b44a8c7a401b/README.md)、[方法文档](https://github.com/arcee-ai/mergekit/blob/9eeb539892c6753b032ea164e818b44a8c7a401b/docs/merge_methods.md)

`ModelReference` 可表达 `base+LoRA`；其 `.merged()` 路径通过 PEFT 先把单个 adapter `merge_and_unload()` 成完整 checkpoint，再进入后续合版。这与分别对 A、B 做平均不是同一个操作。[common.py](https://github.com/arcee-ai/mergekit/blob/9eeb539892c6753b032ea164e818b44a8c7a401b/mergekit/common.py)

它本身不训练领域专家，也不自动提供独立 dev 或预算匹配。README 的 `mergekit-moe` 是把多个 dense 模型组装为 MoE，不等于支持任意现成 MoE 的同架构参数合版；也不等于 Qwen3.6 多模态配置已被本题环境验证。

**本题推断。** 可用作逐张量处理与算法参考；使用前仍需确认 Qwen3.6 架构、自动模型类、完整配置与未训练参数的保留。不要为了使用工具而改造为新的 routed MoE。

## 6. KnOTS：真正针对 LoRA 的对齐与合版

- 原论文：[Model merging with SVD to tie the Knots，arXiv v1，2024-10-25](https://arxiv.org/html/2410.19735v1)，作者仓库标记 ICLR 2025。
- 作者实现：[gstoica27/KnOTS，baa35e8，2025-04-03](https://github.com/gstoica27/KnOTS/tree/baa35e85768b8841820d35edc3e41b25304248c5)。

**核验事实。** 仓库有从共同初始化训练 LoRA 的入口。`LoRAHandler` 先计算各层 `B@A`；`SVDMerger` 拼接各模型的 dense 更新，取得共享基，再对变换后的表示执行剪枝/符号合版并重建更新。它不是简单对 A、B 做对齐平均。[README](https://github.com/gstoica27/KnOTS/blob/baa35e85768b8841820d35edc3e41b25304248c5/README.md)、[ft_handlers.py](https://github.com/gstoica27/KnOTS/blob/baa35e85768b8841820d35edc3e41b25304248c5/ft_handlers.py)、[task_merger.py](https://github.com/gstoica27/KnOTS/blob/baa35e85768b8841820d35edc3e41b25304248c5/task_merger.py)

语言示例使用 Llama-3-8B 的六个 NLI 分类任务，rank=16、alpha=16，仅 attention 投影。搜索脚本先在 `val` 选参数，再在 `test` 评估；但会为每个任务注入对应 classification head，并非一个生成模型面对全部 agent 任务的直接证据。[语言配置](https://github.com/gstoica27/KnOTS/blob/baa35e85768b8841820d35edc3e41b25304248c5/configs/llama8B_r16_knots_ties.py)、[NLI 搜索脚本](https://github.com/gstoica27/KnOTS/blob/baa35e85768b8841820d35edc3e41b25304248c5/eval_scripts/nli_pertask_linearsearch.py)

论文明确：KnOTS-TA 在线性操作下退化为普通 TA；其作用在 TIES 等非线性处理。论文还对 DARE 使用多个随机种子，并按 held-out validation 选择。本次未核到“同总训练 token 的生成式混训”对照。[论文 §4、附录 C](https://arxiv.org/html/2410.19735v1)

**本题推断。** 适合路线 B，但不能将论文提升幅度当成本题预期。作者 handler 的 `B@A` 没有显式乘一般 LoRA scale；其 alpha=r 示例 scale 为 1。本题移植时必须纳入实际 adapter scaling，且原始 float64 dense SVD 的成本需要验证。

## 统一的正确性与选择协议

### dense Δ 与 adapter 的关系

对标准 LoRA，每层更新为 `Δ_i = s_i B_i A_i`。平均更新是 `Δ_avg = Σ_i w_i Δ_i`；最终模型是 `W0 + λ Δ_avg`。分别平均 A 与 B 通常产生额外的交叉项，不能称作正确的 dense Δ 平均。相同 base、相同张量坐标及完整 scaling 是前提；仅同模型家族或同形状不够。

沿用此前只读核验：当前 [PEFT 的 LoRA 合版源码](https://github.com/huggingface/peft/blob/main/src/peft/tuners/lora/model.py) 中，`linear/ties/dare_ties` 路径分别处理 A、B；`ties_svd` 才先得到 dense Δ，但随后有秩截断。此链接是移动分支，访问日期为本笔记日期，不能代替未来安装版本核验。直接保存完整合版权重可以避免把 SVD 截断误差混入 AVG/TIES 比较。

### 对 Qwen3.6-35B-A3B 的迁移边界

沿用此前核验的 [Qwen 官方模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)：35B 总参数、3B 激活参数，具有视觉编码器、Gated DeltaNet/full-attention 混合层和 routed/shared MoE。上述论文的 CLIP、T5、Llama-2、Llama-3、Qwen1.5 结果，均不自动验证这一架构。

本题建议统一训练文本 attention（包括线性注意力投影）与 shared MLP，冻结 routed expert/router/视觉侧；这是减少适配成本的研究选择，不是已被文献证明的最优训练范围。不得把旧模型的 `q_proj/v_proj` 列表当成覆盖全部 Qwen3.6 attention。冻结 router 权重也不保证路由结果固定，因为上游 hidden states 仍会改变。

### dev、预算对照与题面全评要求

1. 专家训练、混训对照、合版 dev、最终测试必须隔离。合版候选只在独立 dev 选 scale/density，随后冻结 checkpoint、提示模板、工具 scaffold、推理预算和评分规则。
2. 最简单的训练对照是三领域混合 LoRA；其总训练 token 与三个专家累计 token 匹配。相同 rank 的对照仍存在合版有效秩更高的容量差异，不能仅据此断言增益来自专业化；rank 匹配对照可作为扩展。
3. **题面要求每个专家至少完成其目标 benchmark 全量评测；最终选定合版完成四项全量评测。** 不能用 dev 诊断替代单专家目标 benchmark 全评。其他合版候选可在独立 dev 比较，不能把每个候选的四项全评强加为最低矩阵。
4. 混训对照若只在 dev 评估，只能支持 dev 上的训练策略比较；不能声称最终四项全量测试均优于混训。混训四项全评是额外扩展，需要单独计入预算。
5. 一旦查看最终测试表现，不再据此重新挑专家、混合权重、scale、density 或推理配置。多次采样保留题目层面的相关性，不把同题重复运行当成独立新题。

## 应避免的误用

- 把领域提示词、多 adapter 动态路由或多模型投票称为已经完成参数合版；本题需要真实训练和单份权重产物。
- 将来自不同祖先 checkpoint 的模型，统一减去一个不匹配的 base；MergeLM 对 WizardCoder 的排除正是反例。
- 平均 LoRA A/B、忽略 scale，或无声明地使用截断 SVD 后声称复现 dense AVG/TIES。
- 将 `mergekit-moe` 与“现成 MoE 的同架构合版”混为一谈，或假定旧 dense 模型脚本直接兼容 Qwen3.6。
- 为每个 benchmark 事后选不同 head、adapter 或合版模型，却把结果汇总为一个通用单模型成绩。
- 照搬旧作者仓库中的自动下载/AlpacaEval 付费 judge 命令；本次只读源码，没有执行这些入口。
- 把 DARE 的高稀疏率成功、KnOTS 的提升幅度或 WIDEN 的 FT/PT 效果当成这次实验的结果保证。

当前证据支持“已有可复用的训练—合版—验证组织方式”，不支持“本题一定提升”或“59h 核心窗口一定足够”。实际训练吞吐、长序列显存、合版成本与 benchmark 总耗时仍须由后续获准的小规模测量确定。
