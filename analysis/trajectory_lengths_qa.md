# 静态科研程序与学术 QA 的训练长度

2026-10-16，80 上 CPU 实测。**D3 全量 2153 条去掉公开 teacher 推理前缀后，assistant 内容最大 3713 tokens，全部能放进 4K；输入加输出的模板总长最大 14924，全部能放进 16K。**这是已发布静态训练目标的长度，不证明 ASI、HLE 生成时 4K 足够。

用户关心的多轮“轨迹”以 SWE、Terminal 为主，由对应报告单独统计。本报告的 D3 是单次科研程序，OpenR1 是单轮学术 QA；不与多轮工具轨迹混成一个分布，不代表正式 HLE 题目。

**raw/clean 仅是长度对照，本轮没有决定正式训练是否去推理、如何清洗或筛选，也没有生成清洗后的训练文件。**

## 数据与口径

- [osunlp/D3-Gym-Trajectories](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/tree/b21b5006956d7d246cf3e35277b13323780a45b2)：固定 revision `b21b5006956d7d246cf3e35277b13323780a45b2` 的 `Qwen3_32B_trajectories.json`，**2153/2153 全量**。schema 仅 instruction/input/output，没有 token 长度列。临时按 instruction→system、input→user、output→assistant 测模板长度；不是已经选定最终 ASI prompt。
- [open-r1/OpenR1-Math-220k](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/tree/e4e141ec9dea9f8326f4d347be56105859b2bd68/data)：固定 revision `e4e141ec9dea9f8326f4d347be56105859b2bd68`，仅已下载 default 的 10 片、93733 行。每片用 seed `20261016+分片序号` 均匀无放回抽 200，共 **2000 条等额分层样本**，只读 messages。以下是未加权的样本统计，不声称全库精确比例；各片 N=9373/9374，样本 n=200。answer、solution、generations、expected_answer 不加入 policy 输入。
- 固定 [Qwen3.6-35B-A3B tokenizer/template](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0)，revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；Qwen2TokenizerFast，transformers 4.55.0、tokenizers 0.21.1。模板 SHA256 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。
- **raw**：保留发布的 teacher 推理，`enable_thinking=true/preserve_thinking=true`；**clean**：只移除 assistant 开头配对的 `<think>…</think>` 前缀及独立 reasoning_content，再用 false/false 渲染。均 `add_generation_prompt=false`。可见解释、答案、代码不删；不平衡标签保留并计数，不猜测边界。
- 最初计数使用全局配对标签移除；随后独立核验全部实际计数记录：D3 的 2153 个配对块全部是前缀，OpenR1 的 1996 个配对块也全部是前缀；两种清理结果逐字差异均为 0。因此不重复 token 计数，当前脚本已改为仅剥前缀。OpenR1 另有 4 条不平衡标签，按规则保留。
- 总长是完整 chat 模板 tokens；assistant 指单条 content 的 tokens，不含消息 wrapper。两源每条恰好一条 assistant，所以每条与每消息输出相同。K=1024，覆盖定义为长度 ≤ 窗口；百分位按 `(n−1)q` 线性插值。单独分段 token 数不一定严格相加等于整段 token 数。

## D3 全量：程序、题目、推理分开看

以下各行 n=2153，单位 tokens；未执行任何样本程序。

| 口径 | mean | p50 | p90 | p95 | p99 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw 模板总长 | 8878.19 | 8441 | 13870.20 | 15640 | 18800.76 | 27986 |
| clean 模板总长 | 3290.97 | 2683 | 6980.80 | 8300.40 | 13366.60 | 14924 |
| raw assistant | 6353.73 | 5856 | 10626.80 | 12075 | 14593.28 | 16208 |
| clean assistant：完整发布解答候选 | 762.51 | 636 | 1415.80 | 1684.40 | 2330.40 | 3713 |
| 其中 Python fenced 代码块合计 | 738.12 | 614 | 1363.80 | 1608 | 2326.40 | 3709 |
| 移除的公开推理前缀（含标签） | 5591.22 | 5159 | 9474.20 | 10633.40 | 13294.16 | 14998 |
| user 题目 | 2428.46 | 1693 | 6163 | 7509 | 11794 | 13291 |
| system instruction | 81 | 81 | 81 | 81 | 81 | 81 |

2153 条均有配对推理前缀和 Python fenced 代码。这只证明代码块存在；完整性、执行成功及任务映射仍沿用此前来源证据，未做本地重放。短输出和较长输入可以同时出现：去推理后仍有 119 条模板总长超过 8K。

| D3 模板总长覆盖 | 8K | 16K | 32K | 64K | 128K |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 47.7938% | 96.4236% | 100% | 100% | 100% |
| clean | 94.4728% | 100% | 100% | 100% | 100% |

| D3 assistant 输出覆盖 | 4K | 8K | 16K |
| --- | ---: | ---: | ---: |
| raw | 26.1031%（超长1591） | 73.4789%（超长571） | 100% |
| clean | 100% | 100% | 100% |

因此若保留发布推理，4K/8K 输出截尾会切掉大量监督目标；若选非思考 SFT 并正确去前缀，本库静态代码输出通常很短。不要把删除 teacher 推理与删除程序的错误混为一谈，也不要直接将本库上界当作正式 ASI 的生成上界。

## OpenR1 学术 QA：2000 条样本，单独列示

| 口径（n=2000） | mean | p50 | p90 | p95 | p99 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw 模板总长 | 6072.56 | 5050.50 | 12088.50 | 14236.15 | 17109.74 | 21395 |
| clean 模板总长 | 672.56 | 637 | 889 | 969.15 | 1231.10 | 18779 |
| raw assistant | 5965.56 | 4950.50 | 11955 | 14174.30 | 16906.58 | 21303 |
| clean assistant | 561.57 | 533 | 754.10 | 828 | 1006.06 | 18262 |
| 移除的公开推理前缀（含标签） | 5404 | 4358.50 | 11388.40 | 13483.95 | 16303.35 | 21220 |
| user 题目 | 97.02 | 81 | 165 | 195 | 339.06 | 2094 |

| OpenR1 样本模板总长覆盖 | 8K | 16K | 32K | 64K | 128K |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 74.95% | 98.35% | 100% | 100% | 100% |
| clean（保留不平衡标签记录） | 99.8% | 99.9% | 100% | 100% | 100% |

| OpenR1 样本 assistant 输出覆盖 | 4K | 8K | 16K |
| --- | ---: | ---: | ---: |
| raw | 41.2%（超长1176） | 75.7%（超长486） | 98.6%（超长28） |
| clean（保留不平衡标签记录） | 99.8%（超长4） | 99.8%（超长4） | 99.9%（超长2） |

不能根据 clean 的短 p95 就直接截断剩余长尾；4 条不平衡标签记录应先作为格式异常单列，之后决定筛选或人工规则。当前没有读取对应正确性标签、筛成功、导出训练集，也没有证明 samples 与多个 generations 的验证标签一一对应。

## 本轮覆盖边界与产物

OpenScienceReasoning-2 固定 `174b02c9cdf231f220765b2a1d5ece4550921894` 的已下载文件有 1600812 行，schema 只有 input/output/expected_answer，**无现成长度**。它是 15.7GB 单 Parquet、9 个 row-group，已查前 5 组均为 200099 行；覆盖全文件的均匀随机抽样仍需较大解压读取。本轮先完成 D3 与 OpenR1，**未 tokenize 此来源**，不能引用早先两条检查作为全库长度分布。

聚合结果见 [trajectory_lengths_qa_20261016.json](source_snapshots/trajectory_lengths_qa_20261016.json)，包括完整阈值计数、抽样文件/种子/索引 SHA、标签规则等价核验；无样本正文。复现脚本 [audit_qa_lengths.py](../scripts/audit_qa_lengths.py)，本次 `--openr1-per-file 200 --open-science-sample 0`。总 CPU 计数用时约 247.66 秒；固定最多 4 个可用 CPU affinity，关闭 tokenizer 自动并行，pyarrow 线程上限 4；没有加载权重、API/GPU 调用、正式评测、下载、样本执行或训练集构造。
