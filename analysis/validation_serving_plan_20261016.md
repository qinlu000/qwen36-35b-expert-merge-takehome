# 已完成 SFT 专家的 validation 推理服务

更新至 2026-10-16 22:22 CST。用户已授权运行实际 validation；本记录只负责新推理服务，不改 Base 评测或在训作业。

## 实际验收结果

**服务已于 22:18:06 CST 通过实际 GPU 验收并交接 direct validation。** 原始验收由主 agent 执行，之后未重复发测试请求。

- `/health` 200；`/v1/models` 恰好列出下表全部五个别名。
- 四 adapter 原生加载成功日志均已出现；未发现忽略 adapter projection / 无匹配 Punica wrapper / unsupported LoRA 警告。
- Base 与四专家均实际生成 `323`（`17*19` 的合成题），全部正常 stop，且没有隐藏 reasoning 字段输出。同一输入的首 token logprob 在五模型中不同，证实 API 请求确实切到了不同权重；这不是任务能力评测。
- SWE 专家实际返回 `bash` tool call，参数为 `echo validation-ready`，finish_reason=`tool_calls`。
- GPU KV cache 原生日志为 3,187,432 tokens；65,536 单请求长度的理论 cache 容量约 48.64 倍，服务仍按约定 max20seq 限制调度。这不是实测吞吐承诺。
- 80 独立桥 `28089` 的 ready 文件已由主 agent 放置，direct runner 随后开始 Base / HLE / ASI 的固定 validation 批次；本服务保留运行，不重启、不新增 GPU 作业。

最小合成检查的 32 / 128 输出 cap 只用于启动验收，**正式 validation 仍是 65,536 context / 8,192 output**。

实际回执：`analysis/source_snapshots/validation_lora_service_727113_20261016.json`。完整原始 `launch.json`、`acceptance.json` 保留于 HPC 与本机 `artifacts/validation/lora-service-727113/`，没有保存密钥。

## 资源与作业

- 已提交 `727113`，`apex-validation-lora`，节点 `ACD1-24`，端口 `18000`。
- 2 张 H100、16 CPU、128 GiB RAM、12 小时；`emergency_acd` / `formal-user`。
- 提交前项目运行 12 张 GPU（Terminal SFT 4、Mixed 4、两份 Base 服务各 2），加本服务共 14，低于 16。无关 `eval-krama-autoddg` 不改动。
- 专属输出目录：HPC `artifacts/validation/lora-service-727113/`；外层日志 `artifacts/validation/lora-service-727113.log`。
- 80 独立桥接端口由主 agent 负责，计划为 `28089`。不修改现有 Base 隧道。

## 模型与接口

| API model | 权重 |
| --- | --- |
| `apex-val-base` | 冻结 Base `995ad96eacd98c81ed38be0c5b274b04031597b0` |
| `apex-val-swe249` | `swe2k-sft-r16-726335/training/checkpoint-249` |
| `apex-val-asi128` | `asi-expanded-sft-r16-726336/training/checkpoint-128` |
| `apex-val-hle16` | `hle-existing2k-sft-r16-726664/training/checkpoint-16` |
| `apex-val-hle250` | `hle-existing2k-sft-r16-726664/training/checkpoint-250` |

全部为 BF16、TP2、65,536 context，max20seq，chunked prefill 8,192。正式请求保持输出上限 8,192；服务 chat template 默认 `enable_thinking=false,preserve_thinking=false`。每个模型按批次依次跑，`max_loras=1,max_cpu_loras=4`，四个 adapter 不用反复加载 Base。

新脚本：`scripts/serve_validation_lora.py`、`scripts/serve_validation_lora.slurm`、`scripts/check_validation_lora_service.py`。Base key 仅从私有文件读入进程环境，日志与文档不记录密钥。

## LoRA 能力检查

HPC 原生 vLLM 为 0.20.2。每个 checkpoint 实际包含 620 张 A/B tensor，即 310 个线性模块，约 84.8 MB；rank16 / alpha32，只有语言模型 attention 与 shared expert，无 routed expert/router/vision 权重。

已检查本机安装的原生 vLLM 实现：

- `model_executor/models/qwen3_5.py`：Qwen3.6 使用的 `Qwen3_5MoeForConditionalGeneration` 路径具备 LoRA 支持。启用 LoRA 时，linear attention 使用分离的 `in_proj_qkv`、`in_proj_z`；`in_proj_b` / `in_proj_a` 由 `in_proj_ba` 融合映射。
- `model_executor/models/qwen3_vl.py`：继承的 `hf_to_vllm_mapper` 正确将 `model.language_model.` 映射到 `language_model.model.`。
- full attention 的 Q/K/V/O 与 shared expert 的 gate/up/down 均走标准线性 LoRA；`lora/layers/column_parallel_linear.py` 还包含 `in_proj_qkv` 所需的三段不同大小切片支持。
- 服务使用显式 runtime projection 列表，包含 qkv/o、linear qkv/z/ba/out、shared gate_up/down，避免给未训练的 routed experts 包 LoRA。不是删减任何训练过的 adapter 层。
- 原生 checkpoint loader 对未知 projection 抛错；其余未应用/被忽略权重仍必须检查启动 warning，不能仅凭服务启动认定正确。

完整 safetensors header 又与冻结 Base 的 40 层结构逐层精确比对：30 个 linear attention 层各 5 个 projection，10 个 full attention 层各 4 个 projection，40 层各 3 个 shared expert projection，共 310 模块 / 620 A/B tensor。四个 checkpoint 的完整 key 集合均没有 missing 或 unexpected，见 `analysis/source_snapshots/validation_lora_projection_coverage_20261016.json`。没有只检查 tensor 数量而忽略层号。

源码证据采用 HPC 已安装 vLLM 0.20.2：

| 证据 | 安装源码相对 `vllm/` 的位置 |
| --- | --- |
| HF → runtime 完整前缀映射 | `model_executor/models/qwen3_vl.py:1619–1624` |
| linear qkv/z 分离、b/a packing | `model_executor/models/qwen3_5.py:617–626`，以及 `455–495` |
| 原生 adapter 全量读取、未知 projection 报错 | `lora/lora_model.py:163–220` |
| runtime 允许 projection 的 suffix / packing 映射 | `lora/model_manager.py:621–642`，`lora/utils.py:260–300` |
| qkv 不同大小切片 LoRA | `lora/layers/column_parallel_linear.py:620–660` |

**证据限制：** 已有完整 key 静态覆盖、原生 GPU 加载、无忽略层警告、五别名真实生成及不同 logprob；没有将每层中间输出与 PEFT merge 做数值等价测试。因此可以说当前部署没有发现遗漏训练 projection，并已实际使用 adapter，不能声称完成逐层数值等价验证。未为此额外占卡或重复全套测试。

启动命令（已有 `727113` 在运行，供复现，不应重复提交）：

```bash
sbatch /data/user/qinlucao/projects/apex-takehome/scripts/serve_validation_lora.slurm
```

## 与现有 Base 的边界

现有两份 Base 服务没有开启 LoRA，不能原地追加 adapter，也不能将其重启以影响当前 Terminal/SWE 正式评测。本次独立两卡副本可同时给 validation 的 Base 对照提供同配置生成；验证数据和结果目录由对应 runner 另行记录。此处不把训练 loss、简短身份检查或 teacher-forced continuation 当作环境任务成功率。
