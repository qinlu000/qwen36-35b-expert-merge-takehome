# SWE / Terminal-Bench 环境准备实况

更新：2026-10-15。本文记录真实安装与检查结果；没有运行正式题作答或评分，没有读取 instruction、参考补丁或隐藏测试，没有调用付费模型。

## 已完成的安装

| 对象 | 80 主机 | HPC |
| --- | --- | --- |
| 项目根目录 | `/data/caoqinlu/projects/apex-takehome` | `/data/user/qinlucao/projects/apex-takehome` |
| Python | 项目独立 CPython 3.12.11 | 同一 standalone Python 已复制并验证可运行 |
| Harbor | `artifacts/envs/harbor`，0.24.0 | `artifacts/envs/harbor`，0.24.0 |
| Harbor 依赖 | 按固定官方 `uv.lock` 安装，含 Modal extra | 同一 lock；101 个 distribution 的版本与 80 逐项一致 |
| 核心依赖 | LiteLLM 1.93.0、OpenAI 2.24.0 | LiteLLM 1.93.0、OpenAI 2.24.0 |
| mini-swe-agent | 独立 `artifacts/envs/mini-swe`，2.4.6 | 官方 wrapper 在容器内安装；本轮未为 HPC 安装另一套宿主 mini |
| CLI / import | Harbor help/run-help、Terminus2、DockerEnvironment、LockedMiniSwe、PatchReplayAgent 均通过 | Harbor help/run-help、Terminus2、SingularityEnvironment 均通过 |

80 使用项目工具 `artifacts/tools/uv/uv` 0.8.22；HPC 安装器使用已有 `/data/user/qinlucao/bin/uv` 0.12.3。Python、venv、下载缓存均放项目 `artifacts/`；没有安装系统包、修改 Docker daemon、写系统 subuid/subgid 或占用 GPU。mini 启动配置单独设为 `artifacts/preflight/swe_tb/mini-config`，避免正式运行继承用户全局 mini 配置。

Harbor 依赖保持官方 lock；mini 的独立宿主依赖保存在 `configs/envs/mini-swe-py312.txt`，当前其中 LiteLLM 1.105.1、OpenAI 2.54.0。这个宿主 lock **不会自动约束**官方 LockedMiniSwe 在任务容器里执行的 `uv tool install`；正式 SWE 启动前还需固定容器内的 mini/LiteLLM/FastAPI 等依赖，并做实际请求验收。

## 固定源码、完整范围与镜像元数据

两个主机均已保存以下完整固定源码；HPC 由 80 的指定 Git commit 导出 archive，并额外保存 `SOURCE_REVISION`，没有用浮动 main 替代。

| 源码目录 | 固定 revision |
| --- | --- |
| `artifacts/benchmarks/harbor` | `f527f8e447038fd242d08ecfa8aaa8029100da97` |
| `artifacts/benchmarks/swe-bench-pro` | `66f92766bba642462d4bbe5479e83f91f9211862` |
| `artifacts/benchmarks/terminal-bench-2` | `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c` |

- SWE `hard51_ids.txt` 为 51 个唯一 ID，SHA256 `6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1`。`artifacts/benchmarks/swe-hard51` 仅以 symlink 物化这完整 51 项。
- TB 使用固定 Harbor registry 中 `terminal-bench@2.0` 的完整 89 项；`artifacts/benchmarks/terminal-bench-2-registered` 物化完整注册集。检查 89/89 个 `task.toml`：均有预构建 `docker_image`，89 个不同镜像，未发现 `environment/docker-compose.yml` 或 `.yaml`。这是原生 Singularity 的定义兼容检查，尚不代表 89 个镜像均已成功启动。
- 完整 51+89 个公开镜像已匿名查询 registry：**140/140 tag 均取得 OCI digest**。24 个多架构 index 另查得唯一 linux/amd64 manifest；116 个为单 manifest。首轮一个 GHCR TLS 瞬断，单项重试成功。结果固定于 `configs/envs/swe_tb_image_digests.json`，仅含镜像元数据。
- 140 个目标 manifest 的压缩层大小累计为 **137,955,104,637 bytes**；此数包含跨镜像重复层，未估算解压后的实际磁盘占用。**本轮没有批量拉取这些镜像层**。

80 原始检查工件位于 `artifacts/preflight/swe_tb/`：`install_check.json`、`task_image_manifest.json`、`images.txt`、`image_digests.json`、`tb_compatibility.json`、两个 requirements 清单和 CLI help。HPC 同目录保存 `hpc_install_check.json`、CLI help、镜像 digest 副本和自造容器检查记录。

来源：[SWE V2 官方说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)、[固定 Harbor registry](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)、[固定 Harbor 依赖定义](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/pyproject.toml)。

## 容器后端的真实边界

80 尚无可用 Docker daemon/socket，用户没有 sudo；本轮没有修改系统。HPC 原有 Singularity 4.1.5 的 `--fakeroot` 因 qinlucao 没有 `/etc/subuid` mapping 失败。固定 Harbor 的 Singularity 后端硬编码 `--fakeroot`，没有原生 kwargs 可以关闭。

主线已实测 `module load apptainer/1.4.5` 提供 `singularity` 同义入口，可通过官方支持的单 UID root-mapped namespace 执行自造 SIF，得到容器内 uid 0，并在可写临时层写入自造文件。没有配置系统 subuid；它不等价于完整多 UID rootless 模式，对 apt/chown/su 等仍需实际验收。[Apptainer 1.4 官方说明](https://apptainer.org/docs/user/1.4/fakeroot.html)、[SingularityCE 4.4 仍要求 subid mapping](https://docs.sylabs.io/guides/4.4/user-guide/fakeroot.html)。

进一步的完整 Harbor bootstrap 检查正在使用自造环境与现有 slime Ubuntu24 SIF，直接调用未修改的 `SingularityEnvironment.start → exec → stop`；结果见 `artifacts/preflight/swe_tb/harbor-singularity-smoke.log` 与 `synthetic-harbor/result.json`。该检查不启动模型或正式任务。

即使 bootstrap 通过，仍有以下正式执行条件：

1. **SWE locked 网络策略尚未解决**：固定 Singularity 后端只声明 `mounted=True`，没有 agent 阶段断网、模型 endpoint allowlist 或 phase network 切换能力。不能把它直接当作满足官方 locked SWE 协议的后端；仍需已获授权、满足这些能力的 backend。
2. **TB CPU/RAM 需在实际 allocation 落实**：Singularity 的 `resource_capabilities()` 中 CPU/内存 limit/request 全为 false；源码建议由 Slurm 约束。`32 CPU / 49152 MiB` 写入配置不等于取得了相应资源。宿主 watchdog 也不能替代资源预留。
3. 尚未逐一拉取并 bootstrap 89 个 TB 镜像；现有自造 SIF 不能证明全部任务依赖可用。Harbor bootstrap 会补系统 Python、FastAPI/uvicorn、tmux/asciinema，代理必须在执行节点实际可达。
4. Base endpoint、Qwen 真实请求参数、工具交互和长历史摘要仍待模型服务验收。固定 `LITELLM_LOCAL_MODEL_COST_MAP=True` 避免启动时从浮动 main 获取上下文/价格表，仍需按总协议为自部署 Qwen 显式注册 model_info。

官方实现：[固定 Singularity 后端](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)。本轮不把 CLI/import 成功或 tag 可解析称为正式评测已经就绪。

## 复现入口

80 在项目根目录执行 `bash scripts/setup_swe_tb.sh`：固定源码、独立环境、完整任务目录和纯元数据检查均可重建。Harbor 使用官方 uv.lock；mini 使用仓库中的版本清单。脚本重复执行已成功，未重新解析更高依赖版本。

HPC 在固定 archive 与 Python 已复制到项目后，执行 `bash scripts/setup_hpc_harbor.sh`。该脚本已成功重复执行并检查完整 51/89 项资源元数据。下载所需 HTTP(S) proxy 只在进程环境设置，不写系统配置。

镜像元数据可用 `scripts/resolve_benchmark_images.py <images.txt> <output.json>` 重新检查；既有 digest 是本次冻结值，不能因为后续 tag 漂移静默替换。

完整无模型容器检查入口为 `scripts/smoke_harbor_singularity.py --root <project> --image <existing.sif>`；先加载 `apptainer/1.4.5`，配置执行节点可达的代理，并把 localhost 加入 NO_PROXY。正式题、评分或训练尚未启动。
