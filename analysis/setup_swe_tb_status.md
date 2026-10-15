# SWE / Terminal-Bench 环境准备实况

更新：2026-10-16。本文记录真实安装与检查结果；没有运行正式题作答或评分，没有读取 instruction、参考补丁或隐藏测试，没有调用付费模型。

## 已完成的安装

| 对象 | 80 主机 | HPC |
| --- | --- | --- |
| 项目根目录 | `/data/caoqinlu/projects/apex-takehome` | `/data/user/qinlucao/projects/apex-takehome` |
| Python | 项目独立 CPython 3.12.11 | 同一 standalone Python 已复制并验证可运行 |
| Harbor | `artifacts/envs/harbor`，0.24.0 | `artifacts/envs/harbor`，0.24.0 |
| Harbor 依赖 | 按固定官方 `uv.lock` 安装，含 Modal extra | 同一 lock；101 个 distribution 的版本与 80 逐项一致 |
| 核心依赖 | LiteLLM 1.93.0、OpenAI 2.24.0 | LiteLLM 1.93.0、OpenAI 2.24.0 |
| 用户态 fakeroot | 项目内 1.25.3，两个 Debian 包按官方 SHA256 校验 | 同一包与重定位脚本，宿主及容器实际执行通过 |
| mini-swe-agent | 独立 `artifacts/envs/mini-swe`，2.4.6 | 官方 wrapper 在容器内安装；本轮未为 HPC 安装另一套宿主 mini |
| CLI / import | Harbor help/run-help、Terminus2、DockerEnvironment、LockedMiniSwe、PatchReplayAgent 均通过 | Harbor help/run-help、Terminus2、SingularityEnvironment 均通过 |

80 使用项目工具 `artifacts/tools/uv/uv` 0.8.22；HPC 安装器使用已有 `/data/user/qinlucao/bin/uv` 0.12.3。Python、venv、下载缓存均放项目 `artifacts/`；没有安装系统包、修改 Docker daemon 或写系统 subuid/subgid。安装脚本不执行 GPU 计算或提交 Slurm。mini 启动配置单独设为 `artifacts/preflight/swe_tb/mini-config`，避免正式运行继承用户全局 mini 配置。

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
- 140 个目标 manifest 的压缩层大小累计为 **137,955,104,637 bytes**；此数包含跨镜像重复层，未估算解压后的实际磁盘占用。已启动按固定 amd64 digest 的全量 SIF 预取，TB 优先；2026-10-16 00:32（上海）检查时，80 与 HPC 均有 **81/140 个最终 SIF、0 下载失败、12,778,250,240 bytes SIF**。全量仍在下载和传输，不能标成 140 个已就绪；缓存成功也不等于内部 bootstrap 成功。

80 原始检查工件位于 `artifacts/preflight/swe_tb/`：`install_check.json`、`task_image_manifest.json`、`images.txt`、`image_digests.json`、`tb_compatibility.json`、两个 requirements 清单和 CLI help。HPC 同目录保存 `hpc_install_check.json`、CLI help、镜像 digest 副本和自造容器检查记录。

来源：[SWE V2 官方说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)、[固定 Harbor registry](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/registry.json)、[固定 Harbor 依赖定义](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/pyproject.toml)。

## 容器后端的真实边界

80 尚无可用 Docker daemon/socket，用户没有 sudo；本轮没有修改系统。HPC 原有 Singularity 4.1.5 的 `--fakeroot` 因 qinlucao 没有 `/etc/subuid` mapping 失败。固定 Harbor 的 Singularity 后端硬编码 `--fakeroot`，没有原生 kwargs 可以关闭。

主线已实测 `module load apptainer/1.4.5` 提供 `singularity` 同义入口，可通过官方支持的单 UID root-mapped namespace 执行自造 SIF，得到容器内 uid 0，并在可写临时层写入自造文件。没有配置系统 subuid；它不等价于完整多 UID rootless 模式，对 apt/chown/su 等仍需实际验收。[Apptainer 1.4 官方说明](https://apptainer.org/docs/user/1.4/fakeroot.html)、[SingularityCE 4.4 仍要求 subid mapping](https://docs.sylabs.io/guides/4.4/user-guide/fakeroot.html)。

完整 Harbor bootstrap 已使用自造环境与现有 slime Ubuntu24 SIF 实测：启动 31.14 秒，容器内 uid 0，FastAPI 0.143.2 / Uvicorn 0.54.0；两次 exec 与自造文件持久性检查通过，总耗时 32.00 秒，停止后端口关闭。结果见 `artifacts/preflight/swe_tb/harbor-singularity-smoke.log` 与 `synthetic-harbor/result.json`，没有模型调用或正式任务。上游 bootstrap 的联网 pip install 本身仍使用浮动依赖；本轮记录了实测版本，正式比较前还需固定/留存各容器实际运行依赖，不能把宿主的官方 uv.lock 当作容器内依赖锁。

验收中发现原生 stop 先终止站点 launcher，不能停止已经分离的 appinit/server；原父 PID 消失后，唯一自造端口仍由本次 `_hbexec.py` 监听，并触发 asyncio pipe 的 event-loop-closed traceback。已清理确认属于本次自造实验的残留 server。本项目增加小型 `scripts/apex_singularity.py:ApexSingularityEnvironment`，在 stop 前调用**官方 server 已有的 `/shutdown`**，再调用官方 stop；重新运行完整原场景后，端口关闭断言通过且无该 traceback。固定 Harbor 源码、exec、评分和资源/网络能力未更改，启动另加下述基础设施 hook。正式采用此站点适配时需显式使用该 import_path，不能仍将它写成完全未修改的原生后端。

### 真实 TB 镜像的合成验收与新增缺口

本轮额外选取已缓存真实 TB 镜像，只运行自造 echo、临时文件与生命周期检查，没有装载任务目录、题面、测试或模型：

- `compile-compcert:20251031`（固定 amd64 digest `f316947b…e1a7f`，SIF 30,019,584 bytes）原生 bootstrap 三次均报无法安装 `/usr/bin/python3`。诊断确认容器内 HTTP(S)_PROXY 正确为登录节点 `127.0.0.1:38082`；真正首个错误是 apt 对 `_apt` 用户执行 setgroups/setegid/seteuid 时失败，随后索引缺失。临时层使用 `APT::Sandbox::User=root` 后，实际安装 Python 3.12.3 成功；仍有其他组 chown 的警告。这只确认基础 Python 安装，不代表该镜像的完整终端环境通过。
- `build-cython-ext:20251031`（固定 amd64 digest `3612a38f…34594`，SIF 284,221,440 bytes）已有 `/usr/local/bin/python3` 3.13.7，原生 bootstrap 仍因只检查 `/usr/bin/python3` 而失败。新增 `scripts/apex_rootmap_bootstrap.sh` 由 Apex 子类只读 bind 至 Apptainer 原生 `/.singularity.d/env/99-apex-rootmap.sh`：在本次 writable-tmpfs 层复用已有 Python 的 symlink，并写单条 apt sandbox=root 配置。后续发现 apt 安装 asciinema 会替换 `/usr/bin/python3`，使原生 venv 改用另一 Python 版本而丢失依赖，因此 hook 另用已有解释器创建 `--copies` 的 `/opt/harbor-server`，固定服务解释器。固定 SIF、其 SHA256、镜像别名与上游源码没有修改，也没有添加题目工具。
- 上述适配后，真实 build-cython-ext 的 **Harbor start → 两次自造 exec → stop 通过**：启动 42.39 秒，总计 43.27 秒，容器 uid 0，FastAPI 0.143.2 / Uvicorn 0.54.0；临时文件跨 exec 保留，结束后端口关闭。原失败回执保留。SIF SHA256 仍为 `0749503602dbf6a1a276c419ce15f24c79f01f4a47139c7e22a89f08ca070e77`。
- 最初同一日志中 apt 解包 `libutempter0` 因设置其他组 ownership 失败，导致 tmux 缺少 `libutempter.so.0`，启动返回 127。Harbor 健康检查与普通 exec 成功没有发现此缺口。后续通过下述官方 fakeroot mode 3 实际解决安装，单 UID root-map 本身并没有变成完整 UID/GID 映射。

HPC 回执在 `artifacts/preflight/swe_tb/`：`real-tb-{compile-compcert,build-cython-ext}-smoke.log`、`compile-compcert-bootstrap-{diagnostic,root-sandbox}.log`、`real-tb-build-cython-ext-rootmap-smoke.log`；成功 JSON 位于 `real-tb-build-cython-ext-rootmap/artifacts/preflight/swe_tb/synthetic-harbor/result.json`。每次使用独立自造 cache 目录，避免现有 smoke 脚本的固定 alias 误复用另一 SIF。

针对这个缺口，已按 [Apptainer 官方 mode 3](https://apptainer.org/docs/user/1.4/fakeroot.html) 在本项目安装用户态 fakeroot command/library，与 root-map 配合处理 ownership，未配置完整 subuid 映射。HPC 原本无 fakeroot command/module，宿主 glibc 2.28。现用 Debian bullseye `fakeroot` 与 `libfakeroot` 1.25.3-1.1，分别核对官方 SHA256 `b67966ee7bad5e87f4ae7eecb6f4fe76ba7c12af7b9876c09f1e758eb742232c`、`04dace71ea2e14940bd0491e41331df77b5a5da82fe98ead228df756b4fe0bc8`；只解包至 `artifacts/tools/fakeroot-1.25.3/rootfs`，使用 [官方安装脚本](https://raw.githubusercontent.com/apptainer/apptainer/v1.4.5/tools/install-unprivileged.sh) 同样的路径重定位原则。`readelf` 确认 daemon 与 preload library 的最高 GLIBC 符号需求为 2.14；宿主运行与真实 Debian TB 镜像中的自动绑定均通过，容器日志明确显示 `Using fakeroot command combined with root-mapped namespace`，自造文件 chown 123:456 / stat 回读通过。安装复现脚本为 `scripts/install_fakeroot_user.sh`；[fakeroot 包与校验值](https://packages.debian.org/bullseye/amd64/fakeroot/download)、[libfakeroot 包与校验值](https://packages.debian.org/bullseye/amd64/libfakeroot/download)。

仅追加 apt sandbox=root 或忽略包管理退出码均不能解决 tmux 缺库；fakeroot 的文件语义模拟也不等于完整 UID/GID 映射。正式运行不应在计算节点依赖登录节点 loopback 代理；基础 Python、server wheels、tmux/asciinema 应缓存并记录实际版本。

80 用户已在系统 subuid 中登记，但缺 newuidmap；默认 `--fakeroot` 会优先选择多 UID 模式而失败。固定 Apptainer 1.4.5 的 [官方 action flags](https://raw.githubusercontent.com/apptainer/apptainer/v1.4.5/cmd/internal/cli/action_flags.go) 确实提供 hidden `--ignore-subuid` / `APPTAINER_IGNORE_SUBUID`。80 项目启动器显式设 `APPTAINER_IGNORE_SUBUID=1`，实际进入较低权限的官方 root-map + fakeroot mode 3，容器 uid 0、已有 Python 与独立 server Python 均为 3.13.7；回执 `80-fakeroot-ignore-subuid-smoke.log`。未改系统 subuid、安装 setuid helper 或改站点 wrapper。

最终同一真实 build-cython-ext SIF 的自造终端完整闭环在两端均通过：

| 主机 | start | 总耗时 | 实际结果 |
| --- | --- | --- | --- |
| HPC | 51.59 秒 | 52.72 秒 | tmux 3.3a、asciinema 2.2.0；PTY 会话收到自造命令并写回标记，录制保存成功，普通 exec / 临时文件保持 / stop 端口关闭均通过 |
| 80 | 51.25 秒 | 52.51 秒 | 同上；使用项目非 suid Apptainer 与官方 IGNORE_SUBUID 模式选择 |

最终回执为各主机 `artifacts/preflight/swe_tb/real-tb-build-cython-ext-terminal-poll/artifacts/preflight/swe_tb/synthetic-harbor/result.json`；HPC 顶层日志 `real-tb-build-cython-ext-terminal-poll-smoke.log`，80 顶层日志加 `80-` 前缀。终端探针使用独立 socket、无 profile 的自造 shell，通过短轮询确认命令真正写出自造文件，避免 wait-for 信号时序影响验收。没有运行正式 agent、题目或 verifier。

**仍有一次真实冷启动超时的边界**：另一轮 bootstrap 超过上游硬编码 60 秒 readiness 窗口，原生 kill launcher 后卡在 `await process.wait()`，因为已分离 server 仍继承管道。那次没有通过普通 exec，已中断该自造检查并对其准确记录端口调用官方 `/shutdown`；旧 PID 与所有已知子 PID 均消失、端口关闭，复核回执 `real-tb-fixedprobe-cleanup.json`，原失败日志保留。当前子类的清理改动覆盖正常启动后的 stop，尚不保证这种上游启动超时路径自动收尾。两端最终 52 秒的成功不证明 89 个镜像都能完成冷启动；下一步应缓存基础依赖并处理启动超时的原生收尾，不能直接标记全部环境 ready。

即使 bootstrap 通过，仍有以下正式执行条件：

1. **SWE locked 网络策略尚未解决**：固定 Singularity 后端只声明 `mounted=True`，没有 agent 阶段断网、模型 endpoint allowlist 或 phase network 切换能力。不能把它直接当作满足官方 locked SWE 协议的后端；仍需已获授权、满足这些能力的 backend。
2. **TB CPU/RAM 需在实际 allocation 落实**：Singularity 的 `resource_capabilities()` 中 CPU/内存 limit/request 全为 false；源码建议由 Slurm 约束。`32 CPU / 49152 MiB` 写入配置不等于取得了相应资源。宿主 watchdog 也不能替代资源预留。
3. 全量镜像预拉仍在进行，尚未逐一 bootstrap 89 个 TB 镜像。真实小镜像的两端 server/终端完整合成闭环已通过，ownership 与服务 Python 替换问题通过上述项目基础设施适配解决；上游冷启动超时收尾仍有已观察到的缺口。Harbor bootstrap 会补系统 Python、FastAPI/uvicorn、tmux/asciinema，代理必须在执行节点实际可达。
4. Base endpoint、Qwen 真实请求参数、工具交互和长历史摘要仍待模型服务验收。固定 `LITELLM_LOCAL_MODEL_COST_MAP=True` 避免启动时从浮动 main 获取上下文/价格表，仍需按总协议为自部署 Qwen 显式注册 model_info。

官方实现：[固定 Singularity 后端](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)。本轮不把 CLI/import 成功或 tag 可解析称为正式评测已经就绪。

## 复现入口

80 在项目根目录执行 `bash scripts/setup_swe_tb.sh`：固定源码、独立环境、完整任务目录和纯元数据检查均可重建。Harbor 使用官方 uv.lock；mini 使用仓库中的版本清单。脚本重复执行已成功，未重新解析更高依赖版本。

HPC 在固定 archive 与 Python 已复制到项目后，执行 `bash scripts/setup_hpc_harbor.sh`。该脚本已成功重复执行并检查完整 51/89 项资源元数据。下载所需 HTTP(S) proxy 只在进程环境设置，不写系统配置。

镜像元数据可用 `scripts/resolve_benchmark_images.py <images.txt> <output.json>` 重新检查；既有 digest 是本次冻结值，不能因为后续 tag 漂移静默替换。

完整无模型容器检查入口为 `scripts/smoke_harbor_singularity.py --root <project> --image <existing.sif>`；先加载 `apptainer/1.4.5`，再执行 `export PATH="$PWD/artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin:$PATH"`，配置执行节点可达的代理，并把 localhost 加入 NO_PROXY。该脚本采用上述站点 bootstrap/清理适配，检查 start、两次 exec、tmux 自造会话、asciinema 自造录制、stop 和端口关闭。正式题、评分或训练尚未启动。

**未来 Harbor CLI 必须显式选择子类**，只写 `-e singularity` 不会启用清理适配。固定版本原生支持如下最短入口（此处仅打印配置，不启动任务）：

```bash
export PYTHONPATH="$PWD/scripts" LITELLM_LOCAL_MODEL_COST_MAP=True
artifacts/envs/harbor/bin/harbor run \
  -p artifacts/preflight/swe_tb/synthetic-harbor -a nop \
  -e apex_singularity:ApexSingularityEnvironment --print-config
```

JSON 的等价写法为 `environment.type=null`、`environment.import_path="apex_singularity:ApexSingularityEnvironment"`，示例保存于 `configs/eval/harbor_singularity_synthetic.json`。HPC 已实际运行 CLI 的 flag 与 config 两种 `--print-config`，再用 `JobConfig` 解析、`EnvironmentFactory.resource_capabilities` 原生导入子类；两条路径均通过，四个 CPU/内存能力仍为 false。解析回执为 `custom-environment-cli-{config,flag}.json`。正式 TB 需在此基础上应用已冻结的模型和资源协议，不能直接用这个 nop/自造路径示例冒充正式配置。

两端统一使用 `bash scripts/run_harbor_singularity.sh <harbor run 参数>`，不要依赖某次交互 shell 遗留的 PATH。脚本在 HPC 显式 source Modules、`module use /data/modulefiles/opensource`、加载 apptainer/1.4.5，然后 prepend 项目 fakeroot；80 选择项目 Apptainer 并设上述 IGNORE_SUBUID。它还加入项目 scripts 的 PYTHONPATH、固定本地模型表、设置 localhost NO_PROXY，并明确传入 `--env apex_singularity:ApexSingularityEnvironment`。HTTP(S)_PROXY 仍由调用环境按执行节点配置。两端 `--help` / `--print-config` 已实测，回执 `harbor-project-wrapper-help.txt`、`custom-environment-project-wrapper.json`；没有启动正式任务。

## 进行中的镜像下载与传输

80 已按官方发布 SHA256 校验 `apptainer_1.4.5_amd64.deb`，仅在 `artifacts/tools/apptainer-1.4.5/rootfs` 解包；`buildcfg` 确认为 `APPTAINER_SUID_INSTALL=0`。配置文件位于项目内，mksquashfs 初始限制每进程2 CPU/1 GiB；00:39发现大型镜像进入压缩后，将后续新builder调为4 CPU/1 GiB，不重启或丢弃在途拉取。prefetch 初始并发2，后调至4，2026-10-16 00:17调至8；8个builder最多约32压缩CPU，仍低于采样空闲资源。下载过程未执行容器内容。安装复现脚本为 `scripts/install_apptainer_user.sh`。[官方发布资产](https://github.com/apptainer/apptainer/releases/expanded_assets/v1.4.5)

- 下载脚本：`scripts/prefetch_benchmark_images.py --root <project> --workers 8`；80 当前后台 PID 为 2262293，记录于 `artifacts/preflight/swe_tb/image-prefetch.pid`，日志为同目录 `image-prefetch.log`，每镜像独立拉取日志在 `image-pulls/`。本次安全重启前 72 个 SIF 已缓存；停止并核对旧 PID 1134008 及本任务子进程后，继承原代理环境重启，新进程恢复 72 个缓存、0 失败，实见 8 个 pull 子进程。最终 SIF 与完成的 layer cache 未删除，旧日志/进度和重启回执保存为 `image-prefetch.workers4.20261016-001702.log`、`image-prefetch.progress.workers4.20261016-001702.json`、`image-prefetch-restart.20261016-001702.json`。
- 完整进度与每个产物的 SIF SHA256：`artifacts/benchmarks/sif/_prefetch_progress.json`。先按 manifest digest 保存数据，再创建与固定 Harbor cache 规则一致的原 tag 同名 symlink。只解析 SIF 分区表并哈希二进制，不打开内部任务文件。
- 对固定公开 layer 的小段压缩字节做网络吞吐检查：GHCR CDN 直连约 3.51 MB/s、经代理约 1.96 MB/s，因此 ghcr.io 与 pkg-containers.githubusercontent.com 在下载进程中加入 NO_PROXY。Docker registry/CDN 直连不稳定，继续使用代理。此测试没有解压或查看文件内容，也不承诺整套下载的固定时长。
- 80 独立只读 rsync：`10.123.4.80:43874/benchmark_sif`，仅导出 `artifacts/benchmarks/sif`，只允许 HPC 登录出口 `10.120.48.33`；未修改 Base 的 `43873` 模块或路径。配置与 PID 位于 `artifacts/preflight/swe_tb/rsync-sif.*`。
- HPC 镜像脚本：`scripts/mirror_benchmark_sifs.sh`，后台 PID 记录于 `artifacts/preflight/swe_tb/sif-mirror.pid`，日志为同目录 `sif-mirror.log`。持续传输本次下载的已完成 SIF；源进度 complete/finished 后再做一次完整 rsync，避免最后镜像在上一轮 file-list 建立后才完成的竞态，然后退出。镜像产物写入 HPC 同相对目录。
- 已实传并在 HPC 对首 **15 个 SIF / 515,747,840 bytes** 逐个验证 SHA256 与 80 回执一致。后续新增产物仍在传输。
- 主线后续在 HPC 对当时全部 **77 个 SIF** 重算 SHA256 并核 alias，均匹配；回执 `artifacts/preflight/swe_tb/sif-hpc-integrity.json`。本轮选中的 build-cython-ext 也另外实际重算 SHA256，与上述回执一致。

正式使用本地缓存时，将 `singularity_image_cache_dir` 指向该主机的 `artifacts/benchmarks/sif`。完整就绪必须读取最终进度确认 `completed=140, failed=0, status=complete`，再核实 HPC 文件完整及所需环境 bootstrap；后台 PID 存在不代表下载完成。

30 秒只读资源采样回执为 80 的 `prefetch-resource-sample.json`：128 逻辑 CPU 的全机 idle 为 50.5%，MemAvailable 约 1.81 TiB；预取存活进程树 RSS 约 384 MiB，CPU 计数下界 0.29 核（不含采样间退出的子进程）。1 Gbps 网卡汇总 RX 16.8 MB/s、TX 31.1 MB/s，包含其他作业流量。CPU/RAM 与本机链路有余量，支持尝试 8 并发；外部 registry/代理瓶颈未由此排除，不能承诺吞吐翻倍。

## Slurm 资源边界（只读快照）

本轮没有申请 GPU、提交新作业或借用已有 allocation。当前实际分区名为默认 `acd_u`、`acd_ue`、`emergency_acd` 与 `debug`，不是 `ACD`。`acd_u` 最大 7 天、40 节点，`debug` 最大 30 分钟；debug_qos 每用户最多 12 CPU / 1 GPU / 240G / 1 节点，因此不适合冻结协议中单 TB trial 的 32 CPU / 49152 MiB / 3 小时 agent 时限。作业总时限还需覆盖 setup 与 verifier，不能恰好只给 3 小时。

用户默认 account 为 qinlucao，formal-user 与 normal 的 `MaxTRESPU` 均为 **每用户合计** 192 CPU / 16 GPU / 3840G，最多 20 个运行、50 个提交作业；不是每个 trial 的额度，也不是已经可用的资源。本快照已有其他用户作业占用 12 CPU / 1 GPU / 160G，未操作该作业。此前主线的 CPU-only `sbatch --test-only` 被站点 Lua 要求 `--gres=gpu:N`，本轮未重新提交。正式 TB 仍须取得符合协议的实际 allocation 或已获授权的 CPU 资源入口，再决定并发；Singularity kwargs 和宿主 watchdog 不能代替 Slurm CPU/RAM 预留。当前登录节点的合成验收不证明正式 Slurm 调度已完成。
