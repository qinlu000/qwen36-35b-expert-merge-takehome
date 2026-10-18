# Terminal seed 2 single-run exploratory completion

固定 seed=2、每个任务只保留一次尝试后，两模型均得到完整 89/89 行：

| 模型 | 有效任务 | 正确数 | single-run 分数 |
|---|---:|---:|---:|
| Terminal 专家 | 89/89 | 8 | 8.988764045% |
| AVG64 | 89/89 | 11 | 12.359550562% |

补齐只复用了历史答案并运行独立 native verifier，没有新的模型调用，也没有覆盖历史 445 条结果。Terminal 专家补了 `pytorch-model-cli/seed2` 和 `train-fasttext/seed2`，AVG64 补了 `train-fasttext/seed2`。`train-fasttext` 使用了固定的离线 CPython 3.11.14 环境；官方 pytest 已运行，候选缺少 `/app/model.bin`，因此 reward=0 是有效 native 结果，不是环境 invalid。

该表是 **single-run exploratory**，不能解释为 Terminal-Bench 官方要求的五次运行均值或标准差，也不能与历史 445 条结果混合计算。
