## 2026-10-17 14:47 CST：原专家结果更新，低LR SWE候选训练已完成

用户问原四专家是否已有完整结果。本轮按三collector顺序刷新并保存strict/terminal_budget双视图，实际14:45:58/14:46:01：SWE249 **51/51、0%** vs Base19.607843%；HLE250 **2500/2500、6.92%** vs Base3.96%；ASI128 audited **240/240、0.378991%归一化得分** vs Base1.570988%。ASI仅核冻结结果，不重复一次性collector；HLE含342图，替代Judge/public-local/历史服务混杂保持。四专家只测各自目标项，不冒称4×4全矩阵。

Terminal250 **285/445有效、7异常、153待完成**，完整主分/五次标准差仍null，不用部分coverage算全量分，异常不填0。本轮仅汇总，没有恢复/重试评分、改预算或生成新答卷。Base strict442/445+3invalid，独立既有预算视图445/445=20.224719%不能混报成strict；AVG64 ASI94/240有效、Terminal263/445另6异常/176待完成，完整macro仍null。具体表及source见analysis/original_experts_status_20261017_1447.md和formal_aggregation_20261017_1447.json。

此前用户授权的728713低LR+32K完整轨迹筛选SWE候选已**COMPLETED/0:0**，Slurm00:57:52、global_step128/epoch1.0、final checkpoint-128/84,760,832字节，620FP32 A/B tensor/r16alpha32；只读summary/state/header核产物，无大hash/新forward/loss选模。GPU4已自然释放，当前仅原727912/727913共4H100。新候选尚无任务评测分数，不替换旧SWE249/主AVG64/ASI128，也不自动合版或发布；完整完成收据单独保存。

更新claud/current_status与候选执行记录，仅提交owned/保留foreign WIP，无coauthor；自动化保持删除，不创建其他定时任务。HPC训练source/config和旧bound执行文件均不重写，静态文档仅独立同步。


## 2026-10-17 13:58 CST：SWE候选首批真实更新已完成

728713普通acd_u/Nice1000、ACD1-19同节点4H100已完成真实optimizer更新，13:58:11原生logging.jsonl为**3/128**，实际加载**1025 train/87历史teacher-forced held-out**；原两条角色格式错误整条删除，导出1027不冒称全部参与。首步loss0.51078051/gradnorm0.33788907/LR5e-6；第3步loss0.55829525/gradnorm0.37195792/LR1.5e-5均有限，peak仍2e-5、4步warmup。这里仅说明训练在运行，不作为质量分或选模证据。

原生日志已生成TensorBoard event文件；本机6006尚未同步新run，不声称自动实时可见。首步137秒含冷启动，后两步合计约59秒；当前原生含首步均速65.30秒/步，剩余2h16m仅初步滚动估计，不能当完成承诺。GPU已实际有4个本rank进程、约46GiB/卡分配、Triton缓存增长；未重启/截断/新增服务，当前仍原4卡+新4=8卡。

独立新收据analysis/source_snapshots/swe_lr2e5_max32k_native_start_20261017.json保存实际配置diff、squeue/scontrol、原生metrics、TB路径和实际加载数，candidate尚未完成。run/plan/源文件已bound，HPC同步只更新静态文档，不重写它们。33d1da8已push两remote并同步静态；本轮仅补实际进展与claud追加，保留foreign WIP，无coauthor。自动化保持删除，不新增loss-only/task-val或正式生成/评分，不更换冻结主AVG64/ASI128；新候选会按原生一epoch自然完成并释放其4GPU。


## 2026-10-17 13:50 CST：已启动低LR＋完整长轨迹过滤的SWE候选

用户明确授权降低LR重训，随后允许筛掉过长轨迹。新候选从原Base重新初始化，峰值LR **2e-5**，整条保留原HF完整序列≤32768的**1027条/23,353,670完整token/5,034,955 assistant输出token**，排除973条；原行bytes/顺序/工具观察/最终提交全部保留，不截断，不把训练max_length从65536调小。原87条held-out仅teacher-forced诊断；没有恢复task-val。源角色错误223/279仍在，实际加载数/步数以后续原生日志为准，预计可能1025。

[执行记录](swe_low_lr32k_execution_20261017.md)：原728711在容器检查阶段1秒FAILED，wrapper将单独--project目录参数误当sandbox，未进入Python/加载模型；只改成原成功脚本相同--project=PATH，保存原源/失败日志/终态，确认旧job退净后13:48:28唯一重提**728713**。13:49:56新job已RUNNING于**ACD1-19、普通acd_u/Nice1000、同节点4H100/24CPU256G/4h**。4-rank命令和原生config已写，原生日志暂空、初始化中，不能称首步完成。当前原727912/727913共4GPU＋新4=**8H100**，无emergency或新服务。

新run `artifacts/runs/swe-lr2e5-max32k-728713/`，唯一control `artifacts/runs/swe_lr2e5_max32k_control_20261017/attempt2/`；已有claim/job，不重复sbatch。独立审阅实际配置与原726335仅7项预期变化：LR、train/val路径、新output/TensorBoard/run_name；原batch8/累积2/r16alpha32/一epoch/cosine/warmup.03/wd.1/非thinking/preserveFalse/ZeRO3/SDPA/grouped_mm/Liger保持，不resume旧adapter。此前空think壳差异此候选未改；联合改变LR和样本/长度/步数，不能声称LR单变量或已修根因。最终checkpoint固定，不按loss选优，不自动替换冻结AVG64/专家。

[筛选记录](swe_low_lr32k_data_20261017.md)含32K/48K/64K分布、原行映射与1027行逐字节检查；HPC基于既有原数据用同脚本重新导出一致计数。原生TensorBoard2.21日志已启用，旧本机6006仍是原五组，未冒称新曲线已同步。原版耗时约2小时，新版待实际吞吐估算。自动化继续删除，既有正式评测与64K/8K协议、ASI128和主AVG64冻结；未新生成正式答卷或Judge评分。下方13:40及以前为历史记录。

## 2026-10-17 13:15 CST：手动训练诊断，TensorBoard已启动

小时自动化已删除，保持取消。按用户要求查看LR/entropy并优先TensorBoard；[五组训练标量与实际收据](swe_tensorboard_diagnosis_20261017.md)已导入本机127.0.0.1:6006，session75430保留运行。SWE峰值LR1e-4/第8步/249步，gradnorm最大0.53184且全有限，无明显梯度爆炸；entropy原本未记录，不能由loss反推熵塌缩。标量wall_time为导出时间，用step轴；loss仍只诊断，不复活task-val或选checkpoint。

[真实训练模板诊断](swe_serialization_parity_20261017.md)发现Swift比HF少7个空think壳/28tokens；同一输入仅CPU实例preserve_thinking=True即5959tokens/全部8轮前缀及完整labels一致，940监督token不变。全2000+87输入已核无隐藏reasoning/think标签。原配置、数据、服务不变，未重训；单样本编码修正尚未证明任务改善。[数据审计](swe_training_repetition_audit_20261017.md)最长相同命令连续3次，未见已有100次复读直接混进训练；来源抽核3条边界如实保留。

[LoRA静态诊断](swe_lora_serving_diagnosis_20261017.md)未见明显映射/缩放故障，但数值和长程状态尚未证实。六固定前缀entropy/KL/backend探针准备完，HPC提交预检因默认Python3.6的capture_output失败，发生在claim/sbatch之前；没有jobID/新GPU/forward，用户转向TensorBoard后未重试。当前仅原727912/727913两TP2共4H100普通acd_u/Nice1000，未重建释放端点。下一版若推进，先统一编码，再在同一模板下1e-4 vs2e-5单变量对照，尚未执行。

正式分数、checkpoint、主AVG64、ASI128和原每题预算冻结；没有新训练、模型/Judge调用、补评分或改collector。TensorBoard是本机查看已有日志，不是恢复定时自动化。浏览器已读到scalars且task58完成keeptrue，截图超时不冒称目视验收；Codex面板仅queued。此次不重跑正式统计/PDF，以下12:10及更早状态保留历史。

# 当前进展与未决事项

**SWE下降诊断（12:33）**：[新增证据与边界](swe_regression_diagnosis_20261017.md)。全51题Base/专家/AVG空patch为3/43/34，context guard为18/34/11；3个专家退化例同一只读命令分别重复106/162/205次、多返回rc0但两例管道掩盖grep/ls错误，模型没有纠正，最终空patch，无捕获失败。SFT内部根因尚未确定，不能直接归因为合版、路径、过拟合或仅上下文长度。只有只读诊断，原评分/权重/预算与取消自动化保持。

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


## 2026-10-17 16:30 CST：新低LR SWE候选正式评测启动与HPC沙箱修复

用户要求评测新SWE候选 `checkpoint-128`。候选服务 `728866` 在 ACD1-30、普通 `acd_u/Nice1000`、TP2、别名 `apex-val-swe-lr2e5-max32k` 健康，LoRA已加载；固定HARD51评测仍使用64K上下文、8K输出、non-thinking、官方任务/测试和每题预算，不重生答案。

评测入口先后保留了 retry1–retry3 的基础设施失败：HPC glibc 2.28 无法加载评测包的 glibc 2.33 `slirp4netns/libslirp`，导致51题均在任务前失败。随后在项目目录放置从已配置Ubuntu 2.35主机取得的用户态兼容loader/库，最小namespace readiness通过。继续诊断发现HPC无user-systemd、SIF FUSE挂载被禁用、默认96线程unsquashfs在4GiB任务限制下OOM、fakeroot无subuid、runtime/uv/wheels/mini约束未同步，以及runtime venv仍指向80的绝对路径；这些均分别在 retry4–retry18 留存原始日志，未将它们计为模型失败。

当前HPC专用评测路径为：项目内glibc235 slirp loader；Slurm 128GiB作业中的直接CPU亲和路径（无user-systemd时）；按SIF digest的已解包rootfs；不使用fakeroot；单进程unsquashfs配置；同步的SWE runtime/wheels/uv/mini约束；修正HPC `pyvenv.cfg`。这些是评测环境适配，不改变题目镜像内容、题目代码、官方测试或模型协议。由于HPC没有systemd cgroup，直接路径不提供原systemd MemoryMax；该偏离需在报告中披露，不能冒充完全同构官方环境。

retry19 的 Vuls 单题已实际越过沙箱启动、runtime安装和模型服务连接，生成 `mini-swe-agent.trajectory.json`（约241KB，28步仍在求解）；尚无 `result.json`/replay/verifier 结果，严格SWE分数仍null。此前所有重试没有模型请求；retry19 才是首个可审计真实模型轨迹。单题按原1800秒预算自然结束后，先独立审计轨迹、patch、replay和资源清理，再决定是否把同一适配路径扩展到HARD51；不因单题未完成而手填0、重生答案或改变预算。

新增/修改的HPC适配代码仅为可选路径：`baseline_netns.py`兼容loader、`baseline_singularity.py`直接限额/无fakeroot/rootfs目录、`baseline_exec_limits.py`、`swe_baseline_v2.py`的无root离线mini安装，以及对应retry配置；默认systemd/fakeroot路径保持原行为。训练分数、loss、旧SWE249/AVG64/ASI128身份均未改。

## 2026-10-17 17:20 CST：ASI退化定位与Terminal单次运行口径

- ASI128与Base使用同一 public/local replacement Judge、同一240条件（60任务×B1–B4），分数分别为0.3789913819%与1.5709884069%，配对差−1.191997pp，95% CI [−2.278710,−0.303023]。两侧分母、score divisor和聚合公式已核对，未发现缩放错误；服务验收也通过同一alias、64K/8K、nonthinking和direct_llm协议。
- 逐任务方向为3升、11降、46平；最大下降五项约占净降82.04%。训练数据1073条中82条是完整SAB程序，976条DS-1000函数/片段，15条SciCode函数或主解。ASI正式direct_llm要求单次完整Python程序读取工作区并写声明产物，且只提取闭合code fence、执行一次；这使静态函数/片段监督与正式产物契约发生明显错配，是当前一级假设。
- 观察到的失败包括12条8192截断导致未闭合fence、36条未声明import、1条pyscf子模块路径和48条其他程序/API/数据/CLI错误。它们是观察分类，不把全部失败归因训练；学习率1e−4、LoRA r16/alpha32、单epoch是待用低LR复训验证的次级因素。ASI train/val loss无发散证据，loss继续只作训练诊断。
- 详细证据见 `analysis/asi_drop_and_terminal_one_run_20261017.md` 和 `analysis/asi_base_expert_task_comparison_20261017.md`。
- 用户明确改口：后续新Terminal评测每个89任务只跑一个固定seed/attempt（共89次），不再启动五次重复；已有445条五seed结果、均值和SD全部保留，不覆盖、不混报。新单次结果必须使用独立manifest/结果目录并标注 `single-run exploratory`，不能称满足题面五次均值/标准差。当前不因该改口重跑已有Terminal答案。

## 2026-10-17 17:30 CST：新SWE候选retry23实际开始

- HPC 51 个固定SWE镜像 rootfs 已重新解包并逐目录验证 `bin/bash`/`usr/bin/bash` 均存在；retry20–22 的旧基础设施失败保留，不计入模型成绩。
- 发现旧服务脚本固定读取通用输出目录，第一次启动未进入新目录；该路径已自然结束且未纳入新分数。随后用独立 `configs/eval/swe_lr2e5_max32k_retry23_hpc_20261017.json` 和 `artifacts/eval/swe_lr2e5_max32k_retry23_20261017` 直接启动 runner，Slurm step `728866.50`，10 CPU、复用候选服务 `728866` 的2卡端点，普通 `acd_u/Nice1000`。
- 17:28 快照为 `running`、10 个 active、40 个 pending、0 valid scored；固定51题、64K/8K、nonthinking、每题1800秒和官方测试不变。当前没有可报告的SWE分数，完成后再独立审计。
- 17:34 更新：服务节点 ACD1-30 发生 Slurm `NODE_FAIL`，728866 与 step 728866.50 同时终止；不是模型 reward。retry23 10 个 active 均无 generation/replay result，已保留原始目录并登记 `node_fail_recovery.json`，重新排回50个待处理项。新服务729431已按普通 `acd_u/Nice1000` 提交，但当前仍 `PENDING(Priority)`，不擅改优先级或启用emergency。

## 2026-10-17 18:46 CST：SWE候选评测仍未取得分数

- 低LR候选训练728713已完成，checkpoint-128可用；但retry23在服务节点ACD1-30发生NODE_FAIL，当前checkpoint为`recovered_after_node_fail`、`valid_scored=0`，没有把节点故障计为模型失败。
- 新候选服务729431仍为普通`acd_u/Nice1000`、2 GPU/16 CPU/128G，状态`PENDING(Priority)`，预测启动时间已滚动到10月18日约14:59，不能作为保证；因此新候选尚无SWE分数。
- 已有旧SWE专家正式结果仍为0/51，Base为10/51，AVG64为4/51；这些是旧冻结结果，不代表低LR候选。

## 2026-10-17 21:46 CST：新LR SWE仍在等待GPU服务

- 实时检查：服务729431仍为普通`acd_u/Nice1000`的`PENDING(Priority)`，申请2 GPU/16 CPU/128G；Slurm预测启动时间滚动到10月18日00:49，不能视为保证。
- retry23状态仍为`recovered_after_node_fail`、0/51 valid scored、0 active、50 pending；没有把节点故障计为模型失败，也没有新的模型请求或分数。
- 若00:49后才获得服务，按51题完整队列的历史时长，完成时间可能超过02:20核心实验窗口；不擅自改Nice、启用emergency或缩短每题预算。

## 2026-10-17 21:50 CST：用户授权提高新LR SWE优先级

- 按用户授权，将服务729431的Nice从1000提高到0，仍是普通`acd_u`、2 GPU/16 CPU/128G；Slurm优先级由2355升至3355。
- 负Nice进一步提权被Slurm拒绝（权限不足），未启用emergency、未取消其他作业、未改变评测预算。GPU碎片仍可能使预计启动时间晚于核心窗口。

## 2026-10-17 22:00 CST：停止新LR候选，整理第一次训练结果

- 用户决定不再等待新LR SWE 候选；等待中的729431已取消。新LR checkpoint、retry23节点故障证据和配置均保留，但不纳入主结果。
- 第一次训练结果已整理到 `analysis/first_training_results_summary_20261017.md`，涵盖Base、四专家、Mixed、AVG64、训练曲线、benchmark分数和协议限制。后续汇报以该摘要和冻结strict结果为准。

## 2026-10-17 22:10 CST：Mixed与最终缺口核对

- Mixed883只完成HLE正式2500题，结果146/2500=5.84%；没有SWE、Terminal或ASI正式全评。它是训练对照，不是主合版，也不要求自动扩成四项全评。
- 题面硬性最低矩阵是：Base四项全量；每个专家至少完成自己的目标项；最终选定合版四项全量；至少一个可解释训练对照；至少两种合版方法或关键配置消融；训练曲线、宏平均/配对区间、失败案例、成本和可复现交付。
- 当前关键缺口：Base Terminal strict仍3 invalid；Terminal专家和AVG64 Terminal未完成；AVG64 ASI未完成；因此最终AVG64四项macro仍null。AVG64已有完整SWE/HLE，Mixed已有完整HLE，AVG16也只有HLE对照。
- 合版方法/消融已有AVG64与AVG16辅助对照及TIES-Dense HLE-only材料，但尚不能称完成四项方法比较；最终还需整理对照解释、20个失败案例、最终一页report.pdf、资源/成本和提交索引。

## 2026-10-18 01:40 CST：继续全量评测的最终口径

- 用户确认：继续推进正式评测；Terminal 后续每个任务只跑一次固定 seed/attempt，不再启动五 seed；合版消融先只看 HLE。
- HLE 对照已整理：HLE专家6.92%最高，Mixed5.84%，AVG64 4.68%，AVG16 4.04%，Base3.96%；因此 AVG64 不是 HLE 最优。TIES-Dense仅2499/2500有效，保留为未完成方法对照。
- Terminal现有服务727912/727913将在02:01/02:09左右到期，当前剩余时间不足以完成新的89题单次全量队列；不启动注定无法完成的半截队列，历史445条结果继续保留并与新single-run口径分开。

## 2026-10-18 01:45 CST：invalid修复审计与每小时推进

- 用户要求修复所有 invalid。已创建每小时 heartbeat automation `apex`，每轮优先处理有明确证据的 grade-only 工程恢复；未知、环境故障、缺少原件和无授权重答项继续保留 null，不伪造分数。
- 已知可接受的修复包括部分 SWE 原答案 native0、Terminal git-leak/nginx 的精确审计 overlay、ASI CMOS import 恢复；这些不重生成答案。仍未闭合的 Terminal invalid（cleanup guard、依赖供应、缺少归档）需逐项审计，不能统一重跑。
- 当前终端服务接近自然到期，没有新 GPU 或 benchmark 队列；自动化在核心截止前只做安全审计和已有资产整理，截止后不启动新实验。

## 2026-10-18 03:18 CST：自动检查收尾

- 只读核对显示 Terminal 专家服务727912和AVGExec727913已按原TimeLimit自然`TIMEOUT`，batch被Slurm正常取消，未发现新任务控制器或模型请求。
- 截止核心窗口后不再启动新的GPU、Terminal single-run或grade-only任务；invalid继续按证据分类保留，后续仅整理报告、统计快照和复现索引。

## 2026-10-18 04:22 CST：截止后只读审计

- 本轮按核心窗口后的规则仅做只读核对。HPC `hpc3` 当前 `squeue` 为空；Terminal专家服务727912和AVGExec服务727913均已自然 `TIMEOUT`，分别运行21:35:28和21:43:29，未发现新的GPU、benchmark控制器或模型请求。等待中的新LR SWE服务729431已取消，不能产生新分数。
- invalid修复状态没有安全新增项：Base Terminal 3条计算型timeout、Terminal专家7条、AVG64 Terminal 6条异常、TIES-Dense 1条缺`correct`继续保留原始证据和null；没有满足同一答卷/环境/预算/完整排空条件的grade-only恢复，不填0、不重答。
- HLE现有消融排名保持：HLE专家6.92% > Mixed5.84% > AVG64 4.68% > AVG16 4.04% > Base3.96%；因此AVG64不是HLE最佳。主AVG64四项宏平均仍因ASI和Terminal coverage不足而不能计算。
- 由于已超过2026-10-18 02:20核心截止，后续automation只整理报告、统计快照和复现索引，不再启动新的GPU、Terminal single-run或benchmark任务。

## 2026-10-18 05:23 CST：只读状态无变化

- HPC `hpc3` 队列仍为空；没有新的 GPU、benchmark controller、模型请求或 grade-only 任务。727912、727913 仍以自然 `TIMEOUT` 作为最终服务状态，729431 仍为已取消且无分数。
- invalid 分类与 HLE 消融结果无变化。Terminal/ASI coverage不足、Base Terminal strict invalid、TIES-Dense缺失`correct`继续保留原始证据和null；AVG64四项macro仍不能发布。
- 本轮未修改评测资产；只将状态记录于本文件和统一进展文档。后续继续保持截止后的报告整理模式。

## 2026-10-18 06:18 CST：只读审计无新结果

- 本地和 `hpc3` 核对均未发现新作业或新评测结果；队列为空，727912/727913 仍是自然 `TIMEOUT`。工作区保留既有其他会话 WIP，本轮没有整理或覆盖它们。
- 当前 strict 结果、invalid 分类、HLE 消融排名和 AVG64 macro 缺口均无变化。由于核心窗口已结束，继续只做报告与复现索引整理，不发起新的 GPU、benchmark 或 grade-only 作业。

## 2026-10-18 07:28 CST：只读审计无新结果

- `hpc3` 用户队列和全队列均为空；近期只有已记录的727912/727913自然超时、728713训练完成、728866节点故障、729431取消，未出现新的GPU或benchmark结果。
- 工作区仍保留既有多会话WIP，本轮不覆盖、不提交；strict结果、invalid分类、HLE消融和AVG64宏平均缺口没有变化。
- 继续遵守截止后规则：只整理报告、成本与复现索引，不启动新任务。

## 2026-10-18 08:25 CST：只读审计无新结果

- `hpc3` 队列为空，未发现运行进程或新 benchmark controller。728866 的节点故障、729431 的取消和727912/727913的超时状态均与既有记录一致；retry23仍是0个有效计分，原始产物保留。
- 本地工作区仍有既有未提交WIP，HPC项目镜像没有新的可同步Git状态。本轮不修改这些资产，不启动新的GPU、benchmark或grade-only任务。

## 2026-10-18 09:33 CST：只读审计与遗留镜像同步

- `hpc3` 的 Slurm 用户队列和全队列仍为空，没有运行中的评测作业或 benchmark controller。发现一个更早启动的非Slurm背景进程 `mirror_benchmark_sifs.sh`（PID 19075）仍在同步镜像；源进度为 `finished`、140个镜像中138个完成、2个 ProtonMail webclients 镜像失败。该进程不是新评测任务，本轮未停止或重启，完整性收据仍未更新为complete。
- 728866/729431/727912/727913状态与此前记录一致，retry23没有有效计分；invalid、HLE消融和AVG64宏平均缺口没有变化。
- 截止后仍只做报告和复现索引整理，不启动新的GPU、benchmark或grade-only任务。

## 2026-10-18 10:22 CST：停止自动化并冻结项目状态

- 用户要求停止每小时自动化；heartbeat `apex` 已在 Codex 自动化服务中删除，不会再按小时触发检查。
- 当前 HPC 无 Slurm 作业；727912/727913 已自然超时，728866 为节点故障，729431 已取消，retry23 无有效分数。非Slurm的SIF镜像同步进程仍按原状态保留，未将其误认为评测服务。
- 项目结果冻结为现有 strict/审计视图：第一次训练结果、HLE合版消融、ASI/SWE对照和已记录的Terminal覆盖均以现有文件为准；不补造AVG64四项macro、不把partial coverage或invalid填成0。

## 2026-10-18 10:24 CST：按题目要求核对剩余交付项

- 实验性硬缺口：Base Terminal仍有3条strict invalid；Terminal专家目标项、AVG64 Terminal和AVG64 ASI没有完整有效覆盖；因此最终合版四项全量矩阵和宏平均不能宣称完成。Terminal官方五次均值/标准差及3小时/32CPU/48GB/256K设置也未实现，已有445条历史结果必须按实际协议披露。
- 合版消融已有AVG64/AVG16和TIES-Dense的HLE材料，但TIES有1条invalid且没有四项完整结果；应在报告中标成部分HLE-only对照，不能包装成完整两方法四项比较。
- 可整理交付项：最终一页`report.pdf`、最终成本/GPU小时账本、README中的模型链接/revision/merge recipe、逐任务结果索引和完整复现路径仍需最后核对。20个失败案例、训练曲线和主要实验记录已经存在。

## 2026-10-18 11:25 CST：AVG64 ASI 已有完整 score-only 结果

- 复核 host80 远端 `artifacts/eval/avg64_asi240_20261017`：240/240 条生成、240/240 条评分、active/unsubmitted/scorer error 均为0，CPU消费者已排空。该结果不需要新生成或模型调用。
- public local replacement Judge 的完整分数为 `110.56851907426662/24000 = 0.4607021628%`；`official=false`，Judge 为`deepseek-flash`，revision未固定。原始 answer JSON 中222/240状态为failed，但保存的轨迹/代码/outputs均存在，评分器将失败尝试作为0分保留；若要改善这些失败需要新生成，不能把它们误写成成功。
- 因此此前“AVG64 ASI 94/240未完成”的汇总已过时，已新增 `analysis/source_snapshots/avg64_asi_complete_20261018.json` 并修正第一次训练汇报。AVG64 四项 macro 仍因Terminal coverage不完整而不能计算。

## 2026-10-18 11:31 CST：开始补齐实验硬缺口的可行性审计

- 用户明确要求补齐硬缺口。已先按不重生答案原则审计：AVG64 ASI 可直接采用远端已完成的 score-only 结果；Base Terminal 三条仍只有 fixed-budget 派生0，strict native reward缺失，若要补strict必须实际重跑原verifier。
- Terminal 专家和AVG64 Terminal是否按题面五次运行重启，与用户此前“只跑一次”的口径冲突，已单独请求确认；在确认前不启动新的Terminal队列，避免产生无法归类的半截结果。

## 2026-10-18 11:29 CST：补齐审计的最新阻塞

- Base Terminal 三条 strict invalid 已确认原答案、原归档、原SIF和900秒timeout证据都在，但缺少三条对应的 exact frozen restore manifest；现有 manifest 明确把它们列为 excluded computation timeouts。没有 manifest 前不推测解压步骤、不运行 verifier。
- AVG64 ASI 的240/240 score-only结果已落本地证据快照；当前真正仍依赖用户口径确认的是Terminal专家/AVG64 Terminal是否恢复为题面五次运行。

## 2026-10-18 11:31 CST：Terminal 445 队列已结束，转入 grade-only 修复

- 复核 host80 两个历史445 controller：两边均已 `all445_attempts_finished`、active/pending为空、CPU消费者排空。Terminal专家为 `valid_scored=428/445`、17条 infrastructure-unscored；AVG64为 `435/445`、10条 infrastructure-unscored。此前只汇报的285/263是较早中间快照。
- 两个模型服务已结束，不能继续生成；现有答案完整保留。专家17条中已有3条独立grade-only产物待接入，另有9条具备archive；AVG64 10条中8条具备archive。下一步只对有完整archive和可复现原verifier的条目做独立grade-only，不重生答案、不启服务、不改原summary；已知依赖/输入故障继续null。
- Terminal仍不改变用户先前的单次 exploratory 口径；本轮修复的是已经完成的历史445答案的工程性 invalid，不会把grade-only覆盖混入新的单次队列。

## 2026-10-18 11:35 CST：两条专家 grade-only 仍为环境 invalid

- 已执行并审计专家 `pytorch-model-cli/seed2` 与 `query-optimize/seed3` 的独立 grade-only。两条均未进入官方 verifier：前者为 `nsenter: singularity 不存在`，后者为 `baseline_exec_limits.py OSError: [Errno 22] Invalid argument`。
- 两条均保持 `verifier_result=null`、`new_model_calls=0`，原始结果/归档/445 summary 未改；独立输出和 SHA 收据见 `analysis/source_snapshots/terminal_grade_only_execution_20261018.json`。按规则不重试、不填0。

## 2026-10-18 12:10 CST：Base 三条 grade-only 修复仍被恢复环境阻塞

- Base 三条 attempt3 均因归档中的 `etc/resolv.conf` 与环境预挂载文件冲突，未进入 verifier。对 FEAL seed0/seed4 做了一次最小 attempt4，仅使用 `tar --exclude='etc/resolv.conf'`，其余归档成员、SIF、依赖、候选和900秒预算不变；两条仍在restore阶段约180秒后超时，未产生测试输出或reward。model-extraction seed4保持同类恢复失败。
- 所有 attempt 已排空，原结果和strict summary未改；三条继续保留 `null`，不再扩大排除范围或盲目重试。该硬缺口需要更完整的环境恢复方案才能安全修复，不能靠派生0闭合。

## 2026-10-18 12:15 CST：历史445结果不能直接抽成完整single-run

- 逐seed核对历史445：Terminal专家各seed有效数为86、85、87、85、85；AVG64各seed为86、87、88、87、87，均没有89/89完整seed。缺口主要是train-fasttext等已知环境项，以及少量独立invalid。
- 因此不能从现有结果直接抽出两个模型都完整的single-run；只能抽出partial coverage。Base历史结果另有seed1–3达到89/89，但不能与专家/AVG64拼成完整公平矩阵。
- 新的single-seed目录已准备但尚未提交服务；若继续，应预先固定一个seed并只补该seed的缺失任务，单独报告single-run exploratory，不改旧445结果。

## 2026-10-18 12:20 CST：seed2 single-run 已补齐

- 固定 seed=2 后，仅补三条缺失任务：Terminal 专家 `pytorch-model-cli/seed2`、`train-fasttext/seed2`，AVG64 `train-fasttext/seed2`。三条均取得 native reward=0，历史445结果和summary未覆盖。
- 得到两个完整 single-run 行：Terminal专家 **8/89 = 8.988764045%**，AVG64 **11/89 = 12.359550562%**。`train-fasttext` 的官方 pytest 已在固定离线CPython3.11.14环境中运行，候选缺少`/app/model.bin`，所以0分是有效native结果。
- 该结果只标为 `single-run exploratory`，不能替代Terminal官方五次均值/标准差，也不与历史445条混合。证据见 `analysis/source_snapshots/terminal_seed2_completion_20261018.json` 和 `analysis/terminal_seed2_completion_20261018.md`。

## 2026-10-18 12:26 CST：补齐后剩余项目清单

- 实验结果层面：Terminal专家/AVG64已有完整seed2 single-run；Base strict Terminal三条仍是native null；AVG64的正式四项macro仍不能发布，因为Terminal这一项采用了用户确认的single-run exploratory口径。
- 题面协议层面：Terminal五次均值/标准差和3小时/32CPU/48GB/256K设置未实现，需在README/report中明确标注为协议偏离，不再追加五次运行。
- 合版层面：AVG64/AVG16与TIES-Dense已有HLE对照，但TIES仍1条invalid且没有四项完整对照；只能作为部分消融披露。
- 交付层面：剩余工作主要是最终report.pdf、结果矩阵/CI/失败率、资源/API成本账本对账、README模型revision与merge recipe、复现索引收口。训练曲线、20个失败案例和主要配置已存在。

## 2026-10-18 12:43 CST：TIES-Dense invalid 已完成离线 score-only 修复

- TIES-Dense HLE 唯一缺`correct`的条目已用两份冻结 HTTP200 Judge body 做独立离线解析；原文明确为 `correct:no`。新增 API/Judge/model 调用为0，原始 result/summary 不改。
- 独立 overlay 将 disclosed complete 视图补为 **131/2500 = 5.24%**，并保留原始 invalid；这不是官方 Portal 重判。manifest/result/summary 及 SHA 位于 `artifacts/eval/ties_dense_hle2500_20261017/scoring/offline-score-only-overlay-20261018/`。

## 2026-10-18 12:45 CST：最新剩余项核对

- 已完成：四专家第一次SFT、AVG64 ASI 240/240、TIES-Dense HLE离线overlay、Terminal专家/AVG64 seed2 single-run 89/89，以及HLE/训练/失败案例材料。
- 仍需披露而非继续重跑：Base Terminal strict 3条native null；历史445 Terminal的环境型invalid；Terminal single-run与题面五次均值/资源配置的偏离；AVG64正式四项macro不能用exploratory Terminal行替代。
- 交付收口：最终`report.pdf`、最终结果矩阵/CI/失败率、资源/API成本对账、README模型revision/merge recipe和复现索引仍需整理。

## 2026-10-18 12:47 CST：加入标注后的 AVG64 exploratory macro

- 按用户确认，将固定 seed=2 的 Terminal single-run 写入独立补充视图：AVG64 四项 exploratory macro **6.335847%**，Base 对齐 seed2 exploratory macro **11.059989%**，差值 **−4.724141pp**。
- 该视图明确标注 Terminal single-run、非题面五次均值/标准差及本实验资源协议，不覆盖 strict aggregation；详情见 `analysis/exploratory_macro_20261018.md`。

## 2026-10-18 13:56 CST：用户确认暂记 Base Terminal timeout 为0

- 用户允许先将 Base Terminal 三条 verifier timeout 在报告审计/预算视图中记为派生0。现有 accounted 视图为 445/445、90 correct、20.224719%；新增明确快照 `analysis/source_snapshots/base_terminal_timeout_zero_overlay_20261018.json`。
- 该处理不改原生 `reward`/`verifier_result=null`，不把派生0写入 strict native 结果；正文标注为“用户确认的 timeout-derived provisional zero”。

## 2026-10-18 14:05 CST：完成全部已跑结果矩阵

- 已将 Base、四专家、Mixed、AVG16、AVG64、TIES-Dense 的 SWE/HLE/ASI/Terminal 结果统一整理到 `analysis/complete_results_table_20261018.md`，同时展示 strict、audit/provisional、历史445 coverage、seed2 exploratory 和 TIES offline overlay，不隐藏非正式结果。

## 2026-10-18 14:10 CST：简化对外结果表

- 按用户要求，主表改为单一最终汇报口径；不在表格单元格中展开 strict/overlay/coverage 分类，协议偏离和原始证据移到表后说明与附录。

## 2026-10-17 17:45 CST：Terminal当前覆盖汇报

- 最新严格快照14:46：Terminal专家 `285/445` 有效、7 invalid、153 pending；AVG64 Terminal `263/445` 有效、6异常、176 pending。Base为442/445 native有效、3 invalid；独立预算视图的445 accounted不等于445 native完整。
- 727912/727913是仍在运行的模型服务，不代表新启动了Terminal五次队列。用户改为单次89题后，新的single-run exploratory队列尚未启动。

## 2026-10-17 17:50 CST：Terminal禁网限制继续冻结

- 用户确认本轮继续保持 Terminal solver 沙箱禁网，不修改既有 Base/专家/AVG64 结果、不为联网问题重跑旧答案。
- 最终报告必须明确：官方任务文件没有要求该禁网设置，这是本实验额外的环境限制；它可能阻断 PyPI/Ubuntu 域名解析和依赖下载，相关失败不能直接解释为模型能力下降，也不能在 strict 统计中手工填0。

## 2026-10-17 17:55 CST：Terminal完成时间估算

- 按最后一次可审计短窗吞吐（专家19.52终态/小时、AVG6418.02终态/小时）估算，Terminal专家剩余153条约7.8小时，AVG64剩余176条约9.8小时；还需预留排空、审计和invalid处理时间。
- 以北京时间17:55粗略换算，专家约01:40、AVG64约03:35结束任务尝试；这是线性估算，不是保证。要发布strict完整分，还必须处理7/6条invalid，不能把它们自动填0或重跑。
- 该估算针对已启动的旧445-trial队列；用户改定的单次89题新队列不启动、不与旧队列混报。

## 2026-10-18 12:25 CST：seed2 Terminal 缺口完成并同步证据

- host80 已完成三条独立 archived-answer grade-only：Terminal专家 `pytorch-model-cli/seed2`、Terminal专家 `train-fasttext/seed2`、AVG64 Terminal `train-fasttext/seed2`。三条均 `valid_native`、native reward `0.0`、verifier 已启动且无异常；旧445目录和summary未覆盖。
- 两条 `train-fasttext` 使用一次性、仅作用于 verifier sandbox 的官方离线 CPython3.11 供应修复（candidate/tests/budget/network/model calls 均不变）；官方测试仍按原候选结果给出 reward 0。无 grade-only 进程、Apex scope 或锁残留。
- 远端原始结果：`/data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal-seed2-completion-20261018/terminal250-pytorch-model-cli-seed2/native-grade/result.json`（SHA256 `acdb0c6ed088f3aec72f34f9b684317c0f75678799024ec4031f89282226c131`）；`terminal250-train-fasttext-seed2/native-grade-fix2/result.json`（`686b29e871090f7530366c159088bcd4738d474cac4284e6e5b47e38676778c3`）；`avg64-train-fasttext-seed2/native-grade-fix2/result.json`（`ceeb882052977839b9ab513506a0dd11e224598bb90afb39b03262c2b3bceb2e`）。
- seed2 独立汇总：Terminal专家 `89/89`，8 correct，`8.98876404494382%`；AVG64 Terminal `89/89`，11 correct，`12.359550561797754%`。JSON/Markdown 已同步到本地 `analysis/source_snapshots/terminal_seed2_completion_20261018.json` 和 `analysis/terminal_seed2_completion_20261018.md`，本地 SHA 分别为 `e8e2686a32788a952ce59e4663c9d951d46fe59f47d6ebb2ae7defa88332bf7e`、`b9bd76e783fe165f252d8526bd6ba92c056e39a9bbfee4e6434a418f5bafe3d2`。
## 2026-10-18 12:42 CST：TIES-Dense HLE 唯一 invalid 离线 overlay

- 只读复核确认任务 `672d8b9b504a98f0e4799ae0` 的原始回答、criteria、两次 HTTP200 Judge request/response 均完整；两份 frozen Judge body 都显式写出 `correct: no`，只是缺少严格 parser 要求的 `correct` 字段，原结果因此是 `evaluation_invalid`。
- 按授权仅做独立离线解析，不重发 API、不修改 parser、不重生答案，不覆盖原 `result.json`/`summary.json`。远端 overlay：`/data/caoqinlu/projects/apex-takehome/artifacts/eval/ties_dense_hle2500_20261017/scoring/offline-score-only-overlay-20261018/`；本地镜像：`artifacts/eval/ties_dense_hle2500_20261017/scoring/offline-score-only-overlay-20261018/`。manifest/result/summary SHA 分别为 `00a85463487dbbfa8ccbefc04d2ddfe8640fd8928d0a0ad5003e88b8ae573229`、`7dc375e8391509e20300121730a84c1b513ab97b8a9a2b99997c79dd9c43c556`、`6526b7ca9f7fb1a81acc374c6393677321c00537b334b9e31117e8d6e5ae52fc`。
- 独立 complete 视图将 TIES-Dense 记为 `131/2500=5.24%`、overlay reward=0、new API/model calls=0，并明确这不是官方重新判分；原始 invalid 仍保留。审计 manifest 另存为 `analysis/source_snapshots/ties_dense_hle_offline_score_only_20261018.json`。

## 2026-10-18 14:35 CST：最终提交仓库收口

已生成并目视验收根目录 `report.pdf`（A4、1页、中文字体嵌入），并更新根 `README.md` 为最终交付说明。五个 Hugging Face 模型按 `models/release_manifest.json` 的 immutable revision 重新匿名核验，均为公开、非 gated，未重复上传或改变模型身份。最终仓库将包含代码、配置、模型卡/发布清单、结果快照、HLE 消融、失败案例、成本与复现索引；大权重、原始数据、任务缓存、SIF、完整日志和凭据继续留在 Git 忽略资产中。Terminal 五次官方口径和官方资源配置未完全复现，README、结果矩阵和 report.pdf 均明确该限制。
