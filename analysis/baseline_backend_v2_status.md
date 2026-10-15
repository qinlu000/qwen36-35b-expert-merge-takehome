# SWE / Terminal v2 Linux backend

2026-10-16。该后端服务于本项目的 80 主机，不改变固定 Harbor 0.24.0、任务镜像、Agent prompt/parser/工具或 verifier。正式运行状态由各 benchmark 的 runner 另记；本文的测试均为自造任务，没有读取正式 instruction/tests/solution，没有模型或付费 API 请求。

## 实现

- `scripts/baseline_singularity.py:BaselineSingularityEnvironment` 使用固定 Harbor 的 bootstrap/server 和既有 SIF；不修改已安装 Harbor。启动、传输、停止仍走原 server HTTP 协议，控制面使用宿主私有 Unix socket，不将宿主网络暴露给 sandbox。
- `scripts/baseline_netns.py` 为每个环境创建独立 user/net namespace，以项目目录内解包的 slirp4netns 1.0.1 / libslirp 4.6.1 提供公开网络。public 阶段拒绝 RFC1918、链路本地、CGNAT 目标，私网目的地址只有 slirp DNS 端口例外；solver 阶段 IPv4/IPv6 均只保留本 namespace loopback，随后可恢复 public。没有修改或暴露用户的 38080 代理。可用 `bash scripts/setup_baseline_backend.sh` 在 Ubuntu22 主机复现项目内工具安装；两个 deb 均固定版本与 SHA256，不需 sudo。
- 模型桥可选：`baseline_model_socket` 接收宿主 `FixedModelRelay` 的 Unix socket，sandbox 仅见 `http://127.0.0.1:18000/v1` 和随机 agent token。真实服务 key 只在宿主 controller，外部 URL、CONNECT、错误模型/路径和远程 image/video URL 被拒绝。TB controller 在宿主调用模型，因此默认不开放 sandbox 模型桥。`baseline_model_host_port` 仅用于本文自造假服务 fixture。
- 任务 payload 显式丢弃 `CAP_NET_ADMIN/CAP_NET_RAW/CAP_SYS_ADMIN`。不能靠自身 root 或新建子 user namespace重置父 net namespace 的 firewall；不能用 AF_PACKET 绕过 IPv4 OUTPUT 规则。单独再套一层 `unshare -Ur` 会触发 Apptainer 对 root subuid 的错误路径，已放弃该实现。
- `scripts/baseline_exec_limits.py` 复用 ASI 的 affinity/BPF 和 cgroup 校验，先限制 allowed CPU 集合，再加载可继承 seccomp，`sched_setaffinity` 返回 EPERM；随后启动整个 Apptainer 进程树。每个环境独立 systemd user scope，实际 `memory.max` 必须等于配置字节数，`memory.swap.max` 必须为 0。不把 systemd 静默忽略的 CPUQuota/AllowedCPUs 当作真实能力。
- `baseline_cpu_offset` 指定可用 CPU 排序中的起点；`baseline_cpu_slots` 为同 controller 进程内的最小 slot 池。环境从 start 到 stop 占一个槽，失败也归还。TB 配置 offset32/slots8/4CPU，SWE offset64/slots8/1CPU，可避开 ASI 的前32核。仅声明 hard limit，不声称 CPU/RAM 资源预约。
- 禁用自动 home/cwd/hostfs/sys 挂载，清理宿主环境变量；只挂载 staging、声明的日志、task environment/files 和只读 bootstrap hook。真实 key、宿主 user bus、项目目录与可写 cgroup 不进入任务。评分文件由原生 Harbor 在 verifier 阶段处理，不能为了方便把宿主仓库或 reference/gold 挂入 solver。

## 超时与正常完成

进入 no-network 时记录环境内 `(PID,starttime)` 基线。`await env.terminate_solver_processes(reason)` 用于 timeout/error：取消上游 HTTP 后，杀死相对基线新增的进程，含 detached/setsid/tmux 后代，保留既有服务、Harbor server 与已落盘产物；返回 PID/signal/remaining/confirmed receipt。若未确认清理，backend 拒绝恢复 public。

正常原生完成不调用该 kill hook；保留任务要求启动的 web/db 等服务供官方 verifier 检查，controller 停止继续调用模型。这一区分已由 root 确认，不能将所有 no-network→public 切换误判为超时。

## 已完成验收

80 上的 receipt 均位于 `/data/caoqinlu/projects/apex-takehome/artifacts/preflight/backend_v2/`。

1. `network_probe.json`：真实 GitHub IPv4 TCP443 在 public 成功，OUTPUT DROP 后超时，恢复后成功；嵌套 user namespace 的 iptables 变更返回权限错误。最初使用不可达的 1.1.1.1 目标失败，不把该失败归为 slirp 故障。
2. `smoke-5jj3yoro/result.json`：4CPU/8192MiB 自造 Harbor 环境全链通过，启动33.42秒、测试总34.56秒；父子4CPU，扩宽 EPERM，实际 memory.max=8589934592/swap0，宿主 project/bus/cgroup 不可见，public HTTPS200→solver DNS失败而固定模型桥通→public HTTPS200，NETLINK 管理请求返回 EPERM，tmux 跨正常 phase 切换保持，stop 后 scope inactive。
3. `memory_hard_limit_probe.json`：独立64MiB/swap0 scope 内子进程申请128MiB，内核 SIGKILL(-9)，memory.events `oom=1/oom_kill=1`，不是依赖 Python 内存采样 watchdog。
4. `fixed_relay_hooks.json`：默认兼容200、validator 拒绝400/接受200、过期 deadline408，只有2次允许的上游调用。原 OpenCode fixture `artifacts/preflight/asi/bwrap-candidate-8_5cx2de/summary.json` 的7次合成模型调用、路径/模型/URL/认证拒绝、8秒超时及子孙清理全部回归通过；这只是共享 relay 兼容性，不改变 ASI 当前 direct_llm 选型。

## 最后执行验收

完整4CPU8GiB与1CPU4GiB已通过，分别为 `smoke-ypuo4cn1/result.json` 和 `smoke-o4k34qz1/result.json`，启动66.56/75.09秒。走原生 `set_network_policy`、固定 CPU offset32/64、直接 IP 拒绝、AF_PACKET 拒绝、detached solver 清理与 server 存活均通过。超时 fixture 分别终止新生 PID447/446，`remaining_pids=[]` 且 `confirmed=true`，随后 server 仍可执行 cleanup-only 命令。两个 scope 最终均 inactive。

同 controller 的两个4CPU slot（offset72/slots2）额外并行验收 **2/2通过**：`smoke-edgirsh0` 得到[76,77,78,79]，`smoke-4s2qlo62` 得到[72,73,74,75]，互不重叠；启动68.14/84.21秒，全部网络/资源/超时清理检查通过，两个 scope 最终 inactive。该探针避开各正式 runner 已分配的0–71核。receipt 为 `parallel_slots_summary.json`。

Terminus/SWE runner 已收到可冻结后端并接线的通知。该 backend fixture 不等于正式 benchmark、全部镜像或8环境实测吞吐；原生 Agent 链和正式启动由各 runner 记录。受控回执与全部源码 SHA 见 [backend snapshot](source_snapshots/baseline_backend_v2_20261016.json)。

生产四个 helper 已向 root、Terminus 与 SWE runner 宣告冻结，后续不再原地修改：

| 文件 | SHA256 |
|---|---|
| baseline_singularity.py | `4c01b92729d94cb4ea700edd2dc79dc857ec378374459930aba00e53907b6532` |
| baseline_netns.py | `09303db588a5b15f95116a679140af7eb4ad0b7dfb24d52d033c1d81e3990a23` |
| baseline_exec_limits.py | `540f46a4b2b2b0d5a417f4b7ff99c309c6d2417c3e463f44b7df2af17d605757` |
| asi_fixed_relay.py | `984d39b13799df2b7511cad0eefeb6e28630607171936f3e58b56349ddfcdf2f` |

源码与80副本 SHA 全部一致。HPC直接环境后端尚未验收；HPC GPU服务通过固定宿主模型relay接入，不声称HPC提供相同user-systemd隔离。
