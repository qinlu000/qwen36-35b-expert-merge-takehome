# Terminal-Bench 2.0：单任务资源、时间与提速边界

核查日期：2026-10-15。仅阅读固定 Harbor 通用资源与 agent 代码、官方说明；未读正式任务答案/隐藏测试，未运行任务或模型 API。题面数值为 32 CPU、48 GB RAM、3 小时 agent timeout、89 任务×5 次；以下不把上限当作实测消耗。

## 关键纠正：32 CPU 是默认容器上限，不是自动独占预留

固定 Harbor commit `f527f8e447038fd242d08ecfa8aaa8029100da97` 的 Docker backend：

- `resource_capabilities()` 只声明 CPU/memory limit 支持。
- `_write_resources_compose_file()` 默认 `auto_mode=ResourceMode.LIMIT`。
- `write_resources_compose_file()` 把 CPU limit 写作 `services.main.cpus`，内存写作 `mem_limit`；只有显式 request 才写 reservations。该默认路径未配置 cpuset 独占绑核。

因此 `128/32=4` 表示“所有环境同时用满 32 CPU 时的容量情景”，**不是 Harbor 的最大并发数**。此前合计约9路也是按独占满额预留算的情景，不能说成机器只能运行9个任务。多个等待模型 API 的环境可共享 CPU；不需要把每个容器的32配额改小才能增加并发。共享若拥塞会放大 wall time，不能承诺每路独占32。Slurm 的 CPU allocation 另按实际资源绑定/分配规则检查，容器不能越过父 cgroup 的总配额。

Docker 的 `cpus` 限制累计 CPU 时间份额，和 `cpuset-cpus` 指定哪些逻辑处理器不同；不能把32 CPU直接等同于32个物理核心。48 GB也是内存上限，不代表每个 trial 启动就实际分配满48 GB。

证据：[固定 Docker backend](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/docker.py#L483)、[固定 Compose 资源生成](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/__init__.py#L31)、[Docker 官方 CPU 说明](https://docs.docker.com/engine/containers/resource_constraints/#cpu)、[Harbor 资源策略](https://docs.harborframework.com/tasks/resources)。

## 三小时是 agent 上限，完成就退出

`Trial._run_agent_phase()` 对 `agent.run()` 使用 `asyncio.wait_for(timeout=...)`；Terminus2 连续两次确认 `task_complete=true` 即 return，不会强制等待3小时。准备环境、agent setup、verifier和清理另计，因此端到端 trial 也可能超过3小时。当前没有真实平均耗时。

3小时固定值需设置 `agent.override_timeout_sec=10800` 并核对最终导出的配置；只设 `max_timeout_sec=10800` 是对原任务 timeout 取较小值，可能保留任务自身较短值，不能当作全局覆盖。

证据：[固定 trial 的 timeout 与 phase](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/trial/trial.py#L1434)、[Terminus2 提前完成](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py#L1528)。

## 能缩短什么

正式评测保持题定预算与五次运行；可提速：

1. 镜像提前拉取/构建并使用缓存；每个 trial 仍用干净工作区，不能共享执行后状态。
2. 同一来源独立 dev 上比较 4/8/16 等并发档，保留每容器32 CPU与48 GB上限，观测宿主机CPU、RSS、I/O、cgroup throttling及API等待，选择固定并发和资源政策用于全部模型。升并发不是线性提速保证。
3. API服务低延迟/本地连续批处理减少模型等待；异步启动/回收，已完成的trial立即补位；预加载依赖减少重复下载。
4. verifier与环境清理合理流水化，不能跳过评分、泄露测试或复用模型输出。

不能将3h改成15min、减CPU配额、砍任务/五次重复、减少固定上下文或输出上限，然后仍称题定正式配置。独立开发集/工程冒烟可以另用小预算，必须单独标注，不能冒充正式分数。

`max_tokens=80K` 应按API每次生成参数与题面口径核实；当前Terminus2逐轮调用模型、累计计量，没有在该agent循环中发现“每trial累计80K就停”的相同限制，不能在排期/费用时自动把它当总量上界。

## 用吞吐估计总时长，而不是按满额算必然开销

一模型445 trials；本题最低Base+交互专家+合版合计1335。设实测平均端到端每trial为t分钟，有效并发C，则理想小时数 `N*t/(60*C)`，另加尾部、排队/错误重试与模型切换。

| 范围 | 平均时长情景 | C=8 | C=16 | C=32 |
|---|---:|---:|---:|---:|
| DeepSeek一模型445次 | 15min | 13.9h | 7.0h | 3.5h |
| DeepSeek一模型445次 | 30min | 27.8h | 13.9h | 7.0h |
| 三个题定模型1335次 | 15min | 41.7h | 20.9h | 10.4h |
| 三个题定模型1335次 | 30min | 83.4h | 41.7h | 20.9h |

这些是情景算术，不是已测速度。独立dev应记录p50/p90耗时、平均CPU核秒/CPU峰值、峰值RSS、环境启动/模型等待/命令执行/评分耗时分解；正式任务启动后只用运行遥测更新完工预测，不根据正式正确率调整模型/agent方案。

待讨论：容器backend何时可用、共享并发的固定资源政策、真实dev吞吐；不能在没有实测时把CPU预留情景或3h超时当作每任务消耗。
