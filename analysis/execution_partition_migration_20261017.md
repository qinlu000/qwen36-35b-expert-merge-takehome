# Terminal / AVGExec 普通分区迁移

用户明确不再使用 emergency，运行作业也不能原地改partition。本次只迁移727640（Terminal专家）与727660（AVG64 SWE+Terminal），采用**停止新题、在途完整预算收尾、释放旧2GPU、再申请普通2GPU**的顺序；不处理其他agent的HLE/ASI服务。

## 当前实际状态

80持久driver最初于 **2026-10-17 04:04:45 CST**启动，原PID **3320283**；**04:09 CST**在两组均为`waiting_original_consumers`且尚无drain proof、取消或提交意图时，仅替换迁移driver为当前PID **3421568**，移除`--time-min`。原求解parent/worker未收到信号。工作目录为`/data/caoqinlu/projects/apex-takehome`：

- 状态：`artifacts/eval/execution_partition_migration_20261017/state.json`，每组另有`terminal250/state.json`、`avg64_execution/state.json`。
- 日志：同根`driver.log`；初次启动记录`driver-launch.json`保留，换driver记录`driver-restart-no-time-min.json`另存；原parent argv、启动标识与必要环境白名单保存在`launch_context.json`。
- driver代码：[migrate_execution_services.py](../scripts/migrate_execution_services.py)；固定配置：[execution_partition_migration_20261017.json](../configs/eval/execution_partition_migration_20261017.json)。

04:05初次实际状态为`waiting_original_consumers`：专家Terminal 7 active /30 terminal /408 pending；AVG Terminal 10 active /26 terminal /409 pending；AVG SWE 10 active /3 terminal /38 pending。三个output已写本次owner的`STOP_ADMISSION`，pending保持停止准入时的数量，原在途继续结束。旧两服务尚未取消，新GPU作业尚未提交；**此时不能声称迁移已完成**。初始执行/CPU修复核验见[setup收据](source_snapshots/execution_partition_migration_setup_20261017.json)。04:09换driver收据见[restart收据](source_snapshots/execution_partition_migration_restart_20261017.json)：当时专家Terminal 7 active /30 terminal，AVG Terminal 9 active /27 terminal，AVG SWE 8 active /5 terminal；pending仍分别408/409/38，两组仍等待原消费者。

## 自动执行顺序

1. 每组独立等待其原parent正常退出、checkpoint active为空且状态为正常停止/完成；检查其实际使用CPU池上的`apex-baseline-`、`apex-asi-`、`ai4sci-submission-` scope均空。AVG组必须同时等待SWE与Terminal，不能只凭模型阶段结束取消服务。
2. 经原bridge读取原生vLLM指标，要求running/waiting均0且连续两次成立。仅在完整drain proof保存后，`scancel`该组旧服务并等其从squeue消失；**此时才可sbatch该组替代服务**。两组并行推进，但各组绝不先占新2卡。
3. 新作业显式`--partition=acd_u --nice=1000`，沿用原脚本的TP2、16CPU、128GiB、QoS formal-user/account qinlucao及排除节点；保留原端口/别名/冻结adapter。GPU数仍2，非新增副本。提交使用唯一job name，未知提交结果不自动重发，防止重复申请。
4. 新作业最大窗口不晚于原服务：Terminal **2026-10-18 02:01:37 CST**；AVGExec **02:09:48 CST**，两者也均早于02:20总cap。time按提交时剩余分钟，deadline为原截止；不传`--time-min`，保留完整剩余窗口。配置的`minimum_job_minutes=60`仅作过晚提交的拒绝门槛。运行后核实实际EndTime不越界，必要时只缩短，绝不延长；队列采用实际新EndTime。
5. 对照原/新HPC launch收据，检查Base revision、adapter路径/rank/alpha/620tensor、完整服务命令、TP2相关固定配置、20序列、64K/8K与nonthinking相同；核实实际Slurm为acd_u/nice1000/2GPU/16CPU/128GiB。重定向原bridge28091/28092到新node原service port18003/18000，更新tunnel job/node元数据。
6. 每组只做1次独立的短合成`MIGRATION_READY`验收（tokenize、模型别名、65,536上限、无reasoning、usage一致）；不读正式题或生成Base答卷。验收32输出cap仅属合成校准，正式8,192 cap未改。原native环境/agent接线和冻结runtime overlays保留。
7. 备份旧checkpoint/config/admission/controller等迁移前元数据，更新相关队列service job/node/end与服务日志路径。只清除本次owner写的STOP，按捕获的原argv与原PATH/PYTHONPATH/XDG/DBUS/线程环境重启。原terminal ledger中已有的键无论0、1或invalid都保留，待续集合只来自未准入ID；启动后核对原terminal条目不变。

Terminal仍是原分离CPU租约与独立扩展stage；SWE仍是CPU0–9、每题1CPU/4GiB。Terminal每题4CPU/8GiB、1800s solver/900s verifier；SWE1800s solver/3000s replay；64K/8K、采样和模型均未改。原first-admission、原始答案、native结果与评分不改写。Terminal admission等可更新元数据的旧版另存每组`before-resume/`，不抹去历史。

## AVG SWE 续跑修复与历史

原helper把handoffs重置为空，续跑可能重写`source-cpu-release-checkpoints/initial.json`和首次partial receipt。本次最小修复：读取既有`cpu-handoffs.json`；原条目保持；新的slot释放使用新resume snapshot；首次partial receipt存在时不重写；已有handoffs也能通过续跑入口，不要求再次获得一个新slot。

补丁仅staged于`artifacts/eval/execution_partition_migration_20261017/staged/run_swe_merged_benchmark.py`，driver等AVG SWE旧parent完全退出后才替换实际脚本。CPU人工场景已验证：原9条handoff逐值不变，旧initial source snapshot不变，新释放CPU5引用新独立快照；两个脚本语法检查通过。没有启动新任务/容器来测试。

## SSH、恢复与后续取回

使用80已有完整SSH key和known_hosts做有限HPC CLI，未创建key、未修改authorized_keys、未触碰共享control master。driver使用独立`/tmp/apex-execution-migration-hpc-ctl`连接复用。若后续确需修改restricted forwarding规则，必须与其他迁移agent共用HPC锁`/data/user/qinlucao/.ssh/apex-authorized-keys.lock`；本实现不需要该写操作。

两份tunnel配置也使用上述已有完整key，并非restricted forwarding key，因此本次无需追加PermitOpen。专家原tunnel supervisor读取原配置自动切换node；AVG旧手动forward在消费者排空/旧服务释放后由已有通用supervisor管理，配置为[avg64_execution_hpc_tunnel_20261017.json](../configs/eval/avg64_execution_hpc_tunnel_20261017.json)。没有改HLE/ASI或其他bridge。

每组到`resumed`才表示新普通服务已验收、STOP已清且新parent已启动；`needs_attention`会保留错误和ledger，不擅自重复submit/生成。driver不能与另一个副本同时启动（flock）。若人工恢复，应先读状态/现存PID，不直接再次提交或清STOP。源模型服务硬截止仍受Slurm EndTime约束。

未来新job/node及队列配置由80 driver实际落盘；本地当前配置尚保留旧job并链接迁移state，不能将未来job填成猜测值。根线程后续只需取回80对应state、acceptance、resume收据和更新后的三个队列/tunnel配置，再统一提交。无需保持笔记本在线，也不需在本轮阻塞等待45–80分钟。

本轮未改Git/claud、其他服务或评分；Slurm默认脚本已由根线程改普通分区，本agent仅同步这两份既有脚本到HPC供后续调用。
