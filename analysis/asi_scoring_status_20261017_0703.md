# ASI只读状态：07:03采集

实际状态采集为2026-10-17 07:03:09–07:04:25 Asia/Shanghai；后续import诊断另见下方链接。[小收据](source_snapshots/asi_scoring_status_20261017_0703.json)

专家科学评分已结束，pipeline3237024和scorer837390均不存在。报告是**239 completed + 1 evaluation_invalid、pending0、complete=false、主分null**，不能称240条有效评分。唯一异常是`electrical_engineering.cmos_opamp_design__seed31415__b1`：两个native scorer发生`ModuleNotFoundError: No module named tasks`，不是Judge parse失败。原结果仍保留。

generation CPU marker为05:38:35 finished/240/pool shutdown/scopes[]；all-CPU marker于06:21:42写出，grader exit0、process finished、scopes[]，同时如实记录grader_complete=false/error1。该marker证明CPU资源排空，不代表分数完整。92–95全局锁当前无持有人、无专家科学程序scope。原program预算维持MAXSAT1800秒/TSP3600秒、1CPU/3GiB；评分条件外层7200秒、HTTP90秒。专家GPU已故意释放，不探测失效旧route、不重建服务。

API journal现已生成，真实来源为`artifacts/eval/asi128_asi240_20261017/scoring/judge_calls.jsonl`：15 started、15 completed、0 failed、0 unsettled。预留上界0.1431576元，completed token价格上界合计**0.0380304元**；prompt13,482、completion591、cache-hit7,424/cache-miss6,058 tokens。它是观测价格上界，不是提供商发票；与之前missing状态分开记录，不再当未知路径，也不输出请求/响应正文。总预算仍396次/20元。

AVG ASI已于06:38:25独立接续：coordinator1126014、generator1126055分别持自己的controller lock；复用既有727856/28095，alias`apex-avg64`，0新GPU。07:03:02进度18/240、8 active，声明8组4CPU覆盖96–127；实际采到1个程序scope在124–127、MemoryMax8GiB，未侵入92–95。8个逻辑inflight并不要求同刻存在8个程序scope，模型API阶段也是合法consumer。生成/全CPU完成marker尚不存在，评分尚未启动；源码仍明确workers1，不改在途或预排池。

TIES服务728016的2500生成已完成，model-consumer marker为true，controller处于generation_released_scoring_external。sacct为CANCELLED by14348，06:10:55结束，squeue无该job；这是正常释放后的外部评分状态，无重建需求。当前Slurm可见4个普通服务727912/727913/727856/727857，共8GPU。

针对CMOS异常，本轮仅做CPU import RED/GREEN、原输出字节和cache身份核验，**未评分、未执行候选、未发API、未安装生产环境修复**。恢复方案及未来AVG评分环境注入方案见[import recovery准备](asi_cmos_import_recovery_prep_20261017.md)。root结论保持未来AVG评分workers1。
