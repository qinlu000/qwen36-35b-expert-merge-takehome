# SFT 进度（2026-10-16）

| 模型 | train / val | H100 | 作业 | 本次查询状态 |
|---|---:|---:|---:|---|
| 学术推理专家 | 500 / 100 | 1 | 725704 | 完成，63步，43分34秒 |
| 仓库修复专家 | 448 / 87 | 2 | 725982 | RUNNING；尚未确认首个optimizer step |
| 交互执行专家 | 456 / 62 | 2 | 725987 | RUNNING；尚未确认首个optimizer step |
| 同数据Mixed对照 | 1404 / 249 | 2 | 725984 | PENDING(Resources)，已解除依赖，可并行 |

此前四卡排期较晚，已取消仅本项目尚未启动的旧申请，改同节点双卡。global batch保持8，GA从2改4；所有新训练仍从同一Base开始、r16/alpha32/dropout0.05、LR1e-4、1epoch、非思考模式。新三组使用64K完整序列、显式delete超长，不截断工具历史，group_by_length=true。HLE原实跑为2K。AdamW weight_decay显式0.1，与已完成HLE的实际默认一致；共享配置原写0的记录已纠正，无需重训HLE。

SWE完整序列筛选保留448/500训练和87/100验证，约15.68M训练token。执行专家为Terminal374/42加全部SAB82/20：保留完整教师历史，按既有长度表优先原episode、同任务替代、同类别train备用，独立task-val99不变；SAB不以任务环境/依赖/CPU/GPU筛选。Terminal训练部分约18.73M完整token。Mixed准确拼接三个最终专家分区各一次，无额外采样或重复，约176 optimizer steps。

数据均位于HPC项目`artifacts/data/candidates/`：`night_hle_20261016/swift_ready`、`new_swe_20261016/night_v2/swift_ready64k`、`execution_sft_20261016`、`mixed_sft_20261016`。入口为`scripts/run_sft.slurm`和`scripts/run_sft.py`，逐次启动命令落在对应`artifacts/runs/*-sft-r16-JOB/training_command.json`。

HLE最终权重为`artifacts/runs/hle-sft-r16-725704/training/checkpoint-63`，第16步另保留。验证loss从2.624升到3.155，不能声称HLE成绩提升。训练/验证loss源CSV及图已保存到`curves/hle_sft_725704_loss.*`，绘图入口`scripts/plot_sft_loss.py`。新三组保留每个小LoRA checkpoint，后续只用独立dev比较。

当前baseline占8卡、两组专家占4卡，共12；Mixed若分配再加2卡，共14，低于用户16卡上限。没有额外任务环境验收、教师API、重复hash或诊断callback。
