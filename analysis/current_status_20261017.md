# 当前进展与未决事项

**12:10用户取消自动化，状态汇报**：每小时“笔试评测持续推进”已由App确认删除，见[取消收据](source_snapshots/automation_cancelled_20261017_1210.json)。不会再定时检查或推进；现有持久评测/科学评分及原STOP准入守护继续按冻结预算自然运行，没有取消GPU作业或缩减在途预算。

[12:08最新严格/预算双视图](source_snapshots/formal_aggregation_20261017_1210.json)按三collector顺序刷新：SWE Base/专家/AVG全51，19.607843%/0%/7.843137%；HLE三组全2500，3.96%/6.92%/4.68%。ASI专家全240为0.378991%、Base1.570988%，AVG86/240有效，0error、154科学评分待完成。Terminal专家219/445有效另5invalid，AVG200/445另5invalid，完整主分/四项macro仍null。没有重生答卷、评分API调用或新增训练，固定ASI审计仅核验。

reshard原答案唯一补评已11:33:21自然结束、11:33:28完整排空/停guard/解锁，原raw reward0/noHarbor不自动有效：官方pytest在session fixture获取固定allenai/c4输入时HEAD报Network is unreachable，fallback缺所需config缓存；压缩/解压候选尚未进入测试，属输入供应infra unknown，继续null，不重试/换输入/联网修候选，也不扩collector接受范围。原19845项恢复通过不等于测试输入供应成功。

12:07实时仅727912/727913普通acd_u共4H100（Nice1000为最近已核值，本轮未另改优先级）。AVG科学评分仍唯一1126014/2282159；当前TSP b3原3600s/1CPU3GiB在CPU92计算，采样OOM0，无新增工程错误，原workers1/396calls/20CNY不变，API journal未落盘仍unknown。Terminal stage2继续等待实际ASI allCPU marker，不能凭生成已结束伪造评分完成。存储80/data余约1.81TiB、系统/tmp28.85GiB、本机28.79GiB，未耗尽。

训练/五个公开HF模型/完整SWE与HLE及专家ASI、20失败案例和一页阶段PDF均已有；最终尚缺Terminal全范围有效结果、AVG ASI全量判分、TIES唯一格式缺口及最终report.pdf/完整macro与正式提交。已有负面结果如实保留，不承诺合版提升。最后阶段PDF仍是11:15版本，没有因本轮仅coverage变化重复生成。

以下保留历史，以12:10取消状态和时点快照为准。

**11:27单项补评已实际运行**：[reshard准备](terminal_reshard_saved_grade_preparation_20261017.md)经root/独立审阅后，11:25:41只启动一次parent**2394544/start870656591**（child2394547/start870656770），新root `artifacts/recovery/terminal250-reshard-c4-seed1-grade-only-20261017`。parent**2a2f31efc4d175f37ec2c3105c801d622da797a08eb29afde9cc9717b97f1df9**、manifest**92af3fc0d2d809c168fd1177608b2ade81e2c41ab07c030f1219f4f3390e759b**、preparer**3ed35de941195c0a248299a053d64c310584e9f9c426424d38d11bdf8972fa55**及42小文件绑定已冻结；不能重跑preparer写manifest或同步截断这些live文件。

真实AVG240生成关闭/T774原guard排空后，使用同一124–127锁inode90780234，独立visible guard，child词法Harbor解释器、taskset124–127/relative offset0，保留原4CPU/8GiB/900秒、minimum_runway3600，不碰科学grader92–95或Terminal既有stage2。原reshard journal精确绑定旧scope af8481795ec4及namespace/host keeper，确认当前已清；捕获的namespace PID不冒充host PID。恢复原app19831、10精确etc差分与4外部uv原状态，dpkg/default旧symlink先仅移除该点再恢复，排除resolver，没有git-leak特殊模式或候选修补。

root实际读3条restore均rc0，严格**19845**项content/mode/type/link和app名单/resolver全同，官方pytest已collected1 item运行；当前仍native_running/lockheld、0模型调用。原PUBLIC verifier/UV group20/HF `allenai/c4/en/c4-train.00009-of-01024.json.gz`输入保持，下载供应异常继续infra unknown，不替换输入或自动填0。结果尚待root完整native/资源/原bytes/两次scope排空→停guard→两次全scope空→解锁独立审核，不依reward自动接分/重试，原raw null保持。


**11:15历史快照（以下计数截至11:14）**：SWE Base/专家/AVG64均已全51有效，分别**10/51=19.607843%、0/51=0%、4/51=7.843137%**。AVG−Base差−11.764706pp、配对95%CI[−23.529412,0]；不以正式分数换冻结AVG64/专家。[完整51题对照](swe_task_comparison_20261017.md)为Base/AVG都对2、仅Base对8、仅AVG对2、都错39，不再有null；专家43空patch/34项context guard等原诊断保持。

[AVG最后T774独立审核](avg64_teleport7744_grade_review_20261017_1110.md)：原ASI生成marker于10:54:11真实全240/poolshutdown/源scope空后才交接CPU124，原musl环境原站TLSprobe HTTP200/证书校验开启；原空patch没有完成instruction79明确要求的netlink v1.6.0 direct require，官方setup自动取v1.11.2后缺iter编译阻断。root独立读自身任务/日志/43原与45准入绑定/资源/原生0/noHarbor及10:55:39完整排空解锁，接受exact native0，**TestSendEvent未执行，不能称断言测试失败**。未改Go、依赖、答案或预算；原timeout/null保留，manifest现6项独立native0审计。原Mac84416专用路由已在确认父子/relaygone、私有socketgone、124–127无scope后关闭，38444和control socket均已消失；故意关闭不重建，原route/admission收据字节保持。

[11:14:04 strict/预算双视图](source_snapshots/formal_aggregation_20261017_1115.json)已按三collector顺序刷新，source issues空。Terminal专家**190/445有效另5invalid**、AVG**178/445另5invalid**，为coverage而非完整成功率；AVG ASI**85/240有效、0error**，完整score与四项macro仍null。HLE五组完整结果、固定ASI专家240和TIES2499/1缺correct保持，不扩规则或重生答卷。

[Direct实际核查](direct_status_20261017_1110.md)：AVG ASI全240于10:54:09保存、10:54:11源生成池真实关闭；727856于10:54:16由既有watcher验证原metrics0/归属后自动释放，现仅**727912/727913普通acd_u/Nice1000共4H100**。唯一科学grader2282159/start870467612及coordinator1126014持原run/global92–95锁；当前TSP native solver CPU92持续计算，原3600s/1CPU3GiB，所见OOM0，无工程卡死证据，不人为截预算。原runtime182项身份保持、workers1/396calls/20CNY；API journal未materialize，calls/cost unknown。AVG allCPU marker仍缺，因此Terminal stage2按原门继续等，不能伪造完成或拿回已交接核。

Terminal最新只读库存新增AVG train-fasttext/seed1，未审计评分继续null；原专家sanitize-git-repo/seed1、AVG qemu-alpine-ssh/seed1仍缺最终archive，不重建候选。reshard seed1在11:15快照时只有约1.65GB app/etc归档及只读恢复准备；11:25后已唯一启动原答案补评，见本文顶部11:27收据，不套nginx/git-leak特殊规则。

[11:11账本](resource_ledger_20261017.md)结束241.293889GPUh、4卡active暂计26.997778，总268.291667；API已核算15.029134794CNY另.328327020USD，未有账本仍unknown。新[存储快照](source_snapshots/storage_20261017_1115.json)：80/data余约1.84TiB、系统/tmp余30.72GiB，本机余28.67GiB，未耗尽；未删原件。**11:15一页阶段PDF**已加入AVG完整SWE分数/区间及新成本，1页/181汉字199总字符/嵌入字形完整/底y98.09，PNG已目视通过，仍非最终report.pdf。

以下10:43及更早记录保留历史，以本轮更新为准。


[T774等待器实际启动收据](avg64_teleport7744_grade_execution_20261017.md)已补齐：10:43:31独立metadata复核2223041/start870388084、43绑定保持、lockfalse、无guard/native/admission、原生成marker尚缺。它是等待状态，不是分数或CPU已交接。

**10:42唯一等待器已启动**：root与独立审阅通过新版fb5a/8cff及真实route receipt后，10:40:56只启动一次T774 parent**2223041/start870388084**；10:41:47仍waiting_source_or_route、lock_held=false、0native。它只在原AVG ASI全240/pool shutdown/源scope空marker与124–127实际scope排空后领取独立未来租约，native仅124/1CPU4GiB3000s，不碰92–95或Terminal到123的原扩容。当前232保存、8在途，不能释放生成核。route依赖Mac专用84416/control socket，结束无消费者后只关自身route，不能因中途断路自动重跑未知原生结果。


**10:39计分更新**：[新strict/预算快照](source_snapshots/formal_aggregation_20261017_1039.json)实际10:38:34，已按三collector指定顺序刷新，root再次通过17人工检查。git-leak seed1 exact native1已显式接入只读overlay，nginx0不变；Terminal专家**177/445有效另5invalid**、AVG**165/445另4invalid**，完整主分及macro仍null、source issues空。SWE专家完整0/51与AVG50/51保持。AVG ASI10:34:45已226/240生成、8在途，科学评分0，未写完成marker。

**T774原站路由已准备**：HPC对AVG自己原IP142.250.73.145唯一HEAD失败，Mac同IP/原URL HEAD200/TLS校验通过；root建立独立Mac ssh84416反向到80 loopback38444，80同URL HEAD也200/TLS0/无正文。route receipt已不可变写出；新driver的reverse识别分支仍待独立审阅，尚无native/claim。仅评分器原站路径，不改变solver禁网、依赖/Go版本、URI或答案，未来仍须等ASI240生成和真实124–127交接。


**10:33接续（最新）**：SWE专家全51题已审结，**0/51=0%**；Base10/51=19.607843%，专家−Base差−19.607843pp，配对95%CI[−31.372549,−9.803922]，如实保留负面结果，不据此换checkpoint或主模型。[51任务对照](swe_task_comparison_20261017.md)记录43空patch/8非空；34项有原request明确context_budget_exceeded，17项exit_status缺失记unknown，不倒推全部失败根因。AVG SWE50/51有效、4resolved、1项Teleport7744仍null，完整分未齐。

[追加SWE最终审核](swe_additional_grade_final_review_20261017.md)：两个T2各自原空patch没有实现任务明确要求接口，原生编译到达产品缺项，root分别接受exact native0；并非14个测试均已执行。NodeBB原生3000s超时/null和EXIT-trap reward1保持；原Mocha335调用去重后311个官方required测试完整覆盖，307P2P全PASS、4F2P全FAIL，经原官方parser和Base同类先例显式批准parsed-report审计0。不是native0或通用timeout归零。专家manifest为8项native0+1项完整报告审计，AVG5项native0。cohort1765416已10:15双native空→停guard→双全scope空→解锁，全部源绑定与预算保持。

**Terminal git-leak原答案已获官方5/5通过。** [原生执行](terminal_git_leak_header_mode_recovery_execution_20261017.md)唯一parent2189065/start870321012于10:29:53产出native1/noHarbor，10:29:59完整排空解锁、44绑定未变，root已独立读原result/config/CTRF/73恢复验证及原测试名并接受exact1。此前2152787恢复校验失败、2170741诊断均在官方测试前结束，原null及失败保留。仅将跨路径硬链alias header0644与canonical600冲突的预期权限归到同inode600；不chmod候选、不拆链、其他72项mode/type/hash仍严格。collector正在追加精确只读overlay，原队列和raw null不覆盖。

[10:26双视图](source_snapshots/formal_aggregation_20261017_1027.json)在三collector指定顺序刷新后生成：Terminal专家171/445另6invalid、AVG159/445另4invalid，均部分coverage且早于git-leak接入；source issues空，AVG四项macro仍null。HLE五完整组、ASI专家240完整和TIES2499/1invalid保持。新[Terminal库存](terminal_invalid_inventory_20261017_1030.md)记录reshard等新增异常；专家sanitize-git-repo/seed1与AVG qemu-alpine-ssh/seed1缺最终归档，继续null，未重建候选或答卷。

[AVG T774独立准备](avg64_teleport7744_grade_preparation_20261017.md)已审原IP为142.250.73.145，与旧专家不同；旧38443关闭，尚无新route或native/claim。新prepare-only脚本拟CPU124/1CPU4GiB3000s，独立124–127锁/guard；两Terminal现及全部既有扩容只到123，但124–127仍属AVG ASI生成，必须等240生成完成/worker pool关闭marker与真实scope排空，不能凭瞬空抢占。root尚未批准执行，先核原站TLS路由与独立审阅，不动92–95科学评分或stage2。

当前三个普通acd_u/Nice1000 TP2共**6H100**：727912/727913/727856；没有新增、重建或emergency。AVG ASI10:10保存193/240、8在途，10:22约205/240，科学评分0，原1126014/1126055和28095接续；生成/全CPU marker未齐。future评分仍workers1/global92–95/原runtime和预算，Terminal12/11槽0–91保持。01:10 metadata guard1508852仍唯一等待，不伪造完成marker。

[10:10成本](resource_ledger_20261017.md)结束227.570GPUh、6卡active暂计35.190556，总262.760556；API仍15.029134794CNY另.328327020USD，缺账本unknown。10:18 /data余2,060,775,186,432B，未耗尽。**10:33一页阶段PDF**已加入SWE真实退化及区间，摘要181汉字/199总字符、1页/字体嵌入/缺字0，PNG目视通过；仍非最终report.pdf。

以下09:25及更早记录保留历史，以本轮更新为准。


**Terminal离线准备补充**：[git-leak原归档恢复条件](terminal_git_leak_grade_only_preparation_20261017.md)已核50个app成员/46个.git成员，独立副本fsck完整检查rc0且无输出、无外部对象依赖，30来源绑定保持。记录23处精确etc差分和跨路径硬链`/etc/apt/apt.conf.d/01-vendor-ubuntu`→`/app/repo/.git/info/refs`；未来恢复必须保留该拓扑、排除resolver，不能盲恢复全etc。尚无该项driver/claim/native/成绩，先等SWE1765416合法收尾，再准备独立4CPU/8GiB/900秒grader租约；建议2400秒准入余量。

**09:25:51实际原生核验**：恢复cohort三个child1765421/22/23的实际CPU分别92/93/94，各native scope为4GiB/swap0，parent1765416持global锁，guard92–95/32MiB。NodeBB原patch应用成功并进入官方测试；两T2复制原Go缓存，接近4GiB但采样OOM/OOMkill0。已通过原namespace启动阻塞，尚无终态或恢复分数；全部原绑定保持，见[执行收据](swe_additional_short_tmp_recovery_20261017.md)。

**09:25接续（最新）**：[09:13:51正式双视图](source_snapshots/formal_aggregation_20261017_0915.json)按三collector指定顺序刷新后生成strict与独立预算视图，source issues空。两SWE各**49/51有效**，专家0resolved、AVG4resolved，各2invalid，完整分仍null；Terminal专家**141/445另3invalid**、AVG**131/445另3invalid**，均是部分coverage。HLE五组完整成绩和ASI专家240完整成绩不变，AVG四项macro仍null。

**两Vuls已分别接受exact native0。** [审核](swe_vuls_grade_review_20261017.md)和root重读确认：各自原空patch保留三参数接口，官方任务要求四参数，新编译明确到达该产品错误；无Harbor异常，不能称11个测试都执行失败。各自原29绑定、SIF stat及1CPU/4GiB/3000秒保持，保存OOM/OOMkill0，双native空→停guard→双全scope空→解锁完整。manifest现专家7项/AVG4项批准，原raw null保留，不跨模型借评分。

**三个追加补评分正在启动恢复。** [初次cohort](swe_additional_grade_only_execution_20261017.md)于09:18启动后都在namespace relay失败，agent/verifier未开始、reward null：新host TMPDIR过长使内部socket达263–272B，超过Linux108B限制。这是本轮工程疏漏，原失败及实际源码已归档。安全排空后只改两行，短路径实际bind78/82/82B及默认prepare三项各38绑定通过；root/direct独立审阅后，**09:24:49唯一恢复parent1765416/start869931371**已启动，见[恢复收据](swe_additional_short_tmp_recovery_20261017.md)。新根`artifacts/recovery/swe-additional-short-tmp-20261017`，script冻结7da575a6、新manifest b6dcd844；E/NodeBB92、E/T2 93、AVG/T2 94，各1CPU/4GiB/3000秒，单global92–95租约/guard，0模型调用。所有原答卷/测试/预算保持，pending_root_review不自动valid；不能由启动修复声称旧超时已解决。AVG T774仍仅静态原proxy方案、未准入。

**Terminal新增异常保留null。** [git-leak-recovery/seed1](terminal_new_invalid_audit_20261017.md)在求解1800s后的cleanup guard阻断评分交接，verifier未开始，不是900s评分计算超时，不能派生预算0。归档含.git，完整恢复条件仍在只读核查，未启动该项native/claim；nginx旧raw null和已批准exact0 overlay均保留，不重复评分。

[09:10 Direct核查](direct_status_20261017_0910.md)：AVG ASI保存132/240、8在途、100未准入，科学评分0；coordinator1126014/generator1126055唯一正常，复用727856/28095。仍三个普通acd_u/Nice1000 TP2共**6H100**，无新卡或重建。96–127未来生成租约保持；Terminal12/11槽用0–91，stage2等两ASI真实marker及scope排空，不能取回已交接核。唯一metadata guard1508852/start869510981仍等明日01:10，两STOP尚无，不重复创建。

新增[HLE完整配对表与20例补充](hle_base_avg_disagreements_20261017.md)：都对38、Base对AVG错61、Base错AVG对79、都错2322；61项中35有AVG答案、26原生无答，固定ID排序取20个有答案例。未公开题面/金标/答案，原20失败保留；历史服务混杂和语义原因unknown继续披露，不当纯权重因果退化。

[09:13资源账本](resource_ledger_20261017.md)：结束227.570GPUh、6卡active暂计29.532778，总257.102778；API仍15.029134794CNY另.328327020USD，缺失unknown。09:24恢复准入时80/data余2,126,852,165,632B，MemAvailable1,988,225,520kB；未耗尽，新scratch走/data。完整单项未变化，保留07:28一页阶段稿。

以下08:20及更早保留历史过程，最新阶段以上述09:25为准。

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
