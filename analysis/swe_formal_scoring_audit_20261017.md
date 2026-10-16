# SWE 正式评分只读审计（2026-10-17）

结论：初始专家5项 invalid 中，Ansible两项与Flipt524共3项有充分证据建议保留原生reward=0、仅解除empty-tests audit。Teleport7744原public Go超时确为infra；获授权恢复原网络并重放同一空patch后，参考依赖元信息显示预期实现本应固定兼容模块版本，因此新结果另建议作为缺必要依赖实现的原生0候选，由主线程统一审核。NodeBB原因未定，不能自动归infra，也不能只凭捕获配置删除就归因模型。**只读审计阶段未改任何评分、原始patch、队列、服务或Base输出，也未执行新模型/容器/测试/replay。** 主线程随后明确授权了文末单项score-only修复与短只读原镜像probe；原三项0分建议仍未改collector。

快照：`artifacts/eval/swe249_hard51_20261016/summary.json` 于2026-10-16T18:49:40.831097Z，28 valid/51、0 resolved、10 active、8 pending、5 invalid。队列仍在继续，这不是最终分数。原4项外新增Teleport7744 public dependency timeout。本报告不会把尚在途的`not_scored`当invalid，也不重算“修正后分数”。

## 判定方法与范围

只读保存的generation `agent/model.patch`、完整mini工具动作、replay `agent/replay.json`、原生verifier stdout/stderr/output、固定task的run_script/parser/test_patch；第一阶段没有读取gold_patch内容；主线程随后仅为评分归因授权读取Teleport的go.mod/go.sum依赖元信息，未读/复制参考实现代码，也未送入模型或训练。对5个已保存结果提取并运行当前`collect_swe_final.score()`，复现其5个原始分类；Flipt另运行原parser处理已有stdout，稳定复现tests=[]。这些是保存记录的确定性核对，不冒称新跑测试已验证修复。无CONTEXT/ADR文件可供补充。

当前collector空tests逻辑是audit门槛：它只对少量compile/import错误正则放行，不认识future-import SyntaxError、缺任务要求的新模块、或“只有顶层FAIL/缩进PASS”的Go输出。**tests=[]不是统一infra证据。** 不能简单扩大为“所有ModuleNotFoundError都0”，因为缺pytest/pip等runner依赖仍是infra。若主线程采纳3项结论，宜用针对固定result路径＋patch SHA的明确audit记录，不改官方parser、不改变已存reward，更不改Base owner结果。小patch的SHA/字节数及原路径见配套receipt。

工具观察已由主线程核实为目标JSON；训练system63字符、actual62字符仅尾换行差异，strip相同。console XML显示不能作为harness错位证据。环境差异来源仍有未证实部分，本审计不声称已解决。

## 专家逐项证据

下列短ID均对应配套receipt的完整task_id；证据根为`artifacts/eval/swe249_hard51_20261016`，完整文件在80项目同一相对目录，报告不复制题面或完整exception_message。

| 项 | 原分类 / patch | 只读判断 | 建议 |
| --- | --- | --- | --- |
| Ansible c1f2 | empty_tests；0字节 | 任务要求新建bigip_message_routing_route，测试先尝试library fallback再尝试Ansible目标；空patch未提供目标模块 | 原生0，解除该项audit，无需replay |
| Ansible d33 | empty_tests；10,153字节 | patch在manager.py函数之后插future import，native import链精确报同文件69行SyntaxError | 原生0，解除该项audit，无需replay |
| Flipt524 | empty_tests；0字节 | 测试真实执行，3个顶层FAIL＋5个子测试FAIL＋147个子测试PASS；原parser只接受无缩进顶层PASS，结果为空 | 原生0，解除该项audit，不改parser或replay |
| Teleport7744 | public Go timeout；0字节 | 原网络超时是真实infra；后续同patch网络修复成功，参考实现本应固定兼容依赖而空patch未提供 | 原timeout保留invalid；新replay为原生0候选，见文末依赖审计 |
| NodeBB8168 | VerifierTimeout；7,422字节 | 捕获patch删6文件225行，包括.mocharc的exit:true；但40条保存工具调用均读操作，未见删除命令 | 保持未决，先核初始dirty状态；不盲重放/不改成0 |

Ansible c1f2的`replay/<id>/verifier/run-script-stdout.txt:9,18,40`摘录：
```text
collecting ... collected 0 items / 1 error
ModuleNotFoundError: No module named 'library'
ModuleNotFoundError: No module named 'ansible.modules.network.f5.bigip_message_routing_route'
```
这是所需实现缺失，不是pytest或第三方runner包缺失；任务固定说明和test_patch imports互相吻合，空patch没有引入新依赖。

Ansible d33的`verifier/run-script-stderr.txt:8,9,11`：
```text
File /app/lib/ansible/config/manager.py, line 69
from __future__ import annotations
SyntaxError: from __future__ imports must occur at the beginning of the file
```
固定patch第9行就是新增future import，位于原文件函数之后。因果链可从patch与已保存trace直接闭合，不需要重新求解或以“收集失败”豁免。

Flipt524的`verifier/run-script-stdout.txt:28,373,389`：
```text
--- FAIL: TestExport (0.00s)
--- FAIL: TestDBTestSuite/TestUpdateRollout_OneSegment (0.01s)
FAIL go.flipt.io/flipt/internal/storage/sql 4.696s
```
原parser正则只匹配`^--- (PASS):...`；原生测试有明确失败，raw reward本来0。空patch不等于infra，不能因为没有顶层PASS让该结果无期限null。

Teleport7744的`verifier/run-script-stderr.txt:4`（去掉非必要URL标点）与stdout:2：
```text
module github.com/mdlayher/netlink: Get https://proxy.golang.org/github.com/mdlayher/netlink/@v/list: dial tcp 142.251.34.209:443: i/o timeout
FAIL github.com/gravitational/teleport/lib/auditd [setup failed]
```
使用既有`SweCleanMuslScoreEnvironment`，prep return_code0/29.35s，preseed copied185/kept42。已有cache确有netlink v1.6.0的info/mod/zip/ziphash/list/lock六文件，先前官方下载receipt也存在；故“重新拷cache即可修复”尚无证据。冻结test.sh:5–6重置原GOPROXY及其自带sumdb设置，原test_patch imports触发版本list请求。最小方向是恢复原public proxy可达egress，保留原URI、原版本解析和原校验设置；不得借修复加入任意版本、改go.sum或关闭校验。

NodeBB的`verifier/test-stdout.txt:7`是`Terminated`，`trial.log:3`记录3000秒timeout，未保存run-script stdout/stderr或output。原run_script会把stdout/stderr暂存至临时文件，**仅在命令返回后**复制到logs；timeout造成证据缺失。run_script覆盖reporter/bail/timeout，但没有显式--exit；捕获patch删除.mocharc里的`exit:true`可能影响进程退出。另一方面完整mini轨迹40条bash调用全为ls/cat/grep/sed读取，exit_status为BadRequestError，未见写/删命令。官方capture直接`git add -A; git diff --cached`，没有初始dirty diff扣除；因此删除可能先于模型，尚缺原镜像/初始状态证据。不能把“model.patch文件中的删除”自动叫模型主动删除，也不能因此就宣告基础设施根因。

## Base五项只读对照

Terminal agent并行核权威`artifacts/eval/base_swe_v2_20261016_clean28/corrected51_summary.json`的5个invalid；本地旧`swe_final_*`是另一份legacy51/51、5resolved汇总，不是本次canonical来源。**不改判、不覆盖、不给Base追加任何replay。**

| Base项 | 原分类 | 既有原生日志所能支持的判断 |
| --- | --- | --- |
| NodeBB8168 | VerifierTimeout | 同样捕获.mocharc删除、仅Terminated；不能单称infra，删除来源与因果仍需核 |
| Flipt c188 | public Go timeout | prep在0.570秒先return1，ecr v1.30.0/go.mod checksum mismatch；patch新增该go.mod/go.sum记录。后续网络timeout不是唯一问题，不能概括纯infra |
| Vuls5af | RemoteProtocolError | `Server disconnected without sending a response`；prep return0/104.352秒；无原生编译/断言结果，符合verifier传输失败证据 |
| Teleport2b | RewardFileNotFound | 官方test_patch已apply；prep return0/232.857秒，无run-script stdout/stderr/reward，缺失根因未定 |
| Protonmail5f | empty_tests | `TypeError: (0 , _hooks.useConfig) is not a function`，精确落在patch新增BitcoinInfoMessage.tsx:11:35；有模型新增组件运行错误证据 |

Base Flipt prep记录与patch的go.sum不一致，须保留原安全检查，不能删除sum或跳过校验来“修复”。Base Protonmail的empty-tests也不是自动infra结论。这些只提供owner审计线索，不改变其canonical状态或得分。

## 初始修复建议与CPU租约（后续授权执行见下）

1. **无需replay的3项**：采纳上述逐结果audit结论即可保留native0。不要重新生成答案或修补模型代码。执行评分归类变更由主线程决定，本分支未写override或collector代码。
2. **Teleport7744单独score-only replay**：沿用同一固定task、SIF、空patch和PatchReplayAgent，独立新attempt目录，恢复原public Go proxy的网络可达性；先只检查实际请求所需/@v/list可达，不改变官方test.sh、go.mod/go.sum、动态版本解析或原sumdb行为。已有cache/prep成功但测试仍访问公网，故仅重复cache安装不是充分修复。不要复用会重新generation的expert `--single-task`入口；现有score-only `replay_swe_score_environment.py`可指定`--category all --task-id`和原source_job，只作审核入口，尚未启动。
3. **NodeBB先60秒只读preflight**：在同一原始SIF/既有setup后、无模型无verifier地读取`git status --short`、`.mocharc.yml`是否存在/是否tracked及原始内容，核预存dirty状态；对照固定captured patch，不restore配置、不添加--exit。若仍无法确定卡在哪里，可另外审核一次同patch、原3000秒replay，只增加临时stdout/stderr的增量外部留存，原测试命令/预算不变；目前不建议盲等50分钟后再拿相同空日志。
4. **租约**：建议CPU10单槽、每replay仍1CPU/4096MiB；CPU11只给上述短preflight（≤60秒）后释放。最多1个正式replay，0GPU/0模型API，保留原3000秒verifier与既有1800秒prep上限，单次租约预留≤85分钟含启动/排空。启动前确认10–11没有现有SWE/merged consumer scope，并由root正式授租；不得占用0–9或Terminal/ASI区域。最终须等replay及所有scope真实退出后释放。**提交该建议时尚未实际占用租约；主线程随后授权的真实执行与排空记录见下。**

配套小receipt为`analysis/source_snapshots/swe_formal_scoring_audit_20261017.json`，只含身份、相对路径、短错误、patch小文件SHA和核验记录；未写原始题面、完整exception_message或凭据。Git/共享claud.md仍由主线程处理。


## 主线程授权后的独立修复实际结果

主线程明确授权仅对专家Teleport7744固定patch进行网络修复后的score-only replay，并允许CPU11短只读原镜像检查；禁止改测试、go.mod/go.sum、模块版本、工具链、校验或Base/原专家队列。实现为`scripts/swe_score_original_proxy_repair.py`，输出独立`artifacts/eval/swe249_teleport7744_proxy_repair_20261017/`，始终引用原expert source_job与原invalid result。没有模型请求，没有改collector/原始result/canonical。

**NodeBB原镜像probe**于18:54:21Z完成：真实scope `apex-baseline-78cffdfdb5c3`、CPU11、原始git status与diffstat均空；.mocharc是tracked文件，内容包含exit:true。只启动原环境，没有agent安装/求解或verifier；18:54:23Z确认CPU11排空。说明缺文件不是原始SIF一开始就缺，但删除发生在后续哪个阶段仍未证明；40条读操作与最终删除之间存在证据缺口，不能反过来声称模型主动删除或harness已定位修复。

**Teleport网络探针通过**：80直接到原Go proxy超时；Mac通过同一原日志原站IP142.251.34.209可达，保留原TLS SNI和证书校验。因此只为本次scoring提供固定路由：namespace loopback → 私有Unix socket → 80 loopback SSH reverse → 原站IP443。只接受CONNECT proxy.golang.org:443，未改DNS/全局代理/URI。HTTPS_PROXY仅传给该环境官方verifier命令。2026-10-16T18:54:50.720998Z，**同一官方musl环境**对原URL `https://proxy.golang.org/github.com/mdlayher/netlink/@v/list`返回HTTP200、curl return0；真实CPU10 scope `apex-baseline-b951df765612`，实际进程affinity[10]，沿用1CPU/4096MiB/3000秒。探针成功才进入原PatchReplayAgent及verifier。仅4次CONNECT且全部原host，无额外CDN/其他host；没有扩大allowlist。

原生fresh replay在18:55:48.886419Z完成，raw reward0、无Harbor异常、tests仍为空，**原collector给empty_tests_requires_audit，未经统一audit不能接入有效分**。网络故障消除后，官方未固定版本的netlink依赖解析到v1.11.2，与冻结镜像的Go工具链不兼容。新`verifier/run-script-stderr.txt:2,4,11`三行：
```text
go: downloading github.com/mdlayher/netlink v1.11.2
go: found github.com/mdlayher/netlink in github.com/mdlayher/netlink v1.11.2
/go/pkg/mod/github.com/mdlayher/netlink@v1.11.2/conn.go:4:2: package iter is not in GOROOT (/usr/local/go/src/iter)
```
仅凭上述iter错误不足以完整归因。主线程要求再只读参考依赖元信息后，补齐了关键证据：该任务gold_patch确实同时修改go.mod/go.sum，在go.mod patch:9新增netlink v1.6.0，在:25新增socket v0.1.1 indirect，go.sum patch:46–49固定对应module/go.mod校验记录。这里仅记录依赖版本与修改位置，不复制参考实现代码。既有专家保存工具观察中，assistant message5执行grep mdlayher/netlink go.mod无输出；message14确认原native Go1.18.10、原go.mod为go1.18。即原base缺该依赖，预期实现应自行带兼容版本固定，而专家空patch没有提供。

**最终建议修正**：原public proxy超时是真实infra，所以此次score-only网络修复有依据；网络恢复后的最新依赖不兼容，并不能继续自动归“全局infra”。它是模型未提交所需依赖声明、被官方mod=mod解析到latest的后果，符合原生0候选，应由主线程按与其他模型补丁setup失败一致的规则审核。该结论不要求参考实现一定通过全测试，也没有拿gold修补模型答案。新结果仍由原collector标audit，尚未改有效性或canonical。

按授权范围已停止：没有pin旧netlink、改go.mod/go.sum、升级Go、应用参考patch或再跑一轮；无任何参考代码送模型/训练。不得为了让空patch“可跑”补上它本来应实现的依赖。

新结果和原invalid并存，原patch SHA始终为e3b0c442...b855（0字节）；新source引用、raw reward、原collector原因都在receipt。**没有按reward选择、没有接canonical**；待原51队列结束后仍由主线程统一审核最早环境有效结果。

启动阶段的小失败也原样保留：第一次在正式probe前Unix socket路径过长；下一次native bootstrap因独立launcher缺少原expert leaf的musl shim而失败，未运行agent/verifier，保存于bootstrap_attempt1。随后采用与原expert leaf相同的shim/私有运行路径，通过native probe并执行上述唯一实际verifier。实现现在显式准备同一private PATH，避免重复该启动问题；没有系统环境改动。

18:55:48Z后已确认CPU10–11无任何apex-baseline scope；私有Unix socket删除、namespace relay退出、SSH reverse TLS转发关闭，80端口38443不再监听。所有原任务/权重/源patch/官方测试保持；本分支本轮owned files仅本报告、配套receipt、score-only修复脚本三项。


## 统一评分有效性建议（独立核审前不改实现）

主线程认可三态方向，仍要求独立核审后再决定采用；本轮collector、canonical和Base均保持。官方test.sh以`fail_to_pass ∪ pass_to_pass ⊆ parsed PASSED`判resolved，EXIT trap对任何非零退出写reward0，包括早期脚本/环境失败。因此**已有官方reward0不能单独证明评分有效**；环境有效时才直接沿用其0/1，不另造打分器。

| 状态 | 同一通用标准 | 处理 |
| --- | --- | --- |
| valid native0/1 | 固定任务/镜像/patch的新环境replay；原生日志充分，无阻断判定的环境故障；失败可直接归因模型补丁、缺应交付实现/依赖或官方必需测试 | 沿用官方reward；模型引发收集/构建失败即使tests=[]也可0 |
| infrastructure-null | 明确缺runner预装依赖、public网络/服务/传输故障，且没有已闭合的独立模型失败证据 | 保留null；仅允许修复环境后同patch评分重放 |
| unresolved-null | 超时、缺日志/缺reward、解析不全或混合故障，无法作足够因果区分 | 保留null；不因错误名字或raw0归类 |

每个异常都用**三组证据**，不要求凑三条日志：①固定task/image/patch SHA与fresh-replay来源；②实际原生执行记录、错误阶段和reward；③错误点与patch改动/缺失交付之间的直接因果，或明确环境故障。已有证据能闭环就无需新执行；不能把“某错误常见于infra”当因果。某个ModuleNotFoundError可能是缺pytest，也可能是本应新增的目标模块未实现；go.sum校验失败可能来自模型错误记录，也可能是缓存/下载损坏，须读对应来源。

本案应用：Ansible d33在模型改动行发生future-import SyntaxError；c1空patch缺任务要求的新模块；Flipt524的官方必需TestExport/TestImport/TestDBTestSuite有原生FAIL而parser只匹配顶层PASS，均支持原生0。Teleport原网络timeout仍是infra-null；网络恢复后的同patch重放有缺预期兼容依赖声明的证据，另列native0候选。NodeBB来源与超时因果未明，继续unresolved-null。参考依赖元信息只用来分清环境与应交付依赖，不要求模型与gold逐行/选库一致，不用gold修补答案。

风险与统一性：不能把任意Go FAIL算作必需测试失败，不能只因tests=[]归infra或归0；不能按异常类型一刀切；明确模型失败若早于后续网络报错，不能让后续超时遮蔽它。规则应对Base/专家/合版同一触发集合做相同审核，不按模型名或reward设例外。先固定每模型的generation来源（Base仍为其owner冻结的clean28＋native23），不跨旧/clean28答卷择优。只有证实infra才重放同patch、无重答；在同一patch来源内按时间取最早有效结果，valid0即停止，不取最好reward。固定分母51；存在null时只报coverage与resolved/51保守值，完整有效后才发布正式主指标，不能删除难评分项改分母。

## 五个已结束专家轨迹的tool/API边界只读统计

这次诊断与评分规则分开：**不能由0resolved推出infra，也不能把mini最终BadRequestError误称所有工具400。** 定向样本覆盖先前异常项与一个已有非空测试的valid0；不是全51失败频率估计，没有重答或更改服务/预算。

| 样本 | bash tool观察 rc0/rc1 | 工具层400 | 最终mini/agent终止 | 本地guard精确prompt计数 |
| --- | --- | --- | --- | ---: |
| NodeBB8168 |40 /0|0|BadRequestError|58,749|
| Ansible40ade |45 /0|0|BadRequestError|58,339|
| Ansiblec1f2 |39 /1|0|BadRequestError|58,759|
| Ansibled33 |83 /2|0|NonZeroAgentExitCodeError，exit124|无context拒绝|
| Flipt524 |42 /0|0|BadRequestError|57,707|

合计252条真实tool observation：249个rc0、3个rc1，**没有sandbox工具HTTP400**；全部调用均bash、command为字符串，实际request的tools schema逐项等于真实synthetic验收。c1唯一rc1是grep目标文件名无匹配、output为空，是正常命令非零返回，不是HTTP错误。

四个BadRequestError的最短安全描述都是`context_budget_exceeded`。冻结guard先tokenize并要求`prompt_tokens_exact + 8192 <= 65536`；以上四项分别超过，总和为66,941、66,531、66,951、65,899。`SweModelBridge.validate`抛ValueError，本地LoggedModelRelay在转发前返回HTTP400，LiteLLM把它显示为BadRequestError。不是sandbox exec400，也不是上游vLLM拒绝工具schema。末次被拒请求没有对应upstream raw；此前HTTP均200并完整保存。**这是冻结64K/8K预算的模型终止，不能转成基础设施重答理由；也不在本次缩减8K保留或滚动压缩上下文。**

d33另外77个上游响应HTTP200；第78个logical request通过token guard但在模型响应前RemoteDisconnected，response_bytes0。该请求开始于agent执行1737.11秒、结束1743.88秒，agent总1743.94秒、原生exit124，与固定内部1740秒GNU timeout终止吻合。不能仅凭该最后断连就判全局服务故障；保留确切时间与边界，不更改该模型补丁原生SyntaxError评分证据。

**synthetic同链路范围**：纯parser fixture的19/19只核已装mini2.4.6解析/JSON观察/结束检测，不发模型或容器请求；不能冒称完整端到端。另有真实`artifacts/preflight/swe_v2/native-lxwl19kv` synthetic_add，走mini2.4.6、相同LockedMiniSwe→bash工具schema、bridge精确tokenizer guard与fresh patch replay，5个真实model request与正式tools JSON完全相同，initial/replay reward均1。其agent类是较早SweBaselineV2，正式是继承链SweBaselineNativeV2（再经SitePackagesV2，增加私有安装/运行时核对）；端点是Base而非SWE249、运行时接受时间也不同，不能声称部署完全相同。该旧fixture receipt的cpu_memory_network:false，也不覆盖后续独立的资源/网络隔离验收。其prompt只到1,744 tokens，不能验证57K附近长历史边界或复杂任务能力；但本次实测252次bash工具成功返回JSON提供了正式链路证据。训练system与actual仅尾换行差异，console XML渲染仍不是工具契约错位证据。

本轮只追加本报告与同一receipt，无新脚本、API、GPU、容器或评测；三项owned files仍为本md、配套JSON与上一阶段既有score-only修复脚本。
