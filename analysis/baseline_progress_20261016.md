# Base baseline 持续推进记录

开始：2026-10-16T03:28:30+08:00。用户已授权本会话持续推进正式Base，并每30分钟检查。本文是本会话baseline工作入口；总体数据/费用/其他会话交接见[夜间总记录](overnight_progress_20261016.md)。正式执行以[协议v2](evaluation_protocol.md)与其JSON为准，不以安装成功代替原生验收。

## 最新实核状态（2026-10-16T13:47:02+08:00）

用户允许夜间断网类补跑，并选只远端继续、不重建半小时任务。HLE1679补跑已正式启动PID3887939，新服务725539；原309答卷+512预算超时保留。TB445恢复manifest已验、新725545独立近56K队列验收中；SWE原生CPU闭环已PASS，新725561真实端点验收与镜像兼容处理中，固定51不缩。3组共6H100已RUNNING，80直连HPC无需本机网络；ASI240答案齐，真实Judge校准14/14 PASS，CMOS grader环境适配后在¥6硬限内正式评分。下文03:xx/13:27均为历史检查点。

## 调度与所有权

- 当前会话side推进：`01a14017-2078-7490-9d13-6246c400173c`。heartbeat `apex-baseline` 已由应用确认ACTIVE，每30分钟恢复本会话检查与推进。
- 另一会话“整体推进”已在实现`serve_base_night.py/.slurm`及HLE薄runner，继续由该会话拥有，当前HLE专用服务作业724196、ACD1-61、2H100、18000端口。本会话不另起重复HLE服务，不修改其新数据工作。
- 本会话三子任务：ASI独立正式薄runner；Terminus2独立正式薄runner；SWE/TB的Apptainer网络phase与CPU/RAM后端。各任务只写自有脚本及专属status文档，由root整合，避免共享环境/索引争用。
- GPU总上限16H100、单组最多4卡；当前单TP2/4活跃序列/8准入solver及单benchmark块起点保持。申请更多副本前须测吞吐并冻结调度修订。不触碰其他项目722434，不改用户代理/镜像队列。

## 初始实际状态

| 项目 | 固定范围 | 当前状态 | 下一步 |
| --- | --- | --- | --- |
| HLE | 2500题／342图像 | 另一会话负责薄runner与共享端点；正式完成0 | 接真实视觉guard、300s、逐题保存与原生独立验收 |
| ASI | 60任务×4条件 | 本会话已启动direct_llm薄runner子任务；正式完成0 | 生成/执行共享1200s、单生成、4CPU8GiB、保存恢复 |
| Terminal | 89任务×5seed | 本会话已启动Terminus2薄适配子任务；正式完成0 | 原生主/辅助guard、单层安全重试、资源与网络 |
| SWE | HARD51 | LockedMini/mini2.4.6选定；backend关键门槛未过；正式完成0 | phase网络、1CPU4GiB、容器依赖锁与fresh replay |

## 必须保留的边界

HLE/ASI可先生成冻结答卷/产物，Judge独立校准和评分后置；不因Judge失败重答。正式逐题结果不回流训练数据或调prompt/预算。题目失败保留分母，输入超限不删图/裁题/缩输出；生成和辅助统一64K/8K非thinking。Terminal继续披露资源受限设置；ASI为官方direct_llm，不切回旧OpenCode。

rank/window仍未确定，本会话不启动训练或GPU反向。DeepSeek夜间总账与另一会话共用30元上限，不分别花30元；调用前先核总账。本轮尚无API费用。

## 检查点

### 2026-10-16T03:28:30+08:00：持续推进与半小时检查已启用

- heartbeat创建成功：automationId=apex-baseline、ACTIVE、30分钟间隔，绑定本会话；未修改另一会话现有apex heartbeat。
- 只读squeue确认724196 RUNNING（8小时服务申请）；722434为其他项目，未干预。启动成功不等于HTTP ready或正式Base已跑。
- 三子任务已并行开始，独立验收先于正式题。状态细节将链接baseline_asi_v2_status.md、baseline_terminal_v2_status.md及baseline_backend_v2_status.md。
- 自动检查依赖本地电脑唤醒、联网、应用运行；远端作业本身独立驻留HPC。依据已核官方Scheduled tasks说明：https://learn.chatgpt.com/docs/automations。

### 2026-10-16T03:34:57+08:00：按新增授权扩为三组独立TP2、共6张H100

- 用户补充：能提效即可多开HPC卡。独立每benchmark TP2服务避免HLE/ASI/TB互相排队；不改每请求64K/8K、每服务4活跃序列/8准入solver。多服务正式并行将在各服务并发与原生链验收后冻结调度修订，不能把分配当正式ready。
- HLE由另一会话管理：724196、ACD1-61:18000；80现有18061桥健康HTTP200，未修改该桥或runner。
- 本会话新增ASI724241、ACD1-61:18001；Terminal724242、ACD1-54:18002，均RUNNING，每组2H100/16CPU/128GiB/8h。本项目共6卡，ACD1-61本题两组共4卡；另一个项目722434不干预，账户QoS16卡额度另需计其现存使用。
- 已核本账号qinlucao只获formal-user QOS，最高可用本次emergency_acd分区PriorityTier=300；没有擅换账户/QoS或改别人的作业。空闲卡分散，先拿两组2卡，SWE后端就绪再申请其独立组，避免空转。
- 独立脚本serve_base_worker.py/.slurm复用准确Base运行参数，额外端口隔离，不修改另一会话的serve_base_night。两份语法检查通过。
- 本会话SSH控制socket /tmp/apex-baseline-80-ctl，新增80 loopback18071→ASI、18072→Terminal；HPC转发复用/tmp/apex-hpc-setup-ctl；不改用户代理/其他桥。新增服务仍加载；勿将health连接失败当正式题失败。
- 80独立队列验收probe PID2136213(ASI)、2136214(Terminal)，先等health，再各发8个合成并发请求(4长输入+4短输入)，检查exact/tokenize、完整输出marker、无thinking、采样及4活跃序列；未读正式题。回执目录artifacts/preflight/base-worker-probe-724241及724242。
- ASI子任务7/7合成验收首轮通过：真实三组科学环境/电路、8GiB/swap0、不可扩宽4核、断网、共享deadline和超时子树清理、超限零生成、已发送断连不重试、安全连接失败最多两次。还在补journal和真实Qwen链，不先跑正式240。
- backend已实证public→iptables deny→恢复public，以及嵌套userns改父firewall为EPERM；尚在接Harbor资源/模型桥，未把capabilities提前设真。Terminus薄runner/原生parser已落盘，真实端到端仍待验。

### 2026-10-16T03:41:34+08:00：独立TP2队列验收通过，冻结扩容部署记录

- ASI服务724241：8个合成请求均成功，其中4个prompt精确57344、输出预留8192；批次21.21s，Prometheus观测running峰4/waiting峰4。
- Terminal服务724242：同8个请求均成功44.49s，running峰4/waiting峰5；同窗另一项独立marker校准使服务共收到9个synthetic请求，额外压力如实保留，正式准入仍8。
- 两端服务精确tokenize与真实usage一致、无thinking、固定采样与auth通过，没有用正式题做压测。原始聚合分别base_worker_asi_queue_20261016.json、base_worker_terminal_queue_20261016.json。
- 单独冻结部署修订configs/eval/deployment_tp2_blocks_v1.json：core v2请求协议SHA保持，独立服务各跑一个benchmark/model块，可跨服务并行；每个比较模型同profile，不重写另一会话已有HLE run配置。原生门槛逐项通过才正式启动。
- ASI已真实自造程序产出正确矩阵/线性解/PNG，8进程生产worker与10项资源/恢复/length检查通过，真实取消观测running1→0/waiting0；最终同版native positive正在复核，正式240尚未启动。
- SWE已新增薄LockedMini子类与runtime约束，假environment的1740s内timeout和参数fixture通过；全容器/模型/patch replay链未过，不先申请闲置SWE GPU。

### 2026-10-16T03:43:10+08:00：正式ASI produce-only已启动

- 完整最终ASI验收passed=true：10项合成、8个生产worker隔离、真实自造科学单生成/单执行、取消后实际running1→0、scope/断网/恢复/length答卷先落盘。安全聚合baseline_asi_v2_smoke_20261016.json；最初独立开发题路径错误失败保留，没有对正式题调试或重答。
- 已在80启动正式固定60×4=240条件，专用worker724241/桥18071，控制PID2473386，最多8准入。flock锁artifacts/runs/base-asi-724241.lock防重复，启动记录.launch.json/日志.log同目录。
- 正式输出artifacts/eval/base_asi_v2_20261016，mode=produce_only_unscored；读取/执行正式输入已获用户授权，只保存产物不看逐题失败调训练或prompt。Judge后置，不把产物覆盖数当已评分分数。
- core v2 SHA与独立部署修订一致，runner/helper/runtime精确hash写入原生run metadata，进程已脱离SSH shell。另会话HLE独占724196，不复用同一服务抢队列。ASI脚本自本次启动冻结，不在运行中改源码。
- 保持本地已有或新设8小时caffeinate idle-sleep断言，帮助半小时心跳/SSH桥持续；合盖、断网或退出应用仍可能影响本地续跑及桥，不承诺离线助手决策。

### 2026-10-16T03:50:12+08:00：后端最终GO、TB原生闭环通过、SWE服务排队

- 80后端4CPU8GiB与1CPU4GiB两profile全部通过：actual cgroup/硬OOM/不可扩宽affinity，public→deny→public，AF_PACKET/NETLINK拒绝，固定模型桥，tmux正常保留/异常detached清理，停止后scope inactive；同controller两slot互不重叠。生产4helper源码SHA冻结，不能在正式运行期间改原文件。
- 代码与完整聚合analysis/source_snapshots/baseline_backend_v2_20261016.json；实现脚本和安装脚本/系统包SHA均可重放，无sudo。先前候选namespace路径失败也保留，不把放弃实现当已部署。
- TB真实独立native链63s PASS：Qwen→原生Tmux写读文件→两次完成确认→官方verifier reward1，精确P774/P1151；11项stub和实际取消归零均通过。89份SIF完整SHA已核，运行时源码/依赖已只读冻结。
- TB首次正式前置因Harbor拒跨task symlink而退出，0trial/0模型请求；只修metadata任务stage为字节原样copy并校验，新runtime/output保留旧失败目录，未改prompt/预算/Agent。由该子任务在前置通过后自主flock启动445试次。
- SWE新增独立TP2 job724254（2GPU/16CPU/128GiB/18003），排除已占本题4卡的ACD1-61，目前PENDING(Resources)。现有仍6卡运行、另2卡排队，不把排队称已获得8卡。SWE driver/受控模型桥/容器锁安装及自造fresh replay验收继续。
- 已直接核另一会话最新人类消息“数据弄好可以开始训练”；其已选r16/alpha32/dropout0.05并做四卡训练诊断准备。本会话仍只baseline，容量上留完整4卡训练组，不把全16卡占成推理；总账号16还计722434的1卡，不能私自换账户。旧“rank未定”是历史状态，不阻止另一会话已授权训练。
- 另一空闲子任务转ASI官方scorer/替代Judge dry-run与合成校准；未授权其付费调用，夜间30元数据支出总账仍由另一会话统一，评分先准备代码再核预算。


### 2026-10-16T04:01:56+08:00：8卡运行，SSH事故恢复与显式基础设施补跑

- 四组TP2服务均真实RUNNING：HLE724196/ACD1-61:18000，ASI724241/ACD1-61:18001，Terminal724242/ACD1-54:18002，SWE724254/ACD1-36:18003。共8H100，不把GPU在跑等同四项正式baseline在跑；另训练724277四卡等待，722434他项目一卡保留。
- 约03:53旧SSH master/socket消失，80桥18071/18072失效；HPC内网服务health均200，故障实证在转发进程。进程最初消失原因未证明；未改用户代理。HLE由整体推进恢复18061，本线只接管18071–73。
- 新scripts/supervise_baseline_tunnels.py+configs/eval/baseline_tunnels_20261016.json，Mac后台PID11878，状态artifacts/runs/baseline-tunnels-20261016/state.json，两条前台SSH子进程自动重连、独立socket /tmp/apex-baseline-hpc-ctl与/tmp/apex-baseline-80-ctl。真实杀自己HPC转发后health从reset转200，7.05s恢复；三服务self-authored marker请求正确、精确tokenize/usage/非thinking通过，SWE首次预热36.3s，另两端<1s。原GPU服务未重启。
- ASI旧attempt0已退出：240保存结果=229 tokenizer拒连未生成+8已发送断连无答卷+3已收完整答卷且执行失败。3保留为模型/程序失败，不允许重生；其余237经核为infra，明确人工授权第1次同ID/seed/预算全trial补跑，新目录/显式manifest，全部原日志/答卷/成本保留，按first valid chronological选择，不按分数择优。8项不被混写成安全HTTP重试。
- TB r2已SIGINT安全停，21结果=13transport+8取消，0正常完成、0不完整目录，5份完整policy response保留；明确人工授权21项第1次同条件infra补跑，未开始424项仍按固定445总清单。
- 两个独立修复driver验收中：最多8个future，每次准入health，transport异常熔断停止新准入/取消在途/保存checkpoint；旧生产源码/runtime SHA不改，桥绿之后也需断网stub通过才启动。原全trial自动重试0、人工infra最多2次、同HTTP read/ambiguous不得自动再发的协议保持。
- 尝试仅延长本线724241/724242/724254的Slurm TimeLimit，被权限拒绝，未升级/换账户；仍各8h，ASI11:30:57、TB11:31:29、SWE11:52:47到期（CST）。巡检至少提前1小时有序checkpoint/服务换班，避免到期被杀。
- ASI评分独立stub/校准及reference隔离准备继续；当前零付费，不挤占另一会话夜间30元数据预算。apex-baseline半小时heartbeat已更新事故分类/新桥/人工补跑/到期处理；本线持续推进baseline，另一线训练授权保持。


### 2026-10-16T13:27:18+08:00：用户询问后的baseline现场核对

- 当前HPC squeue(qinlucao)为空。sacct确认724196/724241/724242/724254均TIMEOUT，各占2H100约8小时；不能再把03:xx的8卡运行当当前状态。累计这四个服务约64 GPU小时，不等于有效求解GPU小时。
- ASI独立手工infra1的checkpoint在09:32:57(CST)完成237/237，237份原始response与237份精确condition result都存在；沿用旧3份答卷，固定240全部取得一次保留回答。原始执行status：新237中37 completed/200 failed，加旧3 failed，共37 completed/203 failed；执行失败尚未做完整原因审计，不把它们冒充最终正确率。正式Judge尚未执行，无最终得分。
- HLE由整体推进核实：2500保存记录中309完整回答、512真实300秒预算超时、1671生成前infra、8已发生成后断连；尚未评分/未完成有效全量。原答卷与失败均保留。
- TB目前现场仅旧r2的21结果(13transport+8取消)，没有正常完成的正式trial；owner已核recovery从未launch，无runtime3或445恢复manifest；当前仅两个新恢复源码通过语法检查，断网/恢复stub尚未完成。SWE未见正式result目录，最后文档仍native闭环验收中，正在核最新回执。
- 本线半小时automation apex-baseline当前toml状态PAUSED，未证实此时后台仍在自动检查；上轮设置ACTIVE不代表已实际完成到期服务续接。本轮已向用户明确夜间续跑/到期衔接没有做好。未擅自改他线自动任务、作业或代理。
- 另一会话训练724277已拿4卡，但数据加载cache权限错误FAILED，未到反向/正式训练；该会话正修同一配方。此处仅交叉核验，不接管其训练。


### 2026-10-16 13:35：用户明确允许断网类补跑，本线接管HLE网络修复

- 用户说明夜间自己电脑网络出问题，明确“如果是这类原因你可以重跑”。只对经核实network/transport infra按原ID/seed/预算补跑，不把程序错误/完整答卷/正常预算超时当补跑资格，原记录不删。此前ASI237补跑已完成，不重生240答卷。
- 本线现接HLE独立infra1修复：原run artifacts/runs/base_hle_v2_724196，显式选择1671未发生成+8发后断连=1679；原309完整答卷、512真实300s预算超时继续原结果；source/core/system/input hash必须一致。独立脚本repair_hle_infrastructure_v2.py，旧run_hle_v2.py原SHA不改，8并发/逐次准入health/独立周期health/断网取消checkpoint。合成断网/恢复与2500分类fixture已PASS，0真实请求。使用相同HLE block flock避免另一会话重复启动。
- 已验证80直接TCP到HPC内网SSH可达；专属ed25519私钥仅在80 artifacts/private，600，不复制用户原私钥。HPC只追加本项目受限public key：禁shell/PTY/agent、只允许18000–18003端口转发；已用原先信任的known_hosts严核连接成功。正在部署80驻留直连supervisor，后续推理链不再需要Mac转发。未修改原用户代理或其他密钥。
- HLE新GPU服务申请24h（命令覆盖旧8h申请，不能延长旧job的权限限制不适用于新提交），实际接入前需服务health/图文合成与真实取消验收。TB恢复445 manifest/stub及SWEbootstrap修复并行，消费者ready前不分配其空闲GPU。


### 2026-10-16T13:47:02+08:00：仅远端续跑已恢复，HLE网络补跑正式启动

- 用户已选择“只继续远端补跑”，不重建半小时任务。原apex-baseline在应用返回does not exist；本地残留TOML不是现存任务证明。本线未创建新自动任务，后续远端controller/supervisor常驻，不承诺本地助手定时决策。
- 新服务全部RUNNING共6H100：HLE725539 ACD1-16/24h，TB725545 ACD1-24/36h，SWE725561 ACD1-36/12h；原ASI生成已完成不再占卡。另训练725568四卡排队，额度与CPU均保留，不改他线作业。
- 新直连80→HPC supervisor PID3864879，端点28081/28082/28083，独立SSH子进程可各自重连/换服务，无Mac转发依赖。实测杀HLE的SSH子进程后3.615s恢复，TB子进程PID未变；用本机原known_host严格验hostkey，80私钥600、HPC公钥仅允四个模型端口、禁止shell/PTY/agent。首次候选18081端口被其他程序占用（只做无凭据health），已改确认空闲的28081–83，未改占用程序。
- HLE正式补跑已启动：80PID3887939，artifacts/runs/base_hle_v2_724196_infra1，固定1679人工network retry1；真实初始running/8 admitted/8started/8active、0完成，未预排1679；原821结果（309答卷+512预算超时）不改。独立断网/恢复stub PASS，继承冻结原请求/图像/采样/300s/core/input/system/source SHA；完整响应先落盘，每题准入与等待均健康检查。服务新图文8合成全部PASS，4图像，耗时<48s。第一轮合成和断线注入误重叠导致8合成失败，原目录保留，正式题0；待断线测试结束后独立r2通过，不隐去这次工程失误。
- TB显式445 manifest/runtime3与熔断/445全调度stub已PASS，旧21/5响应保留；新725545身份/短marker/tokenize/usage/nonthinking通过，8近56K合成队列验收正在跑，全绿后owner持同锁自主launch。SWE cached bootstrap已在原生mini/patch/fresh replay CPU fixture PASS（1CPU4GiB/断网/资源/cleanup），新725561实际端点还在warming与真实原生验收；49/51镜像已缓存，8musl/fakeroot、10缺curl单列继续修，不删51分母。
- ASI真实Judge校准14次PASS，正确/错误text10/0、vision10/0、CMOS12/0，身份全一致；observed usage峰价上界¥0.0298728，保守预留¥0.3157632。240固定选集无APIprepare全部通过，正式评分预计含native重试≤396calls/¥5.7539952；root已授权独立评分硬限396/¥6，在CMOS固定ngspice backend与fixture验收后自主启动，绝不再生政策答案。
- 代码/metadata部署configs/eval/deployment_direct_hpc_v2.json仅变网络与服务生命周期，不改pertrial资源/预算/原生prompt或分母；core JSON SHA不变，Terminal资源受限/替代Judge披露继续。


### 2026-10-16T14:00:12+08:00：速度优先与实际HPC效率核对

- 用户明确时间紧、速度效率优先、hash可以不做。所有子任务已通知停止后续全量hash、重复资源/镜像/包验收、非必要健壮性框架；沿用已完成证据，保留原Agent/参数/固定范围/预算/结果落盘/不重复答卷基本正确性。已经启动的生产源不边跑边改；新cohort不再以hash作为启动gate。
- 用户已选“只继续远端补跑”，不重建app每半小时任务。本线远端controller与SSH supervisor持续运行。GPU消费块完整结束才由远端小watcher释放本线725539/725545/725561；暂停审计不自动取消。SSH专属key仅增加固定三job的status/release强制命令，无任意shell；HPC Python3.6兼容问题已修，own-job status实测通过，未取消任何job。watcher PID52101，SWE完成标记需owner写入固定path后才触发。
- 13:59实测6H100尚未完全利用：HLE4 active/4 waiting；Terminal0/0（bootstrap300s卡apt导致RuntimeError，8项保留、437待开始，私有缓存bootstrap修复中）；SWE4 active/1 waiting，已进入真实模型和fresh replay，51固定范围分批推进。SWE初次symlink stage错误0模型请求41条保留，materialized driver实际PID3919212；7项Ansible被额外egg-info版本gate误挡0生成，按用户加速偏好取消这类额外gate后另cohort继续，不重生已收答案。
- HLE15秒实际aggregate decode62.78 tokens/s，4active/4waiting稳定。分配到本服务的两卡15个样本GPU util均值100%与20%（rank1范围19–21%）；说明当前4序列软件上限在跑满，但不能声称两卡算力/整个HPC利用最优。另两组在该瞬时NVML样本均0%（之后SWE已进入4 active）。优先修生产阻塞，暂不继续增加闲置副本。
- ASI评分最初prepare遗漏public参数导致8个evaluator KeyError；原结果parameters为空，grader已从原framework_task_info.json补齐内存参数，不改答卷/gold/rubric。旧评分API0、回执保留；新--skip-hashes正式score PID4019427，目录scoring_v2_formal_params_20261016，240固定scope、¥6/396硬限，正在推进。
- ASI203 failed只读类别审计：49ModuleNotFound（pandas37/sklearn4/scipy4/numpy3/markdown1）、2ImportError，另Key/Syntax/Value/Type等；未命中网络/权限/OOMpattern。缺依赖/文件59项需审计声明环境后判断，不能一概叫模型失败，也不能重生完整答案。


## 2026-10-16 14:32 CST: full production, concurrency x2, no extra tests

- Latest human instruction: run the full baseline directly, spend no more time on tests, preserve logs and checkpoints. Synthetic concurrency/boundary probes were cancelled before any model request. No new hash gates. New server only waits for HTTP health.
- New TP2 job725705 requests2H100/16CPU/128GiB/12h, max_active_sequences8; still PENDING(Resources). Existing HLE725539/TB725545/SWE725561 use6H100. Training725704 uses1GPU; leave it untouched. Actual per-task64K/8K, seed, CPU/RAM, timeout, native agent and fixed denominators stay unchanged; disclose concurrency profile in final results.
- Remote80 one-time continuation PID449163 is resident: artifacts/runs/baseline-x2-725705/{state.json,events.jsonl,controller.log}. It waits for the fixed job, adds28084 forwarding, then executes swe-launch.json on health readiness. No laptop dependency or app automation.
- SWE full first-generation cohort43 is RUNNING, parent PID452167, artifacts/eval/base_swe_v2_20261016_full: glibc33+musl10, two8-slot groups on CPU64-71/76-83, existing28083(max_model_sequences4) until the new8-sequence service is healthy. Two missing images remain in the download queue and are admitted when ready. Handoff writes STOP_ADMISSION, waits for all active trials naturally, then moves only pending never-started IDs to28084; no task is cancelled merely to change concurrency.
- SWE old NodeBB and Ansible d624 hit normal budget exit124; retain their patches for fresh replay, never regenerate. Six prematurely cancelled tasks retain all trajectories/patches and remain incomplete rather than silently becoming normal1800s failures. Old7 zero-generation setup tasks are included in the43 first generations. Fixed denominator51 remains.
- TB runtime5 still runs full445: observed14:27 eight active/421pending/16historical infra,120complete policy responses+8inflight, no final valid trial yet. Native request/raw response files and checkpoint writes are atomic, first_valid uses setdefault. New16 runner has natural STOP_ADMISSION drain and nextpoint; old live runner has no such interface and was not hot-patched.
- HLE infra1 continues1679 with original821 results retained; observed14:26 admitted79/completed71/active8. Raw complete responses are saved before validation. ASI240 answers stay frozen; native CPU grading continues.

- 14:35 follow-up: job725705 is now RUNNING on ACD1-12, model loading. Inference allocations total8H100 plus the other chat single training GPU=9; no extra synthetic model requests. Remote waiter has added the new28084 forwarding target and is waiting for model health.

- Latest production observation: SWE glibc452169 has8active with137requests/137raw responses; musl root461500 has8active with5requests/5raw responses, total16formal tasks in flight. Earlier9musl setup errors were all before generation and are retained. Additional child registration participates in natural handoff. Budget-only fresh replay489743 usesCPU84-85 and no model calls.


## 2026-10-16 15:34 CST: measured progress and campus API route

- Human asks for actual progress and clarifies HPC can call the HKUST(GZ) API even without general Internet. Authenticated HPC GET https://aigc-api.hkust-gz.edu.cn/v1/models returned200 and lists exact DeepSeek-V4-Flash / DeepSeek-V4-Pro. Host80 direct call failed. No generation request, no new calibration, and no credentials copied to files or logged. Route metadata is configs/eval/hkust_api_route.json; current completed scores and Base answer generation are unchanged.
- HLE15:29:197/1679 network-repair attempts ended,70 complete answers/127 failed,8active. Including original821 retained attempts:1018/2500 ended,379 complete answers; ended includes genuine budget timeouts and is not accuracy.
- ASI native grading finished15:14:37:240 visited,239 valid/1 evaluator-invalid/pending0. Native soil file_match crashes on empty prediction. Strict headline remains null; valid239 subset mean1.57756158%, clearly-labelled full240 zero-fill auxiliary1.57098841%. Formal Judge API0calls/0CNY; previous14 synthetic calibration calls are separate. No answer regeneration.
- SWE15:25:43 first-generation cohort has18terminal/8active/17pending; old2 normal-budget patches have fresh replay and6early-cancelled tasks remain incomplete. All51 images cached by14:44, download queue failed0. By15:32 glibc has9terminal/7active/17pending; musl root10terminal/0active/0pending. Replay-valid coverage is tracked separately from terminal counts.
- TB stopped14:41 after a single distribution-search verifier timeout incorrectly tripped the entire queue.7/445 valid=1reward1+6reward0,414never-admitted pending,7cancelled partial solvers retained,17failed attempts including historical bootstrap errors. Owner is starting a new16-solver production leaf that isolates verifier failures and preserves existing valid results and raw responses.
- New8-sequence service725705 actually became ready14:36:53. The once-waiter had exited on unhandled early-health ConnectionResetError; its stale checkpoint made it look merely loading, and the2GPUs remained unused for about49min. Fixed only that observed exception, restarted80 PID2004017 at15:25; consumer2004064 now performs natural drain before moving pending SWE IDs to28084. No new synthetic tests or hashes. Old live trials are not cancelled for handoff.


### 15:40 CST follow-up: real16-solver Terminal resumed; scoring issues retained

- Terminal runtime6 launched15:37:29, PID2052444, endpoint28082, first16admitted/398pending/haltedFalse.7prior valid remain1pass+6fail.24older unscored entries are retained as21cancelled+2failed_attempt+1verifier_incomplete; no answer regenerated. Single verifier errors now remain local to the trial rather than trip the full generation queue. Source scripts/run_terminal_full16.py; native log runner-full16.log and launch-full16.json.
- HLE15:39:217network-repair attempts ended,225admitted/8active;821original retained gives1038/2500ended. Ended counts include failures/timeouts, not only full responses.
- SWE15:39:glibc15terminal/1active/17pending, musl root10terminal/0active/0pending; plus2older normal-budget replays gives27terminal records. The audited25replays contain1official reward1,24reward0, but7need environment review:pytest4,pip1,Go download timeout2.18have no such environment error flag; do not call7unreviewed errors model failures.6old premature cancellations remain incomplete. Original patches are retained; owner continues grader-only repairs/replay, without regenerating answers or extra synthetic tests. New8-sequence service handoff remains in natural drain until the last old trial ends.
- ASI remains239valid/1native-evaluator-invalid/0pending.49missing-import execution errors were audited:37pandas,4sklearn,4scipy,3numpy,1markdown all use packages absent from the official corresponding TaskEnv declarations. All declared packages satisfy the16cached environments checked; no declared dependency missing-install evidence, so no package-addition execution reruns. HKUST route available for future API calls; current ASI formal API count0 and existing completed scores were not moved.


## 2026-10-16：完善四项完整 baseline 结果（16:08 CST）

- 用户要求继续完善并跑完。远端80生产、评分、补跑、汇总常驻，不重建app定时任务，不增加hash或额外测试；保留原始答案、全部attempt和成本，以及固定范围与预算。
- ASI已完整240/240有效、0invalid/0pending，百分分1.5709884069%（377.0372176580/24000）。soil b2原(3650,0)预测违反公开(n_days,5)契约；定点adapter使空min异常成为原hard-gate失败，其余239条记录保留，官方src/rubric/gold未改；正式Judge0次/0元。
- HLE保持原300s/64K8K生成。正式streaming Judge PID2370521，校内DeepSeek-V4-Flash，经80专属TLS28443通过HPC访问校内API，保持原SNI和CA验证，2并发/10元与5000calls硬限。16:06已969/2500有效，0judgeinvalid，未齐主分null；原生预算无答卷记0，网络或评分错误不冒充0。
- SWE当前17项在maxseq8服务725705上16并发；已27有效、2resolved，Flipt原patch官方评分继续补精确Go缓存。历史6项获当前用户授权infra retry，旧部分轨迹、patch和成本保留；group1自然完成并确认旧namespace进程归零后复用76至81提前接6，与group0重叠最多14solver。GPU完成marker等待17加6全部消费结束。
- Terminal发现runtime6单题tmux缺libutempter又取消15peer，当前396从未准入；至少5旧reward0是curl/uvx缺失导致原生tests未运行，必须改infra-invalid并恢复原答卷评分。owner正隔离单项infra错误、补私有harness/原PATH/官方依赖、纠正隐藏600s verifier HTTP deadline为官方3600s；后续评分失败在cleanup前保留必要输出或就地恢复评分。
- Terminal无在途，已把旧maxseq4服务725545替换为新726129/ACD1-32/36h/TP2/maxseq8，仍80:28082；新模型加载中，健康后直接全量16solver/CPU0至63。旧服务已释放；新job固定release白名单和常驻release配置同步。短暂部署8张baseline卡，稳定仍6张，不触碰其他会话SFT。
- 统一只读最终汇总PID2380282/scope apex-baseline-final-collector-20261016，CPU86/256MiB，每30秒读各owner摘要，输出80 artifacts/results/base_baseline_final_20261016/{summary.json,report.md}，四项完整有效才complete。固定2500/240/51/445；TB5乘89仅齐全才报mean与sample SD(ddof1)，不把四种指标平均，不把缺失或infra填0。


## 2026-10-16：按用户要求改为异步滚动并发（16:34 CST）

- 用户明确要求异步并行、不要一批一批执行。HLE生成和SWE/TB解题已是FIRST_COMPLETED有界滚动队列；HLE Judge原来确有整批future屏障，已在旧2条API自然结束、账本reserved归零后切独立rolling源，PID2446501，每完成一条即补一条，collect独立每30秒，不取消或重复在途请求。
- SWE现44/51有效、5resolved、0invalid，剩余7个生成全部已在途（17最后1加历史6）；不存在新一批待开始任务。Go评分修复按真实workspace预取原声明版本，原test.sh执行；Navidrome候选未声明新import属于有效模型0，不偷偷补go.mod。SWE还会分别提供模型消费完成和CPU消费完成标记。
- Terminal新8叶将历史39个已核infra未完成项与其余未准入项交错放入同一滚动队列，消除先396后历史的屏障。旧7只做一次STOP_ADMISSION自然交接，保留所有在途。已有完整或正常预算结束的答卷独立并行复评分，不再等生成队列整组结束。
- 5个旧curl/uvx缺失伪0已按原逐条轨迹恢复评分可观察状态后执行真实原生pytest，无新模型或更好答案搜索。root的DNA-insert与DB-WAL为原1800s到时未写要求文件，分别执行1和7项测试后有效0；backend另外3项执行2/2/1项测试后有效0。原错误评分、原超时、原始轨迹及缓存阻塞尝试全部保留，未声称完整文件系统byte-identical。
- 官方uv0.9.5原install.sh和Linux release tar.gz已缓存，评分阶段按精确URL提供原bytes，测试源码未改。原生APT、公网安装和隐藏HTTP600s问题仅修评分环境；测试未执行不能当有效0。
- 计划复用SWE自然结束后的相同TP2/maxseq8服务725705/28084作为TB第二路，保留已有两卡而非再次加载模型。尚未启用，需SWE全CPU消费者及本轮grader永久完成标记、CPU64至119无scope占用、两个endpoint健康后自动创建runtime8/ENABLE_SECOND_REPLICA；一个共享CPU池16槽再追加14，合计最多30solver/CPU0至119，题内endpoint固定，两路各15。
- 轻量HLE Judge已无中断迁到CPU124至125，汇总126，离线cache127；必要SWE后续复评分只占120至123。GPU释放配置已将725705暂交TB full445条件，避免SWE模型一结束就提前释放即将复用的服务。若第二路无足够allocation余量，启用器不准入并记录原因。
- 16:33四项统一快照：HLE1136/2500有效、0Judge异常；ASI240/240完整1.57098841%；SWE44/51有效且5resolved；TB13/445有效，41项基础设施未评分单列。四项未全齐，主总状态仍complete=false；未完成项不填0。
- 16:38最终CPU分工更新：TB解题扩容后0至119，TB保存状态复评分120至123，必要SWE后续复评分124单槽，HLE Judge125（仍2条HTTP并发），汇总126，cache和一次启用守卫127；均不打断在途生成。第二副本守卫PID2517615已常驻，7个旧grader已全部有效收敛并给永久CPU完成marker，继续等SWE永久CPU完成marker。新B任务还需逐次检查距离725705到期不少于35分钟。


### 16:53 CST：异步评分收尾与重建审计

- old7最后的评分依赖下载独立处理，只有solver已结束、final-task-state已保存的实例才允许中断评分安装并从原现场补评分；模型和原答案不重跑。旧APT无进展下载及uv官方安装等待保留真实失败日志，不伪造工具成功或把未执行测试的结果填0。
- archive复评分无论reward0还是1，都需要逐项恢复充分性review，确认官方checker所依赖的文件、环境、服务状态未被fresh SIF回滚改变；无法证明则保持infra-invalid。当前modernize/openssl/password三项已完成同标准review，后续观察器统一要求review。
- SWE已全部结束模型生成；50/51评分有效时最后Flipt处于不参与最终成绩的初评，后续仅对冻结patch做正式native fresh replay。Element原patch的评分启动参数错误已在独立CPU124叶以--instance-token=value修复，有效0，未生成新答案。新私有bootstrap及两段原评分attempt均保留。
