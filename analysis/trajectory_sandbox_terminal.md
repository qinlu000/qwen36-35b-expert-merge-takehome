# Terminal-Corpus 原始 sandbox 与环境恢复核验

核验：2026-10-16。**已有 Ubuntu 24.04/Python 3.12 的任务环境定义和输入资产，可以优先复用 mixed 终端小池；但公开发布没有记录每条教师采集时的镜像 digest、实际 UID/权限、网络策略及资源覆盖。因此不能说“与我们当前 Apptainer sandbox 完全相同”，也不能仅因后端不同判定旧轨迹不能用于 SFT。**

本轮只读固定 README、作者论文、训练任务的 task.toml/Dockerfile 及公开环境实现；没有读取正式 benchmark 的题目/答案/tests，没有执行容器、轨迹、模型或 API，没有安装依赖。任务包中的 instruction、tests、solution 和输入文件正文均未读取；引用此前已完成的题面 hash 配对。纯环境元数据/路径/哈希快照：[terminal_sandbox_environment_20261016.json](source_snapshots/harness/terminal_sandbox_environment_20261016.json)。

## 1. 作者披露到哪一层

作者明确用 Terminus-2 在 Docker 容器内的持续 tmux 会话采集，任务环境采用按领域共享的预装依赖镜像，并允许 agent 安装运行时依赖；论文称共九类共享镜像。它说明容器与交互形态，**没有提供该次采集的 UID、capabilities、seccomp、挂载清单、网络规则、实际 CPU/RAM 覆盖或镜像 digest 清单**。本次没有找到由论文/固定数据卡链接、可确认就是原始 Terminal-Task-Gen 采集部署的公开代码，不能拿第三方同名库或后来的 NeMo Gym bridge 冒充原采集版本。[作者论文 §3.2、§4.2.3、附录 A.2](https://arxiv.org/html/2602.21193v1)、[固定任务卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/blob/7e53648e183cee7bcb0aed623cc91a121d37fa38/README.md)、[固定轨迹卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)。

轨迹 schema 为 conversations、agent/model/model_provider、date、task、episode、run_id、trial_name、enable_thinking。没有 environment/image_digest/uid/network/resource 字段；日期和 run_id 不能还原这些运行参数。固定卡 SHA256：任务卡 `9890af8f9185184fd7ecfd5147f713f054ffcc62e8131e3ba53fae91dbf7310b`，轨迹卡 `ab2e781e4dc4cf7db8931078b5dfa72f5e02629937775d518bf88ed5e6e153e7`。

## 2. 已下载六包的实际环境定义

任务版本 `7e53648e183cee7bcb0aed623cc91a121d37fa38`，80 根目录 `artifacts/tasks/raw/nemotron_tasks/<revision>/`；以下路径相对于其中 tar 解包根。实际读了 **5,984 份 task.toml** 和所有环境 Dockerfile，按配置/哈希聚合，没有启动构建。

六域全部顶层 Dockerfile 使用 `FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:latest`，安装 Python 3.12 并设为 python3，`WORKDIR /app`，`COPY files/ /app/`。apt/pip 包没有固定版本。每域顶层 Dockerfile 字节相同；debugging 内另有两个用户项目的嵌套 Dockerfile，不是两个额外 task sandbox。

| 域/压缩包 | task 数 | 顶层 Dockerfile SHA256 | 典型预装依赖 |
| --- | ---: | --- | --- |
| mixed/data_processing.tar.gz | 1,000 | `5597d8f070c767568039da7f99272dce121190e79694a2bc337d4eaee2c23f74` | jq、xmlstarlet、numpy/pandas/polars/pyarrow/orjson/lxml |
| mixed/data_science.tar.gz | 1,000 | `427c7013129e37c4af5770c1b7ec59440a31b1f005203a390089ecb82a94aae6` | numpy/pandas/scipy/sklearn、matplotlib、statsmodels、SQLAlchemy |
| mixed/debugging.tar.gz | 1,000 | `b8457c9afead706f505c99bc76d2f76d1018e40d91cd63bde70ac35e5397ba4d` | gdb、valgrind、strace、ltrace、pytest、ipython |
| mixed/file_operations.tar.gz | 997 | `4cb7cecb5267de4e7ad52225129d09ccc4c2c8fef9d4062f13b152d09150fc32` | 压缩工具、ImageMagick、ffmpeg、pillow/pypdf/python-docx |
| mixed/scientific_computing.tar.gz | 1,000 | `2d3a8dd21254d533537d1fbf8bf5a06c49429459505b6002c6bd11e1ca0ca6e0` | gfortran、cmake、BLAS/LAPACK、numpy/scipy/sympy/h5py/numba |
| mixed/security.tar.gz | 987 | `2eff5620543f5fe3d38155f39c7f1179fc5baf4a3cc0ee391d68b5db53c62424` | openssl、nmap、netcat、tcpdump、cryptography/pycryptodome/scapy |

表中归档全路径前缀均为 `skill_based/`。Dockerfile 成员路径形如 `./data_processing/data_processing_task_0459/environment/Dockerfile`。环境 Python 包清单是构建声明，尚未拉取实际镜像检查安装结果或版本。

全部 task.toml 的环境/超时配置同型，仅镜像域名后缀不同：

- `[environment] cpus=1, memory="2G", build_timeout_sec=600.0`。
- `[agent] timeout_sec=900.0`，`[verifier] timeout_sec=900.0`。
- `docker_image="gitlab-master.nvidia.com:5005/renjiep/datagen-flash-images/hb__datagen-flash-<域名连字符>:latest"`。
- 没有显式 USER、network_mode/allow_internet、端口/挂载/权限或依赖 lock。六包没有 container.def；少量环境输入项目附带 compose/setup 文件，不能当全池统一启动规则。

**这些是发布任务包的默认声明，不是已经证明的原教师实际运行资源。** 采集命令可能覆盖；没有原 run config 无法确认。它们也不是本题 TB 正式要求的 32 CPU/48GB/3 小时，正式评测需要按题定 override，训练池无需按每题 32 CPU 才能使用。当前 Harbor 能兼容解析旧 memory="2G" 为 memory_mb，但还要验证具体 runner 资源落实。

两个已配对示例的环境文件：

| 文件成员 | SHA256 |
| --- | --- |
| `./data_processing/data_processing_task_0459/task.toml` | `73ef6a91d80f9c9cd813d214994a65c7e3d3ea4ca6aeaffb6a80ff4a2c4d9972` |
| `./data_processing/data_processing_task_0459/environment/Dockerfile` | `5597d8f070c767568039da7f99272dce121190e79694a2bc337d4eaee2c23f74` |
| `./scientific_computing/scientific_computing_task_0939/task.toml` | `1d66ffaaed8d157ad595457a1d72db394377344b1fc0ca76720cd6b74777209b` |
| `./scientific_computing/scientific_computing_task_0939/environment/Dockerfile` | `2d3a8dd21254d533537d1fbf8bf5a06c49429459505b6002c6bd11e1ca0ca6e0` |

基础镜像公开源码在 Terminal-Bench repo `d28711d0da2675d0bb1d56de45ae5df6082438a3/docker/base-images/ubuntu-24-04/Dockerfile`：基于 ubuntu:24.04，安装 tmux/asciinema，WORKDIR /app，无 USER；文件 SHA256 `8665f6ab40b215e595b0b13021284091e7b653f4c73c0a083f381e0308e57a20`。这是本轮固定的源码快照，**不证明教师当时的 latest tag 就对应这些字节或同一系统包版本**。[基础镜像源码](https://github.com/laude-institute/terminal-bench/blob/d28711d0da2675d0bb1d56de45ae5df6082438a3/docker/base-images/ubuntu-24-04/Dockerfile)

## 3. 可恢复什么、不能从 ID 推出什么

当前 mixed 六包有题目、环境 Dockerfile、environment/files 和评分入口资产；对应六个 Corpus 分片共 **5,689 条记录**。此前按同 difficulty/同域核验的两个例子，wrapper 内 instruction hash 与任务包完全一致，可以把这些资产关联起来。它们的过程记录无完成 true，不能推断 grader 已通过。[前次兼容性与哈希证据](harness_compatibility_terminal.md)

easy/medium 与 mixed 会复用 task 名称但题面不同。只凭 `data_processing_task_0459` 之类的 ID，不能把 mixed 文件系统配给 easy/medium 轨迹。我们尚未下载其他 difficulty 的环境包；固定官方文件索引还提供 easy.tar.gz 110,525,687B、medium_shard1.tar.gz 704,025,716B、medium_shard2.tar.gz 188,396,953B，不能因为它们线上存在便称本地已可恢复。[固定任务文件索引](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/tree/7e53648e183cee7bcb0aed623cc91a121d37fa38/skill_based)

`environment/files` 能提供恢复输入的材料，但本轮未打开正文或核对教师执行时文件哈希；同题面不证明输入字节、随机状态或镜像状态相同。恢复环境时应采用 revision/config/difficulty/domain/task ID + 题面 hash，并保存实际输入 manifest、依赖和权限，而非仅 task ID。

## 4. NeMo Gym 公开路线是参考重建方式，不能充当原教师部署记录

本轮查阅固定 NeMo Gym `5ba257d4526b5d2a52ca47c9f5921e2d871abceb`。其 Harbor bridge 明确拿本数据的 mixed/scientific_computing 作示例，支持 Docker image→SIF、自定义 Singularity、task-local setup 和别名 workdir；requirements 固定 Harbor `9dddd797b57ab8a0f9d6352a20fce73abbb29573`，**与本项目已安装 f527f8e 不同**。没有证据它就是 Terminal-Corpus 最初采集代码。[bridge README](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/README.md)、[requirements](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/requirements.txt)

其源码使用 `--fakeroot --containall --pid --writable-tmpfs`，默认关闭 home/tmp/bind-paths 自动挂载，显式绑定 staging/日志；网络仍共享宿主，无断网能力。CPU 不由该后端加 cgroup 限制，资源依赖 Slurm；内存有 PSS watchdog。它们都是当前公开实现的行为，不能倒推教师记录具有同样权限/隔离。[固定 Singularity 源码](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/custom_envs/singularity/singularity.py)

**若我们采用这条共享 SIF 重建路线，有一个具体初始化风险需先处理：**

1. 官方 `build_and_push_images.py --shared-image-subfolder` 只用该域一个任务的 Dockerfile/context 构建镜像，随后给整域写同一个 image ref；而任务 Dockerfile 含 `COPY files/ /app/`，输入因任务而异。逐任务 build 可把每题自己的 files 烘入镜像；共享 build 则需要明确的逐任务输入恢复/清理步骤。[共享镜像脚本](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/custom_envs/singularity/scripts/build_and_push_images.py)
2. 当前 NeMo bootstrap 明确说 staged files **不自动复制到 /app**，应由 setup.sh 自行搬运；`write_min_setup_sh.py` 只安装 uvicorn/fastapi，没有实现任务输入复制。照搬“一个共享镜像+最小 setup”可能缺输入或残留源任务文件。不能据此指控原教师采集有缺输入 bug，因为没有它的 runtime 初始化实现。[bootstrap 源码](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/custom_envs/singularity/singularity.py#L270)、[最小 setup 脚本](https://github.com/NVIDIA-NeMo/Gym/blob/5ba257d4526b5d2a52ca47c9f5921e2d871abceb/responses_api_agents/harbor_agent/custom_envs/singularity/scripts/write_min_setup_sh.py)
3. 本项目固定 Harbor f527f8e 的 `should_upload_environment_dir` 在存在 Dockerfile 时不会走预置镜像自动上传环境路径；Singularity bootstrap 会执行 setup.sh，也没有统一把 files 树复制到 /app。故这个输入恢复问题同样需要在我们的 runner 接线时明确解决，不能期待 framework 自动补齐。[固定环境定义逻辑](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/definition.py)、[固定 bootstrap](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/singularity/bootstrap.sh)

## 5. Docker→Apptainer 的实际判断

复用相同 OCI rootfs/依赖和恢复相同输入，可以减少环境偏差，但不保证可观察行为相同：UID/GID、可写 overlay、宿主挂载、进程与网络 namespace、设备/capabilities、资源限制都由启动方式决定。Apptainer 的 fakeroot 有多种模式；root-mapped 无完整 subuid 映射的权限行为，与完整 rootless 模式不同，不能看到容器内 UID 0 就认为等同 Docker root。[Apptainer 官方 fakeroot 说明](https://apptainer.org/docs/user/main/fakeroot.html)

我们对旧轨迹做离线 SFT，不需要为了加载训练文件启动原容器，也不要求先全量重放；但若要把某任务放入独立 dev 或补采，必须恢复可验证的输入/依赖/工作目录及所需权限。网络服务、抓包、sudo/chown、多用户、嵌套 Docker、性能门槛等任务，对后端差异更敏感，应单独核。**目标 TB89 自身也不是全部 Ubuntu24.04**；训练任务不需要逐个拥有和目标题相同的镜像，目标各任务仍须保留各自官方环境与题定资源。

## 6. 确定的首批优先级与剩余缺口

首批优先取 **mixed/data_processing**：已有 957 条 Corpus 记录和 1,000 个环境包，前次 10/10 样本题面对齐，日志0459还做了精确 hash 配对；优先筛离线文件处理、不依赖网络/多用户/嵌套容器/性能阈值的任务。随后是 mixed/data_science 的 944 条记录。科学计算仍应保留独立份额，但从纯数值/文件工件、依赖可恢复的题开始，不自动采用 N 体的并行性能要求。首批数量是候选来源规模，**不是合格成功示范数**。

接下来小池的必要动作：固定可取得的基础/rootfs digest 或明确记录重建差异；逐题恢复 environment/files 到正确初态并核 manifest；检查实际 UID、cwd、依赖及所需网络/文件操作能力；再做少量独立环境与评分验收。若无法取得原私有 latest 镜像，可从公开 Dockerfile 重建并锁住本次环境，公开其版本差异，不称原 sandbox 精确复现。旧过程可继续作为候选 SFT 数据，不能因为缺 digest 就一律丢弃；dev/补采则需要运行验证。

尚无证据的部分集中保留：原教师 image digest与系统/包版本、实际启动/初始化命令、资源 override、UID/capabilities/网络/挂载、执行前输入 hash和后续 agent 安装状态；其不确定性不会被“同 harness”“同 Dockerfile”“同镜像名称”消除。
