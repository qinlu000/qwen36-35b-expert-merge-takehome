# 学术专家 LoRA SFT 实际运行（2026-10-16）

正式作业 **725704已COMPLETED/0:0**，ACD1-55，单张 H100 /12CPU /128G。14:22:41→15:06:15，总耗时43分34秒；500 train完成1epoch、63/63 optimizer steps，平均train_loss **0.41485302**，峰显存 **70.9238GiB**。

最终adapter：`/data/user/qinlucao/projects/apex-takehome/artifacts/runs/hle-sft-r16-725704/training/checkpoint-63/adapter_model.safetensors`，约81MiB。

| checkpoint | 100条独立val loss | val token_acc |
|---|---:|---:|
| 16 | 2.62409234 | 0.69100785 |
| 32 | 2.97443628 | 0.68497284 |
| 48 | 3.10861635 | 0.68376584 |
| 63 | 3.15466952 | 0.68195534 |

**验证交叉熵持续变差，不能把训练成功称作HLE效果提升。** Native best_model_checkpoint指向16；另有硬链接保留目录 `artifacts/runs/hle-sft-r16-725704/retained-checkpoint-16`，避免任何保留策略丢失早期候选。没有本次Base独立val指标或正式HLE准确率，后续比较应优先保留这个事实。

实际原生结果 `analysis/source_snapshots/hle_sft_725704_result_20261016.json`；HPC完整numeric日志 `artifacts/runs/hle-sft-r16-725704/training/logging.jsonl`。按用户效率优先，未额外重载完整Base、未加自写callback或重复hash/preflight。

## 配方与数据

- 固定Base `Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`；固定ms-swift `a01a3ae004e0b1071814a3d357666184211ed178`（4.7.0.dev0）。
- 独立新版学术500 train /100 val；实际Swift完整train243,140 tokens、监督165,244，max1531，val max582。此前CPU编码与目标检查已通过，按用户效率优先指令不再重复执行。
- r16 /alpha32 /dropout0.05，语言full-attention、linear-attention五投影、shared MLP三投影；视觉、router、routed experts、embedding/head/norm冻结。native实际21.1661M可训练参数。
- BF16 /SDPA /grouped_mm /ZeRO3 /gradient checkpointing（non-reentrant）。2K，microbatch1×world1×GA8=global8，1epoch约63步；LR1e-4 /cosine /warmup0.03 /AdamW默认weight_decay0.1，seed20261016。
- 无packing/padding_free；非思考模板，`default+ignore_empty_think`屏蔽空think标签；save/eval每16步、保留2checkpoint、save_only_model。

入口：`sbatch scripts/train_hle_sft.slurm 1`。正式流程直接调用native Swift，无自写callback、synthetic两步、Base重载、重复hash或全量preflight。若发生实际OOM再按已授权调整2GPU/GA4；当前单卡已真实反向成功。

## 运行时与已修阻塞

独立HPC环境 `artifacts/envs/sft`；Torch2.11.0+cu130 /Transformers5.15.1 /PEFT0.20 /DeepSpeed0.19.6 /FLA0.5.2。安装入口 `setup_sft_runtime.sh`，核心约束 `configs/envs/sft_constraints.txt`，完整freeze `requirements-sft-runtime.lock`。未修改donor或推理服务环境。

1. 724277：Swift本地JSONL显式使用ModelScope缓存，原HF_HOME不足，尝试写只读管理员目录失败。显式MODELSCOPE_CACHE、HF_DATASETS_CACHE等落到作业本地/tmp后，CPU红绿和native数据加载通过。
2. 725511：自写诊断callback缺少Swift的(args,trainer)构造接口，未反向。接口修复后按用户速度优先要求完全去掉该诊断callback；尚pending四卡725568已仅取消自身，不动其它作业。
3. 725630：单卡首个forward通过，backward被FLA的Hopper/Triton3.6已知错误正确性保护终止，global_step0、无checkpoint、未OOM。独立SFT环境已将编译器替换为FLA要求的Triton3.7.1；未绕过保护，725704已真实反向成功。Torch2.11发行metadata仍钉Triton3.6，这项编译器偏离已如实记录在安装脚本；decord发行包还存在已知ABI标签警告，实际import通过。

旧失败日志均保留各job原输出；没有将前置加载或分配GPU称训练成功，没有额外benchmark评测或API消耗。
