# 最终交付的最小剩余清单

**12:10自动化已按用户要求删除**；现有队列继续运行，不再定时检查/推进。最新coverage为Terminal专家219/445、AVG200/445，AVG ASI86/240；完整主分/总宏平均仍空，reshard输入供应异常继续null。[最新状态](current_status_20261017.md)。

**11:27补评在途**：reshard专家seed1一次原答案官方补评parent2394544已在124–127独立4CPU/8GiB/900秒运行，3条restore/19845项严格校验通过，pytest已启动1item；尚非有效成绩，不重试或提前改summary。SWE完整10/0/4与11:14双视图、11:15阶段PDF保持；Terminal/AVG ASI未齐及两项无archive原null仍是最终交付未决项。


**11:15更新**：SWE Base/专家/AVG64全51有效，10/0/4resolved，[T774原答案审核](avg64_teleport7744_grade_review_20261017_1110.md)已接受exact native0；原instruction79要求的v1.6.0依赖遗漏导致编译阻断，未运行TestSendEvent，旧timeout/null不改。Mac专用route在原生完整排空/无消费者后已关闭，[释放收据](source_snapshots/avg64_t774_route_release_20261017_1115.json)保存38444/control socket消失，原route收据保留，不重建。新[完整任务对照](swe_task_comparison_20261017.md)和[双视图](source_snapshots/formal_aggregation_20261017_1115.json)及11:15阶段PDF已更新。AVG ASI全240生成/727856释放，科学评分85/240尚未齐，Terminal专家190/AVG178也只是部分coverage，完整macro/最终提交仍缺。


**10:42唯一等待器已启动**：root与独立审阅通过新版fb5a/8cff及真实route receipt后，10:40:56只启动一次T774 parent**2223041/start870388084**；10:41:47仍waiting_source_or_route、lock_held=false、0native。它只在原AVG ASI全240/pool shutdown/源scope空marker与124–127实际scope排空后领取独立未来租约，native仅124/1CPU4GiB3000s，不碰92–95或Terminal到123的原扩容。当前232保存、8在途，不能释放生成核。route依赖Mac专用84416/control socket，结束无消费者后只关自身route，不能因中途断路自动重跑未知原生结果。


**10:39正式覆盖**：[新双视图](source_snapshots/formal_aggregation_20261017_1039.json)已接git-leak原答案native1；Terminal专家177/445另5invalid、AVG165/445另4invalid，全部未齐备结果保持null。AVG T774原站TLS路由已恢复，CPU124 prepare-only入口仍待新版路由识别审核与ASI真实交接，不能把转发成功当官方测试已跑。


**10:33更新覆盖旧coverage**：SWE专家全51题0通过（50nativevalid+1完整官方报告审计），Base10/51；[逐题对照](swe_task_comparison_20261017.md)与配对95%CI已齐。AVG50/51、4resolved，剩T774原proxy恢复准备，尚未native。Terminal git-leak原候选官方5/5/native1已独立接受，其他新增invalid尤其两项缺最终archive继续null；原raw和既有历史不改。10:26双视图TB171/159只是接入前coverage，不构成完整分。阶段PDF10:33已验收，继续等待Terminal445、AVG ASI科学评分、AVG SWE最后项及TIES唯一未决，仍无最终report.pdf/最终提交。


**09:25运行增量**：三个SWE原答案补评分已在独立92/93/94三核运行，见[短TMPDIR恢复](swe_additional_short_tmp_recovery_20261017.md)；原namespace启动失败保留，不构成有效分数或模型重答。新Terminal git-leak/seed1的[离线恢复准备](terminal_git_leak_grade_only_preparation_20261017.md)已完成Git完整性与同SIF差分，但尚无native/成绩，仍是待完成评分。不得以这些准备状态覆盖下述正式coverage。

**09:15增量**：两项Vuls一次原答案native补评经root独立读任务/日志/资源与排空证据后接受0，各SWE有效coverage升至49/51，仍各2invalid，完整分继续null。Terminal专家141/445另3invalid、AVG131/445另3invalid，均非完整成绩。新增专家git-leak-recovery/seed1清理异常正在只读核查，不派生预算0。[最新双视图](source_snapshots/formal_aggregation_20261017_0915.json)与[独立Vuls审核](swe_vuls_grade_review_20261017.md)。[额外HLE配对退化案例](hle_base_avg_disagreements_20261017.md)补充20个Base对/AVG错且AVG有答案的真实案例，原20失败与三项未来实验不替换。


初审时点：2026-10-17 03:03–03:10 CST；**07:28更新实际完成状态**。依据用户最初粘贴的多专家题面（附件`20b2f4c3-6e03-4746-a389-d488086d7780/Pasted text.txt`）、[需求转录](../EXPERIMENT_REQUIREMENTS.md)、当前[根README](../README.md)、模型/训练/合版/统计/资源回执。后来的线上SFT→stage2模板不覆盖原题面。原初审只读；后续真实执行与时点见统一进展日志和逐项收据。

## 已完成，不再列作待重做

| 项目 | 实际证据与边界 |
|---|---|
| 独立候选人GitHub | [创建/推送回执](source_snapshots/github_repository_20261017.json)：由官方template创建Private仓库，实验已推送`master`且设为默认分支，模板`main`保留。不是只有本地bare remote。尚不等于最终材料齐备。 |
| 四专家与Mixed训练 | 五个native run均完成；实际加载数、固定checkpoint、曲线/CSV/原生日志索引齐备，见[训练曲线](training_curves_20261017.md)与[数据报告](training_data_report_20261016.md)。旧数据报告中的“Terminal待启动”等历史状态不能覆盖完成回执。 |
| 两个合版产物 | AVG64精确等权更新与AVG16固定rank压缩均导出，张量和dense代数核验已完成，见[合版记录](merge_execution_20261017.md)。最终AVG64在正式反馈前固定，不能再根据正式分数选配方。 |
| 固定候选的249条SFT loss对照 | [完成回执](source_snapshots/sft_loss_only_execution_20261017.json)：四候选均249行、65,536上限、step0、无optimizer/训练/生成。Base CE=2.1059763432，AVG64=1.3579210043，AVG16=1.3792226315，Mixed883=1.6724628210；Mixed与原训练末次val精确一致。不是仍在等待全部候选，也不是四项任务准确率。 |
| 五个公开HF模型 | [模型索引](../models/README.md)、[发布回执](source_snapshots/hf_publication_20261017.json)：四专家及AVG64均Public、ungated、固定revision，匿名完整下载与源权重字节比较通过，卡片/许可证/NOTICE/加载示例已保存。无需再创建或重复上传。 |
| 汇总与统计实现 | [汇总协议](final_aggregation_20261017.md)、[路径清单](../configs/eval/final_results_20261017.json)：四项百分制等权、missing/invalid拒绝完整主分、同ID paired bootstrap、TB五seed簇/ASI四condition簇及人工算例已实现。脚本就绪不等于最终数字已齐。 |
| 资源与成本证据 | [账本](resource_ledger_20261017.md)已分结束/active GPUh、失败/取消/服务、API usage估计/reservation/未知发票。原02:38快照保留，不回写成持续状态。loss-only727689后来COMPLETED、4GPU×1749s=1.943333GPUh，已另有完成回执；它不是按四候选耗时再重复加四遍。人工主动工时未计时、学校单价未知，不能编造补齐。 |

## 真正还缺的交付

1. **完成剩余正式范围及有效判分，再生成最终结果包。** Base固定答案补评分已完成：SWE51/51、HLE2500/2500、ASI240/240；Terminal442native，另3计算超时仅在独立预算视图派生0，raw null保留。HLE专家/Mixed/AVG64/AVG16已全2500有效，6.92%/5.84%/4.68%/4.04%；ASI专家全240有效，公开local原生0.378991%低于Base1.570988%，如实保留。SWE现已Base/专家/AVG各51/51有效，10/0/4通过；11:14统计Terminal专家190/445、AVG178/445，AVG ASI已全240生成、科学评分85/240有效。11:25唯一reshard原答案补评仍在途，不提前接分。每次先刷新专家/AVG两SWE collector及Terminal只读审计collector，再执行strict+独立预算`summarize_experiment.py`。只交付完整有效范围的主分/paired CI，未齐备保持null，不用有效子集估最终提升。最新[固定快照](source_snapshots/formal_aggregation_20261017_1115.json)。

2. **失败材料已完成，收尾时同步最终索引。** [20个真实AVG64有效wrong与三项后续实验](avg64_failure_cases_20261017.md)已有原始输出/评分路径及短证据；同ID Base也全失败，不能称合版引入退化。没有把环境invalid或pending充作20例，不需再凑占位案例。最终只需把已成文材料和完整矩阵/资产索引关联。

3. **一页`report.pdf`。** 根目录最终`report.pdf`尚无；[11:15一页阶段稿](progress_report_20261017.md)及重画源脚本已生成并目视验收。原题固定结构为摘要（150–200个中文字符）、过程、结果，总计不超过一页。结果至少包含四项×{Base、目标专家、AVG64}分数矩阵、专家范围标注、宏平均提升、失败率和成本，详细曲线/20案例/CI留仓库链接。若截止仍不完整，表格需明确null/未完成及真实coverage，不能将报告排版完成冒称实验全部完成。需要实际生成PDF、核对页数并目视检查可读性；保留生成源稿便于后续更新。

4. **补齐原题明确的合版方法/配置对照，并收束训练对照。** 用户指出压缩不在原题合版示例中，AVG64/AVG16仅为辅助压缩对照，Mixed属于另一条训练对照；不能据此称该项完成。任务算术改系数草稿又被用户撤回，未启动新评测/GPU。真实TIES六shape pilot已通过，但SVD64残差30%-57%，未导出该近似；现[完整Dense导出](source_snapshots/ties_dense_export_728007_20261017.json)728007已验收：1045tensor/310目标/735非目标，BF16相对更新误差10.531%；普通TP2服务728016已全2500生成并释放，TIES2499有效、131correct，另1项缺correct且不符合已批准截断恢复例外，保留null；完整方法比较尚缺。该表示不再是同r64参数化容量，需要披露dense-vs-LoRA舍入差异。主AVG64保持冻结，不按正式成绩换主模型、不恢复独立task-val；已有CE仅作诊断，不新增loss-only工作。新方法导出验证、实际任务成绩、配对区间与方法指标图齐备后才可称完成对照。

5. **补齐可复现交付的资产取用路径。** README已诚实说明固定机器路径和offline依赖，不是fresh portable安装。但现有命令仍依赖clone不会带来的资产：HPC外部donor Python/wheelhouse与SIF、`artifacts/source`、已筛选train/val与行级provenance、task SIF/cache、Base修复runtime多层快照、native环境缓存与完整训练/评测日志。最小补充是一份可随最终提交定位的资产索引：每类资产的固定版本/来源、公开下载或构建命令、派生资产的重建顺序，以及无法公开资产给面试方的受控取用方式。尤其Terminal preparer依赖`configs/eval/*terminal*.json`列出的`artifacts/.../runtime*/scripts`，仅有Git中的顶层controller与路径名不足以从空目录重建。保留这些代码overlay与source_inventory并给出可取用位置；不要为补齐复现而公开凭据、隐藏测试/参考答案或不宜再分发的原始benchmark包。现有公共HF adapter已解决模型取用，不需要重复导出大权重。

6. **最终同步与提交凭据。** 当前GitHub已创建/推送、五HF已发布，这两项不再列作“未开始”。待结果、案例、PDF和资产索引齐备后，更新README的实际完成状态与最终模型/结果revision，提交最终commit并检查Private仓库的面试方访问方式。创建回执仍`complete_submission=false`且明确未发送邮件/邀请；原题要求将仓库/模型链接与revision按面试通知提交，尚无最终通知回执。本文不自行发送或邀请。

## 必须保留的协议边界

Terminal当前全89×5并不等于满足原题的3h/32CPU/48GB/256K/80K；目前实际为1800s/4CPU/8GiB/64K/8K，仍无面试方例外批准证据。这个缺口不能靠README或PDF措辞补成“已达标”，最终需如实披露并说明接受情况。HLE/ASI替代Judge、ASI公开local而非Portal、SWE缩短预算、历史Base与后续服务/并发差异也应进入一页报告的限制或明确链接，不能因完整任务数而消失。

另，用户取消独立task-val后，主模型AVG64按先验固定，249条SFT loss-only对照在其固定后完成。该对照没有被用作开发集选择，也不能写成已经完成原题“最终配方用独立开发集选择”的过程；继续遵守取消val的决定，同时如实记录这个过程偏离。

本清单不要求扩训练、再采数据、重启已完成训练、重复发布模型或恢复已取消的独立任务级validation。最小主线是 **收齐有效正式结果 → 真实20案例 → 一页报告与已完成对照整理 → 资产取用与最终提交**；无法完成的条目必须保留真实未完成状态。

以下保留03:03历史审核来源，不代表07:28当前状态（均以`/data/caoqinlu/projects/apex-takehome/`为根）：`artifacts/eval/avg64_swe_hard51_20261017/summary.json`（as_of2026-10-16T18:12:25Z、仍waiting）、`artifacts/eval/avg64_terminal_full445_20261017/summary.json`（updated2026-10-16T19:03:20.992602Z，即10月17日03:03:20 CST）、`artifacts/eval/avg64_hle2500_20261017/scoring/summary.json`（缺失）、`artifacts/eval/avg64_asi240_20261017/scoring/local_score_seed31415.json`（缺失）。这些是审核时点的保存状态，不当作持续进度。
