# 正式结果统一汇总与配对 bootstrap

**任务对照补记（2026-10-17）**：loss只作训练诊断，不是val标准。新增固定 Mixed883 与 AVG16 的 HLE2500实际任务对照，路径在同一显式配置中；每个视图观测总数由9708增至14708。额外报告 AVG64−Mixed883 与 AVG64−AVG16 的同ID HLE差值和配对CI。两项对照只测HLE，不产生四项宏平均；主比较仍是冻结AVG64对Base。没有根据正式反馈选择checkpoint或合版配方。下文六模型/9708是原快照范围，不能覆盖此补记。

下文初次运行数值是02:29–02:30保存快照；03:25更新与Terminal双视图见文末补记及[最新执行说明](terminal_budget_aggregation_20261017.md)。默认strict字段原义保持。

实现：[summarize_experiment.py](../scripts/summarize_experiment.py)。显式路径清单：[final_results_20261017.json](../configs/eval/final_results_20261017.json)。本脚本独立读取原 owner 输出，没有修改 Base collector、任何答卷选择、队列或评分。

已在80实际运行，输出为 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/final_aggregation_20261017/`：

- `summary.json`：六模型矩阵、完整性、coverage、配对覆盖、主分、逐项/宏平均区间、来源全路径及协议限制。
- `observations.jsonl`：全部固定范围的9708个观测，包括 missing/pending/invalid；每条保留 ID、任务簇、seed/condition、有效分子/分母和原始评分/生成结果路径。
- `matrix.csv`、`report.md`：可直接用于后续表格和报告。未完整分数是空值/null；专家非目标项明确未评。

运行命令（现有 ASI Python 环境含 NumPy；Harbor环境没有 NumPy，没有为此安装或修改环境）：

```bash
cd /data/caoqinlu/projects/apex-takehome
artifacts/envs/asi-py312/bin/python scripts/summarize_experiment.py \
  --project "$PWD" --config configs/eval/final_results_20261017.json \
  --output artifacts/eval/final_aggregation_20261017
```

本次一次性读取和CPU统计绑定空闲 CPU80 执行，没有提交 GPU 作业或调用模型/Judge API。脚本不轮询、不修复原结果；未来 owner 更新后重跑即可，路径变更只需修改清单。

## 固定口径

共同任务 ID 来自原冻结协议 manifest，强制 SWE51、HLE2500（图像342）、ASI60项目×b1–b4、TB89任务×seed0–4。SWE、HLE、TB均以有效0/1评分；ASI保留原生 `final_score/max_score`，当前每条件 max_score100，主项为 `100*sum(final_score)/sum(max_score)`，不是仅挑有分数项目的平均，也没有将部分分二值化。

只有完整且来源无冲突时才输出单项主分：全部固定键有效、无重复/额外 ID、原 owner `complete=true`，且逐条复算主分与 owner 完整主分一致。ASI scorer error 也会阻止完整主分。任意缺失、pending、invalid均不填0，也不剔除后计算主分或区间。有效模型错误、原生无答案/预算结束的有效0分仍保留为 wrong；ASI单列有效零分、部分分和满分，不能把零分误叫评分失败。

Base和AVG64的四项主分齐全才计算 **(SWE%+HLE%+ASI%+TB%)/4**。四个目标专家各自仅有目标项，不把不同专家拼成一个假想单模型的宏平均。目标专家与Base可比较完整目标单项；AVG64–Base宏平均差只有四项均完整配对才出现。

TB逐seed固定89题；完整seed才给该轮百分数，完整五轮才给五轮mean和sample SD（ddof=1）。主分是五轮均值，不是pass@5；不把445次当作445个独立任务。

## 配对 bootstrap

冻结设置为 **10000次、master seed20261015、95% percentile区间**。SWE按51任务 ID、HLE按2500问题 ID，TB按89任务簇保留簇内全部五seed，ASI按60项目簇保留簇内全部四condition。

每个benchmark采用 `SeedSequence(20261015).spawn(4)` 的独立子流，顺序固定为SWE/HLE/ASI/TB，PCG64。每个replicate的 ID 索引同时用于该benchmark所有完整模型，所以候选–Base使用同一采样；不能用完整观测交集补成配对结果。各项差值仍为百分点，宏平均差区间来自同一replicate内四项差值的等权平均，不是四个区间端点的平均。实际 NumPy版本与随机数方法写入 `summary.json`；80 本次为 NumPy2.5.4。

这些区间仅对固定任务、预算、已保存输出/评分解释，不能去除原有服务并发、资源、Judge替换和运行环境差异。完整单项可单独报告其区间，未完成的整体比较仍为null。

## 实际来源与适配边界

所有下列相对路径都以80项目根 `/data/caoqinlu/projects/apex-takehome/` 为根，实际结果内记录绝对路径；清单不做自动搜索或“取最高奖励”。

| 数据 | 分数权威来源 | 适配方式 |
|---|---|---|
| Base SWE | `artifacts/eval/base_swe_v2_20261016_clean28/corrected51_summary.json` | `tasks`，同时兼容 retained native23的status字段与clean28的invalid_reason字段；不用历史5/51 |
| Base HLE | `artifacts/runs/hle_judge_v2_20261016/{summary.json,results/*.json}` | 只读冻结评分结果；`judged/native_no_answer`且correct为bool才有效 |
| Base ASI | `artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json` | `results`原生分子/分母，保留公开local与替代Judge标记 |
| Base TB | `artifacts/results/base-terminal-independent-repair32-20261016/corrected445_summary.json` | 只有canonical `accepted_first_valid`供应分数；旁边187条repair checkpoint仅补未接受键的失败状态，不新增答案或分数 |
| SWE249专家 / AVG64 SWE | `artifacts/eval/{swe249_hard51_20261016,avg64_swe_hard51_20261017}/summary.json` | `tasks`中的reward/invalid_reason，原始replay路径保留 |
| HLE250专家 / AVG64 HLE | `artifacts/eval/{hle250_hle2500_20261017,avg64_hle2500_20261017}/scoring/{summary.json,results/*.json}` | 与Base HLE相同逐题评分schema |
| ASI128专家 / AVG64 ASI | `artifacts/eval/{asi128_asi240_20261017,avg64_asi240_20261017}/scoring/local_score_seed31415.json` | 生产agent已确认与Base相同native `results` schema；当前尚无评分文件，不臆造结果 |
| Terminal250专家 / AVG64 TB | `artifacts/eval/{terminal250_full445_20261017,avg64_terminal_full445_20261017}/summary.json` | `scores`与pending/active，固定task/seed键；valid=false或缺失原生result单列invalid |

HLE Base已只读核对原 `infra1/manual_retry_manifest.json` 和2500份冻结inputs：**821份原始保留结果 + 1679份原infra1 selection**，全部ID、选择引用与评分source_result一一匹配，未发现新的修复selection。见 [HLE来源审计](source_snapshots/final_aggregation_hle_source_audit_20261017.json)。没有自行把其他目录的答案覆盖进来。

适配不确定性：专家/AVG64 HLE与ASI生产格式已由其owner确认，但尚未产生真实评分文件，本轮只能验证缺失状态；未来出现不同schema会显式报告source_schema_error并阻止主分，不猜测转换。TB Base canonical只提供accepted键；当前9个未评分键能由原repair状态源识别为invalid，未来缺失且无状态信息的键保留missing。不能据owner总数把未知ID随意分配成0分或已知invalid。任何新的canonical/overlay需由原owner确认并修改清单，算法不主动扫描寻找候选。

## 当前真实结果与验证

本次完整复算的Base coverage：**SWE46/51（5invalid）、HLE2499/2500（1invalid）、ASI240/240、TB436/445（9invalid）**。完整ASI单项为 **377.03721765801566/24000×100 = 1.5709884069%**；HLE2400份有效wrong与1份评分invalid分开，TB347份有效wrong与9份invalid分开。SWE专家最后一次汇总为19/51有效，其余专家及AVG64评分尚未就绪。

因此所有模型的四项宏平均、AVG64–Base宏平均提升及其区间均为 **null**，没有任何3pp/5pp达标声明。实际时间、逐项coverage和来源见 [执行快照](source_snapshots/final_aggregation_execution_20261017.json)，而不是把此文快照当持续状态。

必要人工金标准脚本：[check_experiment_aggregation.py](../scripts/check_experiment_aggregation.py)，本机与80都通过，无模型/API调用：

- 0分wrong与评分invalid分开；missing、重复/额外ID、owner未完成或主分不一致均阻止主分。
- 同ID结果物理顺序反转，配对差及区间仍严格为0。
- 两个TB任务各保留五seed的配对差，精确采样分布为{-100,0,100}pp，概率{1/4,1/2,1/4}；10000次区间为[-100,100]pp。
- TB五轮[0,50,100,50,0]%：mean40%，sample SD=`sqrt(1750)=41.8330013267`个百分点。
- ASI八个condition原生分子275、分母800，结果34.375%；每项目四层的簇分母均400。
- 四项[0,100,0,0]%宏平均25%，不按题数加权；任何项null则宏平均null。

见 [人工算例回执](source_snapshots/final_aggregation_manual_examples_20261017.json)。本轮无Git操作、无 `claud.md` 修改。

## Base未评分项的只读附记

02:30:33 CST瞬时核查：TB9个未接受键中，`pytorch-model-cli` seed3/4为VerifierTimeoutError；`train-fasttext` seed3/4为原AgentTimeout且pytest wrapper写零但无测试执行证据；其余5键是`feal-differential-cryptanalysis` seed0/4、`make-doom-for-mips` seed3、`sam-cell-seg` seed3、`model-extraction-relu-logits` seed4，原exception为AgentTimeout且canonical未有有效评分。这是“原预算结束后仍无有效原生判分”，不能仅凭AgentTimeout自动计模型0分。9个键均有保存状态receipt，但文件存在不证明能恢复任务的实时服务状态。SWE5项分别是NodeBB verifier超时、flipt公开Go依赖超时、vuls replay RemoteProtocolError、teleport RewardFileNotFoundError、protonmail empty_tests_requires_audit。HLE唯一invalid为`672ecc6946f619ca9b0495c5`，两次Judge均HTTP200但finish_reason=length且内容不是有效JSON，已用完原两次尝试。

同次进程名审计仅发现原 `collect_baseline_final_v2.py`（PID4181090）；未发现匹配followon/regrade/clean-replay/HLE-scoring脚本的在途修复进程。这不能排除其他chat尚未启动的计划。本轮只读原canonical与错误工件，没有叠加新答案、修改Base、补答卷或启动评分。

## 03:25来源与统计更新

Base owner仅补评分后，配置明确读取`base-gap-completion-20261017/swe51_summary.json`及`terminal_strict_summary.json`；HLE原source已2500/2500有效、99正确、3.96%。SWE专家改读[独立四项原生0审计汇总](swe249_audited_summary_20261017.md)，每次统计前先运行其只读collector刷新，原答案与原始invalid保持。

默认strict本次为Base SWE50/51、HLE2500/2500、ASI240/240、TB442/445；SWE专家41/51，Terminal专家/AVG64分别15/14份有效，所有宏平均与模型配对差仍null。

显式增加`--terminal-budget-policy configs/eval/terminal_budget_policy_20261017.json`会在同一输出下另写`audited_terminal_budget/`。严格结果及原生reward不变；平行视图只对已独立审核、精确路径匹配且真实测试后900秒计算超时的结果派生预算0，未准入或环境故障不补分。Base平行TB为442 native＋3 derived＝445，mean20.224719%、五seed sample SD2.635065个百分点；89任务簇95%CI[13.033708%,27.865169%]。该政策对所有比较模型一致，Base audit不能迁给专家同名task。其他三项仍需完整，预算宏平均与配对CI才可生成。

实现复用原固定ID和10000次paired bootstrap；新人工算例验证计算超时/环境错误/未准入分离、exact path与模型不符拒绝、strict原dict和文件不变、完整445和空active/pending、89簇保留五seed及缺项阻止macro。[双视图执行收据](source_snapshots/terminal_budget_aggregation_execution_20261017.json)和[人工算例](source_snapshots/terminal_budget_aggregation_cpu_20261017.json)均已保存，无新模型/API/GPU或任务评测调用。
