# 旧执行池 CPU 审计回执（备选池）

2026-10-16。用户改为新数据优先后，本轮只收尾已运行的旧池审计，不继续扩池或选样。脚本 [audit_execution_candidates_cpu.py](../scripts/audit_execution_candidates_cpu.py)，聚合回执 [data_audit_execution_20261016.json](source_snapshots/data_audit_execution_20261016.json)。80 单 Python 进程、PyArrow CPU/IO 各 1 线程，340.81 秒；未运行轨迹命令、教师程序、容器、validator、模型/API/GPU。训练正文没有打印或导出，静态解析不代表执行通过。

## Terminal

固定 Corpus `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9` 全 26 片 **139,841 行**，均为 DeepSeek-V3.2 / Terminus-2 / thinking=true。schema 无逐行 result/reward，故成功状态全部 unknown。

- 82,955 个不同裸 task ID；**41,843 个 ID 有多个不同题面**，同 ID 跨 difficulty 不能直接连接环境或分别切 train/val。
- 按 `(domain, bare ID)` 跨 difficulty 联合，并用 whitespace-normalized 题面连接，形成 **82,955 个保守 family group**。这用于防止已知相关项泄漏，不证明这些不同题面是同一语义任务，也没恢复生成模板族。
- 139,815 个不同规范化题面，只有 26 行额外同题面；139,841 个不同完整日志 hash、trial_name。run_id 仅 33 个、episode 仅 37 个，均是采集批次/循环编号，不能当独立任务身份。
- 已有 mixed 六包 5,984 任务；**5,689 行**做到同 difficulty/domain/ID 加精确题面 hash 对应；easy/medium 不因裸 ID 命中而认领 mixed 环境。
- 83,145 行所有 assistant 消息能在清 leading balanced think 后被固定官方 parser 解析；其中与任务包精确对应的 3,906 行。中间 parser 错误可能是有反馈的可恢复错误，这些数字不是最终质量筛除规则。
- 任一完成代理 59,572 行、末动作完成代理 59,023 行；**task_complete 不等于 verifier 成功**。

来源目录类别对应 TB 的 16 类只能视为元数据粗覆盖，不是实际语义重标注：software-engineering 15,559、system-administration 7,776、security 17,010、scientific-computing 19,482、data-science 17,565、debugging 17,382、file-operations 16,096、data-processing 9,287、model-training 214、data-querying 9,535；mathematics / machine-learning / games / personal-assistant / optimization / video-processing 均无直接标签。另有 dependency_management 9,935 行未强映到其他类。此处仅旧来源的原始目录标签，不可沿用为新数据分类。

任务包已对 instruction、task.toml、Dockerfile、environment/files 清单做 hash；没有证明教师实际输入字节、镜像 digest、UID/网络/资源或本项目重建环境等价。之前 sandbox 报告的初始化缺口仍在，**当前不能将这些任务自动标成已验收 task-dev**。

## D3 静态科研程序

固定轨迹 `b21b5006956d7d246cf3e35277b13323780a45b2` 全 **2,153 行**；任务 metadata `8499689ac98882a7cac9b5ef9e93365cc37df57e` 共 565 行，只读 task_id/task_instruction/dataset_previews/original_repo/discipline，未读 eval_script。

- **231 个不同规范化 input**；不同答案不能当不同任务。2,153 个 input+清后 output hash 均不同。
- **2,131 行**通过唯一 task_instruction 原文包含关系映射到 **228 个任务、119 个 source repo**；22 行无可靠匹配，0 行歧义。1,083 行还完整包含 metadata 的全部 dataset preview；其他映射仅确认题目身份，不能声称输入资产一致。
- 同任务多 rollout 按任务聚组，再将同 original_repo 的任务保守归为一族；22 行未映射不能独立进入 task-dev 或被当成可靠隔离来源。
- 来源标签：Chemistry/chemistry 合计 872 行 / 92 任务；Bioinformatics/bioinformatics 488 行；GIS 309 行；Psychology and Cognitive Neuroscience 462 行。后面三个标签保留原名，未猜成 ASI 的 biology/earth_science 等，因此 11 域严格标签交叉表仅 chemistry 有直接供给，其他为未证实覆盖，**不是判断这些学科毫无相邻价值**。
- 2,153 行均有可分离的前缀 think；2,149 行清后至少有一个可 AST parse 的 Python fence，4 行没有。AST 仅检查语法，未执行，不验证输出文件/依赖/科学正确性。
- [作者论文 Appendix E](https://arxiv.org/html/2604.27977v1#A5)报告对各任务采 16 条，仅保留 silver verifier 通过者；公开 3 列 JSON 没有逐行执行回执。继续称“来源报告通过 silver 筛选的静态程序 SFT”，不能称本项目复验成功或 OpenCode 多轮轨迹。

## 长度复用及待核

没有重跑大 tokenization。沿用 [旧长度回执](trajectory_lengths.md)：Terminal 加权样本清后 median 12,694 / P95 22,537；mixed 全量 median 9,937 / P95 17,543。D3 全 2,153 行清后完整序列 median 2,683 / P95 8,300.4，assistant content 代理 median 636 / P95 1,684.4。以上不是最终 ms-swift labels/processed tokens，也不把新教师长度代入旧均值。

未做正式 benchmark 近重复/原仓库同源排除、模板语义聚类、运行环境验收；未产生最终 train/val 或训练文件。新 Terminal 资格结果另记新池报告。80 ignored 行级清单：`artifacts/data/audits/execution_candidates_20261016/terminal_row_family_map.jsonl`、`terminal_task_pack_manifest.jsonl`、`d3_row_task_family_map.jsonl`；hash/字节数见聚合 JSON。
