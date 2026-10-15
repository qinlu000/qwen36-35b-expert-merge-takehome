# Base baseline 持续推进记录

开始：2026-10-16T03:28:30+08:00。用户已授权本会话持续推进正式Base，并每30分钟检查。本文是本会话baseline工作入口；总体数据/费用/其他会话交接见[夜间总记录](overnight_progress_20261016.md)。正式执行以[协议v2](evaluation_protocol.md)与其JSON为准，不以安装成功代替原生验收。

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
