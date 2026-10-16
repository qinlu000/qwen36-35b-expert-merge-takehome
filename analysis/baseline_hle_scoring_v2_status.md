# HLE baseline 实时最终评分

2026-10-16 **16:15:46 CST已切为真正rolling调度**：独立新源`score_hle_baseline_v2_rolling.py`、scope `apex-hle-judge-rolling-20261016`、wrapper PID2446501，保持CPU84–85、内存8GiB、并发2。每条Judge完成立即补一个future；每30秒独立collect新generation终态，没有整批barrier。原PID2370521在stop.json禁止新准入后自然结束，旧scope inactive、旧账本在途reserved0才启动新进程，未取消／重发API。切换时保留417已Judged＋686原生无答卷零分，账¥0.54497325；原答案／逐题缓存／账本／协议均未变。切换receipt `rolling-upgrade.json`，旧stop留`stop.batch_drain_20261016.json`，新源码副本`scorer_rolling_source.py`、旧副本`scorer_source.py`并存。

输出仍为 `artifacts/runs/hle_judge_v2_20261016/`，日志`controller.log`、实时覆盖`summary.json`、逐题结果`results/`、固定输入`inputs/`、无密钥请求／原响应`requests/`和`responses/`、逐请求事务预算`budget.json`。原HLE生成PID3887939继续运行，未中断。15:58首版batch调度启动属于历史，当前使用rolling版本。

首次collector冻结1070/2500个最终结果：401份完整答卷待Judge、669份正常求解预算内无答卷按固定2500分母记零；其余1430仍待生成。随后正式Judge已HTTP200并产出有效五字段JSON，不把未完成2500的部分结果当最终成绩，`score`与`accuracy_percent`保持null。初始逐次快照和实际token／费用见 `analysis/source_snapshots/hle_judge_v2_launch_20261016.json`；实时数字应读80的summary和budget，不将启动快照当最终状态。

## 选集与评分协议

读取原 `base_hle_v2_724196_infra1/manual_retry_manifest.json`：retained821条只取原309答卷＋512真实300秒timeout；selected1679条仅取infra1同ID第一次最终结果。已收到但尚未写完final metadata的checkpoint暂不纳入；基础设施取消／传输异常不冒充正常零分。正常timeout或context overflow无预测直接保留在分母记零，不重答。

逐题首次冻结后缓存复用，不重新生成／选择答案。Judge只读取官方问题、gold与已冻结response；原图仅用于text/image分组，官方judge本身只传问题文本／gold／response。所有gold和Judge产物只在grader目录，未提供给solver或训练。

复用固定官方源码22ed3074b1e7b134bcbc09028d0ba320839b0655的原JUDGE_PROMPT，与项目冻结criteria逐字比对；原JSON wrapper五字段、temperature0、seed0、nonthinking、JSON mode、4096输出cap保留。每份相同冻结答卷最多2次请求（仅transport/schema等必要失败重试，不择优标签），缓存零新增费用。全部2500有效后按原 `round(100*correct/2500, 2)` 给完整accuracy，并分别报告text2158／image342；此前主score=null。Judge两次失败保留evaluation_invalid，不算有效零分。

## 校内真实接口、价格与预算

新正式Judge明确为校内 **DeepSeek-V4-Flash**，endpoint `https://aigc-api.hkust-gz.edu.cn/v1/chat/completions`，与先前外部deepseek-flash校准身份不同。首批实际returned model精确为`DeepSeek-V4-Flash`，fingerprint为`vllm-0.25.1-dp16-ep-35b4db70`；未暴露权重不可变revision。实际身份单独落`judge_identity.json`，后续漂移或nonthinking不被遵守即停，绝不静默混用。

80通过固定TLS转发`127.0.0.1:28443`经HPC连接学校443；stdlib TLS继续校验CA，SNI和HTTP Host均保留学校域名，无verify=False、不使用环境proxy。key只读原`/data/caoqinlu/projects/data-perception/.env`进内存，不复制／打印key，不加新GPU。

学校[API模型列表及定价](https://docs.hpc.hkust-gz.edu.cn/docs/aigc/api-model-list/)和[2026-09-02官方升级通知](https://itdid.hkust-gz.edu.cn/cn/detail-1069)均列Flash输入**¥0.75/M**、输出**¥2.25/M**；没有套用DeepSeek外部官方价或假定API免费。

每次发送前按完整UTF8文本字节上界＋1024模板余量和4096输出cap，使用线程锁＋跨进程flock保守预留；总计费预留／实际结算不超过**¥10／5000调用**。成功且有有效usage时按校内价实际token结算释放未使用预留，失败（含无法确定是否被处理）保留满额预留；缓存0新增。预算耗尽停止新Judge，但继续收集生成终态，主score不冒充完成。费用为按公布价计算，不是PBMS实账。

launch前原三data ledger仍为362／2／64行，无新增：6.896572704＋ASI校准保守0.3157632＋ASI正式0＋HLE最大10＝**17.212335904<夜间30**。共享旧data writer未统一事务锁，不能声称跨项目总账原子；本Judge独立账本有硬限，root维护总账。

## 可重放入口

在80项目目录使用已有HLE环境；再次运行复用已有逐题缓存和请求账，不重发已started请求：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 taskset -c 84,85 \
  artifacts/envs/hle/bin/python -u scripts/score_hle_baseline_v2_rolling.py \
  --project /data/caoqinlu/projects/apex-takehome \
  --retry /data/caoqinlu/projects/apex-takehome/artifacts/runs/base_hle_v2_724196_infra1 \
  --output /data/caoqinlu/projects/apex-takehome/artifacts/runs/hle_judge_v2_20261016
```

`--collect-only`仅更新真实选集／正常无答卷零分，无API；`--once`处理当前已有答卷后退出。生产rolling源码副本保存为输出目录`scorer_rolling_source.py`，后续不原地修改当前运行源码。未新增校准、模型生成、hash或额外测试，未改claud或根索引。

Latest CPU allocation is recorded in analysis/source_snapshots/baseline_cpu_rebalance_20261016.json: HLE Judge125, final collector126, cache/enable guard127, future SWE grading124, Terminal archive grading120-123. HTTP concurrency and scoring budgets remain unchanged.
