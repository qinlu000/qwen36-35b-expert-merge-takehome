# Terminal执行状态：08:10只读检查

队列/endpoint实际采集2026-10-17 08:09:14 CST，deadline源码核对08:10:14；0810是文件标签。[小型证据JSON](source_snapshots/execution_status_20261017_0810.json)。未刷新主summary/collector，未改配置、模型、队列、预算，未新增生成、native评分或API请求；health/metrics仅GET。当前覆盖不是445完整分数。

| 队列 | terminal/445 | raw valid/invalid | 已有audited view | active | pending | 自有槽 |
|---|---:|---:|---:|---:|---:|---:|
| Terminal专家 | 112 | 109/3 | 110/2（仅既有nginx native0 overlay） | 12 | 321 | 12 |
| AVG64 | 107 | 104/3 | 同raw | 11 | 327 | 11 |

parent489933/start868194930与489934/start868194945均存活；23槽全部有在途任务。两endpoint health200，原生metrics分别12/10 running requests、0/0 waiting，KV cache约8.63%/5.91%。generation_tokens_total累计848923/1094178，未将累计counter当瞬时TPS；AVG执行服务历史还接过SWE，不当作纯Terminal总吞吐。

## 异常增量与原预算

相对main0727专家92valid/2invalid、AVG90valid/3invalid，**新增invalid均0**。专家raw的第三项nginx是原04:13异常，已获批的独立同答卷native0只存在audited view；不能把raw与audited计数混合成新异常。全部当前raw invalid的finished_at早于07:26:42参考时点。

仍未充分核审的原null如下，本次不改变其归类：

| 模型/原条件 | 原记录提示 | finished CST | 当前判断 |
|---|---|---|---|
| 专家torch-tensor-parallelism/seed0 | AgentTimeoutError，reward null | 07:05:48 | 未决；solver timeout本身不证明verifier有效0 |
| 专家train-fasttext/seed0 | AgentTimeoutError，pytest wrapper零值但无执行测试证据 | 07:08:41 | 评分执行证据不足，保留null |
| AVG torch-pipeline-parallelism/seed0 | AgentTimeoutError，reward null | 07:06:40 | 未决，保留null |
| AVG torch-tensor-parallelism/seed0 | RemoteProtocolError，reward null | 07:06:25 | 通道异常提示，不足以排除资源/候选等根因，保留null |
| AVG train-fasttext/seed0 | AgentTimeoutError，pytest wrapper零值但无执行测试证据 | 07:09:30 | 评分执行证据不足，保留null |

固定每trial仍4CPU/8192MiB、solver1800秒、verifier900秒、64K上下文/8K输出。没有新增异常需要本轮展开原日志审计；已有异常metadata/路径见JSON，未进行新的环境/候选测试。

## CPU交接与scope

stage1已有永久交接证据：AVG SWE all_cpu marker于06:47:28 finished、51终态、active/pending空、scopes空；专家06:47:29.633接offset0/4（CPU0–7），AVG06:47:29.834接offset8（CPU8–11），各自当时新CPU scopes为空。当前真实scope分别在0–3/4–7/8–11，process_count146/16/16；对应专家git-multibranch、financial-document-processor及AVG extract-moves-from-video在途。CPU0–11已经由Terminal实际使用，不是等待释放。

stage2尚未交接：两队列均无cpu-expansion-asi_finished.json，槽仍12/11；专家ASI all-CPU marker已finished，但AVG ASI generation及all-CPU markers均缺，pipeline仍asi_generation/pid1126055、逻辑active8。采样时92–127未见相关实际program scope，不能将模型/API阶段的短暂scope空当作永久释放，不能提前扩容。现23槽没有因保守stage1 gate空等。

## 445截止速率与截止边界

相对main0727的07:26:42至08:09:14约42.53分钟，专家新增18终态，约**25.39 trials/h**；AVG新增14，约**19.75 trials/h**。剩余333/338次，若要求全部terminal在各GPU EndTime前完成，需约**18.63/18.77 trials/h**。机械延续短窗速率得到专家10/17 21:16、AVG10/18 01:16完成；这不是保证：后续任务难度/测试时长不同，AVG余量较窄，stage2实际释放时间未知。完整有效分还取决于既有null，不能用预计445 attempts等同445 valid。

Slurm实核：普通acd_u/Nice1000的727912、727913各TP2，均在ACD1-22 RUNNING，GPU EndTime分别10/18 **02:01:28、02:09:28 CST**。两持久runtime helper相同SHA `20fbbfd02e77c24d4bbffcb6e8f74e85757bdd715f6cae2b6c1296f68b267b5c`，142–143行service_safe只要求GPU剩余至少2100秒；172行每次新题前检查，并支持STOP_ADMISSION（当前不存在）。因此最新准入约**01:26:28/01:34:28**，不会到GPU截止最后几分钟仍无门槛发题。未发现独立02:20 core新题门；migration中的stop_new_tasks_after亦按EndTime−2100写出。

**区分GPU与完整native尾部**：verifier在80执行，不需要模型GPU；2100秒可以覆盖1800秒solver加300秒前置余量，不能机械断言35分钟一定不足。然而真实manifest未override setup/build：89 task的environment build/start上限均600秒，倍率全1；冻结继承链TerminalRepairAgent→RecoveryTerminalBaselineV2→TerminalBaselineV2→Terminus2→BaseAgent给agent setup上限**360秒**，不是300。单次start600+agent setup360+solver1800的上限情景为2760秒，长setup可能消耗模型服务runway。再加verifier900为3660秒、尚未计cleanup；若在最后准入点且这些阶段都耗满，简单链尾部可到02:27:28/02:35:28，cleanup总上界本轮未证，非精确完工预测。

root当前core语义是到点停止定时推进、已准入自然保留原预算，因此尾部可能跨02:20是需披露的边界，不据此缩短既定solver或打断在途。本轮未启动停止watcher、扩容、重试、改预算或parent。

## 随后获授权准备的01:10准入guard（未execute）

root决定保留live parent及每题预算，只在10/18 **01:10 CST**通过既有STOP_ADMISSION门停止未来submit。[最小guard脚本](../scripts/terminal_core_admission_guard_20261017.py)已同步80，默认prepare-only；固定两正式输出、原config/manifest SHA、model/checkpoint及service EndTime，不新增config。--execute才独占建立`artifacts/eval/terminal-core-admission-guard-20261017/{claim.json,state.json,log.jsonl}`，sleep不超过30秒；到点只独占创建STOP门，原门存在则保留其内容/原因，绝不kill在途、写CPU marker或释放GPU。两队先445终态且active/pending均空则early no_consumers退出。没有child/model/API/container入口，SIGTERM只结束本guard。

01:10距专家GPU02:01:28有3088秒，超过已知start600+agent setup360+solver1800=2760秒；单次该链加verifier900=3660秒到02:11，距core02:20尚9分钟供其余尾部。这是已知预算裕量，不能保证全部未知phase/cleanup上限；仍不缩任何在途预算。

08:13:56实际CPU10 defaultprepare/AST通过，4个离线fixture验证cutoff前等待/正点停止/过点停止/两队先完成提前退出；写gate0、新native0、claim目录未产生。脚本5041B，SHA256 `91b262ff2798739ca5c0dabd30050815cfdac7e30f4cef4cc2e8df1f8227eaac`。本agent未执行--execute，root审核后负责唯一后台启动。

## Root后续唯一启动（08:14:45）

root完整审核后于08:14:45.787 CST使用`taskset -c 10 /usr/bin/python3 scripts/terminal_core_admission_guard_20261017.py --project /data/caoqinlu/projects/apex-takehome --execute`唯一启动，PID**1508852**、startticks**869510981**，脚本仍为上述冻结SHA。未使用cgroup AllowedCPUs限制。host80 launch receipt为`artifacts/eval/terminal_core_admission_guard_launch_20261017.json`，[本地副本](source_snapshots/terminal_core_admission_guard_launch_20261017.json)保留刚launch时的pending-claim-observation状态；root随后已核实真实claim/state为**waiting_cutoff**、两STOP均不存在、0新native/模型调用。

canonical状态路径为`artifacts/eval/terminal-core-admission-guard-20261017/state.json`，claim同目录`claim.json`。此段记录root后续实际操作，不回写此前08:13 prepare-only历史；本agent仍execute/launch0、未重复启动或改脚本。这次文档更新未另做远端状态查询。
