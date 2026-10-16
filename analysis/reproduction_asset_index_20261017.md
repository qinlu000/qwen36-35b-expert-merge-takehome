# 复现资产索引（2026-10-17）

本索引只读核查仓库文件、80/HPC目录存在性、少量stat和既有manifest/revision；未执行模型、容器、评测、API调用、发布或大权重哈希扫描。公开可取性依据既有来源/发布验收，不是本轮重新联网承诺。这里只指出取用位置，不打包数据、密钥、参考答案或隐藏测试。

位置约定：**R80**=`/data/caoqinlu/projects/apex-takehome`（10.123.4.80）；**RHPC**=`/data/user/qinlucao/projects/apex-takehome`（hpc3）；下文`artifacts/...`按所在主机根展开。工作站checkout只包含Git跟踪的代码/配置/分析材料，不能据此推定ignored artifacts随clone存在。训练/服务的绝对路径、Slurm账户和模块路径需在新站点显式适配。

状态：**公开**=有固定公共repo/package/model来源（权限要求另列）；**可重建**=由固定源与既有脚本派生，但先决输入必须齐；**离线原件**=目前只在80/HPC留存、没有本项目公开下载入口。三者可同时适用：例如SIF可从公开OCI重建，但本次实际SIF仍是离线原件。

## 1. 基座、五个公开adapter与合版证据

基座公开ID为[Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0)，冻结revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。两端均有`artifacts/models/Qwen3.6-35B-A3B/<revision>/`；完整下载身份见该目录`download_receipts.json`与仓库[model_sources.json](../model_sources.json)。下载入口[download_base.py](../scripts/download_base.py)，不仅需26个权重分片，也需同revision的tokenizer、chat template、processor/config/index；不能只取adapter或改文本模型架构。

五个adapter已公开、匿名完整六文件读回；本轮只引用已验收immutable commit，不重新请求HF：

| Public HF仓库 | 冻结commit | 容量 |
| --- | --- | --- |
| [csminion/apex-qwen36-swe](https://huggingface.co/csminion/apex-qwen36-swe) | `cf6f5bd1a9f6ee13a9e760640dd509b7b2d80c65` | r16 / alpha32 |
| [csminion/apex-qwen36-terminal](https://huggingface.co/csminion/apex-qwen36-terminal) | `79110026fe20fc7c64a8afc8abcedd94a676c37e` | r16 / alpha32 |
| [csminion/apex-qwen36-hle](https://huggingface.co/csminion/apex-qwen36-hle) | `026d926ae6ff639b7cdd540863b6c527467f1a36` | r16 / alpha32 |
| [csminion/apex-qwen36-asi](https://huggingface.co/csminion/apex-qwen36-asi) | `abe468e5531abe8a51fd3b3a110f29159464d31c` | r16 / alpha32 |
| [csminion/apex-qwen36-avg64](https://huggingface.co/csminion/apex-qwen36-avg64) | `53fbd83b8c6d56d9b24dfccbe58789063f7ca853` | r64 / alpha64 |

证据：[模型索引](../models/README.md)、[release_manifest.json](../models/release_manifest.json)、[匿名发布收据](source_snapshots/hf_publication_20261017.json)。每仓仅README/config/safetensors/LICENSE/NOTICE/Apache全文，原训练正文和base shards不在其中。加载顺序为冻结base/processor → PEFT adapter；实际FP32存储与BF16服务cast见各model card。

RHPC训练源分别为`artifacts/runs/{swe2k-sft-r16-726335,terminal-retry-sft-r16-726665,hle-existing2k-sft-r16-726664,asi-expanded-sft-r16-726336}/training/checkpoint-{249,250,250,128}`。AVG64在两端`artifacts/merges/four-experts-avg-v1-20261017/avg-r64/`，同级`merge_report.json`、`serialization_verification.json`和候选内`merge_manifest.json`保留数学/序列化证据。重建入口[merge_expert_adapters.py](../scripts/merge_expert_adapters.py)、[合版配置](../configs/merge/four_experts_avg_v1.json)，先有四个固定checkpoint再合版。AVG64是scaled delta等权平均的rank64精确拼接，不是因子均值；`avg-svd-r16/`与Mixed883是离线消融，不代替五产物。

## 2. HPC训练与推理运行时

| 资产 | 当前实际固定位置 | 来源/复现边界 |
| --- | --- | --- |
| 实际训练及vLLM OS/CUDA SIF | RHPC之外`/data/user/qinlucao/software/containers/slime-39be6cbb00f9.sif`，18,337,001,472B | 离线原件；已有SHA身份在[base_runtime_container.json](../configs/envs/base_runtime_container.json)。未发现本仓库从公共OCI/Dockerfile重建此精确SIF的完整入口，不能只凭文件名猜来源 |
| donor核心wheelhouse | `/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/trainer_glibc235/` | HPC离线原件，setup依赖此manylinux_2_35/CUDA包源；部分包有公共发行版，但本项目未发布完整donor文件清单/镜像 |
| donor补充wheelhouse | `/data/user/qinlucao/datasets/training_mix_sft_wheelhouse_v1/` | HPC离线原件；不能由一个pip freeze恢复相同wheel/ABI |
| Python与uv | `/data/user/qinlucao/datasets/training_mix_hpc_wheelhouse_v1/python/`；`/data/user/qinlucao/envs/agent-lightning-trainer-cu130-tmix-v1/bin/python`；`/data/user/qinlucao/bin/uv` | 解释器树/原venv路径是现脚本真实依赖，均实存；新站点需提供兼容Python或重建并显式改路径，不能搬失效symlink |
| ms-swift源码 | RHPC `artifacts/source/ms-swift-a01a3ae004e0b1071814a3d357666184211ed178/`与`ms-swift-a01a3ae.tar.gz`（16,875,095B） | [公共固定commit](https://github.com/modelscope/ms-swift/tree/a01a3ae004e0b1071814a3d357666184211ed178)，4.7.0.dev0；源码可重新取，实际archive仅HPC留存 |
| 项目补充wheels | RHPC `artifacts/wheels/sft/`（46个顶层文件，包含包与receipt，不是46个wheel）；`artifacts/wheelhouse/liger_kernel-0.8.2-py3-none-any.whl` | 有各包`*.receipt.json`。其中Triton3.7.1覆盖Torch发行metadata的3.6 pin；Liger0.8.2、FLA0.5.2、DeepSpeed0.19.6、decord等不可漏 |
| 已安装环境与锁 | RHPC `artifacts/envs/{sft,base-inference}/`；`artifacts/preflight/sft-runtime/requirements.freeze.txt`；`artifacts/preflight/base-runtime/` | 可重建派生venv，不保证可直接跨主机搬运。[SFT锁](../scripts/requirements-sft-runtime.lock)、[约束](../configs/envs/sft_constraints.txt)、[推理锁](../scripts/requirements-base-runtime.lock)是身份而不是自带全部二进制 |

上述source/wheels/SIF/Python在HPC已轻读确认；80的`artifacts/source`、`artifacts/wheels`和`artifacts/wheelhouse`不存在。80不是该训练运行时的完整备份。

已有依赖顺序：先取得SIF、原解释器树/uv与两donor wheelhouse → 固定Swift源码及项目补充wheels → [setup_sft_runtime.sh](../scripts/setup_sft_runtime.sh)或[setup_base_runtime.sh](../scripts/setup_base_runtime.sh) → 放入冻结base与最终数据 → [run_sft.py](../scripts/run_sft.py)经[run_sft.slurm](../scripts/run_sft.slurm)。[download_sft_wheels.py](../scripts/download_sft_wheels.py)能按给定spec取公共包并写receipt，但不是完整donor重建器，宽spec再次解析会漂移，且不替代CUDA/Torch特殊发行源。

训练入口还依赖Slurm、H100、站点Apptainer1.4.5与modulefiles。现wrapper绑定节点本地/tmp缓存，并使用`--key=value`以适配站点sandbox检查；ACD1-59的FUSE缺库故障已有记录。先决资产不全时不能声称直接sbatch即可从空环境成功。共享配方以[四专家配置](../configs/train/four_experts_v1.json)及[LoRA recipe](../configs/train/lora_r16_shared_v1.json)为准；旧500条HLE/2K smoke/旧held作业不是本次最终训练。

## 3. 最终训练JSONL与选择材料

四个最终目录在80/HPC均实存，两个train/val文件字节数在本轮stat一致；本轮没有重读正文或重新计算大文件hash。

| 专家 | 两端共同项目相对目录 | 最终导出train/val；主要旁证 |
| --- | --- | --- |
| SWE | `artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k/` | 2000/87；`train.manifest.jsonl`、`val.manifest.jsonl`、`val.excluded_over64k.jsonl`、`summary.json`。原生Swift另删除7条角色配对不合法行，实际1993/87 |
| Terminal | `artifacts/data/candidates/terminal_sft_2k_20261016/` | 2000/42；`provenance.jsonl`、`summary.json`，HPC另有`sync_receipt.json` |
| HLE | `artifacts/data/candidates/hle_existing_2k_20261016/swift_ready/` | 2000/100；`train.provenance.jsonl`、`val.provenance.jsonl`、`val.tasks.jsonl`、`summary.json` |
| ASI | `artifacts/data/candidates/asi_sft_expanded_20261016/` | 1073/20；`train.provenance.jsonl`、`auxiliary.provenance.jsonl`、`excluded.jsonl`、`protected_input_overlap.jsonl`、`val.tasks.jsonl`、`summary.json` |

以上每目录均含`train.messages.jsonl`/`val.messages.jsonl`。Mixed最终目录`artifacts/data/candidates/mixed_existing_hle2k_20261016/`也在80/HPC，7073/249导出、原生7066/249；其summary保留四源顺序。

公开上游ID/revision/许可见[训练数据报告](training_data_report_20261016.md)、[模型NOTICE](../models/notices/)与[模型训练证据快照](source_snapshots/model_card_training_evidence_20261017.json)。最终JSONL、人工allowlist、候选分区与既有teacher接受结果目前是离线派生原件，未随五个adapter分发。可重建依赖顺序为：

1. 固定base tokenizer/template及公开源快照（`data_sources.json`只覆盖一部分来源，不是完整下载器）→保留各候选的题族/分区/排除manifest。
2. SWE：80 `artifacts/data/raw/open_swe/<固定revision>/`＋`new_swe_20261016/{ranked_candidates.jsonl,family_split_index.jsonl,night_v2,...}` → [expand_swe_sft_2k.py](../scripts/expand_swe_sft_2k.py) → 既有adapted长度与contract材料 → `scripts/prepare_swe_sft64k.py`。该最后入口截至本索引仍是工作区未提交原件，需随复现材料补齐，不能从当前Git clone获得。缺原排名/冻结split不能随意重抽2000。
3. Terminal：`new_terminal_horizon_20261016/{traces,environment_metadata.jsonl,proportional_candidates,complete_history_64k_audit}` → [expand_terminal_sft.py](../scripts/expand_terminal_sft.py)的Horizon候选；固定Pivot原parquet `nemotron_terminal_pivot_20261016/raw/`与[download_terminal_pivot.py](../scripts/download_terminal_pivot.py) → [prepare_terminal_pivot_sft.py](../scripts/prepare_terminal_pivot_sft.py)按已记录FP8选择/族排除导出最终2000。没有补造未发布轨迹尾部。
4. HLE：公开Math/Science/MMLU/broad源＋`night_hle_20261016/expanded_2k/{math.ready.jsonl,new_teacher_accepted.jsonl,teacher_reservoir.jsonl}`＋冻结100val → [materialize_hle_existing_math_science.py](../scripts/materialize_hle_existing_math_science.py)、[materialize_hle_existing_broad.py](../scripts/materialize_hle_existing_broad.py)的固定allowlist → [prepare_hle_existing_2k.py](../scripts/prepare_hle_existing_2k.py)。已接受722个High回答、旧候选/字节范围与既有API原回答必须保留；重新调用教师不能保证得到同一训练文件。`finish_hle_2k_and_mixed.py`属于被替换的教师扩量/释放旧held作业流程，不能当最终一键重建命令。
5. ASI：固定SAB任务原件/分族manifest → [prepare_sab_sft.py](../scripts/prepare_sab_sft.py)的82/20；`artifacts/data/raw/scientific_python_aux/{ds1000.jsonl.gz,scicode_problems_dev.jsonl}`＋公开正式输入排除清单 → [expand_asi_scientific_python.py](../scripts/expand_asi_scientific_python.py)。只保留原人类代码，辅助DS-1000/SciCode已被训练使用，不能再作独立同名测试。
6. 上述四份最终文件按[prepare_mixed_sft.py](../scripts/prepare_mixed_sft.py)组合。不得恢复已取消的独立task-val来重新选checkpoint；可复现的是已固定数据与选择。

原候选、teacher原响应/账本保存在80 `artifacts/data/candidates/night_hle_20261016/`及其`expanded_2k/`（例如`teacher_raw_responses.jsonl`、`new_teacher_accepted.jsonl`、teacher ledger），不是公共adapter文件。数据本身按上游许可/访问权限受控取用；本索引不复制其正文。

## 4. 四benchmark固定源、任务与环境

| 项目 | 固定公共身份 | 实际离线位置与入口 |
| --- | --- | --- |
| SWE Pro V2 HARD51 | [scaleapi/SWE-bench_Pro-os@66f92766bba642462d4bbe5479e83f91f9211862](https://github.com/scaleapi/SWE-bench_Pro-os/tree/66f92766bba642462d4bbe5479e83f91f9211862)；HF ScaleAI/SWE-bench_Pro@2d52cb3df914a3fcf80c7f66738b3a88ae37fc50；完整51 ID | 80/HPC `artifacts/benchmarks/swe-bench-pro/`、派生`swe-hard51/`；[ID清单](source_snapshots/protocol/swe_hard_task_ids.json)、`scripts/run_swe_baseline_v2_native.py`/`run_swe_expert_benchmark.py`/`run_swe_merged_benchmark.py` |
| Terminal-Bench2 | [laude-institute/terminal-bench-2@69671fbaac6d67a7ef0dfec016cc38a64ef7a77c](https://github.com/laude-institute/terminal-bench-2/tree/69671fbaac6d67a7ef0dfec016cc38a64ef7a77c)；89任务来自固定Harbor registry | 80/HPC `artifacts/benchmarks/terminal-bench-2/`、派生`terminal-bench-2-registered/`；后者无独立.git，不可把向上找到的项目HEAD误作task revision；[89 ID](source_snapshots/protocol/terminal_task_ids.json)，89×5=445 |
| HLE | [centerforaisafety/hle@22ed3074b1e7b134bcbc09028d0ba320839b0655](https://github.com/centerforaisafety/hle/tree/22ed3074b1e7b134bcbc09028d0ba320839b0655)；cais/hle@5a81a4c7271a2a2a312b9a690f0c2fde837e4c29（需上游访问许可） | 80 `artifacts/benchmarks/hle/source/`与同根`<datasetrev>/test-00000-of-00001.parquet`、setup_manifest/download_receipt；2500含342图，非text-only。入口[setup_hle.py](../scripts/setup_hle.py)、`run_hle_v2.py`/`run_direct_hle_formal.py`；锁`requirements-hle.lock` |
| ASI | [apexin-ai/ASI-Bench@cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc](https://github.com/apexin-ai/ASI-Bench/tree/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc)；公开seed31415@0fa14219cafdbab634d8b3cfbce238a8735a214f | 80 `artifacts/benchmarks/asi/`、`artifacts/asi/{hf_seed31415_agent_inputs,instances_seed31415}/`；60×B1–B4=240。入口[setup_asi.sh](../scripts/setup_asi.sh)、[download_asi_agent_inputs.py](../scripts/download_asi_agent_inputs.py)、`run_asi_baseline_v2.py`/`run_direct_asi_formal.py`；不是seed42/Portal |

共同Harbor源码为两端`artifacts/benchmarks/harbor/`，固定上游[f527f8e447038fd242d08ecfa8aaa8029100da97](https://github.com/harbor-framework/harbor/tree/f527f8e447038fd242d08ecfa8aaa8029100da97)，0.24.0；实际存在本地startup补丁，不能只checkout上游后声称同一后端。源码补丁入口[apply_harbor_startup_patch.sh](../scripts/apply_harbor_startup_patch.sh)及说明[harbor_startup_patch.md](../scripts/harbor_startup_patch.md)，再加各formal runtime冻结副本。

SWE51＋TB89的140个固定linux/amd64 SIF在80/HPC本轮都按路径存在140/140。身份清单为[configs/envs/swe_tb_image_digests.json](../configs/envs/swe_tb_image_digests.json)，实际`artifacts/benchmarks/sif/sha256-<platformdigest>.sif`；已有`_prefetch_progress.json`、`.oci.json`及`artifacts/preflight/swe_tb/image-pulls/`保留历史大小/校验/拉取日志。本轮只stat，没有重扫SIF哈希。它们由公共OCI派生，入口[setup_swe_tb.sh](../scripts/setup_swe_tb.sh)→[prefetch_benchmark_images.py](../scripts/prefetch_benchmark_images.py)的ranged-oci transport→[pull_oci_resumable.py](../scripts/pull_oci_resumable.py)；**复现时沿用已冻结digest，不能重新resolve当前tag再当原镜像**。网络、磁盘、Apptainer/FUSE仍是先决条件。

80 SWE实际执行还依赖`artifacts/cache/{swe-v2-wheels,swe-v2-runtime,swe-score-go}/`、`artifacts/preflight/swe_v2/musl_compat/`以及`artifacts/tools/{python,apptainer-1.4.5,fakeroot-1.25.3,slirp4netns}/`。mini锁在[mini-swe-py312.txt](../configs/envs/mini-swe-py312.txt)；[setup_swe_runtime_v2.py](../scripts/setup_swe_runtime_v2.py)只负责一部分wheel/server/native curl派生；musl的loader/fakeroot/uv/Python wrappers还有实际私有ABI bundle，已存源码摘录`analysis/source_snapshots/swe_musl_compat_source/`，不应遗漏原`musl_compat/{native,shim,prepare.py,result.json}`。Go cache与原公开proxy可达性也要分开，已审计的网络/版本问题见[SWE审计](swe_formal_scoring_audit_20261017.md)，不能把cache齐全等价于所有评分成功。

80 ASI实际task venv在`artifacts/benchmarks/asi/.ai4sci-bench/task-envs/`，45组/60项目的依赖锁来自[configs/asi/task_requirements.json](../configs/asi/task_requirements.json)、`artifacts/preflight/asi/{task_runtime_inventory.json,task_env_summary.json,task_constraints_*.txt}`。重建先setup框架/uv/Python，再[prepare_asi_task_envs.py](../scripts/prepare_asi_task_envs.py)，还需`artifacts/tools/ngspice/`、`artifacts/asi/scoring_tools/bubblewrap-0.8/`、评分ngspice rootfs和80支持user namespace/systemd资源限制；不能拿旧OpenCode smoke替代最终direct_llm执行链。正式ASI scorer冻结代码为`artifacts/asi/scoring_v2_formal_params_20261016/runtime/{scripts,ai4sci_bench}/`，专家/AVG grader复制此runtime，不仅依赖当前Git顶层脚本。对应[score_asi_baseline_v2.py](../scripts/score_asi_baseline_v2.py)及scoring_config保留task rubric/聚合与替代judge口径。

## 5. Terminal470代码快照和多层overlay（主要移交缺口）

80两正式输出各有`artifacts/eval/{terminal250_full445_20261017,avg64_terminal_full445_20261017}/runtime/scripts/`及`runtime/source_inventory.json`。每份inventory记录470个(relative_path,source,sha256)，本轮逐记录确认目标存在、缺失0，只读取既有sha未重算；两份inventory仅acceptance脚本记录有差异，不能说二者逐字完全相同。**runtime/artifacts是指向R80/artifacts的symlink，整目录仍非自包含bundle。**

[prepare_terminal_expert_benchmark.py](../scripts/prepare_terminal_expert_benchmark.py)按低→高顺序复制/覆盖，最终来源胜出数如下（不是各层原始文件总数）：

| 顺序 | 80项目相对代码层 | 最终胜出 |
| ---: | --- | ---: |
|1|`artifacts/runs/base-terminal-724242/runtime2/scripts/`|448，含patched Harbor、Terminus模板、Singularity及baseline netns/limits/rootmap等|
|2|`artifacts/runs/base-terminal-recovery-v2-20261016/runtime3/scripts/`|3，recovery runner/smoke|
|3|同根`runtime7/scripts/`|1，terminal_native_environment.py|
|4|同根`runtime11/scripts/`|10，verifier/apt/curl/evidence、rolling、admission/routing等|
|5|`artifacts/results/base-terminal-independent-repair32-20261016/runtime-v2/scripts/`|5，repair agent/environment/takeover/grader/runner|
|6|R80当前`scripts/{run_terminal_expert_benchmark.py,accept_terminal_expert.py,release_validation_cpus.py}`|3|

五层源目录、runtime11 manifest/seed配置以及两份合成runtime目前仅80实存，本地checkout/HPC均未发现。只给新controller的几个Python文件无法恢复其导入链。复现有两种互斥取法：**A**直接受控提供每个正式输出合成后的470份`runtime/scripts`＋source_inventory，附其manifest/config与task来源索引；**B**保留以上五层完整代码，再用仓库preparer按同一覆盖顺序重建。A不需要重复五层，但现有preparer从空目录仍依赖五层，不能宣称现已提供独立的A型安装器。

还需80 `artifacts/runs/base-terminal-recovery-v2-20261016/runtime11/manifest.json`（89 task/445 entries），其`seed_job_configs`指向`artifacts/results/base-terminal-v2-724242-r2/seed{0..4}.json`（5份实存）及同根`tasks/<task>/`。新输出各自`manifest.json`/`config.json`也须保留。runtime写有R80硬编码，需按同一路径布局或审阅后统一重定位，不可只改外层--project而默认所有内层路径跟随。

代码之外还依赖80 `artifacts/cache/terminal-v2-native/`、`artifacts/tools/terminal_verifier_offline_20261016/`及其`core-uv-cache/`，另有`artifacts/cache/terminal-v2-runtime/`、Harbor venv、原任务树/140 SIF中的TB89。实际终端/录屏/tmux/verifier离线包与rootmap helper不等于Python requirements；这些目录均已确认实存，需保持自己的安装/来源receipt。启动前仍须原systemd/DBus、Apptainer/fakeroot PATH、TMPDIR和CPU真实租约。先重建运行时再做原生验收，不能直接把现控制器命令当空机一键入口。

## 6. 原始训练、作答、patch与评分材料

下列是追溯原件位置；正式队列在继续，存在目录不表示完整评分已完成。canonical选择以[final_results_20261017.json](../configs/eval/final_results_20261017.json)及各owner有效性记录为准，不能从多个历史输出取最高reward。

- **完整训练原件在HPC**：第1节四个run根各有`training_config.json`、`training.log`、`summary.json`、`training/{args.json,logging.jsonl}`；`trainer_state.json`在checkpoint目录，**不在training根**。外层Slurm日志为`artifacts/runs/expert-sft-{726335,726665,726664,726336}.log`；Mixed726666同样保留。80同名run目录虽存在，本轮核查这些完整训练文件均不存在，不能当训练日志镜像。`save_only_model`产物无完整optimizer/scheduler状态，支持重新训练/加载adapter，不保证从中途bitwise续训。导出曲线入口[export_training_histories.py](../scripts/export_training_histories.py)。
- **HPC原生服务日志**：`artifacts/validation/lora-service-727113.log`（SWE服务）、`artifacts/eval/direct-expert-service-{727643,727654}.log`（两Direct服务，merged脚本沿用同输出前缀）及Terminal/merged execution各`.slurm`中output位置；80没有这三个HPC原生log。80的bridge/controller/requests只是另一层证据。
- **Base SWE**：80 `artifacts/eval/base_swe_v2_20261016_clean28/corrected51_summary.json`为owner canonical，clean28目录的source/generation/replay/requests/audit保留；native23的旧源由canonical逐项引用，相关`base_swe_v2_20261016_{full,full_x2,manual_infra1,score_*,budget_replay}`也需保留。不能只交一个corrected数字或误用旧5/51 legacy表。
- **SWE专家/AVG**：80 `artifacts/eval/{swe249_hard51_20261016,avg64_swe_hard51_20261017}/`，含generation/agent/model.patch、完整mini轨迹、requests/raw原始模型响应、fresh replay原生日志/官方输出、audit与summary。专家单项网络修复原件另在`swe249_teleport7744_proxy_repair_20261017/`；旧invalid不被覆盖，是否接canonical仍须统一审计。
- **Base Terminal**：80 `artifacts/results/base-terminal-independent-repair32-20261016/corrected445_summary.json`为owner canonical，逐项accepted_first_valid指向历史trial；该目录trials/logs/runtime/repair状态及其引用的`artifacts/runs/base-terminal-*`、`artifacts/results/base-terminal-*`不能删。修复checkpoint的187行只补状态，不是另一份可择优答案。
- **Terminal专家/AVG**：80 `artifacts/eval/{terminal250_full445_20261017,avg64_terminal_full445_20261017}/`保留独立manifest/config、trials、原生agent/verifier/log/录屏状态、runtime/source_inventory、summary与资源门闩。两模型均445完整目标，目录创建或先完成部分不等于全部有效。
- **Base HLE**：80 `artifacts/runs/hle_judge_v2_20261016/{summary.json,results,requests,responses,inputs,scoring_config.json,...}`；其答案选择来源是`base_hle_v2_724196_infra1/manual_retry_manifest.json`引用的821原始＋1679既有infra1选择。原答案及调度历史在`base_hle_v2_724196/`、`..._infra1/`、`..._seq50/`及被引用的prior_seq20等目录，不得按新分数选择重答。
- **HLE专家/AVG**：目标`artifacts/eval/{hle250_hle2500_20261017,avg64_hle2500_20261017}/`的questions/manual_retry_manifest与`scoring/{results,requests,responses,budget.json,summary.json}`；核查时专家仅预建questions，AVG目录尚未创建，不能将未来路径说成完整实存。准入/控制器在`artifacts/eval/{expert_direct_pipeline_20261017,merged_direct_pipeline_20261017}/`，其中state与实际启动记录才表明后续进展。
- **Base ASI**：80 `artifacts/asi/scoring_v2_formal_params_20261016/`保存`local_score_seed31415.json`、scoring_config、conditions、runtime、judge_calls、restart_events与soil_empty_prediction_repair；原240答案/执行在`artifacts/eval/base_asi_v2_20261016/`及其infra1选择引用，完整输入不包含在公共adapter。
- **ASI专家/AVG**：目标`artifacts/eval/{asi128_asi240_20261017,avg64_asi240_20261017}/`逐项目/条件保留原answer、code/data/program执行与状态，完成后`scoring/`保存native local聚合/调用账本；核查时专家generation目录实存、AVG目录尚未创建。不能用未生成的summary补0。
- **汇总与费用**：80 `artifacts/eval/final_aggregation_20261017/{observations.jsonl,matrix.csv,summary.json,report.md,manual_examples.json}`为派生快照，可由仓库最终汇总入口及固定final_results配置重建；不是原始答案替代品。账本索引为`analysis/source_snapshots/resource_ledger_20261017/`，HLE judge budget、ASI judge_calls和训练teacher ledger分别保留，不能只用汇总估计代替原消费记录。

## 7. 从空环境的实际依赖顺序

这是一条依赖索引，不是本轮执行计划或“一键成功”命令：

1. 取得本Git提交/固定协议、五公开adapter与冻结base；先选定Linux执行主机和具备H100/驱动/Slurm/Apptainer能力的训练主机，建立可用systemd user bus、user namespace、DBus和任务CPU/RAM限额。历史端口/PID/SSH tunnel不是可下载资产，须重新配置。
2. 重建/受控取得第2节OS/Python/wheels/Swift与第5节Terminal合成代码；再装训练与推理venv。只安装pip锁不足以获得原container/ABI/helper二进制。
3. 先取第3节最终JSONL＋provenance可直接复训；若要从原公开数据重导出，必须补齐冻结split、allowlist、token计数和原accepted teacher回答，再按分支顺序导出。不能靠重新生成High回答声称同一训练集。
4. 固定四benchmark源码与140个SIF；HLE数据由有权限者自行取得，ASI public-local输入/独立评分材料按原manager分离。任务环境bootstrap、45组科学依赖、Terminal/SWE离线工具与本地补丁都须先就绪。
5. 按冻结recipe完成四训练并保留native加载/过滤记录 → 选既有249/250/250/128 → AVG64精确合版；或使用已匿名验证的公开adapter直接进入推理，不必为推理重复训练。
6. 按[protocol_v2_unified64k8k.json](../configs/eval/protocol_v2_unified64k8k.json)及实际deployment/每模型config启动服务，确保model alias、tokenizer、vision、64K/8K/非思考与各deadline一致；需要API Judge访问权限时自行安全提供凭据，**本索引不分发密钥**。外部Judge版本/服务与调度历史使“完全逐字重现答案/评分”不获保证。
7. 运行完整固定ID与原native verifier、保存全部attempt和环境失败，待最终有效性审计后才做配对bootstrap/宏平均；SWE未定原因、Base历史调度差异等不能通过资产复制抹去。已取消的独立task-val目录保留作为历史，不恢复为流程依赖。

## 8. 面试方受控取用的最小离线清单（本轮不移交文件）

公开权重/源码由上述immutable ID自行取得；为使现仓库可执行，最少还需明确以下受控资产的取用授权/位置：

1. **训练/推理二进制底座**：HPC精确SIF、两donor wheelhouse＋Python树/uv，项目补充wheels/receipts与Swift源码archive（公共源可重取）；也可由接收方另建兼容底座，但必须披露差异，不能称相同运行时。
2. **Terminal代码overlay**：优先第5节A的两份合成470代码＋source_inventory＋manifest/config/task来源索引；或B的五层代码。只交新controller或一个pip lock不够。这里只列代码位置，不夹带任务数据、参考或隐藏测试。
3. **其他冻结执行/评分代码和离线依赖身份**：patched Harbor/startup层、SWE musl/native bundle与receipt、ASI评分runtime/{scripts,ai4sci_bench}、45组依赖/工具的锁与安装receipt；大cache若不移交，接收方需按同版本公开包重建，缺的二进制来源须单独补齐。
4. **最终四train/val与选择旁证的受控读取**：第3节JSONL/provenance/manifests，HLE原accepted teacher材料用于逐字重导出。许可与语料再分发范围按已有NOTICE/来源报告判断；本轮不打包、不上传，也不把正式参考/隐藏测试混进训练包。
5. **完整证据原件的只读取用**：HPC训练logs/config/checkpoint trainer_state、80正式generation/patch/native评分与选择manifest/费用账本；可先交去敏的现有analysis快照，复核具体任务再授权读取原件。原日志不能在未经去敏/来源检查时整目录变成公开repo文件。
6. **最终运行清单与环境失败判定**：固定final_results配置、各owner source引用、最终完成/排空/有效性receipt。尚在运行或未创建的目录等完成后再固化，不用此索引冒充完成收据。

最重要缺口是：训练底座依赖未公开的HPC SIF/donor目录；Terminal470和五层overlay目前仅80、非自包含；精确重导出依赖离线accepted teacher/选择材料；完整训练日志不在80/Git；部分正式评分和目录尚未完成。五个公开adapter可加载不等于训练、环境、完整实验已可从空机逐字复现。唯一新增tracked文件为本索引，未改现有文件、Git/claud或任何服务。
