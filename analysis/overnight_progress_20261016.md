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
