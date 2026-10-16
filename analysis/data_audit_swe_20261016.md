# 新 FlashNext SWE 数据 CPU 审计与候选划分（2026-10-16）

本轮优先新增 `nvidia/Open-SWE-Traces` 的 Qwen3.8-Flash-Next / mini 分区。新数据固定 revision 为 `1db674173119d71df45c22007af99e214600711a`。旧 Qwen3.6 数据只用于跨教师的同任务族识别，不进入本轮新候选主池。没有调用模型推理/评分API、GPU、容器或轨迹命令；没有读正式 benchmark 题面、答案或测试。

## 固定来源与扫描边界

- [固定数据卡](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[固定分布表](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)、[固定文件大小与 LFS SHA API](https://huggingface.co/api/datasets/nvidia/Open-SWE-Traces/revision/1db674173119d71df45c22007af99e214600711a?blobs=true)。
- 新分区全量为16片、3,653,370,550字节；其中 Scale-SWE 7片、SWE-rebench-v2 9片。每片下载后核对 API 给出的大小和 SHA-256；原始文件和逐文件回执保留80 ignored artifacts。
- 数据卡许可为 CC-BY-4.0，另保留每行原仓库许可与来源记录，不把原仓库 MIT/BSD/Apache 标签当成整个训练集的许可。
- 长度仅抽两片：两个来源的 `train-00000`，每片按固定 seed 20261016（第二片 seed+1）随机128行。每片全量元数据分别2500行。这是两个预先固定分片内的随机样本，**不是16片全库随机样本**；合并统计未加权，不能外推全库长度、质量或分布置信度。
- Qwen tokenizer 固定 Base revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，使用保存的原始 chat template；tokenizer/template SHA 在[长度审计 JSON](source_snapshots/data_audit_swe_20261016.json)。单进程、tokenizer/BLAS/PyArrow线程1，无截断、无 packing、无训练导出。
- 代码只投影 `metadata.category`、`metadata.teacher_model`，不读取 reference/model patch 子字段。正式排除仅读取 `configs/data_exclusions.json` 的11个仓库名。

## 新源与目标 mini 的实证差异

新样本工具声明为 `bash(command: string)`，与本项目目标 mini 的 `BASH_TOOL` 同形。新轨迹经 JSON arguments 解码、去掉 None 字段后可按固定 Qwen 模板渲染。源行的 `resolved=1` 只是发布方成功标签，尚未重放验证。

**多调用是新旧教师的重要差异。** 两片256条样本中224条含一次 assistant 输出多个工具调用；旧 Qwen3.6 624条有界结构样本均为单调用。新源和旧源的 Parquet 消息 schema 都没有 `tool_call_id`。

目标 mini-swe-agent 2.4.6 的 `parse_toolcall_actions` 会按输入顺序接收多个调用；`DefaultAgent.execute_actions` 逐个串行执行；`format_toolcall_observation_messages` 按 `zip(actions, padded_outputs)` 写出调用ID。真实已安装模块的自造双调用 parser/formatter fixture 已通过，未执行 shell。这证明目标支持有序多调用，**不能证明源采集时一定采用同一顺序或同一 agent revision**。候选保留 `multi_call_source_order_unverified` 状态，不因多个调用整批误排除，也不称为已经通过真实回放。

末尾 `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` 提交调用没有后续 tool 结果，是该公开源的终止约定；审计允许单个末尾提交，不补造结果。非终止缺结果、额外 orphan tool、无效工具参数及不平衡 think 单独隔离。

源精确 agent/container revision、cwd、依赖安装、命令超时、观察截断和上下文压缩仍未知。不能用“mini 同名”推断源环境已与目标 SWE-bench Pro 完全相同。候选 val 目前是 teacher-forced 保留池；可执行 dev 仍需恢复独立任务的源环境并接目标协议。

## 清理与长度口径

仅删除 assistant `reasoning_content` 和确定闭合、位于 content 开头的 `<think>…</think>`；其余解释和工具动作保留。自造 fixture 先核：两种思考字段同时删除、结构化 bash 参数与工具状态保留、标记模板与原模板输出完全一致、不平衡 think 隔离。

`raw_total` 为保留公开思考的完整模板序列；`clean_total` 为删除思考后的完整模板序列，包括所有 system/user/tool、工具观察和协议标记。`clean_assistant_body_proxy` 只统计模板中的 assistant body，含工具 XML、空 think wrapper 和结束标记，不含 role header。**它不是 ms-swift 的最终 labels / supervised tokens；完整静态序列也不是切窗、重复历史、padding 后的训练 processed tokens。** 窗口和 loader/mask 未定，最终 P/S 待验。

两片256条样本均有非空 reasoning 字段，未见 content 内显式 think tag。没有因关 `enable_thinking` 就跳过清理。清后完整序列统计如下：

| 两片内样本范围 | n | 中位 | 均值 | P95 | ≤64K |
|---|---:|---:|---:|---:|---:|
| 全部标签 | 256 | 38,844 | 42,942 | 86,901 | 85.55% |
| 发布方成功 | 137 | 35,265 | 40,881 | 86,901 | 86.13% |
| 发布方成功且bug-fix | 64 | 35,265 | 41,801 | **89,018** | **85.94%** |

64条bug-fix成功样本均能匹配本轮9436候选family，其 assistant body代理占完整序列约24.61%，单次body最大3,384。表中不是全库或最终定量子集的长度分布；新源存在超过64K的明显长尾，不能沿用旧源“成功约99%≤64K”的结论。

这支持先核窗口成本，不能直接把完整轨迹尾部截断到8K/32K。64K是评测协议，不自动成为训练窗口；更不能仅据这组样本锁定15M或固定题数。

## 候选划分规则

SWE正式51项的公开 category 统一为 `debugging`，没有已验收的语言频率可用于数字配比。本轮只把源 `metadata.category=bug-fix`、`resolved=1` 且排除正式11仓库的行作为修复候选，按 **来源×公开language×bug-fix** 建立候选层；没有虚构“benchmark语言比例”，也没有从正式题目内容推断类别。

同一 `lower(owner/repo) + NUL + instance_id` 计算 family SHA-256。使用共享 `candidate_selection.py` 的 seed `apex-new-data-v1-20261016`，`family_rank=sha256(seed+NUL+family_key)`；`int(rank[:16],16)%10==0` 保留为 val，其他为 train。同族的所有新旧教师版本继承这一划分。**90/10是候选保留规则，不是 benchmark 类别比例，也不是最终要执行或训练的数量。** 各层按共享 rank 排序，最终配额仍由 root 的覆盖表、窗口与训练吞吐决定。

元数据阶段不读正文、补丁和测试；成功 bug-fix 候选另做消息角色、动作/结果数量、bash参数和 thinking 结构检查。每个 family 只留一条完整代表，优先单调用，再按固定源路径/行号稳定选取。没有生成 ms-swift训练正文。

正式11仓库仅做不区分大小写的 owner/repo 精确排除；fork、改名、语义相同的跨库PR和其他派生关系尚未全部核实，所以候选标 `fork_rename_lineage_status=pending`。不称“fully decontaminated”。旧教师联合结果和全16片候选计数见[候选聚合 JSON](source_snapshots/new_swe_candidate_split_20261016.json)。

## 全16片实测候选池

轻元数据实际读到 **36,577行、36,577个已知family**：Scale-SWE 16,063，SWE-rebench-v2 20,514。全部teacher字段为 Qwen3.8-Flash-Next、thinking=true。任务类别为 bug-fix 18,799、feature-request 10,831、enhancement 4,565、other 2,382；全池发布方成功标签17,807，正式11仓库精确命中0。

bug-fix成功且通过精确仓库排除的9,451行中，15行含除 `command` 以外的额外参数，保守隔离；目标parser有时会忽略额外参数，**这里是主池的规范动作筛选，不宣称这些行被官方parser全部拒绝**。没有删除额外参数后冒充原动作。余下 **9,436独立family** 组成有序候选储备，train 8,568、val 868；不是决定全训8,568题，也不是决定全量执行868题。

| 公开language | 候选family |
|---|---:|
| Python | 6,319 |
| TypeScript | 1,088 |
| Go | 852 |
| JavaScript | 775 |
| PHP | 286 |
| Rust | 54 |
| Java | 46 |
| C | 12 |
| C++ | 4 |

其中Scale 4,598、rebench 4,838；1474条为单调用配对可观察，7962条为多调用源顺序待验。全候选的工具观察已经分别分类：Scale的4598条全部 `json_only`，rebench的4838条全部 `xml_only`，没有mixed/unknown，详见下一节。原始候选中的Python占多数，不能默认直接随机取就等于匹配目标语言生态。稳定family hash保留导致C/C++暂未命中val，Rust val仅2条、Java val3条；最终覆盖层和配额应明确处理这些稀少层，不悄悄改同族分区或编造比例。

旧Qwen3.6已下39片共95,291行、39,540个family；新全池中 **34,274/36,577** 个family已在旧池，修复候选中 **8,824/9,436** 个也已在旧池。新教师并不意味着新任务；`family_split_index.jsonl` 固定同族保留，旧teacher若以后作为备选也必须继承该分区。当前旧数据只用于这个join。

## JSON / XML观察差异与有界桥接证据

目标官方 `mini_toolcall.yaml` 的观察模板是JSON：短输出为 `returncode/output`，长输出为 `returncode/output_head/output_tail/elided_chars/warning`，可附 `exception_info`。80实际安装mini的 formatter对每个 action/output 渲染这个配置模板，并保留tool call ID；不能把其类默认XML字符串当成本实验目标配置。

新源两个来源的格式不同：全9436候选中，**Scale 4598条全部JSON观察，rebench 4838条全部XML观察**。两片256样本包含14,619个tool结果：Scale的6596个都是JSON（其中146个head/tail），rebench的8023个均为XML returncode包装（7898个完整output、125个head/tail、27个异常前缀）。未观察到Python repr、纯文本或损坏/截断JSON。这是实际逐条类型分类，未贴工具正文。

在上述 **8023个有界XML观察** 上，审计只做内存中的字段提取与roundtrip：

- 7898个短输出提取后，使用已安装mini `config/benchmarks/swebench.yaml` 的XML模板重渲染，**7898/7898逐字相同**。
- 125个head/tail提取可见的5000字符首尾和elided数量，使用只暴露这些片段与原长度的对象重渲染，**125/125逐字相同**；没有补造不可见的中间输出。
- 再用目标官方JSON观察模板内存渲染，8023/8023保留相同的returncode、短output或head/tail/elided、exception字段；未改存储的源消息、候选正文或评测配置。模板文件SHA保存在长度审计JSON。

这说明样本中的XML观察与已安装mini swebench配置存在精确格式证据，**可设计保留可见状态字段的schema bridge**。仍不能称全库已无损转换：这里只检查两个分片的256条轨迹，原始XML多行warning改为目标JSON warning会改变提示字面和协议包装；长输出原本已删去的中间内容也无法恢复。实际选入的数据应逐条通过相同roundtrip后再考虑转换，并用独立任务验证多调用结果关联和行为。本轮没有做批量桥接，也没有因为XML外形不同把新rebench整批排除；其候选仍明确为协议待验。

## 回执与复核

80项目根为 `/data/caoqinlu/projects/apex-takehome`，Python为 `/data/caoqinlu/envs/datamind-sft/bin/python`。下载沿用 `scripts/download_data.py:download`，只传固定新分区文件清单，进程代理为 `http://127.0.0.1:38080`，并发2；CDN数据采用既有校验下载方式，不改系统代理。

```bash
cd /data/caoqinlu/projects/apex-takehome
/data/caoqinlu/envs/datamind-sft/bin/python scripts/audit_new_swe_cpu.py --per-shard 128
/data/caoqinlu/envs/datamind-sft/bin/python scripts/select_new_swe_candidates.py
```

- `artifacts/data/audits/new_swe_20261016/download_receipts_all16.json`：逐文件大小、上游及本地SHA、固定revision与来源。
- `artifacts/data/audits/new_swe_20261016/{summary.json,metadata_rows.jsonl,sample_numeric_rows.jsonl,quarantined_rows.jsonl}`：两片长度/结构审计、行级任务ID和数值。
- `artifacts/data/candidates/new_swe_20261016/{summary.json,ranked_candidates.jsonl,family_split_index.jsonl,metadata_rows.jsonl,quarantined_rows.jsonl}`：全新池轻元数据、候选rank和跨teacher family保留。原题/动作正文未导出到这些候选清单。

Git只保存聚合JSON与本说明，不保存原始数据、行级任务ID或训练正文。
