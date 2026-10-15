# 四项评测：单任务资源、时间与提速

更新：2026-10-15。仅核对固定官方代码、资源字段与题面；未运行正式任务或模型调用，尚无平均耗时/P50/P90实测。本表CPU是任务环境配额，不包含模型推理服务；时间是上限，不是每题必须跑满。

| Benchmark | 单路 CPU / 内存 | agent 时间 | 可缩短与边界 |
|---|---|---|---|
| Terminal-Bench 2.0 | 题定32 CPU / 48 GB；固定Docker默认是limit，不自动独占 | 题定3小时上限；正常完成提前返回；构建/判分/清理另计 | 保留上限、89项×5次及固定预算；靠有效并发、镜像缓存和减少等待提速 |
| SWE Pro V2 HARD-51 | 已扫描51/51，统一1 CPU / 4096 MB；storage 10240 MB | agent上限50分钟；verifier另50分钟，build另30分钟；还要fresh replay | 保留locked protocol的50分钟与fresh replay；多路并行和镜像预热；不能把上限相加当平均耗时 |
| ASI-Bench | Docker os默认4 CPU / 8 GiB；选定60项全部声明requires_gpu=false、services=0；linux_ns不施加相同CPU/内存限制 | 默认3小时 / (task,B层,attempt)，可在实验前统一配置；非题面写死值 | 可提高并发；缩timeout会改变实验设置且可能降分，需训练前确定、全部模型一致并披露 |
| HLE | 没有逐题固定CPU沙箱；请求/答案处理与评分客户端共享CPU，模型推理另算 | 没有统一题定每题墙钟时间；由生成长度/吞吐、网络和Judge决定，均值未测 | 并行请求/连续批处理、异步评分；受模型服务或供应商吞吐限制，不按TB的32CPU分配 |

SWE/ASI证据见[固定资源字段核验](task_resources_swe_asi.md)；TB见[固定Harbor核验](task_resources_terminal.md)。HLE固定参考：[生成客户端](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)。

关于30分钟/最多4CPU：见[原题与协议边界](budget_30min_4cpu_review.md)。SWE50分钟是当前官方locked protocol，而非题面直接写死；30分钟可作披露的自定义预算实验，不能称原locked protocol。TB3h/32CPU则为题面明确配置；ASI可提前固定30分钟；HLE不按每题独立CPU沙箱处理。本轮未修改正式预算。

当前风险判断：现有已落实资源**不足以保障**题定TB全矩阵在截止前完成；这不等于单任务不能运行，也不是已测得CPU必然不够。保留cpus=32仅证明容器quota配置，不能证明共享宿主上同时获得相同实际资源。不得以任意超卖代替资源保障；争用可能增加命令耗时和超时，必须测量并披露宿主负载/有效分配、固定跨模型资源政策。80共享资源未保留、HPC180CPU只是尚未分配的account上界，因此不能承诺9或16有效并发。后续需增加兼容CPU资源，或取得面试方对资源受限协议的接受；当前正式配置不改。详见[CPU容量风险](tb_cpu_capacity_risk.md)。

## 纠正此前9路并发结论

此前80可见128逻辑CPU÷32约4，加HPC当前account剩余180CPU÷32约5，合计约9，隐含每个环境同时独占满额CPU。**这是满额容量情景，不是最大软件并发数**。固定Harbor Docker默认CPU为limit，没有给每trial独占32核；48GB也不是启动即占满的实际RSS。等待模型/API时可以多开，因此不能据9路直接判定必然超时。

更高并发不是已验证能力。CPU、内存、磁盘I/O和模型队列拥塞都会拉长任务；Slurm allocation/父cgroup仍限制总用量。80共享主机且容器后端未ready，本轮没有安装后端或启动试验。

建议在独立自造/dev任务比较4/8/16等并发，保留题定每容器上限，记录CPU核秒/峰值、RSS、I/O、throttling、模型等待与总时长，再训练前固定所有模型的资源与调度政策。不能默减quota后仍报告32CPU。

## 吞吐情景，不能当实测排期

理想总小时数约为 N×每trial平均分钟/(60×有效并发)，另留长尾、环境与判分/重试。

TB若实际达到16有效并发、平均端到端15分钟，单DeepSeek模型完整445次约7.0小时；平均30分钟约13.9小时。本题Base/交互专家/合版三个模型1335次对应约20.9/41.7小时。均为示例，增加并发不保证平均时长不变。

优先完成容器后端、测有效并发与模型吞吐、预拉镜像，轻CPU的HLE/SWE填空、独立评分随产物启动。开发冒烟可短预算；正式TB/SWE不任意砍上限、任务、重复或replay；ASI timeout可选但需另行提前冻结。

补充：固定ASI全部60项只读task_meta.yaml核查，无任务声明GPU必需或sidecar。不能继续把本版本部分任务必须占GPU当事实；若后续agent选择GPU程序，仍需按冻结设备策略处理。linux_ns只施加namespace/超时，无CPU quota/cgroup/rlimit，资源需外层落实。
