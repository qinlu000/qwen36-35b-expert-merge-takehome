# SWE v2 baseline status — 2026-10-16

15:38只读快照：固定51项中，当前43项接续队列已有23项generation+fresh replay终态、3项在途、17项未准入；另2项旧正常预算patch的fresh replay完成、6项旧工程熔断提前取消保留incomplete。旧musl的9个0生成setup结果不重复计入覆盖。全51镜像现已缓存，无缺镜像阻塞。

共25个唯一fresh replay已落盘，官方binary reward为1项1、24项0，replay级Harbor异常0。但7项存在verifier环境异常标记，暂不视为可靠模型失败：pytest缺失4、pip缺失1、Go module公网下载timeout2。其中Ansible b748同时有模型缺实现的collection error，环境并非已证实唯一原因。其余18项当前未发现上述异常，包含4项模型Go语法/API/build失败；有效resolved为1，保守已解决比例1/51=1.96%，完整主分未形成。部分tests PASSED只是诊断，官方不按测试比例给部分分。

旧28083生产父PID452167、glibc PID452169仍在自然drain，glibc checkpoint为stopping_admission、3active/17pending/13terminal，无新infra暂停；musl root-map修复PID461500已结束，10/10 generation与replay完成。正常1740s/exit124未再被误判infra，已有patch照常fresh replay，答卷没有重生。

新725705模型实际14:36已ready；root一次性waiter早期因health ConnectionReset退出，root修复后于15:25:55启动consumer2004064自然交接。`base_swe_v2_20261016_full_x2`目录已建，15:38尚无新leaf checkpoint，在等上述3项自然结束。新28084为maxseq8、16solvers、CPU64–71及76–83；旧28083仍maxseq4。

主log为`artifacts/eval/base_swe_v2_20261016_full/full-controller.log`，有效child状态看`glibc/admission_checkpoint.json`和`musl_root_repair/admission_checkpoint.json`及`additional_children.json`。旧父checkpoint仅含初始children，不能单独代表总数。原始响应位于child的`requests/<taskID>/raw/`，逐chunk落盘后转给mini。

handoff spec固定`artifacts/runs/baseline-x2-725705/swe-launch.json`，只让当前在途自然结束，迁移未准入pending；明确0生成的旧musl setup journal不阻挡repair pending，当前repair自己的started journal仍禁止重答。策略留档`<full>/handoff-selection-policy.json`。25项逐条评分审计在Mac `analysis/source_snapshots/swe_progress_20261016_1536.json`（实际as_of15:38）和远端`<full>/progress-audit-20261016-1536.json`。未新增测试、hash gate、prompt修改或模型重答。

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

