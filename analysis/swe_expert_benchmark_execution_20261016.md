# SWE249 正式 HARD51 全量评测

更新：2026-10-17 01:24 CST。用户取消 SWE 独立 source validation，明确保留已有 Base 评测，只将完成训练的 SWE 专家 checkpoint249 跑正式 benchmark。独立 validation 的 controller/image进程已全部退出，模型请求0；100题/2个SIF/cache/gold原件保留，`CANCELLED_BY_USER.json`与启动/准入guard阻止恢复。取消回执见 `analysis/source_snapshots/validation_swe_cancelled_20261016.json`。

正式专家评测常驻 **PID824673**，输出为80 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/swe249_hard51_20261016/`。**固定51个正式任务与缓存SIF全部就绪，01:21:20已实际准入10题，当前10在途/41待跑；01:23:24保存87份实际upstream request记录，alias全部为SWE249，尚0有效评分。** 不生成任何Base答卷，不改正在跑的Base clean28、其最终corrected51汇总或训练。

## 固定任务、权重与服务

- 完整正式清单：`analysis/source_snapshots/protocol/swe_hard_task_ids.json`，官方 `scaleapi/SWE-bench_Pro-os@66f92766bba642462d4bbe5479e83f91f9211862/v2/hard51_ids.txt`；不是Base环境修复的28题子集。
- HF任务快照：`ScaleAI/SWE-bench_Pro@2d52cb3df914a3fcf80c7f66738b3a88ae37fc50`，hard/test，51题。沿用原 `artifacts/benchmarks/swe-hard51` 的 instruction、environment setup、tests与官方fresh replay，独立完整copy后仅把image字段指到其原已缓存固定SIF。
- 权重：`swe2k-sft-r16-726335/training/checkpoint-249`，Base revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，原r16/alpha32。使用已验收727113的TP2 BF16服务 `http://127.0.0.1:28089`，唯一模型alias **`apex-val-swe249`**，没有新GPU申请。
- Agent请求名和bridge固定allowlist同时为`openai/apex-val-swe249` / `apex-val-swe249`。LoggedRelay在validator之前检查incoming model，因此这两处必须一致；不能只改bridge再保留旧`apex-qwen`。配置断言不接受Basealias。准备检查只解析实际51份TrialConfig、无model/container/test调用，回执保存全部51行环境类/alias。

## 与已有Base一致的Agent及运行预算

复用 `run_swe_baseline_v2_native.py` 的实际 `stage_tasks/run_phase/trial_config`，固定mini-swe-agent2.4.6、官方LockedMiniSwe→`SweBaselineNativeV2`私有安装、原官方 `mini_toolcall.yaml` system/user/tool/JSON observation/结束标记。当前Base actual runner 是 `run_swe_clean28.py`，原输出 `base_swe_v2_20261016_clean28/`；Base最终比较源为其 `corrected51_summary.json`，包含clean28全部替换＋native23保留，旧5/51历史结果不覆盖。

每题保持1CPU/4096MiB、seed0、非思考且preserve_thinking=false、65536总上下文、8192单次输出、temperature.7/top_p.8/top_k20/min_p0、presence0/repetition1。总求解1800秒、mini内1740秒＋30秒kill grace、原bash30秒、环境build1800秒、每次verifier3000秒。无summary滚动截断、额外步数上限、job自动重答或较高output cap重试。当前实际LoggedRelay每逻辑HTTP请求只发1次upstream；沿用Base相同代码与SDK禁重试，不把协议允许的最多2次误报成实际已发2次。

生成阶段和fresh replay均保留原官方verifier行为；不以省时为由关闭初评。模型错误/超时保留原轨迹与patch，继续按既有规则fresh replay；未评分/基础设施异常为null，完整51有效齐才报告主分。使用同一个 `collect_swe_final.score`函数分类，不给invalid编造0，不按新旧reward择优。

## 环境修复按独立任务子进程固定

41项glibc使用当前clean层 `SweCleanGlibcRuntimeEnvironment`；10项musl使用 `SweCleanMuslRuntimeEnvironment` 与原已验收private ABI shim。均恢复SIF原生PATH，managed Python/uv只在private位置，setup公网→solver隔离→verifier公网的冻结策略不变。

Fresh replay使用原官方 `patch_replay:PatchReplayAgent`。glibc中原Flipt/Vuls verifier使用当前 `SweCleanGlibcGoRuntimeEnvironment` 的既有Go缓存/preseed/workspace准备，musl使用 `SweCleanMuslScoreEnvironment`；缓存仅评分阶段可见，原tests不改、sumdb不关闭。每题独立leaf Python进程，musl只在自己的child PATH前加已有shim，避免并发热改native全局环境类型造成串线。

## 自动接续与资源边界

1. **用户01:22取消全部独立task-val后，已移除direct五块生成summary前置条件。** 当前父进程在01:21:19已自然越过旧门槛并开跑，不杀进程/不取消答题；其后续准入从不复查direct。未来源码/config启动只检查正式CPU资源、服务健康及剩余35分钟，不再等待任何独立validation。
2. 等root现有 `validation_direct_20261016/shared_cpu_ready.json` 为ready且cpu_consumers_finished，并实时确认目标0–9无Base scope后，最多10路各1CPU4GiB。门闩覆盖TB原队列/repair未来准入和评分scope的永久排空，不抢当前Base任务下一槽。正式Base clean28继续在124/126/127，互不占用。每题结束立即补位。
3. 727113服务实际12小时，**10月17日10:05:32 CST到期**；每次新模型任务准入检查至少剩2100秒，**09:30:32后停止新准入**、保留pending/service_expiring，在途与CPU评分自然完成。没有延长成功或隐含新GPU服务；不把服务到期算模型0分。
4. 每task的started journal/原始响应/model.patch、初评及fresh replay、outer日志、checkpoint都在专家独立目录。若进程中断，有active记录会拒绝无审计重启；已完整答案不自动再生成。

**调度差异必须披露：**专家计划10路、专属TP2/maxseq20；Base目前clean28为3路CPU，复用与Terminal共享的TP2端点，且native23来自先前时段。模型、任务、prompt、预算与评分保留，但不能把最终分差全部因果归到LoRA权重；本次不为对齐调度再重跑Base。

自有实现 `scripts/run_swe_expert_benchmark.py` 与 `configs/eval/swe249_hard51_20261016.json`；只做语法/实际配置准备核对，没有追加synthetic model smoke、全量镜像hash或新训练。启动回执与alias证据见 `analysis/source_snapshots/swe_expert_benchmark_launch_20261016.json`、`swe_expert_alias_preparation_20261016.json`。

## 23:08 最新并发10已实际加载

用户明确“并发10试试”后，旧817853在0模型请求、无active任务时退出，旧16路准备记录以`*.preparing16slots`保留。新controller**824673**、config、launch和实际experiment均一致：CPU0–9、最多10题并发，每题1CPU4GiB；service maxseq20、HLE/SAB8路、已有Base均未改。23:08复核仍为等待direct5块与永久CPU门闩、51题pending、0评分、0模型请求，alias只SWE249。

正式准入后才每30秒读取原生`/metrics`，在`serving_metrics.json/jsonl`保存实际running/waiting、KV-cache usage、preemptions等可用gauge；不发合成模型负载。若某个版本不暴露特定gauge，保留真实可用项，不填0。OOM需结合逐请求原始HTTP响应、任务日志以及服务原生输出判断，不由并发数或KV占用推测。真实HPC日志已只读确认存在：`/data/user/qinlucao/projects/apex-takehome/artifacts/validation/lora-service-727113.log`，不是preflight目录中的旧猜测路径。

当前可复核状态另存`analysis/source_snapshots/swe_expert_benchmark_execution_20261016.json`；新代码和报告交root统一Git/claud，本agent未操作索引。

## 2026-10-17 01:24：独立validation依赖已撤销，正式10题继续

用户明确停止所有独立task-val benchmark后，本agent先只读核实实际进程：原824673已经running，10个generation子进程均于01:21:20准入，不能再当作0请求等待进程重启。现有正式答题和PID全部保持；仅更改未来源码/config的启动前置，删除`direct_finished`/`direct_output`，并新增明确的`independent_task_validation_required=false`及正式启动依赖清单。没有创建/伪造direct完成summary，也未触碰Base、训练、727113服务和28089隧道。

新leaf继续读取同一专家alias、mini、环境和预算；所有实际87份upstream请求记录只有`apex-val-swe249`。旧父进程已过一次性旧门槛，其剩余41题自然滚动，无需停止或重排在途请求。保留并发10、CPU0–9、1CPU4GiB、30min/64K8K非思考和35分钟服务余量守卫；正式CPU门闩已由root写true，启动前原生scope检查为空。源SWE独立validation仍有用户取消标记，其任务/镜像准备不恢复、16–19扩容不执行。

小回执：`analysis/source_snapshots/swe_expert_direct_dependency_removed_20261017.json`，记录实际准入时间、未重启、10在途/41pending、原生请求alias计数、取消独立validation前置和其余完整预算。本agent未Git/claud。
