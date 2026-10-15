# Terminal-Bench：CPU容量与完工风险

更新：2026-10-15。仅只读核查与容量算术；未运行正式任务、API或Slurm作业。尚无实测平均耗时或已获CPU分配。

## 当前判断

现有资源不足以保证题定全量在剩余窗口完成，但不能据配置断言每次实际用满32CPU或3小时。问题是有效并发和完工时间未获保障，而不是单个任务绝对无法运行。

- 80可见128逻辑CPU，只对应4路同时用满32CPU的理论容量；宿主共享、项目未获独占预留，因此4路也不是已保障能力。64物理核的SMT不代表吞吐翻倍。
- HPC当前账户在已有12CPU作业不变时理论剩余180CPU，最多对应5路满额TB；还需扣本题训练和推理CPU。CPU-only政策、实际分配和兼容容器后端未验证。
- 不能承诺合计9路或16路。硬件可见资源、账户上限、实际分配和有效并发是不同概念。

## quota与实际资源的边界

固定Harbor Docker默认CPU为limit，不自动独占预留32核。Docker cpus限制累计CPU时间配额，与cpuset绑核不同。等待模型期间可以共享，但过度争用会拉长命令、增加wall-time超时并改变得分。保留cpus=32本身不足以证明实际资源与参考配置相当。需落实主机或Slurm资源、避免明显争用，并固定及披露所有模型的并发和共享政策。

固定证据：[Harbor Docker资源实现](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/docker.py#L483)、[Compose资源生成](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/docker/__init__.py#L31)。通用语义：[Docker官方CPU说明](https://docs.docker.com/engine/containers/resource_constraints/#cpu)。

## 36小时条件算例

单Base为89题×5次=445次；最低题定矩阵Base、交互执行专家、合版为3×445=1335次。以下仅TB，不含其余三项。设每次平均端到端t分钟、有效并发C，理想小时数=N×t/(60×C)，另需长尾、排队和重试余量。

| 有效并发C | 单Base在36h内要求平均不超过 | 三模型1335次在36h内要求平均不超过 | 1335次若平均30min的理想耗时 |
|---:|---:|---:|---:|
| 4 | 19.4min | 6.5min | 166.9h |
| 8 | 38.8min | 12.9min | 83.4h |
| 9 | 43.7min | 14.6min | 74.2h |
| 16 | 77.7min | 25.9min | 41.7h |

均为情景算术，并发与均值均未实测；36小时是示例预算，不代表当前剩余时间。升并发可能使每次耗时增加。单Base若9路且均值30分钟约24.7小时，但9路未获资源保障。

## 可行方向

1. 落实CPU总配额及兼容Docker后端，必要时增加组内评测主机或额外CPU资源。
2. 用独立开发任务测CPU核秒、RSS、I/O、throttling、模型等待和吞吐，选取避免明显争用的固定策略。
3. 若资源和期限无法同时满足，向面试方请求接受30分钟/4CPU等资源受限协议；这是题定配置偏离，不能自行等同。
4. SFT/RL与模型大小影响GPU和模型吞吐，不能代替任务环境的CPU资源。当前不修改正式配置或减少五次重复。
