# AVG16 HLE判分收尾资格快照

**2026-10-17 07:15:45 CST**只读核查：AVG16全目录2459/2500终态、41条已准入请求仍在途；generator **485903/start868175753**、原grader **485904/start868175753**均活。generation summary与model-consumer-finished均未写，尚未达到收尾条件。本轮只保存[snapshot](source_snapshots/avg16_hle_scoring_preparation_20261017.json)，不长等、不写stop/collector/API，也不固定最终compact恢复config。

原scorer的07:15:28摘要为2455 frozen、2454有效、1 Judge invalid、46 pending；selection另有1 generation_protocol_invalid。当前1192份已冻结answer均已有terminal结果（1191 judged+1 invalid），1193预算行均settled（1191 completed+2 failed_full_reservation），账1.2437565 CNY。**这不能允许提前stop**：41条在途仍可能产生新answer；当前invalid名单只是partial，不能用于最终恢复白名单。

实际CLI来自`artifacts/eval/avg16_hle2500_20261017/task_control_launch.json`，解释器原文为`/data/caoqinlu/projects/apex-takehome/artifacts/envs/hle/bin/python`，脚本`score_direct_hle_formal.py`，原retry/output指向AVG16目录，参数`--max-cny 20 --max-calls 5000 --workers 2`。snapshot完整保留这个保存的argv，未resolve解释器或安装包。

既有ReadTimeout边界仍仅`6720066a447f1bb0370f36b1`：300.0061秒，prompt1232，无raw/usage/infra，原record SHA256 **c1a81d103a5497677ce638bbc9052726b2e20cba085aad0874d79c775db40c97**，本轮复核未变。后续可复用root已批准的统一兼容规则：显式infra先拒，TimeoutError/ReadTimeout且>=299、无raw才认原预算无答案；不改原record、frozen source、parser或criteria。须等2500终态及全部answer判完，再由root核无inflight/unknown，走既有stop gate自然退出、原CLI collect-only、固定最终双length4096名单并defaultprepare。本轮未写实际intent或执行上述动作。

TIES待讨论项单列：`672d8b9b504a98f0e4799ae0`原两响应均HTTP200/stop/79token，JSON缺必需的`correct`，因此不在既有双length4096的一次compact例外内。root已完成其他6项，但这项继续null；不从其余字段猜标签、不改变frozen parser或擅自扩恢复资格。任何是否纳入新的统一schema恢复政策，留待root讨论决定。

仅新增本文件和对应snapshot；没有共享文档/Git、模型/服务、任务答案、原评分或GPU申请变更。

## 07:18:55复查

全目录已2492/2500、339/342图终态，剩8条已准入请求在途；原generator485903及grader485904仍活。最新scorer摘要2489frozen、2488有效、1 Judge invalid；1198个当前冻结answer均已有terminal结果，1199账行全settled（1197 completed+2 failed_full_reservation）。ReadTimeout仍exact1条，原SHA与前述binding一致。尽管当前answer已判完，8条在途仍可能新增answer，尚不具备stop/collect资格。

唯一当前候选`6725fbd80aae355a51195cca`原两响应已只读复核HTTP200/length/4096completion、frozen parser均JSONDecodeError，身份与既有规则一致；它仍是partial候选，未固定最终名单或创建compact config，也未运行defaultprepare。

727857仍为普通acd_u RUNNING；28096 metrics显示8running/0waiting。releasewatcher3321991/start868018087活跃，Mixed+AVG16合计5000 consumer marker尚无，因此它尚未释放controls服务符合gate。没有重建或另申GPU。更新后的snapshot保留07:15观察摘要及这次完整小元数据；本轮不长等。

## 07:21:54全量关闭与root收尾资格

AVG16已于**07:19:49**完整生成2500（342图），1198完成、1302失败；全目录0在途，原generator485903退出。Mixed+AVG16合计5000 marker随后写入。releasewatcher于**07:19:59.534**确认metrics running+waiting=0并释放727857；07:21 Slurm独立确认该job消失，当前727912/727913/727856三TP2共**6GPU**，不重建controls服务。

原grader485904/start868175753仍活，因旧classifier不认那1条ReadTimeout而停在2499frozen。当前1198 answer全部terminal（1197 judged+1 invalid），2499inputs=2499results；1199预算行全settled（1197 completed+2 failed_full_reservation），1.2532275 CNY，无reserved/unknown；stop尚不存在。该状态满足root采用既有stop gate自然退出、原HLE venv同参数collect-only的资格；本agent不写stop、不执行collector。

ReadTimeout仍exact1条旧SHA，live classifier为已批准608c5d6a…，frozen source仍148721d6…；没有引入其他infra零分。全部answer已关闭后的最终Judge invalid仅`6725fbd80aae355a51195cca`，原两响应HTTP200/length4096、相同Judge身份、frozen parser均JSONDecodeError。

已写[固定1项config](../configs/eval/hle_compact_judge_recovery_avg16_20261017.json)，expected_items=1、原graderPID485904、20CNY/5000calls合并cap、每项仅加1次及unknown不重发均沿用现脚本。**07:21时尚未defaultprepare**：须先等root自然stop及collect-only到2500；再复核最终集合并取得原排它锁，完整核原消息/solver bytes/预算。后续结果见下，execute仍由root另行批准，本agent不发API。

## 07:22:49 defaultprepare通过

root先完成既有stop gate自然收尾和原HLE venv collect-only，并保留原6份元数据及ReadTimeout record/source binding。随后本agent只读确认485904退出、2500frozen、最终invalid恰固定1项，再运行默认prepare：原controller.lock排它取得，原双响应/identity/冻结criteria与user/solver bytes/parser全部通过，**0网络请求**。

[原输出receipt](source_snapshots/hle_avg16_compact_preparation_20261017.json)记录原1199calls/1.2532275 CNY，保守新增1次reservation后1200calls/1.26528525 CNY，低于5000/20总cap；原budget SHA仍c3b8f9e4…、frozen source仍148721d6…。没有创建恢复请求、备份或账本，也未execute；后续实际一次恢复由root审核决定。727857已释放且当前6GPU，不为外部Judge重建GPU。
