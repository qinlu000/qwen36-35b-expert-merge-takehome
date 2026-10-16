# SFT 进度（2026-10-16）

四专家为仓库修复→SWE、终端操作→Terminal、学术推理→HLE、科研编程→ASI。ASI采用direct_llm一次生成完整Python。Mixed是同一四份训练分区并集各一次的单独对照，不计入专家、不参与合版。

| 模型 | train / val | 当前状态 |
|---|---:|---|
| SWE | **2000 / 87** | 新正式作业**726335**，4H100、16h上限；最后读取PENDING(Resources)，尚无优化步 |
| Terminal | **2000 / 42** | **726345**，4卡，依赖ASI726336及HLE726344成功后接替 |
| HLE | 旧500 / 100，新目标2000 / 原100 | 725704完成63步、43分34秒；新主训改用强教师High，旧结果保留 |
| ASI | **1073 / 20** | **726336**，2卡RUNNING，已完成真实optimizer **7/134步**，最近loss0.6613 |
| Mixed | 新计划**7073 / 249**，旧池历史保留 | **726346**，4卡依赖SWE726335及HLE726344成功；新并集就绪后才释放HLE |

旧held SWE726162、旧Mixed726073、旧Terminal726180均在PENDING/0运行时取消，避免旧数据引用或失败依赖。没有取消任何baseline或其他项目作业。新SWE引用artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k/，Mac/80/HPC已实读2000/87；原448训练全保留，val逐字节相同。完整序列67,735,326 tokens，946仓库；最长65,424，最长单回复4,702。Go供给不足，缺额按其他目标语言比例重分配，不声称精确匹配benchmark比例。[SWE详情](swe_expand_2k_20261016.md)

Terminal已完成2000条：Horizon1107全留＋Pivot893个不同UID，共1303个来源任务键、71,660,040完整tokens，最长65,507。Pivot选自580个ATCB任务，教师实际unsuffixed GLM-5.1共332、官方FP8共561，原样记录精度名。新目录artifacts/data/candidates/terminal_sft_2k_20261016/已三端同步，原42轨迹val和99任务val不变。作者过滤post-completion confirmations，因此采用完整初始历史至最后发布完成动作、且之后无执行动作的语义；排除较早失败完成尝试，不将31111决策点当完整轨迹。不截断、复制或新造观察。[Terminal详情](terminal_expand_2k_20261016.md)

## 教师能力与新HLE/ASI数据

用户最新明确：生成轨迹的模型不能比Base弱。官方证据见[教师强度核查](teacher_strength_gate_20261016.md)：GLM-5.1 TB2.0/Terminus2为63.5、Base同harness家族51.5；Qwen3.8-Flash-Next SWE Pro62.5对Base49.5，但scaffold/预算不同；V4-Pro High HLE34.5对Base21.4也非严格同协议证明。优先保留这些有强教师依据的来源，不自动混旧M2/V3.2或Science-v2中的弱教师。

重要修正：此前fresh HLE296条实际thinking.disabled，不能用V4-Pro High分数背书。旧500数据、已完成权重与原100val保持历史原样；新2000主训计划Math817个现成V4-Pro High题＋七类1183个金标题由V4-Pro High重解（包括原296题），hidden reasoning不进入SFT。教师High生成不改变学生训练/正式评测非思考协议。80现用16并发滚动PID2603822；首4真实题均gold匹配并用于新池，旧4路切换时至多4个未返回请求以未知usage/潜在费用上界8.55482496元计账，已落盘53个accepted保留。新输出使用expanded_2k独立目录，不覆盖历史。HLE2卡726344目前held，待HLE完整2000/100和Mixed7073/249导出、同步、计数通过后才release；80已有SSH私钥直连HPC可供一次性后续流程使用，无需本机常驻。

ASI已补DS-1000人工976与SciCode人工15主任务，加SAB82共1073训练；val20字节原样。完整train594275tokens/max12295，valmax23056，新增最大回答3110，全64K/8K内。24条DS（6族）因与SABval原输入13gram重叠保守排除，正式ASI240公开输入无命中。EcoCoder虽为V4-Pro High且train有459个Python样本，部分将真实实验问题改成随机模拟，未直接全混。辅助原始补全不伪称ASI完整文件任务，现成参考SFT不先搭环境。[ASI记录](asi_expand_20261016.md)

## 训练配方与实际限制

保持r16/alpha32/dropout.05、global8、LR1e-4、weight_decay.1、一epoch、原loss mask。长序列64K/单回复8K，完整样本不截断。旧HLE2K cap没有裁剪（原最长1531），新HLE将按实际完整长度选足够cap，不按旧2K筛数据。Liger仅启用fused-linear CE；旧长序列CE/FLA OOM均0步，无checkpoint，尚未证明真实64K batch已能反向。

run_sft.py和swift_sft_from_config.py保留Liger真dict，ASI726336实际完成前后向并到7/134步，最近loss0.66132712、grad_norm1.24585、Trainer memory42.16GiB；这证明当前ASI完整数据上的Liger/ZeRO3双卡路径通过，不能外推到SWE64K反向。SWE726260实际在ACD1-59因Apptainer helper缺libfuse3挂载失败127/0步；wrapper仅排除该实证故障节点并重提726335，没有为此新增GPU探针。HLE旧checkpoint63和16保留，val loss2.624→3.155，不能宣称HLE提升；曲线curves/hle_sft_725704_loss.*。

HLE最新快照为153/1183个新High解答合格，累计保守记账17.8675元（含历史和4个未知返回的潜在上界，不是精确扣款）。生成PID2603822与一次性后续PID2611502均在80存活；后续状态expanded_2k/followup_state.json为waiting_for_high_generation。它在配额满足后自动导出HLE2000/100、构建Mixed7073/249、同步HPC并核数/原val字节，最后仅release726344；失败记状态并保持held，无需本机常驻。入口scripts/finish_hle_2k_and_mixed.py。

项目GPU上限16；按baseline最多8卡预留，SWE/Terminal各4卡。HLE/ASI小组需排在Terminal之前或专家空位，Mixed接替释放的4卡，避免额外并发超额。没有新建自动化、额外环境验收或数据hash。
