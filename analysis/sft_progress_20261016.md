# SFT 进度（2026-10-16，17:45 CST）

用户最新决定：HLE不再生成2000条答案，直接复用已有已清理答案和关闭thinking的训练结果。HLE采用原500 train /100 val与已完成725704；不重训HLE，不把新High生成结果自动混入。以下为当前执行方案，覆盖此前High2k与Mixed7073安排。

| 模型 | train / val | 当前状态 |
|---|---:|---|
| SWE / 仓库修复 | 2000 /87 | 726335，4H100，PENDING(Resources)，尚未训练 |
| Terminal / 终端操作 | 2000 /42 | 726345，4H100，仅依赖ASI726336成功 |
| HLE / 学术推理 | **500 /100** | 725704已完成63步；复用已有权重，无新训练 |
| ASI / 科研编程 | 1073 /20 | 726336，2H100，最新只读快照121/134步，已保存checkpoint112 |
| Mixed对照 | **5573 /249** | 726346，4H100，仅依赖SWE726335成功；新数据已同步HPC |

四个专家彼此独立；ASI为direct_llm一次生成Python。Mixed是相同四份训练分区并集各一次，不计入专家，也不参与合版。

## HLE生成与后续已停止

80生成PID2603822已退出，summary.stop_reason=manual_stop_admission；STOP_ADMISSION已设置，无新增请求。最后809条尝试、722个High答案合格，作为未使用的历史候选保留，未导入当前HLE500或Mixed。原自动后续PID2611502已终止，followup_state.json已记cancelled_by_user_reuse_hle500、released=false。预留HLE2卡726344确认0运行后取消。

High分支最终保守累计69.62712336元，含此前学术账2.62661616元、4次未知返回的潜在上界8.55482496元，以及按峰值价格/8元换算安全系数计算的用量；这是内部保守记账，不是精确账单。原始回答、接受/拒收记录和usage仍保留，未因停止而删除。

## 复用原HLE与Mixed

HLE路径：artifacts/data/candidates/night_hle_20261016/swift_ready，500/100；完整train243140 tokens、最长1531，val最长582。训练enable_thinking=false，messages没有reasoning_content或think标签，2048内部cap没有截断。原teacher provenance为204条现成Math-v4 High加296条DeepSeek非思考生成，不能将500条全部称为教师原始生成都关闭thinking。

已核旧模型checkpoint16、checkpoint63及retained16文件齐全。checkpoint16 val loss2.62409234、checkpoint63为3.15466952，Trainer最佳记录为16；保留两者用于既定dev选择，不将val loss当HLE benchmark成绩。模型根目录artifacts/runs/hle-sft-r16-725704/training/。

Mixed已实际重建到artifacts/data/candidates/mixed_expanded_20261016，来源顺序HLE500→SWE2000→Terminal2000→ASI1073，每条一次；验证100/87/42/20共249，保持原内容。80/HPC实际行数和summary确认5573/249；没有覆盖已运行的训练目录，没有重采样、截断或新增教师。[复用与Mixed记录](hle_reuse_500_mixed_20261016.md)

## 其余数据与训练

SWE新目录new_swe_20261016/expanded_2k/swift_ready64k：原448全保留、val87原样，67,735,326完整tokens/946仓库；Go供给不足的缺额按其他目标语言比例分配，不声称精确benchmark比例。[SWE记录](swe_expand_2k_20261016.md)

Terminal新目录terminal_sft_2k_20261016：Horizon1107＋Pivot893个不同UID，共1303来源任务键、71,660,040完整tokens，最长65507。Pivot来自580个ATCB任务，GLM-5.1原名332/官方FP8原名561；原val42及独立task-val99不变。恢复完整初始历史至末发布完成动作，排除完成后仍有执行动作的候选，不把决策点当完整轨迹。[Terminal记录](terminal_expand_2k_20261016.md)

ASI新目录asi_sft_expanded_20261016：SAB82完整程序＋DS-1000人工976＋SciCode人工15主解，共1073；val20原样。完整train594275tokens/max12295，valmax23056，新增最大回答3110。辅助代码保留原始片段性质，不伪称ASI完整文件任务。[ASI记录](asi_expand_20261016.md)

ASI726336已真实前后向，最新121/134步train loss0.36261481，checkpoint112 val loss0.583276（step16为0.730787），仅为SFT验证损失，不外推benchmark提升。SWE尚排队，实际64K SWE反向未验证。此前SWE726260在ACD1-59容器挂载缺libfuse3、0步退出；wrapper仅排除该实证故障节点，不另起GPU探针。

## 配方、资源与依赖

保持r16/alpha32/dropout.05、global8、LR1e-4、weight_decay.1、一epoch、原loss mask；长序列64K/单回复8K、完整样本不截断。Liger只启用fused-linear CE；原生dict配置与双卡ASI路径已有真实优化步证据。

Terminal726345依赖仅afterok:726336，Mixed726346依赖仅afterok:726335；已移除取消HLE726344的依赖并用scontrol核实。以baseline最多8卡预留，SWE4与ASI2合计最多14；ASI结束后Terminal4接替，SWE结束后Mixed4接替，最多16卡。未操作其他项目或Base评测作业，没有新hash、环境验收或app自动化。

此前强教师来源研究保留于[教师证据](teacher_strength_gate_20261016.md)；本次按用户最新决定复用已有HLE，不继续追加High生成或以此重训。
