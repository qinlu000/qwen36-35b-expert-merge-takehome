# 基座与算力预核验

核验日期：2026-10-15。当前仅做来源和环境检查，未训练、未正式评测、未申请 GPU 作业或租用算力。

## 指定模型

- 官方 `Qwen/Qwen3.6-35B-A3B` 可公开访问，非 gated；本次 HF API 返回 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。后续固定模型、tokenizer、processor 和 chat template 时应使用同一 revision。[模型仓库](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0)、[元数据 API](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B)
- 官方模型卡说明总参数约 35B、每次激活约 3B，含视觉编码器。配置中的架构为 `Qwen3_5MoeForConditionalGeneration`，语言模型有 40 层、256 个 routed expert、每 token 选择 8 个 expert。这里的内部 MoE expert 与本题需要训练的专精模型是不同概念。[固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)、[固定配置](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/config.json)
- safetensors 索引给出的权重总字节数为 `71,903,645,408`，约 71.90 GB / 66.97 GiB。该数字仅是权重文件张量大小，未包含激活、KV cache、优化器、CUDA runtime 和临时张量；不能用激活的 3B 参数推算完整显存。[权重索引](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/model.safetensors.index.json)
- 原生上下文为 262,144 token；chat template 支持 `enable_thinking` 和 `preserve_thinking`。generation config 为 temperature=1.0、top_p=0.95、top_k=20；每个 benchmark 内还须显式保存实际生效请求，不能只依赖默认值。[模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)、[生成配置](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/generation_config.json)、[模板](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/chat_template.jinja)
- 模型卡推荐 `vllm>=0.19.0` 或 `sglang>=0.5.10`，Transformers 要使用支持此架构的新版。`config.json` 中记录的旧 `transformers_version` 不是已验证的安装要求；正式环境需另锁定并验证完整版本。[推理部署说明](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)
- 官方许可标注 Apache-2.0；训练数据、代码和下游模型的许可仍需逐项记录。[模型许可](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/LICENSE)

上述模型卡、配置、生成配置、chat template 和权重索引的小文件快照保存在 `analysis/source_snapshots/`；未下载模型权重。

## 用户确认的执行条件

- 收到用户信息时剩余 2 天 23 小时，即 71 小时；最后预留半天，即 12 小时，核心工作窗口为 59 小时。这是相对排期，不替代面试通知的绝对截止时间。
- 本题可额外申请最多 4 张 H100，不需要等待已有其他 GPU 作业释放。
- 仅按四卡占满 59 小时计算，核心窗口上界为 236 GPU-hours；这是资源预算上界，未实际发生，不是费用。实际资源日志应按作业分配 GPU 数乘运行时间统计，并另计 CPU sandbox 和外部判分费用。
- 当前优先核验 35B LoRA 路线；是否改为 Qwen3-8B，应由实际加载、短训练和推理吞吐证据决定，不能仅凭四卡数量保证可完成。

## hpc3 只读检查

- 本地 SSH alias `hpc3` 可连接，入口是 Slurm 登录节点；登录节点没有 `nvidia-smi` 不意味着集群没有 GPU。未在计算节点确认 H100 每卡显存和实际空闲情况。
- 可调用 Slurm 工具，存在 `emergency_acd` 队列，队列 walltime 上限为 7 天。
- 对 `4 GPU / 48 CPU / 480 GiB RAM / 54 小时` 进行了 `sbatch --test-only` 调度估计，调度器当时返回可安排节点。`--test-only` 未创建实际作业，结果不等于已获得持续资源保证。
- 登录节点可调用 Singularity CE 4.1.5；未发现 Docker / Podman 命令。Harbor 的 Singularity 条件与限制见 `terminal_hle_feasibility.md`，尚未做容器运行验证。
- 有 `uv` 和 Python 3.12 module 条目，但当前 `python` 命令仍指向系统 Python 3.6.8；正式环境需明确使用正确的解释器路径，不能声称已安装完成。
- `hpc3` 的常用 HF / OpenAI 环境变量与默认 HF active token 文件未配置。本机常用 HF 环境变量、默认 active/stored token 文件也未找到；已检查目录的 `.env` 文件搜索未发现 HF 配置。该结论仅覆盖已检查位置，不代表用户其他配置文件不存在凭据。没有输出密钥内容。

## 当前判断

先完成数据访问、官方协议锁定、容器兼容性和吞吐验证，再确定专家数量、rank、训练 token 数、并发与排期。TB 五次全量和 ASI 的任务执行需要单独的 CPU / 内存 / GPU 任务资源；仅有模型推理用的四卡，不能保证 59 小时完成全部交付。详细证据见同目录的 `benchmark_sources.md` 和 `terminal_hle_feasibility.md`。
