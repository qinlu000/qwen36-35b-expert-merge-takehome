# Base SWE 五项缺口收尾

权威来源为80服务器的`artifacts/eval/base_swe_v2_20261016_clean28`。原队列已在10月17日01:23结束，28项中23项有效评分、7项通过；与保留的23项合并为46/51有效、10项通过。原generation、patch、result、replay与历史汇总均保留。

**03:28收尾结果：五项缺口已全部有有效判定，整套Base SWE为51/51有效、10/51通过（19.607843%）。** 其中Vuls和Teleport为新鲜原patch重放得到原生0；Protonmail/Flipt沿用已有原生0并补逐项候选错误审计；NodeBB依据本轮完整官方测试报告审定0，原始native_reward仍为null并保留受控cleanup异常。没有重新生成任何模型答案。

## 两项候选错误：沿用原生0，不重新生成或评分

固定逐结果审计在`analysis/source_snapshots/base_swe_gap_audits_20261017.json`，服务器副本为`artifacts/eval/base_swe_gap_repair_20261017/candidate-failure-audits.json`。每项绑定原result路径、原patch路径与该小文件的身份，记录原生reward=0；本审计不修改共享collector或原结果。

- Protonmail `5f0745`：模型新增`BitcoinInfoMessage.tsx`，从`../../../hooks`导入`useConfig`。原生评分运行该组件时在11:35报`useConfig is not a function`。空tests是候选运行错误造成的报告缺失，应保留原生失败0。
- Flipt `c188284`：模型patch自行加入ECR v1.30.0，并加入两条错误go.sum。原native Go准备已在0.57秒内因checksum mismatch失败。[Go官方checksum database](https://sum.golang.org/lookup/github.com/aws/aws-sdk-go-v2/service/ecr@v1.30.0)的HTTPS响应已保存，精确确认原下载的go.mod checksum正确，候选的模块zip和go.mod两条值都不符。其后网络超时不能使候选变为可构建；不修改go.sum、依赖版本或校验规则。

## 三项只重放原patch

用户授权补齐Base结果，root授予CPU11单槽，CPU10继续由另会话专家修复使用。运行脚本为`scripts/repair_base_swe_gaps_20261017.py`，输出独立保存到`artifacts/eval/base_swe_gap_repair_20261017`。

三项使用同一已授权CPU11滚动收尾：Vuls `5af1`在03:10结束后立即交给NodeBB，完整失败报告审定后提前结束仅挂退出的scope，再直接交给Teleport，避免空等其他队列。未实际占用92–95共享租约；先前零准入等待parent均确认无子进程后停掉。每项仍为1 CPU、4096 MiB、原生verifier 3000秒。使用原`PatchReplayAgent`及同一原patch，0模型调用；不改官方task、tests、parser或候选代码。

每个新容器的`/tmp`绑定到独立`/data/caoqinlu/apex-base-swe-repair-tmp/native-*`，避免session tmpfs存储不足。评分过程中额外复制原测试已写出的临时stdout/stderr到独立`live-run-script-*`，避免超时或服务断连后证据消失；官方命令与退出行为不变。此举不预先宣称SIGBUS根因已被证明。

启动时已实查CPU11无consumer，独立lease写入`cpu11-lease.json`。持续sleep guard `apex-baseline-base-swe-repair11-20261017.scope`的affinity固定11，确保三项切换时其他队列仍能看到租约。所有原生scope确认退出后才停止guard并写`all_cpu_consumers_finished=true`。

Vuls在03:10完成：同patch新鲜replay原生reward=0、无exception；真实编译报`scanner/utils.go:12:2: logging imported and not used`，现有评分逻辑已有效认定为候选失败。receipt为`analysis/source_snapshots/base_swe_vuls_native_repair_20261017.json`。scope CPU affinity实证为`{11}`，MemoryMax=4294967296，容器/tmp位于/data磁盘。

原零准入等待controller PID3004525和后续等待parent PID3102265均确认无子进程后停止，Vuls未被中断。CPU11的sleep guard保留到最后一项结束，正式scope退出后再释放；遇未解决的基础设施错误则保留guard等待修复。

03:14，NodeBB同patch新鲜replay已完整输出Mocha结果。保持原测试原parser，对额外保留的live stdout/stderr执行原parser，得到311/311测试、307通过、4明确失败，恰好覆盖官方311项required tests。原Mocha统计335次调用（含重名），331通过、4失败，报告完成时间为03:12:50.153。receipt为`analysis/source_snapshots/base_swe_nodebb_completed_test_evidence_20261017.json`，原始输出及完整官方parsed output仍在80独立evidence目录。

root接受完整测试报告作为该固定patch失败0的证据，并明确授权结束仅挂退出的自有scope。先持久化完整原始输出、原parser结果与exact patch身份后，仅停止`apex-baseline-b52c8ab6295b.scope`，未加--exit、未恢复.mocharc、未写reward文件。03:16确认scope成员为空、controller退出；新原始result保留`RemoteProtocolError`、native_reward=null，verifier目录无reward文件。第三条audit以原clean28 result为身份、另指新evidence result，明确`audit_kind=complete_official_test_report_with_failures`，audited_reward=0，保留受控cleanup事实；这不是默认None转0。receipt为`analysis/source_snapshots/base_swe_nodebb_cleanup_20261017.json`。

后续Go容器启动时会将原GOCACHE/GOMODCACHE内容复制到/data临时磁盘，再将写入指向该副本，减少4GiB范围内的不可回收tmpfs压力；原依赖、校验和内容均不变。Vuls在途未应用该变更。额外保留server日志与cgroup资源事件，供区分SIGBUS、OOM和传输错误。

Teleport首个新attempt在正式测试前因启动环境漏掉既有musl shim而失败：glibc libfakeroot在Alpine中缺`__snprintf_chk`等符号。该attempt未生成答案、未执行评分测试，原result及receipt完整保留。修复只是在专用musl进程PATH首位恢复已验证的`musl_compat/shim`（`--ignore-fakeroot-command`），与原clean28 musl cohort一致。

03:20，Teleport attempt2 PID3166965已进入scope `apex-baseline-093707571691`，/tmp及两个Go cache已实证在/data磁盘且原样复制成功。新结果将写`artifacts/eval/base_swe_gap_repair_20261017/replay_attempt2/<task>/result.json`。精确选择路径和实际controller PID在`analysis/source_snapshots/base_swe_replay_selection_20261017.json`，原bootstrap失败路径不覆盖；启动receipt为`analysis/source_snapshots/base_swe_teleport_repair_launch_20261017.json`。

03:28:43，Teleport attempt2正常完成：原生reward=0、exception=null、23 PASSED与2 FAILED，14项required中12通过。官方`-race`报告候选修改的`Agent.plan`及`AsynchronousTokenCounter`并发读写data race，导致`TestChat_Complete/text_completion`及父测试失败。原生stderr为空、oom/oom_kill均0，不是新基础设施异常；详见`analysis/source_snapshots/base_swe_teleport_native_repair_20261017.json`。原patch不变、0新模型调用。

最终已核所有自有native scope与CPU11 guard均inactive、成员为空、controller退出，`cpu11-lease.json`及`all_cpu_consumers_finished.json`真实置完成。仅在确认排空后清理本分支四个独立`native-*` scratch目录，/data可用空间观察增加约4.99GiB；共享Go cache、SIF、答案、raw logs、parser输出和审计全部保留。receipt在`analysis/source_snapshots/base_swe_gap_repair_cleanup_20261017.json`。

自有repair脚本现已将Teleport必须使用原musl shim固化为启动前置条件，并保存实际PATH/完整启动命令，避免直接运行再次漏掉；本轮首个启动失败仍保留为独立历史attempt。
