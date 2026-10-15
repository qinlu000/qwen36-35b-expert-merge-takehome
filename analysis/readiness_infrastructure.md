# 评测基础设施只读核验

核验时间：2026-10-15 21:12–21:18（北京时间）。仅 SSH、调度信息查询、容器元数据检查、已知主机连通性检查；未安装软件、拉取镜像、提交 Slurm 作业、占用本题 GPU、运行容器/benchmark 或修改 SSH 配置。现有本人作业未被调整。

## 结论

80 可继续作为开发/数据处理节点，HPC 可作为四 H100 的训练和推理节点；**正式评测运行链路尚未具备**。当前主要阻断是容器后端、可用于 CPU 沙箱的配额，以及 80 与计算节点之间的模型服务通路。发现两份 HPC 现成 SIF，可作为兼容性检查起点，不能据文件存在认定已支持本模型或官方评测。

## 1. 已核实的资源

| 位置 | 已核实 | 限制与边界 |
|---|---|---|
| 80 `10.123.4.80` | Linux x86_64，2×Xeon Gold 6530，64 物理核/128 逻辑 CPU，2.0 TiB RAM（约1.9TiB available），`/data`约3.0TiB空闲 | 共享整机可见资源，不等于本项目独占配额；核验负载约17，已有其他用户 |
| HPC 计算节点 | Slurm 每节点96 CPU（ThreadsPerCore=1）、RealMemory=2,000,000 MiB、8 GPU | GRES只写`gpu:8`，没有按型号细分；当前空闲数不保证调度时间 |
| 已有本人作业所在节点 ACD1-13 | 经登录节点 SSH 只读查询可见 GPU：`NVIDIA H100 80GB HBM3`，81559 MiB，driver 610.43.02 | 只验证该节点可见 GPU；本题未来四卡的具体节点、互联及可用显存需实际分配后核实；未进入已有作业运行环境、未启动计算 |
| HPC 存储 | `/data/user/qinlucao`位于大型共享`/data`文件系统，系统剩余约12PiB | 系统剩余不等于个人 quota；本轮未核到个人容量限额 |

Slurm 查询结果：

- `acd_u`默认分区、`acd_ue`、`emergency_acd`均UP，最长`7-00:00:00`；普通formal用户组在AllowGroups内，AllowAccounts/AllowQos为ALL。分区名可见不构成使用高优先分区的独立授权，优先延续账户既有合法配置。
- `debug`最长30分钟，`debug_qos`每用户上限`cpu=12,gres/gpu=1,mem=240G,node=1`；不能拿它做单路要求32CPU的正式TB任务。
- `SelectType=select/cons_tres`、`SelectTypeParameters=CR_CORE_MEMORY`、`TaskPlugin=task/cgroup,task/affinity`、`OverSubscribe=NO`。
- 正常分区`DefMemPerCPU=10240`MiB；仍应显式请求内存。分区最大时长不是当前作业时长或保证等待时间。
- `JobSubmitPlugins=lua`；**未验证CPU-only作业是否获准、是否另有CPU/GPU比例规则**。不能因CPU有空闲便声称可以分配。

### 账户与 QoS 硬限额

`sacctmgr -n -P show assoc where user=$USER ...`返回：

| account | 授权QoS | 已核到每用户QoS上限 |
|---|---|---|
| `qinlucao` | `formal-user` | `MaxTRESPU=cpu=192,gres/gpu=16,mem=3840G`；最多20运行作业/50提交作业 |
| `d_liuh_team` | `normal` | 同上：`cpu=192,gres/gpu=16,mem=3840G`；最多20运行作业/50提交作业 |

当前本人作业`722434`使用account=`qinlucao`、QoS=`formal-user`，1节点、12CPU、1GPU，时间限额2天。**不更改、不复用此作业。** 本题四卡是用户额外授权；QoS的16GPU上限不是本题可以用16卡。

在仅使用当前`formal-user`、既有12CPU作业不变的假设下，理论还能分配至多180CPU，且本题四卡训练/推理作业也要从其中扣除CPU。这是账户上界，不是已获CPU分配。两条association不能未经明确资源安排就相加当作项目保证配额；团队account是否用于本题列入待讨论。

## 2. 容器运行条件

### 80

- PATH与用户常见`bin/tools/software/apps`目录没有找到Docker/Podman/Apptainer/Singularity/Enroot/nerdctl，以及dockerd/rootlesskit/runc/crun。
- 未发现`/var/run/docker.sock`、`/run/user/1012/docker.sock`、`/run/user/1012/podman/podman.sock`。
- 已有`/usr/bin/unshare`、`/usr/bin/bwrap`；`kernel.unprivileged_userns_clone=1`、`user.max_user_namespaces=8255326`。
- `/etc/subuid`和`/etc/subgid`均给caoqinlu分配`886432:65536`；但未找到newuidmap/newgidmap/fuse-overlayfs/slirp4netns/pasta。
- `/sys/fs/cgroup`为cgroup2fs。这些信息说明有部分rootless基础条件，**不能据此认定rootless Docker或官方评测沙箱已经可用**。

### HPC

- `/bin/singularity`：Singularity-CE `4.1.5-1.el8`；PATH未发现Docker/Podman。
- `/etc/singularity/singularity.conf`：allow setuid=yes、allow pid ns=yes、enable overlay=try、enable underlay=yes、systemd cgroups=yes。user.max_user_namespaces=2052751。
- 已有可读SIF：
  - `/data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif`，约18GiB；label显示`lmsysorg/sglang:v0.5.15.post1-cu129`、cuDNN9.10.2.21、2026-09-07构建；镜像旁有.sha256文件。
  - `/data/user/qinlucao/software/containers/hpc-benchmarks_24.09.sif`，约5.1GiB；来自`nvcr.io/nvidia/hpc-benchmarks:24.09`，这是NVIDIA HPC性能测试镜像，不能因文件名含benchmarks就当作本题四项评测环境。
- 仅读取labels，未运行镜像，未验证ms-swift/PEFT/Transformers版本或Qwen3.6支持。Singularity也不能自动替代Harbor或SWE runner期望的Docker API/Compose与任务隔离语义。

## 3. SSH与模型服务路径

| 链路 | 本轮结果 |
|---|---|
| Mac → 80 | BatchMode SSH成功；账号caoqinlu |
| Mac → hpc3 | BatchMode SSH成功；解析为`hpc3login.hpc.hkust-gz.edu.cn`，账号qinlucao |
| HPC登录 → 已有本人分配节点ACD1-13 | BatchMode、严格host key校验SSH成功；用于hostname与GPU只读查询 |
| 80 → HPC登录IP`10.120.81.30:22` | 网络可达；以已有且与Mac一致的域名host key校验后，返回`Permission denied(publickey,password)`，即当前直接鉴权未打通 |
| 80 → 已知计算节点`10.120.48.102:22` | 一次6秒TCP/SSH banner检查未完成；不能据此认定所有节点都不可达，也不能按直连可用设计 |
| HPC登录 → 80 | SSH可到达但本地known_hosts没有80记录，严格校验阻止连接；未绕过校验，鉴权未核实 |

Mac两个Host的`ForwardAgent=no`；未复制私钥或启用agent forwarding。80已有127.0.0.1:38080代理监听；该链路的长期可用性和是否依赖Mac现有会话仍须保证，不能等同于离线批作业稳定联网。

**暂定架构**：80开发与数据清洗；Mac用既有双端SSH同步冻结Git版本/必要文件；HPC分配内训练/推理。若CPU评测留在80，模型端点可以规划为“计算节点 → HPC登录可达端口 → Mac本地转发 → 80反向转发”；后续本轮已以SSH banner验证临时TCP桥接，详见第6节，模型服务仍未验证。

以后在模型服务绑定于分配节点可达端口的条件下，Mac可采用以下两跳转发示意；它们本轮没有执行，端口也没有被占用：

```bash
# NODE替换为本题真实分配节点，8000为真实模型服务端口。
ssh -N -L 18000:NODE:8000 hpc3
ssh -N -R 18000:127.0.0.1:18000 10.123.4.80
# 80上的评测客户端再访问 http://127.0.0.1:18000/v1
```

第一跳要求HPC登录可访问计算节点服务端口；后续已验证22端口SSH banner桥接，不假定模型服务端口可达。该方案依赖Mac与双SSH会话持续在线，适合快速兼容验证，长时正式评测仍应优先让CPU沙箱和推理位于互通的HPC/获批评测主机上。

## 4. CPU并发与排期含义（后续纠正）

TB每路题定32CPU/48GB RAM。固定Harbor Docker默认将资源作为limit，不自动独占32核。**此前称最多4/5/9路过于绝对，除法只适用于各环境同时用满CPU的容量情景。**

- 80可见128逻辑CPU，可供4路同时满额32CPU；共享宿主需余量，64物理核的SMT不能视作吞吐翻倍。
- HPC单节点96可调度CPU可供3路满额，是否获分配另计。
- formal-user已有12CPU不变时，额外180CPU可供5路满额TB，尚未扣本题训练/推理；扣32CPU后为4路。Slurm实际allocation/父cgroup仍限制总用量。
- 合计约9路满额不是软件最大并发。等待模型/API较多时，保留每容器32CPU/48GB上限可能支持更多环境；需实测CPU/RSS/I/O/模型队列并固定公平资源政策，不能保证无拥塞。

1335次若平均30分钟，共667.5 trial-hours；4路166.9h、9路74.2h是条件算例。36h至少约19个有效并发槽位；608CPU/912GB只是19路同时用满题定资源的容量，不是必须硬下界。目前均值、有效并发和后端均未落实，排期未证实；也不能用9路直接否定可行性或减五次/抽题冒充全量。见[单任务资源与提速](task_resource_budget.md)。

## 5. 待讨论/后续验证清单

1. **优先级P0，资源决定**：本题可使用的CPU-only总配额/其他组内评测主机，以及d_liuh_team account是否可用于本题；正式TB是否有足够并发。
2. **优先级P0，后端决定**：80已有管理员/组内可用Docker服务，还是允许在独立目录部署rootless引擎；HPC是否支持符合官方语义的任务容器后端。不要把Singularity存在当作已解决。
3. **优先级P0，短CPU分配后验证**：CPU-only作业提交政策、容器启动/写层/网络/资源限制、runner环境启动。此核验不需要占本题GPU，也不需要正式评测题。
4. **优先级P0，网络验证**：获批计算节点模型服务端口与CPU评测节点互通；若用Mac双隧道，需进程与断线恢复方案。无需把HPC密钥复制到80。
5. **优先级P1，四卡分配后验证**：实际四H100型号/显存/拓扑、Qwen3.6加载、8K训练与256K评测服务的内存和吞吐、图文请求。现成SGLang镜像只能作为候选。
6. **优先级P1，存储核验**：HPC个人quota、模型与容器缓存目录、80至HPC文件同步速度。共享存储系统空闲不等于个人配额。

除第6节随后完成并清理的临时TCP桥接外，其余后续运行验证尚未启动；没有恢复暂停的数据下载或修改用户现有任务。


## 6. 后续实际临时双隧道验证：通过并已清理

在不复制凭据、不运行模型、不在计算节点启动新进程的前提下，实际验证以下TCP路径：

`80:127.0.0.1:45182 → Mac:127.0.0.1:45181 → hpc3登录 → ACD1-13:22`

- 先通过`squeue`确认已知本人作业722434仍分配于ACD1-13；没有修改或进入作业任务。
- Mac45181和80的45182均先以socket bind确认空闲并立即释放。
- 创建两条仅127.0.0.1监听的临时SSH隧道，显式`BatchMode=yes`、`StrictHostKeyChecking=yes`、`ExitOnForwardFailure=yes`、`ControlMaster=no`、`ControlPath=none`。
- 第一条Mac→hpc3本地转发PID **721**；第二条Mac→80远程转发PID **725**。均是本轮`Popen`直接返回并精确保存的PID。
- 从80通过该路径收到 **`SSH-2.0-OpenSSH_10.5`**，探针returncode=0，两隧道当时均存活；没有对计算节点执行命令。
- 在`finally`中仅终止并wait自己的725、721；二者退出码均0、无stderr。清理后重新bind证实Mac45181与80的45182均已释放。未留下后台隧道、未改SSH配置或known_hosts。

**这解决了“80无法直接连接计算节点时，能否借Mac双SSH进行TCP桥接”的连通性问题。** 仅验证22端口的短连接；不代表模型服务已启动、任意模型端口可达、HTTP/流式响应/图文请求通过、长期稳定性或吞吐满足正式评测。

以后复用的模型端点转发示意（变量需先按本题实际分配和服务填入；此处未启动任何模型或正式转发）：

```bash
# NODE：本题分配节点；MODEL_PORT：真实模型服务端口。
# LOCAL_PORT：Mac空闲端口；LAB_PORT：80空闲端口。
ssh -N -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ExitOnForwardFailure=yes -o ControlMaster=no -o ControlPath=none \
  -L "127.0.0.1:${LOCAL_PORT}:${NODE}:${MODEL_PORT}" hpc3
ssh -N -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ExitOnForwardFailure=yes -o ControlMaster=no -o ControlPath=none \
  -R "127.0.0.1:${LAB_PORT}:127.0.0.1:${LOCAL_PORT}" 10.123.4.80
# 80客户端使用 http://127.0.0.1:${LAB_PORT}/v1；先验证实际health再运行任务。
```

模型服务必须绑定为HPC登录可达的地址；本轮没有改变任何计算节点防火墙/监听或SSH安全规则。正式长时评测仍需核查断线处理、流式超时及Mac持续在线安排。
