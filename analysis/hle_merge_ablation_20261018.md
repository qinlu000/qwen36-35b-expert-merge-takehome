# HLE 合版消融对照

更新时间：2026-10-18（Asia/Shanghai）。本轮只比较 HLE，不扩展 AVG16、TIES-Dense 或其他合版候选到四项 benchmark。

| 模型/对照 | 有效题数 | 正确数 | HLE 分数 |
|---|---:|---:|---:|
| Base | 2500 | 99 | 3.96% |
| HLE 专家 | 2500 | 173 | 6.92% |
| Mixed883 训练对照 | 2500 | 146 | 5.84% |
| AVG64 主合版 | 2500 | 117 | 4.68% |
| AVG16 压缩对照 | 2500 | 101 | 4.04% |
| TIES-Dense | 2500* | 131 | 5.24%* |

AVG64 在 HLE 上**不是最佳**：HLE 专家 6.92% 最高，其次 Mixed 5.84%，AVG64 4.68%，AVG16 4.04%，Base 3.96%。相对 Base，AVG64 仅提升 0.72pp，且配对区间为 `[-0.20, 1.64]`，不能确认稳定提升。

HLE 专家和 Mixed 是训练/专家对照；AVG64 与 AVG16 是合版/压缩对照。TIES-Dense 的 `2500*` 是在原 2499 条 replacement-Judge 结果上，对唯一缺 `correct` 的冻结 Judge body 做独立离线 score-only overlay 后得到的 `131/2500 = 5.24%`；没有重生答案、没有重发 API，也没有修改原始 `result.json`/`summary.json`。该项不是官方 Portal 重新判分，原始 invalid 仍保留在源目录。其余结果使用同一 HLE replacement Judge、342 道图像题、64K/8K/nonthinking 协议；该 Judge 不是官方 Portal 认证。

本轮不启动新的 HLE 任务、不按 HLE 分数更换主 AVG64；Terminal 新口径另行记录为每任务单次 exploratory，不能与历史五 seed 445 条结果混报。
