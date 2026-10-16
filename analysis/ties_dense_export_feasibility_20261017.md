# Dense TIES完整模型导出可行性

**执行更正**：以下元数据调研之后，728007已完成完整导出及310/735/1045/26验收，[实际收据](source_snapshots/ties_dense_export_728007_20261017.json)含BF16相对更新偏差10.531%。728016已正式运行HLE方法对照，见[接入执行](ties_dense_hle_execution_20261017.md)。以下“尚未导出/提交”描述只针对原调研时点，不代表最新状态。

2026-10-17仅只读Base config、分片index、已有merge报告与文件stat/文件系统余量；**未读权重tensor payload，未实现/提交export，未调用模型或申请GPU。** 结论：可以直接将真实dense TIES更新写入独立完整HF模型，跳过SVD64，使用原TP2架构推理。全部26个权重分片均命中目标，因此最简单可靠的导出需重写约71.90GB完整分片集；不能只硬链接原权重后原地改动。

## 已验证的Base与310目标映射

HPC冻结Base目录：

`/data/user/qinlucao/projects/apex-takehome/artifacts/models/Qwen3.6-35B-A3B/995ad96eacd98c81ed38be0c5b274b04031597b0/`

公共来源为`Qwen/Qwen3.6-35B-A3B`同一revision。完整`config.json`的architecture为`Qwen3_5MoeForConditionalGeneration`、model_type=`qwen3_5_moe`，text dtype声明BF16，40层，hidden2048；视觉config与tokenizer/chat template均存在。需要保留这些多模态配置，不能改成纯文本model class。

`model.safetensors.index.json`包含1045个tensor key、26个分片，metadata.total_size=71,903,645,408 bytes；26文件stat合计**71,903,776,776 bytes（约66.97GiB）**，最大分片3,996,199,712 bytes（约3.72GiB）。差额为safetensors header等开销。此轮没有扫描大文件hash。

已有`artifacts/merges/four-experts-avg-v1-20261017/merge_report.json`的310条module按以下**精确规则**全部唯一命中Base index，0 missing：

```text
base_key = module 去掉开头 "base_model.model." + ".weight"
```

例如`base_model.model.model.language_model.layers.0.linear_attn.in_proj_a`对应`model.language_model.layers.0.linear_attn.in_proj_a.weight`。目标仅语言attention/linear attention/shared_expert投影；735个其他tensor不属于更新集合。Base的routed experts存在如`model.language_model.layers.0.mlp.experts.gate_up_proj`（无`.weight`后缀）及`...experts.down_proj`，视觉存在`model.visual.blocks...`，它们均不能误当目标或改名。索引本身无shape/dtype；当前shape依据已有merge报告，export时仍需逐tensor核真实shape/dtype，不把本次metadata核验称为已读取Base tensor验证。

按分片编号01–26，命中的目标数量依次为：

```text
6,10,15,16,15,9,15,10,13,10,13,10,13,9,15,10,13,10,13,10,13,16,15,16,8,7
```

总计310，**26/26 shard都受影响，未命中的整片数量0**。因此不能靠“只重写少数shard、其余整片hardlink”节约主要权重存储。也不建议把原shard硬链接后另加同名target tensor的新shard：旧shard仍含旧target key，不应依赖不同loader的重复key加载/覆盖顺序。

## 最小导出策略

与merge owner确认的输出为`artifacts/merges/four-experts-ties-dense-v1-20261017/`根目录，无`hf-model/`子目录。初次核查时未完成；随后728007导出完成，本owner已通过实际HPC Python3.6纯metadata guard：310目标、735非目标bitwise、1045个BF16 tensor/26shard、sources_unchanged/reload_verified=true、SVD0，EXPORT_COMPLETE passed。方法固定rho0.2/majority total/ones/λ1，不根据HLE结果改变。

1. 只加载四份既定专家LoRA因子及metadata，固定Base revision与310-key映射。每个真实专家更新为`Δi=2BiAi`，scale只计一次；调用已核实的PEFT0.20 `utils.ties`，跳过任何SVD/低秩回投影。
2. 按原index逐个分片处理。每次只在CPU打开当前分片的原tensor；对命中的matrix计算`W_new = cast_original_dtype(W_base.float() + TIES(Δ1…Δ4))`。每层临时delta和TIES工作数组及时释放；其他735个tensor不参与运算，不做dtype转换，保留其shape/dtype/payload。禁止原地修改Base tensor或源文件。
3. 每个新分片写独立临时文件，再原子rename到新输出目录，保留原26分片名/weight_map可减少重分片逻辑。所有1045个key必须且只能出现一次；index的metadata.total_size按实际导出dtype重新计算，不盲目照抄。仅在全部分片及校验完成后写完成marker/将stage目录rename为最终目录；服务不能读取半成品。
4. tokenizer、merges/vocab、chat template、preprocessor/video processor、generation config及model config从冻结Base保留；这些小文件可以复制，若硬链接则必须当作不可变文件。新增provenance/方法报告记录原revision、4 checkpoint、TIES参数、一次scale规则、310-key集合、逐层写回dtype/舍入误差及完成校验。不要把adapter_config放到完整模型目录当作主model config。
5. 校验所有目标实际shape与报告一致、全key集合/映射/shape/dtype完整、无重复/缺失；保存被更新310个tensor的FP32→原dtype舍入误差。735个非目标tensor应验证值或payload字节保持，不能只凭完整文件大小断言；新的shard header/布局可不同，原shard文件整体字节当然会变化。本轮尚未执行这些tensor级检查。

**不要对原shard创建hardlink后进行任何原地写入**，那会改变冻结Base及现有服务所用源文件。Base与merges当前同一st_dev=50，技术上可创建hardlink，但本模型没有可整片保留的权重shard；copy-on-write/reflink支持未核实，不应把其节省计入容量计划。

310目标共1,409,024,000元素，FP32一份约5.249GiB，四份全展开约21GiB；应按层计算而非全量常驻。单最大8192×2048更新64MiB FP32，四份加stack512MiB，另有TIES prune/sign/topk临时数组。当前最大原shard约3.72GiB，单shard字典加逐层工作区的CPU实现以**32GiB为保守工程起点**，不是实测peak；不需要加载Base35B完整模型对象。取消SVD消除了该项分解成本，但完整约72GB读写仍需实际export计时，不能沿用pilot十秒作为全量用时。

## 存储可写性与余量

HPC `artifacts/merges`的`os.access(W_OK)=true`，与Base同filesystem；`statvfs`当次可用12,434,377,959,227,392 bytes（共享文件系统，约11.04PiB）。这足以容纳约72GB逻辑副本，但**不是用户quota证明**：`quota -s -u qinlucao`退出1且无输出，本轮未获得用户/项目quota值。

建议批准export前再次确认有效quota/可用空间至少约80–100GB，覆盖新26片及一个临时shard/小报告；独立stage目录最后rename无需再复制第二份完整模型。不先删除或挪用冻结Base及既有adapter。若目标310矩阵原dtype实际均BF16，则保留原dtype后的完整模型大小接近原72GB；如果改将这些目标存FP32，会额外增加约2.818GB，具体以实际dtype为准。

## 精确度、容量与TP2推理边界

Dense导出可称**无低秩/SVD截断的TIES**，不能称所有数值都精确无损：FP32 TIES加到Base后写回BF16仍有舍入，服务`dtype=bfloat16`也会转换FP32目标。实际728007报告：effective update相对FP32 delta的偏差为**0.10530998616066448（10.5310%）**；cast error相对composed weight为0.0012621630280071768（0.1262%）。不能用后者较小的weight分母淡化前者对更新的影响。服务admission会保留完整global_rounding字段。与现AVG64 LoRA运行时加法路径也有舍入次序差异；不能用FP32输出文件名掩盖BF16推理转换。

与AVG64的r64比较必须披露：AVG64是310模块/84,664,320个低秩因子参数，dense TIES可产生高于64的实际matrix rank，310目标以1.409B个dense元素存储。虽然四个输入专家完全相同、完整Base架构/总tensor shape不变，但这**不再是同r64参数化容量对照**。不能把去掉约30%–57%已观察SVD残差后的dense方法称为“同容量TIES-r64”；它是保留真实TIES更新的另一种部署表示。也不要由同35B Base参数数目推导方法自由度相同。

完整模型可用现同架构vLLM TP2加载，保留64K/8192、maxseq50、BF16及视觉支持，**不需要LoRA**。但现`serve_direct_experts.py`固定Base目录并总是加`--enable-lora/--lora-modules`，不能只把新路径当成adapter。后续需明确的dense profile/入口：`--model <完整新HF目录>`、独立served alias（例如`apex-ties-dense`），去掉所有LoRA开关/target/rank相关参数。完整模型权重shape不增加，理论权重驻留接近原Base且省去LoRA因子，但实际KV/并发峰值和视觉接入仍须另行授权后最小验收，当前未作承诺或测试。

若与现AVG64直接做HLE对照，需同时披露dense-vs-LoRA运行表示和非r64容量差异；不会改变冻结AVG64或据正式分数选择方法。后续root已授权准备独立普通TP2接入实现，见更新后的[TIES HLE接入准备](ties_hle_comparison_preparation_20261017.md)：可与AVG16并行，不必等旧controls释放，但不复用旧job/route/watcher，保护AVG28095→ASI；正式完整2500含342图/50并发/300秒、同Judge及compact例外保持。该实现及merge owner的export作业分别归各owner，本可行性核查未读tensor或发模型请求；SVD64与TA不启动。
