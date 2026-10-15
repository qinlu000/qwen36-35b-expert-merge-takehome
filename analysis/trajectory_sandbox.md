# 轨迹介绍中的sandbox：来源、可恢复性与目标差异

日期：2026-10-16（上海）。本轮补读轨迹介绍、作者论文、上游任务环境schema、通用构建/执行代码和训练任务包环境文件；只检查元数据与通用源码。没有执行轨迹命令、容器、模型或正式任务，没有读取正式题答案、gold程序或隐藏测试，没有拉取镜像层或安装依赖。

## 结论

### 用户明确的方案前提：训练与最终评测一致性优先

用户重申的核心目标是让训练轨迹的sandbox接近最终四项benchmark的执行环境，并优先让评测harness与对应轨迹harness一致；这是主训练数据的资格前提。前面的“可复用/无需全池重采”均以满足这一前提为条件，不能由可解析、同属Linux或数据已经下载就直接选作主数据。

- 每项benchmark分别对齐工具/提示/观察、shell状态、完成方式，以及依赖、输入初始化、权限、网络和资源政策。任务内容保持独立，官方测试镜像/评分契约保持题定范围；不要求四项共用一个harness。
- 在题目允许的agent入口内，优先选择轨迹已经使用的harness，并补核版本与sandbox行为；TB仍遵循题定Harbor/Terminus-2。此前SWE mini与ASI OpenCode都是候选，不能为了保留候选实现而强行把不相容轨迹升为主数据。
- 每项正式Base开始前确定并冻结该项harness，随后Base/各专家/合版共用相同配置。兼容未验的记录保持待验证；确定存在差异时，选择更匹配的轨迹/合规agent，或在目标设置下真实补采。
- 当前D3静态程序与ASI OpenCode多轮没有对齐，只能保留辅助候选，不能宣称已满足ASI主交互训练要求。最终训练主配方先满足环境与harness一致性，再考虑清洗成本和可用量。

**轨迹来源并非完全缺少环境信息。** Terminal提供了最直接的任务环境文件；Open-SWE可通过上游任务ID找到镜像与初始化字段；D3作者明确报告程序经对应环境验证后才保留。因此不能因为轨迹表没有image列，就认定环境无法恢复或必须重采全部教师数据。

需要分别记录：轨迹采集时实际用的sandbox、作者发布供用户恢复的任务环境、我们最终部署的评测sandbox。三者相关，但数据卡/默认配置不能自动证明逐条运行时完全一致。

| 轨迹来源 | 已有环境证据 | 对复用的意义 | 原采集sandbox仍缺什么 |
| --- | --- | --- | --- |
| Open-SWE mini/Qwen3.6 | source记录有hf_dataset_name/instance_id；Scale-SWE上游提供image_url/workdir/parent_commit/pre_commands；SWE-rebenchV2提供image_name/base_commit/install_config | 提供按原任务恢复镜像、repo初态和依赖的入口；尚未完成上游逐题联表、镜像可用性和collector额外初始化验证 | 固定轨迹发布没有mini采集launcher/config；精确mini版本、UID/网络/CPU/RAM/超时、原镜像digest与路径改造未逐条锁存 |
| Nemotron Terminal | 论文为Docker容器+tmux/Terminus2；mixed六包有Dockerfile、task.toml和输入files；5,984份顶层配置均为1CPU/2G、agent/verifier900s、build600s | 可恢复独立终端任务，用于dev或少量补采；题面已匹配的mixed最容易先做关联 | task默认值不等于teacher运行覆盖；内网registry的latest引用无digest，公开Dockerfile依赖未锁；实际UID/网络/挂载/资源覆盖未完整披露 |
| D3-Gym-Trajectories | 作者报告每任务采16个推理+完整程序，执行silver evaluator后仅保留成功；32B为2,153条；另发布task_N Docker环境 | 现成程序可继续作静态科研SFT候选，不要求全部重新生成；任务镜像可供少量独立执行验证 | 逐条镜像digest/运行日志/OS/UID/网络/配额未关联；这批记录没有OpenCode多轮动作和观察 |

详细来源与证据分级：[SWE](trajectory_sandbox_swe.md)、[Terminal](trajectory_sandbox_terminal.md)、[D3/ASI](trajectory_sandbox_asi.md)。

## 具体环境差异及能做什么

### SWE：可恢复原任务环境，不能把上游默认冒充采集配置

SWE-rebench通用模板按base_commit初始化仓库并安装依赖；其工作目录可以是仓库名路径，而已检查Open-SWE提示要求/testbed。可能存在collector另做路径映射/重打包，不能在没有采集脚本时断言“上游镜像原样就是teacher环境”。Scale-SWE的AweAgent示例资源也不是NVIDIA mini的采集预算。旧Open-SWE论文讲OpenHands/SWE-agent，不能用旧框架参数填补mini版本空白。

目标SWE V2则明确使用逐题官方镜像、sanitised base checkout；agent解题阶段仅允许模型端点出网，评分在全新镜像重放patch。其初始化/网络/提交政策与源轨迹是否一致要分项核，不能只比较Docker标签。[固定V2协议](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)

### Terminal：基础工具环境相近，但重建不保证原始版本

本次任务包顶层Dockerfile为Ubuntu24.04系列基底、Python3.12、WORKDIR /app、COPY files/ /app/；相同领域复用相同顶层构建配方。没有显式USER或网络限制不能直接推断原采集时实际UID/网络策略。内部registry的latest引用也不能当作已验证可匿名拉取的固定原镜像。

公开Dockerfile可以重建，但未锁apt/pip版本、基底latest及逐题输入初始化会影响复现。若采用当前NeMo共享镜像→SIF方案，必须确认每题files在启动时正确复制；只构建一次某题COPY后的镜像再全领域复用，不能保证其他题输入正确。这是我们候选重建方法的初始化风险，不是原教师数据有错的证据；当前NeMo工程源码不是原论文采集部署记录。

另对目标89项只读environment/Dockerfile指令：既有Ubuntu24.04，也有Python slim Bookworm及其他Debian基底，并非全都与合成任务共用一个Ubuntu镜像。任务自身依赖不同属于泛化范围，不能据发行版不同直接判轨迹无用。需要核的是命令/依赖可见性、工作目录、文件初始化和交互语义是否自洽。

**任务包默认预算和正式覆盖要分开。** 本次metadata中TB任务文件大多写1CPU/2G，这既不是本题32CPU/48GiB/3小时的替代方案，也不能证明原teacher实际用量。目标审计仅记录打包默认值并另列当前协议草案的覆盖；没有改变正式预算。[目标元数据快照](source_snapshots/harness/target_sandbox_metadata_20261016.json)

### D3：有成功验证依据；静态监督与交互sandbox适配分开

[D3论文Appendix E](https://arxiv.org/html/2604.27977v1#A5)明确写出环境内执行、silver判分和2,153条32B成功程序。它们不是没有验证过的随意代码；同时没有逐条公开执行回执，不能标为本项目已验证通过。

任务构建阶段的Conda执行器、论文teacher生成/筛选和后来发布的Docker镜像是不同阶段。现成程序可作静态SFT；若把任务改为OpenCode多轮采集，还需正确输入/输出映射、CLI依赖、非root可写性和评分资产隔离。D3镜像同时放置gold/eval，不能未经隔离直接给交互agent全部shell可见；ASI runtime.image分支也不会自动给任意D3镜像补齐OpenCode。

## Docker与HPC Apptainer的关系

固定Harbor本来就有Docker image→SIF的Singularity/Apptainer后端；更换容器运行器本身不要求重采已有SFT数据。离线SFT只消费已记录消息，不会在每个训练step重新启动sandbox。真正要验证的是目标运行器是否保留了镜像用户态、工作目录、可写文件和命令状态等语义。

但同一镜像不等于同一运行政策。固定后端使用writable-tmpfs/fakeroot/containall，仍共享宿主网络；没有直接用容器cgroup CPU/内存参数，另有进程内存watchdog并建议Slurm层管理资源。因此不能用“转换成SIF并能启动”证明SWE分阶段网络白名单或每任务资源配额已满足。当前项目后端还在另一工作流验收，本报告不更改其配置或承诺正式可用。[固定Harbor后端](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/singularity.py)

## 数据路线判断

目前证据更支持：SWE/Terminal先清洗可追溯轨迹，并利用配套任务元数据恢复少量独立环境，核初始化与目标政策；D3复用已有验证依据的静态程序，缺失科研多轮才真实补采。不能因sandbox细节未全部公开就全池重采，也不能因同属Linux/Docker就跳过环境验收。

如果源过程依赖目标禁止的网络/权限、输入初态不可恢复或动作状态语义不成立，则隔离这部分并在正确独立训练环境下补采。正式benchmark任务、镜像和评分流程保持题定范围；不把训练任务强行放入正式测试镜像，不用正式题答案生成示范。实际迁移收益仍由独立dev比较Base/SFT判定。
