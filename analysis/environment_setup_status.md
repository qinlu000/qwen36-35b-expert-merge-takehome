# Base 与四项评测环境安装

更新：2026-10-16。用户授权下载准确 Base 和安装四项环境；无正式题作答、正式评分或训练。80 无 sudo，所有软件安装在项目 artifacts 内。

## 当前进度

| 项目 | 实际完成 | 尚待完成 |
| --- | --- | --- |
| Base 文件 | **80与HPC均完整到齐并独立校验：40文件、71,926,865,825B；26分片/1,045张量与固定index匹配** | 无剩余下载；不把文件校验当成GPU加载成功 |
| Base 推理环境 | HPC独立184包锁；723821在两H100上完成权重加载、鉴权及文本/图像/多轮工具4个合成HTTP检查，`passed=true`、退出0；本地`/tmp`缓存修复实测通过 | 长上下文、持续吞吐、正式四卡参数和评测节点到端点的链路尚未验收；smoke服务已退出 |
| HLE | 固定源码、独立44包锁；2500题文件/ID/342图像计数核对；自造图文与schema检查通过 | 接入冻结的Qwen推理及Judge运行参数；不把安装通过当成正式评分完成 |
| SWE Pro HARD-51 | 固定源码、Harbor/mini环境、完整51任务、镜像digest | 镜像缓存、容器内mini依赖锁，以及官方locked流程的phase断网与模型白名单 |
| Terminal-Bench2 | 80/HPC固定Harbor0.24与完整89任务；89项均有预构建镜像，无Compose任务；两端真实TB镜像的Harbor/两次exec/tmux/asciinema/停止合成闭环通过 | 全量镜像预拉/容器启动、冷启动超时收尾、实际Slurm资源与端点验收 |
| ASI-Bench | 固定源码、OpenCode1.17.15、657输入文件/60项目/240条件；45组任务依赖及自造CPU/工具检查通过；图片能力声明已补齐并离线解析通过 | 正式文件/网络隔离、CPU/RAM约束、Qwen端点及最终Judge配置 |

各项详细证据：[HLE](setup_hle_status.md)、[SWE/TB](setup_swe_tb_status.md)、[ASI](setup_asi_status.md)、[Base runtime](setup_base_runtime_status.md)。候选协议仍沿用80上的configs/eval/protocol_v1.json；安装不自动冻结尚待决定的thinking与Judge路线。

## 下载、同步与位置

- 80根目录：`/data/caoqinlu/projects/apex-takehome`；HPC根目录：`/data/user/qinlucao/projects/apex-takehome`。
- 两端权重路径均为根目录下`artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0`。
- 固定来源见`model_sources.json`，下载入口`scripts/download_base.py`。LFS检查SHA-256，小文件检查Git blob SHA-1；完成后检查26分片中所有tensor名称与固定index完全一致，不加载模型。
- 80日志：`artifacts/preflight/download-base-aria2.log`；HPC同步日志：`artifacts/preflight/sync-base-rsync.log`；完成回执在权重目录的`download_receipts.json`，只有complete=true且最终index_check通过才算下载完成。
- 大文件从80直连HF CDN，通过临时只读rsync端口43873直接同步HPC登录节点。服务只允许源IP10.120.48.33、只公开本公开Base目录，不包含凭据或HLE数据；**两端完整校验后已关闭43873服务**。HF元数据请求使用现有代理。
- HPC最终独立检查回执时间为2026-10-15T16:25:55Z（上海10月16日00:25:55），40文件全部通过，failures为空。确认完整后已清理本次旧下载的6,661,411,433B重复断点文件；失败日志继续保留。

## 容器实际边界

HPC默认Singularity4.1.5需要subuid mapping，当前账号没有。集群Apptainer1.4.5提供singularity兼容入口，可用官方root-mapped namespace，已在自造小SIF上通过uid0/可写临时层检查；这不等价于完整多UID映射。共享盘sandbox目录按管理员wrapper要求不能直接运行，构建时使用本地/tmp后输出标准SIF，没有关闭或绕过wrapper。

Harbor原生Singularity后端可以启动工具环境，但没有SWE所需phase网络开关，也不原生实现CPU/RAM quota。ASI linux_ns实测可读宿主sentinel，不能把它直接当作充分隔离的正式环境。正式资源必须实际落实，不能仅在配置里填写32CPU/48GiB或4CPU/8GiB。

ACD分区已实测拒绝CPU-only作业。容器检查作业723418为本次单独申请的1GPU/2CPU/4GB/5min，后已取消；未执行GPU计算，未改动原用户作业722434。后续GPU smoke最多使用授权的4卡，不复用原用户任务。

HPC的完整自造Harbor检查已通过：启动31.14秒，两次exec成功，停止后端口关闭。为兼容集群launcher，用19行子类在官方stop前调用官方`/shutdown`，不修改固定上游源码或网络能力。140个固定digest镜像正在80预拉并转为SIF，当前100/140、0失败；4个大TB镜像仍以约2.7–2.9 MB/s持续传输。HPC镜像进程已用新脚本重启为PID2266968，源完成后会额外rsync一次，再逐140项检查SHA256、字节数和alias；全140项最终回执尚未产生，不能写为全量缓存完成。

后续真实TB镜像检查在两端均通过（约52秒）：项目内fakeroot1.25.3配合官方root-map模式，基础设施启动hook处理既有Python路径、服务解释器副本与apt sandbox用户，未改固定SIF或上游源码。统一入口为`scripts/run_harbor_singularity.sh`，80还使用官方`APPTAINER_IGNORE_SUBUID=1`选较低权限模式。此适配不提供完整多UID映射、网络策略或资源限额。另一次冷启动超过上游60秒窗口并卡在launcher收尾，已清理；当前正常启停成功不能保证全部镜像的冷启动超时路径。

Base运行容器18,337,001,472B已重新计算SHA-256，与原回执一致；身份固定在`configs/envs/base_runtime_container.json`。GPU smoke作业**723821已完成**：`sacct=COMPLETED / 0:0`，总用时5分07秒，启动270.19秒，`summary.json`为`passed=true`。两张H100 80GB、TP2/BF16，配置上下文262,144；纯文本、32×32红图、自动tool call和工具结果回传4个合成case全部通过，带key请求200、无key请求401。ready每卡显存占用70,627 MiB，请求后70,635 MiB。回执在`artifacts/preflight/base-smoke-723821/`，服务及作业已正常退出。

成功版本为每job在节点本地XFS `/tmp`创建独立目录并绑定至容器`/tmp`，Triton/vLLM/TorchInductor/FlashInfer/HF/XDG缓存均放其中，`MAX_JOBS=4`；健康等待1200秒，使用eager、最多4序列及GDN-prefill/MoE Triton backend。历史723706曾加载权重后耗尽容器私有`/tmp`；723727的项目临时目录版本编译超过600秒；723784虽约280秒启动并通过health/models鉴权，首文本仍因共享DPC Triton缓存元数据缺失返回500。迁本地cache后的723821才完成全部HTTP检查。历史失败日志保留，未改HOME、系统或管理员wrapper。

这次合成检查分配2GPU/16CPU/128GiB/30min，未实际填满长上下文或测持续吞吐，也未验收正式四卡配置。thinking、Judge及各benchmark正式协议仍待各自冻结。用户授权提高优先级后，Slurm默认分区为`emergency_acd`（PriorityTier/JobFactor300，高于`acd_ue`的200）；723821实际priority为10023，仍用本人qinlucao账号/formal-user QoS。未调整原有其他项目作业722434。
