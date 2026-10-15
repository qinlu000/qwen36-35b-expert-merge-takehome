# SWE Pro 与 ASI 单任务资源及时间核验

更新：2026-10-15。仅核对公开 ID 清单、task.toml 资源字段、通用 runner 代码；未读取正式题面、答案、补丁或测试内容，未执行任务、模型调用或 Slurm 作业。

## 结论

| 项目 | 每路 CPU / 内存 | 每次 agent 时间预算 | 已知额外耗时 |
|---|---|---|---|
| SWE Pro V2 HARD-51 | **51/51 均为 1 CPU、4096 MB RAM、10240 MB storage** | **3000 秒 = 50 分钟**，51/51 相同 | verifier 上限另为 3000 秒；build 上限 1800 秒；还须在全新镜像重放模型 patch 并重新评分 |
| ASI-Bench Docker `os` | runner 默认 **4 CPU / 8 GiB**；不是 TB 的 32 CPU / 48 GB | 默认 **10800 秒 = 3 小时 / (task, B层, attempt)**；CLI 可改并冻结 | 镜像构建、任务计算、评分；需要 GPU 的任务还会请求 GPU；带 sidecar services 的任务最多额外 2 路各 1 CPU / 1 GiB |

以上都是资源配额或时间上限，**没有正式运行实测均值/P50/P90**。不得把 50 分钟或 3 小时写成每题必需耗时。

## SWE 全量扫描

固定代码版本 `66f92766bba642462d4bbe5479e83f91f9211862`。先读 `v2/hard51_ids.txt`，然后并行只解析其 51 个 `task.toml` 的 `[agent]`、`[verifier]`、`[environment]` 白名单字段。全部 51 项配置相同：

```json
{
  "count": 51,
  "agent": {"timeout_sec": 3000.0, "network_mode": "no-network"},
  "verifier": {"timeout_sec": 3000.0, "network_mode": "public"},
  "environment": {
    "build_timeout_sec": 1800.0,
    "cpus": 1,
    "memory_mb": 4096,
    "storage_mb": 10240,
    "network_mode": "public"
  }
}
```

单模型 51×50min = **42.5 agent-sandbox-hours**；若能实际支撑 16 并发且每次都用满预算，agent 阶段分四批，约 3h20min，非整个 SWE 完成时间。模型 API 吞吐、容器 setup、verifier、fresh replay 仍在外面。最低三模型矩阵共有 153 次 agent 运行及其 fresh replay。

### 可以怎样缩短

- 1 CPU 配置允许更多并行 sandbox，瓶颈可能转为模型 token 吞吐、网络或磁盘；增加并发是主要合法加速途径。
- 预拉固定镜像、预热依赖下载缓存，重评分与后续模型运行流水并行；保持 fresh sandbox、不共享被测任务的可写状态。
- 官方 locked protocol 明确 50 分钟预算。不能为赶时间把正式 agent 预算改为 10 分钟再宣称同一配置；模型自然完成可提前退出。
- fresh replay 是 authoritative score 的必要步骤，不能省略；不能把先前模型结果复用给新模型。

来源：[官方 locked protocol 与运行方法](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#the-locked-protocol)、[完整 HARD-51 ID 清单](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/hard51_ids.txt)、[资源文件目录](https://github.com/scaleapi/SWE-bench_Pro-os/tree/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks)。

## ASI 资源与可调整项

固定代码 `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`：

- `core/types.py` 的 `DEFAULT_TIMEOUT_SECONDS=10800`。
- `run --timeout` 默认取该值，明确写着 task metadata 不能覆盖它。`--parallel` 默认 1，可显式提高；`run-score` 也能提高执行和评分并行。
- `OSSandbox.DEFAULT_CPU_LIMIT=4.0`，`DEFAULT_MEMORY_LIMIT=8g`，主容器的资源是 runner 统一默认，不会据各 task runtime 自动精细调整到不同 CPU；构造器可接受覆盖，但公开 run CLI 没有对应 CPU/memory flags。
- `runtime.services` 支持最多两个 sidecar，每个另给 `--cpus 1.0 --memory 1g`。其声明包含 image/port/command/startup_timeout/environment，不是每题主容器的 CPU 配额表。
- `difficulty.requires_gpu=true` 会传 `--gpus all`。这不等于每题仅占一张 GPU；必须显式规划可见设备，否则会与模型服务抢四张卡。
- `auto_limit_workers` 对 `os` 模式按主机 `CPU_count//4` 与物理总内存的 80%/8GiB 夹紧。它看的是宿主机可见资源，不代表 Slurm 已分给本项目同等配额；`linux_ns` 不享有这套 Docker 限额语义，不能照搬 4CPU 保证。
- 补充全量 metadata 核查：按固定 open split metadata.json 的 60 个 task_id，在固定代码版本读取各 task_meta.yaml，只输出 difficulty.requires_gpu 与 runtime 键/sidecar 数量。**60/60 requires_gpu=false，60/60 无 runtime.services**。因此当前选定 60 项没有声明必须 GPU 或额外 sidecar；不能将“ASI 存在必须用 GPU 的任务”当本版本已证实约束。runtime 键分布：54 项 packages+python，1 项另有 platform，1 项另有 dockerfile，2 项只有 packages，2 项没有 runtime。未读取 task_eval.yaml、任务执行代码或参考答案。

完整单模型 240 个条件若都用满默认 3 小时，为 **720 agent-task-hours**。16 路理想 45 小时，24 路理想 30 小时；实际task早停可能更短，镜像/评分等更长；当前60项metadata均未要求GPU，不额外预留任务GPU。

### 可以怎样缩短

- 优先加大 `--parallel`、提前构建固定 task images，作答与独立评分分阶段流水运行。
- ASI 的 3 小时是框架默认，不是题面要求的统一硬值。可以在训练前决定统一如 1 小时的预算，所有模型一致并明确披露；但会改变实验设置，可能损失成功率。必须先看独立任务耗时，不能保证足够，也不能声称复现原始 3 小时配置。
- 当前60项metadata均未要求GPU；若后续agent选择GPU程序，按预先冻结的设备策略处理，避免自动暴露所有模型服务卡。
- 不缩减 60 项×四层，不在不同模型间改预算，不在看到正式得分后挑预算或失败题。

来源：[超时常量](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/types.py)、[CLI timeout/parallel](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L1469)、[OS runner 资源、services、GPU](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py)、[并发自动限制](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/parallel.py)。

## 补查：linux_ns 不是 Docker 资源限制

固定 linux_ns_sandbox.py 定义了 DEFAULT_MEMORY_LIMIT_KB=8*1024*1024 并保存到 self.memory_limit_kb，但该字段未在 run_command 或其他方法中应用；命令只通过 unshare user/mount/pid namespaces 与 subprocess wall timeout 执行，没有 CPU 配额、cgroup 或 rlimit 设置。parallel.py 对非 os 模式也不根据 CPU/内存自动下调并发。故 **不能把 Docker os 的 4 CPU / 8 GiB 写成 linux_ns 的强制每题资源隔离**。若使用 linux_ns，资源限制需由外层 Slurm/cgroup 等落实并记录，不可仅用 namespace 名字当作已有保证。

来源：[linux_ns runner](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/linux_ns_sandbox.py)、[固定 60 项公开 metadata（仅任务 ID）](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed31415/blob/0fa14219cafdbab634d8b3cfbce238a8735a214f/metadata.json)、[task_meta.yaml 所在目录](https://github.com/apexin-ai/ASI-Bench/tree/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks)。
