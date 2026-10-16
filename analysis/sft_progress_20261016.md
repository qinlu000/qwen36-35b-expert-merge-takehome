# SFT 进度（2026-10-16，19:24 CST）

用户澄清需要更多现成 HLE 回答，随后授权继续。此前退回500条是执行方理解过窄；现在已实际完成HLE **2000 train /100原val**，没有恢复教师API。原500数据与725704权重保留历史，不作为新2k已训练的证据。

| 模型 | train / val | 当前实证状态 |
|---|---:|---|
| SWE / 仓库修复 | 2000 /87 | 726335，4H100，RUNNING，155/249步，best checkpoint144，val loss0.32061967 |
| Terminal / 终端操作 | 2000 /42 | 新726665，4H100，等待HLE726664及旧Base B服务725705自然结束 |
| HLE / 学术推理 | **2000 /100** | 726664，2H100，PENDING(Priority)，尚无optimizer步 |
| ASI / 科研编程 | 1073 /20 | 726336已完成134步，51分36秒；best checkpoint128，val loss0.58268344 |
| Mixed对照 | **7073 /249** | 新726666，4H100，afterok:726335；新并集已同步HPC，尚未训练 |

四专家均从同一Base独立SFT；ASI采用direct_llm输出程序。Mixed使用相同四份分区各一次，不参与合版。验证loss不是四项benchmark成绩。

## HLE现成2k已完成

路径`artifacts/data/candidates/hle_existing_2k_20261016/swift_ready`，Mac/80/HPC均有完整导出。组成：817条Math-v4 High、722条此前已接受的High回答、201条Science-v2 V4-Pro final、98条筛选后跨学科final（82 V4-Pro /16 GLM-5.1）、162条MMLU-Pro公开参考短答案。

八类与原2k配额完全相同：Math817 / Biology224 / CS193 / Other186 / Physics184 / Humanities175 / Chemistry132 / Engineering89。人文现成完整解答仅补得11条，加原High2条后缺162，用原已分train并排除正式HLE/原val的题池gold做短答案监督，明确不冒称完整推理轨迹或强模型生成。没有用弱模型编写解释。

完整序列合计 **1,125,593 tokens**、max4043；assistant正文793188、max3977。未截断，不沿用旧2K筛选；训练窗口仍65536、单回复预算8192、学生非思考。原100val三个文件逐字节保持；未披露effort的公开V4/GLM回答不补写High。

详见[执行记录](hle_existing_2k_execution_20261016.md)、[Math/Science](hle_existing_math_science_20261016.md)、[跨学科](hle_existing_broad_sources_20261016.md)。类别相同不等于难度匹配，题族/来源追溯不完整和无独立gold的局限均保留。

## Terminal验证OOM与接续

原726345完成16/250训练步后，首次验证在普通CE申请21.06GiB时OOM，未保存checkpoint。Liger只在training默认跳过全词表logits，eval走另一分支。最小worker包装让带标签eval使用同一官方FLCE；CPU实际Liger前端分支红→绿，与dense CE在causal shift、-100 mask、归一化下差分一致。

数据、完整64K序列、全验证集、global8与r16不变；未修改安装包、正在运行的SWE或Base评测。新726665从Base重训同2000条。**真实GPU首次全量验证尚待完成，不能只凭CPU检查称OOM已解除。** [修复证据](terminal_eval_oom_fix_20261016.md)

## Mixed、资源与固定配方

原726346在PENDING/0运行时先hold，确认未读取旧5573后取消。新目录`artifacts/data/candidates/mixed_existing_hle2k_20261016`已在HPC实数7073/249：HLE2000→SWE2000→Terminal2000→ASI1073，各一次；val100/87/42/20。旧Mixed目录保留。

HLE双卡；Terminal四卡真实依赖`afterany:726664:725705`，只等待旧Base B自然退役，不操作其作业，以覆盖另一个任务迁移推理服务时的GPU重叠。Mixed四卡在SWE成功后替代同四卡。迁移期Base最多10＋SWE4＋HLE2≤16；旧B结束后Base至多8＋Terminal4＋SWE/Mixed4≤16。无关项目GPU不计入本题，也未操作。

共用r16/alpha32/dropout.05、global8、LR1e-4、weight_decay.1、一epoch、BF16、原loss mask及完整样本策略。新HLE与Mixed不覆盖在训SWE数据；旧High生成STOP_ADMISSION与已停止的后续保持，无新教师API、数据hash审计或app自动化。

19:24启动修正：初次HLE726647获得调度后因集群包装器误把独立`--data-dir`目录参数当sandbox而0步失败，未加载模型；CPU原样解析条件已确认改用`--data-dir=...`通过。现HLE726664、Terminal726665、Mixed726666均用equals参数写法重提，旧0步后续726648/726649取消，数据与预算未变。HLE仍排队，GPU真实optimizer/eval尚待实证；详见执行记录和重提交回执。
