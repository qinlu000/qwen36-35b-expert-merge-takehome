# 结果索引

本目录是最终提交的结果入口。大规模原始日志、模型请求、benchmark 题目/答案和沙箱产物仍位于受控本地/HPC `artifacts/`，没有复制进 GitHub；README 对此限制和复现根路径有明确说明。

## 已纳入 Git 的紧凑结果

- [完整结果矩阵](../analysis/complete_results_table_20261018.md)
- [SWE 逐题对照 CSV](../analysis/swe_task_comparison_20261017.csv) / [JSON](../analysis/swe_task_comparison_20261017.json)
- [ASI 逐任务对照 CSV](../analysis/asi_base_expert_task_comparison_20261017.csv) / [Markdown](../analysis/asi_base_expert_task_comparison_20261017.md)
- [HLE 合版消融表](../analysis/hle_merge_ablation_20261018.md) / [图](../curves/hle_merge_ablation_20261018.png) / [源数据](../curves/source/hle_merge_ablation_20261018.csv)
- [Terminal seed2 完整 exploratory 汇总](../analysis/terminal_seed2_completion_20261018.md) / [JSON](../analysis/source_snapshots/terminal_seed2_completion_20261018.json)
- [invalid 修复与 strict/null 说明](../analysis/invalid_repair_status_20261018.md)

## 原始结果位置

`configs/eval/final_results_20261017.json` 和各执行文档保存 canonical owner 输出与路径映射；这些路径指向被 Git 忽略的 `artifacts/eval/`。在原 HPC/CPU 环境中可用固定配置和汇总脚本重建逐项报告。公开 GitHub 提交不包含参考答案、完整轨迹、SIF、私有日志或凭据，因此 clone 后不能直接声称拥有全部原始 benchmark 结果。

缺失、invalid、环境失败和协议偏离均保留为 null 或独立审计视图，不能通过删除任务或缩小分母制造完整分数。
