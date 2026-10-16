# 普通分区迁移与 GPU 用量

用户要求降低优先级、停止使用 emergency，并确认 HLE 50并发。最初仅设置Nice1000只改变同分区的调度分数，不能降低分区PriorityTier；这是需要明确区分的两件事。本集群普通 `acd_u` 与 emergency 使用同一节点集合，PriorityTier分别100/300。运行中作业不能原地修改分区，须排空请求后重提，见[Slurm官方说明](https://slurm.schedmd.com/faq.html#job_size)。

所有新服务默认 `acd_u / Nice1000`。迁移仅停止新题、让在途题完整预算结束；逐套先释放原2GPU，再申请同规格普通2GPU，核实模型与协议后继续未准入ID。已经保存的答案、原始失败和判分保留。新服务不延长原结束时间，且不晚于10月18日02:20核心窗口。没有把每题64K/8K、CPU/RAM、solver或verifier预算缩短，也没有恢复独立val。

## 12卡从何而来

当前六个TP2副本：Terminal专家、AVG64 SWE＋Terminal共享、ASI专家、HLE专家、AVG64 HLE、Mixed883／AVG16轮流使用的一套对照。各2张H100，共12张。这是重复加载同一基座换取并行度的安排，不能称为模型硬性最低需求。HLE原生生成器和服务均已固定50并发，三个活跃模型各自50，Mixed与AVG16串行；续跑会话的completed计数会重新从0开始，整体已保存回答须看questions目录或最终summary，不能误报进度倒退。

用户在另一会话明确释放的727113与727654共4张保持释放。原合版ASI等待parent已停止、没有题目准入，不重新申请它的独立GPU。待专家ASI释放生成CPU、AVG64 HLE全2500生成排空且原生模型running/waiting均0后，复用已在普通分区的AVG64 HLE副本跑合版ASI。该复用控制器不执行sbatch，见[启动收据](source_snapshots/merged_asi_hle_service_reuse_20261017.json)和[补充空闲检查](source_snapshots/merged_asi_hle_reuse_idle_guard_20261017.json)。

HLE专家全2500生成结束及Mixed／AVG16都全2500生成结束后，各自2卡会由独立watcher在确认原生请求归零后释放，使当前用量从12降到8；外部API grader继续工作。AVG64 HLE副本在复用的ASI240生成完成且worker池/请求排空后也释放。见[释放watcher](source_snapshots/normal_hle_service_release_20261017.json)。

## 已部署的持久控制器

| 控制器 | 80上状态根目录 | 作用 |
|---|---|---|
| HLE迁移 | `artifacts/eval/hle_normal_migration_20261017` | 三套服务排空、普通重提、保留原grader、恢复未开始题 |
| ASI专家迁移 | `artifacts/eval/asi-acdu-migration-20261017` | 只暂停原parent提交，原workers自然结束；普通服务验收后恢复同parent |
| Terminal／AVGExec迁移 | `artifacts/eval/execution_partition_migration_20261017` | 两组独立等待原parent和CPU scopes排空，再普通重提和续跑 |
| 合版ASI复用 | `artifacts/eval/merged_asi_existing_hle_service_20261017` | 等专家CPU与HLE生成结束，复用28095；不申请GPU |
| 完成服务释放 | `artifacts/eval/normal_hle_service_release_20261017` | 根据完整模型消费者marker及原生空闲指标释放已结束副本 |

这些程序均在80常驻，不依赖笔记本SSH连接。实际PID、作业ID、分区、stage、队列计数和错误以[最新机器快照](source_snapshots/ordinary_partition_handover_20261017.json)及各目录实时state为准；启动driver不等于迁移完成。任一 `failed`／`needs_attention` 必须保留原因并检查，不能直接重提同名作业或重新生成答卷。

HLE三套普通替代服务已真实运行：727855（专家，ACD1-1）、727856（AVG64，ACD1-20）、727857（对照，ACD1-30）；原727821/727822/727831已退出。Terminal／AVGExec等待各自原在途收尾；ASI专家原138个已准入condition自然终态后，旧727643已释放，普通727879（ACD1-8）正在加载，验收后恢复同parent2752099。workers未收到信号，不写伪完成marker。各组不同阶段不能笼统写成全部已切普通。

## 评测环境问题另记

真实Terminal探针已证明：本实验的 `no-network` solver策略会使PyPI／Ubuntu DNS失败；同沙箱public模式可以成功，Base、专家与AVG使用相同断网overlay。这不是HPC分区导致。用户了解三组均从正式Base起采用该设置后明确“那不用改了吧”，本轮保持既有网络协议；不改变生产策略、重生成旧答案或重算原分，报告披露这一额外限制及其潜在影响。详见[网络诊断](terminal_network_diagnosis_20261017.md)。
