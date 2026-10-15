# 夜间推进记录：进展、证据与未决问题

开始：2026-10-16 03:20（北京时间）。本文件是本轮统一进展入口，持续更新；机器回执和各工作线技术记录作为附件链接，不以候选数量冒充完成数量。

## 已确认的执行范围

- 用户已授权睡觉期间持续推进；SWE先用新版Qwen3.8-Flash-Next的9436个发布方标成功的修复候选。最终目标每项100个独立val、约500个train；优先按目标任务类型与生态覆盖选择并隔离任务族。
- 训练数据全部使用本轮新版来源。删除此前旧教师原始数据和其可重下载副本；保留来源清单、审计、同族映射、代码、正式benchmark与模型。Terminal/HLE/ASI新版缺口集中记录，不能偷偷回退旧池或用其他类别凑数。
- GPU本题最多16张H100，单组最多4张；只能用现账户已授权资源提高优先级，不改其他项目作业。rank/alpha/targets/训练窗口仍待定，暂不启动正式SFT或GPU反向。
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

1. 正式SFT的rank、alpha、target modules与训练窗口；以实际处理后长度和吞吐证据讨论。
2. Terminal新版若无法补齐成功标签/环境，采用何种质量门槛或补采策略；本夜先核证，不伪造完成。
3. HLE独立gold与缺失学科/图像，ASI多领域环境与验证器的来源缺口。
4. 替代Judge的校准及与官方评分模型差异；冻结答卷/产物可后判，评分失败不重新生成答案。

### LoRA与对比实验：原题复核

用户询问LoRA参数和题目对比要求，已重新逐条读取原始附件。题面独立要求：（1）至少一个可解释训练对照，rank只是举例之一；（2）至少两种合版方法，或合版关键配置消融；（3）Base与最终合版四项全量、专家至少其目标项全量；（4）各专家train/val loss曲线，合版消融有对比指标图。不能用只有Base/专家/合版的基础矩阵代替前两项探究要求。

当前建议保持三个专家＋同数据Mixed共四次SFT；Mixed使用同一基座、LoRA目标/容量、相同窗口与监督mask multiset/出现次数，报告实际步数和GPU小时差异。AVG/TIES作为两种合版候选，在独立dev比较后冻结最终方法，最终模型再四项全量。原题未要求每一个rank或合版消融候选都四项全量；Mixed若只做独立dev对照须明确其证据范围，不冒称正式benchmark提升。

LoRA草案仍非已批准参数：r16/alpha32为保守起点，dropout0.05可作候选；语言侧full＋linear attention及shared MLP，冻结视觉、router及fused routed experts。普通LoRA缩放alpha/r与学习率共同影响更新；目标模块、上下文/激活与精度比只盯rank更重要。实际模块匹配/显存/训练吞吐仍待项目训练栈验收。不新增rank搜索，不因本次问答自动训练。依据：[PEFT LoRA文档](https://huggingface.co/docs/peft/main/en/package_reference/lora)、本地readiness_training精确架构草案。

## 运行账本

API小量调用已启动，按10/20元硬上限逐支累计，最终账待汇总。GPU：724196两卡服务运行中。正式Base完成0。旧数据已删81文件/25,054,619,487B。自动续跑ACTIVE。
