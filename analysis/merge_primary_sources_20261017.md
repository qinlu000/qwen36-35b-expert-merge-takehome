# 四个 LoRA 的 AVG64 与 AVG16：一手来源核验

核验日期：2026-10-17。沿用并重新联网检查 `research_web_algorithms_20261016.md` 的 PEFT、TIES 原始来源。本文件仅记录数学定义与实现选择依据；没有运行合版、GPU 任务或评测。

## 本轮固定选择

主产物是四个 `r=16, alpha=32` 普通 LoRA 的等权 **AVG64**；唯一消融是同一 AVG 更新逐权重矩阵压缩为 rank16 的 **AVG16**。不制作 TIES 产物，不搜索权重、rank、density 或 scale。这是已知合并与低秩截断的研究对照，不声称算法创新。

## 1. rank 拼接精确表达更新之和

对每个目标权重，令 `A_i∈R^(16×n)`、`B_i∈R^(m×16)`。普通 LoRA 的更新为 `Δ_i=(alpha/r)B_iA_i=2B_iA_i`，目标是

```text
M = (Δ_1+Δ_2+Δ_3+Δ_4)/4 = 0.5 Σ_i B_i A_i.
B64 = [B1 B2 B3 B4]                 # m×64
A64 = 0.5 [A1; A2; A3; A4]          # 64×n
M = B64 A64.
```

输出采用 `r=64, alpha=64, use_rslora=false` 时 scaling=1，上式可直接保存。若输出 scaling 为 `s_out`，应保存 `A64/s_out`，使实际更新仍为 `s_out B64(A64/s_out)`；例如 `r64, alpha128` 需各 A 块乘0.25。这里的“精确”指代数恒等及无秩截断；存储转换、矩阵运算仍有浮点误差。

PEFT 的 `cat` 正是把 `weight_i × scaling_i × A_i` 沿dim0拼接、B沿dim1拼接，并令新 rank 为输入 rank 之和、新 scaling=1。[PEFT 固定源码 e8e8a7c](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)；本轮也重新读取了[官方 main 原始源码](https://raw.githubusercontent.com/huggingface/peft/main/src/peft/tuners/lora/model.py)。普通 LoRA 的 alpha/r 定义见[官方 LoRA 文档](https://huggingface.co/docs/peft/v0.21.0/en/package_reference/lora)。

由矩阵乘法直接可得，分别平均 A/B 会出现 `B_iA_j (i≠j)` 交叉项，不等于上述 AVG；不要用因子空间 `linear` 代替。`rank(M)≤64` 是秩上界，不保证实际秩恰好64。

## 2. AVG16 用薄 QR 加小核心 SVD

以已经吸收 AVG 权重和输入 scaling 的 `B=B64, A=A64` 为输入，逐矩阵在FP32计算：

```text
B = Qb Rb,    A.T = Qa Ra             # reduced QR
C = Rb Ra.T                          # 至多64×64
C = U diag(σ) Vh                     # 普通确定性 SVD，σ降序
B16 = Qb U[:, :16] diag(σ[:16])
A16 = Vh[:16, :] Qa.T
M16 = B16 A16                         # 输出r16、alpha16，scaling=1
```

Qb、Qa列正交，因此 `M=Qb C Qa.T` 与C具有相同非零奇异值。保留C最大的16个奇异值，等价于对完整M做截断SVD：它在精确算术下给出Frobenius范数和谱范数的最优 rank≤16 近似。Frobenius残差平方为 `Σ_(j>16)σ_j²`，可直接用于报告截断损失；这不保证任务分数最优。FP32数值分解及最终BF16等存储转换会再引入误差，应将“最优”限定在数学截断目标。

[PyTorch QR 官方定义与reduced形状](https://docs.pytorch.org/docs/2.14/generated/torch.linalg.qr.html)、[SVD 官方定义与奇异值降序约定](https://docs.pytorch.org/docs/2.14/generated/torch.linalg.svd.html)支持上述分解。截断SVD最优误差见[Halko、Martinsson、Tropp原论文，§9.3与§10的Eckart–Young说明](https://arxiv.org/pdf/0909.4061v2)。PEFT已有对dense合并更新执行SVD、取前 `new_rank` 项的实现，因此AVG16应描述为固定rank压缩消融。[PEFT `_svd_generalized_task_arithmetic_weighted_adapter`](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)

## 3. TIES定义与本轮不采用它的原因

论文对同源dense task vector `τ_i=θ_i−θ_init` 定义三步：按绝对值保留最大k%的坐标；按裁剪后更新之和的符号选方向；每坐标只对同方向的非零项取均值，最后乘λ加回base。零项不进入均值分母。论文免调参配方为 `k=20%, mass sign, disjoint mean, λ=1`，其证据不能直接变成本项目LoRA效果保证。[TIES原论文算法1、§5、附录C.4](https://arxiv.org/html/2306.01708v2)

作者参考实现先把state_dict展平，再对每个专家整条向量裁剪；其 `topk_values_mask` 用幅值阈值，阈值处并列可多保留，`resolve_sign` 对零和符号另作全局majority处理，`disjoint_merge` 的mean分母是所选非零项数。[作者固定参考源码](https://github.com/prateeky2806/ties-merging/blob/44e7891fc84f3de7e4caa52664cd864ca3715e91/src/utils/merge_utils.py)

PEFT `ties` 对传入的tensor裁剪并在投票后应用weights，`total`零和时取正号；逐权重调用与作者全向量裁剪有差别。LoRA `combination_type="ties"` 作用于A/B因子，`ties_svd` 才先恢复dense Δ再做TIES并SVD，因此二者不能混称。[PEFT数值核心](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/utils/merge_utils.py)、[LoRA合并入口](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/src/peft/tuners/lora/model.py)

以下是按矩阵形状作出的成本推断，不是测速结果：令R=64，AVG64只保存 `O((m+n)R)` 个因子元素；AVG16的QR与核心SVD约需 `O((m+n)R²+R³)` 运算、`O((m+n)R+R²)` 工作空间。dense TIES需要恢复并扫描 `m×n` 更新、执行逐元素筛选，输出也未必保持rank≤64。对远大于64的投影矩阵，薄QR路线避免dense更新的内存与计算，并只改变rank这一变量，适合当前固定消融。没有据此宣称任何GPU耗时或指标提升。

本轮读取的main链接仅表示访问日观察，版本依据仍引用固定提交；此核验不证明执行环境安装了该版本。
