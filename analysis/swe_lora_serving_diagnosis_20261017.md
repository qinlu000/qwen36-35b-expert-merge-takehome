# SWE / AVG64 LoRA serving 静态诊断

本轮只读检查实际历史 launch、完整日志中的特定警告、adapter config / safetensors header 与 HPC 已安装源码。**没有发现能解释固定工具动作复读的明确加载、缩放或 parser 故障；尚未完成 HF/PEFT ↔ vLLM 数值一致性验证，不能把“Loaded”当作全部层正确的证明。** 本轮没有重新部署、生产模型请求、Judge、原生任务执行或改权重。证据与小文件 SHA 见同名 JSON。

## 实际服务，而非仅配置

所有路径相对于相应 HPC 或 80 项目根；不包含认证值。

| 服务 | 历史 alias / 节点 | 实际 launch / log |
| --- | --- | --- |
| SWE 专家 727113 | `apex-val-swe249` / ACD1-24 | HPC `artifacts/validation/lora-service-727113/{launch.json,acceptance.json}`；同根上一级 `lora-service-727113.log` |
| AVG64 初始 727660 | `apex-avg64` / ACD1-50 | HPC `artifacts/eval/merged-execution-service-727660/launch.json`；同根上一级同名前缀 `.log` |
| AVG64 普通分区替换 727913 | `apex-avg64` / ACD1-22 | HPC `artifacts/eval/merged-execution-service-727913/launch.json`；同根上一级同名前缀 `.log` |

AVG64 迁移链另由 80 的 `artifacts/eval/execution_partition_migration_20261017/avg64_execution/state.json` 绑定至 727913；不能把全部 AVG 运行都称为初始 727660。此处没有更改仍在使用的 AVG 服务。

三份 engine 初始化日志第 26 行都明确：vLLM **0.20.2**、`Qwen3_5MoeForConditionalGeneration`、冻结 Base `995ad96eacd98c81ed38be0c5b274b04031597b0`、BF16 / TP2 / PP1 / DP1、context 65,536、`enable_prefix_caching=False`、chunked prefill。实际 launch 均设置 `max_num_seqs=20`、prefill token budget 8,192、eager、GDN Triton、MoE Triton、auto tool choice、`qwen3_coder` 工具 parser、`qwen3` reasoning parser、两个 thinking 开关为 false。日志实际选择 FlashAttention 3 与 Triton/FLA GDN prefill。

专家 max-rank16 / max-LoRAs1 / CPU-LoRAs4；AVG64 max-rank64 / max-LoRAs1 / CPU-LoRAs1。727113 日志 119 行、两 AVG 日志 113 行均实际启用 `PunicaWrapperGPU`；分别在 150 / 144 / 144 行登记目标 alias 的加载成功。

完整三份日志中，`These parameters will be ignored`、`no matching PunicaWrapper`、`While loading `、`does not support LoRA`、`not supported for LoRA`、`not in the deployment-time target_modules` 六种字符串各为零。另有 NIXL 缺失、eager 禁用 compile、video processor 文档 `[ERROR]`、默认 MoE / LoRA kernel 配置、per-LoRA tokenizer 弃用等信息。这些消息不构成训练 projection 被忽略的证据，也不能用于保证数值正确。

日志还提示 `generation_config.json` 改变默认 temperature/top-p。安装版 `entrypoints/openai/chat_completion/protocol.py:469–491` 仅在请求值为 None 时使用默认值。实际读取专家与 AVG 的同一 d624 任务首条 accepted request：两者 prompt 精确 1,645 tokens，明确发送 output8,192 / temperature0.7 / top-p0.8 / top-k20 / min-p0 / presence0 / repetition1 / seed0 / n1 / streamfalse / nonthinking。因此该默认值警告不能证明这些实际请求被换成 temperature1。

## 训练 target、运行映射与缩放

只读两份 safetensors header，没有读取大 tensor payload：

| 权重 | r / alpha / scale | header | 运行 dtype |
| --- | --- | --- | --- |
| SWE checkpoint249 | 16 / 32 / 2 | 310 模块，620 个 FP32 A/B tensor | BF16 |
| AVG64 `avg-r64` | 64 / 64 / 1 | 同一完整 key 集合，620 个 FP32 tensor | BF16 |

两者都无 rsLoRA、DoRA、bias、rank/alpha pattern、modules-to-save；没有 router、routed experts 或 vision tensor。SWE 原 config 的 revision 字段为 null，但保存的实际 launch 指向冻结 revision 的 Base snapshot 目录；AVG config 明确写该 revision。target regex 对真实 HF module name 的只读 `re.fullmatch` 成功，没有发现转义失配。

每份完整 header 的 310 source module 覆盖如下。完整层号核对已有 `analysis/source_snapshots/validation_lora_projection_coverage_20261016.json`，本轮又读取了 SWE / AVG header 并重新核其 suffix 映射。

| 家族 | source 模块 | 融合后的预期 wrapper | 映射 |
| --- | ---: | ---: | --- |
| 30 层 linear attention | 150 | 120 | qkv、z、out 独立；b/a → ba |
| 40 层 shared expert | 120 | 80 | gate/up → gate_up；down 独立 |
| 10 层 full attention | 40 | 20 | q/k/v → qkv；o 独立 |
| 合计 | 310 | 220 | 全部通过实际 8 suffix whitelist |

这里的 **220 是静态推导的 wrapper 数量，不是运行时逐层 dump**。不能将 310 source module 与 220 packed wrapper 的差异称为丢层。

安装版源码相对于 `artifacts/envs/base-inference/lib/python3.12/site-packages/vllm/`：

- `qwen3_vl.py:1619–1624` 将 `model.language_model.` 映射为 `language_model.model.`；loader 先去 PEFT prefix 再应用该 mapper。
- `qwen3_5.py:135–141,488–495,617–626` 在启用 LoRA 时使用独立 qkv/z；`gdn_linear_attn.py:290–325,419–439,533–540` 真实 forward 调用这些投影，并保持 b/a 为两段。`lora/layers/column_parallel_linear.py:620–691` 为 qkv 的三段不同尺寸切片提供 wrapper。
- `qwen3_next.py:56,130–147` 的 shared expert 是 `Qwen2MoeMLP`；`qwen2_moe.py:77–122` 使用普通 TP gate_up/down 线性层。FusedMoE 的 `runner/shared_experts.py:135–176` 调用这个共享 MLP 对象，没有静态证据表明它绕过 LoRA 线性层。
- `lora/utils.py:208–300`、`lora/model_manager.py:363–455,621–641` 根据可支持线性层与 packed suffix 设置 wrapper；匹配但不能包装且设置了 whitelist 时会抛错。`worker_manager.py:103–175` 验证 rank/feature 并检查未应用 target。
- `peft_helper.py:53–58` 计算普通 `alpha/r`；`lora_weights.py:31–41,128–149,230–236` 将 scale 吸收至 B 后重置为 1。当前静态路径没有发现专家 scale2 被重复乘两次。AVG 的 FP32 构造是 `A64=.5·stack(Ai), B64=concat(Bi)`、scale1，等于四专家真实 delta 的等权平均；推理仍会将因子转为 BF16。

已读取的小源码 SHA 与部分 mtime 保存在 JSON。检查的 LoRA/GDN 文件 mtime 在 2026-10-15，早于上述实际 launch；但没有每个历史 job 独立冻结的全部 installed-source inventory，因此这些 SHA 不能冒充当时进程的逐文件 hash receipt。

## Prefix cache、线性状态与 parser 边界

三份 engine 日志明确关闭 prefix caching，故“这轮跨请求 prefix cache 复用了另一 adapter 的前缀”与实际配置不符。当前源码的 KV hash 另包含 LoRA 名称（`v1/core/kv_cache_utils.py:460–472,501–536`），但本轮没有靠该机制保证安全，因为 cache 实际未启用。

线性 attention 的 recurrent state 仍是独立问题。`gdn_attn.py:167–170,207,336–339` 使用每请求 block table 与 computed-token 数构造 state index / has-initial-state；`gdn_linear_attn.py:948–971` 在新 prefill 的 `has_initial_state=false` 时把初态清零，并将新状态写回对应 index。这是隔离/reset 的静态证据，**没有执行过 GPU request-order / state-contamination 数值测试**，不能把它升级为实测保证。

原 727113 acceptance（2026-10-16 14:18:06 UTC）保存同一 26-token 合成输入的 Base 首 token logprob `-0.0000402919`、SWE `-0.0007479969`，两者最终均为 `323`。这证明 adapter 改变了部分 logits；没有证明所有 310 层均正确。另有 SWE bash 合成调用 `echo validation-ready` 正常解析，finish `tool_calls`。AVG 的原 native echo/read 验收保存在 `analysis/source_snapshots/merged_execution_queue_deployment_20261017.json` 所引用路径，没有在本轮重复。

正式轨迹中已解析出的多次 bash 调用也不符合“parser 完全没加载”的假说，但不能证明所有历史 multi-call 都没有边缘错误。此前复读命令的 returncode0 不能等同命令内容成功：root 的独立观察已证明 Teleport grep 参数错误、OpenLibrary 路径不存在而管道 `head` 返回 0，见 `analysis/source_snapshots/swe_repeated_read_commands_20261017.json`。本诊断不改先前已提交的上下文统计文件。

## 独立数值 probe，已写未提交

Root 已授权准备 `scripts/diagnose_swe_backend_parity.py` 与 `.slurm`，实际 submit 由 root 审后唯一进行。本 agent 没有申请 GPU 或调用模型。普通 `acd_u`、Nice1000、TP2、16 CPU / 128 GiB、45 分钟；root 需预建 Slurm stdout 的父目录 `artifacts/diagnostics`。每 job 独立 `artifacts/diagnostics/swe-backend-parity-<jobid>`，HF 首次创建拒绝覆盖；vLLM intent 使用独占创建，失败/未知不会自动重试。

三段固定非 benchmark 历史：bash 拼写纠错、一次失败 ls 后的 JSON tool 观察、两个历史 tool calls；后两段直接以 tool 观察结束，不追加额外 user。每段分别取 assistant_start 与强制追加原生 XML `<tool_call>\n<function=bash>\n<parameter=command>\n` 后的 command_start，共六个 prefix，逐位置报告，不混平均。实际 tokenizer 要求每个 prefix 小于 2,048 tokens。不实际执行任何命令。冻结相同 chat-template token IDs、长度及 SHA 后依次：

1. 同一 SIF 的现有 sft Python 跑 HF Base → PEFT SWE249 → disable-adapter Base，每阶段六个 prefix，共十八次 forward。BF16、HF SDPA/native GDN、无 cache；核 620 个 BF16 adapter factors / 310 个 scale2 层。保存末位完整词表 FP32 log-softmax 至 ignored 小 npz，并完整计算 temperature1、无 top-k/top-p/penalty 的 Shannon entropy、top1 probability、双向 KL、JS；disable 前后另对完整词表复核。
2. HF 进程自然退出后，同 SIF 的现有 base-inference Python 建独立离线 vLLM0.20.2 engine，使用历史 TP2/BF16/8 target/GDN Triton/eager 配置、显式 prefix-cachefalse。Base / SWE 每 prefix 各一 token，共十二个固定请求，raw-logprobs top20。无生产端点、无 key、无 Judge。直接传相同 token IDs，故有意绕过 OpenAI tool parser来隔离数值加载；parser 本身不在本 probe 的 parity 范围。
3. 仅比较 Base backend 漂移、SWE backend 漂移及 adapter effect 的差分残差。HF full logp 可查询 vLLM top20 任意 token；vLLM 尾部分布仍未知，不作完整词表 backend 等价声明，也没有事后设准确性门槛。

两个现有环境的 torch2.11.0+cu130、transformers5.15.1、safetensors0.8.0、hub1.28.0 一致，Qwen3.5 与 MoE HF 源码 SHA 逐字一致；sft 额外有 PEFT0.20.0 / accelerate1.14.0，base-inference 无两包。方案无需改生产环境或安装依赖。实际设备 dispatch、token 长度与加载用时仍需这次唯一 job 验证，45 分钟是硬上限，不是完成承诺。

**旧训练日志没有此 Shannon entropy，teacher-forced cross-entropy loss 也不是模型下一 token 分布的 Shannon entropy。** 新熵/KL/JS 仅诊断，不作为 task validation、checkpoint 或主模型选择；短 prefix、单 token 对照也不能直接解释长轨迹吸引子或证明训练因果。

已完成 default plan、stdlib self-test、Python compile、`bash -n`。self-test 检验 top20 intersection，以及均匀/one-hot 的全熵、KL 零控/无限反例、JS 已知值和对称性，没有导入模型或发出请求。两脚本冻结 SHA 在同名 JSON 与 root handoff；执行结果尚不存在。

本轮 owned 仅上述两脚本与本 MD / JSON。没有改 Git、共享文档、既有模型结果或服务。
