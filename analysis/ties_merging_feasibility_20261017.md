# TIES 合版可行性（只读研究，2026-10-17）

**建议：新增“PEFT 0.20.0 逐模块 dense-delta TIES → truncated SVD64”作为第二种端到端合版方法，保留主AVG64。** 推荐固定 density=0.2、majority_sign_method=total、四个输入权重均1、最终λ=1、输出r64/alpha64；这些是拟议固定配方，不是已验证最优配置。本轮没有导出TIES、运行真实专家SVD、训练、模型调用或评测。

## 1. 来源与适用范围

原方法以共同初始化的参数差值作为 task vector，经过 trim、elect sign、disjoint mean，再加回基座。它改变逐坐标保留哪些专家更新，因而与线性平均/任务向量系数缩放有实质差别。[TIES论文，固定 arXiv:2306.01708v2，§4/Algorithm1](https://arxiv.org/html/2306.01708v2)

论文给出的无需本项目验证集调参的参考配方是保留20%、按幅值总量选符号、disjoint mean、λ=1；该配方来自论文的IA³实验，不是对本项目35B LoRA的效果保证。[同一论文§5及Appendix C.4](https://arxiv.org/html/2306.01708v2#A3.SS4)

本轮核读 HPC 已安装 `/data/user/qinlucao/projects/apex-takehome/artifacts/envs/sft/lib/python3.12/site-packages/peft`，`__init__.py` 声明 **0.20.0**；核查文件为 `tuners/lora/{model,layer}.py` 与 `utils/merge_utils.py`。公开对照固定到官方 **v0.20.0**，不使用main分支行为推断。[PEFT v0.20.0 model.py](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/model.py)、[layer.py](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/layer.py)、[merge_utils.py](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/utils/merge_utils.py)

本项目四个冻结输入均r16/alpha32、普通LoRA、相同Base revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，只有同一310个LM attention/linear-attention/shared-expert模块，620个A/B张量；无routed-expert、vision或router合版。输入与精确AVG配方见[现有merge配置](../configs/merge/four_experts_avg_v1.json)，形状和已有产物记录见[merge_report.json](../artifacts/merges/four-experts-avg-v1-20261017/merge_report.json)。适用前提是继续逐项验证这些共同Base、目标模块、张量方向、LoRA scaling及无bias/DoRA/rsLoRA等条件，不能仅凭四个adapter同名就合版。

## 2. 应合并真实Δ，不能独立合并A/B

普通LoRA的实际模块更新是

```text
Di = (alpha_i/r_i) Bi Ai = 2 Bi Ai
AVG = W0 + (D1+D2+D3+D4)/4
```

`Linear.get_delta_weight` 正是先做B@A，再乘 `self.scaling[adapter]`；普通LoRA的scaling是alpha/r。已安装源码对应 `layer.py:274–277,1000–1023`。[PEFT v0.20.0 layer.py](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/layer.py)

PEFT `combination_type="ties"` 走 `_generalized_task_arithmetic_weighted_adapter`，把A列表与B列表分别做TIES；`"ties_svd"` 则走dense delta与SVD路径。两者不是相同运算。A/B因子可作 `A→cA,B→B/c` 而保持BA不变；逐因子裁剪/选符号却可能改变结果，因此它不具备真实参数差值合版应有的这种不变性。后者是由因子公式推得，并由本轮tiny示例核实；不把PEFT的factor-TIES称为论文dense-delta算法。[PEFT v0.20.0 model.py，两个generalized helper](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/model.py#L801-L949)

## 3. PEFT函数的精确语义与两个不能直接照用的点

`peft.utils.merge_utils.ties` 对**每个输入tensor**按绝对值保留 `int(density*numel)` 个位置；在未加weights的保留值上选符号；`total` 依据数值总和，零和时选正号；随后对符号一致的非零项做加权求和，并除以**被选项数**，不是weights之和。全无保留项时分母clamp到1。[PEFT v0.20.0 merge_utils.py，prune/sign/disjoint_merge/ties](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/utils/merge_utils.py#L37-L214)

所以平等专家应使用 `weights=ones(4)`，因为disjoint mean已经做平均；沿用AVG的四个0.25，会把TIES结果另外缩小4倍。官方文档也建议从全1权重起步。[PEFT v0.20.0 model merging guide](https://huggingface.co/docs/peft/v0.20.0/developer_guides/model_merging)

**不要未经核验直接调用 `add_weighted_adapter(..., combination_type="ties_svd", svd_rank=64)`：**

1. 已安装 `model.py:819–832` 先构造 `valid_weights=weight*target.scaling`，同时又调用已包含scaling的 `get_delta_weight`。因此，对我们四个scale=2的输入，传入全1权重会相对“真实Di送TIES”的目标再乘2。本轮用抽取的真实helper和人工小矩阵复现了这个差异；这是该版本wrapper对所需公式的语义陷阱，不声称上游已确认bug。[PEFT v0.20.0 SVD helper](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/model.py#L801-L867)
2. 同helper直接取 `U[:,:new_rank]`、`S[:new_rank]`、`Vh[:new_rank,:]`，没有把小于r的结果补零。我们有60个32×2048模块，reduced SVD最多32个分量；要输出配置r64的标准形状，必须补A/B零列/行，不能保存r32形状却声明r64。同版本未显式给svd_rank时默认输出最大输入rank，即16；输出64必须明确设置。默认full_matrices=True，也应在逐模块实现里改用False。[同一PEFT v0.20.0 model.py，rank选择与SVD切片](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/model.py#L626-L867)、[本项目形状记录](../artifacts/merges/four-experts-avg-v1-20261017/merge_report.json)

若坚持使用原wrapper，理论上可以把期望weights除以各输入scaling补偿第一点，但仍需修复第二点。更小且更容易审计的路径是只复用官方 `merge_utils.ties`，自己计算一次Di及SVD导出。

## 4. 推荐的最小逐模块实现

下面是**拟议代码轮廓，未用于真实权重**；四个输入config/keys校验、独立目录、manifest与原产物保护可沿用现有CPU合版入口，但不修改已冻结AVG产物。

```python
# Pinned PEFT 0.20.0 utils; ordinary LoRA, fan_in_fan_out=False.
from peft.utils.merge_utils import ties

deltas = [(cfg["lora_alpha"] / cfg["r"]) * (B.float() @ A.float())
          for cfg, A, B in four_expert_module_factors]
dense = ties(deltas, torch.ones(4, device=deltas[0].device),
             density=0.2, majority_sign_method="total")  # lambda=1
U, S, Vh = torch.linalg.svd(dense, full_matrices=False)
q = min(64, S.numel())
A_out = dense.new_zeros((64, dense.shape[1]))
B_out = dense.new_zeros((dense.shape[0], 64))
A_out[:q] = Vh[:q]
B_out[:, :q] = U[:, :q] * S[:q]
# Save r=64, alpha=64: scale=1. Do not multiply scaling again.
```

TIES步骤复用PEFT函数；SVD因子取法与官方helper一致，并加上标准r64形状补零。输出同一310模块和r64时，参数个数与AVG64相同（84,664,320），但这不等于TIES delta无近似误差。[PEFT v0.20.0 helpers](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/tuners/lora/model.py#L727-L867)、[现有AVG参数记录](../artifacts/merges/four-experts-avg-v1-20261017/merge_report.json)

这里明确推荐**PEFT逐模块变体**：作者原实现把state_dict展成全局向量后裁剪，其阈值并列处理及零和符号回填也与PEFT不同；不能把逐模块top-k称为逐字复现作者实现。[作者固定commit 44e7891fc84f3de7e4caa52664cd864ca3715e91，state_dict_to_vector/topk_values_mask/resolve_zero_signs](https://github.com/prateeky2806/ties-merging/blob/44e7891fc84f3de7e4caa52664cd864ca3715e91/src/utils/merge_utils.py)

## 5. r64的比较含义、误差与资源边界

这是**TIES-SVD64端到端方法 vs exact AVG64**，不能只凭同rank就声称测到了“纯TIES效应”。线性平均的rank上界为四个r16之和64；逐元素裁剪会破坏这个低rank结构，所以dense TIES未必可被r64精确表示。这是矩阵代数推论：例如rank1的 `[[3,4],[6,8]]` 去掉最小项后得到行列式非零的 `[[0,4],[6,8]]`。SVD64因此可能丢失TIES更新，而AVG64原先精确。[TIES裁剪定义](https://arxiv.org/html/2306.01708v2)、[PEFT实际逐元素裁剪与SVD](https://github.com/huggingface/peft/blob/v0.20.0/src/peft/utils/merge_utils.py#L37-L53)

若实施，应分别记录每模块及全局 `||D_TIES-B_out A_out||F / ||D_TIES||F`、前64奇异值能量占比、零padding模块数、真实保留密度、序列化重载误差；把float32 SVD误差与服务端bfloat16因子转换误差区分。AVG可做一次不含任务评测的SVD64重构sanity；它能核验导出，但不能消除TIES自身截断这一比较混杂。不得按正式测试分选择density、λ或最终模型。

只读已有JSON得到最大模块8192×2048，单份FP32 delta64MiB；四份256MiB，再stack约256MiB，尚未计mask/weighted tensor/SVD workspace。全部310模块一次展开，每专家5.249GiB、四份约21GiB，故应逐模块处理并及时释放。最大reduced U/Vh约80MiB，full约272MiB；这些是按形状的静态计算，不是测得峰值或耗时。CPU可算但310次大矩阵SVD耗时尚未测量；若采用GPU实现，单GPU逐模块即可先测实际峰值，不需要加载整个35B基座。[本项目merge_report的310个weight_shape](../artifacts/merges/four-experts-avg-v1-20261017/merge_report.json)

合法执行落点仍需另行排期。已于本轮只读核对HPC现场primary source：`/etc/slurm/job_submit.lua:330–348` 强制所有提交作业显式申请至少1GPU，`:382–389` 限制CPU:GPU≤12:1，所以不能把独立纯CPU Slurm作业当成可用方案。后续若排期实施，可在普通`acd_u`/nice1000申请1GPU及≤12CPU，先核项目合计≤16GPU与既定结束时间；或在80上单独预留的空闲CPU池做CPU导出。两种都不是本轮已执行的工作；本轮未提交作业、未测真实SVD峰值/耗时。

## 6. 本轮tiny CPU核验及撤销项

在本机 PyTorch **2.5.1 CPU、单线程**，仅抽取已安装0.20.0的纯函数及SVD helper，对四组人工B(2,1)/A(1,2)运行；没有实例化真实模型或读取四专家tensor。本轮通过：原生wrapper相对显式真实Δ路径多出2倍；全0.25相对全1再缩1/4；保持BA不变的因子gauge变换会改变factor-TIES；2×3小矩阵的SVD补零到r4后仍重构原矩阵，误差约 `4.995779363525799e-7`。

人工dense TIES为 `[[4.6666665,7],[12,-18]]`，原生helper重构为约 `[[9.3333359,14.000001],[24.000002,-35.999996]]`，符合2倍而非所需1倍。该结果验证实现尺度与形状，不提供任何模型质量结论；没有运行真实专家SVD。

此前TA λ=.5 / r64-alpha128产物在用户取消前已于80/HPC导出；它现为**撤销草稿，不进入评测**，未替换主AVG64。本轮只新增本文；不清理其他agent草稿，不改服务、协议、权重或正式队列。
