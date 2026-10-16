# 执行评分缺口与恢复可行性（2026-10-17）

初次只读原文件、冻结源码、归档目录、运行ledger和CPU scope；实际快照 **05:15:23 CST**，保存于本文及[小JSON收据](source_snapshots/execution_scoring_gaps_20261017.json)。后续root批准AVG c1f2独立审计，新增专属collector、manifest及一次执行收据，见下文。全程没有启动verifier、solver、容器、模型请求、SVD、训练或GPU，未改网络、原队列配置和原始结果。SWE专家剩余NodeBB/Vuls5af/Teleport2b继续null。

## Terminal专家 nginx / seed0

原结果为`artifacts/eval/terminal250_full445_20261017/trials/nginx-request-logging__seed0/result.json`，model=`apex-terminal250`、seed0，verifier字段null，raw reward null。04:13:14 CST失败于冻结`baseline_singularity.py:58`：`Refusing public network after unconfirmed solver cleanup`。原agent已达到1800秒预算，cleanup receipt仍有curl/head读取链在运行；不能把这个guard错误改称900秒verifier计算超时，也不能直接填0。

**有可追溯的原答案归档，但没有完整文件系统/进程检查点。** 同trial的`artifacts/logs/artifacts/final-task-state.tar`为727,040B，配套JSON记tar return0、stderr为空、captured_before_verifier=true。静态tar目录有483成员、117普通文件、314symlink，无绝对/上跳成员名、无特殊设备文件；168个symlink目标为绝对路径，所以任何恢复必须在隔离任务根内，不能在80宿主直接解包。小文件SHA与原task checksum在收据中。

完整前缀仅`/app`和`/etc`；`/app`只含空目录，归档无nginx路径、无`/var/www`。外部改变文件只有`/tmp/resolv.conf`和apt日志。捕获进程无nginx，原镜像Dockerfile为`python:3.13-slim-bookworm`，只安装requests和curl；原agent观察有`Temporary failure resolving deb.debian.org`及`Unable to locate package nginx`。官方原测试确实检查nginx安装、运行、HTTP页面、配置与日志。因此没有可用的原nginx运行状态可恢复；**不能替候选安装nginx、补配置、造页面或启动新服务来让测试通过**。这些缺失也不等于已经得到原生0。

归档生成器`runtime/scripts/terminal_repair_environment_v2.py:93–151`保存完整前缀和按ctime发现的外部变化，不保存完整/usr、外部删除清单或进程内存；捕获时未证实全局静止。配套receipt也明示`live_service_state_is_not_reconstructed_by_tar=true`。所以“tar成功”不能升级成“整个原环境字节/进程完全一致”。上述安装失败发生在原冻结求解环境内，后续结果仍应保留该环境/网络条件的解释限制，不能全归因模型权重。

**结论为条件可行的grade-only方案，尚不能直接执行。** 原verifier从未开始，因此不存在恢复后的追加solver或放宽900秒问题；未来可在同SIF/同task/原归档上独立运行一次原native verifier，保持4CPU、8192MiB、900秒、无模型，并将独立评分来源指回原result。原invalid和归档不覆盖。

必要前提：

1. 先对同一原SIF的/etc做静态逐项差分，只恢复确证的候选改变及完整前缀中的确证删除。不要把全部/etc直接untar到overlay；现有Base差分脚本已记录这会对不变lower-layer文件触发copy-up问题。
2. `/etc/resolv.conf`是NetworkNamespace管理的只读bind；原归档还含`/tmp/resolv.conf`。恢复计划必须区分候选文件和运行器管理的resolver，沿用冻结的阶段策略，不修改路由、DNS映射、网络白名单或公共网络权限来补原答案。不能绕过cleanup安全guard在原脏环境继续。
3. 使用新的干净同SIF环境，保留原不存在的nginx/网页/服务状态。若任务需要重建原来存在的live服务而现有证据不足，则继续null；本例捕获状态没有该服务。
4. 复用专家冻结470 runtime和同verifier依赖cache；现有`run_terminal_repair_grade_v2.py`和`run_terminal_native_gap_grade_20261017.py`提供grade-only骨架，`prepare_terminal_native_gap_delta_20261017.py`提供同SIF静态差分方法，均不能不审就直接套用其Base批量plan或硬编码目录。新恢复计划要绑定本候选exact来源与资源，且独立输出。
5. 当前没有已授权且释放的4核块，须等待/协调明确租约后再执行；仅看到空scope不是释放证明。测试未实际运行，本轮无法承诺一定取得有效reward。

## AVG64 SWE c1f2：root批准的独立native0审计

只使用AVG自己的原fresh-replay结果、generation和task，未套专家白名单。精确任务为`instance_ansible__ansible-c1f2df47538b884a43320f53e787197793b105e8-v906c969b551b346ef54a2c0b41e04f632b7b73c2`，根`artifacts/eval/avg64_swe_hard51_20261017/`。

- `tasks/<ID>/instruction.md:11,31`要求新增`bigip_message_routing_route`及`lib/ansible/modules/network/f5/bigip_message_routing_route.py`。
- `generation/<ID>/agent/model.patch`实际0字节；generation result模型为`apex-avg64`。replay使用`patch_replay:PatchReplayAgent`，source_job精确指向该AVG generation，replay.json为patch:null；不是另一模型答案。
- `replay/<ID>/result.json`原native reward0、exception_info=null；reward.txt为0，output.json为tests空列表。原native stdout明确`ModuleNotFoundError: No module named 'library'`，随后`No module named 'ansible.modules.network.f5.bigip_message_routing_route'`。这是测试要求的产品实现缺失，不是缺pytest、pip或runner包。

**后续root已独立读取并明确批准该exact AVG64原native0。** 原collector的`empty_tests_requires_audit`及raw result保持；新增[AVG专属manifest](../configs/eval/avg64_swe_audited_hard51_20261017.json)仅有这1项，没有借用专家白名单。收据的`proposed_exact_native_zero_entry`保留05:15提案历史并标注后续批准，original=accepted始终为同一AVG原结果。

[独立只读collector](../scripts/collect_avg64_swe_audited.py)复用既有`collect_swe249_audited.approved_row`的exact path、result/patch SHA、PatchReplayAgent/source_job、reward.txt与无Harbor异常检查，另检查AVG generation模型身份。其他50行逐值复制，不把其余invalid/pending改成0，不生成答案、不重跑verifier。

完整分数还必须同时满足51固定唯一ID全部有效且原attempt全部terminal、active/pending空、owner最终状态，以及原owner的model/scoring结束和all-CPU排空marker及时间顺序。collector只读这些原marker，不创建或修改CPU完成证明。不能直接要求原summary.complete=true：原collector仍将已批准的c1f2标invalid；本独立层以所有51行有效＋原生消费者结束证明判完整。raw marker的benchmark_complete=false也保留原义，不伪造原source已通过其audit。

一次实际CPU10执行于 **05:19:39 CST附近**完成，源summary更新时间为05:19:38.947537 CST：原20有效＋已批准1＝**21/51有效、1 resolved**；30项仍active/pending，`complete=false`、主分null。输出为80 `artifacts/eval/avg64_swe_audited_hard51_20261017/summary.json`，无后台循环。10项本地临时文件夹具覆盖未批准invalid/pending原样保留、源数据不变、错模型/路径/native1拒绝、51有效但缺owner marker不完整、完整证明可出分、非空scope证明/active/重复ID拒绝。实际systemd scope affinity为[10]、MemoryMax1GiB，前后CPU10无native scope，原result和patch SHA前后相同。详细[执行收据](source_snapshots/avg64_swe_audited_execution_20261017.json)保存全部证据。

可在原80环境显式刷新（纯读原评测来源，仅更新独立summary）：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/collect_avg64_swe_audited.py --project=/data/caoqinlu/projects/apex-takehome
```
后续源进度变化不需要重新生成或评分；root负责最终结果spec指向此输出。nginx本轮依然未执行、原null不变。

## 排除迁移空窗后的真实速度

以每组不可变resume收据为起点（04:35:25/28 CST），对照迁移前终态ledger逐键求差；原终态均逐值保留。到05:15:23约39.97分钟：

| 队列 | 终态前→现 | 新终态 | 终态/小时 | 新准入ID | 含首批填槽的准入/小时 | 从当前到截止所需终态/小时 |
|---|---:|---:|---:|---:|---:|---:|
| Terminal专家 | 37→50 | 13 | 19.52 | 23 | 34.53 | 19.02 |
| AVG64 Terminal | 36→48 | 12 | 18.02 | 22 | 33.03 | 18.99 |
| AVG64 SWE | 13→20 | 7 | 10.52 | 17 | 25.55 | 1.48 |

新准入包含恢复时首批10槽填充，不能把34.53/33.03当稳定吞吐；后续补位分别13/12次。终态速度排除了drain和载模，却仍是短窗、不同题型且包含30分钟求解与verifier尾部，**不是线性ETA**。Terminal专家当时只有约2.6%速率余量，AVG约低于所需5.1%，仍有完整445截止风险；SWE/ASI释放后的原定扩容可能缓解，未在此擅改并发/预算。专家50终态中49有效、AVG48均有效；终态完成和严格有效覆盖不能混为一谈。

## 是否有已释放而未采用的CPU

瞬间没有匹配native scope的范围为10–11和92–127；前者只有2核，不能满足一项Terminal的4核固定预算。92–95仍属ASI grader，96–127仍属ASI原/后续程序池，模型生成阶段暂时没有执行scope不表示永久释放。AVG SWE仍10 active、21 pending；SWE及两份ASI all-CPU marker均未生成。因此没有符合现有marker＋scope规则、可直接claim的额外4核块，也没有“已经就绪却被Terminal忽略”的gate证据。本轮没有领取CPU或让其他owner让路。
