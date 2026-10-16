# AVG64 正式执行队列部署

主合版继续固定为 `four-experts-avg-v1-20261017/avg-r64`，不根据正式结果调整。此处是实际服务与正式完整队列部署记录，不是独立 task-val，也没有将代理分数标成最终成绩。

## 专用服务

- 作业 `727660`，`ACD1-50`，2×H100 80GB，TP2，24小时；截止 `2026-10-18 02:09:48 +08:00`。
- 计算节点端口18000；80端点 `http://127.0.0.1:28092`。固定 adapter alias **`apex-avg64`**，基础 alias `apex-avg64-base`。
- vLLM0.20.2、BF16、65536上下文、单次8192输出、max-num-seqs20、max-lora-rank64、max-loras1，非thinking，沿用既有工具与reasoning解析器。FP32 adapter 在服务加载时按与专家一致的 BF16 LoRA 运行精度转换。
- 排除ACD1-59，并额外排除ACD1-24以避开已有SWE专家18000端口；既有727113、727640、727643未停止或改配。部署时项目六个作业共14GPU，低于16上限。
- 源码：[服务](../scripts/serve_merged_execution.py)、[Slurm](../scripts/serve_merged_execution.slurm)。HPC真实启动记录：`artifacts/eval/merged-execution-service-727660/launch.json`，日志为同级 `merged-execution-service-727660.log`。

## SWE与并行Terminal

[SWE配置](../configs/eval/avg64_swe_hard51_20261017.json)对应完整固定HARD51，输出 `artifacts/eval/avg64_swe_hard51_20261017`。自有[控制器](../scripts/run_swe_merged_benchmark.py)复用原SWE专家的native配置、模型桥和fresh replay评分辅助函数；模型请求明确为 `openai/apex-avg64`，桥只允许 `apex-avg64`。保留mini-swe-agent2.4.6、1800秒solver、1740秒mini内预算、1CPU/4GiB、64K/8K、非thinking和官方测试。

SWE只能在这些条件同时成立后准入：Base永久CPU释放、SWE专家51个attempt结束且pending/active为空、其canonical模型消费者完成、CPU0–9没有残留scope、AVG64 native验收完成、端点健康、服务余量≥2100秒。随后10个固定CPU槽0–9运行；不重新生成Base或SWE专家答案。全部attempt及replay/CPU清理后写出独立 `all_cpu_consumers_finished.json`，与较早可能产生的 `model-consumer-finished.json` 分开。

[Terminal配置](../configs/eval/avg64_terminal_full445_20261017.json)对应原89任务×5seed的445个native TrialConfig，输出 `artifacts/eval/avg64_terminal_full445_20261017`。复用Terminal agent准备的固定驱动和修复后的Base运行层，已在该输出下隔离快照470个源码文件。每个trial的任务checksum、seed、原生agent/verifier保持冻结；4CPU/8GiB、1800秒solver、900秒verifier、64K/8K、temperature1/top-p.95/top-k20、非thinking。

Terminal在2026-10-17 02:40:29 +08:00切换为用户授权的并行、不重叠CPU租约：专家初始offset12,16,…48（CPU12–51），AVG64初始offset52,56,…88（CPU52–91），各10槽。启动只要求永久Base释放、自己初始CPU池清空、已有验收、health与服务余量；不等待SWE或另一Terminal队列。迁移前实核两队列均445 pending/0 active/0 terminal、无正式trial目录，且原fixture CPU12–15及两初始池无scope，只停止两个旧waiting parent，没有中断或重生成任何attempt。

两个独立扩容stage可按任意顺序触发，且只检查各自新增CPU：

- mergedSWE的 `artifacts/eval/avg64_swe_hard51_20261017/all_cpu_consumers_finished.json` 为true后，专家增加offset0,4，AVG64增加offset8；原SWE专家前序由mergedSWE自身gate保证。
- ASI专家和mergedASI的以下两份all-CPU marker均为true后，专家增加offset92,96,100,104，AVG64增加offset108,112,116,120。

```text
artifacts/eval/asi128_asi240_20261017/all_cpu_consumers_finished.json
artifacts/eval/avg64_asi240_20261017/all_cpu_consumers_finished.json
```

ASI原生producer的最终all-CPU文件以 `state=finished`、`generation_worker_pool_shutdown=true`、`grader_process_finished=true`、`active_program_scopes=[]` 和 `generation_conditions=240` 证明释放，未自带现有Terminal parent所读的同义bool。为避免重启已准入parent，80上的单次sidecar [normalize_asi_cpu_markers.py](../scripts/normalize_asi_cpu_markers.py)（PID2945577）等待这两份原文件正式生成，严格核对上述五项后保留全部原JSON字段与时间，另存精确原文快照，原子补充 `all_cpu_consumers_finished=true`、`normalized_at` 与来源说明；两个完成后退出。日志为 `artifacts/eval/asi-cpu-marker-normalization-20261017/normalizer.log`，原文和操作收据保存在同目录。此兼容处理不要求grader评分有效，CPU释放与null分数分别记录；现有parent、worker、producer未重启，各stage对自己新增CPU的实际scope门槛继续生效。CPU临时文件验收确认缺文件不创建、五项任一不符不写入、原文/原字段保留。[启动收据](source_snapshots/asi_cpu_marker_normalizer_20261017.json)记录精确条件。

最终专家16槽、AVG6415槽，总31槽/124CPU。初始Terminal80CPU+SWE10+ASI32+grader4=126CPU；SWE先结束扩容时92+36=128；ASI先结束扩容时112+SWE10=122。各模型租约和stage CPU互不重叠。scope检查覆盖apex-baseline-、apex-asi-和ai4sci-submission-，按实际CPU affinity求交集；不检查会互相等待的整个0–91或92–123大池。固定445 native manifest、权重、采样、时限、每题CPU/内存和已有GPU服务均未改变，未增加GPU作业。

完成资源交接依据是全部attempt及CPU清理，不要求所有评分有效；评分基础设施失败继续保留null。只有51/445全部有效评分时才产生完整主分数，禁止按reward重跑或自动再生成。

## 启动与验收记录

80隧道PID2749797，SWE队列PID2749804。早期串行等待队列曾在零准入时同步scope规则；最新并行迁移只停止expert旧parent2782415与AVG旧parent2781816。当前expert parent **2878518**、AVG64 parent **2878519**；均实核active10/pending435/terminal0，各已有10个native trial目录。首次准入均为adaptive-rejection-sampler/seed0：expert child2878526使用CPU12–15，AVG child2878546使用CPU52–55。两输出各有 `first-admission.json`、`parallel-schedule-launch.json`；完整新调度证据见 [并行调度收据](source_snapshots/terminal_parallel_schedule_20261017.json)。

同一AVG64服务只安排一次native命令验收：使用隔离的官方缓存环境，执行写入/read-back小文件并验证最终状态；CPU12–15，避开SWE0–9和ASI92–127。其instruction为合成连通性命令，不读取benchmark题目、不调用Base生成、不形成benchmark成绩。验收保存在Terminal输出 `acceptance/acceptance.json`，通过后作为SWE `service-acceptance.json` 的依据。验收已于2026-10-17 02:17:46 +08:00通过：一个fixture内3次native请求均使用apex-avg64，fixture reward1、最终状态在verifier前保存、实测CPU12–15和8GiB；清理后这些CPU没有残留scope。rank64/310模块加载警告审计通过。该验收沿用于正式队列；SWE仍等待其前序，Terminal已按上述并行策略真实准入。最终验收结果与实际队列状态见 [部署收据](source_snapshots/merged_execution_queue_deployment_20261017.json)。

所有启动环境继承原SWE用户会话所需的systemd/DBus变量；Terminal仅使用自身冻结runtime/scripts，并设置独立TMPDIR和数值库单线程。私钥/API key内容未进入日志或收据。Slurm服务、隧道与后台控制器均已实际启动；各正式队列严格按当前已授权的自身资源gate准入；新的Terminal调度已进入运行。
