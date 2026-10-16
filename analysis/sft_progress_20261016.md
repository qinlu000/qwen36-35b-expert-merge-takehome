# SFT 进度（2026-10-16，21:08训练日志／21:12调度复核）

用户澄清需要更多现成 HLE 回答，随后授权继续。此前退回500条是执行方理解过窄；现在已实际完成HLE **2000 train /100原val**，没有恢复教师API。原500数据与725704权重保留历史，不作为新2k已训练的证据。

| 模型 | 导出train→实际加载 / val加载 | 当前实证状态 |
|---|---:|---|
| SWE / 仓库修复 | 2000→**1993** /87 | 726335，4H100，19:55完成249步；best checkpoint249，val loss0.31768048 |
| Terminal / 终端操作 | 2000→待确认 /准备42 | 726665，4H100，21:10解除旧依赖；21:12仍PENDING(Resources)，尚无新native run |
| HLE / 学术推理 | 2000→2000 /100 | 726664，2H100，RUNNING，189/250步；best checkpoint16，val loss2.00219154 |
| ASI / 科研编程 | 1073→1073 /20 | 726336已完成134步，51分36秒；best checkpoint128，val loss0.58268344 |
| Mixed对照 | 7073→**7066** /249 | 726666，4H100，RUNNING，128/883步；best checkpoint64，val loss1.21849561 |

21:08原生Trainer估计：HLE剩约23分钟，Mixed剩约6小时10分钟；这会随批次长度、验证和保存变化，不是完成承诺。Terminal当前调度器暂估10/17 01:11分配，尚未获卡，不能据此推算训练完成时间。HLE最新一次验证（176步）loss3.48262358高于早期最佳，保留早期checkpoint，随后按独立val选择；不能将此loss直接当HLE准确率。

原始快照：[训练状态](source_snapshots/sft_status_latest_20261016.json)、[Terminal依赖释放与资源排队](source_snapshots/terminal_scheduling_20261016_2110.json)。

本轮首次按native loader复核：SWE7条中途tool→user纠正反馈触发Swift `response_role:user`，被整条过滤；Mixed同7条也过滤。不是超长或截断。导出文件保持2000/7073，下文该数均为导出量；实际加载数与7条来源定位已修正，见[训练数据汇报表](training_data_report_20261016.md)。SWE2k实际run路径为`swe2k-sft-r16-726335`。加载数不等于每步batch的逐条曝光计数。

四专家均从同一Base独立SFT；ASI采用direct_llm输出程序。Mixed使用相同四份分区各一次，不参与合版。验证loss不是四项benchmark成绩。

## HLE现成2k已完成

路径`artifacts/data/candidates/hle_existing_2k_20261016/swift_ready`，Mac/80/HPC均有完整导出。组成：817条Math-v4 High、722条此前已接受的High回答、201条Science-v2 V4-Pro final、98条筛选后跨学科final（82 V4-Pro /16 GLM-5.1）、162条MMLU-Pro公开参考短答案。

八类与原2k配额完全相同：Math817 / Biology224 / CS193 / Other186 / Physics184 / Humanities175 / Chemistry132 / Engineering89。人文现成完整解答仅补得11条，加原High2条后缺162，用原已分train并排除正式HLE/原val的题池gold做短答案监督，明确不冒称完整推理轨迹或强模型生成。没有用弱模型编写解释。

完整序列合计 **1,125,593 tokens**、max4043；assistant正文793188、max3977。未截断，不沿用旧2K筛选；训练窗口仍65536、单回复预算8192、学生非思考。原100val三个文件逐字节保持；未披露effort的公开V4/GLM回答不补写High。

详见[执行记录](hle_existing_2k_execution_20261016.md)、[Math/Science](hle_existing_math_science_20261016.md)、[跨学科](hle_existing_broad_sources_20261016.md)。类别相同不等于难度匹配，题族/来源追溯不完整和无独立gold的局限均保留。

## Terminal验证OOM与接续

原726345完成16/250训练步后，首次验证在普通CE申请21.06GiB时OOM，未保存checkpoint。Liger只在training默认跳过全词表logits，eval走另一分支。最小worker包装让带标签eval使用同一官方FLCE；CPU实际Liger前端分支红→绿，与dense CE在causal shift、-100 mask、归一化下差分一致。

数据、完整64K序列、全验证集、global8与r16不变；未修改安装包、正在运行的SWE或Base评测。新726665从Base重训同2000条。**Mixed已用同一修复完成7次真实GPU全量验证，其249条val包含全部42条Terminal长轨迹；修复已有实际GPU通过证据。Terminal独立job的首次验证仍待运行。** [修复证据](terminal_eval_oom_fix_20261016.md)

## Mixed、资源与固定配方

原726346在PENDING/0运行时先hold，确认未读取旧5573后取消。新目录`artifacts/data/candidates/mixed_existing_hle2k_20261016`已在HPC实数7073/249：HLE2000→SWE2000→Terminal2000→ASI1073，各一次；val100/87/42/20。旧Mixed目录保留。

HLE双卡、Mixed四卡（SWE完成后接续）。Terminal原依赖`afterany:726664:725705`用于覆盖此前Base服务迁移峰值；21:10实查本题运行GPU仅10张（HLE2＋Mixed4＋Base两个TP2共4），加Terminal4为14≤16，故只清除Terminal自有job旧依赖，21:12已核`Dependency=(null)`、因Resources等待。未操作Base或其他项目作业。

共用r16/alpha32/dropout.05、global8、LR1e-4、weight_decay.1、一epoch、BF16、原loss mask及完整样本策略。新HLE与Mixed不覆盖在训SWE数据；旧High生成STOP_ADMISSION与已停止的后续保持，无新教师API、数据hash审计或app自动化。

19:24启动修正：初次HLE726647获得调度后因集群包装器误把独立`--data-dir`目录参数当sandbox而0步失败，未加载模型；CPU原样解析条件已确认改用`--data-dir=...`通过。现HLE726664、Terminal726665、Mixed726666均用equals参数写法重提，旧0步后续726648/726649取消，数据与预算未变。HLE仍排队，GPU真实optimizer/eval尚待实证；详见执行记录和重提交回执。

以上为19:24启动历史；21:08 HLE与Mixed已真实训练，最新状态见上表。Mixed同修复全val已有7次GPU通过记录，Terminal独立job仍待获卡。

提示对齐优先级已复核：当前HLE/ASI差异不是已证实的训练/评分阻塞，不为纯文案一致性改当前数据或重训。接下来完成Terminal、HLE、Mixed，训练后用既有独立val检查抽取/工具/代码输出及任务表现，再做专家合版与对照评测。[必要性结论](sft_harness_alignment_20261016.md)

## Base评测只读进度（21:09，另一会话负责执行）

- ASI：240/240完成，本地协议mean_percent 1.5709884%，scorer_error=0。
- SWE：旧51题有28题生成受PATH/Python环境影响，旧分不作为干净最终比较；固定28题独立重跑已3/28有效评分，3在途、22待准入，corrected51最终分仍null。
- HLE：2500题均有生成终态，2499/2500有效评分；1题评分基础设施异常，完整主分仍null。
- Terminal：184/445有效，30在途、197待准入、34基础设施或未评分项；五组运行均值/标准差尚未齐。

本轮仅只读以上Base状态；未改Base作业、评分规则或服务。专家正式评测、合版和Mixed效果对比尚未完成。
