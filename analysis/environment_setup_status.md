# Base 与四项评测环境安装

更新：2026-10-16。用户授权下载准确 Base 和安装四项环境；无正式题作答、正式评分或训练。80 无 sudo，所有软件安装在项目 artifacts 内。

## 当前进度

| 项目 | 实际完成 | 尚待完成 |
| --- | --- | --- |
| Base 文件 | **80与HPC均完整到齐并独立校验：40文件、71,926,865,825B；26分片/1,045张量与固定index匹配** | 无剩余下载；不把文件校验当成GPU加载成功 |
| Base 推理环境 | HPC独立184包锁；Ubuntu24 SIF内CPU import、准确架构和自造图文预处理通过；两卡检查作业723673已提交acd_ue | 作业当前排队，GPU加载、真实HTTP图文/工具往返及长上下文资源尚未验收 |
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

HPC的完整自造Harbor检查已通过：启动31.14秒，两次exec成功，停止后端口关闭。为兼容集群launcher，用19行子类在官方stop前调用官方`/shutdown`，不修改固定上游源码或网络能力。140个固定digest镜像正在80预拉并转为SIF，尚不能把首批成功外推为全140项完成。

后续真实TB镜像检查在两端均通过（约52秒）：项目内fakeroot1.25.3配合官方root-map模式，基础设施启动hook处理既有Python路径、服务解释器副本与apt sandbox用户，未改固定SIF或上游源码。统一入口为`scripts/run_harbor_singularity.sh`，80还使用官方`APPTAINER_IGNORE_SUBUID=1`选较低权限模式。此适配不提供完整多UID映射、网络策略或资源限额。另一次冷启动超过上游60秒窗口并卡在launcher收尾，已清理；当前正常启停成功不能保证全部镜像的冷启动超时路径。

Base运行容器18,337,001,472B已重新计算SHA-256，与原回执一致；身份固定在`configs/envs/base_runtime_container.json`。GPU smoke脚本为`scripts/smoke_base.slurm`。首个四卡作业723633因排队预测延后，确认仍PENDING后由本次工作取消，未占GPU；现以`sbatch --partition=acd_ue --gres=gpu:2 --mem=128G`提交作业723673（2GPU/16CPU/128GiB/30min），等待结果。仅做自造文本/图片/工具往返，不是正式Base跑分或正式资源冻结。
