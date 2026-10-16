# 新学术数据 CPU 审计与候选分族（2026-10-16）

## 范围与结论

本轮实际检查了新发布的 Math-v4 / Science-v2，并生成远端仅含元数据的 train/val **候选保留分区**。尚未确定最终训练题数、token 配额或可运行 task-dev 数量；未导出 ms-swift 训练正文、调用教师/评分 API、占用 GPU、执行数据里的代码或生成新任务。

- **Math-v4 可以作为新数学主候选**：首个固定 Parquet 的 23,605 行全部为 AoPS / cot，发布者提供参考答案匹配依据。128 条随机测长显示，删除 reasoning 后仍通常保留数百 token 的可见正文，不能说全部只剩最后一个答案。
- **Science-v2 需要逐桶处理**：分散 Range 确实找到 V4-Pro 的数学、物理、化学、生物内容。它同时含 V3.2、Kimi-K2、GPT-OSS，不能把整库称为 V4 数据；没有独立 gold 的候选保留 `needs_gold` / `needs_answer_verification`。
- **协议有实质差异**：rqa 分散段中的 728 行含 `developer` 角色，固定 Qwen 模板不接受；本轮隔离，不擅自改角色。工具调用、工具结果或仅声明了工具的消息不进入 HLE no-tools 候选，仍可在另一个工具任务研究中单独考虑。
- 已知来源覆盖数学、物理、化学、生物，不能据此补齐 HLE 的 CS / Other / Humanities / Engineering 或图像边际。类别不足保留缺口，不用数学填满。

## 固定来源与有界读取

| 来源 | 固定 revision | 本轮实际读取 |
| --- | --- | --- |
| [NVIDIA Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/README.md) | `84d42ad0cb960f07f951b9baa9ed2b46a5a18c66` | `data/train-00000-of-00012.parquet` 一片，480,546,925 B；SHA256 与 LFS `875c8a6d…81199f` 全值相符；不是 12 片全量 |
| [NVIDIA Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/6536a5021222a94126968e8c92f29ee47fc8a7df/README.md) | `6536a5021222a94126968e8c92f29ee47fc8a7df` | 四个 JSONL 各 8 个 8MiB 范围，偏移为 0 及 `floor(file_size*k/8), k=1..7`；每文件 64MiB、总 256MiB |

Science 的全部 32 次请求均核验 HTTP 206、精确 `Content-Range` 和接收字节上限；每段有内容 SHA256。分散段丢弃首尾不完整行。每段 hash 证明收到的局部内容一致，**不等于完成整文件 LFS 校验**。读取为按字节分散的便利样本，不是均匀抽行，不能推断全库教师/类别比例。HF viewer schema 只作辅助；实际消息来自上述固定原文件，未按 viewer 的 partial 行数计算全库。

| Science 文件 | 完整可解析行（本轮范围内） | 首 8MiB 的完整行 |
| --- | ---: | ---: |
| rqa | 3,190 | 734 |
| so | 8,341 | 450 |
| syn_mcq | 11,793 | 1,135 |
| vendor | 688 | 141 |

对比可见，首段曾让 rqa/so 看起来全部是 V3.2、vendor 全部是生物；补充分散段后才出现其他教师/学科，因此不能沿用前缀比例。完整 receipts 含 URL 可重建的源路径、revision、请求范围、HTTP 状态、字节数与 hash，存于远端 ignored 审计目录及聚合 JSON。

## 清理、渲染与长度

使用 80 的 `/data/caoqinlu/projects/dslighting/.venv/bin/python`；transformers 5.15.0、tokenizers 0.22.2、pyarrow 25.0.1。CPU affinity 和相关线程上限均为 2。固定 Base tokenizer revision 为 `995ad96eacd98c81ed38be0c5b274b04031597b0`，chat template SHA256 为 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。

先用两个人造消息样例验证字段清理、JSON 工具参数解析、工具动作/结果/角色保留，再用三个畸形 think 样例验证隔离。真实样本只静态解析，不运行 Python 或任何工具。

- raw：`enable_thinking=true, preserve_thinking=true, add_generation_prompt=false`。
- clean：去 assistant `reasoning_content` / `reason_content` 和一个平衡的开头 think 块；畸形、非开头、嵌套/多块不盲删；`enable_thinking=false, preserve_thinking=false, add_generation_prompt=false`。
- 可见解释、工具动作、观察和消息顺序均保留。JSON-string 工具参数按发布 schema 解码为对象，使其能被固定模板渲染，未更换工具名或动作。
- 模板仍会输出空 `<think>\n\n</think>` 壳；关闭模式不等于所有 tag 在序列里消失。

Math 在首片内固定 seed 20261016 均匀随机抽 128 行。Science 按实际观察到的 teacher / 工具行为 / topic / subtopic / 源文件 / license 组合各抽至多 8 条，seed 同上；**下表为未加权审计样本统计，不是全库估计**。

| 来源 | 可渲染 / 抽样行 | raw 完整序列 P50 | clean 完整序列 P50 / P95 | clean assistant 正文 P50 |
| --- | ---: | ---: | ---: | ---: |
| Math-v4 | 128 / 128 | 19,441 | 631.5 / 1,183.2 | 542.5 |
| Science rqa | 292 / 440 | 4,103.5 | 825 / 2,833.6 | 246.5 |
| Science so | 541 / 541 | 1,832 | 253 / 5,087 | 64 |
| Science syn_mcq | 434 / 434 | 2,490.5 | 398.5 / 3,472.85 | 87.5 |
| Science vendor | 203 / 203 | 29,913 | 499 / 1,107.5 | 180 |

共抽 1,746 行，成功渲染 1,598 行；rqa 的 148 条抽样因 `developer` 角色隔离。此表包含工具样本用来审计，后续 HLE 候选筛选还会排除工具契约。

清后 assistant 正文 ≤128 token 的形式短答标记分别为 Math 4/128、rqa 52/292、so 424/541、syn 253/434、vendor 59/203；≥512 token 分别为 74/128、54/292、2/541、1/434、20/203。长度只说明形式，不能自动判定保留了解题过程或答案正确。SO / syn 清后通常较短；不能因为原始 trace 很长就把其 raw thinking 数量算成实际监督。

这里的完整序列长度是一遍渲染的成本代理；assistant 正文长度排除了 thinking 字段、消息壳和工具调用序列化，**不是 ms-swift 最终 labels/S**。窗口、packing、mask、重复历史、epoch 和 padding 未定，因此也不是最终 P 或训练吞吐。

## 候选分族与保留分区

候选清单由 `scripts/select_new_academic_candidates.py` 生成，正文/答案不写入 Git。按原题规范化 hash、规范 URL、发布 UUID 传递联合成族，每族先取一条代表。规范化采用 NFKC → 压缩 Unicode 空白 → strip → casefold → SHA256。不同教师的同题不会按不同轨迹行分到两侧。

共享规则为 `candidate_selection.py` 的 seed `apex-new-data-v1-20261016`，`family_rank = sha256(seed+'\0'+family_key)`；rank 前 16 hex 转整数 `%10==0` 留候选 val，其他留候选 train。这是约 10% 的保留规则，不是 HLE 类别比例或最终验证规模；类别内另有稳定排名，后续按可用 token/时间给配额。

八类目标保持题面锁定的公开统计：Math1021、Bio280、CS241、Other233、Physics230、Humanities219、Chem165、Engineering111，共2500。Math/Science 新扫描只作明确的 math/Mathematics、biology、physics、chemistry 映射；Science `Other` 等模糊标注不强行套进 HLE Other。图像342/2500单独报告，当前新池未提供实际图像输入。

正式 HLE 只用 root 提供的 question 指纹做精确排除，不读 answer/rationale、不据其题面选择训练题。一个命中即整族排除。**零精确命中不等于完成去污染**，仍缺改写、嵌入 prompt、图像、来源近重复的核验。

旧 OpenR1 的 10 片只投影 `problem/uuid` 共 93,733 行，用于跨教师同题联组；旧源重叠单列 `old_source_overlap`，保留新教师代表且共享同族 partition，**不会误当正式测试题剔除**。尚未扫描旧 OpenScience 的 1.6M input，也未完成语义/题族近重复检查。

最终得到 35,340 个观察到的精确族，一族一条代表；下表是足量候选池，**不是按 HLE 比例最终选出的训练集**。后续按八类目标比例从各类排名取配额，缺类配额空缺。

| HLE 类 | 候选 train 族 | 候选 val 族 | HLE 目标份额 |
| --- | ---: | ---: | ---: |
| Mathematics | 12,880 | 1,474 | 40.84% |
| Biology | 3,001 | 323 | 11.20% |
| Physics | 11,759 | 1,316 | 9.20% |
| Chemistry | 4,133 | 454 | 6.60% |
| Computer Science | 0 | 0 | 9.64% |
| Other | 0 | 0 | 9.32% |
| Humanities | 0 | 0 | 8.76% |
| Engineering | 0 | 0 | 4.44% |

train 共31,773族、val共3,567族。其中 **Math-v4 发布参考可用**的 train12,739、val1,463；其余21,138族为 Science teacher 答案、无独立 gold（train19,034 / val2,104）。Science 的 `validation_needs_gold` 不计为可运行 task-dev；Math 仍需核评分器和参考语义，不能宣称全为人工独立真值。更细的 teacher/category/readiness 计数见 `analysis/source_snapshots/new_academic_candidate_split_20261016.json`。

本范围内 HLE 完整规范化输入精确命中0；旧 OpenR1 对上10个观察族，保留新代表且旧别名同分区。manifest35,340行的共享hash分区规则、族key唯一、88,223个族别名跨侧无重叠、精确prompt跨侧无重叠均验证通过；manifest SHA256 为 `ecb4e688535ed91196eed6463e727027b9d8011adc91dc7e6bff78be0cb8e412`。这些只验证已观察的精确关系，仍非完整语义去重。

## 来源依据与下一步

Math 首片全为 AoPS，原题 URL 为空，题族识别目前主要依赖发布 UUID 与题面 hash；它尚不代表 Math-v4 的 Math StackExchange/TIR 分布，也不证明覆盖 HLE 研究型数学难度。Science SO 范围 8,341 行中有 8,339 行带 QuestionLink；rqa/syn/vendor 未带原始问题 URL，vendor 研究生难度标签不能代替透明原始题源或金标准。保留逐行 license/归属信息（Math 此片 CC BY4.0，Science CC BY-SA4.0），不把 teacher 开放当作质量标签。

接下来以每类稳定排名和完整族别名为索引，先补缺失 HLE 类/图像的可信新源，再决定最终配额。Math 可以进入评分器核验；Science 优先核有透明源链接和可获取参考的子集，缺 gold 的 val 仍留待补齐。训练窗口、LoRA 配置和 GPU 训练吞吐未定，本轮不再据未清理 raw 长度硬推固定 15M。

## 文件与复核

- 本地聚合：`analysis/source_snapshots/data_audit_academic_20261016.json`、`analysis/source_snapshots/new_academic_candidate_split_20261016.json`。
- 远端审计：`/data/caoqinlu/projects/apex-takehome/artifacts/data/audits/new_academic_20261016/`，含固定源 index/README/schema、receipts、hash/数值测量（ignored）。
- 远端候选：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/new_academic_20261016/ranked_candidates.jsonl`、`quarantined_metadata.jsonl`（ignored，只元数据）。
- 脚本静态编译通过；人造清理/工具保留测试通过；真实原文件只作数据解析与 tokenizer 渲染。候选 manifest 另外核验 hash 分区规则、族别名 train/val 无交叉及行数一致。未执行真实样本代码或模型训练。
