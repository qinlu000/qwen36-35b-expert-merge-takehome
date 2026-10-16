# AVG64 正式执行队列部署

主合版继续固定为 `four-experts-avg-v1-20261017/avg-r64`，不根据正式结果调整。此处是实际服务与正式完整队列部署记录，不是独立 task-val，也没有将代理分数标成最终成绩。

## 专用服务

- 作业 `727660`，`ACD1-50`，2×H100 80GB，TP2，24小时；截止 `2026-10-18 02:09:48 +08:00`。
- 计算节点端口18000；80端点 `http://127.0.0.1:28092`。固定 adapter alias **`apex-avg64`**，基础 alias `apex-avg64-base`。
- vLLM0.20.2、BF16、65536上下文、单次8192输出、max-num-seqs20、max-lora-rank64、max-loras1，非thinking，沿用既有工具与reasoning解析器。FP32 adapter 在服务加载时按与专家一致的 BF16 LoRA 运行精度转换。
- 排除ACD1-59，并额外排除ACD1-24以避开已有SWE专家18000端口；既有727113、727640、727643未停止或改配。部署时项目六个作业共14GPU，低于16上限。
- 源码：[服务](../scripts/serve_merged_execution.py)、[Slurm](../scripts/serve_merged_execution.slurm)。HPC真实启动记录：`artifacts/eval/merged-execution-service-727660/launch.json`，日志为同级 `merged-execution-service-727660.log`。

## 先SWE，再Terminal

[SWE配置](../configs/eval/avg64_swe_hard51_20261017.json)对应完整固定HARD51，输出 `artifacts/eval/avg64_swe_hard51_20261017`。自有[控制器](../scripts/run_swe_merged_benchmark.py)复用原SWE专家的native配置、模型桥和fresh replay评分辅助函数；模型请求明确为 `openai/apex-avg64`，桥只允许 `apex-avg64`。保留mini-swe-agent2.4.6、1800秒solver、1740秒mini内预算、1CPU/4GiB、64K/8K、非thinking和官方测试。

SWE只能在这些条件同时成立后准入：Base永久CPU释放、SWE专家51个attempt结束且pending/active为空、其canonical模型消费者完成、CPU0–9没有残留scope、AVG64 native验收完成、端点健康、服务余量≥2100秒。随后10个固定CPU槽0–9运行；不重新生成Base或SWE专家答案。全部attempt及replay/CPU清理后写出独立 `all_cpu_consumers_finished.json`，与较早可能产生的 `model-consumer-finished.json` 分开。

[Terminal配置](../configs/eval/avg64_terminal_full445_20261017.json)对应原89任务×5seed的445个native TrialConfig，输出 `artifacts/eval/avg64_terminal_full445_20261017`。复用Terminal agent准备的固定驱动和修复后的Base运行层，已在该输出下隔离快照470个源码文件。每个trial的任务checksum、seed、原生agent/verifier保持冻结；4CPU/8GiB、1800秒solver、900秒verifier、64K/8K、temperature1/top-p.95/top-k20、非thinking。

Terminal先等待两套SWE全部CPU/模型消费者结束，以及Terminal专家完整445的 `all_cpu_consumers_finished.json`；初始23槽占0–91。只有下列两条显式CPU完成文件均完成且实际scope清空，才增加8槽、扩为31槽0–123：

```text
artifacts/eval/asi128_asi240_20261017/all_cpu_consumers_finished.json
artifacts/eval/avg64_asi240_20261017/all_cpu_consumers_finished.json
```

完成资源交接依据是全部attempt及CPU清理，不要求所有评分有效；评分基础设施失败继续保留null。只有51/445全部有效评分时才产生完整主分数，禁止按reward重跑或自动再生成。

## 启动与验收记录

80隧道最初PID2749797，SWE队列PID2749804。Terminal等待队列在零准入时加强为直接依赖两套SWE和两条all-CPU完成文件，原PID2749805退出后由2766468接替；随后在零准入时同步实际CPU scope清理规则，最终Terminal控制器PID为2781816；没有formal生成。真实PID及后续仅等待状态的源码同步记录保存在两套输出的 `queue-launch.json`。

同一AVG64服务只安排一次native命令验收：使用隔离的官方缓存环境，执行写入/read-back小文件并验证最终状态；CPU12–15，避开SWE0–9和ASI92–127。其instruction为合成连通性命令，不读取benchmark题目、不调用Base生成、不形成benchmark成绩。验收保存在Terminal输出 `acceptance/acceptance.json`，通过后作为SWE `service-acceptance.json` 的依据。验收已于2026-10-17 02:17:46 +08:00通过：一个fixture内3次native请求均使用apex-avg64，fixture reward1、最终状态在verifier前保存、实测CPU12–15和8GiB；清理后这些CPU没有残留scope。rank64/310模块加载警告审计通过。两套队列endpoint_accepted均为true，仍分别保持51/445 pending、0 active、0 terminal，只等待资源前序。最终验收结果与实际队列状态见 [部署收据](source_snapshots/merged_execution_queue_deployment_20261017.json)。

所有启动环境继承原SWE用户会话所需的systemd/DBus变量；Terminal仅使用自身冻结runtime/scripts，并设置独立TMPDIR和数值库单线程。私钥/API key内容未进入日志或收据。Slurm服务、隧道与后台控制器均已实际启动；正式队列在资源gate通过前保持零准入。
