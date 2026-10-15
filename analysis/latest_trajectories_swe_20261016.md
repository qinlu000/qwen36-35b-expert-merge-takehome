# 最新强教师 SWE 训练轨迹候选（2026-10-16）

## 结论

存在比已下载的 Qwen3.6-27B 教师更新、而且继续使用 mini-swe-agent 的真实公开轨迹。最值得先审计的是 NVIDIA Open-SWE 的 **Qwen3.8-Flash-Next / mini-swe-agent** 与 **Qwen3.8-27B / mini-swe-agent** 两个分区。它们与现有 Open-SWE 同仓、同固定 revision，能复用此前的数据读取与 mini 工具协议适配思路；新分区尚未下载、逐行核验或选入 train/dev。不能将“同为 mini”写成已通过本实验 harness 兼容验收。

本轮只查官方数据卡、分布表、文件索引与模型卡；未读取正式 benchmark 答案、样本补丁、轨迹正文，也未运行任务或模型。表中的轨迹与成功数量是发布方统计，不是本轮重新执行验证。

## 四个优先候选

前三项均固定到 `nvidia/Open-SWE-Traces@1db674173119d71df45c22007af99e214600711a`。数据卡声明：底层 issue 和执行环境**全部来自 Scale-SWE 与 SWE-rebench-V2**；数据为完整 system/user/assistant/tool 消息，带 `resolved`、`instance_id`、`trajectory_id`、仓库、语言、来源及 teacher 等元数据。`resolved=1/0/-1` 分别表示成功、失败、未知。许可为 **CC-BY-4.0**，并保留上游仓库许可要求。[固定数据卡](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[固定分布表](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)、[含字节数的固定文件 API](https://huggingface.co/api/datasets/nvidia/Open-SWE-Traces/revision/1db674173119d71df45c22007af99e214600711a?blobs=true)。

| 候选 | 发布方统计 | 可下载路径与大小 | 思考 / harness / 使用代价 |
|---|---|---|---|
| **Qwen3.8-Flash-Next mini** | 36,577 轨迹、36,577 unique PR；**17,807 resolved**、18,770 unresolved、0 unknown | `data/minisweagent/qwen38_flash_next/`；**16 Parquet，3,653,370,550 B**。其中 `scale-swe/train-00000-of-00007.parquet` 至 `00006`，`swe-rebench-v2/train-00000-of-00009.parquet` 至 `00008` | 分布表标 **Thinking**；mini-swe-agent。体量较小、成功轨迹已够本项目，建议作为新增数据的首个结构审计对象。 |
| **Qwen3.8-27B mini** | 107,267 轨迹、41,405 unique PR；**49,925 resolved**、46,670 unresolved、10,672 unknown | `data/minisweagent/qwen38_27b/`；**44 Parquet，10,687,441,540 B**。Scale-SWE 与 SWE-rebench-v2 各 `train-00000-of-00022.parquet` 至 `00021` | 分布表标 **Thinking**；mini-swe-agent。同一 PR 多次 rollout，不能将轨迹数当独立任务数。 |
| **DeepSeek-V4-Flash-0731 / OpenHands** | 50,295 轨迹、32,660 unique PR；**23,110 resolved**、27,185 unresolved、0 unknown | `data/openhands/deepseek_v4_flash_0731/`；**21 Parquet，3,701,902,589 B**。Scale-SWE 11 片、SWE-rebench-v2 10 片 | OpenHands 的多工具和状态语义与 mini 不同；可作为强教师备选，不能只改工具名就直接混用。具体生成开关未在本轮逐条扫描，应以实际元数据为准。 |
| **GLM-5.2 coding/debugging traces** | **207 个 accepted 完整任务轨迹 → 1,821 个 cumulative-next-action 训练行**；不是 1,821 个独立任务 | `greghavens/glm-5.2-coding-and-debugging-traces@f115b6689332e3bb2d22c6a42bd22a3ebb95625b`；卡提供 `traces.jsonl` 及 Parquet。卡标注约 35 MB JSONL / 约 1 MB Parquet，非本轮重新汇总的精确大小 | Pi / moonshiner 的 read/edit/bash 等工具，与 mini 存在语义差异；作者声明通过测试、保护文件检查、约束门禁与独立接受审查。此为作者声称的 QC，不是我们实跑。 |

GLM 数据卡记录的任务混合为 building 79、debugging 73、project integration 18、feature 16、tool 13、refactor 7、other 1；不是纯 GitHub 修复集。教师接口名为 `glm-5.2`，尝试 xhigh→medium→low 并保留先通过者，未给每次调用不可变权重 revision。累计前缀样本只能监督目标的最后一次 assistant 动作，否则早期动作会被重复加权；同轨迹必须整体归入同一 split。该数据集于 2026-07-15 建立，固定版本最后修改于 2026-07-25，许可 CC-BY-4.0。[固定 GLM 数据卡](https://huggingface.co/datasets/greghavens/glm-5.2-coding-and-debugging-traces/blob/f115b6689332e3bb2d22c6a42bd22a3ebb95625b/README.md)、[固定 API](https://huggingface.co/api/datasets/greghavens/glm-5.2-coding-and-debugging-traces/revision/f115b6689332e3bb2d22c6a42bd22a3ebb95625b?blobs=true)、[作者 runtime](https://github.com/greghavens/moonshiner)。

### 发布时间的准确口径

NVIDIA 固定数据卡写 `[09/26] Release v1.2`，宣布 Qwen3.8-27B mini；文件索引和分布表同时已有 Flash-Next mini。该日期文本不用于断言“9 月 26 日”；本轮未取得两个子分区各自的首次文件提交日期。整仓固定 revision 最后修改为 **2026-10-13 23:39:28 UTC**。v1.1 的 `[08/26]` 条目声明 DeepSeek-V4-Flash-0731 与 Qwen3.6-27B 发布。[数据卡与文件 API 同上](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)。

公开 Qwen3.8-27B 官方仓库有 **2026-08-14 发布**的公告；Flash-Next 模型仓库建立于 **2026-08-24**，本轮固定版本修改于 08-27，但没有将仓库建立日等同正式发布日。DeepSeek 官方 0731 模型仓库建立于 **2026-07-31**，卡声明其取代 Preview。公开模型卡 revision 只能证明该公开模型的版本，不能反推 NVIDIA 采集时加载的精确权重 hash。[Qwen 官方发布记录](https://github.com/QwenLM/Qwen3.8/blob/main/README.md)、[Flash-Next 模型 API](https://huggingface.co/api/models/Qwen/Qwen3.8-Flash-Next/revision/de4b8e4d43b917e7706784d8bb445c9af86a3540)、[DeepSeek 固定模型卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md)。

## 教师更强，有哪些公开证据

Qwen3.8-27B 官方同表报告 **SWE-bench Pro 61.7 vs Qwen3.6-27B 53.5**，DeepSWE 1.1 为 **42.2 vs 13.3**。Qwen3.8-Flash-Next 同表报告 **SWE-bench Pro 62.5 vs Qwen3.8-27B 61.7**，DeepSWE 1.1 为 **58.7 vs 42.2**。这支持优先审计新版教师，而非仅因版本名称较新就认定更强。[Qwen3.8-27B 固定模型卡](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md)、[Flash-Next 固定模型卡](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md)。

比较边界：这些模型默认支持/开启 thinking，NVIDIA 两个新 Qwen 分区也明确标 Thinking；上述 SWE Pro 是 Claude Code、256K context、经过 refined 的任务集，**不是本题 HARD51 / 本实验非思考 64K 总上下文、8K 输出的同条件测量**。DeepSWE 表还混合采用 Claude Code 与 mini 的最佳成绩，Flash-Next 最佳为 mini；不能将分数差直接解释为现有 base 的本实验提升，也不能证明删去思考后的轨迹质量。[两份固定模型卡的 evaluation 设置同上](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md)。

## 可以直接复用什么、仍须自己完成什么

1. **优先沿用 mini 路线**：复用现有 Open-SWE 下载清单、Parquet 读取、按完整 task/PR 分组、消息与 bash 调用检查的代码。新 teacher 分区仍需少量结构核验：工具签名、call/result 对应、system/prompt、完成动作与环境约定、字段级 teacher 开关；同为 mini 并不保证版本和 prompt 完全相同。
2. **教师思考处理须按既有决定另行验收（当前执行仍暂停）**：显式移除 assistant 发布的 `<think>` / `reasoning_content`，保留行动所需内容、正常解释和工具协议。保留源模型与 thinking 标签作为 provenance。新分区清理后 token 分布及成功动作可用性尚未实测，不能沿用旧 Qwen3.6-27B 的长度结论。
3. **训练 / dev 去重与排除先锁定**：对照四项正式 manifest 排除 exact ID，再按当前保守 SWE 仓库排除规则核仓库、fork/派生及任务来源；跨 Qwen3.6 / 3.8 / DeepSeek 的同 PR 只能归同一 split。发布方称底层来源为独立训练池，不等于已完成本项目去污染。`reference_patch`、gold、测试答案等不可进入 policy 输入。
4. **OpenHands 与 Pi 作为后备**：源码和消息确实可参考，但需另做消息、工具、副作用、状态及停止动作适配。不能为了教师较新，未经验证就把 OpenHands/Pi 多工具动作改名为 mini bash。

## 其他线索的处理

`fxiao0369/deepseek-v4-flash-swebench-replay@b8af71521a384aebf0fe400a5b87d8afcbd19554` 确有 EvalScope 的 assistant/tool 评测日志，Verified 500 + Lite 300 共 800 条运行；分别 354/500 与 182/300 成功。但它于 **2026-05-29** 发布，教师仅称 DeepSeek-V4-Flash，不能冒称 0731；Verified/Lite 也可能重叠，不是 800 个独立训练任务。评测日志并非仅因“来自别的 benchmark”就一概禁止训练，仍要按本题正式集、保守仓库和派生排除规则审计；其 `other` 许可与 EvalScope→mini 的成本也须先明确。因此不优先于 NVIDIA 独立训练来源。[固定数据卡](https://huggingface.co/datasets/fxiao0369/deepseek-v4-flash-swebench-replay/blob/b8af71521a384aebf0fe400a5b87d8afcbd19554/README.md)。

`AlienKevin/SWE-ZERO-12M-trajectories` 虽约 1,229 万条，但教师是 `ricdomolm/mini-coder-1.7b`、execution-free、无 verifier，不符合本轮“最新强教师成功轨迹”的主要需求，不应只因体量大而替换现有源。[固定数据卡](https://huggingface.co/datasets/AlienKevin/SWE-ZERO-12M-trajectories/blob/44e028077c55e7255c328516c8bd76080fbb3840/README.md)。

本轮建议是**先核 Qwen3.8-Flash-Next mini 的一小份结构与许可/排除映射，再决定下载和替换比例**；没有执行下载、清洗、train/dev 选题或修改训练方案。
