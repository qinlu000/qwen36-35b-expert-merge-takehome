# 执行队列只读检查（05:07请求）

实际采集时间为 **2026-10-17 05:09:33 CST**；后续只补读原异常与SWE原日志，不刷新或改动队列。完整小型[JSON收据](source_snapshots/execution_status_20261017_0507.json)保存来源、父/worker进程、普通作业、原生请求计数及CPU scope。未启动模型生成、verifier、容器、训练或新GPU；未改网络、CPU租约、主配置和原始结果。

| 队列 | 固定总量 | 终态 | 原生有效 | 正确/解决数 | active | pending | 近60分钟终态 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Terminal专家 | 445 | 46 | 45 | 9 | 10 | 389 | 16 |
| AVG64 Terminal | 445 | 45 | 45 | 9 | 10 | 390 | 18 |
| AVG64 SWE | 51 | 16 | 15 | 1 | 10 | 25 | 11 |

三者主分仍null，表中分子不是完整成绩。父进程489933/489934/489978均存在，worker在途；新普通服务727912/727913均RUNNING于acd_u、ACD1-22，各2GPU，截止分别为10月18日02:01:28/02:09:28 CST。服务原生请求running为7/12、waiting均0；这些是只读/metrics计数，不是生成请求。

Terminal专家唯一invalid为`nginx-request-logging/seed0`：04:13:14 CST原运行在切换verifier网络前拒绝继续，精确错误为`Refusing public network after unconfirmed solver cleanup`，来源`baseline_singularity.py:58`。verifier尚未开始、raw reward null；此事发生在普通替代服务前，不能归因新服务，也不能套900秒verifier计算超时规则或自动计0。专家33项、AVG35项AgentTimeoutError已有有效原生reward，属于有效0/1结果而非新增invalid。此快照未见已终态OOM/context invalid。

AVG SWE唯一invalid为Ansible c1f2：原fresh replay reward0、无Harbor异常、空patch，原日志明确缺少任务应交付的`ansible.modules.network.f5.bigip_message_routing_route`，由empty-tests audit门槛保留未决。它与专家已审计同题有相似因果证据，但必须按AVG自己的exact result/patch独立批准，不套专家白名单；本次没有改判或自动0。

CPU交接没有“marker已就绪却不准入”的证据：Terminal仍用各10槽自有池，SWE完成marker尚未产生且其10个消费者仍活跃；两份ASI all-CPU marker也未产生。专家ASI随后只读progress为193/240完成、8 active（05:09:47 CST），AVG ASI尚无progress。旧merged coordinator保留03:53的paused状态，不能当作其他owner新resume driver的实时清单。模型生成期间没有正在执行程序scope，也不构成永久释放证明。

近60分钟含停止准入、排空、重新载模的迁移空窗；04:35续跑后两条Terminal各新增9终态。按最近一小时简单外推，专家剩399项约需24.94小时、AVG剩400项约22.22小时，超过剩余20.87/21.00小时。此为真实窗口风险，不是ETA；后续SWE/ASI释放增加槽位、题目难度和verifier用时都会改变速度。当前AVG SWE剩35项，按该窗口11项/小时约3.18小时；也不是完成承诺。本次不提前扩CPU或改预算。

SWE专家独立审计仍48/51有效、51终态、active/pending空、0 resolved，三个缺口没有新增足够证据可批准：

- **NodeBB8168**：3000秒VerifierTimeout；仅`reward.txt=1`，无output.json/原生测试结果，保存stdout只到应用test patch并以`Terminated`结束。删除.mocharc的退出选项是线索，来源和超时因果仍未闭合，继续null。
- **Vuls5af1**：RemoteProtocolError，无reward/测试结果；此前原CPU6 scope在03:28:13 CST有OOM记录，victim及归因未定。空patch不足以支持自动0，继续null。
- **Teleport2b152**：3000秒VerifierTimeout，无reward/output.json，stdout仅应用官方测试patch；没有确证失败的测试结果，继续null。

逐项原result/patch与现存verifier文件均在收据中；[已有剩余审计](swe_remaining_scoring_audit_20261017.md)和原OOM证据保持原样。没有新可追加native0建议，没有重新评分或清理原资产。
