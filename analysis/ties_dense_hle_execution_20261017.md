# Dense TIES HLE正式准入收据

root已审阅并于2026-10-17 05:33:26 CST在80唯一持久启动controller **782323/startticks868543002**，host metadata affinity10–11。launch receipt/stdout位于`artifacts/eval/ties_dense_hle_control_launch_20261017/`；真实controller state/claim/submit-intent位于`artifacts/eval/ties_dense_hle2500_20261017/controller/`。本owner只读跟进，无重提、重启、附加synthetic或模型调用。

实际普通TP2 job **728016**，ACD1-19，acd_u/Nice1000，16CPU/128GiB/2GPU；05:33:34开始、09:33:34结束，STOP_ADMISSION计划09:28:34，保留最后300秒自然排空。提交时项目10GPU，新增后12；随后实际squeue/WorkDir核对仍12GPU。独立bridge28097→ACD1-19:18006，tunnel supervisor782811；旧controls/watcher、AVG28095→ASI均未改。

实际服务启动记录确认完整HF目录`artifacts/merges/four-experts-ties-dense-v1-20261017/`、真实alias apex-ties-dense、LoRA disabled、TP2/BF16/65536/8192/maxseq50、nonthinking。完整export guard通过310目标/735非目标bitwise/1045个BF16 tensor/26shard、source revision正确、SVD0；服务与controller admission包含BF16 effective-update偏差**10.5310%**，不称数值无损。

05:38:31开始实载，26/26片于05:40:41结束（loader记录129.42秒）；随后encoder/KV warmup，05:42进入API启动。processor日志中的min_frames/max_frames文档检查未造成中止，后续模型成功加载，无需重启/改参数。未将任何单worker的load内存当作所有GPU的实测peak。

唯一synthetic intent在05:42:39落盘，05:43:19.420验收完成，恰好2个模型请求：text prompt22/completion11、image prompt87/completion10，token计数/真实alias/vision/schema/非空assistant/nonthinking均通过。`semantic_correctness_used_for_admission=false`，未因red/42是否答对选择准入；raw输出保留于controller的acceptance-text.response.json和acceptance-image.response.json。

正式generator **887555**、外部Judge **887556** 于05:43:19启动。首个保存答卷ID`668825f80a642802bdfeadfa`：05:43:20.818准入、05:43:24.603结束，tokenize及chat均HTTP200，prompt125/completion10，真实alias正确、无reasoning字段；未复制题目或答案原文到本收据。

05:44:12 CST安全快照：

|范围|已保存终态|已准入|在途|备注|
|---|---:|---:|---:|---|
|全局questions/started文件|112|162|50|112均completed，含8个image结果|
|本会话checkpoint|112|162|50|独立读取，不能用它代替全局ledger|

native running50/waiting0。Judge当时14有效、0invalid、15个已预留调用、账面含reservation费用¥0.0206055；complete=false，不报告最终score。固定2500/342图、原protocol/sampling、50并发/64K8K/300秒均保留；仅HLE方法对照，不称四项macro或据结果选主模型。

评分沿原20CNY/5000calls/2workers。后续若符合原两次200+length且parse失败，使用事先披露的固定名单2+1 compact格式恢复，独立recovery reservation/calls计入同模型总cap；本轮没有自动恢复或依reward补请求。GPU仅由本controller在generator退出、实际drain后释放本job，外部Judge可继续。

安全详细[snapshot](source_snapshots/ties_dense_hle_execution_20261017.json)记录实际PID/startticks、资源/guard、两个synthetic协议收据、首个正式结果元信息、全局与session计数及评分账面；无question/gold/solver文本或凭据。快照非事务性，不把后续增长当作同一时刻。此执行跟进仅新增本文件与该snapshot，未改运行代码/配置/路由。
