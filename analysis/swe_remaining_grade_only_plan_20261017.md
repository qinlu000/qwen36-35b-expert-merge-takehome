# SWE剩余6项：原答案grade-only准备方案

**仅方案，未准入或执行。** 2026-10-17 07:28:38 CST只读核对80元数据、原配置和现有源码；SWE专家、AVG64审计层各48/51有效，以下各3项仍null。本轮没有native/container/model/API调用、claim、网络或队列变更。唯一新增文件为本说明；原答案、测试、结果和共享marker不改。

可复用已有fresh-patch评分链和磁盘scratch/日志留存经验，但**不能直接执行原controller或Base修复CLI**。最小实现应从每项**原replay/config.json逐字段复制**，只换独立输出、CPU映射及经root批准的环境实现，仍用原`PatchReplayAgent`。六项并不都已证实只需环境修复；具体问题和准入前提如下。

## 精确输入与当前证据

所有下列相对路径均以80项目根`R=/data/caoqinlu/projects/apex-takehome`展开。两套原件根：

- `E=R/artifacts/eval/swe249_hard51_20261016`，generation模型必须`openai/apex-val-swe249`。
- `A=R/artifacts/eval/avg64_swe_hard51_20261017`，generation模型必须`openai/apex-avg64`。

当前清单来自`R/artifacts/eval/{swe249_audited_hard51_20261017,avg64_swe_audited_hard51_20261017}/summary.json`；已获批的6/3项审计分别见仓库`configs/eval/{swe249_audited_hard51_20261017,avg64_swe_audited_hard51_20261017}.json`。这两个manifest中的白名单不包含本轮六项。

| 代号 | 完整task ID |
|---|---|
| N | `instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` |
| V | `instance_future-architect__vuls-5af1a227339e46c7abf3f2815e4c636a0c01098e` |
| T2 | `instance_gravitational__teleport-2b15263e49da5625922581569834eec4838a9257-vee9b09fb20c43af7e520f57e9239bbcf46b7113d` |
| T774 | `instance_gravitational__teleport-7744f72c6eb631791434b648ba41083b5f6d2278-vce94f93ad1030e3136852817f2423c1b3ac37bc4` |

对表中每个`根/ID`，精确原件为：`根/generation/ID/agent/model.patch`、`根/generation/ID/{result,config}.json`、`根/replay/ID/{result,config}.json`、`根/replay/ID/agent/replay.json`及`根/tasks/ID/`。原测试五文件为`tasks/ID/tests/{config.json,parser.py,test.sh,run_script.sh,test_patch.patch}`，本轮均确认实存。不得跨E/A引用generation、patch、结果或原生0。

| 原件 | 当前原因与证据 | 只读判断 / 最小方向 |
|---|---|---|
| E/N | `VerifierTimeoutError`，3000秒；7422B patch，apply_rc0；`verifier/test-stdout.txt`只有Terminated，缺durable run-script日志/output；reward.txt1来自EXIT trap | 未决。原patch删除`.mocharc.yml`里的exit:true，但删除来源及挂起因果未闭合。可考虑同patch重放并增量保留原临时stdout/stderr；**不恢复.mocharc、不加--exit、不改测试/产品代码**。 |
| E/V | `RemoteProtocolError`；原prep0/71.76秒；CPU6对应scope在03:28:13 OOM，随后断连；OOM victim未知 | 只证明资源终止，不能据此填0或加内存。可考虑同1CPU/4GiB、磁盘/tmp和原Go cache内容副本，并留memory.events/peak/server日志；尚未证明这一定消除根因。 |
| E/T2 | `VerifierTimeoutError`，prep0/84.24秒，cache190 copied/37 kept；后续3000秒超时，缺durable测试结果 | 未决，不能套T774的proxy故障。可考虑原musl环境+磁盘scratch/cache+增量日志；保留原工具链/依赖。 |
| A/V | `RemoteProtocolError: Server disconnected without sending a response`；0B patch；prep0/71.82秒；stdout止于官方test patch成功apply | 本轮未获得该AVG断连的OOM归因。磁盘scratch/资源事件是有依据的诊断性环境加固，不是已证实修复或有效0。 |
| A/T2 | `RewardFileNotFoundError`；0B patch；prep0/73.74秒；stdout止于官方test patch成功apply | 无reward根因未明。优先同musl运行时及原预算、磁盘scratch和durable日志；不能继承Base的data race或专家超时结论。 |
| A/T774 | 原native0但invalid=`verifier_public_go_dependency_timeout`；0B patch；prep0/34.29秒；`run-script-stderr.txt:4`原`proxy.golang.org/.../netlink/@v/list`超时 | 明确存在原public proxy网络障碍。仅考虑恢复同原host/URI/TLS/校验语义后独立同patch评分；不能复制专家T774的新result或直接套其native0白名单。 |

本轮读取的原result SHA256（只读小文件，不扫描SIF大文件）：

| 原件 | `replay/ID/result.json` SHA256 |
|---|---|
| E/N | `822402c314da8d9e068846a21352f318d55a76da215956100ae26530d68924e9` |
| E/V | `86f0aaa9099eec75842eecd7684f5c53a635ce1b4f41a1f51fb17a7335a2dfc1` |
| E/T2 | `bdcd84c5d83fc4b2f8aab42578349ad72c0a88b2e7c682da3a70b0a85d2240a2` |
| A/V | `50a08c0202e77a93a96beb1f9f8c0e78147cb1a2088b1f22a6391d947e6e4067` |
| A/T2 | `fa0edc7b1a48b197cda3e4e74c23b6dd4648b31fde15b455c66cf81f07a05b73` |
| A/T774 | `1d68a5172d9c0835f69b654f6ec2ae5dcf30fde9db14d6b3692815e40f9c7b27` |

E/N patch SHA=`aff1970c0bf1d670854f4a268ae4172d83574a9fff6f6db12d82e4fc0817ff77`；其余五份原patch均0B、SHA=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。空patch仍须绑定各自generation/result/model，不能因字节相同就借用另一模型的判分。

原task.toml指向的SIF均实存于`R/artifacts/benchmarks/sif/`，保持该文件及原task checksum：

| task | 原SIF文件名 |
|---|---|
| N | `sha256-267632c93bae96eb120292b36e68227a41f2b6edd8e8ff5d7a3bdd7ef4af3b6b.sif` |
| V | `sha256-ce030de85a57473a9b52d493fd023ab90871959e7129b4281edb1b2e5038d078.sif` |
| T2 | `sha256-79cc62083ee6186c30fe3cd455b993344b92da3bbda87c792abee5bf130f57c4.sif` |
| T774 | `sha256-83645a1c5565267675a19af0916ba1eed14131c315d92cedb05abea398a03527.sif` |

这是原metadata中的身份与文件存在性，不冒称本轮重新hash了SIF。

## 可复用入口及不能直接运行的地方

1. **原PatchReplayAgent**在`R/artifacts/benchmarks/swe-bench-pro/v2/tooling/patch_replay.py`，SHA=`5c8b344de37164e9723f1724c2573013957fb644c3913a64c12c1718c737d876`。`scripts/swe_baseline_v2.py`先把该tooling目录插入sys.path，因此单独只设`PYTHONPATH=scripts`时`find_spec('patch_replay')`为空不等于原文件丢失。未来独立worker应显式保留tooling路径。此agent仅找各自source_job中的捕获patch、在fresh image apply；不会请求模型。N必须确认非空patch恰好命中原来源且apply_rc0，五个空patch明确保留“apply nothing”。
2. `scripts/replay_swe_score_environment.py --audit … --output … --category all --task-id … --environment … --concurrency 1 --cpu-offset …`确为score-only；但它从`run_swe_baseline_v2_next.trial_config()`重建配置、只拿输出本地controller锁，**没有92–95 global锁/完整原config绑定**。不得原样提交。`run_swe_expert_benchmark.py`和`run_swe_merged_benchmark.py --single-task`包含generation，禁用。
3. `scripts/repair_base_swe_gaps_20261017.py`的`DiskScratchAndLogs`与三个修复环境已有实测先例：`/tmp`写/data、Go原cache原样复制到磁盘副本、每10秒外部留存官方run_script临时stdout/stderr、stop前留server/cgroup events。原CLI硬编码Base SOURCE/OUTPUT、CPU11 guard、Base scratch目录，不能直接对本六项运行或修改。未来只在**新独立文件**移用这段最小环境实现，使用自己的scratch/output，原Base文件和输出不改。
4. 原环境类仍为`swe_clean_glibc_runtime:SweCleanGlibcRuntimeEnvironment`（N）、`SweCleanGlibcGoRuntimeEnvironment`（V）、`swe_clean_musl_runtime:SweCleanMuslScoreEnvironment`（T2/T774）。musl启动必须保留`R/artifacts/preflight/swe_v2/musl_compat/shim`在Apptainer之前；原Base T2首个attempt漏shim已失败，不能复现这个缺口。
5. `scripts/swe_score_original_proxy_repair.py`的私有CONNECT relay和musl subclass是T774恢复原proxy可达性的既有实现参考；但它硬编码**专家T774** SOURCE/OUTPUT、CPU10、socket与日志，不能直接给AVG用。既有route已结束，不将“脚本存在”说成当前网络已通。若root批准A/T774，应独立namespace/socket/output，限制同`proxy.golang.org:443`、保留原URI和TLS校验，先做同环境的原URL可达性验收；不改官方测试、go.mod/go.sum、Go版本或依赖版本。专家修复后解析到新netlink并报Go工具链不兼容，只是专家的后续证据，不替AVG评分。

`artifacts/eval/{swe249_hard51_20261016,avg64_swe_hard51_20261017,base_swe_gap_repair_20261017}/runtime`均未发现。不能声称它们拥有Terminal式独立冻结runtime/source_inventory。当前Harbor venv实际源码为`R/artifacts/benchmarks/harbor/src/harbor/`；生产依赖还包括`R/scripts/`、上述tooling、`artifacts/cache/{swe-v2-runtime,swe-v2-wheels,swe-score-go}`与musl bundle。本轮确认这些关键入口/资产实存。执行前须在独立恢复输出中固定所用小型源码/原config/tests的身份和导入路径，经root验收；不借用Terminal470层来假装SWE原运行时。

## 预算与92–95租约：保留SWE协议

六项原replay均为**1CPU、4096MiB、0GPU、verifier3000秒**；PatchReplay override1800秒，environment的其余原timeout字段照抄。Go wrapper单个workspace-prep exec上限1800秒；但当前Harbor `Trial._verify_with_timeout`以`wait_for(verifier.verify(),timeout=3000)`包住验证，`environment.exec('/tests/test.sh')`触发的workspace prep也在其中，**不能给测试另加1800秒**。这不是nginx/TB的4CPU8GiB900秒协议。

可以作为`R/artifacts/eval/direct_asi_grader_cpu92_95.lock`的EX消费者串行使用共享grader池：整池92–95持租约，单项native只用**物理92单核+4GiB**，其余核不另起任务。外层`taskset -c 92`时wrapper的**逻辑offset须0**，不能再传物理92作为当前mask内索引。parent有效cgroup必须包含92，不能给parent设AllowedCPUs10后再期望child扩大cpuset。使用真实`artifacts/envs/harbor/bin/python`词法venv路径、原Apptainer/fakeroot PATH、`XDG_RUNTIME_DIR=/run/user/1012`、同user DBus及独立/data TMPDIR。

**global flock不等于Terminal租约。** ASI和grade-only消费者拿同锁；正式Terminal扩容依靠marker/scopes，不拿这个flock。07:28:38只读快照中该锁inode90775088没有FLOCK记录、两Terminal都没有`cpu-expansion-asi_finished.json`、AVG ASI all-CPU marker仍缺；这仅是瞬间观察，不是永久释放或准入授权。未来必须：

- root确认92–95仍属于共享grader池，尚未由正式Terminal扩容接管；若已接管，不能因某个间隙scope为空抢回CPU。
- 单项持同EX锁，再核实际92–95 busy scopes；如为避免未来Terminal扩容竞态而需要可见sleep guard，只能在root明确批准的grader租约内创建独立`apex-baseline-*` guard，创建后复核没有外来scope/已完成扩容证据才spawn。guard只保留调度租约，不给native增加CPU/RAM；没有获批可见租约时不运行。不能靠写ASI/all-CPU marker阻止或诱导交接。
- lease FD传给child；原预算运行完再做两次scope排空（排除自有guard但不忽略其他owner），停止guard并确认消失，最后解锁。每项后让出锁给ASI，不把六项包成数小时不可让出的batch；不触动96–127生成池、现0–91 Terminal槽、ASI完成marker或任何正式队列。

## root批准后才实现/执行的最小顺序

建议新文件仅`configs/eval`下的**独立六项恢复manifest**与一个parent/单项worker脚本（准确建议名`configs/eval/swe_remaining_grade_only_20261017.json`、`scripts/run_swe_remaining_grade_only_20261017.py`；本轮均未创建）。各输出分开建议`R/artifacts/recovery/swe-remaining-grade-only-20261017/{swe249,avg64}/ID/attempt1/`，绝不写回原replay。

1. 默认prepare-only：绑定各模型原generation/config/result、patch、task checksum、tests/镜像路径、实际导入源码及恢复方式。验证每项原native/source身份和预算，声明本次只允许的scratch/log/route变化；元数据检查不创建native环境或claim。无明确环境修复依据的项先停留在方案状态。
2. 优先审Vuls的磁盘scratch+资源日志方案；T2采用既有musl磁盘方案但不预言一定修好；N只允许日志留存，不修产品退出配置；A/T774另需原host路由恢复审核。每个模型自己的结果独立产出，不继承Base/其他专家的失败审计。
3. root逐项批准后才唯一claim；等待同锁/真实租约与core runway，独立新输出、0模型请求、不自动retry。新准入要为原build/PatchReplay/verifier上限和cleanup留足截至10/18 02:20的窗口，不能套用TB的1800秒runway；不得中断已准入的原3000秒预算。
4. 完整保存原生stdout/stderr/parser/reward、增量live日志、cgroup memory.events/peak与源bytes比对。真实0/1也先由root独立验收再加exact overlay；OOM、无reward、超时或混合错误若仍未闭环则继续null。N即使重现“测试报告完成但进程挂退出”，也不自动加--exit、填reward或提前停止；需留本模型自己的完整官方报告，root另审。

现有Base修复证明该类grade-only链可运行，不证明六个新结果必然有效。参考[专家剩余审计](swe_remaining_scoring_audit_20261017.md)、[Base修复实录](base_swe_gap_repair_20261017.md)、[原proxy修复实录](swe_formal_scoring_audit_20261017.md)；它们提供环境经验和风险，不提供可跨模型挪用的分数。本轮到此结束，等待root审核方案。
