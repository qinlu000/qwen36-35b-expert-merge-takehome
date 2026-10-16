# 四专家 AVG 合版执行记录

2026-10-17 已实际导出并验证两份 adapter。最终配方在任何新增 loss-val 或正式 benchmark 之前固定为 **AVG64**；AVG16 只作同一更新的输出 rank 压缩消融。未启动任务级独立验证、judge、生成或 benchmark；既有训练、Base/SWE 服务未修改。

## 输入与固定选择

底座 revision：`995ad96eacd98c81ed38be0c5b274b04031597b0`。四份输入都为普通 LoRA，`r=16, alpha=32, scaling=2`，310 个目标模块、620 个 FP32 A/B 张量；模块配置和键/形状已核对。仅覆盖语言 attention、linear attention、shared expert 投影，不新增 routed experts、router 或视觉目标。

| 专家 | 固定 checkpoint | 权重 |
| --- | --- | --- |
| SWE | `swe2k-sft-r16-726335/training/checkpoint-249` | 0.25 |
| Terminal | `terminal-retry-sft-r16-726665/training/checkpoint-250` | 0.25 |
| ASI | `asi-expanded-sft-r16-726336/training/checkpoint-128` | 0.25 |
| HLE | `hle-existing2k-sft-r16-726664/training/checkpoint-250` | 0.25 |

上述路径均相对 `artifacts/runs/`。HLE250 沿用已完成的独立 proxy100：48 correct；cp16 为43 correct、2 invalid，即使两条 invalid 全算对也仅45。选择已由计数确定，没有追加 judge 或生成。

## 两个产物

每个目标矩阵的真实平均更新为 `M=Σ0.25×2×B_iA_i=0.5ΣB_iA_i`。

- **AVG64（最终）**：`A*=0.5[A1;A2;A3;A4]`、`B*=[B1 B2 B3 B4]`，输出 `r=64, alpha=64, scaling=1`。这是标准拼接表示，没有交叉项，也没有 SVD 截断。
- **AVG16（消融）**：先对上述 B 与 A 转置作薄 QR，再对至多64×64核心作 FP32 SVD，保留前16个奇异值；输出 `r=16, alpha=16, scaling=1`。精确算术下它等于 M 的最优 Frobenius rank≤16近似。它隔离压缩/容量这一变量，不是新的合版算法。

本轮以这个固定 rank 消融替代 TIES，避免 dense trim/sign 及另一次压缩引入多个变量和计算成本；没有搜索权重、rank、density 或 scale。来源与数学推导见 [一手来源核验](merge_primary_sources_20261017.md)，冻结配方见 [配置](../configs/merge/four_experts_avg_v1.json)。

| 项目 | AVG64 | AVG16 |
| --- | ---: | ---: |
| FP32 adapter 参数 | 84,664,320 | 21,166,080 |
| 文件体积（约） | 323 MiB | 81 MiB |
| 全局理想截断相对 Frobenius 误差 | 0 | 0.144715145 |
| 保存因子的 QR 重构相对误差 | 2.934e-7 | 0.144715147 |
| 最大单层 QR 重构相对误差 | 4.610e-7 | 0.192318949 |

全局误差为 `sqrt(Σ层||M−M_hat||²/Σ层||M||²)`，不是逐层误差简单平均。AVG16保留约97.906%的更新平方 Frobenius 范数。AVG64的约3e-7是 FP32 QR 诊断的数值残差；其因子拼接没有秩截断，所有源 A 块乘0.5、B块不变均已逐张量精确核验。两份输出均保持 FP32，没有新增 BF16 量化。AVG64的参数容量为单个 rank16专家/Mixed的4倍，不能把后续差异全部解释为专家分工有效。

## 实际运行与核验

在 `10.123.4.80` 的项目目录运行，`taskset -c 10-13`、Torch4线程，GPU使用0。合版主体耗时8.437秒。专用环境为 Python3.12.13、Torch2.5.1+cpu、safetensors0.6.2；[运行依赖](../configs/merge/cpu_runtime_20261017.freeze.txt)已保存。初次环境创建遗留 Python3.10软链接以及 safetensors 缺失 packaging 的问题已修正，最终执行退出码0。

核验包括：

1. 小矩阵真实 dense Δ AVG 与拼接乘积一致；测试明确拒绝分别平均 A/B 的交叉项错误以及重复应用输出 scaling。
2. 薄 QR 核心的 rank2截断与直接 dense SVD一致，残差与舍弃奇异值范数一致。
3. 两份输出的620个张量重新加载，与生成 FP32 张量逐元素 bitwise 相等。
4. 实际 AVG64 全310模块的源因子块精确对应；每模块取输出维均匀分布的16行，实际读取的 adapter `B*A` 与四源真实 dense Δ 之和核对通过。全局相对误差 `1.6062e-7`，最大单层 `1.8340e-7`。

第4项在本地完成，只修改验证配置中的源文件存放路径；checkpoint内容和算法未改变。未为文件另做全量哈希。完整每层记录在产物的 `merge_report.json`，额外 dense 检查在 `serialization_verification.json`；简要证据见 [执行收据](source_snapshots/merge_export_20261017.json)。

## 位置与复现

HPC产物根目录：`/data/user/qinlucao/projects/apex-takehome/artifacts/merges/four-experts-avg-v1-20261017/`；80镜像根目录为 `/data/caoqinlu/projects/apex-takehome/` 下同一相对路径。本地也保存了两份产物，均被Git忽略。

子目录 `avg-r64/` 与 `avg-svd-r16/` 各含 `adapter_model.safetensors`、`adapter_config.json`、`merge_manifest.json`。使用固定底座加载；AVG64需要服务 `--max-lora-rank 64`，现有max-rank16的独立服务不能直接热载入它。本记录验证导出和代数一致性，未声称已完成 vLLM 加载或 loss-val/任务分数比较。

在80或已分配的计算节点、具备源checkpoint的项目根目录复现：

```bash
taskset -c 10-13 artifacts/envs/merge-cpu/bin/python3.12 scripts/merge_expert_adapters.py \
  --config configs/merge/four_experts_avg_v1.json --project "$PWD"
taskset -c 10-13 artifacts/envs/merge-cpu/bin/python3.12 scripts/merge_expert_adapters.py \
  --verify --config configs/merge/four_experts_avg_v1.json --project "$PWD"
```

上述CPU绑定只适用于本轮80资源分配；重跑前按实际资源安排。不要在HPC登录节点进行合版。独立代数测试可运行 `python scripts/merge_expert_adapters.py --self-test`。如补充已有SFT loss-val，它仅作固定候选诊断，AVG64最终选择不随正式 benchmark 回流改变。
