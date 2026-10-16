# SWE / Terminal执行核查：06:10 heartbeat

已先读最新`claud.md`与`analysis/current_status_20261017.md`。直接采集时刻为 **2026-10-17 06:12:15 CST**；具体源的as-of、PID/startticks、EX锁、scope、marker和小文件身份见[快照](source_snapshots/execution_status_20261017_0610.json)。本轮只读80/HPC和两个服务的GET metrics；没有刷新collector、生成/评分、取新锁、改队列/网络/预算、装产品、启动第二parent或申请GPU。

## 终态与有效覆盖分开

| 队列 | 终态 | 原collector有效 | active / pending | 独立审计层及未决 |
|---|---:|---:|---:|---|
| SWE专家 | 51/51 | 42 | 0 / 0 | 48/51有效、0通过，3未决；旧parent824673已退出 |
| AVG64 SWE | 37/51 | 32 | 10 / 4 | 当时审计文件32，来源为06:09:36的31原生＋既有c1f2审计1；较实时源稍旧 |
| Terminal专家 | 67/445 | 66 | 10 / 368 | 12正确；仅nginx/seed0原invalid，无新增invalid |
| AVG64 Terminal | 66/445 | 66 | 10 / 369 | 12正确；无invalid |

AVG SWE实时原生32与06:09审计文件32不是同一来源时刻；不可把两者误当审计没有作用。本轮没有写新canonical数字。root随后于 **06:14:39** 刷新其两collector及strict/预算汇总，报告覆盖AVG SWE37、AVG HLE2186、两Terminal各68、ASI专家109；这是后续独立时点，未回填本表的终态/active/pending或吞吐分母。所有未完成单项主分及AVG64四项macro仍不由本快照计算。

两Terminal唯一parent分别489933/start868194930、489934/start868194945；AVG SWE唯一parent489978/start868195246，三者均存活并各持自身`.controller.lock`的EX锁。进程inventory没有第二owner。SWE专家的历史model消费结束证明已在，0–9已正式交给AVG；当前这些CPU上的scope属于AVG，不能误认为专家未排空。

## 近57分钟真实吞吐与截止风险

使用05:15:21–23的同源[上轮收据](source_snapshots/execution_scoring_gaps_20261017.json)，对照本次06:12:14的固定ledger。实际窗口约56.9分钟，已经排除迁移、载模和最初填10槽；窗口起止均10 active，因此新增准入数等于新增终态数。

| 队列 | 终态变化 | 新终态 / 小时 | 原生有效变化 | 仍需尝试（含active） |
|---|---:|---:|---:|---:|
| Terminal专家 | 50→67（+17） | 17.93 | 49→66 | 378 |
| AVG64 Terminal | 48→66（+18） | 19.00 | 48→66 | 379 |
| AVG64 SWE | 20→37（+17） | 17.94 | 19→32 | 14 |

Terminal专家若要在核心截止10/18 02:20前收完剩余尝试，余下平均需要约18.78终态/小时，高于该窗口17.93；AVG需18.83，实测19.00只有很小余量。按各自GPU服务EndTime计，分别需19.07/18.99。**完整445仍有风险**，不能用这段不同题型的有限窗口给线性ETA或保证完成；严格有效覆盖还要另处理nginx缺口。

普通服务727912/727913实查均RUNNING、acd_u、ACD1-22、各2GPU，EndTime为10/18 02:01:28/02:09:28。冻结controller要求新题距离service end至少2100秒，对应01:26:28/01:34:28停止新准入；原在途按原预算自然结束。GET metrics专家7 running/0 waiting，AVG11/0，说明服务有实际消费者，没有停在空服务gate。未据此改并发或预算。

## CPU交接没有已就绪却被忽略的marker

两Terminal仍各10槽，scope对应专家12–51、AVG52–91。当前捕获10个专家/9个AVG原生scope均MemoryMax=8GiB；AVG第10个child刚准入CPU84–87、存活且age约0秒，尚未建scope，属于正常setup而非永久空闲租约。AVG SWE的0–9共10个scope各1CPU/4GiB。30个现存native scope的`oom_kill`均0；两SWE scope的memory.max事件只说明触及限额，不等于OOM杀进程，也不能推断已删除的历史Vuls scope。

- **SWE释放stage未就绪**：AVG仍10 active/4 pending，model/all-CPU结束marker都不存在；因此新增专家2槽＋AVG1槽的条件未满足。原专家释放已被AVG消费，没有未利用的SWE释放证明。
- **ASI释放stage未就绪**：专家240条件生成与96–127源scope已正常关闭，但其grader3237024仍占92–95 global锁，真实程序scope存在；expert及AVG两个all-CPU marker均缺。96–127瞬时无scope仍属于后续AVG程序池，不能凭空闲claim给Terminal。
- **AVG ASI复用是有意等待**：唯一watcher4143547已看到专家生成CPU ready，但AVG HLE generator4076145尚在跑、model-consumer marker缺失。watcher显示HLE202来自04:02历史drain summary；真实06:12 checkpoint为本次会话1957完成/50 active。`run_direct_hle_formal.py`在退出后重数所有已有结果并写最终summary，故202不是实时总数，也没有证明它卡在202或忽略就绪gate。

没有发现可按既有marker规则直接领取的额外4核块；10–11只有2核。未来SWE stage可加3槽、两个ASI全部CPU完成后可再加8槽，实际就绪时间未知。本轮没有改变这些stage或资源所有权。

## nginx唯一parent合法等待

851972/start868587717仍存活、affinity10，state=`waiting_shared_cpu_lease`、lock_held=false。锁`artifacts/eval/direct_asi_grader_cpu92_95.lock`（inode90775088）真实EX owner为ASI pipeline3237024；有`ai4sci-submission-b343ee5014ec.scope`在CPU92运行，不能把93–95暂空当整块释放。没有重复claim或第二parent。

12项原source/restore/delta SHA全部不变，独立native目录/result尚不存在，模型与native尝试仍0，正式summary没有接入补评。等锁循环及锁后spawn前均保留距10/18 02:20至少1800秒的准入门；不足则停止新native，不截断已开始的900秒预算。此次没有新的test/restore/两次排空证据可供接纳，继续等待原持久parent。

## AVG SWE新增评分异常与独立审计

既有c1f2仍使用先前唯一批准的AVG审计。其余新增项分别读了**AVG自己的**generation模型、空patch、原replay及原日志，没有照搬专家名单：

| 任务简写 | 原证据 | 本轮处理 |
|---|---|---|
| Vuls5af | 原native null，`RemoteProtocolError: Server disconnected without sending a response`，0B patch；未取得该原scope的确证OOM材料 | 保留null，不能由断连直接判模型OOM或0 |
| Teleport2b | 原native null、`RewardFileNotFoundError`，没有有效reward/测试结果 | 保留null，原因未决 |
| Teleport7744 | 原native0，但`proxy.golang.org/.../netlink/@v/list`发生`i/o timeout`，setup failed、required test缺失 | 继续invalid/null；专家后来同patch恢复不迁用于AVG |
| OpenLibrary630 | 本AVG原native0、exception=null、0B patch、`replay.patch=null`；原task明确要求`openlibrary/core/bestbook.py`，原测试导入缺该产品模块 | 下述exact审计已获root独立批准；本agent未改manifest/collector |

OpenLibrary完整result为：
```text
/data/caoqinlu/projects/apex-takehome/artifacts/eval/avg64_swe_hard51_20261017/replay/instance_internetarchive__openlibrary-630221ab686c64e75a2ce253c893c033e4814b2e-v93c53c13d5f9b383ebb411ee7750b49dcd1a34c6/result.json
```
其SHA256=`a7e0d3360d55558bb58d2708618ea4b98dc27df0fedb8e6f294359669b35f2f2`。快照`avg_openlibrary630_independent_audit.identities`列全路径/SHA：同ID `tasks/.../instruction.md`（72等行要求产品模块）、`generation/.../agent/model.patch`、generation result、`replay/.../agent/replay.json`、原`verifier/{test-stdout,run-script-stdout,run-script-stderr}.txt`、reward.txt及output.json。模型为`openai/apex-avg64`，replay为`patch_replay:PatchReplayAgent`且source_job精确指向AVG generation；原reward.txt0、required9/passed0、output tests空。安全错误证据仅三行：
```text
from openlibrary.core.bestbook import Bestbook
E   ModuleNotFoundError: No module named 'openlibrary.core.bestbook'
3 warnings, 1 error in 0.14s
```

root在直接快照之后重新读取上述原task/候选/native0/日志并明确批准这个**exact AVG原生0**为未实现必需产品模块，非缺runner依赖；审计记录时点06:14:31 UTC+8，root于06:14:39自行修改其manifest并刷新统计。本agent只补批准结论和精确来源，不编辑该manifest、collector或正式summary。其他未审项继续null；审计artifact存在本身不等于已有效计分或整队完成。
