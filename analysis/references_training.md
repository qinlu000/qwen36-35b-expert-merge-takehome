# Qwen3.6-35B-A3B 的 SFT / LoRA 工程参考

核验日期：2026-10-15（Asia/Shanghai）。本轮按 research / ego-browser 技能只读检索官方模型资料、框架文档、源代码和 notebook；只新增本笔记，没有安装软件、下载权重、执行训练/评测、读取 benchmark 答案或凭据、调用收费模型 API。本笔记提供讨论依据，不代表本地环境已运行成功。

## 结论与建议

**首选：ms-swift 的 Transformers + BF16 LoRA + DeepSpeed ZeRO-3 路线。备选：Unsloth BF16 MoE LoRA。暂不以 bitsandbytes 4-bit QLoRA 或 Megatron 为第一条实施路线。** 这是基于接近目标模型的官方工程证据和依赖数量作出的工程判断，并非实测速度或质量结论。

首选的依据是 ms-swift 在固定代码中**明确注册了 Qwen/Qwen3.6-35B-A3B**，并存在同一 `Qwen3_5MoeForConditionalGeneration` 架构的 Qwen3.5-35B-A3B 四卡 LoRA 示例。Unsloth 的 Qwen3.6 官方指南明确将训练引导至 Qwen3.5 微调指南，后者提供 35B-A3B MoE 的 BF16 LoRA/A100 notebook，因而比只写“支持 Qwen3”的通用教程更接近任务。[ms-swift 注册](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/model/models/qwen.py#L1631)、[四卡近邻示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/transformers.sh)、[Unsloth Qwen3.6 指南](https://unsloth.ai/docs/models/qwen3.6)、[Unsloth MoE 指南](https://unsloth.ai/docs/models/qwen3.5/fine-tune#moe-fine-tuning-35b-122b)

**本次没有找到“指定 Qwen3.6-35B-A3B、指定 batch/长度/LoRA 范围、4×H100 的完整峰值显存和吞吐实测”这一组合的官方证据。** ms-swift 示例注释的 `4 * 30GiB` 针对 Qwen3.5-35B-A3B；Unsloth 声称的 74GB 针对 Qwen3.5-35B-A3B BF16 LoRA。两者都不能直接改写为本任务的 4×H100 已验证配置，也不能据此承诺在剩余窗口完成。

## 1. 模型与 MoE 参数结构：先确定不能套用的假设

- Qwen 官方模型卡把指定模型列为带视觉编码器的 35B 总参数、约 3B 激活参数模型；不是纯文本 dense Qwen3。已有固定模型 revision 为 `995ad96eacd98c81ed38be0c5b274b04031597b0`，配置架构是 `Qwen3_5MoeForConditionalGeneration`。模型卡的 Transformers/vLLM/SGLang 兼容声明不等于提供了本任务的训练配方或四卡训练实测。[固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)、[固定配置](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/config.json)
- Transformers `v5.2.0` 的这个**准确 MoE 架构**中，`Qwen3_5MoeExperts` 的 `gate_up_proj` 和 `down_proj` 是三维 `nn.Parameter`，第一维为 expert，不是每专家一个常规 `nn.Linear`。因此“配置 all-linear”不能不经核查就宣称 fused routed experts 全部量化或全部加了 LoRA。[准确架构实现](https://github.com/huggingface/transformers/blob/v5.2.0/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py#L811)
- PEFT 对这类参数提供独立的 `target_parameters`；普通 `target_modules` 的语义不能直接替代它。当前文档说明支持二维/三维参数，多个 adapter 若使用该能力需要相同目标参数集合；参数式 MoE LoRA 还可能增加未合并推理的开销。因此各专家应使用一致的目标参数约定，并保存实际匹配与可训练参数清单。[PEFT 参数式 LoRA](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/docs/source/package_reference/lora.md#targeting-nnparameter-directly)
- “4-bit 加载成功”也不能证明全部 35B 权重已变成 4-bit。主线选择 BF16 LoRA，可先避免 fused MoE 权重量化覆盖范围和量化后合版的额外不确定性。该选择不表示 BF16 已在 hpc3 测通。

## 2. 四组官方工程参考

### A. ms-swift：首选

核验代码 `a01a3ae004e0b1071814a3d357666184211ed178`，提交日期 `2026-10-15T03:29:22Z`。使用该 commit 是本次来源快照，不是建议不经验证安装当天 main。

**准确支持证据。** `qwen.py` 明确列出指定 Qwen3.6-35B-A3B 与其 FP8 变体，选择 `Qwen3_5MoeLoader`，加载 `Qwen3_5MoeForConditionalGeneration`；注册要求为 Transformers≥5.2.0、qwen_vl_utils≥0.0.14、decord。这比泛称支持 Qwen3.5 更强，但仍只是框架注册和实现证据。[固定注册/loader](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/model/models/qwen.py#L1631)

**最接近的现成配方。** 官方 `examples/models/qwen3_5/transformers.sh` 使用 Qwen3.5-35B-A3B、四进程、BF16、LoRA rank 8 / alpha 32、all-linear、grouped_mm experts、ZeRO-3、2048 长度、每卡 batch 4、学习率 1e-4，并附 `4 * 30GiB` 注释。它是适合改用目标模型和自建数据的起点；示例的数据、非 thinking 前缀和超参数不是本项目应自动照抄的定稿。[完整官方示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/transformers.sh)

**视觉与 LoRA 目标。** `freeze_vit`、`freeze_aligner` 默认 true，`freeze_llm` 默认 false；文档解释在多模态 all-linear LoRA 中这些参数控制哪些分支加 adapter。pipeline 也支持独立 `target_parameters`，并转交 LoRA 配置。建议讨论稿明确保留视觉塔和 projector，所有专家使用相同语言侧目标；不要未经匹配清单就把 all-linear 描述为“所有 routed expert 权重都已训练”。是否给 fused expert 参数显式加 LoRA，需要在后续短验证中确定，不能从四卡示例注释推断。[参数定义](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/arguments/tuner_args.py#L36)、[目标构造与参数传递](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/pipelines/train/tuner.py#L93)

**kernel 边界。** 准确模型的线性注意力快路径涉及 flash-linear-attention 与 causal-conv1d；Transformers 有部分 torch fallback。ms-swift 的多序列 packing/padding-free 实现明确要求 flash-linear-attention，因为 fallback 不支持 packed sequence boundaries。为降低初始工程风险，可先不启用 packing/padding-free；这不免除 kernel、CUDA、PyTorch、分组 GEMM 和 ZeRO-3 兼容性验证。[Transformers 快路径及 fallback](https://github.com/huggingface/transformers/blob/v5.2.0/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py#L295)、[ms-swift packing 限制](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/model/models/qwen.py#L1285)

**数据与导出。** 官方自建数据文档支持 JSONL `messages`、多轮、OpenAI tool calls、tool response 与多模态 `images`。适合保留代码/终端轨迹而不自行拼聊天模板。官方有 adapter 导出合并入口和 `merge_lora` 示例；多专家之间如何合成仍是本项目研究方法，单 adapter merge 入口不会自动完成多专家算法。[数据格式](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/docs/source_en/Customization/Custom-dataset.md)、[merge 示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/export/merge_lora.sh)

**已知版本风险。** 官方仓库曾有 Qwen3.6 tool/thinking 模板字节不一致和 all-linear 识别失败的公开报告，两者当前均 closed；closed 本身不证明本项目选择的全部组合已修复或已回归验证。后续需要用无害的多轮 tool/thinking 样例检查训练与部署模板、实际 target 和保存再加载，不能直接套旧版本教程。[模板报告 #9276](https://github.com/modelscope/ms-swift/issues/9276)、[目标识别报告 #9538](https://github.com/modelscope/ms-swift/issues/9538)

**为何先不选 Megatron。** 同目录 packing 示例是 8×80GiB、Qwen3.5-35B-A3B 全参训练、TP/EP 和额外融合配置；FP8 示例则是 dense Qwen3.5-4B。不能用它们证明目标 35B MoE 四卡 FP8/LoRA 已跑通。对紧窗口而言，先复用 Transformers/ZeRO-3 的较短依赖链更合理。[packing 示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/packing.sh)、[FP8 示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/fp8.sh)

### B. Unsloth：备选

核验代码 `02d9ea35a3cdbd60059aa21fac2fb9d2f98b5486`，提交日期 `2026-10-15T09:51:46Z`；notebook 快照 `31a8d597f678f54ea343368713d8db880af008a7`，提交日期 `2026-10-14T09:30:54Z`。网页指南未提供本次可固定的文档 commit，故按核验日期引用。

**准确程度。** Qwen3.6 指南明确说其训练可参考 Qwen3.5 fine-tuning guide；后者直接列出 35B-A3B MoE，不是仅 dense 27B，并提供 A100 notebook。文档声称 Qwen3.5-35B-A3B BF16 LoRA 可用约 74GB VRAM，但未把该数字的完整 batch/序列/目标覆盖条件列成目标 Qwen3.6 的四卡实测。[Qwen3.6 训练指引](https://unsloth.ai/docs/models/qwen3.6)、[35B MoE 指南](https://unsloth.ai/docs/models/qwen3.5/fine-tune)

**现成 notebook。** `Qwen3_5_MoE.ipynb` 面向 A100 Colab；加载 `unsloth/Qwen3.5-35B-A3B`、不启用 4-bit、2048 长度、rank 8，并在 LoRA 目标中显式包含 `gate_up_proj`，使用 TRL SFTTrainer。它还演示 adapter 保存和 merged_16bit 导出。改为题目指定官方 base/revision、保留 processor/chat template 后，需要重新验证；不能把 Unsloth 重传模型 revision 当作 Qwen 官方 revision。[固定 MoE notebook](https://github.com/unslothai/notebooks/blob/31a8d597f678f54ea343368713d8db880af008a7/nb/Qwen3_5_MoE.ipynb)

**MoE/量化与 kernel。** 指南推荐 BF16 MoE LoRA，明确不推荐该 MoE 的 bitsandbytes 4-bit QLoRA，并默认不训练 router；需要 Transformers v5。MoE kernel 默认启用，可切换 backend；自定义 Triton kernel 有首次编译成本。固定 notebook 说明其打包了 gated-delta kernels，不需另装 flash-linear-attention，并单列 causal-conv1d 的安装兼容逻辑；不能把“没装 FLA”误判为与普通 Transformers 路线完全相同的执行路径。[MoE 与 kernel 说明](https://unsloth.ai/docs/models/qwen3.5/fine-tune#moe-fine-tuning-35b-122b)、[notebook kernel 单元](https://github.com/unslothai/notebooks/blob/31a8d597f678f54ea343368713d8db880af008a7/nb/Qwen3_5_MoE.ipynb)

**视觉与数据。** 官方视觉 LoRA 接口允许 `finetune_vision_layers=False`，其样例默认可能训练视觉分支，因此不能原样套用。文本 SFT 示例使用格式化后的 `text` 列；本项目若含 tool 轨迹或图像，需要采用正确 processor/collator 与同一聊天模板，不能仅拼接纯文本。官方支持 adapter 保存与 merged_16bit 导出，但多 GPU 策略和导出后准确 Qwen3.6 的图文/工具能力仍需验证。[视觉训练与保存说明](https://unsloth.ai/docs/models/qwen3.5/fine-tune#vision-fine-tuning)、[导出说明](https://unsloth.ai/docs/models/qwen3.5/fine-tune#saving-export-fine-tuned-model)

选择它作为备选是因为近邻 MoE notebook 和显存证据较明确；不代表其自定义 kernel、patch、四卡并发或最终导出风险低于已经跑通的 ms-swift 环境。

### C. LLaMA-Factory：有准确架构代码，不作为当前首选备选

核验代码 `1fded918ac4723ac9966363f51ed4500866c5d1d`，提交日期 `2026-10-10T07:29:22Z`。

- 代码包含 `qwen3_5_moe` 的 ZeRO-3 leaf 配置，并有 `Qwen3_5MoeDecoderLayer` / vision block 的 FSDP2 wrap 配置，属于准确架构支持证据。[MoE 实现](https://github.com/hiyouga/LLaMA-Factory/blob/1fded918ac4723ac9966363f51ed4500866c5d1d/src/llamafactory/model/model_utils/moe.py#L154)、[FSDP2 配置](https://github.com/hiyouga/LLaMA-Factory/blob/1fded918ac4723ac9966363f51ed4500866c5d1d/examples/accelerate/fsdp2_config_qwen35_moe.yaml)
- 找到的最接近完整配方是 **Ascend NPU** 的 Qwen3.5-35B-A3B LoRA SFT/FSDP2，rank 8、2048、batch 1、packing false，FSDP 配置默认 8 进程。不能称为 Qwen3.6 四张 H100 的 recipe 或显存实测。[近邻官方配方](https://github.com/hiyouga/LLaMA-Factory/blob/1fded918ac4723ac9966363f51ed4500866c5d1d/examples/ascend/qwen3_5moe_lora_sft_fsdp2.yaml)
- `freeze_vision_tower` 和 `freeze_multi_modal_projector` 默认 true；adapter 实现提供 all-linear 目标查找和 `merge_and_unload`。这些通用能力仍不能自动证明 fused expert 参数覆盖、bnb 量化覆盖或目标模型端到端训练成功。[冻结参数](https://github.com/hiyouga/LLaMA-Factory/blob/1fded918ac4723ac9966363f51ed4500866c5d1d/src/llamafactory/hparams/finetuning_args.py#L571)、[adapter 代码](https://github.com/hiyouga/LLaMA-Factory/blob/1fded918ac4723ac9966363f51ed4500866c5d1d/src/llamafactory/model/adapter.py#L180)

### D. 原生 Transformers + TRL / PEFT：底层参考，不自行搭首条训练流水线

本次 PEFT 代码快照 `e8e8a7c40af177652ad88a3682d64e0480f5f919`，提交日期 `2026-10-15T08:03:38Z`。准确模型架构证据使用 Transformers `v5.2.0`；本轮没有找到和核验目标模型在四张 H100 上的独立 TRL 端到端训练 recipe，不能据 SFTTrainer 的存在宣称该组合已验证。

PEFT 文档可用于确认 `target_parameters`、三维 expert 参数限制、adapter 合并和参数式 LoRA 的推理开销；通用 NF4/QLoRA 文档本身不能证明 Qwen3.6 fused MoE 参数全部被 bitsandbytes 覆盖。原生搭建还需自己处理准确多模态模型 loader、processor/collator、loss mask、分布式、Gated DeltaNet kernel、模板和导出，时间风险较大，故作为核对底层语义的参考。[PEFT MoE LoRA](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/docs/source/package_reference/lora.md#targeting-nnparameter-directly)、[PEFT 通用量化](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/docs/source/developer_guides/quantization.md)、[准确 Transformers 架构](https://github.com/huggingface/transformers/blob/v5.2.0/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py)

## 3. 讨论后仍需补齐的最小执行证据

以下是后续被授权执行时的验证目标，本轮没有运行：

1. 固定实际可安装的框架、Transformers、PEFT、PyTorch/CUDA、DeepSpeed、FLA/causal-conv1d 与 grouped GEMM 组合，确认准确 MoE 架构能够加载和反向传播。
2. 保存所有可训练参数的完整名字、dtype、shape 和数量；确认视觉塔/projector/router 的冻结决定，确认 fused experts 是有意覆盖或有意不覆盖。不能只记录一个 `all-linear` 字符串。
3. 用独立无害的多轮 thinking/tool/image 样例核对训练渲染与推理模板，验证 adapter 保存、恢复、合并和导出后同一输出链路；这与正式 benchmark 得分无关。
4. 在实际 H100 型号/显存、所选序列长度/batch 上记录短训练峰值显存、有效 token/s、kernel 编译、checkpoint 与 merge 时间。只有这一步才支持四卡训练排期。
5. 专家使用同一 base revision、rank/目标布局和导出约定；正式合版后保留原始模型架构、视觉 processor 和聊天模板。任何量化改变都另行固定、记录，不能将量化和合版收益混在一起。

这些训练工程参考可以减少实现工作，但**不解决 TB/ASI 的 CPU、容器、任务 GPU 和长尾评测瓶颈，也不构成 59 小时交付保证**。
