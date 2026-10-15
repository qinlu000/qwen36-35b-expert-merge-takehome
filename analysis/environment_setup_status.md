# Base 与四项评测环境安装

更新：2026-10-16。用户授权下载准确 Base 和安装四项环境；无正式题作答、正式评分或训练。80 无 sudo，所有软件安装在项目 artifacts 内。

## 当前进度

| 项目 | 实际完成 | 尚待完成 |
| --- | --- | --- |
| Base 文件 | **80与HPC均完整到齐并独立校验：40文件、71,926,865,825B；26分片/1,045张量与固定index匹配** | 无剩余下载；不把文件校验当成GPU加载成功 |
| Base 推理环境 | HPC独立184包锁；723993在两H100/TP2/64K/8K上通过文本、图像、多轮工具、57,280-token长输入及越界400；本地缓存与退出清理均实测通过 | 满8K生成、并发/持续吞吐与四benchmark原生端点链路仍需验收；smoke服务已退出 |
| HLE | 固定源码、独立44包锁；2500题文件/ID/342图像计数核对；自造图文与schema检查通过 | 接入冻结的Qwen推理及Judge运行参数；不把安装通过当成正式评分完成 |
| SWE Pro HARD-51 | 固定源码、Harbor/mini环境、完整51任务、镜像digest | 镜像缓存、容器内mini依赖锁，以及官方locked流程的phase断网与模型白名单 |
| Terminal-Bench2 | 80/HPC固定Harbor0.24与完整89任务；89项均有预构建镜像，无Compose任务；两端真实TB镜像的Harbor/两次exec/tmux/asciinema/停止合成闭环通过 | 全量镜像预拉/容器启动、实际Slurm资源与端点验收；冷启动收尾补丁已完成两端回归 |
| ASI-Bench | 固定源码、657输入文件/60项目/240条件；45组依赖；v2已选DirectLLM，其执行隔离候选通过单次生成/执行、3组task env、ngspice及超时验收 | 实现正式预算/参数并验收全量运行；CPU/RAM约束、Qwen端点及最终Judge配置 |

各项详细证据：[HLE](setup_hle_status.md)、[SWE/TB](setup_swe_tb_status.md)、[ASI](setup_asi_status.md)、[Base runtime](setup_base_runtime_status.md)。正式执行应读取协议工作流最终冻结配置；本页记录安装，不替代协议或自动冻结thinking、adapter与Judge路线。

## 下载、同步与位置

- 80根目录：`/data/caoqinlu/projects/apex-takehome`；HPC根目录：`/data/user/qinlucao/projects/apex-takehome`。
- 两端权重路径均为根目录下`artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0`。
- 固定来源见`model_sources.json`，下载入口`scripts/download_base.py`。LFS检查SHA-256，小文件检查Git blob SHA-1；完成后检查26分片中所有tensor名称与固定index完全一致，不加载模型。
- 80日志：`artifacts/preflight/download-base-aria2.log`；HPC同步日志：`artifacts/preflight/sync-base-rsync.log`；完成回执在权重目录的`download_receipts.json`，只有complete=true且最终index_check通过才算下载完成。
- 大文件从80直连HF CDN，通过临时只读rsync端口43873直接同步HPC登录节点。服务只允许源IP10.120.48.33、只公开本公开Base目录，不包含凭据或HLE数据；**两端完整校验后已关闭43873服务**。HF元数据请求使用现有代理。
- HPC最终独立检查回执时间为2026-10-15T16:25:55Z（上海10月16日00:25:55），40文件全部通过，failures为空。确认完整后已清理本次旧下载的6,661,411,433B重复断点文件；失败日志继续保留。

## 容器实际边界

HPC默认Singularity4.1.5需要subuid mapping，当前账号没有。集群Apptainer1.4.5提供singularity兼容入口，可用官方root-mapped namespace，已在自造小SIF上通过uid0/可写临时层检查；这不等价于完整多UID映射。共享盘sandbox目录按管理员wrapper要求不能直接运行，构建时使用本地/tmp后输出标准SIF，没有关闭或绕过wrapper。

Harbor原生Singularity后端可以启动工具环境，但没有SWE所需phase网络开关，也不原生实现CPU/RAM quota。ASI原生linux_ns实测可读宿主sentinel；新增DirectLLM执行隔离候选已通过自造检查，但没有落实CPU/RAM限额。正式资源必须实际落实，不能仅在配置里填写额度。

ACD分区已实测拒绝CPU-only作业。容器检查作业723418为本次单独申请的1GPU/2CPU/4GB/5min，后已取消；未执行GPU计算，未改动原用户作业722434。后续GPU smoke最多使用授权的4卡，不复用原用户任务。

HPC首轮自造Harbor检查通过：启动31.14秒，两次exec成功，停止后端口关闭。当时用项目子类处理集群launcher收尾，后续显式patch见下文。140个固定digest镜像在80预拉并转为SIF；当前已统一为单个**16-worker代理队列，PID2878546**，实见16个pull、53条连接全部经过代理。2026-10-16 02:09（上海）复扫已有**109/140个final SIF，0失败**，其余31项继续下载；原8+补8两队列已精确停止，两个退出0的大TB镜像保留17,569,775,616B。最初GHCR小段直连测速较快，但整层反复PROTOCOL_ERROR/EOF，HTTP1也未解决；改走既有38080代理后，一个此前失败的1.08GB镜像完整拉取/分区表/SHA256检查通过，故当前远端registry均走代理，保持HTTP1。未修改用户代理，不承诺固定速度。安全回执见`source_snapshots/image_prefetch_transport_20261016.json`。

HPC镜像进程PID3040078只在源complete后额外rsync并逐140项检查SHA256、字节数和alias；不会因旧finished/failed回执提前停止。Mac收尾进程PID15079逐轮读取当前`image-prefetch.pid`，现有队列活着时不另起下载；必要时最多3轮全缓存复扫，然后等HPC的complete=true、sha256_verified=140及固定manifest匹配，才关闭本次SIF只读rsync。状态/日志为ignored `artifacts/preflight/swe_tb/download-pipeline.{json,log}`。当前全量仍未完成，没有运行正式题、模型或评分。

真实TB镜像检查两端已通过。随后针对上游60秒启动窗口及launcher无界等待，实际应用固定f527上的显式local patch：启动默认300秒、实例身份校验、服务日志落文件、关闭/等待有界；项目旧stop override同步移除。80/HPC各用同一固定SIF重验，约44/46秒通过两次exec、tmux、录屏和stop后端口关闭；故障分支8项合成通过。依赖锁和固定SIF未变。详见`scripts/harbor_startup_patch.md`；监听前已脱离launcher的bootstrap仍有清理边界，未证明全140项bootstrap、完整多UID、网络策略或资源限额。

Base运行容器18,337,001,472B已重新计算SHA-256，与原回执一致；身份固定在`configs/envs/base_runtime_container.json`。GPU smoke作业**723821已完成**：`sacct=COMPLETED / 0:0`，总用时5分07秒，启动270.19秒，`summary.json`为`passed=true`。两张H100 80GB、TP2/BF16，配置上下文262,144；纯文本、32×32红图、自动tool call和工具结果回传4个合成case全部通过，带key请求200、无key请求401。ready每卡显存占用70,627 MiB，请求后70,635 MiB。回执在`artifacts/preflight/base-smoke-723821/`，服务及作业已正常退出。

成功版本为每job在节点本地XFS `/tmp`创建独立目录并绑定至容器`/tmp`，Triton/vLLM/TorchInductor/FlashInfer/HF/XDG缓存均放其中，`MAX_JOBS=4`；健康等待1200秒，使用eager、最多4序列及GDN-prefill/MoE Triton backend。历史723706曾加载权重后耗尽容器私有`/tmp`；723727的项目临时目录版本编译超过600秒；723784虽约280秒启动并通过health/models鉴权，首文本仍因共享DPC Triton缓存元数据缺失返回500。迁本地cache后的723821才完成全部HTTP检查。历史失败日志保留，未改HOME、系统或管理员wrapper。

723821历史合成检查未填满长上下文；当前v2已选TP2单服务/65536总context/8192输出和关闭thinking，723993另已通过近边界长输入及同预算越界400。满8K生成、并发/持续吞吐和benchmark原生参数/共享deadline仍待验收，Judge还需独立校准。用户授权提高优先级后，Slurm默认分区为`emergency_acd`（PriorityTier/JobFactor300，高于`acd_ue`的200）；723821实际priority为10023，仍用本人qinlucao账号/formal-user QoS。未调整原有其他项目作业722434。


最新v2合成GPU作业**723993**已COMPLETED0:0（8分44秒），startup410.31秒，五项正例HTTP200与一项预算越界400通过。57,280实际prompt tokens与固定模板计数完全一致、携max_tokens8192成功；8token短标记输出不代表完整8K decode通过。批日志证实本次节点临时目录已删除，服务退出0。详见`setup_base_runtime_status.md`与`source_snapshots/base_gpu_smoke_v2_20261016.json`；未运行正式题、训练或评分。
