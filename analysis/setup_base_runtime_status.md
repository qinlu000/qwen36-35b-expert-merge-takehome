# HPC Base 推理环境配置回执

首轮安装于2026-10-15，主机 `hpc3` / `ACD-Login-3`，项目根目录 `/data/user/qinlucao/projects/apex-takehome`。2026-10-16，准确权重在80/HPC双端完整校验后，两张H100上的合成文本、图像和多轮工具HTTP检查全部通过。没有正式评测或训练。

已实际安装 `artifacts/envs/base-inference`：Python 3.12.13、vLLM 0.20.2、Torch 2.11.0+cu130、Transformers 5.15.1、torchvision 0.26.0+cu130、qwen-vl-utils 0.0.14、Av 19.0.1。184 个包完整固定在 `scripts/requirements-base-runtime.lock`，SHA-256 `632490600719f2eba07a6cf1a975d17da8b6356ce6b2d955ba66f0e3a3b142d3`；实装 freeze 与锁文件一致。为目标容器平台执行的 `uv pip check` 已通过。

核心栈来自本机现有 `/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/trainer_glibc235`，182 包离线安装；不下载 Torch/CUDA 大包。只新增下载 qwen-vl-utils 与约 33.4 MiB 的 Av。项目环境是独立 venv，不继承 system-site-packages，未修改 donor 环境。Torch 大库在项目环境与 uv cache 间使用硬链接。

本轮候选使用 vLLM 0.20.2，区别于前序协议草案中的 0.27.1；没有修改正式协议或启动评测。[固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)推荐 vLLM >=0.19.0。该安装版本的 registry 含 `Qwen3_5MoeForConditionalGeneration` 条目；CPU注册检查和后续GPU/HTTP实测分别留据。[vLLM 0.20.2 registry](https://raw.githubusercontent.com/vllm-project/vllm/v0.20.2/vllm/model_executor/models/registry.py)

登录节点 glibc 为 2.28，已安装 vLLM wheel 的标签为 manylinux 2.35，部分其他依赖也需要更高 glibc。因此该环境的目标运行方式是现有 Singularity 镜像 `/data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif`，已实际无 GPU 启动并确认 Ubuntu 24.04.2。镜像为现有文件，18,337,001,472 bytes，没有重新拉取或修改。已重新读取完整文件计算 SHA-256：`1602b61642a5bd4ca5fd99796500267afcdd0808ef43754c8bdbcd045a50c7bc`，与原 sidecar 一致；身份记录见 `configs/envs/base_runtime_container.json`。

可在 HPC 项目根目录重放安装，依赖现有 wheelhouse 和已缓存的 qwen-vl-utils/Av：

```bash
bash scripts/setup_base_runtime.sh
```

脚本显式使用 manylinux 2.35 目标平台，默认全程 offline。若在全新缓存的主机重建，还需要先缓存 qwen-vl-utils/Av；其余依赖来自现有 wheelhouse。`APEX_UV`、`APEX_PYTHON`、`APEX_WHEELHOUSE`、`APEX_PROJECT` 可覆盖已有路径。

CPU 自造图文检查入口是 `scripts/check_base_runtime.py`，运行不加载权重。检查使用从 80 复制的同一固定 revision 的五个 tokenizer/processor 元数据文件，放在 `artifacts/preflight/base-runtime-metadata/995ad96eacd98c81ed38be0c5b274b04031597b0`；没有干扰正在后台下载的模型目录。该检查已在目标 SIF 内通过：核心库与 vLLM CLI 模块 import、AutoConfig 架构识别、qwen-vl-utils 解码、Qwen3VLProcessor 自造图文输入均通过，`pixel_values=[256,1536]`，未初始化 CUDA。机器回执在 `artifacts/preflight/base-runtime/cpu_check.json`。Transformers 输出了与前序 80 检查相同的两条 video 参数 docstring 诊断，图像处理成功；没有修改库源码。

```bash
APEX_PROJECT=/data/user/qinlucao/projects/apex-takehome
APEX_PYTHON_ROOT=/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/python
singularity exec --cleanenv --containall \
  --bind "$APEX_PROJECT:$APEX_PROJECT" \
  --bind "$APEX_PYTHON_ROOT:$APEX_PYTHON_ROOT:ro" \
  /data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif \
  "$APEX_PROJECT/artifacts/envs/base-inference/bin/python" \
  "$APEX_PROJECT/scripts/check_base_runtime.py" \
  --model-metadata "$APEX_PROJECT/artifacts/preflight/base-runtime-metadata/995ad96eacd98c81ed38be0c5b274b04031597b0" \
  --output "$APEX_PROJECT/artifacts/preflight/base-runtime/cpu_check.json"
```

donor 的 Torch 与 vLLM 顶层 import 已在登录节点通过；直接导入 CUDA 扩展因登录节点没有 `libcuda.so.1` 失败，完整 `vllm --help` 也因无法推断 device type 失败。后续分配节点上的两卡实测已通过权重加载和短HTTP请求，结果如下；长上下文、持续吞吐及正式四卡服务参数仍待验证。

## GPU smoke：两卡合成HTTP检查通过

作业 **723821** 在 `emergency_acd` / `qinlucao` / `formal-user` 下完成，实际priority为10023；`sacct`为`COMPLETED / 0:0`，总用时5分07秒。`artifacts/preflight/base-smoke-723821/summary.json`记录`passed=true`，四个合成case全部通过，服务启动270.19秒，脚本正常退出0。带key的HTTP请求成功200，无key的`/v1/models`返回401，认证已实际生效。

检查使用两张H100 80GB、TP2、BF16、配置上下文262,144；分配为2 GPU / 16 CPU / 128 GiB / 30分钟。服务ready时每卡显存占用70,627 MiB，四次请求后为70,635 MiB。显存按Torch可见设备UUID调用`nvidia-smi`查询，并保存CUDA→UUID映射，避免Slurm设备重编号混淆。

四个case分别是纯文本、32×32红色PNG、`add_numbers(17,25)`自动tool call，以及返回工具结果42后的回答。每次保存请求、响应、usage与延迟；回执和`server.log`位于上述作业目录，Slurm输出为`artifacts/preflight/base-smoke-723821.log`。仅证明此配置下的短文本、图文及工具往返通路；没有实际填满262,144上下文、测持续吞吐或验收正式四卡参数。

入口为`scripts/smoke_base.slurm`和`scripts/smoke_base.py`。Slurm默认请求4 GPU / 16 CPU / 192 GiB / 30分钟；本次用以下覆盖提交两卡检查：

```bash
cd /data/user/qinlucao/projects/apex-takehome
sbatch --gres=gpu:2 --mem=128G scripts/smoke_base.slurm
```

通过固定Ubuntu 24.04 SIF的`--nv`启动，清洁环境中显式保留Slurm的`CUDA_VISIBLE_DEVICES`，服务只监听`127.0.0.1:18000`。本次参数还包括eager、`max-num-seqs=4`、`gdn-prefill-backend=triton`、`moe-backend=triton`、`qwen3_coder` tool parser和`qwen3` reasoning parser，served model为`apex-qwen`。合成请求显式关闭thinking及preserve_thinking；这些设置没有冻结正式评测协议。

缓存修复已由723821实际验证：每个作业在节点本地XFS `/tmp`创建唯一目录，整目录绑定为容器`/tmp`；Triton、vLLM、TorchInductor、FlashInfer、HF/XDG cache均在该目录下，`TMPDIR=/tmp`、`MAX_JOBS=4`。配置EXIT清理自己的目录；本次没有独立的目录删除回执。不改HOME、系统或管理员wrapper。服务健康等待上限已改为1200秒。

API key 由 Python 生成到 Git 忽略的 `artifacts/private/base_smoke_api_key`（目录 0700、文件 0600）。只通过服务子进程的 `VLLM_API_KEY` 环境变量及请求内存中的 Authorization header 使用，不放进模型命令行、请求 JSON 或日志。`--prepare-only` 仅创建私有文件和输出目录，不用 GPU、不读权重、不启动服务；后续重复运行使用同一项目私有 key。

历史失败日志继续保留：

- 723633在PENDING时取消，没有占GPU。723673被站点wrapper误判空格形式的`--project`参数；改为等号形式后CPU预检查通过。
- 723693因默认Triton缓存无写权限，在权重加载前失败。723706通过架构/NCCL及26分片加载（52.98秒，rank0模型32.86 GiB），随后首次编译耗尽容器私有`/tmp`。
- 723727使用项目共享盘临时目录，编译超过原600秒健康等待上限。723784在高优先级分区约280秒启动，health/models与鉴权通过，但首个文本请求因共享DPC上的Triton缓存元数据文件缺失返回HTTP500。
- 723821将临时目录及所有cache迁到节点本地`/tmp`后，完成上述全部HTTP检查。

超时或失败返回非零；结束和SIGTERM/SIGINT时向整个服务进程组发TERM，等待主进程最多20秒，再清除残余进程组。本次服务与作业均已退出，没有留下常驻endpoint。

用户已授权提高优先级，脚本默认分区为`emergency_acd`（PriorityTier/JobFactor300，原`acd_ue`为200），仍用本人`qinlucao`账号/`formal-user` QoS。未调整其他项目作业722434。后续v2协议已选TP2单服务/64K总context/8K输出；262K短smoke不能替代当前参数、长请求和队列验收，也不再将四卡端点作为既定前提。本轮正在另做对应64K/8K的合成检查，未运行正式题。
