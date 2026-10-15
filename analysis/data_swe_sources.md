# 修复专家的数据来源与分工调研

核验日期：2026-10-15（Asia/Shanghai）。仅检查作者论文、官方仓库文档、HF 数据卡与 schema/版本元数据；未读取本题逐题答案、参考补丁、隐藏测试，未下载 Parquet/权重，未写实验代码或跑实验。下述数据都仍是候选，不等于本项目已经完成去污染或许可审计。

## 建议与范围

修复专家应学“读仓库→定位→修改→执行验证→根据报错恢复”，主来源需要真实多轮 assistant/tool 轨迹。建议将 **NVIDIA Open-SWE-Traces 的 mini-swe-agent 分区升为第一审计候选**，SWE-smith 现成轨迹作为小比例补充；SWE-Gym 491 条作为兼容性备选。不要把 SWE-smith 新多语言任务环境误当作现成 SFT 数据。

修复专家负责代码仓库任务；终端专家负责环境、命令、文件与系统工作流。科学计算中的代码也可以由科学专家负责，但同一训练任务只能计一次，避免多专家仅重复同批轨迹。专家不是按 Python/Go 等语言再拆分；在修复专家内部覆盖 Go、Python、JS/TS 即可。这个分工是本项目建议，尚待讨论确认。

## 1. 第一审计候选：Open-SWE-Traces

- 作者官方数据：`nvidia/Open-SWE-Traces`，revision `1db674173119d71df45c22007af99e214600711a`，最后修改 2026-10-13，CC BY 4.0。明确提供 `repo`、`license`、`language`、`instance_id`、`trajectory_id`、`messages`、`tools`、`resolved`。成功标签取 1/0/-1，不能把 -1 当作失败或成功。[固定卡片](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)
- 当前公开配置含 v1.0/v1.1/v1.2。v1.1 有 Qwen3.6-27B 的 mini-swe-agent；v1.2 有 Qwen3.8 系列。优先比较 mini 分区与我们官方 `LockedMiniSwe` 的工具 schema、观察格式及结束动作；同框架谱系只意味着更值得检查，不证明可以直接替换工具名。[配置卡片](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[本题工具配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)
- 官方分布表：v1.0 经 git-hacking 清理后为 151,219 条；v1.1 共 263,226，其中 mini/Qwen3.6-27B 95,291；v1.2 共 263,371，其中 mini/Qwen3.8-27B 107,267。不能继续把摘要旧版 207,489 写成当前版本规模，也不能把版本/教师/框架条数当成独立 PR 数。[分布表](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/data_distribution.md)

**质量与边界。**保留成功标签仍不够：必须检查工具闭合、截断、最终产物、过长空转、git/网络取答案，以及数据卡标签和执行日志是否自洽。v1.0 公开做过 git-hacking 清理，不能因此推断每个后续版本或所有作弊方式均已被覆盖。上游包中 `metadata.reference_patch` 是原训练任务参考补丁字段，必须和 assistant 监督内容分开管理；任何与本题正式任务关联的记录整组排除，不从正式参考材料构造匹配器或训练目标。

**方法参考。**作者在 Qwen3-30B-A3B 上比较多语言/单语言、跨 harness、resolved-only/full：多语言有效，跨框架有代价，保留未解决轨迹在其设置下优于只保留成功轨迹。因此不应宣称“success-only 已被证明最好”；本项目若先用成功轨迹降低小样本审计成本，应明确这是时间与质量控制的选择，不能归因于论文证实。[论文与消融](https://arxiv.org/html/2606.16038v1#S4)

该论文评的是旧 731-task SWE Pro，训练最长 131K、3 epochs；与我们 Qwen3.6、LoRA、8K 分段、HARD-51 locked V2 不同。可借鉴数据组织，不能照搬其分数或声称四卡已复现。[实验设置](https://arxiv.org/html/2606.16038v1#S3.SS1)

## 2. 污染资格检查是主源选择的前置条件

Open-SWE 卡片列出上游 Scale-SWE、SWE-rebench-V2。**它们没有给出本题四项评测均已去污染的保证。**

- SWE-rebench-V2 的固定卡片明确警告：只排除了原始 SWE-bench 仓库，没有显式过滤其他 benchmark，要求训练前自己检查交叉。revision `10483de0f50fe5da545942705a76c6150171af7f`（2026-10-01），CC BY 4.0，逐 repo 原许可仍生效。[作者警告](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)
- Scale-SWE 是 AweAI/RUC/ByteDance 的独立数据项目，名称不意味着它与 ScaleAI 的 SWE-bench Pro 是同一个发布方。作者论文 §2.2 声明排除 SWE-bench Verified 仓库；没有据此证明排除了 SWE Pro。[作者论文 §2.2](https://arxiv.org/html/2602.09892v1#S2.SS2)、[Scale-SWE 固定卡片](https://huggingface.co/datasets/AweAI-Team/Scale-SWE/blob/d8db20390a936bbda9c96d88b97cc4778dff1481/README.md)

建议本项目采用便于审计的保守规则：先根据允许使用的公开来源元数据排除 SWE Pro 全部 11 个评测 repo 及其 forks/镜像/改名映射，排除四项评测的任务 ID、PR/commit、衍生来源；不只排 HARD-51 的 51 个 ID。其余训练池按 canonical repo、PR/instance、来源任务家族分组，所有教师、框架、同题重复 rollout 和跨数据集拷贝一起分配。先分 train/train-dev/merge-dev，后做分段与抽样。这个规则是本项目建议，尚未执行；也不能完全证明不存在语义派生污染。

## 3. SWE-smith：现成轨迹与多语言任务要分开

**现成轨迹。**`SWE-bench/SWE-smith-trajectories` revision `08e109b4a59eaeebf80e4675cd125d42e7ac99a4` 仍为 2025-07 发布，MIT，提供 messages、instance_id、resolved、model、traj_id；tool/xml/ticks 是不同 action 表示，不能三份堆叠。主论文年代的数据主要来自 Python 任务。适合补充可追溯、经执行成功的合成 bug 修复，不宜单独代表本题多语言长程需求。[轨迹卡](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/blob/08e109b4a59eaeebf80e4675cd125d42e7ac99a4/README.md)、[作者论文](https://arxiv.org/abs/2504.21798)

**最新 language-specific 发布仅有任务 schema。**以下元数据均只有 `instance_id/patch/FAIL_TO_PASS/PASS_TO_PASS/image_name/repo/problem_statement`，没有 messages 或 rollout 成功字段；所谓“validated”指合成任务的测试条件，不等于有成功 agent 轨迹。

| 发布 | train 条数 | revision | 数据卡许可 |
| --- | ---: | --- | --- |
| [Python](https://huggingface.co/datasets/SWE-bench/SWE-smith-py/blob/77cab9055d42ab4a5c25c89a8f937096db13558e/README.md) | 50,908 | `77cab9055d42ab4a5c25c89a8f937096db13558e` | MIT |
| [Go](https://huggingface.co/datasets/SWE-bench/SWE-smith-go/blob/d2f6ecc2cf8ae1af00fc790801bbacfa2913e015/README.md) | 8,212 | `d2f6ecc2cf8ae1af00fc790801bbacfa2913e015` | MIT |
| [JavaScript](https://huggingface.co/datasets/SWE-bench/SWE-smith-js/blob/d6aeb41ba9fb045c39e1c6d2322a8f08ee31cef4/README.md) | 6,073 | `d6aeb41ba9fb045c39e1c6d2322a8f08ee31cef4` | 未显式声明 |
| [TypeScript](https://huggingface.co/datasets/SWE-bench/SWE-smith-ts/blob/c243d86f112d01b8507d311af912668aa1d74449/README.md) | 5,032 | `c243d86f112d01b8507d311af912668aa1d74449` | 未显式声明 |
| [Java](https://huggingface.co/datasets/SWE-bench/SWE-smith-java/blob/1172df9919a8232e066562dfdb6e0193156de0c4/README.md) | 7,470 | `1172df9919a8232e066562dfdb6e0193156de0c4` | 未显式声明 |

代码仓库 MIT 不自动填补 js/ts/java 卡片的许可缺项，上游 repo 的许可还要逐项保留。作者 JS 更新介绍的是先生成故障、再执行验证；需要另跑 teacher rollout 才能得到 agent SFT。当前截止时间不建议从这些环境重新大规模采样。[作者更新](https://www.swebench.com/post-260113-swesmith-javascript.html)

## 4. SWE-Gym / OpenHands：小型备选

`OpenHands-SFT-Trajectories` 的固定发布是 491 条成功消息轨迹，MIT，但只公开 messages schema，缺显式 instance_id，可靠来源映射未恢复前不作为主数据。`OpenHands-Sampled-Trajectories` 有 6,055 条，提供 instance_id、run_id、resolved、messages、tools、test_result，更方便追溯；其卡片没有显式许可声明，不能直接继承其他发布 MIT 当作已解决。两者工具动作也须对齐 LockedMiniSwe。[SFT 卡](https://huggingface.co/datasets/SWE-Gym/OpenHands-SFT-Trajectories/blob/4aaa5a4a4b5861f4799d2336908760c190ac3b17/README.md)、[raw 卡](https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories/blob/baf3a4e4bff514d48ddc08a93a2ade5c126212c7/README.md)

## 5. 对训练配比与数据处理的具体建议

1. 先把 Open-SWE mini 分区通过来源、许可、工具及污染资格审查，再确定是否作为主源。候选起点是同系列 Qwen3.6 的 v1.1；v1.2 thinking 数据可比较但不是因版本更新就自动更好。没有真实 token 统计前不报固定能装下多少条。
2. 修复专家内部先用 Go/Python/JS-TS 的多语言混合，避免 Python-only。SWE Pro 官方全量 V2 是 Go 256、Python 237、JS 145、TS 4；这是全量公开概况，不是 HARD-51 的分布。可以据此确认多语言必要性，不能用正式分数反复调语言比例。[官方数据卡](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/blob/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50/README.md)
3. 预算以输入 processed token 与新增 assistant 监督 token 分别记录。长轨迹按工具轮切片、保留必要文件内容和任务约束，不能仅硬截前 8K；历史前缀只做上下文，不重复计入监督。若无法在 8K 内保留动作的必要依赖，丢弃该片段或留到更长上下文方案，不伪造观察结果。
4. 对成功完整轨迹保留中间失败命令与修复过程。整条 unresolved 轨迹是否加入，是独立设计选择，不能把负面终局当正确最终答复；先看独立 dev 的恢复能力与工具成功率，不依据 HARD-51 反馈选择。
5. 主源加补充都按 canonical repo+PR/instance 去重并限制每任务教师/rollout 数；专家训练并集和混训对照必须使用相同最终片段与出现次数。不要用更多重复数据让混训或某专家隐性获得更多预算。

**尚未完成。**未检查逐条 messages、工具 schema 的实际差异、训练可用语言比例、supervised token 数、上游逐文件许可或四榜来源交叉；没有声称已获得一个可直接开训的数据集。可复用的是公开轨迹与字段，仍需我们实现轻量的 manifest/规范化/分组/切片与资格审计。OpenThoughts-Agent-SFT-100K 的 SWE 分区由主线另外核验，和 SWE-smith 补充源必须做跨源任务去重。
