# SWE低LR候选：完整轨迹长度筛选

2026-10-17。本次按用户允许筛掉过长轨迹，使用既有`full_sequence_tokens`元数据，保留完整序列不超过32768 token的训练样本。没有截断消息、动作、观察或最终提交，没有改64K训练上下文与8K输出上限。本次仅本机CPU筛选，没有训练、模型/API调用、远程修改、作业提交或自动化操作。

来源仍为nvidia/Open-SWE-Traces revision `1db674173119d71df45c22007af99e214600711a`，教师Qwen3.8-Flash-Next。原始目录为`artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k`，新目录为`artifacts/data/candidates/swe_low_lr32k_20261017`。输出只创建新目录，不覆盖原数据。

|完整序列阈值|保留条数|完整序列token合计|assistant输出token合计|
|---|---:|---:|---:|
|32768|1027|23,353,670|5,034,955|
|49152|1672|49,306,082|10,631,131|
|65536原集|2000|67,735,326|14,751,457|

32K集合排除973条，保留最大完整序列32754、最大单assistant输出2442 token。保留语言为Python528、JavaScript242、Go233、TypeScript24；来源为swe-rebench-v2 576条、scale-swe451条。过滤会改变样本量和语言/来源比例，因此后续降低LR到2e-5并使用本数据属于联合修复，不能称严格LR单变量对照。

所有长度均沿用原固定HF Qwen chat template的统计，不是本次重新tokenize的Swift实际长度，也不是实际参与loss的监督token数。未用缓存中的token总数替代实际训练加载量。

原2000条train、87条val的工具ID/观察配对与完整最终提交检查通过。新train的messages和manifest均保留原始行bytes及顺序，二次逐行比较1027条全部一致；包含58,743条消息、32,651次bash调用、31,624条工具观察及1027个完整最终提交。仅最终提交没有后续工具观察，符合原格式。`train.row_mapping.jsonl`逐条记录原行号和保留/排除后的行号；排除manifest保留原元数据。

原87条val的messages和manifest原样复制并逐字节比较一致，不对val应用新长度过滤，仅保留历史teacher-forced训练诊断用途，不恢复task-level validation。原7条Swift角色预处理错误的源行中223、279仍被选中；它们未被改写或额外剔除，若原加载行为重现可能进一步减少2条。新run实际加载量与步数须以原生日志为准。

复现：

```sh
python3 scripts/filter_swe_complete_trajectories.py \
  --source artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k \
  --output artifacts/data/candidates/swe_low_lr32k_20261017 \
  --max-tokens 32768
```

[JSON收据](swe_low_lr32k_data_20261017.json)记录原/新路径、大小、数量、分布、token口径及检查结果；没有对大文件计算hash。脚本只负责数据过滤，不触碰训练配置或冻结正式评测。
