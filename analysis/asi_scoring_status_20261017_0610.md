# ASI科学评分只读状态（06:10文件标签）

实际采集为2026-10-17 **06:09:41–06:14:26 Asia/Shanghai**。专家评分正常推进：先为94/240，06:14:26已增至 **106/240、pending134、scorer error0**。完整标记仍false，主分数为null；这不是完整分数快照。[精简原始证据](source_snapshots/asi_scoring_status_20261017_0610.json)

此前94停留约30分钟是合法inflight：`computer_science.max3sat_assignment_optimization__seed31415__b3.grading1`在scope `ai4sci-submission-b343ee5014ec.scope`运行。程序PID888599固定CPU92，两次约43.75秒采样增加43.88 CPU秒，处于持续计算。原任务task_eval固定**1800秒、1CPU、3GiB、10秒终止宽限**，MemoryMax实核3GiB，当前RSS约44MiB、OOM/oom_kill均0。它后来按原预算自然返回，PID888356/888599均已退出，进度随即增加。7200秒是外层整个科学评分条件兜底；此前约07:43的时间只是该兜底参考，不是此程序必须占用两小时，也不是整体评分ETA。TSP原生提交另有3600秒、同1CPU/3GiB预算。

pipeline3237024在do_wait等待scorer837390；/proc/locks实核92–95全局FLOCK由3237024持有，scoring/.run.lock由837390持有。评分workers=1，因此一个长条件使后续队列串行等待。主日志asi_scoring.log仍0字节，与源码只在最终print的行为一致，不能单凭空日志判断卡死。pipeline/state.json仍写旧asi_generation，但实际子进程、条件报告和科学scope优先于这个过期标签。没有证据表明28090释放造成评分工程阻塞；本轮未探测/重建已故意释放的专家GPU服务。

## 成本journal的真实位置

实际执行的 `scoring/runtime/scripts/asi_score_transport.py:45,57–76`确认root提供的路径就是正确位置：

```text
artifacts/eval/asi128_asi240_20261017/scoring/judge_calls.jsonl
```

它由第一条journal事件懒创建。截至本次检查仍不存在；`judge_calls/`已有95个condition-attempt目录，06:11时其中request/response文件0个，94个已完成结果中也未见嵌入raw/parsed Judge响应；未见budget_exhausted、identity_drift或token_bound_exceeded marker。该证据与尚未进入LLM Judge通路相容，但**缺journal不能计为0calls或0元**，成本字段保留unknown/not_yet_materialized。本次没有发现另一个实际使用的替代API账本，不把不存在的文件改称可用账本。

当前能纳资源账本的实际执行来源是已存在的 `scoring/scoring_config.json` 和 `scoring/invocations.jsonl`：paid模式、https://api.deepseek.com、全局396调用/20元、workers1；它们证明配置/执行，不证明已发生费用。未来journal产生后，用started的id/condition/request_sha256/occurrence、max_tokens/input_token_bound/reserved_cny/at_unix记占用；completed的usage/observed_ceiling_cny、failed的error_class，以及cache_reused分开记账。observed_ceiling_cny是token价格上界，不是提供商发票。原源码在HTTP前、同一a+文件的独占flock里核全体started/reserved总量并append/flush，因此预算不是每worker各20元；失败调用的reservation也保留。

## AVG ASI gate与未来workers4

AVG ASI driver4143547正常等待复用28095/727856：expert generation_cpu_ready=true，当前96–127无生产scope，AVG ASI目录尚未产生、0正式准入。它在等AVG HLE完整2500及原generator退出、consumer marker和metrics排空。driver显示的saved202来自滞后的summary.saved，**不是当前全目录生成进度**；root在06:14刷新得到实际有效2186条，本agent不重复扫描。原generator4076145仍活跃，尚无consumer-finished marker，完整2500 gate未满足。它不需要等专家评分结束才生成；只有后续AVG科学评分要等待专家all_cpu marker并取得同92–95全局lease。没有发现额外的专家评分gate挡住AVG生成。该driver截止为2026-10-18 02:20本地时间，不申请新GPU。

对root提出的**仅尚未启动AVG评分workers1→4**，本轮最终建议**保持1**，当前专家pool不动。API/显式submission并发机制已核清，但root要求其他科学子程序CPU隔离不明确时不启用4；host侧custom/reference计算尚无逐condition独占CPU/内存隔离证明。`score_asi_baseline_v2.py:70–90,306–314`给每条件独立spawn进程；`asi_score_submission.py:36–47`已有同输出根的per-CPU flock，再由helper的offset/继承affinity filter限制到池内CPU；已核60个selected task目录，显式TSP/MAXSAT contracts和SDK默认均1CPU/3GiB，未找到这些合同的非1CPU覆盖。四个这类提交scope最多12GiB，API396calls/20元由同一journal锁共享，不能乘4。

内存边界需保留：科学scorer自己的可信参考计算、部分custom subprocess在host worker中，继承92–95 affinity，但并不全受提交scope的3GiB cap；静态review不能证明每个host参考计算都有固定内存峰值。当时host MemAvailable约1.84TiB，四worker没有明显容量阻塞，仍不能把它宣传为严格12GiB总峰值。单index lease也不能泛化到未来多CPU spec；若新增这种合同，须一次预留足够CPU bundle。提高并发保留原每题限时，资源争用可能改变walltime，不据此声称数值完全一致。

因此本轮不改评分命令或merged配置，未来AVG workers继续1，也不扩大调研。若未来先明确host侧逐condition资源隔离，再考虑最小代码点：`scripts/run_direct_formal_pipeline.py`评分命令的`--workers`仅在profile=merged时取4，expert仍1，并在merged配置/实际invocations.jsonl记录4；原7200/396/20、条件集合、答卷及cached records、全局92–95锁和完成marker均保持。不要另开与当前预排队重叠的grader。本轮**只读评估，未修改任何生产文件、pool、进程、预算或marker，未调用模型/Judge**。
