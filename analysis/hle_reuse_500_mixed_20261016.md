# HLE 复用现有结果与 Mixed 重建

2026-10-16，按用户最新要求，HLE 不再等待新生成的 2000 题答案，Mixed 复用既有 HLE 500 条训练数据、100 条验证数据。HLE 模型和数据本身未在本次操作中修改。

Mixed 使用现有 `scripts/prepare_mixed_sft.py` 在服务器 80 导出，并通过 rsync 同步到 HPC。四个来源各出现一次，顺序如下：

| 专家 | 训练条数 | 验证条数 | 相对项目根目录的数据路径 |
|---|---:|---:|---|
| HLE | 500 | 100 | `artifacts/data/candidates/night_hle_20261016/swift_ready` |
| SWE | 2000 | 87 | `artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k` |
| Terminal | 2000 | 42 | `artifacts/data/candidates/terminal_sft_2k_20261016` |
| ASI | 1073 | 20 | `artifacts/data/candidates/asi_sft_expanded_20261016` |
| 合计 | **5573** | **249** | `artifacts/data/candidates/mixed_expanded_20261016` |

导出保留完整 messages 与 tools；缺少 tools 时填空列表。来源的其他元数据继续保存在各专家目录中。未重采样、未截断、未重复样本，未改动既有验证集。

产物包含 `train.messages.jsonl`、`val.messages.jsonl`、`summary.json`，位于：

- 80：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/mixed_expanded_20261016`
- HPC：`/data/user/qinlucao/projects/apex-takehome/artifacts/data/candidates/mixed_expanded_20261016`

HPC 实际读取文件确认训练 5573 行、验证 249 行，summary 中的训练来源条数为 `[500, 2000, 2000, 1073]`、验证来源条数为 `[100, 87, 42, 20]`。80 导出前目标目录为空，没有覆盖或删除此前的 7073 条版本。

本次工作仅完成 CPU 数据导出和传输；未调用 API，未提交、解除依赖或修改 GPU 作业，未重新训练 HLE。队列依赖及主进展文档由主任务更新。
