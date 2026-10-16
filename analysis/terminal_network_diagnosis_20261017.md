# Terminal sandbox 网络诊断 — 2026-10-17

已证明的最小原因：**当前选定协议的 agent `no-network` 正常执行，足以产生工具中的 DNS 错误。** 本次没有发现当前 resolver、代理或 public 网络入口失效。普通分区只迁移 HPC 模型服务，不改变80上的 sandbox 网络策略，续跑仍会出现同类下载失败。

## 真实红绿反馈

按 [diagnosing-bugs skill](/Users/caoqinlu/.codex/skills/diagnosing-bugs/SKILL.md)，先做 frozen `NetworkNamespace.set_public` 的规则构造检查，再使用真实同入口 rootfs 做最小差分。实际探针运行于 **2026-10-17 04:11:07–04:11:15 +08**：同一 `bn-fit-modify` 缓存 SIF、AVG frozen `TerminalRepairEnvironment`，独立 CPU11、8GiB；不启动 Trial/agent/setup/test/verifier/model，只对两个域做 DNS/HTTPS HEAD，每域最多5秒。没有改全局网络、镜像或生产 scope。

| 位置/阶段 | pypi.org | archive.ubuntu.com |
|---|---|---|
| host | DNS成功，HTTPS200 | DNS成功，HTTPS200 |
| sandbox public_before | DNS成功，HTTPS200 | DNS成功，HTTPS200 |
| 同 sandbox solver_no_network | `[Errno -3] Temporary failure in name resolution` | 同左 |
| 同 sandbox public_after | DNS成功，HTTPS200 | DNS成功，HTTPS200 |

三次 sandbox 阶段的 `/etc/resolv.conf` 都是 `nameserver 10.0.2.3`，代理变量均为空。只切网络 policy 就产生/消除与轨迹完全相同的错误；无需改 DNS 文件、代理或重建镜像。自己的 `apex-baseline-4c50737e7c2d.scope` 已随环境停止；未碰生产 scopes。

实际可执行的捕获反馈检查：

```sh
taskset -c 11 artifacts/envs/harbor/bin/python scripts/probe_terminal_network_20261017.py --check-captured artifacts/eval/terminal-network-probe-20261017/probe.json
```

实际输出：`PASS: host/public DNS+HTTPS green, solver DNS red, restored-public green; resolver unchanged`。原始真实探针调用同脚本无参数，通过原 Terminal 启动环境和 frozen PYTHONPATH 运行；它拒绝覆盖已有诊断目录。脚本没有运行任务/评分的入口。检查捕获文件不会再次联网或创建 sandbox。

## 原实现与 Base 对照

- [run_terminal_baseline_v2.py](../scripts/run_terminal_baseline_v2.py) 的 `stage_network_metadata` 明确检查89份 upstream agent 元数据未设置网络字段，然后只在本地副本添加 `network_mode = "no-network"`。所以这是**本实验选择的约束**，不能称为这8个官方任务明确要求断网。
- [baseline_netns.py](../scripts/baseline_netns.py) 启动独立 rootless namespace + slirp4netns，resolver 为10.0.2.3。`set_public(False)` 设置 IPv4 OUTPUT DROP，仅允许 loopback，无DNS53例外；IPv6也拒绝外部流量。`set_public(True)` 恢复 public，并在私网拒绝前允许 slirp DNS。规则构造检查通过。
- [baseline_singularity.py](../scripts/baseline_singularity.py) 的 `_apply_network_policy` 调用该方法；resolver只读 bind 到容器。启动使用 `--cleanenv`，显式允许的宿主环境变量不含 HTTP(S)/ALL_PROXY。更换resolver地址也不能绕过 solver OUTPUT DROP。
- 8个 DNS 案例逐项核对：AVG与对应 Base `config.task.path` 和 task.toml 完全相同，均含本地断网 overlay。7项环境类相同；bn-fit-modify Base使用 rolling wrapper，网络 backend 仍来自同一冻结链。AVG frozen `baseline_netns.py` / `baseline_singularity.py` 与 Base runtime2 对应文件逐字节相同；中间 overlay 不含替代 backend 文件。
- 本次重新核实的是原 `trajectory.steps[].observation` 中的实际下载/DNS错误，不是 agent 分析文字。涉及 Ubuntu apt、PyPI包、github.com、archive.org 等多种来源；同一 pane 重复显示不计作独立请求次数。

## 用户追问：此前是否全部禁网

这里的“全部”限于Terminal的求解沙箱：Base、Terminal专家及AVG64使用相同的本地`agent.network_mode = "no-network"`设置。它覆盖89个任务，五个seed沿用该配置；并非本轮诊断后才开始断网。环境准备与verifier可以切回public，模型服务调用在agent宿主侧，因此既有补评分下载成功、模型请求正常都不能证明solver能访问外网。该结论不等于四项benchmark的所有阶段都禁网，也不表示每个失败都由禁网造成。

04:25:19 CST进一步只读核对：三组各445项冻结manifest所指任务元数据全部为no-network；Base现有442份accepted记录逐项沿原result/config读取task.toml，442份均一致、无缺metadata（recovery258、independent178、nativegaps6）。官方原始89份agent网络字段均未设置。这里不对更早未纳入冻结链的临时运行或训练轨迹做相同断言。

用户在上述范围说明后明确“那不用改了吧”。本轮已决定保持三组共同的no-network协议，普通分区续跑也不解禁，不重新生成旧答案或把历史失败重新标分。最终报告继续披露这是本地额外限制，可能影响需要下载依赖的任务；环境准备和评分的public阶段按原协议保留。此前讨论的更换联网策略或新增离线solver依赖包不在本轮实施。

## 三种假设的结论

1. **选定断网策略导致下载失败：已用真实入口复现。** public→no-network→public 的唯一变量就是 policy，错误可确定地出现/消失。
2. **当前 resolver/代理或 runtime 网络构建错误：本次差分不支持。** public阶段恢复成功、resolver始终相同、代理未设置。不能据此保证历史每一时刻上游都健康。
3. **瞬时 registry 不可达：不是解释本次症状所必需。** 历史瞬时故障不能仅凭当前探针完全排除；但原 case 的 solver 策略本来就不允许这些请求。

## 可统一修复的边界

协议 [protocol_v2_unified64k8k.json](../configs/eval/protocol_v2_unified64k8k.json) 同时写了“Solver only model endpoint”和“task-specific download/build dependencies staged before timer”。当前 frozen runtime 中，通用 native/UV/pip cache 是在 solver结束、`_prepare_verifier` 时才加入，不能充当已向 solver 预置依赖的证据。原任务 Dockerfile 也并非把所有后来尝试的软件装好：例如 Cython任务只预装numpy，pmars镜像只装tmux/asciinema，povray镜像还显式purge povray。**预置是否覆盖每个任务的必要前提仍需单独审核；不能把所有 agent 自选包都认定为必要依赖。**

建议的统一方案是保持 solver断网，先按原任务说明与环境构建清单，冻结、校验并向所有模型同样提供离线包/源码归档；在计时前检查可用性。不得包含参考答案、测试资产、解题代码或预先构建本来要求模型交付的目标程序。solver cache 与 verifier cache 要分开。该方案需要显式新环境版本和共同验收；当前所有已生成答卷、有效native0、未决项及原评分保持不变，不能在普通分区续跑时静默只修剩余题、再与旧 Base 混算。

本轮没有实施生产修复、扩大网络权限、安装依赖、重生答卷、评分或改 canonical。动态反馈已建立；由于这是诊断交付，没有“修复已完成”的声明。详细短证据与限制见[收据](source_snapshots/terminal_network_diagnosis_20261017.json)，完整轻量探针保存在 ignored artifacts 路径。
