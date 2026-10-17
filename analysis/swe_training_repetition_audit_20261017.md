# SWE训练动作复读与观察对齐审计

**2000条真实导出没有推理中106/162/205次完整同命令复读。** 最大连续run为3，10/2000行出现run≥2，全部run≥5计数为0。三个原始来源代表的可见字段转换一致，未发现观察错复制或assistant错位；这不是对SWE退化原因的完整解释。

## 范围与量化

全量流式读取本机已有训练副本 `artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k/{train,val}.messages.jsonl`，共234.89MB+10.54MB；与80四个导出/manifest文件size匹配，不重做全文件hash、不重编码。训练入口与实际加载数见 [four_experts_v1.json](../configs/train/four_experts_v1.json)、[训练数据报告](training_data_report_20261016.md)。实际Swift删除原7条role配对异常后1993条，也单独统计；不能把导出2000称加载2000。留出87仅SFT诊断集。

|范围|行数|bash动作|最大完整命令连续run|run≥2行数|相邻重复excess/全部动作|
|---|---:|---:|---:|---:|---:|
|完整train导出|2000|88445|3|10|13/88445=0.014698%|
|原生加载保留子集|1993|88056|3|10|13/88056=0.014763%|
|source留出|87|4107|2|1|1/4107=0.024349%|

“连续”指完整bash字符串逐字相等，允许动作间有tool观察；不折叠空白、不只比首个命令。训练24个动作属于长度≥2的run；13为去首个动作后的重复次数，分母不同不能混用。两个最长run分别在train行122、482，均为 `sleep55` 加读取构建/测试日志的等待轮询。10个有重复行的最长run例子均含sleep55/58，不等于推理中百次无等待复读。合成205次同命令能被同一审计函数检出；故max3不是计数器截到3。

## 同前缀、近邻与数据重复

工具ID去除、JSON对象key排序后，完整轨迹重复0；train/val完整轨迹与完整用户消息跨split重合均0。训练仅1组相同完整用户消息：train行798/860，同仓库shellscape/postcss-less、instance98/101，family不同、后续动作不同；不把这个真实prompt重复隐去，也不误称完全相同训练样本。

69,611个训练assistant动作事件中，全历史prefix仅1组重复（2次、不同下一动作），相同完整prefix→同动作重复excess0。以同任务用户消息hash为条件，最近2条消息的context-action重复excess2；最近4条为0。87留出这三种重复均0。2/4条是精确字节可见上下文窗口，**不是语义embedding近重复**；不能据此排除语义相似或训练诱发的其他退化。

保守语法启发式识别的只读动作占48.77%（含最终echo）；逐样本排除最终submit后，仅4/2000行≥80%只读、0行≥90%、0行全只读。未识别命令记unknown，不能反向称其必定写文件。因此没有“大批仅只读样本被标成功”的证据。2000个source resolved标签均1；87留出可从ranked metadata找到87个resolved1。它们是发布方成功标签，**未在本审计执行环境或核原测试成绩**，最终echo也只是终止契约，不能当独立成功证明；本轮同样无证据断言这些标签大面积不可信。

## 清理与角色对齐：全导出结构＋3条源核验

全2087条导出的assistant tool_call→tool_call_id、响应数量/顺序检查无错误，无孤立tool或未回答的非最终call；最后submit无伪造tool响应。此检查不等于Swift role-pair检查：train223/239/279/1256/1462/1530/1972的tool后user纠正反馈已由原native loader删除，保留原数据与报告；未在此修改。

按root收束要求只核3条原parquet：train122（最长run3，SWE-rebench-v2）、train998（Scale-SWE，含多调用assistant）、val1；并非全2000原源重审。固定源revision `1db674173119d71df45c22007af99e214600711a`，3条源file/row/family见 [JSON收据](source_snapshots/swe_training_repetition_audit_20261017.json)。

三条的角色序列、可见assistant内容、全部工具动作及顺序、工具schema、观察returncode/exception/output或head/tail/elided_chars、完整消息序列均一致。只正规化既有清理：移除reasoning/前导think、system/submit wrapper与最终echo契约、缺省null exception_info和展示warning的格式差异；未泛忽略观察内容。最初literal字典hash会因XML→JSON省略null字段而不同，按原converter定义比较可见语义字段后3/3通过；没有修改数据来“修绿”。

143条原tool观察都未发布tool_call_id，故导出ID来自原消息顺序生成。能确认顺序和可见字段保留、生成ID自洽；**无法凭不存在的source ID独立证明原始调用对应关系**。这是来源可审计性边界，不能写成已经全量证明源语义正确。

代码核对：[normalize](../scripts/audit_new_swe_cpu.py)仅清理assistant隐藏reasoning并解析arguments；[convert_observation](../scripts/prepare_new_swe_night.py)对XML短输出及head/tail做可见字段断言；[expand_swe_sft_2k](../scripts/expand_swe_sft_2k.py)保留消息顺序、逐次生成call ID，并仅替换明确wrapper/final command。本轮没有修改这些原脚本。

## 复现与限制

轻量主审计（本机，stdlib；不需要模型/tokenizer）：

```bash
python3 scripts/audit_swe_training_repetition.py
```

原源仅3固定代表（80已有mini-swe环境及离线parquet；不声称fresh安装可一键复现）：

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 taskset -c 10 nice -n 19 artifacts/envs/mini-swe/bin/python scripts/audit_swe_training_repetition.py --raw-source-fingerprints --output artifacts/tmp/swe-training-repetition-audit-20261017/representative-fingerprints.jsonl
```

将该小fingerprint文件拷回本机同路径后：

```bash
python3 scripts/audit_swe_training_repetition.py --compare-fingerprints artifacts/tmp/swe-training-repetition-audit-20261017/representative-fingerprints.jsonl
```

反馈loop已实际检出合成205次重复和错tool ID；真实导出指标见收据。原始全源扫描在root要求收束后只终止本任务自有元数据PID2724423，未影响native/模型；最终只报告3源代表，原dataset从未重写。全程0环境/模型/API/训练/评测调用，无GPU或CPU租约改变。最终结论只排除这里检验的直接数据现象，不把反证延伸成权重、解码器或推理harness无问题。

## 13:02 附加：preserve_thinking CPU反事实的输入前提

按root新授权，仅本机对2000/87原导出逐message做纯stdlib文本扫描，没有parquet读取、模板render、编码或模型调用。train160065条消息（assistant69611）、val7400（assistant3206）；所有消息只有role/content/tool_calls/tool_call_id四种字段。reasoning/reasoning_content/thinking/analysis等隐藏字段存在0、非空0；所有role的content中think开标签/闭标签、完整空壳、非空块及孤立标签全部0。

因此，导出本身没有任何think壳；另一个审计观察到的7个历史空壳来自渲染层，不能归为原数据保存的隐藏推理。在enable_thinking仍False的单样本CPU preserve_thinking=True反事实中，这批导出没有可供重新启用的非空隐藏reasoning。本结论只确认输入前提，不代表反事实渲染/label parity已完成，也不授权模型调用或训练配置变更。

已实际执行并将精确计数追加原JSON的 `hidden_reasoning_field_audit`：

```bash
python3 scripts/audit_swe_training_repetition.py --hidden-field-scan
```
