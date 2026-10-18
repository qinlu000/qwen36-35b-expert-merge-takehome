# 训练数据与来源

本目录只保存数据说明和入口索引，不重新分发 benchmark 原始题目、答案、参考补丁或完整轨迹。实际大 JSONL、任务缓存和运行产物位于 Git 忽略的本地/HPC `artifacts/`；评审所需的来源、版本、清洗规则和行级索引保存在仓库的 `analysis/` 中。

## 数据矩阵

| 专家 | 固定来源与 revision | 导出 train / val | 原生加载 train / val | 主要清洗与限制 |
|---|---|---:|---:|---|
| SWE | [nvidia/Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces) @ `1db674173119d71df45c22007af99e214600711a` | 2000 / 87 | 1993 / 87 | 选择成功修复轨迹；按仓库/任务族去重、排除 hard 任务和公开输入重叠；Swift 拒绝 7 条 role-pairing 错误 |
| Terminal | [TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K) @ `45f1e98e317d3639437f0eb02f4e8bc5825732f3` + [Terminal-Pivot](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1) @ `eaef26944643644c8a3dbbf361ce6128142f5976` | 2000 / 42 | 2000 / 42 | 保留到公开 `task_complete=true` 的完整历史；按任务/家族去重并保护正式任务输入；未发布尾部不补造，类别分布未推断 |
| HLE | Math-v4 817、MMLU-Pro 884、Science-v2 201、V4-Pro 82、GLM 16 及参考短答案 | 2000 / 100 | 2000 / 100 | 按学科配额和家族去重；清理 hidden reasoning；342 道图像题保留在正式评测；公开重叠排除不等于语义零污染证明 |
| ASI | ScienceAgentBench 82、DS-1000 976、SciCode 15 | 1073 / 20 | 1073 / 20 | 保留完整人工程序/代码；函数库补全单列，不冒称完整科学执行轨迹；固定公开 seed 的评测数据不进入训练 |
| Mixed | 上述四份训练分区按固定顺序合并 | 7073 / 249 | 7066 / 249 | 继承 SWE 的 7 条原生 role-pairing 过滤；不复制样本凑整 |

## 统一清洗与划分

- 训练数据、SFT validation 和正式 benchmark 任务分开；validation 只用于训练诊断，正式任务结果不用于挑 checkpoint 或合版系数。
- 统一使用冻结的 Qwen chat template、总上下文 65,536、单次 assistant 输出上限 8,192；超长样本删除，不静默截断。`enable_thinking=false`、`preserve_thinking=false`；删除 hidden reasoning 字段和闭合的 leading `<think>`，保留可见解释、工具观察以及 Terminal 的可见 analysis/plan。
- 去重使用来源任务/家族、仓库、内容和公开输入重叠检查；正式 benchmark 的题目答案、参考补丁、隐藏测试和测试反馈不进入训练或 checkpoint 选择。
- 每条样本的 provenance、任务/轨迹 ID、来源版本、教师、类别、长度、许可和筛选依据按来源写入对应 manifest；缺失的来源信息保持未知，不补造。

## 追溯文件

- [完整训练数据报告](../analysis/training_data_report_20261016.md)
- [行级来源与加载清单](../analysis/source_snapshots/training_data_inventory_20261016.json)
- [CSV 汇总](../analysis/training_data_report_20261016.csv)
- [SWE 数据专项](../analysis/data_swe_sources.md)
- [Terminal 数据专项](../analysis/data_terminal_sources.md)
- [ASI 数据专项](../analysis/benchmark_training_asi.md)
- [HLE 数据专项](../analysis/benchmark_training_data.md)
- [数据来源注册表](../data_sources.json)

许可证和上游 notice 见 [models/README.md](../models/README.md)、[models/notices](../models/notices/) 与各模型发布目录。数据规模、来源和清洗记录是本实验的可复现说明，不构成所有上游问题、代码或数据的统一再授权。
