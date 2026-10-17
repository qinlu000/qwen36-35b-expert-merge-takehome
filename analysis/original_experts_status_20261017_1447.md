# 原四专家目标benchmark结果：2026-10-17 14:46

本轮按用户要求手动核对。三个原专家已有各自目标项的完整结果，Terminal尚未完整；不是四专家×四benchmark全矩阵。新LR候选单独记录，不替换原SWE249。

|原专家|目标项有效覆盖|原专家完整成绩|对应Base完整成绩|
|---|---:|---:|---:|
|SWE249|51/51|0/51 = 0%|10/51 = 19.607843%|
|HLE250|2500/2500，含342图|173/2500 = 6.92%|99/2500 = 3.96%|
|ASI128|240/240，60任务×4条件|0.378991%原生归一化得分|1.570988%|
|Terminal250|285/445有效，另7异常、153待完成|null，尚无完整五次均值/标准差|strict442/445另3invalid，完整分null|

ASI不是成功任务比例：专家原生得分总90.95793165941141/24000，Base377.03721765801566/24000。固定audited结果只读核验，未重复一次性collector。HLE/ASI使用替代Judge，ASI为public/local协议、非Portal认证；历史服务/排队差异仍需披露，HLE分差不能全归于训练。SWE含已批准的原答卷grade-only恢复及完整官方报告审计，旧raw invalid保持。

Terminal当前已观察36次成功，仅用于逐项账本，不用36/285冒充完整89×5结果。7异常保持null，没有新恢复/重试/安装或联网；153含在途和未完成项，不按缺失填0。单独审计预算视图的Base445/445、20.224719%沿用既有显式三项预算规则，不与专家strict混报；专家在两视图均285有效、完整分null。

本轮按顺序刷新collect_swe249_audited→collect_avg64_swe_audited→collect_terminal250_audited，再运行summarize_experiment及terminal_budget_policy，保留[strict与独立预算双视图](source_snapshots/formal_aggregation_20261017_1447.json)。实际strict时点06:45:58UTC/14:45:58CST，独立预算06:46:01UTC；source issues均空。AVG64另为SWE51完整7.843137%、HLE2500完整4.68%、ASI94/240有效、Terminal263/445有效另6异常/176待完成，四项macro仍null。以上不恢复自动化，不进行模型/Judge调用或答卷生成。

## 本轮顺带完成此前授权的SWE低LR训练验收

728713已COMPLETED/0:0，Slurm耗时00:57:52，GPU4自然释放；唯一final为`artifacts/runs/swe-lr2e5-max32k-728713/training/checkpoint-128`，global_step128/epoch1.0。适配器84,760,832字节、620个FP32 A/B tensor，r16/alpha32，最终summary passed=true；仅读小header，不做权重hash/forward或loss选模。独立TensorBoard与原生log都保留。新候选没有task benchmark成绩，不称效果已改善，不自动合版或发布。

[训练完成收据](source_snapshots/swe_lr2e5_max32k_completed_20261017.json)记录实际sacct/squeue和产物；当前只有原727912/727913两个TP2共4H100，已释放训练卡不自动重建。此后训练结果的质量必须由任务评测另证，原四专家结果和主AVG64保持。
