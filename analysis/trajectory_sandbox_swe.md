# Open-SWE mini 轨迹的 sandbox：公开信息与恢复路径

调研日期：2026-10-16。**上游任务数据确实公开了镜像、初始 checkout 和环境安装线索；源轨迹本身缺少环境列，不代表环境无从恢复。**但本次固定的 NVIDIA mini/Qwen3.6 轨迹没有附完整 collector runtime/config，不能把上游当前默认值或旧论文的其他 harness 设置归因于这一子集。

本轮只读官方说明、通用构建/适配源码和元数据；未拉/构建/启动镜像，未执行任务、轨迹命令、模型或付费 API，未读取 gold/hidden tests 值。远程 Parquet 仅尝试投影环境元数据，因延迟较长已停止；没有下载整个任务池，也没有完成上游逐题联表。

## 版本与一手来源

| 来源 | 固定 revision / 检查对象 | 用途 |
|---|---|---|
| NVIDIA Open-SWE-Traces | `1db674173119d71df45c22007af99e214600711a`，只研究已下载 v1.1 `data/minisweagent/qwen36_27b/{scale-swe,swe-rebench-v2}` | 训练轨迹实际发布资产 |
| AweAI-Team/Scale-SWE | HF `d8db20390a936bbda9c96d88b97cc4778dff1481` | 上游任务字段与复原入口 |
| nebius/SWE-rebench-V2 | HF `10483de0f50fe5da545942705a76c6150171af7f` | 上游任务环境 schema |
| SWE-rebench/SWE-rebench-V2 | GitHub `c71902a8cf8d2b725f63d51f199f4d3e56f68d2d` | 官方镜像生成模板与基础 Dockerfiles |
| AweAI-Team/AweAgent | GitHub `b38414e5dc9c7c51f2ec48318b718af0c8852060` | 上游当前任务适配与 Docker 运行参考；不是 NVIDIA 原采集器 |

后四项是本轮调研固定的公开快照，**不是 NVIDIA 已声明的采集依赖版本，也没有替换本项目已锁来源版本。**

## 轨迹发布了什么，缺什么

固定 Open-SWE 数据卡将任务及仓库环境指向 Scale-SWE、SWE-rebench-V2。完整仓库 tree 共 330 条目；除目录和 Parquet，仅有 README、data_distribution 与 Git 属性文件，没有 mini collector 源码、配置或 Dockerfile。data_distribution 明确列出 v1.1 mini/Qwen3.6 的 95,291 条轨迹、39,540 个不同 instance_id，**但没有给它们的 CPU/RAM、网络、超时或镜像 digest**。[固定数据卡](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[固定分布说明](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)、[固定仓库 tree](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/tree/1db674173119d71df45c22007af99e214600711a)

实际 Parquet 的环境关联列是 `hf_dataset_name`、`instance_id`、`repo`，另有 trajectory_id 和 language；未发布独立 image/base_commit/cwd/runtime/资源列。metadata 的实际 struct 主要是分类、teacher 设置和补丁信息，本轮不读取补丁值。源文件本地在80 `artifacts/data/raw/open_swe/1db674173119d71df45c22007af99e214600711a/`。

这次读取到的ID例子包括 Scale-SWE 的 `jazzband_dj-database-url_pr257`、`kjd_idna_pr111`、`mapbox_mercantile_pr65`，以及 SWE-rebench 的 `sharksforarms__deku-99`、`pallets__click-2417`、`mpmath__mpmath-922`；这里只核源记录的关联键，未把它们视为已通过独立性筛选的训练/dev任务，也未证明已匹配上游环境行。

另外，[论文 2606.16038](https://arxiv.org/abs/2606.16038) 本轮可查版本只有 v1，摘要对应 OpenHands/SWE-agent、MiniMax/Qwen3.5 的旧发布；不是后来 mini/Qwen3.6 的运行配置依据。未从已查官方入口定位到该 mini 子集的独立采集代码，**不等于断言全网绝不存在**。

## 已确认 / 未公开 / 需要恢复验证

| 项目 | 已确认的公开信息 | 对固定 NVIDIA mini 仍未公开或未核到 | 恢复时需要验证 |
|---|---|---|---|
| 任务与轨迹关联 | 本地两源首片各读3条，均有正确 hf_dataset_name 与 instance_id，能指向相应任务来源 | 源采集时上游 dataset revision 未声明；尚未实际完成逐题 join | 固定上游快照后查 ID、repo/commit 一致性；不能用同名 repo 代替同一任务 |
| 镜像 | Scale-SWE 公开 image_url；SWE-rebench 公开 image_name、install_config 的基础镜像/工具链配置 | collector 是否另打包、更换或改挂载；原镜像 digest | 镜像可取、架构、digest、文件系统和初始 git 状态 |
| 初始 checkout | Scale-SWE 有 parent_commit 与必须执行的 pre_commands；SWE-rebench 有 base_commit | 源采集时是否额外 reset/clean/预热/拷贝文件 | 运行前 HEAD 正确且无泄漏；安装造成的残留单独记录 |
| OS/工具链/用户 | SWE-rebench 官方模板指定 linux/amd64；Python示例基于 python:3.11-slim，Rust示例基于 rust:1.83。基础镜像创建 nonroot，但示例未启用 USER，通常继承基础镜像 root | 每个实际任务的基础镜像版本与实际执行 UID；不能由两个示例外推全部 | image config、UID/GID、依赖版本和文件权限 |
| cwd | Scale-SWE 有 workdir；SWE-rebench 模板把工作区设为 /<repo_name> | NVIDIA 是否重定位/链接到 /testbed；另读两源各3条源初始提示均提及 /testbed | 原镜像工作区与 collector 提示、硬编码路径的关系 |
| shell 状态 | 已有624条审计提示明确每个动作新 subshell，目录/变量不持久，文件改动持久；工具为 bash(command) | 实际 collector 环境类、shell启动规则、额外环境变量、后台进程策略 | 在正确任务环境验证状态与观察；不能换成持续 tmux 后只改字段 |
| 图文输入 | 固定来源card标为Text，已查624条的消息content为字符串、工具为bash | 没有看到该子集发布图像工具/附件协议 | 不以此类轨迹替代需要图片输入的其他benchmark任务 |
| 网络 | 上游当前 AweAgent Docker runtime 可配置 network，默认 bridge | NVIDIA mini 采集时是否禁网、允许哪些站点，setup/agent/grader是否分阶段 | 目标禁止网络时，筛出需要联网安装/下载/查询的轨迹，不能伪造离线成功 |
| CPU/RAM/时间 | 当前 AweAgent Scale-SWE 示例是4 CPU/8Gi、session14400s、bash1200s、eval3600s | **这些不是 NVIDIA mini 源采集配置**；其采集CPU/RAM/任务或命令超时仍未知 | 在目标资源政策下测试必要命令是否超时/OOM；重资源轨迹不能靠模板转换解决 |
| 测试/评分 | 两任务card公开验证器所需字段与安装/测试配置入口；本轮只确认schema/通用源码，不读测试内容 | 原轨迹实际测试执行条件与评分版本是否一致 | grader与policy材料分离，恢复后验证任务确能独立判分；不能向policy拼gold或hidden测试 |
| 提交 | 源提示包含patch.txt提交指导；目标LockedMiniSwe另捕获工作区diff做fresh replay | collector对补丁、退出与异常的全部规则 | 保留源上下文作迁移，不盲换提示；独立训练任务补目标提交闭环 |

## 上游环境为何可复用

**Scale-SWE：**官方数据卡提供 image_url、workdir、parent_commit、pre_commands 等任务环境字段；当前 AweAgent 的 `scale_swe/task.py` 明确将它们映射为镜像、工作区、base_commit 和 setup commands，并提示 pre_commands 已包含正确 checkout，不应再猜一个 base 或省掉初始化。这提供可落地的环境恢复入口；不需要用 SWE-smith 的另一套仓库任务来冒充 Open-SWE 同源环境。[固定任务卡](https://huggingface.co/datasets/AweAI-Team/Scale-SWE/blob/d8db20390a936bbda9c96d88b97cc4778dff1481/README.md)、[当前官方任务适配](https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/tasks/scale_swe/task.py#L90)

**SWE-rebench-V2：**官方任务card的 install_config schema有基础镜像、工具链、安装步骤、测试命令等。公开组合 Dockerfile 从语言基础镜像开始，将仓库克隆到项目目录、reset到任务 base_commit、移除远端，再执行安装步骤并设置 WORKDIR。模板对安装命令容忍失败，因此存在模板并不保证任一任务的环境已正确构建；需要恢复后实查。Python基础示例的Debian工具链与root状态只能代表该模板，不能冒充全部任务或 NVIDIA 采样环境。[固定任务卡](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)、[组合模板](https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/combine.Dockerfile.j2)、[Python基础模板](https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/base_dockerfiles/Dockerfile_python_3.11)

需要注意公开构建代码的 `install_config.image_name` 与当前任务card schema 的 base_image_name 命名并不完全一样，不能假设当前模板无需适配即可直接重建全部发布镜像。优先使用任务明确给出的发布 image_name，并记录实际 digest，再决定是否重建。

当前 AweAgent 的 bridge 网络、资源配置和逐命令 bash 执行只是证明“上游存在可配置运行器”，没有证据 NVIDIA mini 用了同一运行器或默认值。[运行器配置](https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/core/runtime/config.py)、[Scale-SWE示例](https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/configs/tasks/scale_swe.yaml)、[Docker创建与执行](https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/core/runtime/docker.py#L167)

## 对清洗与重采的影响

1. 先按 hf_dataset_name + instance_id 查回**同一训练任务**的发布镜像、base、cwd、初始化及依赖，排除正式benchmark同源；不要拿任意同仓库版本或 SWE-smith 镜像替代。
2. 选择少量依赖清楚、镜像可获取的独立训练任务，恢复正确初态；在目标工具、网络及资源政策下做闭环检查。任务内容不同正常，真正要排查的是交互契约与权限差异。
3. 格式差异、可确定的单调用ID缺失继续机械清洗；依赖联网、错误工作区、初态不明、重资源/超时差异先隔离，必要时在正确环境补采；不要为清洗好看而改写真实观察。
4. 环境复用有公开路径，因此不应先决定从零重采全库；但“能找到镜像”也不等于源collector政策完全复原或SFT有收益，最后仍用独立dev比较Base/SFT。

本轮没有新增训练样本、正式评测或环境配置，也没有完成六例上游逐题联表/镜像可用性验证。
