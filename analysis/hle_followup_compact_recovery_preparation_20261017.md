# 后续HLE compact恢复：名单校验准备

root审阅后授权的最小改动已完成：恢复脚本不再硬编码8，而以config.expected_items验证总数；唯一键为**(model, task_id)**，拒绝重复pair，允许同一task ID出现在两个不同模型。旧config只新增expected_items=8，原模型/任务顺序及恢复语义保持。原grader退出、原controller排它锁、双200+length/原parse失败、原文件备份、独立reservation、unknown不重发及每模型20CNY/5000calls均未改。

12项离线sanity通过：原9项及跨模型同题允许、expected_items不匹配拒绝、重复(model,task)拒绝。另逐项比较旧config与原8项执行收据，名单未变；80默认prepare-only显示原8项都already_reserved/completed，0 eligible、0新网络请求，原budget hash保持。没有再次执行旧恢复。

**partial invalid名单不是final恢复名单。** 06:07安全快照中的AVG64两项、TIES四项仅为当时观察，两个原grader均活跃；当前不创建新恢复config、不取得其恢复锁或发送Judge请求。必须等某模型全量2500且其原grader真实退出，再独立读取最终全部invalid、核原双200+length及frozen parser、固定expected_items/原PID/config；不必等另一模型，但须root审阅后才--execute。快照明确partial_invalid_inventory_only=true、fixed_final_recovery_manifest_created=false，防止把部分候选误作最终白名单。

## TIES自有GPU已正常释放

06:12:19 CST只读核实：TIES已全2500生成，generator887555退出0；原controller782323已退出，最终state为generation_released_scoring_external。consumer marker于**06:11:00.675 CST**写明generation_process_finished、2500保存、native_metrics_zero_before_release=true、job_absent_from_squeue=true、service_expired_before_release=false。

Slurm独立确认728016不再存在；现四个普通TP2共**8GPU**（727912/727913/727856/727857），不是异常丢失服务，无须重建28097。TIES原Judge887556/start868602347仍活，1193有效、4 invalid、1307 pending，继续外部评分；complete=false，不报告最终score。这4项仍只是partial inventory，后续还可能增长。

原AVG HLE→ASI复用28095保持：06:07实际HLE2100+50在途、summary202旧摘要、源ASI生成CPU gate已真，但HLE最终marker/退出未满足，尚未就绪；未操作复用waiter或重新申请已释放727879/28090。

本轮不长等grader；由后续heartbeat在各模型独立关闭时准备固定配置。安全[snapshot](source_snapshots/hle_followup_compact_recovery_preparation_20261017.json)含12项sanity、旧8项prepare-only、partial非final标记、TIES最终释放marker及Slurm证据。无新恢复配置/模型请求/测试/容器/GPU操作，无共享文档或Git写入。
