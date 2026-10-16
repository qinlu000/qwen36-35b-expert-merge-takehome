# 夜间推进记录：进展、证据与未决问题

开始：2026-10-16 03:20（北京时间）。本文件是本轮统一进展入口，持续更新；机器回执和各工作线技术记录作为附件链接，不以候选数量冒充完成数量。


## 最新核实状态（2026-10-16 13:25，北京时间）

- **尚无训练成功的专家模型。** 学术500train/100val已冻结并跨机验SHA；Swift CPU真实目标/mask检查通过。四卡724277于04:16实际分配，04:21因datasets缓存目录权限退出，未到反向/正式SFT。当前只修复同配方的启动阻塞，CPU最小重现通过后重提，不追加新实验。
- **HLE Base未完成有效全量评测。** 收到309份完整答卷；512个300s预算超时；1671项在生成请求前的基础设施失败；另8项已发生成后连接中断。原2500记录全部保留、尚未评分，没有因失败剔分母或回流训练。服务724196在11:26达到8h上限。后续需按冻结协议明确基础设施补跑及准入/到期熔断。
- 数据实际：SWE500/100协议迁移候选仍待源环境映射与长窗验收；Terminal427完整teacher train/99task-val（91teacher-val），仍待长窗/可执行dev；ASI已核新版来源但尚无主池训练发布，只有1条通过数值测试的SciCode函数候选，不冒称500/100。
- DeepSeek数据支费用保守上界：学术¥2.62661616 + Terminal¥4.269956544 = **¥6.896572704**。没有用正式答案训练。
- 夜间heartbeat `apex`已按首段交接约定设为PAUSED；其他会话自动任务未修改。新研究/下载已停止，当前保留已授权训练启动修复。以下03:xx和队列预计05:53的段落是历史，不代表当前运行状态。

## 已确认的执行范围

- 用户已授权睡觉期间持续推进；SWE先用新版Qwen3.8-Flash-Next的9436个发布方标成功的修复候选。最终目标每项100个独立val、约500个train；优先按目标任务类型与生态覆盖选择并隔离任务族。
- 训练数据全部使用本轮新版来源。删除此前旧教师原始数据和其可重下载副本；保留来源清单、审计、同族映射、代码、正式benchmark与模型。Terminal/HLE/ASI新版缺口集中记录，不能偷偷回退旧池或用其他类别凑数。
- GPU本题最多16张H100，单组最多4张；只能用现账户已授权资源提高优先级，不改其他项目作业。03:43用户已确认r16/alpha32/dropout0.05及语言侧attention＋sharedMLP，并授权数据验收完成即可正式SFT；先独立训练环境、目标/mask与四卡反向保存诊断，长窗口按实测冻结，不再因旧暂缓记录阻止训练。
- Base评测沿用已冻结64K/8K、非thinking协议；各项原生链验收通过后可按完整固定分母启动。Terminal降配实验与题定设置的偏离继续披露。
- API仅用于必要的小量核验/判分，夜间先采用总额人民币30元的运行上限；不批量重采2000条轨迹。未明确计价的校园API不扩量。
- 夜间首段工作窗口至2026-10-16 11:30；届时形成交接，停止追加新的工作，保留已启动的有效远程作业。截止时间仍为10月18日14:20，最后12小时留作交付。

## 当前看板

| 工作线 | 实际状态 | 下一步 | 未决问题 |
| --- | --- | --- | --- |
| SWE新版 | 500train/100val已划分并清理；提交契约迁移副本已产出 | 独立val环境与原生执行验收 | 源patch准备动作和/testbed映射仍需核，尚未放行训练 |
| Terminal新版 | 新TerminalHorizon：2852轨迹/1535环境、Apache2 | 完整下载、TB16类标注、独立环境构建 | 非逐条成功池；长轨迹与Compose/预构建镜像需适配 |
| HLE学术新版 | 100题8类有gold代理dev已产出；新版Pro教师补缺已启动 | 按配额补train，仅收gold一致新答案 | dev无图像、MCQ比例/难度与HLE偏离，Other细类不足 |
| ASI科学新版 | NatureBench90论文，45论文满足有效性/SOTA筛选 | 继续核来源重合与执行契约 | 大多需GPU，原生ClaudeCode，不能凑100/500 |
| Base工程 | HLE724196图文/精确边界/8并发长输入通过，另会话新开ASI/TB两组TP2 | 完整8K输出与超时行为核验后正式HLE生成 | eager约15token/s，8K需超过HLE300秒，须区分输出cap和时间预算 |
| 旧数据清理 | 已删81文件/25,054,619,487B，新SWE16片及同族映射保留 | 默认下载清单已切新版，历史provenance归档 | 旧raw不可回退，历史审计不能当当前主池 |
| 持续推进 | 本线程heartbeat apex已ACTIVE，每30分钟 | 按检查点推进至11:30交接 | 本地需唤醒、联网、应用运行，SSH桥依赖Mac |

## 时间线

### 03:20—03:25：开始执行与任务拆分

- 已核80/HPC连通；HPC仅见用户其他项目722434，本项目无运行中的GPU服务，不触碰该作业。
- SWE、Terminal、HLE/ASI三线并行执行；root负责统一记录、旧数据清理、调度与Base工程。所有工作先落证据再更新状态。
- 80的旧raw约24GB，SWE新旧分区共享父目录；HPC未见artifacts/data，Mac只有新小样本/元数据。精确删除与实际回收量待下一条回执。

### 03:23—03:36：第一轮实际产物和新发现

- **旧数据已删**：80旧SWE Qwen3.6仅删39片子目录，另删旧Nemotron Terminal/OpenScienceReasoning-2/OpenR1-Math/D3 Qwen3_32B，合计81文件25.05GB。新版SWE16片3,653,370,550B及同族索引保留，正式benchmark/模型未动。卡片/许可/历史来源清单保留为provenance，默认下载清单切新版。[回执](source_snapshots/legacy_data_cleanup_20261016.json)、[历史来源](source_snapshots/retired_data_sources_20261016.json)。Science-v2仍是有界range样本，不称完整下载。
- **SWE固定比例纠正**：固定HARD51官方repo_language实际Python20/Go20/JS10/TS1，与当前GitHub语言代理的JS/TS比例相反。按固定元数据重选：train196/196/98/10，val39/39/20/2。500train共19,973,518清理后完整tokens，448条≤64K；100val共4,083,512，87条≤64K。train346repo/val95repo，仓库/任务族/规范化题面交叉0。100val全部联回固定rebench任务image/base/install，仍不是已执行验收。
- SWE真实mini2.4.6对600条24,916 assistant turns/30,937工具调用parse通过；30,337工具观察可见字段与native formatter一致。但源最终提交均为echo+cat patch，与目标standalone echo指导不同，源system也有对应patch包装；正在准备机械协议迁移副本及终止fixture，不伪造观察/改变repo动作。1条val的assistant后缀12,095tokens超过8K，保留记录，不伪截断。[600条回执](source_snapshots/new_swe_night_selection_20261016.json)
- **Terminal新主池候选**：[TerminalHorizon](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K)为DeepSeek-V4-Pro-0813/Terminus2，有1535个Harbor原环境；metadata已校SHA，前缀26完整轨迹26/26精确join环境。作者按过程有效性筛选，允许未成功但有价值的探索，无逐条reward，不能称全成功。前缀26清后mean83,984/P50 69,979 tokens，仅10/26≤64K；非随机总体估计，训练window未定。部分环境Compose/8CPU16GB5h，项目Singularity后端只接预构建docker_image，不能直接ready。[完整证据与未决项](night_terminal_20261016.md)
- **学术代理dev已落盘**：80 `artifacts/data/candidates/night_hle_20261016/proxy_val_100.jsonl`，8类41/11/10/9/9/9/7/4；41Math-v4公开参考＋59MMLU-Pro金标。排重复、缺图上下文及正式HLE重合。0图像、59MCQ、难度较低，Other以trivia/art/music等为主而候选覆盖不全；只称代理dev。拟补161缺四类train，使用新V4-Pro-0813非thinking，仅收gold一致新解答；首8题5一致/3隔离，按本支20元上限继续。
- **科研新来源仍hold**：NatureBench有90独立论文，达到原论文SOTA且有效只有45个，39 gpu_low/4 gpu_high/2 CPU；原生ClaudeCode，尚不能适配ASI direct_llm。1440行不当1440独立任务；ASI公开输入DOI投影0命中不能证明无来源重合。
- **Base/HLE接线**：724196实际获得2H100/16CPU/128GiB/8h，ACD1-61；HLE薄runner只读id/question/image，固定2500/342、原图/官方system、server精确token计数、300秒共享deadline、逐题保存、只安全连接失败/429重试。离线全量SHA/ID通过。目标Python3.12假HTTP已验证正常8条、断点零额外请求、超限零生成、usage mismatch留失败、HTTP500不重答；Mac系统3.9不支持asyncio.timeout，正式运行使用已装3.12环境。

### 当前进程、资源和恢复点

- 本线程automation `apex`，每30分钟ACTIVE。另一人类已授权会话负责ASI/TB/SWE工程，root只读其记录确认不重复HLE/服务；不向该会话发消息。共用单TP2需保持单benchmark/model块，不同时正式抢服务。
- Slurm724196，日志`HPC:artifacts/preflight/base-service-724196.log`。80合成验收PID2027170，日志`artifacts/preflight/base-night-724196/probe.log`；通过精确57344边界、8并发长输入和完整8192解码后再正式HLE。
- 双SSH桥18061：HPC共享`/tmp/apex-hpc-setup-ctl`仅新增本轮local转发到ACD1-61:18000；80独立`/tmp/apex-night-80-ctl`提供reverse。新HPC连接被现有代理关闭，复用已建立连接成功，没有改代理/其他转发；结束只取消自己的转发，不关共享master。此桥依赖Mac在线。
- API分配：Terminal分类≤10元，学术补缺≤20元；预检上界分别约0.0673元/0.05374元。各支记录返回model/usage，以峰值USD费率×8保守人民币控制预算，非实际汇率或账单。凭据只在项目ignored private内存使用，无值入Git。

### 03:36—03:38：用户核对划分并同意继续

- 用户已获知四项未全部ready，并明确“就这样吧，继续推进行了”。SWE已落盘500train/100val及独立manifest，repo/family/规范化题面交叉均0；600条target-contract副本和可逆转换ledger完成，原轨迹保留。源提交指导/末条命令机械迁移及真实mini终止fixture已通过，仍training_released=false，等待源cwd/patch准备动作/真实环境验证。
- 03:36实核学术：val100、现有新源train339、已接受新Pro解答117，共456候选；教师API ledger150条、进程仍在继续，旧summary仍首批8题，不能用其旧数字冒称最终结算。Science135仍无独立gold，val模态/难度限制不变。最终训练正文、模板和交叉检查待生成终局后物化。
- Terminal已近全1535题标注，但数学/查询/debugging等类别明显不足；不能为了100/500改标签凑数。首环境片186任务中31个Compose，多服务构建仍阻塞可执行val。分类/选集仍在推进。
- ASI新源仍未够独立100val/500train，NatureBench45有效SOTA论文多数需GPU、ClaudeCode工具不同；维持hold，继续核来源，不拿未验样本冒充已可训。
- 共享资源实核：HLE724196＋ASI724241＋Terminal724242合计6H100，2卡一服务，单节点组最多4卡；另会话拥有后两者，不干预。资源调度修订和原生通过仍是正式启动条件。HLE单独服务不被其他benchmark占用。
- HLE真实合成8题（4图像）全部通过，server tokenizer计数与usage相符；精确57344输入+8192 cap成功、57345+8192为400，8个近边界长输入并发均完成。当前强制完整8192解码压测约15token/s，预计超过300秒；这是吞吐/墙钟约束，正式HLE保持300秒，不因此改预算或把cap改小。后续合成完整输出可用独立更长诊断限时，并单独披露。
- 新HLE正式runner用80 `artifacts/runs/base_model_block.lock`及`.owner.json`标明服务块所有权，正式输出逐题可恢复，不自动重答失败；其他独立TP2服务各自调度。

## 待讨论清单

1. rank16/alpha32/dropout0.05和目标模块已获确认；长轨迹训练窗口仍依据显存/吞吐实测冻结。
2. Terminal新版若无法补齐成功标签/环境，采用何种质量门槛或补采策略；本夜先核证，不伪造完成。
3. HLE独立gold与缺失学科/图像，ASI多领域环境与验证器的来源缺口。
4. 替代Judge的校准及与官方评分模型差异；冻结答卷/产物可后判，评分失败不重新生成答案。

### LoRA与对比实验：原题复核

用户询问LoRA参数和题目对比要求，已重新逐条读取原始附件。题面独立要求：（1）至少一个可解释训练对照，rank只是举例之一；（2）至少两种合版方法，或合版关键配置消融；（3）Base与最终合版四项全量、专家至少其目标项全量；（4）各专家train/val loss曲线，合版消融有对比指标图。不能用只有Base/专家/合版的基础矩阵代替前两项探究要求。

当前建议保持三个专家＋同数据Mixed共四次SFT；Mixed使用同一基座、LoRA目标/容量、相同窗口与监督mask multiset/出现次数，报告实际步数和GPU小时差异。AVG/TIES作为两种合版候选，在独立dev比较后冻结最终方法，最终模型再四项全量。原题未要求每一个rank或合版消融候选都四项全量；Mixed若只做独立dev对照须明确其证据范围，不冒称正式benchmark提升。

LoRA草案仍非已批准参数：r16/alpha32为保守起点，dropout0.05可作候选；语言侧full＋linear attention及shared MLP，冻结视觉、router及fused routed experts。普通LoRA缩放alpha/r与学习率共同影响更新；目标模块、上下文/激活与精度比只盯rank更重要。实际模块匹配/显存/训练吞吐仍待项目训练栈验收。不新增rank搜索，不因本次问答自动训练。依据：[PEFT LoRA文档](https://huggingface.co/docs/peft/main/en/package_reference/lora)、本地readiness_training精确架构草案。

## 运行账本

API小量调用已启动，按10/20元硬上限逐支累计，最终账待汇总。GPU：724196两卡服务运行中。正式Base完成0。旧数据已删81文件/25,054,619,487B。自动续跑ACTIVE。

## 03:43之后：正式训练获得授权

- 用户原话：“可以，就这么来吧，然后你弄好数据可以开始训练了。”LoRA r16/alpha32/dropout0.05、语言侧full＋linear attention/sharedMLP目标、三专家＋Mixed和AVG/TIES已获确认；正式SFT与GPU反向现在已授权，不再停留在准备建议。
- 共享超参数文件configs/train/lora_r16_shared_v1.json已保存：BF16、普通LoRA、bias none、无额外full modules、seed20261016、lr1e-4/cosine/warmup.03、1epoch、microbatch1×4卡×累积2=global8、GC、无packing/padding_free；目标匹配和kernel/ZeRO/长度仍须实测。最终每项run加数据hash/实际版本/长度/输出路径，不把共享配置当作已经可跑的完整入口。
- 学术专家优先：原500已物化但Science135质检出现上下文/唯一性问题，保留hold并用同类独立金标任务的新V4-Pro答案替换。新版最终目标204Math＋296新Pro gold匹配；MCQ/难度偏差更大且明确披露。val100保持独立，任务val与val-loss分开。
- SFT子任务已切换实际安装HPC独立artifacts/envs/sft；Torch2.11/Transformers5.15.1/PEFT0.20/Accelerate核心63包离线实装，固定Swift源码a01a3ae已同步；datasets4.8.4/TRL0.29.1/FLA0.5.2/DeepSpeed0.19.6传递依赖安装中。旧用户环境/在线vLLM服务不改。计划单节点4H100诊断，加现三TP2共项目10卡，仍核实际配额。
- Terminal完整2852轨迹已核LFS SHA；第一版结构清理补选恢复427train，val原任务99且有完整teacher91。Terminus JSON的2834字符协议前缀与固定Harbor官方模板逐字相同，保留analysis/plan。它是作者过程筛选而非逐条verifier成功池；环境、类别缺口和长轨迹风险不隐去。80 messages_v3为当前待训练验收副本；后续全量精确长度见最新检查点。
- HLE Base此前强制8K压测在300秒正确读超时，其他原生图文/精确token边界/8并发已过。追加独立900秒合成cap诊断，正式仍300秒；80驱动PID2704236，日志artifacts/runs/base_hle_v2_724196/driver.log，通过后自动启动固定2500题生成。不是为了让8K输出完成而修改正式预算。
- 本线程heartbeat apex已更新为最新训练授权，旧“禁止SFT/rank未定”提示已移除；继续每30分钟按本文件检查点恢复。


## 2026-10-16 03:58：首专家数据就绪及连接恢复

- 学术最终Swift文件500train/100val-loss/100task-val已在Mac、80、HPC同步，现场SHA和行数全部一致；训练SHA66dbd5012b560bc7b2358bdd05001fb0fa95e56f56498685288cb5ed7f649b38。500=204新版Math+296独立MMLU-Pro金标一致的新V4-Pro解答，Science135全部hold；train243140完整模板tokens/max1531，val16562/max582。8粗类比例对齐但无图像、MCQ偏多、难度更低，明确只作代理dev。学术支实际保守费用¥2.58201072，未用正式答案。
- 训练agent已收到HPC冻结数据与正式启动授权；独立SFT运行时安装完成，正在CPU实际Swift目标/mask检查，随后单节点4H100二步训练/保存重载，成功后直接学术一epoch。尚无正式SFT job成功回执，不把准备称训练已开始。
- Terminal messages_v3最终427train/91teacher-val，另99独立task-val；全量完整train33,956,071tokens/P50 67,571/max402,023，仅203/427完整≤64K。32K完整回合分块情景可覆盖所有单位但后窗缺早期状态，未导出训练window；原作者262K全参训练不等于我们短窗LoRA。25个assistant正文超过8K，需记训练/评测输出偏差。
- 共享SSH master约03:53中断，HLE900秒合成诊断收到RemoteProtocolError，尚未启动正式题；失败回执保存。已新建本线独立/tmp/apex-hle-hpc-ctl与/tmp/apex-hle-80-ctl，只恢复本线18061，不改另一会话桥；health200后80新driver PID3040907/probe3040912重跑合成。正式HLE仍300秒/8K，不因网络异常生成重答正式题。
- 新SWE独立dev click镜像13个OCI对象756,498,142层bytes已完整校SHA并传HPC；已提交CPU初始state/cwd/依赖metadata检查，未运行源任务命令/patch/测试。source /testbed映射仍无证明，SWE未训练release。
- 只读实核另一会话SWE724254已RUNNING，现HLE/ASI/Terminal/SWE共8H100；四卡训练后本题12、含其他722434账户13，不超过用户16或账户16。不动其他会话服务/正式结果与用户代理。


### 04:00：训练队列与可自动续接入口

- 四卡训练作业724277已提交（24CPU/256GiB/2小时），当前PENDING(Resources)。同一分配内依次实际CPU目标/mask→2K两步反向→独立进程重载forward→HLE正式500/100一epoch约63步；任何前置失败停止，不把排队当训练已开始。最终mask统一default+ignore_empty_think。
- SWE独立dev环境CPU作业724276已提交debug分区（4CPU/12GiB/25分钟），只检查固定镜像初始commit/cwd/安装元数据与/testbed存在，不运行源轨迹/补丁/测试。镜像转换和初始状态通过也不能证明源采集映射完全相同。


### 2026-10-16T04:01:56+08:00：baseline线程基础设施恢复回执

旧共享SSH失联导致ASI/TB正式首轮基础设施失败；GPU服务未退出。四组TP2现8H100均RUNNING。HLE已由本线程所有者自建18061恢复；baseline侧独立supervisor PID11878管理18071–73，真实断连7.05s重连及3路模型marker通过。ASI 240保存结果中237属infra待显式人工补跑、3原答卷执行失败沿用；TB21属13transport+8取消，0正常完成。旧产物和生产源冻结，修复driver正做准入熔断stub，尚未重启正式。详情与后续launch以analysis/baseline_progress_20261016.md为准；本次不改训练/数据与他项目作业。


## 2026-10-16 13:37：ASI相关任务有界复查完成，专项数据不再扩建

- 用户最新要求“ASI你调研一下，找一下有没有相关的任务；实在没有就不管了”。已对ScienceAgentBench verified、D3任务包、SciCode、DS-1000、DA-Code、DataSciBench、DiscoveryBench等按真实公开任务/参考代码/验证器/当前CPU文件契约核证，不恢复旧模型轨迹。
- 最相关ScienceAgentBench为2026-04-30 verified版，实读102任务来自44论文/30代码仓库；要求完整Python读数据并写CSV/PNG等产物。HF仅公开输入与gold/checker文件名；作者完整zip当前HEAD与≤1KB range GET均302→401，0B，没有取得参考代码/数据。候选87 NetCDF拟合、21 GeoJSON缓冲区比例最接近CPU数值文件任务，依赖/内存仍未验。Scanpy方法族与正式ASI单细胞方向可能同源，保守hold；exact/13gram 0命中不等于完整来源独立。
- DS-1000实际1000题均有reference_code/test，但主要短库函数；DA-Code有500任务和产物验证，未核到逐题完整人工程序；DataSciBench 222提示/519GT不能当519程序；SciCode64主族需新生成并适配文件契约。D3有565任务/239仓库与文件产物验证接口，任务元数据/源码不提供565份可直接取用的gold正文，仍需镜像与新解法核验，未重下旧Qwen轨迹。
- **本轮不追加ASI专项train/dev，不再为500/100强建采集流程；ASI必交正式全量评测保留。** 其它三域训练继续；执行专家若只训Terminal需如实标明，不称专门ASI专家。没有独立ASI dev时不拿正式结果调样本/合版。已保存最相关候选与恢复条件，不声称世界上没有可用科学任务。
- 本轮ASI调研新增付费API/GPU/任务执行/大输入下载均0。ScienceAgentBench只取129KB公开输入Parquet；D3只读源码clone留ignored artifacts。总决策analysis/asi_task_sources_decision_20261016.md，两份一手来源子报告链接在其中。
- 训练另线继续：缓存最小红→绿实际通过，725511四卡曾开始执行，但又在诊断callback构造契约处退出（未反向）；训练agent正修相同配方的callback接口并加CPU复现，未追加新参数实验。不会把GPU分配/前置加载称正式训练成功。


## 2026-10-16：SAB获取与防污染声明澄清

- 按用户效率要求，跳过新整包hash与重复审计。ScienceAgentBench verified完整包已下载并同步80解压，1,769,478,786字节；92号官方gold/checker在既有4CPU/8GiB断网环境一次通过，共0.595秒，无新增API。
- 代码头的勿入训练语料/canary是作者防止SAB测试污染的声明。官方README同时注明多数任务CC BY 4.0、代码MIT，少数沿用上游许可；不能把此提示直接等同统一许可证禁训。此前据此一律排除SAB辅助训练的结论过强，撤回。
- 本题正式评测是ASI等四项，SAB仍可保留辅助数据候选；具体选择需隔离train/dev来源、排除正式ASI重叠并披露。当前SAB仅做参考环境验证，SFT导出0，不把参考运行成功称模型成绩。


## 2026-10-16：SAB全部参考加入SFT数据

- 用户明确“加入训练集”，随后强调“全都训练行了，SFT又不需要环境”。已取消CPU/GPU、依赖、外网、模型训练任务与本地复验门槛，不再把常见科学库相似直接判同题；全部102题完整纳入，无筛除。
- 按30个来源仓库整组隔离为82训练/20验证，seed20261016。Swift JSONL、来源manifest及summary已落地本地/80/HPC：artifacts/data/candidates/scienceagentbench_verified_9c6e96c9/swift_ready/。原始gold/code/canary保留，6题保留原仓库许可来源，不一律标CC BY。
- 科研程序采用ASI direct_llm的完整Python回答格式，加入交互执行专家的数据配方；Mixed使用相同SAB训练分区一次。scripts/prepare_sab_sft.py只需官方metadata+gold，既有运行回执可选；configs/data/scienceagentbench_sft_v1.json记录实际82/20和数据路径。没有新增教师API、hash、逐题运行门槛，也未声称所有样本均本地通过。


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


## 2026-10-16：SFT实际完成与其余三组启动

- 用户询问SFT是否开始，已实查sacct：学术专家725704 COMPLETED/0:0，单H100完成500/100、63步、43分34秒；验证loss后期上升，保留16与63。补齐curves/hle_sft_725704_loss.csv及PNG，未把训练成功称HLE提升。
- 原授权其余SFT已推进：SWE725982双H100 RUNNING(448/87)，执行725987双H100 RUNNING(456/62=Terminal374/42+全SAB82/20)；尚未确认optimizer loss，不以GPU分配冒充实际步数。Mixed725984双卡PENDING(Resources)，同并集1404/249各一次，已解除依赖允许并行；baseline8卡加三组训练最多14卡，未超16。
- 四卡排期较晚故改两卡/GA4，global8与其余LoRA配方不变；新三组完整64K/delete超长/group_by_length，HLE原2K实跑不改。weight_decay统一显式0.1，纠正共享config原0与HLE实跑默认0.1的记录差异。入口scripts/run_sft.py/slurm，Mixed与执行数据脚本/逐源manifest已保存，无重复hash、任务环境验收或教师API。
- 详细快照analysis/sft_progress_20261016.md。SWE由night_swe、执行由night_terminal、Mixed由night_academic_asi继续跟真实原生日志，发现实际错误再修，不重复提交作业。


### 15:40 CST follow-up: real16-solver Terminal resumed; scoring issues retained

- Terminal runtime6 launched15:37:29, PID2052444, endpoint28082, first16admitted/398pending/haltedFalse.7prior valid remain1pass+6fail.24older unscored entries are retained as21cancelled+2failed_attempt+1verifier_incomplete; no answer regenerated. Single verifier errors now remain local to the trial rather than trip the full generation queue. Source scripts/run_terminal_full16.py; native log runner-full16.log and launch-full16.json.
- HLE15:39:217network-repair attempts ended,225admitted/8active;821original retained gives1038/2500ended. Ended counts include failures/timeouts, not only full responses.
- SWE15:39:glibc15terminal/1active/17pending, musl root10terminal/0active/0pending; plus2older normal-budget replays gives27terminal records. The audited25replays contain1official reward1,24reward0, but7need environment review:pytest4,pip1,Go download timeout2.18have no such environment error flag; do not call7unreviewed errors model failures.6old premature cancellations remain incomplete. Original patches are retained; owner continues grader-only repairs/replay, without regenerating answers or extra synthetic tests. New8-sequence service handoff remains in natural drain until the last old trial ends.
- ASI remains239valid/1native-evaluator-invalid/0pending.49missing-import execution errors were audited:37pandas,4sklearn,4scipy,3numpy,1markdown all use packages absent from the official corresponding TaskEnv declarations. All declared packages satisfy the16cached environments checked; no declared dependency missing-install evidence, so no package-addition execution reruns. HKUST route available for future API calls; current ASI formal API count0 and existing completed scores were not moved.


## 2026-10-16：单卡短序列与64K显存边界

- 用户问一张H100能否SFT：学术专家LoRA/2K单卡已实跑完成，35,128.348M总参数、21.1661M可训练(0.0603%)，峰显存70.9238GiB；不能把该结果外推到64K。
- SWE725982与执行725987均在双卡首个64K长batch的原生大词表logits/交叉熵处OOM，0 optimizer step、无checkpoint，旧日志保留。已按既定fallback提交唯一四卡SWE726017与执行726065，完整数据/64K/r16/global8不变，GA改2；baseline8+两专家各4最大16卡。
- Mixed725984在loader因原行附带的不同顶层metadata列CastError失败（0步），不是OOM。正在最小规范化为messages/tools，原消息及工具正文不变、1404/249不变；四卡Mixed需依赖SWE释放再跑，避免超16卡。没有偷偷裁序列或换训练题目。


## 2026-10-16：用户确认序列上限与禁止自行缩减

- 用户接受较小max_length，只要完整样本不超过上限、没有内容被截断；现有学术数据最长1531token可完整放入2K，不因配置数字较小而无意义重训。
- 后续不得自行删减训练数据、截断轨迹、降低64K上下文/8K输出预算或调整rank等有实质影响的内容。显存不足先加卡或做等价内存优化；确需改变实验内容，先说明影响并与用户讨论。已通知三条训练监控线，现有冻结分区保持。


## 2026-10-16：三专家结构与真实开训状态

- 用户询问其他SFT及专家数：仍是三个专家——仓库修复(SWE)、交互执行(Terminal+ASI/SAB)、学术推理(HLE)；另训同并集Mixed对照，不算专家、不参与合版。学术725704已完成63步。
- 实查SWE四卡726017首batch在FLA backward autotune OOM失败，0步；执行四卡726065已RUNNING进入首长batch，尚无optimizer loss。Mixed四卡726073因SWE依赖失败暂DependencyNeverSatisfied，不占卡；更新依赖由academic与SWE单writer协作。
- Mixed已最小规范化顶层messages/tools，原内容与1404/249不变，原生datasets CPU加载通过，修复不涉及删样。当前继续官方等价显存优化，遵守用户不自行缩减约束。


- 后续实际更新：执行四卡726065也在首长batch CE/反向OOM（16:03:18–20），0/57步、无checkpoint。已通知SWE/academic统一查官方fused-linear/chunked CE等价内存路径，停止原配置反复重提；数据、64K/8K、r16均不缩减。


## 2026-10-16：第二专家名称与ASI协议澄清

- 用户指出ASI采用direct_llm，不应统称交互执行。第二专家对外统一称“终端与科研编程专家”：Terminal为Terminus2多轮终端，SAB为单轮完整Python生成、ASI评测仍direct_llm。按终端操作/科研编程能力归组，不意味着harness相同。
- 三专家数量、456/62训练分区、消息正文、内部execution路径、评测协议及合版对象均不变；Mixed仍是对照。更新configs/data/scienceagentbench_sft_v1.json显示名和协议说明，不更改正式推理配置。


## 2026-10-16：四专家拆分与SFT数据量调研

- 四专家已按用户要求拆为SWE448/87、Terminal374/42、HLE500/100、ASI82/20；Mixed仍1404/249，四份来源各一次，按原HLE→SWE→Terminal→SAB次序登记。HLE已完成权重保留，旧合训execution文件保留，不删任何训练内容。矩阵configs/train/four_experts_v1.json，Terminal拆分scripts/split_terminal_sft.py，SAB配置归属改为ASI。
- 用户追问2000条与一般SFT需要多少数据。本轮只研究，未擅自扩量或复制样本。按research技能核原论文/作者卡：LIMA1000、Long Is More1000、SWE-smith500与5016、Tulu约94万；没有统一最低条数，现500/82不能视为已证明足够。详见analysis/sft_data_size_evidence_20261016.md及其一手来源链接。
- 2000条是可讨论的高质量独立任务目标，优先考虑HLE/SWE扩量；Terminal仅该源1535环境，SAB仅102题，需新增来源而不是重复凑数。按当前平均完整长度粗推SWE约70M、Terminal约100M token，加对应Mixed份额约340M；HLE同长度单卡粗推约3小时。64K长序列尚无成功吞吐，不承诺小时数。
- 当前训练栈的Liger dict CLI解析修复由terminal单writer处理；SWE保持hold，其余依赖未满足，不为调研启动新GPU或旧小池重训。保留完整数据/64K/8K/r16，没有以数量调研为由手动缩减。
