# Qwen3.6 多专家训练与参数合版实验

研究问题：在相同基座和一轮监督训练下，按代码修复、终端交互、学术推理、科研编程划分专家，再平均参数更新，能否比 Base 和同数据 Mixed 训练更好地兼顾四项任务？重点观察专精收益、跨域冲突、压缩损失和合版退化。

候选人仓库：[qinlu000/qwen36-35b-expert-merge-takehome](https://github.com/qinlu000/qwen36-35b-expert-merge-takehome)，由[官方模板](https://github.com/apexin-ai/qwen36-35b-takehome)实际创建，当前为 Private。实验代码已推送到默认分支 `master`，模板 `main` 保留来源。本实验依据最初的多专家题面，需求转录见 [EXPERIMENT_REQUIREMENTS.md](EXPERIMENT_REQUIREMENTS.md)；后续线上模板的 SFT→stage2 路线不覆盖该题面。

**当前状态（2026-10-17）：四专家和 Mixed 均已完成真实训练，AVG64/AVG16 已导出并验证，正式评测仍在进行。完整指标、宏平均提升和配对区间尚未齐备，未完成项保持 `null`。五个模型均已 Public 发布，并通过匿名完整下载与原权重字节核对；实际链接、不可变 revision、加载方法见 [models/README.md](models/README.md) 和 [release_manifest.json](models/release_manifest.json)。**

当前队列快照、已完成项、未决问题和后续交付见 [进展文档](analysis/current_status_20261017.md)；[一页阶段报告](output/pdf/progress_report_20261017.pdf)及其[生成说明](analysis/progress_report_20261017.md)已保存，正式评分尚未齐备。

07:27有效结果：完整HLE为Base3.96%、专家6.92%、Mixed5.84%、AVG644.68%、AVG164.04%；TIES-Dense2499/2500有效，余1项缺`correct`仍null。ASI专家240/240有效，公开local原生聚合0.378991%，Base1.570988%；真实退化及配对区间见[最新双视图](analysis/source_snapshots/formal_aggregation_20261017_0727.json)。不按这些正式结果更换冻结主模型。SWE两模型各48/51有效，Terminal仍在跑，四项宏平均尚不可报告。

当前资源为三个普通`acd_u/Nice1000`TP2、共6H100：Terminal专家、AVG64共享SWE/Terminal服务、AVG64 HLE后复用ASI服务。TIES生成和Mixed/AVG16生成均已结束并释放自身GPU，离线端点不重建；AVG64 ASI已自动接续，不需另申请卡。SWE结束释放的12CPU已真实交接，Terminal专家12槽、AVG11槽；后续扩容仍等ASI实际CPU完成标记。[20个真实合版失败案例及三项后续实验](analysis/avg64_failure_cases_20261017.md)已整理；同ID Base也失败，不能称合版独有退化。

## 实验设计与数据

基座为 [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0)，model/tokenizer/processor 固定 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，保留多模态架构。四个专家按监督内容和工具契约划分；它们是四份独立 LoRA，不是修改基座 MoE 内部的 routed experts，也不在推理时路由或投票。

| 模型 | 数据与监督 | 导出 train → 原生加载 train / val | 完成步数 → 固定 checkpoint | 正式评测范围 |
|---|---|---:|---:|---|
| Base | 原始固定基座 | — | — | 四项全量 |
| SWE | Open-SWE 成功修复轨迹 | 2000 → 1993 / 87 | 249 → 249 | SWE HARD-51 |
| Terminal | Horizon1107 + Pivot893 公开终端历史 | 2000 → 2000 / 42 | 250 → 250 | TB89×5 |
| HLE | Math/MMLU-Pro/Science 与清洗后的公开推理、短参考答案 | 2000 → 2000 / 100 | 250 → 250 | HLE2500，含图像 |
| ASI | SAB82 人工程序 + DS-1000补全976 + SciCode主解15 | 1073 → 1073 / 20 | 134 → 128 | ASI60×B1–B4 |
| Mixed | 相同四份训练分区，各一次 | 7073 → 7066 / 249 | 883 → 883 | 同数据一轮训练对照；HLE2500实际任务比较已提交 |
| AVG64 / AVG16 | 四专家参数更新等权合版 / 固定 rank16 压缩 | 无新增训练数据 | 已实际导出 | AVG64四项全量；AVG16仅辅助压缩对照 |

原生加载条数不是逐 batch 曝光计数。SWE的7条角色配对错误被 Swift 整条过滤，Mixed继承同7条过滤；保留原始导出与日志，没有复制样本补数。ASI的991条辅助数据多为函数/库补全，不能称1073条完整科研轨迹。HLE训练与留出集答案格式不同，最低交叉熵不等于最高任务准确率。数据来源、许可、清洗去重、来源家族隔离及已知污染风险见 [数据报告](analysis/training_data_report_20261016.md)、[行级来源清单索引](analysis/source_snapshots/training_data_inventory_20261016.json) 和 [模型来源/NOTICE索引](models/README.md)。部分公开推理数据的问题血缘不完整，不能声称已证明不存在语义污染。

统一训练配方为 BF16 LoRA `r16/alpha32/dropout0.05`、LR1e-4、cosine、warmup0.03、global batch8、1epoch、seed20261016、64K序列、非thinking、ZeRO-3、gradient checkpointing、SDPA与FLCE-only Liger。只训练语言 attention、linear-attention、shared-MLP投影；router、routed experts与视觉部分冻结。详见 [共享配方](configs/train/lora_r16_shared_v1.json) 和 [实际训练矩阵](configs/train/four_experts_v1.json)。

五个完成 run 的 train/val 曲线、CSV和原生JSON见 [训练曲线索引](analysis/training_curves_20261017.md)。HLE250依据取消前已完成的独立100题结果冻结；ASI128曾按原生loss选择，这是历史局限，不能证明其任务最优。当前服务、公开adapter与AVG64已固定使用128，不在运行中换权重。Mixed用完整一轮final883。**Loss只作训练诊断，不作为val判断标准；模型质量以实际任务结果判断。** 独立任务级validation已取消，不再用正式测试选择checkpoint或扫描合版系数。

取消task-val后，AVG64按先验固定；新增249条loss对照在它固定后完成，未用于开发集择优。这与原题“用独立开发集选择最终配方”的过程存在差异，保留披露。

AVG64表示 `Δ = Σ_i 0.25 × (32/16) B_i A_i`，通过因子拼接精确保存平均更新，输出rank64/alpha64；不是分别平均A/B。AVG16对同一更新做薄QR+SVD的rank16近似，全局相对Frobenius截断误差约0.144715。AVG64已在新增loss比较和正式评测前固定为最终模型；容量是单个rank16专家/Mixed的4倍，线性平均可能抵消冲突方向。原理、验证和配方见 [合版记录](analysis/merge_execution_20261017.md)、[固定配置](configs/merge/four_experts_avg_v1.json)。

原题明确列出的合版配置示例是合并系数、层范围、是否保留基座；压缩rank未被点名，不能仅凭AVG64/AVG16宣称合版消融要求已经完成。用户随后要求真正不同的方法，已撤回任务算术改系数的拟议对照；其CPU产物保留为未使用草稿，无模型评测或GPU提交。TIES真实层试跑已完成，但rank64回投影样例误差30%–57%，因此不导出该近似；[TIES-Dense完整模型](analysis/source_snapshots/ties_dense_export_728007_20261017.json)现已导出并完成310目标/735非目标位一致及重载校验，去掉SVD，BF16相对更新偏差10.531%单列。它不再是同r64参数化容量对照；独立普通TP2服务728016已通过text/image协议验收、全2500生成并释放；2499有效，余1项缺correct仍未决，完整方法分差尚不可报告。主AVG64身份、权重及已有答卷保持固定。

相同249条原生SFT留出集、64K上限、相同监督mask的loss-only对照已全部完成：Base **2.105976**、AVG64 **1.357921**、AVG16 **1.379223**、Mixed883 **1.672463**。AVG16与AVG64的差值为0.021302，记录固定压缩/容量消融；没有生成新答案、运行task-val或据此重新选择主模型。Mixed883重复原训练最终val loss的数值完全一致。这里是原生Trainer的teacher-forced loss，不能作为任务准确率或benchmark提升。详见 [结果、图及重画命令](analysis/sft_loss_only_plan_20261017.md)。

实际HLE任务对照已完成Mixed883和固定AVG16的全2500评分，与AVG64、HLE专家和Base同范围比较；原普通接续服务727857已自动释放。AVG64比AVG16高0.64pp，配对95%CI[-0.24,1.481]，尚不能确认稳定收益。HLE-only对照不产生四项宏平均，也不回流选择主模型。TIES仍有1项评分未决，不报告其完整主分或方法差值。见[最新收据](analysis/source_snapshots/formal_aggregation_20261017_0727.json)。

## 评测协议与限制

完整任务 ID、源码/数据 revision、prompt、镜像身份和预算由 [固定协议](configs/eval/protocol_v2_unified64k8k.json) 及 [manifest](analysis/source_snapshots/protocol/) 保留。所有受测模型使用65,536总context、单次最多8,192输出，`enable_thinking=false`、`preserve_thinking=false`；可见解释和Terminus的analysis/plan仍保留。相同任务、原生工具和评分规则不因分数改变。

| Benchmark | 固定版本与完整范围 | 本实验预算与主指标 |
|---|---|---|
| SWE-bench Pro V2 | 官方code `66f92766`、数据 `2d52cb3d`，hard/test全部51项 | mini-swe-agent2.4.6；1800s solver、1CPU/4GiB；官方fresh patch replay resolved% |
| Terminal-Bench2 | 任务 `69671fba`、Harbor `f527f8e4`/0.24.0、Terminus2；89任务×seed0–4 | 1800s、4CPU/8GiB；temperature1/top_p.95/top_k20；五轮成功率mean及sample SD |
| HLE | 数据 `5a81a4c7`、代码 `22ed3074`，test2500题，图像342题 | 无工具、完整图像输入、每题300s；固定2500分母准确率 |
| ASI-Bench | 代码 `cf07cb89`、数据 `0fa14219`；open seed31415，60项目×B1–B4 | native DirectLLM，一次程序生成/执行共1200s、4CPU/8GiB；native局部评分分子/分母聚合 |

Terminal保留全89×5范围，但 **30min/4CPU/8GiB/64K/8K低于原题3h/32CPU/48GB/256K/80K**，尚无面试方例外批准，不能称满足原指定配置。SWE也由所选上游50min缩为30min。HLE/ASI使用披露的DeepSeek替代Judge，保留评分材料与接口记录，不能称原官方Judge成绩；ASI是公开local评测，非protected/Portal认证成绩。历史Base与后来专家/AVG64的服务副本、全局并发和排期存在差异，不能把全部分差归因于权重。实际环境修复、并发和准入证据分别见 [SWE](analysis/swe_expert_benchmark_execution_20261016.md)、[HLE/ASI](analysis/direct_expert_benchmark_execution_20261017.md)、[Terminal及AVG64执行](analysis/merged_execution_deployment_20261017.md)。

四项主分转百分数后严格等权：`macro=(SWE%+HLE%+ASI%+TB%)/4`。任何缺失、无效或owner未完成都会阻止该项主分；不丢样本计算“完整分数”，也不把四个不同专家拼成一个宏平均。已有效判错与评分基础设施invalid分开。采用10000次paired bootstrap、seed20261015、95% percentile CI：SWE按51任务、HLE按2500题、TB按89任务保留五seed、ASI按60项目保留四condition；同ID抽样用于模型差值，宏平均按同一replicate的四项等权差聚合。实现和人工算例见 [统一汇总与统计](analysis/final_aggregation_20261017.md)。

默认汇总保持上述严格原生口径；另可显式生成[审计固定预算视图](analysis/terminal_budget_aggregation_20261017.md)。它沿用Harbor将None映为失败的均值语义，但只接受精确逐结果审查通过的计算超时，保留原native null、原生覆盖及审计来源，未决环境故障继续留空。03:25的Base Terminal为442份原生有效＋3个审计超时，独立预算分**20.224719%**、五seed sample SD **2.635065个百分点**；严格主分仍为空。此规则对专家/AVG64同样适用，不能套用Base的task白名单；两种视图和宏平均分别保存，不混称全445份原生reward。

原统一Base审计曾有5 SWE＋1 HLE＋9 TB判分缺口；其owner已03:29仅用原答案补评分收尾，SWE51/51有效、10正确、19.607843%，HLE2500/2500有效、99正确、**3.96%**，ASI240/240、1.570988%，TB442native另3审计超时派生0仅进独立预算视图，见[补评记录](analysis/base_gap_completion_20261017.md)。三个进入官方测试后耗尽900秒的TB结果仍保留native null，另有逐结果计算超时审计，不能与环境故障混算。SWE专家四个已核审native0另存[独立汇总](analysis/swe249_audited_summary_20261017.md)，未改原队列。专家目标项和AVG64四项正式运行仍未收齐，完整矩阵、宏平均提升及其CI尚未齐备，未声明达到3pp/5pp目标。动态结果以 [显式结果路径清单](configs/eval/final_results_20261017.json) 指向的owner输出及其更新时间为准。

## 在原环境复现

这是依赖已保留资产的实验仓库。大权重、原始训练/评测数据、参考答案、SIF、task cache、完整日志和私有凭据位于被Git忽略的`artifacts/`，不随clone自动取得；仓库中的source snapshots、配置和曲线用于追溯。HPC根为 `/data/user/qinlucao/projects/apex-takehome`，CPU评测机根为 `/data/caoqinlu/projects/apex-takehome`。现有脚本含这些固定路径、账号和CPU租约，移植时必须按实际环境改配置并重验隔离，不能直接承诺fresh portable安装。

[复现资产索引](analysis/reproduction_asset_index_20261017.md)列明公开来源、精确离线位置与重建依赖顺序。完整训练日志和训练二进制底座在HPC；Terminal470代码overlay与完整执行资产主要在80，`runtime/artifacts`仍是symlink。两台机器均不能单独当作整个实验的完整备份，最终还需按索引移交必要离线材料。

训练环境使用Apptainer1.4.5及 `/data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif`，现成Python与离线wheelhouse位于 `/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/`、`training_mix_sft_wheelhouse_v1/`，项目还需`artifacts/wheels/sft`、固定ms-swift源码和Liger wheel。版本锁见 [SFT](scripts/requirements-sft-runtime.lock)、[Base推理](scripts/requirements-base-runtime.lock)、[HLE](scripts/requirements-hle.lock)、[ASI](scripts/requirements-asi.lock)、[CPU合版](configs/merge/cpu_runtime_20261017.freeze.txt)。SFT关键版本为Torch2.11.0+cu130、Transformers5.15.1、PEFT0.20.0；FLA要求的Triton3.7.1覆盖Torch元数据旧pin，不能忽略安装脚本中的兼容处理。

以下是实际CLI入口。训练/生成/评分会消耗资源；复跑需使用新的run/output和独立服务、CPU租约，勿与现有正式队列重复启动。示例使用已存在的原环境与数据，不重新采集数据或生成Base答卷。

```bash
# HPC：准备已有离线资产的项目环境；SWE训练示例（wrapper负责容器/torchrun）
cd /data/user/qinlucao/projects/apex-takehome
bash scripts/setup_sft_runtime.sh
sbatch --job-name=apex-swe-repro --time=16:00:00 scripts/run_sft.slurm \
  --data-dir artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k \
  --name swe-repro --max-length 65536 --world-size 4
```

其余专家和Mixed的数据路径、world size和checkpoint见训练矩阵；2GPU作业还需同步覆盖Slurm `--gres`/CPU/RAM与`--world-size 2`，不能仅改Python参数。数据构建入口包括 [SWE](scripts/expand_swe_sft_2k.py)、[Terminal Horizon](scripts/expand_terminal_sft.py)及[Pivot补充](scripts/prepare_terminal_pivot_sft.py)、[HLE](scripts/prepare_hle_existing_2k.py)、[SAB](scripts/prepare_sab_sft.py)及[ASI扩展](scripts/expand_asi_scientific_python.py)、[Mixed](scripts/prepare_mixed_sft.py)。[数据清单](analysis/training_data_report_20261016.md)列固定来源及行级记录；这些入口依赖保留的前序资产。

```bash
# CPU评测机：源checkpoint已经存在；新副本中修改配置output_root后重建合版
cd /data/caoqinlu/projects/apex-takehome
artifacts/envs/merge-cpu/bin/python3.12 scripts/merge_expert_adapters.py \
  --project "$PWD" --config configs/merge/four_experts_avg_v1.json
artifacts/envs/merge-cpu/bin/python3.12 scripts/merge_expert_adapters.py \
  --verify --project "$PWD" --config configs/merge/four_experts_avg_v1.json

# 不调用模型：从保留的原生训练产物导出曲线数据
python3 scripts/export_training_histories.py --project "$PWD" --output curves/training_20261017/source
# 在已安装matplotlib的绘图环境执行（或将curves/source复制至该环境）
python3 scripts/plot_sft_loss.py \
  --result curves/training_20261017/source/mixed_loss.json \
  --output-prefix curves/training_20261017/mixed --title 'Mixed: one epoch, nonthinking'
```

绘图Python需已有matplotlib；不要求CPU评测机存在HPC的SFT虚拟环境。合版不应在HPC登录节点运行。模型加载与五模型发布后的revision固定方式见模型索引。

四项运行需要现成task cache、native runtime快照、Apptainer/fakeroot工具、用户systemd/DBus及已验收的模型桥。真实启动入口如下；服务与租约配置须先按执行文档准备，不能将这些控制器当成独立安装器：

```bash
# CPU评测机，原用户会话；示例为已有配置的执行入口
artifacts/envs/harbor/bin/python scripts/run_swe_expert_benchmark.py \
  --config configs/eval/swe249_hard51_20261016.json
artifacts/envs/asi-py312/bin/python scripts/run_direct_formal_pipeline.py \
  --project "$PWD" --profile expert
# AVG64的HLE/ASI使用同一pipeline的 --profile merged；SWE使用独立控制器
artifacts/envs/harbor/bin/python scripts/run_swe_merged_benchmark.py \
  --config configs/eval/avg64_swe_hard51_20261017.json
```

Terminal由 [prepare_terminal_expert_benchmark.py](scripts/prepare_terminal_expert_benchmark.py) 的`--project/--config`生成新output的445条manifest和冻结runtime，之后以该output的`runtime/scripts`作为`PYTHONPATH`运行 `run_terminal_expert_benchmark.py --output <output>`；同时需要原会话工具PATH、独立TMPDIR与CPU gate。两模型的可执行配置为 [Terminal专家](configs/eval/terminal250_full445_20261017.json)、[AVG64](configs/eval/avg64_terminal_full445_20261017.json)，完整环境/服务/准入记录见上述执行文档。Base已有答卷与canonical collector不通过这些专家命令重新生成。

```bash
# 只读原owner输出，重新汇总；无需GPU或模型/Judge API
artifacts/envs/asi-py312/bin/python scripts/collect_swe249_audited.py --project "$PWD"
artifacts/envs/asi-py312/bin/python scripts/summarize_experiment.py \
  --project "$PWD" --config configs/eval/final_results_20261017.json \
  --output artifacts/eval/final_aggregation_20261017 \
  --terminal-budget-policy configs/eval/terminal_budget_policy_20261017.json
artifacts/envs/asi-py312/bin/python scripts/check_experiment_aggregation.py
```

可选预算视图位于输出的`audited_terminal_budget/`，原根目录仍为strict；省略最后一个可选参数只产strict。刷新汇总不会重答或修改原生结果。

## 资源、目录与未完成交付

用户后续授权的项目上限为16×H100、每连接组最多4卡，并非持续可用配额。截止为北京时间2026-10-18 14:20，预留12小时后核心实验目标结束点为02:20。四专家/Mixed原生成功run合计46.541425 GPUh只是子集；[资源账本](analysis/resource_ledger_20261017.md) 的05:17快照为已结束216.721389 GPUh、另10张在跑GPU暂计10.406111 GPUh，包含失败、取消、服务等待等allocation开销，没有重复加训练子集。API账目分usage估计、预算上界和失败reservation；学校HPC无已知单价，未换算人民币。人工主动工作时长未计时。显存仅为rank0当前设备的PyTorch peak_reserved，不能冒称跨卡峰值。

代码/配置在`scripts/`、`configs/`；训练图与源数据在`curves/`；研究说明、统计验证和小型执行收据在`analysis/`；模型索引在`models/`。大产物实际使用`artifacts/runs`、`artifacts/eval`、`artifacts/results`、`artifacts/merges`，与模板推荐的`logs/results`布局不同；[结果路径清单](configs/eval/final_results_20261017.json)记录精确映射，不依靠自动挑“最新”或最高奖励结果。

尚未完成：完整正式评分矩阵与宏平均/CI、TIES新方法实际任务对照、一页`report.pdf`、必要离线资产收尾和最终交付。Base固定答卷补评分、[20个真实失败案例与三项后续实验](analysis/avg64_failure_cases_20261017.md)、五模型发布及匿名验收均已有记录。HLE专家和Mixed的2500题现已完整判分，分别6.92%和5.84%，其余队列仍继续；Base历史no-answer/服务差异是比较混杂，不能只归因权重。已有249条loss只作诊断。现有曲线、loss改善、合版导出或控制器启动均不替代完整评测；最终结论将随完整有效原始结果更新。
