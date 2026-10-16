# HLE 更多现成回答：跨学科候选核查（2026-10-16）

用户要的是**更多已经有答案的强教师样本**，不需要重新调用 API 生成，也不意味着退回 500 条。已有思考模式生成的数据，可以删除隐藏 reasoning / `<think>` 部分后仅训练完整 final；这与“教师当时关闭 thinking”不是同一件事。下面三源均实际有回答。没有启动下载大包、API、训练或改动队列。

## 1. DeepSeek-V4-Pro-Reasoning-8000x：优先的小型跨学科候选，需筛题

- [发布者卡](https://huggingface.co/datasets/trjxter/DeepSeek-V4-Pro-Reasoning-8000x)，固定 revision `7329257a28babc5998be072a3d8add1dd8ad0fda`。作者及 viewer 均为 **8,014 行**：General 3,366、Science 2,468、Math 2,180。JSONL 547,280,201 bytes。卡声明教师为 DeepSeek-V4-Pro，来自 DeepSeek API；属于**个人发布者声明**，不是 NVIDIA 或 DeepSeek 官方生成的数据卡。
- `input` 是题，`output` / `conversations` 已有 `<think>…</think>` 与 final。逐条 `meta` 有 teacher、source_dataset/config/split/index、seed_id、finish_reason。50 条 viewer 小样本删除 think 后 **50/50 非空 final，中位 1,365.5 字符**；其中包含解释与代码，确实不需要重跑教师。
- 来源链是 `Jackrong/GLM-5.1-Reasoning-1M-Cleaned` 的问题，由 V4-Pro 重新回答。比如第一条 `source_config=main, source_index=847`；另一条 `main, source_index=10927`。这些是**原池定位字段，不是原始学术题来源**。该池与下一项共享题源，合并时不能当两批独立问题；本次未核到它是 NVIDIA Math/Science 的重包，也未完成跨池重复核查。
- 首屏可见大量简单题和缺上下文题，例如列举人体器官、缺失待转换文本的指令。General 不能直接等同 HLE 人文；Science 标签也不证明有唯一正确答案。作者只验证了格式完整性，未提供逐题 gold 判分。13 条 finish_reason=length、2 条 final 截断警告，需排除不完整回答。
- **HLE 风险：**没有公开 HLE 版本或逐题排除清单，也没有把原始 prompt 数据集映射保留到底；不能声明已证明与正式 HLE 无重叠。后续仅从题面及已有排除索引排重，不用 HLE gold 挑样本。本轮小样本不构成全库去污染证明。

判定：**有现成 final、无需 API；适合先筛学术子集，不宜全 8k 直接入训。**

## 2. GLM-5.1-Reasoning-1M-Cleaned：量大，但来源追溯和难度要筛

- [清理版卡](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned)，固定 revision `f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d`。作者统计实际保留 **746,321 行**，不是一百万独立问题：main 527,737；PHD-Science 103,706；Multilingual-STEM 92,781；Math 22,097。完整四文件约 31.7 GB；这些是回答行数，尚未实数独立原题数。
- 清理版有明确 `input/output/conversations/domain/meta`，think 与 final 边界已归一化。仅流式读取 main/PHD 文件各前 512 KiB（不下载全库），分别解析出 42/20 条完整记录；每组查看前 10 条，删除 think 后均 **10/10 非空 final**。main 的 final 中位 425.5 字符，PHD 中位 6,504 字符。main 中有仅 `sand` 的答案，也有代码与解释，因此不能把全部记录都当丰富轨迹。
- PHD 小样本是基因网络、肿瘤多组学、QM/MM、空气化学等开放型研究综述题；输出是长篇解释，不是经过独立验证的数值/唯一答案。main 可见编程、逻辑、哲学等，但**没有足够证据说人文学科、工程、CS 的占比符合 HLE**。
- 逐条 meta 只有 `input_tokens/output_tokens/teacher_model=GLM-5.1`，缺原始 benchmark/URL/原题 ID。来源追至[原版 GLM-5.1 池](https://huggingface.co/datasets/clzoro/GLM-5.1-1000000x)，再至 [KIMI-K2.5-1000000x](https://huggingface.co/datasets/ianncity/KIMI-K2.5-1000000x)。后者仅称修改 Datagen 采集，给大类比例，未列可核的原始题集列表；原版/清理版行数不同，不用原版“1M”替代清理版实际量。
- **教师和污染边界：**GLM-5.1 是发布者声明的回答教师，可按项目已核模型比较证据评估资格；清理不是重新生成。卡没有声称源于 cais/hle，但也**没有证明排除了 HLE 官方题**。由于原始题源缺失，只列候选；不能因 PHD 名字或大规模就标已独立、可全量放心训练。

判定：**存在大量可抽 final 的回答；需按题面筛学术相关性、完整性和正式评测重复，不建议直接替换主池。**

## 3. NVIDIA Finance Document Grounded Reasoning：官方 V4-Pro 答案，窄领域辅助

- [官方卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Finance-Document-Grounded-Reasoning-v1)，固定 revision `292812d664c918bcd2e9103a4b17ed6883ae8458`。**63,056 条**，1,010,575,788 bytes；Qwen3.5-397B 生成问题、**DeepSeek-V4-Pro 生成答案**、GPT-OSS-120B 过滤/GenSelect。主要教师答案有 NVIDIA 一手方法说明，可信度高于个人重包标签。
- `messages[0].content` 已带 SEC 文件上下文和问题；`messages[1].content` 是答案，reasoning_content 单列。流式读取前 512 KiB 共 53 条完整记录，查看前 10 条，答案 **10/10 非空，中位 273 字符**。删除 reasoning_content 不会删掉答案。
- metadata 例：`company_name=ALLE, year=2024, file_path=ALLE/10-Q/2024/0001579241-24-000031/part1item1/part1item1_7.txt, question_type=Adjustments`。有数值、趋势比较、复杂检索、分析等任务；源是 2017–2024 年 S&P500 的 SEC 10-K/10-Q/8-K 片段，有实际文档定位。按公司/文件家族处理关联样本，63k 行不等于63k独立文档。
- 与闭卷 HLE 的任务分布不同，不能靠大量财报检索题补满人文/工程名额。HF viewer 因 metadata 可选字段报 schema 错，但原 JSONL 可解析；文本 SFT 不需要运行新环境。本轮未核到与 NVIDIA Math/Science 同源，正式 HLE 排重仍需保留。

判定：**可直接清理成非 thinking SFT，适合少量金融/数值辅助；不是本轮扩到 2k 的核心来源。**

## 不优先的两项和当前结论

- [Nemotron-Cascade-2-SFT-Data](https://huggingface.co/datasets/nvidia/Nemotron-Cascade-2-SFT-Data)：真实有大量完整对话，但科学答案教师是 GPT-OSS-120B，数学是 V3.2/Speciale/GPT-OSS。general chat 源自旧 Cascade/Instruction-Following，不能仅凭 NVIDIA 品牌或样本大就保证教师不弱于本题 base。
- [Nemotron-SFT-Instruction-Following-Chat-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Instruction-Following-Chat-v4)：官方最新 3,850,582 对话，用 Kimi-K2.6、Gemma4-E4B-it、Qwen3.5-397B 混合生成，逐条公开 metadata 未明确教师字段。官方允许删除 reasoning_content，但需要保持 train_turns_mask；这是一般多轮聊天，不是已筛好的 HLE 学术题，暂不优先。

**最省时间的主路线仍是已核的 NVIDIA Math-v4 纯 CoT final + Science-v2 明确 V4-Pro 的纯问答 final；两者本来就远多于 500 条。**这次新增的 V4-Pro 8k、GLM5.1 清理池证明还有跨学科候选，不必重采教师；若采用，先筛与 HLE 题型相关的完整答案，并把来源不明、缺上下文、空/截断 final、正式 HLE 同题排掉。没有证据预先承诺所有 HLE 学科都能按原比例用强教师现成数据补齐。

本报告仅记录来源核查；未纳入训练，未重建 Mixed，未恢复 HLE 答案生成，未修改当前 500 条权重的状态。后续规模须以实际筛出的独立问题数报告，而非来源卡行数相加。
