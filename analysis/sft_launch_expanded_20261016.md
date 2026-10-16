# 扩量 SWE / ASI 的实际 SFT 启动

2026-10-16。此分支只负责当前原生 SFT wrapper/runner 的最小工程修复，以及 SWE、ASI 两个获授权的正式训练作业；不改 Base 评测、Terminal/Mixed 提交、数据规模、64K/8K、LoRA rank、Git 或 shared claud。

## 已修复的节点问题

SWE 前一作业 `726260` 在 ACD1-59 于 16:40:52 启动后约 3 秒退出，退出码 127；尚未进入 Python、没有 optimizer step。Apptainer 的 `squashfuse_ll` 缺 `libfuse3.so.3`，而 login 节点同 helper 的 ldd 能找到该库，属于已观察到的节点系统库差异。

只在 `scripts/run_sft.slurm` 增加 `#SBATCH --exclude=ACD1-59` 及实际原因注释，`bash -n` 通过，已同步 80 / HPC。未复制系统库、重建环境、启动 GPU 探针或覆盖失败日志。

## 新的正式作业

| 项目 | SWE | ASI |
| --- | --- | --- |
| Slurm job ID | **726335** | **726336** |
| job name | apex-swe2k-sft | apex-asi-expanded-sft |
| run name | swe2k | asi-expanded |
| H100 / world size | 4 / 4 | 2 / 2 |
| CPU / RAM / wall limit | 24 / 256G / 16h | 12 / 180G / 8h |
| data-dir（项目相对路径） | artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k | artifacts/data/candidates/asi_sft_expanded_20261016 |
| train / val rows | 2000 / 87 | 1073 / 20 |
| max length | 65536 | 65536 |
| epochs / global batch | 1 / 8 | 1 / 8 |
| gradient accumulation | 2 | 4 |
| checkpoint / eval steps | 16 / 16 | 16 / 16 |
| LoRA | shared r16 / alpha32 / dropout0.05 | shared r16 / alpha32 / dropout0.05 |

两者都使用原生 Swift Python dict 配置入口与 FLCE-only Liger；此配置 CPU 已通过，但不能据此宣称 GPU 训练、长序列反向或内存已通过。

外部作业日志为 `artifacts/runs/expert-sft-726335.log` / `expert-sft-726336.log`；进入 Python 后的训练日志分别位于 `artifacts/runs/swe2k-sft-r16-726335/training.log` 和 `artifacts/runs/asi-expanded-sft-r16-726336/training.log`。

## 真实状态

提交回执已返回两个 job ID。首个调度快照：SWE **PENDING(Resources)**，ASI **PENDING(Priority)**。

ASI `726336` 已于 **16:56:09** 分配到 **ACD1-13**，容器与 Python 入口启动成功，原生 dict 参数路径实际通过；随后日志明确 `rank:0, local_rank:0, world_size:2`，启动两 worker，并打印固定 Base 路径、ZeRO3 配置、数据参数。运行约 2分52秒时仍处初始化，尚无权重加载完成或 optimizer 首步证据。前次 ACD1-59 的 FUSE 缺库故障未在此节点重现。SWE 仍排资源。

后续实证：ASI 固定权重与 LoRA 加载完成，日志确认 35,128.3480M 总参数、21.1661M 可训练参数（0.0603%），原生 Trainer 总步数134。**已完成 optimizer step1，并继续到3/134**：step1 loss0.96649373、grad_norm0.71721556、learning_rate2e-5；step2 loss0.70910996，step3 loss1.0561142。首步约156秒含初始化编译，后两步各约21秒，Trainer记录 memory42.16GiB。这证明此 ASI 数据上 FLCE-only Liger、原生 dict 入口和 ZeRO3/world2 实际前后向已通过；不等价于64K SWE轨迹反向或完整验证/训练通过。首三步原日志快照为 `analysis/source_snapshots/asi_expanded_sft_726336_firststeps_20261016.jsonl`。SWE `726335` 此时仍 PENDING(Resources)。

后续只按日志记录实际变化，不将“排队/模型初始化”写成“已完成训练”。

本分支收口快照：ASI `726336` 在 ACD1-13 持续 RUNNING，已到 **7/134**，最近 loss0.66132712、grad_norm1.24584759、Trainer memory42.16GiB，无错误。SWE `726335` 仍 **PENDING(Resources)**；Slurm `squeue --start` 此刻估计18:09:45可开始，该时间只是调度器预估，不保证。Root 已接管后续监控及 Terminal/Mixed 依赖，分支不再循环轮询或重提。

资源按 Base 最多 8 卡预留，SWE4＋ASI2 并行最多占到14卡；为 root 后续 HLE2 留余量。未修改其他用户作业或本项目 Base 评测作业。
