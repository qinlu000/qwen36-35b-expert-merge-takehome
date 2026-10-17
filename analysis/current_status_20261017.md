# 当前进展与未决事项

**08:20接续（最新）**：[08:08双视图](source_snapshots/formal_aggregation_20261017_0810.json)依指定顺序刷新三份collector后生成，Terminal专家110/445有效另2invalid、AVG103/445另3invalid；完整主分、AVG四项macro仍null，source issues空。08:09独立队列更新AVG到104有效，所有当前invalid均早于07:26、未新增。两SWE各48/51，HLE/ASI完整单项与配对区间不变。

**实际推进了两项SWE补评分**：[Vuls执行记录](swe_remaining_grade_only_execution_20261017.md) root已08:18唯一提交专家1520240与AVG1520241（startticks均869530503），只重放各自原空patch/测试/SIF，1CPU/4GiB/3000s、0新模型调用；同global92–95锁串行，专家child1520253已运行、AVG尚等锁。守护scope实际92–95/32MiB、真实native只92/4GiB/swap0，原29source bindings/镜像元数据保持。结果未出/未审不能变主分；旧RemoteProtocolError/OOM归因未决，磁盘scratch+durable logs只提供可验证的环境修复候选。两父结束前冻结新script/manifest，不扩4项disabled，不重启或重复submit。08:23 workspace准备53.93秒/rc0、原cache磁盘复制rc0，测试仍在跑，未报新分。后续清理必须先等child自然结束与双native空，再清guard、双全scope空、最后解锁；不能只凭guard不见或helper reward0就接分。

**Terminal尾部准入已加保护**：旧35min GPU gate未覆盖最大环境600s+Agent setup360s+solver1800s=46min。root已独立复核后08:14:45启动唯一metadata guard1508852/start869510981，当前waiting_cutoff、两STOP均不存在。它在10/18 **01:10 CST**只创建两队列既有STOP_ADMISSION门；不改live父、每题预算或在途，不kill/release GPU/写CPU完成marker。已知完整链3660s在02:11后仍留9min cleanup，未知其他阶段不作保证；若两队列提前445/activepending空则自行退出。详见[运行审计](execution_status_20261017_0810.md)及[启动收据](source_snapshots/terminal_core_admission_guard_launch_20261017.json)。

[Direct08:10核查](direct_status_20261017_0810.md)：AVG ASI81/240保存、8在途、151未准入，科学评分尚0，latest08:10:11在推进；79failed/2completed是生成状态，不能当科学分。仍复用727856/28095，实际8running/0waiting。当前727912/727913/727856三普通acd_u/Nice1000 TP2共6H100，无新GPU申请/重建。真实Terminal23个4核scope并集0–91；AVG allCPU/生成完成marker均缺，stage2仍合法等后续32CPU交接。新SWE临时租约只占共享92–95，不碰96–127；未来AVG科学评分仍workers1、同global锁。固定ASI audited已只读复核28输入/239其他行与总分，不重复一次性collector。

08:12账本结束227.570GPUh、6卡active暂计23.388889GPUh，总250.958889；API预算仍15.029134794CNY另.328327020USD，无新paid。08:14 metadata确认80/data可用2,176,642,637,824B、/tmp33,756,135,424B，未耗尽；new scratch在/data。阶段PDF完整单项未变化，无需重复重画，仍保留07:28验收稿。

以下07:28及更早保留历史过程，最新运行阶段以上述08:20为准。

**07:28收尾更新（最新）**：完整HLE为Base **99/2500=3.96%**、专家 **173/2500=6.92%**、Mixed **146/2500=5.84%**、AVG64 **117/2500=4.68%**、AVG16 **101/2500=4.04%**。AVG64较Base +0.72pp，配对95%CI[-0.20,1.64]；较Mixed -1.16pp[-2.24,-0.12]；较AVG16 +0.64pp[-0.24,1.481]。历史native-no-answer为Base1445/专家30/Mixed41/AVG1196/AVG161302，服务和排队混杂仍在，不能把差异全部归因权重。来源[07:26:42完整双视图](source_snapshots/formal_aggregation_20261017_0727.json)。

**ASI专家已全240有效**：唯一CMOS b1导入故障经冻结原候选一次native补评分，复用9条原Judge cache、0新增付费调用，原239行不变；新[只读汇总](../configs/eval/asi128_audited_recovery_20261017.json)累计90.9579316594/24000，即 **0.378991%**，低于Base1.570988%，差 **-1.191997pp，60任务簇配对95%CI[-2.278710,-0.303023]**。已核原native公式/score_divisor，无汇总缩放错误；只代表公开local/替代Judge实验。保留原报告的invalid与历史ASI128选择，不据此更换权重。[执行证据](asi_cmos_import_recovery_execution_20261017.md)。未来AVG评分runtime提前追加冻结ASI源码根，完整原代码和symlink保留、import验收通过，workers仍1。[60任务逐项对照](asi_base_expert_task_comparison_20261017.md)为3任务上升/11下降/46持平，前5下降贡献净降幅82.04%；多数对应专家未形成所需科学产物或未过hard gate，原因尚不能归为训练或环境。

**实际资源为6H100**：普通acd_u/Nice1000三个TP2（727912/727913/727856），727857在Mixed+AVG16全5000生成、原生metrics0后07:19:59自动释放；TIES728016、ASI专家727879和用户旧4卡继续释放，离线端点不重建。AVG HLE已06:38生成完，AVG ASI coordinator1126014/generator1126055已复用727856/28095接续，生成不再等专家科学评分。AVG SWE全51次尝试06:47结束、scope/marker已验，CPU0–11已自动交接：Terminal专家12槽、AVG11槽；第二阶段额外8槽仍等两ASI真实CPU完成标记，不抢未来CPU96–127。

**评分兼容修复及剩余缺口**：两项原满300秒ReadTimeout在原答卷/配置/预算不变、原grader无在途自然退出后，按已有TimeoutError同等native-no-answer规则collect-only，0模型/Judge调用；早退transport/infra判断不变。固定原2次HTTP200+length4096+parsefail名单的compact恢复为AVG2/TIES6/AVG161，9次新增共¥0.00827325，原budget/答卷/criteria/identity均保留，显式2+1格式例外。TIES仍 **2499/2500有效、131correct、1invalid**：缺correct的原JSON不在length规则内，完整分/差值/CI继续null，记录待讨论，不扩大parser或自动再评。

nginx最终补评分07:19实际执行8项官方测试、全部失败且native0/无Harbor异常；只恢复原archive/delta，不安装或启动nginx。原Python和CPUoffset bootstrap失败保留，最终一次原生测试经独立审阅后接[Terminal只读collector](../scripts/collect_terminal250_audited.py)，原队列和raw null不改。07:26严格有效覆盖：Terminal专家 **92/445**（另2invalid）、AVG **90/445**（另3invalid）；两SWE各 **48/51**，专家0resolved/AVG4resolved，各3评分未决，已有[原答案补评方案](swe_remaining_grade_only_plan_20261017.md)，尚无新native准入。完整AVG四项与macro仍null，不用部分coverage算分。每次按专家SWE→AVG SWE→Terminal审计collector→统一双视图刷新；ASI已完成的固定审计输出不重复写。

[07:26成本](resource_ledger_20261017.md)：结束227.570GPUh、6卡active暂计18.8228GPUh；API预算核算15.029134794CNY另0.328327020USD，缓存9次不重复收费、未知发票/CPU工时不编造。[存储快照](source_snapshots/storage_20261017_0730.json)：本机可用30.14GiB，80项目盘1.99TiB/系统31.54GiB（97%已用），HPC项目共享盘11.04PiB、quota未知，未耗尽。阶段PDF07:28已纳完整HLE/ASI真实退化，摘要181中文字符/含标点199字符，一页及PNG目视通过；仍非最终report.pdf。

以下06:15及更早内容保留历史过程，当前阶段以上述07:28为准。

**06:15接续（最新）**：TIES-Dense已全2500生成、原generator退出0、原生metrics0并确认job728016消失；06:11只释放其自身2GPU，外部Judge887556继续，不能因28097离线重建。[本轮Direct审计](direct_status_20261017_0607.md)与后续释放收据保留原始时点。当前四个普通TP2共**8H100**：Terminal专家727912、AVG执行727913、AVG HLE→ASI727856、AVG16 HLE727857；727879/728016及更早用户释放的4卡均保持释放。

[06:14:39双视图](source_snapshots/formal_aggregation_20261017_0615.json)已依次刷新两SWE collector、通过既有人工算例后生成：AVG SWE37/51、HLE2186/2500、TB68/445；Terminal专家68/445，SWE专家48/51，ASI专家109/240；AVG16 HLE1534、TIES1272。AVG新增OpenLibrary630空patch缺题目要求Bestbook产品module，root独立重读任务/原test/native0后接受exact只读overlay，未套专家白名单；其余网络/未知故障仍null。以上均为有效判分覆盖，非生成总数或子集主分；完整AVG64宏平均与TIES方法差值/CI仍null。HLE专家/Mixed完整6.92%/5.84%不变。

ASI专家此前94停留源于max3sat原生评分持续计算：内层固定1800秒/1CPU/3GiB，7200秒是外层condition兜底，并非该程序预计耗时。已自然返回，06:14评分增长至109/240；不是GPU端点释放造成的故障。未来AVG评分亦保持workers1：虽已有API预算锁及submission单CPU租约，部分host侧科学子程序只继承整个92–95 affinity，尚未证明四worker时逐condition隔离相同；不以提速假设直接改4。当前在途、已预排队与原答案均不打断/重复。nginx851972仍等同CPU92–95 global lease，未发native；没有伪造ASI完成marker或抢用未来AVG生成CPU。

Judge截断恢复仅将既有脚本硬编码8条改为显式expected_items及(model,task_id)唯一，旧8条语义保持，12个离线检查通过。AVG/TIES原grader未退出，现有invalid清单只是阶段库存，未固定最终恢复名单/新配置、未发恢复请求。须待原grader结束逐项审核后遵同2+1格式例外，原答案不重新生成。

[06:09资源账本](resource_ledger_20261017.md)计已结束219.743889GPUh、当时10卡暂计16.582778GPUh（早于本次TIES释放）；现存CNY预算核算13.105821894、USD0.328327020，ASI账本缺失仍unknown。80/data可用约2094.9GiB，系统/tmp约31.38GiB；未见空间耗尽，系统盘仍97%用量。所有时点分别保留，不把历史10卡当当前8卡。

以下05:46及更早段落保留历史过程，当前服务阶段以上述06:15为准。

**05:46统计与服务更新**：[新双视图](source_snapshots/formal_aggregation_20261017_0547.json)含9模型、17208固定观测，fixture与所有source schema检查通过。strict有效覆盖：SWE专家48/51、AVG29/51；Terminal专家60/445、AVG58/445；ASI专家94/240（科学评分已启动）；AVG HLE1726/2500、AVG16 1087/2500、TIES-Dense 86/2500。HLE专家/Mixed仍完整6.92%/5.84%。除已完整单项外不公布子集主分，AVG64四项宏平均及TIES方法完整比较仍null。

TIES728016于05:43:19完成恰2次text/image协议验收（不按内容正确筛选），正式generator887555/Judge887556已准入，详见[执行收据](ties_dense_hle_execution_20261017.md)。ASI专家05:38:35全240生成退出，后续仅CPU/API评分；双重审阅、240终态/池关闭/源scope空及两次metrics0后，**727879已释放2卡**，[独立释放收据](source_snapshots/asi_expert_gpu_release_20261017.json)。当前五TP2共**10卡**，均普通acd_u/Nice1000；727879/28090离线是有意释放，不能因旧route失败自动重建。

nginx原答案的一次native补评分parent **851972/start868587717** 已持久启动，[静态准备与锁契约](terminal_nginx_grade_only_preparation_20261017.md)仅恢复原候选差分、保护运行器resolver；目前等ASI评分的同一global锁，不抢占、不额外领取生成池CPU。尚未取得native结果，保持原invalid；若距核心截止不足1800秒就停止新准入。完成后先审独立test证据和两次scope排空，再决定是否接受，不手填0。

[一页阶段PDF](progress_report_20261017.md)已于05:37更新成真实HLE表、混杂与TIES数值结果，摘要182中文字符/含标点199字符，1页及目视检查通过；仍不是最终report.pdf。

**05:34方法实物更新**：[TIES-Dense实际导出](source_snapshots/ties_dense_export_728007_20261017.json)已完成：728007普通1GPU、129秒后释放，完整26片71.90GB，310目标/735非目标bitwise/1045key/source未变/重载全部通过，无SVD。BF16存储相对真实TIES更新偏差**10.531%**；相对目标合成权重0.1262%，两者分母不同。未变元素44.22%含原D=0，不能全归因舍入。

唯一新HLE controller782323（startticks868543002）已提728016，普通acd_u/Nice1000/TP2，ACD1-19，05:33:34–09:33:34 CST；当前总**12张H100**。完整模型alias apex-ties-dense、独立28097，正在冷加载与协议验收；尚不能称正式2500已准入。09:28:34停新题、原300秒自然收尾，模型消费者排空后仅释放自身job。它不使用LoRA、不与AVG64声称同r64自由度，主AVG64/28095→ASI/旧watcher保持。已有唯一claim，不能重复启动。新统计已注册HLE-only `ties_dense_vs_avg64`；未齐备仍null。

**05:22正式统计更新**：[双视图快照](source_snapshots/formal_aggregation_20261017_0522.json)。已依次刷新两份SWE审计collector，再生成strict与独立Terminal预算视图，未发模型/Judge请求。新完整HLE结果：专家**173/2500=6.92%**、Mixed训练对照**146/2500=5.84%**，Base99/2500=3.96%；专家相对Base差值+2.96个百分点，逐题配对bootstrap95%CI[1.80,4.12]，Mixed+1.88[0.80,3.00]。均为含342图的固定2500，非text-only。

**这不是纯权重因果增益**：Base原生no-answer1445，专家30，Mixed41；历史Base与后续的服务并发、队列时间等差异仍在，配对抽样不能消除这些混杂。原Base回答不重生、不按正式结果挑checkpoint。专家/Mixed原8项Judge截断经[一次格式恢复](hle_compact_judge_recovery_20261017.md)后全部有效，原criteria/answer/identity/parser不变，原invalid/budget/requests/responses均保留；新增8次费用合计0.00752625 CNY。明确披露原两次Judge上限之外的一次恢复例外，不能称协议完全没变。

其余strict有效覆盖：SWE专家48/51（0通过、3未决），AVG SWE22/51（1通过）；Terminal专家50/445另1invalid，AVG50/445；AVG HLE1284/2500另1invalid，AVG16 HLE730/2500。ASI尚无科学评分，生成进度另见原队列，不把程序退出当准确率。AVG64四项比较、宏平均和相关CI仍null。Base Terminal保持442native/445；独立预算视图445含3审计计算超时派生0，主分20.224719%、Base预算macro11.340888%，不冒充445native。

**独立合版方法推进**：主AVG64继续冻结，AVG16只作辅助压缩，TA系数草稿撤回。真实TIES pilot727948在tiny top-k并列fixture自检失败；仅换无并列fixture、保持严格断言及真实算法后，727967六种shape成功，1H100/10秒已释放。五个需截断样例SVD64相对更新误差30.42%–56.77%，因此**不导出或评测该SVD64版本**。现按同固定PEFT0.20 dense-delta TIES配方（rho0.2/total/ones/外λ1）准备[TIES-Dense完整模型导出](ties_dense_export_feasibility_20261017.md)，消除低秩截断，BF16存储舍入另报；26片约72GB写HPC新目录，735非目标不变。尚未完成完整导出或任务比较，不写完成、不称与r64参数化容量相同；HLE-only方法对照不产生四项macro。详见[决策](merge_method_decision_20261017.md)及[试跑](source_snapshots/ties_pilot_727967_20261017.json)。

**资源和吞吐**：现五个TP2共10H100，均普通acd_u/Nice1000；无emergency，已释放旧4卡不重建独立ASI。新方法短1卡export、后续独立普通TP2最多临时13卡，需每次实时核验与唯一claim；不碰28095 AVG HLE→ASI复用或旧release watcher。[05:17成本快照](resource_ledger_20261017.md)：已结束216.721389GPUh、在跑暂计10.406111GPUh；不是最终费用。排除迁移后的40分钟[实际终态速度](execution_scoring_gaps_20261017.md)为Terminal专家19.52/小时、AVG18.02/小时，AVG略低于截止所需约18.99，仍有445全量截止风险；后续只按SWE/ASI真实CPU交接扩容，不缩冻结预算。nginx cleanup guard仍invalid，未在无CPU租约时强行重评或补装服务。

以下04:37及更早内容保留历史过程，当前结果、方法和服务阶段以上述更新为准。

**04:37实时更新**：[评测与存储核查](progress_and_storage_20261017_0436.md)。三类普通分区迁移均已完成，Terminal专家/AVG64执行恢复10槽，ASI恢复原parent；HLE专家和Mixed各2500题生成完成，判分继续，HLE专家2卡已自动释放，当前约10卡。AVG64 HLE累计621题、50在途，Mixed已接AVG16。SWE专家51次尝试结束、48份有效且0通过，另3份评分异常尚未决；完整模型比较仍未齐备。80项目盘剩2.1TiB，系统盘剩31.4GiB且97%已用；本机剩约30GiB，暂未发现本轮新磁盘写入故障。详细计数、限制与HPC核查见新收据。

以下保留上一轮迁移过程与03:47队列历史，当前服务阶段以上述04:37记录为准。

最新执行变化是**按用户要求迁移普通分区 `acd_u / Nice1000`，HLE每模型50并发**。实时阶段及保存时点见[普通分区机器快照](source_snapshots/ordinary_partition_handover_20261017.json)，[迁移与卡数说明](ordinary_partition_handover_20261017.md)列具体接续方式。用户在侧会话释放的727113/727654共4卡保持释放，未重新申请独立合版ASI副本；当前六个TP2约12卡，HLE专家及对照生成完自动释放4卡降到8卡。最终截止10月18日14:20，核心窗口02:20收尾、保留12小时。每小时本线程推进已确认ACTIVE；本机和应用需保持运行，80上的现有持久队列独立运行。

**Loss只作训练诊断，不作为val判断标准。** 已取消的独立任务val不恢复；专家、合版及固定训练/压缩对照使用实际任务分数。ASI128历史上按loss选择，不能证明其任务最优；当前服务、公开模型及AVG64已冻结使用128，保留该身份并披露局限，不在运行中悄悄换134。

## 已完成

- **训练**：SWE249、Terminal250、HLE250、ASI134步（固定checkpoint128）、Mixed883均完成一轮。训练配置、实际加载条数、原生train/val曲线与源数据已保存，见[训练记录](training_curves_20261017.md)。独立task-level validation已取消，训练原有的SFT loss留出集保留。
- **合版**：固定四专家等权平均，精确AVG64与固定SVD压缩AVG16均已导出并验证。AVG64在新增loss对照与正式反馈前固定为主模型，后续不依据正式分数选权重或checkpoint。
- **已有SFT诊断**：同249条、64K上限，Base/AVG64/AVG16/Mixed883的原生loss为**2.105976 / 1.357921 / 1.379223 / 1.672463**。四候选完整结束，4卡已释放，原始数据与图保留，见[诊断记录](sft_loss_only_plan_20261017.md)。不把它算作任务级val或效果消融；新增[HLE2500实际任务对照](hle_task_controls_20261017.md)比较Mixed883与固定AVG16。
- **公开模型**：四专家和AVG64共五个Public HF仓库均已发布、固定revision，并通过匿名全部文件下载和源权重比对，见[模型索引](../models/README.md)。
- **代码交付**：[私人GitHub仓库](https://github.com/qinlu000/qwen36-35b-expert-merge-takehome)由原官方模板创建，实验代码在默认分支master，模板main保留。当前提交材料仍会继续更新。
- **统计与成本**：固定ID的四项等权宏平均、paired cluster bootstrap与TB五seed均值/标准差的实现和人工算例已完成；资源账本记录了训练、失败/取消和服务等待等实际allocation。最终数值待全部结果收齐后刷新。

## 正式评测与普通分区迁移

三套HLE已在普通分区实际续跑：专家727855、AVG64727856、对照727857，均50 active的真实状态已保存；Mixed→AVG16保持串行。Terminal727640与AVGExec727660已停新题、等待原在途/CPU消费者完整收尾后自动迁移。ASI专家原parent2752099仅暂停提交，原138个已准入condition均已自然终态、scopes与模型请求排空，旧727643已释放；普通727879（ACD1-8）正在加载，验收后恢复同parent。**未结束的迁移不能称全部切换完成。**

以下表格保留03:47:49的正式队列历史快照，之后的会话计数与阶段以新机器快照为准；HLE续跑checkpoint的completed只计本会话，跨会话总回答数另有`saved_results_total`，不表示丢失旧答案。

| 队列 | 已保存的进度 | 接续方式 |
| --- | --- | --- |
| SWE专家 | 全51次尝试结束、0 active/pending；原生42份有效，已批准审计另汇总 | 原回答冻结；余下评分异常另审计 |
| AVG64 SWE | 已真实准入；1终态有效、10 active、40 pending | 03:40先接9个释放槽，原专家结束后补CPU5到10槽 |
| Terminal专家 | 23/445结束且有效；10 active | CPU12–51初始10槽，与AVG64并行 |
| AVG64 Terminal | 23/445结束且有效；10 active | CPU52–91初始10槽 |
| ASI专家 | 113/240 condition已保存；8 active，未科学判分 | 继续原生成；原生grader另接，不阻塞HLE |
| AVG64 ASI | 等专家ASI生成CPU释放 | 接续同一CPU池及原生grader；HLE已独立运行 |
| 专家/AVG64 HLE | 已正式启动；分别192/13题生成终态，各50 active | 各自2500题，不再等ASI；生成数不是正确率 |
| Mixed883/AVG16 HLE | Mixed883已真实生成70题，50 active；AVG16待接续 | 相同HLE2500依次执行；不是新增独立val |

历史03:45资源峰值16卡；03:47释放已完成SWE专家2卡，03:53侧会话再按用户要求释放未准入合版ASI2卡，此后按12卡一换一迁普通分区。合版ASI将等专家生成CPU释放和AVG64 HLE全2500生成排空，复用现有28095服务，不重建旧28093。HLE专家2500和Mixed/AVG16各2500生成完成后释放各自副本，外部grader不需GPU。Terminal仍初始10+10 CPU槽，后续扩容须按原真实CPU释放门槛；资源迁移未改变每题预算或原始答案。

当前覆盖率与attempt完成数尚不足以形成四项完整成绩。统一完整主分、宏平均提升和配对区间保持null，不能用有效子集均值替代。

**Base评分恢复已收尾**：原owner于03:29完成固定答案的评分恢复，0新增Base求解。HLE2500/2500、99正确、3.96%；ASI240/240、1.570988%；SWE51/51计分结论、10通过、19.607843%，其中NodeBB官方测试解析审计0仍保留raw reward null。Terminal原生442/445、90正确；另3个官方测试900秒计算超时保留原null，仅独立预算视图采用445分母、mean20.224719%、sample SD2.635065个百分点。预算口径Base四项宏平均11.340888%；不能称全部原生reward齐全。来源为[Base缺口记录](base_gap_completion_20261017.md)，不把环境故障或未准入任务补0。

**03:25统一统计补记**：[双视图收据](terminal_budget_aggregation_20261017.md)已实际运行：Base SWE50/51有效；Terminal严格442/445、3 native null，审计预算则445/445、均值20.224719%、五seed sample SD2.635065个百分点、89任务簇95%CI[13.033708%,27.865169%]。派生3项均保留native null，未改原始reward。Terminal专家/AVG64分别15/14份有效，仍在运行；HLE/ASI专家与合版尚待后续评分。严格与预算宏平均、模型差值和配对CI均未齐备。

**最新评分补记**：独立读原任务和日志后，OpenLibrary缺Bestbook实现、Qutebrowser未实现KeyInfo构造的两份原native0已显式接受，专家SWE现48/51有效（原生42＋批准6）。Vuls OOM归因未决、NodeBB单独reward1不足以覆盖timeout、Teleport未决，均保留null。一次纯读双视图汇总保留14708固定观测；Base严格TB442／预算445、预算macro11.340888%，AVG64完整主比较仍null。新coverage与生成会话进度分开，见机器快照。

## 已记录、需要继续处理的事项

1. **评分有效性**：Base原答案补评已收尾，原始null与独立审计/预算来源分开保留。SWE专家已有6个明确批准native0，后三项原因见[剩余审计](swe_remaining_scoring_audit_20261017.md)；每次总统计先刷新collector。逐CPU历史交接不能伪称新消费者在运行时整个池为空。ASI程序completed不是科学评分，不能用4/101称准确率。
2. **模型终止原因**：定向检查的五条SWE轨迹中，252次工具观察没有HTTP400；四次最终BadRequest来自固定`prompt+8192>65536` guard，另一条在墙钟预算边界结束。上下文预算终止继续遵守原协议，不因此放宽窗口或重新作答。该定向检查不能估计全51题的失败比例。
3. **服务截止与吞吐**：SWE专家旧GPU已释放；新普通作业不晚于各自原EndTime及明天02:20核心cap。Terminal约02:01、AVGExec约02:09、ASI专家约02:04；普通排队不保证立即拿卡，迁移耗时与真实吞吐须继续记录，不能由首批推断445次一定完成。
4. **原题过程与配置偏离**：Terminal实际30min/4CPU/8GiB/64K/8K低于原题3h/32CPU/48GB/256K/80K，暂无面试方例外批准。SWE时限、替代Judge、ASI公开local范围和历史Base服务并发差异也继续披露。取消task-val后主AVG64按先验固定，后完成的loss对照未用于开发集择优，与原题该选择过程也有差异；全量任务数不能补足这些偏离。
5. **失败分析与最终报告**：[20个真实AVG64有效判错案例](avg64_failure_cases_20261017.md)及三项后续实验建议已整理，覆盖10个Terminal任务、8个HLE文本、1图像、1SWE。同ID Base也全失败，不能称合版独有退化；描述性抽样不估失败率。[一页阶段报告](progress_report_20261017.md)仍是草稿，最终完整矩阵、成本与report.pdf尚需收尾。
6. **复现资产**：[资产索引](reproduction_asset_index_20261017.md)已列公开来源、离线位置与重建顺序。完整训练日志和二进制底座仅HPC，Terminal470 overlay主要在80且依赖artifacts symlink；精确数据重导出还依赖既有教师回答和选择材料。必要离线材料仍需随最终交付补齐，不能把Git clone称为全资产一键复现。

7. **Terminal网络策略已确认保持不变**：[真实探针](terminal_network_diagnosis_20261017.md)以同SIF/入口/CPU11做public→no-network→public差分，证明当前本地额外断网策略导致DNS失败；Base、专家和AVG求解阶段统一受限。独立probe已清理。用户了解既有三组均禁网后明确“那不用改了吧”，本轮沿用冻结no-network，不只修剩余题、不重生成旧答案或重标历史0；报告披露额外限制及下载依赖任务的潜在影响。迁HPC分区不改变80 sandbox网络。

接下来依次收齐固定正式输出、审核评分异常、重算完整统计、整理真实失败、更新报告与资产索引，再完成最终提交。[最小交付清单](submission_remaining_20261017.md)和[持续进展日志](overnight_progress_20261016.md)保存详细证据。
