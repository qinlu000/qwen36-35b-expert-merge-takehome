# HPC Base 推理环境配置回执

2026-10-15，主机 `hpc3` / `ACD-Login-3`，项目根目录 `/data/user/qinlucao/projects/apex-takehome`。本轮只准备独立推理环境，不申请 GPU、创建 Slurm 作业、启动模型服务或读取模型权重。

已实际安装 `artifacts/envs/base-inference`：Python 3.12.13、vLLM 0.20.2、Torch 2.11.0+cu130、Transformers 5.15.1、torchvision 0.26.0+cu130、qwen-vl-utils 0.0.14、Av 19.0.1。184 个包完整固定在 `scripts/requirements-base-runtime.lock`，SHA-256 `632490600719f2eba07a6cf1a975d17da8b6356ce6b2d955ba66f0e3a3b142d3`；实装 freeze 与锁文件一致。为目标容器平台执行的 `uv pip check` 已通过。

核心栈来自本机现有 `/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/trainer_glibc235`，182 包离线安装；不下载 Torch/CUDA 大包。只新增下载 qwen-vl-utils 与约 33.4 MiB 的 Av。项目环境是独立 venv，不继承 system-site-packages，未修改 donor 环境。Torch 大库在项目环境与 uv cache 间使用硬链接。

本轮候选使用 vLLM 0.20.2，区别于前序协议草案中的 0.27.1；没有修改正式协议或启动评测。[固定模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)推荐 vLLM >=0.19.0。该安装版本的 registry 已确认含 `Qwen3_5MoeForConditionalGeneration` 条目；这还不代表真实 GPU 加载已验证。[vLLM 0.20.2 registry](https://raw.githubusercontent.com/vllm-project/vllm/v0.20.2/vllm/model_executor/models/registry.py)

登录节点 glibc 为 2.28，已安装 vLLM wheel 的标签为 manylinux 2.35，部分其他依赖也需要更高 glibc。因此该环境的目标运行方式是现有 Singularity 镜像 `/data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif`，已实际无 GPU 启动并确认 Ubuntu 24.04.2。镜像为现有文件，18,337,001,472 bytes，没有重新拉取或修改。当前记录了路径、大小和 mtime，尚未重新计算整个 18 GB SIF 的内容哈希；正式冻结时应补齐镜像身份记录。

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

donor 的 Torch 与 vLLM 顶层 import 已在登录节点通过；直接导入 CUDA 扩展因登录节点没有 `libcuda.so.1` 失败，完整 `vllm --help` 也因无法推断 device type 失败，保留这些实际边界。后续需在分配的最多四张 H100 上，以 Singularity `--nv` 验证 CUDA 13 驱动兼容、vLLM 扩展和完整 CLI、BF16 权重加载、图文及工具 HTTP、262,144 上下文、KV cache 显存与吞吐。CPU import、registry 条目或名义版本不能替代这些检查。
