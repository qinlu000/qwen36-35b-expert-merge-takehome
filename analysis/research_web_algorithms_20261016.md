# 算法与合版：本轮联网核验及最小建议

核验日期：2026-10-16（北京时间）。本轮实际通过 research / ego-browser 只读访问论文正文、PEFT/ms-swift/Transformers 官方源码与模型配置；不是重述旧笔记。未训练、未合版、未跑评测、未调用模型 API。范围沿用三专家、ms-swift + PEFT、BF16 LoRA、AVG/TIES 与同数据混训；不变更候选训练模块范围，执行前仍需固定白名单。

## 1. 先采纳的结论

- **继续用 dense Δ AVG + dense Δ TIES。** 算法的关键在完整更新 `Δ_i = s_i B_i A_i`，不在 adapter API 的方法名称。PEFT `linear/ties` 与本项目想比较的两个 dense 方法并不等价。
- **建议 TIES 以 density=0.2、global scale=1 为单一起点，执行前冻结具体语义。** 原论文确有 top-20% / λ=1 的免调参配方；这给默认值提供出处，但其证据来自 IA³/T5/ViT，不能证明 Qwen3.6 LoRA 最优。[TIES §5](https://arxiv.org/html/2306.01708v2)
- **最终保存完整 BF16 权重；计算 Δ、剪枝、符号投票及加回 base 用 FP32，最后一次转换。** 这让本轮比较免受额外低秩截断影响；不是提高模型能力的已证实技巧。
- **同数据 Mixed 必须保留。** AVG 至多累积三个 rank-r 子空间；TIES 的逐元素掩码还可能产生满秩更新。Mixed 的 rank=r 与合版容量并不严格相同，不能把胜负完全归因于专家分工。
- **先冻结具体合版语义，再谈哪个方法更好。** tensor/global trim、disjoint mean/sum、符号平票规则、weights 与 λ 都足以改变结果；仅记录“TIES, density=.2”不能复现。

上述后三项分别是代码核验和线性代数推断，不是论文对本项目的性能结论。

## 2. 本轮读到的一手证据，及其适用边界

| 主源 | 已核验事实 | 本项目怎么用 |
| --- | --- | --- |
| [Task Arithmetic v3](https://arxiv.org/html/2212.04089v3) | 任务向量是同一模型微调后减去微调前的权重；用 held-out validation 定 scale | 定义 Δ 与独立 dev 选择原则；AVG 是 `(ΣΔ)/3`，不把它和未归一化 task-vector sum 混称 |
| [TIES v2](https://arxiv.org/html/2306.01708v2) | 小幅更新清零、按总移动量选符号、只合符号一致项；给出上述固定配方 | 保留第二候选；原 PEFT 实验主要是 IA³，不能拿“PEFT”一词代替 LoRA 证据 |
| [DARE / Super Mario v3](https://arxiv.org/html/2311.03099v3) | 对同源 SFT 的 dense delta 随机丢弃并乘 `1/(1-p)`，再接其他合版方法；decoder 用已有 instruct/math/code 模型 | 领域专精先例、备选 sparsifier；不照搬 90%/99% 丢弃结论到本题 LoRA |
| [Model Stock v1](https://arxiv.org/html/2403.19522v1) | 以 CLIP/ImageNet 为主，从同任务不同 seed 的逐层 thin-shell 观察构造少模型平均并锚定 base | 解释为何需要看层级范数/夹角；其共同中心假设不直接成立于三个异质任务专家，本轮不加候选 |
| [KnOTS v1](https://arxiv.org/html/2410.19735v1) | LoRA task-update 对齐可能弱于全量微调；拼接 dense 更新经 SVD 建公共基，再接合版 | 提醒“dense 还原正确”不保证合版有效；SVD 对齐留后续，不扩大当前矩阵 |

论文实验对象与我们的生成式仓库/终端/科研/学术任务不同；它们支持可检验的方法组织，不提供本题提升幅度或四卡耗时保证。Model Stock 的 v3 URL 本轮返回 404，实际读取 v1，不将未读版本算已核验。

## 3. PEFT 的四类 API，不能互相替代

本轮 GitHub API 核验 PEFT 当前提交为 **`e8e8a7c40af177652ad88a3682d64e0480f5f919`**（2026-10-15）；文档页面显示 v0.21.0。以下实现结论固定到 [lora/model.py](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)。它不证明本项目已安装该版本，执行前仍应对实际 lock 核对。

| `combination_type` | 实际计算 | 与当前目标的关系 |
| --- | --- | --- |
| `cat` | `A*=concat(w_i s_i A_i, dim=0)`，`B*=concat(B_i, dim=1)`；新 scale=1 | 对普通 LoRA 精确得到 `Σ w_i Δ_i`，允许不同 rank，新 rank 为各 rank 之和；可作 AVG 等价验收路径，不是新算法 |
| `linear` | 分别对 A/B 做带 `sqrt(abs(w_i s_i))` 的和，并在一侧保留符号 | 乘回去含跨专家交叉项，通常不等于 `Σw_iΔ_i`；三个 rank 必须相同也不能修复这个问题 |
| `ties` / `dare_ties` | 分别在 A、B 因子上调用相应操作 | 是因子空间合版；不能作为本项目 dense TIES 的实现 |
| `svd` / `ties_svd` | 先 `get_delta_weight()`，在 dense 空间合版，再 SVD 重建 adapter | 默认输出 rank=max 输入 rank，通常有截断误差；文档明确 SVD 路径不支持 BF16/FP16，须另转精度 |

依据：[固定源码中的 `_check_add_weighted_adapter`、`add_weighted_adapter`、两个 generalized 函数](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)，[官方 LoRA 文档的合版说明](https://huggingface.co/docs/peft/v0.21.0/en/package_reference/lora)。

**为什么不能平均 A/B：** 对两专家，`(B1+B2)(A1+A2)` 除目标的 `B1A1+B2A2` 外还有 `B1A2+B2A1`。此外 `BA=(BR)(R⁻¹A)`，同一 dense 更新有多种因子表示；因子坐标相近/同号不具有与 dense 参数相同的意义。这是代数事实，不需要增加实验才能确认。

**rank 限制要精确表述：** AVG 的 rank 至多 `Σr_i`，所以 cat 可精确表示；TIES 的逐元素 trim/sign mask 不是矩阵乘法，结果一般不保留此秩上界，甚至可能满秩。因此“把 TIES adapter rank 提到 3r 就必定无损”也不成立。该点是本项目的线性代数推断，论文并未给本模型实测秩。

**精度陷阱：** PEFT `get_delta_weight()` 实际乘 `transpose(B@A, fan_in_fan_out)*scaling`；CPU 上临时 FP32 计算后会转回原 dtype，GPU BF16 路径也不自动保证 FP32 累加。因此不能只调用该方法就声称整个合版在 FP32；应显式对本轮标准 LoRA 的 A/B 转 FP32，再逐张量处理。[固定 layer.py](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/layer.py)

## 4. TIES 需要再锁定的两个实现细节

**global 与逐张量 trim 不同。** 作者参考代码先将 state_dict 展平为完整任务向量，再为每个专家按全向量绝对值阈值保留；PEFT 的 `merge_utils.ties` 按传入 tensor 剪枝。若逐层调用它，每层固定保留20%，不同于全模型只保留最大的20%。作者阈值法遇同幅值时可能多留，PEFT `topk` 则按数量截断。[作者固定 merge_utils.py](https://github.com/prateeky2806/ties-merging/blob/44e7891fc84f3de7e4caa52664cd864ca3715e91/src/utils/merge_utils.py)，[PEFT 固定 merge_utils.py](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/utils/merge_utils.py)

**本轮建议：** 为保持实现简单，采用 FP32 dense、逐目标权重张量 trim 的 PEFT 数值核心，`density=.2`、`majority_sign_method=total`、disjoint mean、λ=1；在报告中明确这是逐张量 TIES 实现，不声称逐行复现作者全向量参考代码。若团队坚持严格原实现，应在执行前改为 global trim 并冻结；不能让它成为看完 dev 后的第三候选。

**weights 不要重复除以3。** PEFT `task_arithmetic` 是加权求和，而 `ties` 在投票后先乘 weights，再除以符号一致的非零项数量。因此 AVG 对应 `[1/3,1/3,1/3]`；若要通常定义的等权 disjoint mean，dense TIES 应传 `[1,1,1]` 并另设 λ。向二者都传1/3，会把该 TIES 更新额外缩小三倍。[同一固定数值核心](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/utils/merge_utils.py)

需同时记录零和符号平票规则：PEFT `total` 在总和为0时取正号；作者实现另有 zero-sign majority 处理。该差异通常只影响部分坐标，但不能省略。这里提出冻结实现，不新增调参维度。

## 5. rank、scale、target 与 Qwen MoE 的边界

数学上 dense Δ 可以合不同 rank/alpha；**本轮统一 rank、target 和 LoRA 变体是控制变量与工程简化要求**，不是声称只有相同 rank 才能合版。每层实际 `s_i` 必须来自配置：标准 LoRA 为 `alpha/r`，rsLoRA 为 `alpha/sqrt(r)`，还须展开 rank/alpha pattern。标准 LoRA 的当前计划无需改成 rsLoRA/DoRA/PiSSA 等变体。[官方配置说明](https://huggingface.co/docs/peft/v0.21.0/en/package_reference/lora)

必须一致并保存：base 的完整 revision、tokenizer/processor/chat template、实际全模块名与形状、rank/alpha/scaling、bias、modules_to_save、初始化方式及 dtype。不要把同家族、同形状当共同 base；特殊 token 的 embedding index 也必须一致。[官方 model merging](https://huggingface.co/docs/peft/v0.21.0/en/developer_guides/model_merging)

本轮官方 [Qwen config，固定 995ad96](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/config.json) 确认为 `Qwen3_5MoeForConditionalGeneration`，混合 linear/full attention，256 个 routed experts、每 token 8 个，以及视觉配置。[ms-swift 7f2329ff 的模型注册](https://github.com/modelscope/ms-swift/blob/7f2329ff5277e623bcb09350cf9ae6b94a13a22c/swift/model/models/qwen.py) 明确包含 Qwen3.6-35B-A3B。

- 官方 Transformers [Qwen3.5-MoE 源码](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py)（本轮读 main）中，线性注意力有 `in_proj_qkv/z/b/a`；旧 q/v 清单不覆盖它们。routed experts 用融合 3D `nn.Parameter`；shared MLP 与 `shared_expert_gate` 含 `nn.Linear`。
- PEFT 对 2D/3D `nn.Parameter` 提供 `target_parameters`，但本轮固定源码的 **`add_weighted_adapter` 明确拒绝带 `target_parameters` 的任意 adapter**，不能承诺 cat/ties 路径兼容 routed experts。多 adapter 支持本身与 weighted merge 支持是两回事。[固定检查函数](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)
- [PEFT 官方 MoE 注意事项](https://huggingface.co/docs/peft/v0.21.0/en/package_reference/lora#targeting-nnparameter-directly)还说明未合并的专家 LoRA 可能逐专家物化更新、拖慢推理；这不是“3B激活所以35B训练/服务天然便宜”的证据。
- [ms-swift 四卡示例](https://github.com/modelscope/ms-swift/blob/7f2329ff5277e623bcb09350cf9ae6b94a13a22c/examples/models/qwen3_5/transformers.sh) 是 **Qwen3.5**、2K 长度、rank8、all-linear、ZeRO3，不是本题 Qwen3.6/长轨迹吞吐证明。`all-linear` 还可能包含 shared gate；本轮应落实既定注意力投影/shared MLP 白名单，冻结门控与视觉范围，不直接照搬示例。

这些限制支持保持当前候选方案中冻结 routed expert/router/视觉侧的范围；它们不证明当前范围最优。冻结 router 权重也不保证路由输出不变，上游 hidden states 仍随 LoRA 更新。

## 6. 数据混合与专家冲突：先做低成本可解释诊断

**本项目建议，不是文献给出的最优比例：** 继续保留修复、终端、科研执行、学术QA四个内容桶；交互专家里的终端/科研分别计 processed token、assistant supervised token、完整任务数和长度分位数。按行抽样容易让短任务与多 rollout 家族改变实际权重；固定 token 配额应在分组、分段、loss mask 后计算。Mixed 复用三专家所有样本与相同出现次数，不另造一批更容易的数据。

同一批样本、token相同仍不等于严格同优化：Mixed 的训练步数/学习率进度与三个分支不同，合版有效容量也不同。冻结并披露总 processed/supervised token、effective batch、优化器更新数、schedule、padding与GPU时间；不要把预算对齐说成精确等 FLOPs 或完全隔离因果。

| 无需额外训练的诊断 | 具体记录 | 能回答 / 不能回答 |
| --- | --- | --- |
| 更新强度 | 每层 `||Δ_i||F`、`||Δ_i||F/||W0||F`，全局汇总 | 找某专家尺度过大或某类模块更新缺失；不据此自动给它降权 |
| 几何冲突 | 三对专家的 dense Δ 余弦，按层及整体记录 | 找抵消方向；高余弦不证明能力相同，负余弦不证明某专家有害 |
| TIES 影响 | 实际保留率、至少两专家非零重叠坐标上的异号率、每坐标保留专家数、`||Δ_TIES||/||Δ_AVG||` | 区分剪枝/冲突/缩放导致的变化；几何指标不能替代真实成功率 |
| 现有 dev 分项 | 修复/终端/科研/QA，以及图文、工具解析失败、超时 | 看平均分是否掩盖科研或视觉退化；不把小 dev 当四项 benchmark 的总体证明 |

这些诊断随同一次导出/既定 dev 保存即可，不为找漂亮解释再加一轮训练、梯度相似性计算或层级加权搜索。专家仅测目标域时，也不能声称已经测过所有专家的跨域遗忘。

## 7. 当前窗口的最小矩阵与选择规则

沿用 [dev_ablation_plan.md](dev_ablation_plan.md)，不增加训练分支；val-loss总约100K processed token、预定中/末两个点，默认末点，仅作监控及有限 checkpoint 选择。task-dev在训练前按来源任务/仓库/模板族隔离，正式 Base 成绩也不用于挑配方。

| 对象 | task-dev | 作用 |
| --- | --- | --- |
| Base、Mixed、AVG、TIES | 每对象修复10、终端10、科研10、QA40 | 唯一全域算法比较；AVG/TIES各一配方 |
| E-code | 修复10 | 判断目标专长 |
| E-exec | 终端10 + 科研10 | 两桶分别检查，不能只报合分 |
| E-reason | QA40 | 广域与图文分项 |

共150个工具trial、200次QA，与原建议一致；不是声称这些任务已恢复或3h一定跑完。四域成功/准确率等权宏平均，列相对Base的分项变化；AVG/TIES若仅一题级差异，依预定近似持平规则优先AVG，不追加weight/density扫参。这个规则是小样本下控制选择自由度，不是统计显著性结论。

参数诊断、val-loss、task-dev只承担各自用途；正式全评仍是Base与唯一最终合版四项、专家目标项完整范围。Mixed若只跑dev，报告只允许说“在这套dev上与Mixed相比”，不能说正式四项超过混训。

## 8. 采用、备选与不纳入

| 级别 | 方法 / 做法 | 原因 |
| --- | --- | --- |
| 采用 | FP32 dense AVG、固定逐张量TIES、完整BF16导出、同数据Mixed、上述轻诊断 | 覆盖核心研究问题且候选数有界；TIES具体逐张量语义须训练前共同冻结 |
| 验收备选 | 普通LoRA的PEFT cat作AVG数值等价对照；不训练新分支 | 有代数/源码等价性，排查scaling或模块映射；实际误差受dtype/加法顺序影响 |
| 后续备选 | DARE、KnOTS-TIES、rank匹配Mixed | 分别增加随机性、SVD成本、额外训练，适合当前结果完成后的独立问题 |
| 本轮不做 | Model Stock、WIDEN、层级权重搜索、可训练合版、在线RL、routed专家扩训 | Model Stock同任务共同中心与本题异质专家不匹配；其余超出已定变量和窗口，不因论文新而加入 |

算法侧仍需在执行前固定实际安装版本、模块白名单、TIES trim范围/边界语义、最终数据配额，并验收独立dev可执行性，不通过正式测试反推。

访问说明：部分 raw.githubusercontent 请求失败，已改用 GitHub contents API读取同提交源码；两种猜测的 ms-swift Qwen3.6 best-practice URL 返回404，故本文只引用已成功读取的模型注册与真实Qwen3.5示例，不声称存在专门Qwen3.6配方页。
