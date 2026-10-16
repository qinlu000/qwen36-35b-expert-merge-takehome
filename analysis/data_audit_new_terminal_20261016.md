# 新 Terminal 池：实际规模、资格与 48 族人工分类候选

2026-10-16。新数据优先；只读固定来源的 metadata、有限训练输入与轨迹结构，未执行任何轨迹命令、任务代码、容器、validator、模型/API/GPU。未导出训练格式，所有候选保留 `training_released=false` 和质量待核状态。脚本 [audit_new_terminal_cpu.py](../scripts/audit_new_terminal_cpu.py)，聚合 [data_audit_new_terminal_20261016.json](source_snapshots/data_audit_new_terminal_20261016.json)。旧 Terminal/D3 仅作为 [已完成备选审计](data_audit_execution_20261016.md)。

## 1. OpenThoughts 100K 的卡片信息与实际数据分开

固定 [数据卡](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K/blob/45fb28fcc38d352133cb28a1c8a43a2f14fea97b/README.md) 明确 Apache-2.0、GLM-4.7-AWQ、Terminus-2/Daytona、至少 5 个 model turns，以及 SWE-Smith/SuperUser/Tezos/IssueTasks 四来源。后者不是 TB16 分类，也不是逐条环境/成功保证。

实际固定 **10 片共 94,334 行**，不是 100,000 条独立成功任务。全池 agent 均 `terminus-2`，model 均别名 `hosted_vllm/glm`，没有逐条精确权重 revision。卡片给出的教师身份是作者声明，行字段本身只提供别名。

| 全池字段 | 实测 |
|---|---:|
| trace_source=main | 75,879 |
| summary/answers 辅助轨迹 | 6,560 |
| 缺 trace_source，角色待核 | 11,895 |
| result=None | 60,296 |
| AgentTimeoutError | 32,764 |
| ContextLengthExceededError | 916 |
| 其余 Daytona/运行/取消类异常 | 358 |
| 数值 reward | **0** |

`trace_source` 的实际值是 main/summary/answers/空，**并非卡片表格所写的四个任务来源**。作者 [analysis.utils.extract_reward](https://github.com/open-thoughts/OpenThoughts-Agent/blob/3bd1917e62c9d03d73063b433f5c442c279c0563/scripts/analysis/utils.py#L580) 将 result 数值作为 reward，其他字符串不可解析成 reward；这是当前固定作者辅助源码，不是本次已取得原 collector 的完整运行配置。**None 不代表失败，也不代表成功；全部缺独立的数值 verifier 依据。**不得把“没有异常”“task_complete”“至少 5 轮”当通过 grader。

元数据 task 形如 `swesmith-31327_copy0002`，不是题目正文。剥离 `_copyNNNN`，同原 task 的副本、多 rollout 和摘要联合归族，并合并已检查同题面，形成 37,186 个保守族；有 main 的约 33,277 族。源 repo/原问题 URL/生成模板的完整映射未恢复，不能称这些都是已证明独立的任务环境。源级 Apache-2.0 也不能替代 StackExchange 等上游题目归属要求。

## 2. 有界读取和结构检查

- 完整下载且核 LFS SHA256 的仅第一片：241,281,937B；SHA256 `9dd61d89da1c52ec84607ae925150471def1628a2d63237cfdd897ef50860888`。
- 其他片只用严格检查 HTTP206/Content-Range 的 Range 取得 footer 和轻元数据块；全 10 片这部分共 **4,652,195B / 70 次 Range**。sparse metadata 文件不是完整分片，不能套全文件 LFS 校验。
- 第一片正文检查前 3 个完整 row group，共 5,736 行；这是有序 SWE-Smith 段，**不是全池随机质量/长度估计**。其中 4,392 行所有 assistant 消息经清闭合前缀 think 后可由固定官方 parser 解析；3,394 行有完成代理。检查 112,557 个 assistant 消息，1,901 个 parser 错误，112,247 个有前缀 think；中间可恢复 parser 错误不自动决定整条失败。
- 为覆盖另外三个来源，补读第 5 片 RG0（31,215,918B，含 SuperUser+IssueTasks）和第 7 片 RG4（21,406,488B，Tezos），**附加正文合计 52,622,406B < 64MiB**。只挑每来源最多 12 个 main 独立族作输入人工标注，不扩大正文。
- 用固定正式 TB89 的 NFKC/空白折叠/casefold 题面 hash 做 exact 排除。已读输入零命中；这不证明剩余 metadata-only 样本、改写、同源仓库或语义近重复无污染。
- 本轮未对新池重新 tokenize；不套旧 Nemotron 的长度均值，不把清后字符数/assistant 内容量当 ms-swift 的最终 labels 或 processed tokens。

## 3. 48 族人工类别标注及候选分区

从 SWE-Smith、SuperUser、IssueTasks、Tezos 各选 12 个 main 族，共 **48 族**；按确定的 family hash 排序，不按最短轨迹挑选。样本限定 source result=None 是为了先检查未记录异常者，**不表示筛出成功示范**。

分类是本项目人工 annotation：`annotation_method=project_manual_task_instruction_v1`，有逐题 `confidence` 和简短 `evidence`，不是发布者/官方 TB 标签。规则：库/项目修复、实现、测试工作流归 software-engineering；独立脚本/运行错误诊断归 debugging；文件操作、服务/系统配置、查询、ETL、数值运算和认证按主要交付物标注。交叉任务给 medium，不为凑覆盖改变主类。

已见类型包括：文件批量改名/拼接/归档，内核模块与 Apache 配置，离线 CSV ETL，Monte Carlo 方差计算，认证 CLI，仓库修复，节点运维与 API 查询。没有把整个 SuperUser 或 Tezos 来源直接映射为单一 TB 类。逐族标签/依据和 train/val 分类计数见聚合 JSON 的 `manual_annotation`。

全局候选分区复用 `SPLIT_SEED=apex-new-data-v1-20261016`，按任务族 hash 约 90/10；**这是 metadata reserve，不是最终可执行 val 的规模**。同族所有副本/摘要共同分区，每族 main 先保留一条代表，优先数值成功（本池无）、无异常、已检查的解析一致性与完成代理，再按文件/行确定性打破平局，不偏好短/易题。

保留三层回执：全行/家族映射；全部 main 家族的待核 reservoir；48 个已人工标注族的待核清单。后续可按 TB89 比例从已标注池抽一个可审阅 core，并明确无供给类别/缺口。**不能把这个有序、少量、四来源均取 12 的审阅池说成已经匹配全池或 TB16 的分布。**

## 4. 环境和质量缺口继续显式保留

训练输入里有 Windows10 图像转换、Mac EFI 双启动、真实链节点/合约/交易/API 请求；公开 Terminus 名称不证明这些情景已在目标 Linux sandbox 中恢复。部分 IssueTasks 是自包含 mock/玩具项目，领域相邻不等于与真实仓库/benchmark 环境同分布。当前没有恢复逐族 task binary、初态输入、依赖、权限、网络与 verifier。

因此 48 族可作为可审阅分类候选，但 **0 行被本轮称为训练质量验收，0 个 task-dev 环境验收**。缺 verifier 不意味着轨迹全部失败；质量 hold 是证据状态，后续可少量核原环境/结果或采用明确披露的非成功筛选，而非无期限等全池元数据补齐。

## 5. GLM-5.2 Terminus 新线索

固定 [vanilla](https://huggingface.co/datasets/open-athena/nemotron-gym-multichallenge-vanilla-v2-glm52-terminus2-traces/tree/ef4c2f32a99b195859527d8a3a90aa3331d22aa9) `ef4c2f32a99b195859527d8a3a90aa3331d22aa9` 与 [advanced](https://huggingface.co/datasets/open-athena/nemotron-gym-multichallenge-advanced-v2-glm52-terminus2-traces/tree/6bfd72688ec08c3eb1b88ba2bb592d45944348b0) `6bfd72688ec08c3eb1b88ba2bb592d45944348b0` 各 6 片。只读各片 footer 64KiB，共 786,432B，实数各 **1,045 行**。schema 有 conversations/agent/model/task/result/instruction/verifier_output；schema 中存在 model/result 字段不证明具体身份/成功语义。

两项固定 API 仍无 README/card/license。本轮不读行正文，不凭 repo 名放行 GLM-5.2 教师或训练许可，不进入 train/val。

## 80 ignored 回执路径

统一根：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/new_terminal_20261016/`。

- `summary.json`：聚合；`all_row_family_map.jsonl`：全行身份与状态。
- `train_candidate_hold.jsonl` / `val_candidate_hold.jsonl`：每 main 家族一条的待核 reservoir。
- `annotated_train_candidate_hold.jsonl` / `annotated_val_candidate_hold.jsonl`：已人工标注 48 族；分类 `target_category`，分区 `candidate_partition`，身份 `family_key`，依据 `annotation`，状态 `training_released`/`hold_reasons`。
- `annotation_candidates.jsonl`、`manual_annotations.json`：有限原训练输入审阅与标签，不入 Git；`additional_body_range_receipts.json`：附加正文范围与 hash。
- `raw/ot100k_api.json`、固定卡、`raw/metadata_sparse/*.receipt.json`、`raw/athena_fixed_footer_audit.json`：来源/范围回执。全部摘要清单 hash 见聚合 JSON。
