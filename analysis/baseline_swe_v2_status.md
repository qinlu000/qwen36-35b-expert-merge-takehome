# SWE v2 baseline status — 2026-10-16

16:49续记：23个新17+manual6模型relay.end全部齐、无生成pending/infra并稳定10秒，GPU消费者marker已实际写true（评分仍在途，不释放CPU）。当前47/51有效、resolved5，3项原patch官方回放在途，1项Element66d0是真实bootstrap工程错误：随机urlsafe server token以`-`开头，argparse拒绝`--instance-token <value>`。旧invalid与server.log保留；独立`swe_score_bootstrap_runtime.py`/`.sh`仅将服务端参数传成`--instance-token=value`，原patch/tests不改，CPU124单槽fresh replay PID2563381（score_bootstrap_args1），0模型调用。永久CPU marker仍等旧64–119全部future consumer终态。

16:40续记：46/51有效评分，resolved5，invalid_pending0；新17全部含官方fresh replay终态，manual6首1项也有效0，余5在途。Tutanota是原生tsc的TS2322/2345/2416类型/接口不兼容，保留原官方0并保存classification audit；没有重答或重评分。只读collector的类型错误规则限定这3个已审计错误码，缺包错误不能由该规则直接判有效0。消费者watcher当前PID2519609，两个永久marker均等待真实条件，未来必要复评分pool已改[124]/max1。

16:35续记：44/51 valid、resolved5、invalid_pending0；原17最后1项已结束模型调用转fresh replay，manual6仍全部在途，pending0。只读消费者watcher已实际部署PID2511317，live状态`artifacts/runs/swe-base-725705/swe-consumer-watch.json`；模型完成marker与CPU完成marker分离。`model-consumer-finished.json`确认17+6 relay结束且无生成pending/infra后可提前写，评分可仍在途；`cpu-consumers-finished.json`仅全部23项含评分终态、父/leaf退出、旧64–119容器进程为空后写`cpu_consumers_finished:true`。该CPU永久完成后不会再从旧pool准入；所有必要后续原patch复评分固定CPU124，1滚动槽/1CPU4GiB（root随后CPU协调更新）；120–123留给Terminal原archive补评、125 HLE Judge、126汇总、127cache。725705模型由root在SWE消费者结束后交给Terminal复用，我不scancel，也未重启任何在途生产进程。

16:21当前：所有已收44项均有first-valid评分，resolved5，invalid_pending=0；保守比例5/51=9.80%，完整主分仍null。新17首批16已完成，最后1项异步补槽在途；6项manual infra1也已全部在途（PID2449625，CPU76–81，attempt2），所有尚需生成的7项均已准入，无未开始排队。模型输入/采样/预算/答案未改；旧partial、费用和全部invalid评分保留。

Follow-on PID2449593：group1自然结束、controller2087116退场、旧容器PID=[]后复用76–81，与group0最后1重叠；此前waiting wrapper读取旧zombie mountinfo EINVAL的实际错误已修复，未取消任何模型任务。消费者marker仍等待所有17+6结束后才允许释放725705。最终collector PID2465711持续输出固定51的JSON/CSV，manual planned6/actual started6分开记录。

评分修复已闭环：5项Python原patch复评恢复native3.9/3.11/3.12与pytest/pip，1项恢复有效1；3项Go原patch最终均有效0（模型编译错误）。Flipt的真实go.work需在public verifier阶段用镜像预取，42.16s成功后执行完全原test.sh；另发现配置3000s被HTTP缺省600s剪断，私有评分exec显式传3000保持原上限。Navidrome-874b是候选未声明deluan/rest依赖的native Go错误，无网络/Harbor异常，原官方0经审计采纳，不私改go.mod。新grading源`swe_score_go_prefetch.py`与`swe_score_final_runtime.py`；在途17源冻结，manual6启动前已选择修正评分环境。


15:58续记：已部署完整51接续闭环。x2当前16active/1pending，原17不改源、不取消；远端follow-on PID2355044持排他锁，等待自然drain后仅对6个审计确认的CancelledError/空submission incomplete做manual infra retry1，总generation_attempt2、同ID/seed0/1800s，原response/轨迹/费用记录完整保留。没有已验证的剩余预算原生resume入口，未构造resume。汇总器PID2358733持续写`base_swe_v2_20261016_final/final_summary.json`与`task_scores.csv`，未评分为null，只采首个环境有效评分。最终模型consumer marker为`artifacts/runs/swe-base-725705/model-consumer-finished.json`，由follow-on在所有17+6生成消费者结束后写，root已改为仅按该marker释放GPU。

当前有效27/51、resolved2（保守3.92%，主分仍null）；Vuls-ca3和Teleport-7744的原patch Go复评已排除网络错误，均因模型Go代码build错误而有效0。仅Flipt-c188原patch仍在实际native go test评分。Go直接cache之外已用原镜像Go下载ecr/netlink完整传递模块图、默认sumdb验证，0tests/0模型；官方test.sh强制GOPROXY的行为保持原样，cache仅合并到native目录。新回执`analysis/source_snapshots/swe_final_progress_20261016.json`。


15:46只读快照：固定51项中，旧批次28项已有generation与fresh replay结果，6项旧工程熔断提前取消保留incomplete。其余17项已自然交接至新28084/maxseq8：`base_swe_v2_20261016_full_x2`为16active/1pending，两个8-slot组使用CPU64–71和76–83，已实际保存150份raw response。51镜像全部缓存。

新17项在准入前改用独立`run_swe_baseline_v2_native.py`、`SweBaselineNativeV2`、`SweNativeRuntimeEnvironment`。恢复SIF原生PATH，不再将managed python3.12/uv bind覆盖task的`/usr/local/bin`；mini只用私有工具路径与原managed3.12、完整constraints，官方prompt/tools/mini2.4.6/采样/预算不变。没有重生此前已生成答案。旧leaf保持原样。

旧28项原评分中8项出现verifier环境异常标记：pytest4、pip1、Go公网依赖timeout3。Python5项已只用原patch在新`base_swe_v2_20261016_score_envrepair1`完成fresh replay，原生3.9.23/3.11.13/3.12.11的pytest/pip均恢复；官方reward为1项1、4项0，replay级Harbor异常0。旧缺pip的e9e600从无效0恢复到有效1；mixed b748环境问题消失后仍因模型缺少prepare_multipart实现而collection error，保留有效0。旧invalid结果全部保留。

截至15:46，按首个无环境异常标记的结果采纳，当前有效评分25/51、resolved2，保守已解决比例2/51=3.92%，完整主分未形成。部分tests PASSED只是诊断，官方不按测试比例给部分分。3项Go依赖网络失败尚待原patch复评；Flipt-c188/Teleport-7744已用只读官方模块cache开始`score_go_glibc1`/`score_go_musl1`（CPU88/89）；新增Vuls-ca3正在补精确依赖cache。不改原run-script/tests，不关闭sumdb，不生成新答案。

主日志：`<full>/full-controller.log`及`<full_x2>/<group0|group1>/controller.log`；各父/子`checkpoint.json`、`admission_checkpoint.json`保存active/pending/terminal。`<full>/additional_children.json`登记旧musl替换子进程，不能单看旧父checkpoint。原始响应在child的`requests/<taskID>/raw/`，逐chunk落盘后转给mini。所有score repair的checkpoint明确model_calls=0。

评分回执：`analysis/source_snapshots/swe_score_environment_repair_20261016.json`，远端`score_envrepair1/score-repair-summary.json`；逐条保留prior invalid路径、新评分路径与first-valid采纳规则。初次15:38审计回执仍为`swe_progress_20261016_1536.json`。没有新增验收/hash gate、prompt修改、模型替换或重答。

## 前序验收与启动记录（历史，以上为当前）

`native-lxwl19kv/summary.json`真实native mini→bash→153B patch→全新官方PatchReplay通过，initial/replay reward均1，111.544秒；5次工具tokenize计数1053/1157/1279/1369/1744与native模型usage逐项一致。Mac回执`analysis/source_snapshots/swe_native_real_20261016.json`。缺curl分支自造stub也已通过（`native-a28iobw0`，36.679秒，含1CPU4GiB/无网络资源校准）。按用户最新速度优先指示，不再做全SIF重哈希、重复资源fixture或排队/取消额外启动gate；已有正确性验收沿用。

首次正式目录`base_swe_v2_20261016_glibc`的PID3915164已退出：staged任务外链symlink被Harbor任务输入边界校验拒绝，41个journal/driver-error保留，0模型调用/0答卷。新`run_swe_baseline_v2_materialized.py`只把task输入改真实copy，并在driver-error时暂停新准入；新目录的`setup_repair_manifest.json`明确记录零生成setup修复。旧生产源未改。

正在跑的cohort发现7项Ansible在模型前被指纹误挡：importlib.metadata误把/app任务仓库的ansible*.egg-info计入mini依赖。另备`SweBaselineSitePackagesV2`只枚举实际site-packages，保持mini/constraints/prompt不变，不修改运行中的源。一次性远端等待器PID349643：等当前controller正常完成后，只选择该明确异常且requests=0/无mini轨迹的项，到独立`base_swe_v2_20261016_glibc_setup2`做首次生成；当前controller若因infra暂停则仅needs_audit。已有任何回答均不重生，两controller不重叠准入。

2个缺失Proton镜像已复用原ranged-oci队列以2workers重试，PID353782，独立`_prefetch_swe_missing2_20261016.json`，旧140镜像记录保留。8个musl镜像未进入正式模型；TB agent正在独立私有层研究，外置Python方案曾139，不能冒称兼容。没有新GPU申请或半小时automation。

## 已通过

- `artifacts/preflight/swe_v2/native-7l6aq01_/summary.json`：官方mini2.4.6/LockedMiniSwe，3次guard/3次stub HTTP；容器内按完整constraints离线安装并逐包核版本；153B patch，initial reward1；全新容器官方PatchReplay apply_rc0、replay reward1。70.864秒，正式题/判题调用0。Mac回执`analysis/source_snapshots/swe_native_stub_cpu_20261016.json`。
- 实际CPU[64]、扩宽EPERM、memory.max4294967296/swap.max0；公网IP/DNS被拒、AF_PACKET被拒、实际RTM_NEWROUTE修改返回-EPERM；结束无owned scope。创建NETLINK查询socket本身允许，不能用其创建结果判断修改权限。
- guard回归6/6：`guard-ppcbjfek/summary.json`；native mini重试回归2/2：`native-retry-y18kd8k4/summary.json`。发送后断连仅1次HTTP；length按官方格式反馈进入下一步，原响应保留。真实工具模板tokenize已通过，见最新真实验收。

## bootstrap修复与镜像普查

旧`native-bb8_kly4`在原bootstrap的无条件apt-get update阶段300s超时，未进入模型。仅清理PID3839142自己的进程树和scope，确认alive=[]/scope inactive；staging/日志保留`bootstrap-diagnosis-20261016`。独立namespace DNS/HTTPS可通，IPv4 apt仍35s超时于8.79MB索引；短HTTP下载仅约40–110KiB/s。

新`SweRuntimeEnvironment`继承冻结backend，只读bind自己的cached bootstrap、server venv及85个wheel（约164MB）。保留原task setup及公网准备→无网solver→公网verifier；mini仍执行官方uv tool install，添加原完整constraints并离线安装，安装后逐包验指纹。bash型mini不用tmux/asciinema，私有bootstrap不安装这两个终端依赖。缓存manifest记录wheel/UV/Python/server版本/native库SHA；缺curl镜像只在缺失时链接私有loader/library bundle，不覆盖现有curl/libc，该分支自造及真实模型闭环已通过。四个冻结backend和五个ASI源均未改。

只读51项task.toml→镜像OS/工具普查`image-tools-20261016/summary.json`，无正式instruction/tests/patch：49镜像缓存，41可glibc启动；其中10个Ansible/qutebrowser缺curl；8个Vuls/Teleport/Proton因glibc fakeroot与musl不兼容启动失败；2个Proton镜像缺失。固定分母仍51，缺失/未兼容项不得当作模型失败或删掉。

## driver与待补范围

driver固定HARD51、最多8项有界准入、准入前及在途health watch，失联取消并保存checkpoint；逐phase started journal保留中断现场，不自动重生答案；独立bridge/socket/deadline、1800s总solver预算/官方1740s内层timeout/30s kill grace；key仅宿主。官方新环境PatchReplay为主分。排他flock防重复controller，metadata保留runner/runtime/backend/protocol/cache manifest及旧SIF下载receipt；用户授权不再全量重哈希。

当前41项运行后，补明确零生成setup误挡项，以及8个musl/2个缺镜像项；后者仅在私有层兼容完成后进入新的首次生成cohort。保留51分母，已收完整答卷不重生。

