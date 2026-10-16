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

## 7. 2026-10-17 pilot实现待审核（尚未提交）

已新增 [merge_ties_adapters.py](../scripts/merge_ties_adapters.py)、[固定配方](../configs/merge/four_experts_ties_svd64_v1.json) 和 [Slurm入口](../scripts/merge_ties.slurm)。入口仅导入固定PEFT0.20.0的纯 `utils.ties` 文件，核验该9,939字节源码SHA256为 `2b601ee37cc040d42134bf31b7b1b0bbbac4092b08f7084e64d889ae3f5f0163`；不经原生weighted-adapter wrapper。真实输入的alpha/r只在共享 `true_delta` 函数乘一次，输出r64/alpha64、FP32因子、reduced SVD，min_dim<64时补零。real-weight模式要求已分配的Slurm job及单张H100；无模型、训练、loss或推理入口。

本机CPU单线程的七项tiny checks通过：人工真Δ/TIES数值、重复scale拒绝、ones与0.25的尺度区别、同尺度A/B平均交叉项、固定density=.2的top-k、rank64小维补零，以及rank1实测误差与奇异值尾能量一致。Python AST和bash语法通过，独立只读代码复核未发现阻塞问题。仅核读HPC四份adapter config与既有shape JSON；尚未对真实专家tensor做矩阵运算。[准备收据与固定六层列表](source_snapshots/ties_pilot_preparation_20261017.json)

待root审核的命令为HPC项目目录下 `sbatch scripts/merge_ties.slurm pilot`，配置普通acd_u、nice1000、1H100、8CPU、64GiB、30分钟。提交前仍须重核项目GPU总数；当前root报告10GPU，pilot增加1张后为11/16。每个真实shape仅选字典序首个模块一次，不导出adapter；报告逐阶段耗时、PyTorch allocator allocated/reserved峰值（非整卡采样峰值）、CPU当前RSS/进程生命周期RSS峰值、SVD尾能量及实际FP32重构相对Frobenius误差。按各shape的模块数加权估310层耗时，明确单样本及未计最终序列化的限制。

pilot报告位置为 `artifacts/merges/four-experts-ties-svd64-v1-20261017/pilot-<jobid>/report.json`。本次只准备上述文件与tiny验收，**未sbatch、未申请GPU、未运行真实SVD或全量导出**。pilot结果只能支持资源/数值可行性判断；是否全量导出仍待root另行决定，主AVG64与所有原始产物保持冻结。

## 8. Pilot727948失败与tiny fixture最小修复

root核验实时10GPU及唯一submit claim后提交727948：普通acd_u/nice1000、1H100/8CPU/64G。作业在ACD1-28运行29秒后以FAILED/1:0退出；失败发生在报告构造里的CPU人工 `self_test`，尚未进入六个真实模块的循环。只做了8×8 CUDA初始化warmup与metadata读取，**没有真实专家矩阵乘法/SVD、adapter导出、模型请求或训练/loss评估**。因此本次没有可用的六shape耗时/峰值/误差或全量估时，不能把失败误报成SVD资源不足。[原失败小收据](source_snapshots/ties_pilot_727948_20261017.json)

诊断是旧人工fixture在top-k裁剪边界包含相同绝对值：本机PyTorch2.5.1与HPC2.11.0+cu130选到了不同的等值坐标，使固定期望矩阵不再通用。最小修复只替换四组人工因子，并新增严格top-k边界无并列断言；未放宽 `assert_close`、未改真实TIES算法/配方/SVD设置。新fixture的四个边界间隔均为2，固定scale2/density.5的结果是 `[[6,12],[12,18]]`。bottom-left符号总量恰为0，仍严格检查PEFT定义的选正号行为。

修复后的同一脚本在本机2.5.1 CPU及HPC实际SIF/sft-venv的2.11.0+cu130 CPU单线程均通过七项tiny checks；HPC只运行人工tiny，无 `--nv`、无GPU分配或真实权重计算。修复源码已同步HPC。原727948失败保留，不自行重提；下一次pilot由root另行决定，完整导出仍未获准。

## 9. Pilot727967：六shape工程验收通过，SVD64截断显著
root一次提交修复后的727967（`apex-ties-pilot2`）；sacct为COMPLETED/0:0，ACD1-28、普通acd_u/nice1000、1H100/8CPU/64G，实际作业10秒。脚本pipeline为2.694秒，PyTorch2.11.0+cu130/CUDA13.0，六个预先固定代表模块均通过。仅pilot，未导出adapter，也没有模型调用、loss或训练；四专家权重size/mtime校验未变。[精简实测收据](source_snapshots/ties_pilot_727967_20261017.json)，[原始小JSON报告](../artifacts/eval/ties-pilot-727967/report.json)。
| Dense shape | 模块数 | 本层秒 | SVD/因子化秒 | 实际相对Frob残差 | 保留奇异值能量 | allocator allocated峰值MiB | CPU RSS MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| 32×2048 | 60 | 1.0703 | 0.2334 | 2.99799e-06 | 100.000% | 38.00 | 1153.06 |
| 512×2048 | 100 | 0.0570 | 0.0527 | 0.504026 | 74.594% | 128.00 | 1155.75 |
| 2048×512 | 40 | 0.0245 | 0.0206 | 0.495894 | 75.406% | 128.00 | 1156.85 |
| 2048×4096 | 40 | 0.2363 | 0.2285 | 0.304212 | 90.740% | 800.00 | 1159.75 |
| 4096×2048 | 30 | 0.2388 | 0.2315 | 0.567694 | 67.764% | 800.00 | 1161.52 |
| 8192×2048 | 40 | 0.2514 | 0.2404 | 0.524596 | 72.473% | 1568.00 | 1164.91 |

32行样例可用32个分量完整表示并补32个零分量，重构相对误差约3e-6。其余五个样例的实际相对Frobenius残差为 **0.3042–0.5677**、保留能量 **67.76%–90.74%**。这是对dense TIES更新本身的FP32重构误差，不是Base总权重误差，也不是服务BF16转换误差；不能当作小误差或推断任务质量。六层不是全310层误差统计，不能外推全模型残差。

资源方面，最大PyTorch allocator allocated峰值1,644,167,680字节（1.531GiB），reserved峰值2,271,215,616字节（2.115GiB）；它们不是整卡物理显存采样峰值。最大已记录进程RSS/生命周期高水位为1,221,492,736字节（1.138GiB），不是逐层高频采样峰值。资源足够只说明逐模块实现可行，不说明rank64质量足够。

按shape模块数加权的310层计算估时为 **97.572秒**。首个32×2048模块用1.070秒，其中真实Δ matmul0.154秒、TIES0.642秒有明显冷启动成本，却被乘60次；因此该估时重复计入一次性成本。另一方面它没计外层GC/逐层report写入、进程/容器启动、最终adapter序列化和文件系统同步。每shape仅一个样本，矩阵数据和I/O可变，不给虚假置信区间，也不把97.6秒作为保证时限。

root据此**暂不批准SVD64全量导出**。保持density=.2、total、全1、λ=1不变，可以研究逐模块直接dense TIES、跳过SVD，再将 `W0.float()+D_TIES` 写入独立完整HF snapshot；该路径无低秩截断，但FP32计算和最终存储dtype舍入仍必须披露。尤其BF16写回误差应相对原FP32合成权重及D_TIES分别记录，不能称数学完全无近似；不可原地覆盖Base或与Base共享硬链接的待改shard。具体分片/容量由direct agent只读核验，尚未实现、导出或申请新资源。主AVG64身份保持不变。

## 10. TIES-Dense实现待root审阅（未提交）

按root决定保留同一density=.2/total/ones/λ=1配方，新增 [merge_ties_dense.py](../scripts/merge_ties_dense.py)、[固定dense配置](../configs/merge/four_experts_ties_dense_v1.json) 与 [普通Slurm入口](../scripts/merge_ties_dense.slurm)。产物是根目录 `artifacts/merges/four-experts-ties-dense-v1-20261017/` 的独立完整HF模型，不是adapter；原SVD pilot和主AVG64保持不变。服务路径/别名由direct agent单独接入，不由本脚本启动。

只读Base26片的safetensors header共131,368字节、未读tensor payload，确认1045个key完整、310目标映射/shape均命中、310目标及735非目标均BF16，目标共1,409,024,000元素。具体Base分片/容量primary metadata与映射依据另见direct agent的 [dense feasibility](ties_dense_export_feasibility_20261017.md)。所有26片都命中目标，故全部新写，不做hardlink或修改冻结Base。实际全量写约71.9GB仍未执行，不能把pilot十秒当成全量IO时长或quota证明。

代码复用已核实的 `load_ties/input_inventory/true_delta`：只保留一个Base shard字典，每个目标矩阵一次计算真实Δ、官方TIES、FP32的W0+D再回存原BF16。写独立临时shard后rename、重新打开；310目标与写入前预期bits比较，735非目标用uint8视图与源bits比较（含dtype/shape），不以浮点相等替代bitwise。最终核1045唯一key、26片、原index logical total_size、所有源文件size/mtime未变；原HF index/config/tokenizer/chat/vision processor/LICENSE复制成自足普通文件。`merge_report.json`及manifest完成后，最后原子写 `EXPORT_COMPLETE.json`；半成品没有完成marker，不能用于服务。

误差按每目标和全局分别报告：BF16 cast绝对Frobenius及相对FP32合成权重/真实TIES更新D；FP32加法相对输入float值的高精度算术误差；有效更新 `(stored-W0)-D` 相对D的偏差；量化后数值未变的元素数。目标总范数不会掩盖更新误差。保留Base原tensor shape/架构并不等于与AVG64相同低秩自由度；full-snapshot BF16写回与LoRA运行时加法的舍入顺序也不同，均需披露。

本机PyTorch2.5.1与HPC实际容器2.11.0+cu130，CPU单线程均通过共享七项tiny checks与新增五项dense checks。新增测试用两片/五tensor跑真实writer和reopen：两个目标、三个非目标，NaN/符号零bits保持、BF16舍入及有效更新偏差可测、新文件非hardlink。spy使dense路径任何SVD调用即失败，实际0调用。共享历史tiny checks仍含两个纯人工CPU SVD，但只在显式 `--self-test` 执行；真正导出运行只调用无SVD的dense checks，真实导出路径无SVD。

三文件已同步HPC；待审核命令为项目cwd `sbatch scripts/merge_ties_dense.slurm`，普通acd_u/nice1000、1H100/8CPU/64G/30min。提交前由root核实时GPU总量与唯一claim。**本轮未sbatch、未导出真实权重、未申请GPU或发模型/评分/loss请求。** [准备小收据](source_snapshots/ties_dense_preparation_20261017.json)

## 11. TIES-Dense728007完整导出与最终artifact契约

root核验实时10GPU及唯一claim后一次提交728007。作业在ACD1-24以普通acd_u/nice1000、1H100/8CPU/64G运行，sacct **COMPLETED/0:0，129秒**；脚本实际导出阶段 **98.655秒**。收尾时squeue已空，导出卡自然释放。没有提交其他作业、启动服务、调用模型或运行loss/任务评测。[最终精简收据](source_snapshots/ties_dense_export_728007_20261017.json)，[原始小metadata收据](../artifacts/eval/ties-dense-728007/export_receipt_raw.json)；没有下载约72GB权重到80或本地。

标准artifact身份为 `four-experts-ties-dense-v1-20261017`，完整HF目录位于HPC：

```text
/data/user/qinlucao/projects/apex-takehome/artifacts/merges/four-experts-ties-dense-v1-20261017/
```

目录根包含原26个safetensors shard、原index及11个自足HF资产（config/generation、tokenizer/vocab/merges/chat template、image/video processor、LICENSE），全部为普通文件；无adapter_config。26片实际总大小 **71,903,776,776字节（66.966GiB）**，index logical tensor bytes为71,903,645,408；逐片大小见收据。全部1045 tensor保持BF16及原shape；310个目标处理完成，735个非目标逐bit保持。每片写入后重新打开，全部key/shape/dtype和目标输出bits一致，非目标与Base bits一致；源adapter/Base/资产size和mtime检查未变。没有embedding、vision、router或routed-expert更新，真实SVD调用0。

精度结果（分母是310个目标构成的真实dense TIES更新D，非Base总模型）：

| 指标 | 实测 |
|---|---:|
| `||D||F²` | 55.4761948431 |
| BF16 cast绝对 `||cast(W0FP32+D)-(W0FP32+D)||F` | 0.7843734549 |
| BF16 cast误差 / `||D||F` | **0.1053099861（10.5310%）** |
| BF16 cast误差 / FP32合成目标权重范数 | 0.0012621630（0.126216%） |
| 有效更新偏差 `||(stored-W0)-D||F / ||D||F` | **0.1053099862** |
| FP32加法roundoff范数平方 | 1.3814118857e-10 |
| 各目标BF16 cast相对D误差范围 | 0.0234509–0.2002444 |
| 原值数值未变元素 | 623,006,268 / 1,409,024,000（44.2154%） |
| 整块数值完全未变的目标tensor | 0 / 310 |

“44.2154%未变”包含TIES本来就产生D=0的坐标，**不能全部归因为BF16损失**；本报告没有重新计算额外零向量分解。结果没有低秩/SVD截断，但不能称完全无损；相对Base总范数的较小误差不替代10.53%的更新相对误差。full-snapshot/BF16写回与AVG64 LoRA的自由度、运行时加法顺序仍不同，必须披露。配方density=.2、total、全1、λ=1未因这些数值或任务成绩调整，主AVG64不变。

最大PyTorch allocator allocated峰值为1,644,167,680字节（1.531GiB）、reserved峰值2,273,312,768（2.117GiB），不是整卡物理显存峰值；CPU进程RSS生命周期高水位9,574,625,280字节（8.917GiB）。这些是实际逐shard导出数据，不能继续用pilot十秒估完整IO或未来推理峰值。

完成契约已实际检查：`merge_report.json`为state=finished，计数310/735/1045/26、reload_verified/sources_unchanged均true；`EXPORT_COMPLETE.json`为passed=true/snapshot_type=full_hf_model/固定revision/real_weight_svd_calls=0/selected_final=false。文件mtime按**全部26片 → manifest → finished report → EXPORT_COMPLETE**排序，纳秒以字符串存入收据避免精度损失。完成marker已交direct agent用于未来完整模型profile guard；仅普通HF loader不会自动检查marker，因此需显式保留guard。此交付只证明导出工程契约，尚未进行tokenizer/text/image服务接入验收，也不授权额外服务或正式任务生成，后续由root决定。
