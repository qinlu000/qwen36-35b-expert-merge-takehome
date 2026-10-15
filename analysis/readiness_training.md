# 训练准备核查：ms-swift / PEFT / Qwen3.6-35B-A3B

更新：2026-10-15。仅检查元数据和公开源码，未安装／修改环境、下载权重、导入 torch、运行 GPU 算子或申请作业。准确模型 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，架构 `Qwen3_5MoeForConditionalGeneration`。

## 结论

**ms-swift 有指定 Qwen3.6-35B-A3B 的明确注册和 PEFT LoRA 接口，因此路线有源码依据；本机／HPC 尚没有确认可直接运行的完整训练环境。** r16 语言侧 attention + shared MLP、冻结 routed experts/router/视觉，是比 `all-linear` 更明确且便于三专家合版的起点。实际四卡 H100 加载、反向、峰值显存、吞吐和导出仍未验证，不能把 Qwen3.5 的四卡示例当成本题性能证据。

## 只读环境清点

使用各环境解释器的 `importlib.metadata` 或直接读取 dist-info，只输出包名版本；未 import torch/transformers，也未调用 GPU。以下范围不是用户全部环境的穷尽扫描。

| 主机／环境 | 解释器与包版本 | 判断 |
|---|---|---|
| 80 `/usr/bin/python3` | Python 3.10.12；未装 ms-swift/PEFT/Transformers/Torch/vLLM/SGLang/DeepSpeed/FLA/causal-conv1d | 不是训练环境 |
| 80 `envs/datamind-sft` | Python 3.10.12；PEFT 0.15.2、Transformers 4.55.0、Torch 2.6.0+cu126、DeepSpeed 0.16.9 | Transformers 低于准确架构要求；不就地升级用户其他项目环境 |
| 80 `envs/datamind-vllm` | Python 3.12.13；Transformers 5.15.1、Torch 2.13.0+cu132、vLLM 0.27.1 | metadata 版本较新；未证明驱动、模型架构、工具／图文请求可用；也不是已确认训练环境 |
| 80 `envs/qwen35-sft-cu130-v1` | Python symlink 指向不存在的 `/data/caoqinlu/datasets/training_mix_hpc_wheelhouse_v1/python/.../python3.12`；dist-info 留有 PEFT 0.18.1、Transformers 5.5.4、DeepSpeed 0.19.6、FLA 0.5.2 | **解释器无法启动**，不能直接复用；包目录存在不等于完整可运行 |
| 80 `envs/qwen35-sft-upstream-20260907` | 同类失效解释器；metadata 为 PEFT 0.18.1、Transformers 5.8.0、DeepSpeed 0.19.6、FLA 0.5.2 | 不把目录名当作已可训练证据 |
| HPC `envs/qwen35-sft-cu130-v1` | Python 3.12.13 可启动，但 metadata 未检出此次清单中的训练包 | 当前不可称完整训练栈；需查它是否只是未完成／空环境 |
| HPC `envs/dslighting-rollout-vllm017` | Python 3.11.15；Transformers 4.57.6、Torch 2.10.0、vLLM 0.17.1+cu128 | 推理栈低于准确模型卡 vLLM≥0.19.0 建议 |
| HPC `envs/agent-lightning-trainer-sglang058-tmix-v1` | Python 3.12.13；PEFT 0.20.0、Transformers 4.57.1、Torch 2.9.1+cu129、SGLang 0.5.8 | Transformers/SGLang 版本不满足准确模型卡建议；不用于直接承诺支持 |
| HPC `envs/agent-lightning-trainer-cu130-tmix-v1` 及 `...-prewake1` | dist-info：PEFT 0.20.0、Transformers 5.15.1、Torch 2.11.0+cu130、vLLM 0.20.2、Triton 3.6.0 | **存在较新可参考栈**，与旧 vLLM017 环境不同；本轮未导入包或测试 GPU，未发现 ms-swift/DeepSpeed/FLA，因此不能直接作为完整训练环境 |

80 路径根为 `/data/caoqinlu`，HPC 为 `/data/user/qinlucao`。HPC 登录仍以本地 SSH config 的 `hpc3` 为准；本轮两次连接曾被本地 `::1:7897` 代理关闭，重试可连接，这是操作链路不稳定记录，不是 GPU 节点故障。

## 可固定的源码候选，而非已实测依赖锁

- ms-swift：`a01a3ae004e0b1071814a3d357666184211ed178`，版本文件为 **4.7.0.dev0**。明确注册准确模型，`model_type=qwen3_5_moe`、loader=`Qwen3_5MoeLoader`、`template=qwen3_5`；要求 Transformers≥5.2.0、qwen_vl_utils≥0.0.14、decord。[注册](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/model/models/qwen.py#L1631)、[版本文件](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/version.py)
- 模板：固定源码中的 `Qwen3_5Template` 包含 Qwen3.5/3.6 消息 trim、thinking 规范化和工具模板逻辑。不能改用通用 qwen3 模板。必须单独核对 `enable_thinking` / `preserve_thinking`、工具往返与 assistant loss mask。[模板](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/templates/qwen.py#L618)
- Transformers `v5.2.0` 可作为准确架构和目标名的源码核查锚点；它不是最新 ms-swift 所有功能的充分依赖版本。例如此 ms-swift 的非 sequence-parallel packing/padding_free 路径要求 Transformers≥5.9.0。首个 smoke 关闭 packing/padding_free，先减少 kernel／边界变量。
- PEFT：已核查代码 `e8e8a7c40af177652ad88a3682d64e0480f5f919`。普通 nn.Linear 用 `target_modules`／regex；fused MoE 三维参数需要独立 `target_parameters`，本方案暂不训练这些参数，因此不需要以此能力扩展训练目标。[PEFT 参数式 LoRA](https://github.com/huggingface/peft/blob/e8e8a7c40af177652ad88a3682d64e0480f5f919/docs/source/package_reference/lora.md#targeting-nnparameter-directly)

**尚不能给出“已安装可用”的 Torch/CUDA/DeepSpeed/Transformers/PEFT/FLA 完整锁。** 先创建项目专用环境，不修改其他研究项目环境；安装候选解析后，保存精确 wheel/commit、CUDA driver 与依赖清单，再以实际加载和反向证据冻结。以上 commits 可复现源码判断，不是完整版本兼容性实测。

## r16 同结构 LoRA 目标草案

对固定 Transformers v5.2.0 实现和固定模型 safetensors index 逐名核对：

| 分支 | 完整模块尾部 | 层数×模块数 |
|---|---|---|
| full attention | `self_attn.q_proj/k_proj/v_proj/o_proj` | 10×4 |
| linear attention | `linear_attn.in_proj_qkv/in_proj_z/in_proj_b/in_proj_a/out_proj` | 30×5 |
| shared MLP | `mlp.shared_expert.gate_proj/up_proj/down_proj` | 40×3 |

精确 regex 草案（匹配包装前模型，实际匹配结果须落盘）：

```text
model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))
```

固定权重 index 对应 **310 个 `.weight` 键**。按配置矩阵维度估算 r16、bias=none、无 modules_to_save 的 LoRA 参数为 **21,166,080**：full attention 3,440,640；linear attention 12,810,240；shared MLP 4,915,200。这是源码／配置计算，尚非实际 PEFT 匹配清单；安装版本若改变模块路径或包装，必须重新枚举。

明确冻结：`visual`、projector/aligner、embedding、lm_head、norm、linear-attn conv/A_log/dt_bias、`mlp.gate` router、`mlp.shared_expert_gate` 和 `mlp.experts` 的 fused routed tensors。三个专家与混合对照使用同一 base、rank、alpha、regex 和输出布局。不会因为某专家用途不同就改变目标集合。[准确架构](https://github.com/huggingface/transformers/blob/v5.2.0/src/transformers/models/qwen3_5_moe/modeling_qwen3_5_moe.py#L448)、[固定 index](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/model.safetensors.index.json)

注意：r16 的可训练参数小，不等于基座只有约 3B 权重；仍要处理约 71.90GB BF16 张量、分片、激活和临时 buffer。把 routed experts 冻结也不会消除其 forward 算力和加载占用。

## 最小后续 smoke 草案（本轮不执行）

先做不运行 GPU 的版本/模板/目标名检查；再申请授权范围内 4×H100，以自造文本/tool 样例做 2 step。下列只表达待测参数，不是已存在训练脚本；`smoke.jsonl` 尚未创建，不能替代正式数据准备。

```bash
NPROC_PER_NODE=4 swift sft \
  --model /path/to/Qwen3.6-35B-A3B-fixed-revision \
  --model_type qwen3_5_moe --template qwen3_5 \
  --tuner_type lora --lora_rank 16 --lora_alpha 32 \
  --target_regex 'model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))' \
  --freeze_vit true --freeze_aligner true \
  --torch_dtype bfloat16 --deepspeed zero3 \
  --dataset /path/to/self_authored_smoke.jsonl \
  --split_dataset_ratio 0 --max_length 2048 \
  --per_device_train_batch_size 1 --gradient_accumulation_steps 1 \
  --max_steps 2 --logging_steps 1 --save_steps 2 \
  --packing false --padding_free false \
  --output_dir /path/to/isolated_smoke_output
```

kernel/expert backend 不凭空填；应先检查安装组合的默认路径，再按固定官方近邻示例测试 `--experts_impl grouped_mm`。2K 冒烟成功后再测 8K 真实长轨迹；用非 padding token/s、每卡峰值显存、checkpoint/恢复/merge 时间修正排期。最后验证同一多轮 tool/thinking 样例在训练渲染、adapter 重载和合并后服务中的一致性，并补图像输入通路检查。[四卡近邻示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/transformers.sh)

## 问题记录

1. **P0：训练栈未 ready。** ms-swift 在已检查环境中未发现完整可运行安装；80 旧 Qwen venv 失效；HPC 存在较新 vLLM 0.20.2 / Transformers 5.15.1 / Torch 2.11 栈，但缺完整训练依赖证据。需要项目专用环境与 wheel/编译依赖准备。
2. **P0：四卡准确模型未实测。** 不承诺 8K、r16 或 8 小时训练完成；取得真实吞吐后再固定训练 token。
3. **P1：训练／服务依赖可以分开锁。** 不要求 vLLM 与训练 Torch 共用环境；但 tokenizer/processor、chat template、thinking 与模型 revision 必须相同。
4. **P1：LoRA 输出与合版。** 保存实际 310 模块匹配、shape/dtype/count 和冻结清单；AVG/TIES 必须在 dense delta `sBA` 上操作，不能把 A/B 因子平均当权重平均。
5. **P1：长轨迹 mask 与模板。** 必须确认 user/tool token 不被当 assistant 目标训练，思考片段保留策略明确；工具格式差异先记录为数据协议差异。
6. **P1：packing 与 kernel。** 初次关闭 packing；后续若启用，按固定源码满足 Transformers≥5.9.0 和 FLA 边界要求，不以 torch fallback 运行就推断多序列边界正确。


## 后续CPU导入检查通过（仍无GPU训练）

HPC `/data/user/qinlucao/envs/agent-lightning-trainer-cu130-tmix-v1/bin/python` 在CUDA_VISIBLE_DEVICES为空、HF/Transformers离线、OMP/MKL单线程下，实际import torch、transformers、peft及Qwen3_5MoeConfig成功。返回Python3.12.13、Torch2.11.0+cu130、Transformers5.15.1、PEFT0.20.0。证明这部分已超出dist-info存在性检查；ms-swift、DeepSpeed/FLA完整组合、模型加载/反向/导出和四卡吞吐仍未验证。首次SSH/导入返回较慢（超过2分钟，未分离连接与导入耗时），正常结束后检查无匹配探针进程；未终止任何用户作业或使用GPU。
