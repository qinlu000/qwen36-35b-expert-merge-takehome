# Terminal250 正式完整评测执行记录

截至 **2026-10-17 02:17 CST**，Terminal 专家服务 **727640** 已实际部署并通过一次原生终端命令验收；80 上正式完整 **89题 × seeds0–4 = 445次** 的自动队列已常驻，当前 controller **PID2782415**，**0正式准入 / 445待跑**。队列依赖 SWE 专家与合版 SWE 的全部模型和 CPU 消费者结束，不再依赖独立 task-val benchmark。没有生成任何 Base 答卷。

输出：80 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/terminal250_full445_20261017/`。真实启动与队列回执见 [queue snapshot](source_snapshots/terminal_expert_queue_20261017.json)、[launch snapshot](source_snapshots/terminal_expert_launch_20261017.json)。

## 权重与独立服务

- `terminal-retry-sft-r16-726665/training/checkpoint-250`，r16 / alpha32，620个 A/B 张量、310个模块，覆盖与已验收专家一致。HPC 原始 trainer state 实读最后与最佳验证 loss **0.4229174852371216**，step250 / epoch1；不是早期中间权重。
- Base revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，完整视觉模块保留，BF16 / TP2，静态专家 alias **`apex-terminal250`**；服务提供的 Base alias 没有被生成请求使用。
- Slurm **727640**，`emergency_acd` / `formal-user` / `qinlucao`，**ACD1-28、2GPU、16CPU、128GiB**，排除 ACD1-59。实际 Start **10-17 02:01:37**、End **10-18 02:01:37 CST**，`TimeLimit=1-00:00:00`，未调整别人的服务或尝试 owner 延长。
- 专属端口18003，80 专属 SSH supervisor **PID2697218** 将28091转发到 ACD1-28:18003，不改727113或28089。服务 max_num_seqs20、64K总上下文、8K每请求输出、GDN/MoE triton、qwen3_coder工具解析；thinking与preserve_thinking均关闭。
- 服务02:08:23完成启动，认证 `/v1/models` 已实读。原生输出已复核，没有被忽略 adapter 参数或未支持 LoRA 的警告；见 [service snapshot](source_snapshots/terminal_expert_service_727640_20261017.json)。完整日志位于 HPC `artifacts/eval/terminal-service-727640.log`，没有输出密钥。

入口：[serve_terminal_expert.py](../scripts/serve_terminal_expert.py)、[Slurm launcher](../scripts/serve_terminal_expert.slurm)。

## 唯一原生验收

02:10:20已完成一次合成 echo/read 命令夹具，使用原固定 `bn-fit-modify` 的缓存 SIF 与环境文件，指令和测试均为新建合成夹具，官方原题未修改，也没有向模型提交该题问题。实际走原生 Terminus2 的 JSON 动作、持久 tmux、原始请求适配器和 repaired Base 环境：两个专家请求执行 `printf` 后 `cat`，夹具 reward1，exception为空。

实际 CPU affinity 为 **120–123**；原 Base launcher 在启动前核对 systemd `MemoryMax=8589934592`、swap0，并保留继承的 affinity seccomp 限制。已验证原生 verifier 之前保存的 final-task-state tar/receipt。`Trial.run()` 完全返回后才写 `acceptance/acceptance.json` 的 `ready=true`；direct 专家 agent 已收到 CPU120–123释放通知。原始配置、请求、轨迹、答卷与测试输出都保留。见 [native acceptance](source_snapshots/terminal_expert_native_acceptance_20261017.json)。

这只是服务与环境命令链验收，没有额外独立 task-val、没有正式分数，也没有 Base 生成。入口 [accept_terminal_expert.py](../scripts/accept_terminal_expert.py) 可用配置指定合版 alias、Base alias 与临时验收 CPU。

## 正式范围、协议与 CPU 协调

完整范围来自 Base 的 `artifacts/runs/base-terminal-recovery-v2-20261016/runtime11/manifest.json`：保留全部89任务、每题原始 task checksum、五个原始 seed job 配置与 seed0–4，445个唯一键均已生成新 TrialConfig。**旧187条 repair cohort 不是本实验范围**，不继承任何 Base 答案或评分。

每次答题保留相同资源受限协议：原生 Harbor Terminus2，solver1800秒、native verifier900秒、4CPU、8GiB、65536上下文、8192输出，temperature1 / top_p0.95 / top_k20、nonthinking；原生问题、工具行为、测试和 reward 不变。该结果应明确称为资源受限协议，不能当作原3小时 / 32CPU设置的结果。

最初分配 **23个任务槽，CPU0–91**。准入同时检查：Base 永久 CPU release；SWE249 的51个 terminal、active/pending清空、model-consumer receipt；合版 SWE 的 `artifacts/eval/avg64_swe_hard51_20261017/all_cpu_consumers_finished.json` 明确为true；目标实际 scopes 清空；本服务原生命令验收通过；服务至少还剩2100秒。

CPU92–95留给 ASI grader，96–127留给 ASI 专家及合版生成。仅在下列两份回执均为 `state=finished` 且实际 CPU92–123 scopes 清空后，自动增加8个槽，达到 **31槽、CPU0–123**：

- `artifacts/eval/asi128_asi240_20261017/all_cpu_consumers_finished.json`
- `artifacts/eval/avg64_asi240_20261017/all_cpu_consumers_finished.json`

与 repaired Base 的每题预算相同，但 Base 使用两个推理副本，本实验只有一个 TP2/maxseq20 服务，并受上述23→31准入调度影响；分数差异不能只归因于权重。

入口：[fixed config](../configs/eval/terminal250_full445_20261017.json)、[preparer](../scripts/prepare_terminal_expert_benchmark.py)、[controller](../scripts/run_terminal_expert_benchmark.py)。所有实际依赖层按 Base 最终优先顺序合并到本输出 `runtime/scripts`，包括 runtime-v2 repair、runtime11 verifier、runtime7 native、runtime3 recovery 与 Base runtime2/Harbor。保留 native PATH、当前 task verifier cache、独立可写 cache inode、超时后 solver 清理与 verifier 前完整状态保存。`runtime/source_inventory.json` 记录470份实际文件来源和一次性 SHA；没有重扫权重、SIF或大型资产。

## 保存与完成口径

每个预定键仅生成一次新答卷；已有 trial 目录会阻止自动再次生成。保留所有答案、报错与原生测试输出，不按 reward 选择重试。原生正常超时、context/output预算及程序错误按原规则评分；verifier基础设施问题单独保留为未评分，不补成0。

summary固定分母445与每seed89，只有各seed89份有效评分齐备才计算五轮平均和 ddof1 SD。所有445次尝试与 CPU 子进程结束后，进一步检查实际使用过的CPU池中 Terminal、ASI与原生 grader scopes 均已清空，才写 `all_cpu_consumers_finished.json`，记录 `used_cpu_ids` 与 `remaining_cpu_scopes=[]`；未扩容时只检查0–91，避免误等预留的 ASI 池。`benchmark_complete` 单独反映评分是否完整；这份资源释放回执供合版 Terminal 队列等待。合版 agent 已收到同一完整445 preparer/launcher、协议与回执路径。

本轮仅为资源协调重启过自己的零准入等待 controller，保留了启动历史；服务727113、SWE controller824673、Base与训练均未停止或改变。Git与 `claud.md` 由 root agent统一更新。
