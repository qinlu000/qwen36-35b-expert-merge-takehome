# SFT训练数据汇报表

截至2026-10-16 20:12（北京时间），按实际Swift日志复核。数据本体、逐条来源和筛选统计保存在独立数据版本目录；已启动run另存实际配置、启动命令和训练日志。本轮仅汇总记录，未改数据或重训。

## 汇报应使用的样本数

| 模型 | 导出train | Swift加载train | Swift加载val | 状态 |
|---|---:|---:|---:|---|
| SWE |2000|**1993**|87|完成249步，最佳checkpoint249 |
| Terminal |2000|待启动后确认|待确认（准备42）|新作业排队 |
| HLE |2000|2000|100|训练中，快照31/250步 |
| ASI |1073|1073|20|完成134步，最佳checkpoint128 |
| Mixed |7073|**7066**|249|训练中，快照6/883步 |

“加载”是原生预处理后的Dataset长度，不是导出行数，也不是逐个optimizer batch的样本曝光计数。表中val为SFT验证loss数据，不是四项正式benchmark任务数量；Terminal另有原99题独立任务val。

**SWE的7条差额必须披露。**源轨迹在tool观察后以user角色插入工具调用格式纠正反馈，Swift将连续query角色配对到response槽，触发`response_role: "user"`并删除整条。不是超长删除、空回答或截断。Mixed含同7条输入，也被同样过滤，因此实际并集仍是HLE2000＋SWE1993＋Terminal2000＋ASI1073＝7066。保留了原始2000/7073文件，没有为凑整数重复训练。

七条SWE输入行（1-based）：223、239、279、1256、1462、1530、1972。instance、trajectory、family、原分片/行号和日志位置见[原生加载证据](source_snapshots/sft_actual_loaded_rows_20261016.json)。原生warning没有行ID；本轮按保留输入的角色模式与行对齐manifest定位，七条模式与七次原生错误一致，方法明确记录。

## 训练内容与教师

| 专家 | 数据组成与监督内容 |
|---|---|
| SWE | Open-SWE的Qwen3.8-Flash-Next成功修复，逐条保留生成模式；实际保留SWE-rebench-v2 **1224**＋Scale-SWE **769**，946仓库；Python952/Go517/JS477/TS47 |
| Terminal | Horizon1107（发布者声明DeepSeek-V4-Pro-0813）＋Pivot893（GLM-5.1原名332/官方FP8名561），共1303来源任务键；完整公开历史至完成动作，缺未发布确认尾部如实记录 |
| HLE | Math-v4 High817＋此前已接受High722＋Science V4 final201＋筛后跨学科final98＋参考短答案162；八类配额保持，未知effort不标High |
| ASI | SAB82完整人工参考程序＋DS-1000人工代码976＋SciCode人工主解15；991辅助多为函数/库补全，不称1073完整科研执行轨迹 |
| Mixed | 同四份专家分区各一次，源顺序和行范围可追溯；实际过滤与SWE一致 |

## Token口径

| 数据 | 导出完整序列token | 实际保留样本的原模板token |
|---|---:|---:|
| SWE |67,735,326|67,446,810 |
| Terminal |71,660,040|待新run加载确认 |
| HLE |1,125,593|1,125,593 |
| ASI |594,275|594,275 |
| Mixed |141,115,234|140,826,718 |

这里按固定原始Qwen chat template对清理后的完整序列计数，包含prompt、工具观察及可见回答；不是原生Swift精确label token、padding后计算量或optimizer累计消耗。SWE的7条对应288,516个完整序列token，从已有manifest求和扣除，未重新编码。隐藏reasoning/think清理与可见解释/Terminus analysis/plan保留规则已有记录；训练配置为64K、单回复数据上限8K、非思考、r16/alpha32、global8、一epoch。

## 文件与来源映射

以下相对路径同时位于80根`/data/caoqinlu/projects/apex-takehome`与HPC根`/data/user/qinlucao/projects/apex-takehome`下。大JSONL保存在数据目录，不为每个run重复复制；run配置保存实际引用路径。

| 数据目录（均在artifacts/data/candidates/下） | 关键记录 |
|---|---|
| new_swe_20261016/expanded_2k/swift_ready64k | train/val.messages.jsonl、train/val.manifest.jsonl、summary.json |
| terminal_sft_2k_20261016 | train/val.messages.jsonl、provenance.jsonl（train2000＋val42）、summary.json |
| hle_existing_2k_20261016/swift_ready | train/val.messages.jsonl、train/val.provenance.jsonl、val.tasks.jsonl、summary.json |
| asi_sft_expanded_20261016 | train/val.messages.jsonl、train.provenance.jsonl、auxiliary.provenance.jsonl、val.tasks.jsonl、summary.json |
| mixed_existing_hle2k_20261016 | train/val.messages.jsonl、summary.json，后者按顺序指向四份源；逐条出处沿源分区查 |

逐条记录含来源/版本或分片行号、任务/轨迹ID、家族、教师及可用模式、类别、长度、许可、筛选/质量依据；字段因来源而异，缺失信息不补造。Mixed原始行1–2000为HLE，2001–4000为SWE，4001–6000为Terminal，6001–7073为ASI。

四个已启动run均保存`training_config.json`、`training_command.json`、`training/args.json`、`training/logging.jsonl`；完成的SWE/ASI另有`summary.json`和checkpoint状态。run绝对路径、实际超参数和原生日志行号见[运行证据](source_snapshots/sft_actual_loaded_rows_20261016.json)。Terminal排队中只有提交回执与数据manifest，不冒称已有训练日志。

可直接取数的附件：[CSV汇总](training_data_report_20261016.csv)、[完整数据清单](source_snapshots/training_data_inventory_20261016.json)。source summary是准备时快照，其中旧`training_started:false`不作为当前状态；当前运行状态以原生日志证据为准。

未保存每步batch的源样本ID轨迹；完成作业的临时编码cache已随容器清理。当前可通过保留的JSONL、行对齐来源清单、预处理配置与原生日志追溯数据，不能描述成已导出每个batch的精确token/label。SFT验证loss不作正式benchmark成绩。
