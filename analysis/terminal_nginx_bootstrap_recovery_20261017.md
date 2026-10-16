# nginx bootstrap工程恢复及原答案native0验收

**root后续验收07:21 CST**：已独立读最终原生result/test-stdout、6条restore-command结果、资源探针、26原件不变与两次scope排空；接受exact nginx/seed0 native0。主结果只读引用`configs/eval/terminal250_audited_20261017.json`与`collect_terminal250_audited.py`新汇总，不覆盖原队列或raw invalid。下文“待root验收”等措辞保留各阶段原审阅时点。

本轮应用diagnosing-bugs闭环；仅修改[既有一次性parent](../scripts/run_terminal_nginx_grade_only_20261017.py)，未改原config、preparation、候选、SIF、冻结Harbor/runtime或正式summary。完整小收据见[bootstrap快照](source_snapshots/terminal_nginx_bootstrap_recovery_20261017.json)。没有找到本项目CONTEXT/相关ADR。本次不把setup成功与有效native评分混为一谈。

## 第一层：实际CLI RED/GREEN后修复venv身份

旧parent851972已06:21:53退出；child1056668 rc1，在导入时抛`PackageNotFoundError: No package metadata was found for harbor`。当时native目录、restore结果、test和reward均无；两次scope空后锁已释放。错误来自使用`/proc/原parent/exe`解析后的基础Python路径，遗漏原生产argv的venv身份，是本方准备缺口。

先列三个可证伪解释：基础解释器缺venv元数据（预测只换venv就通过）；venv本身损坏（预测两者都失败）；冻结PYTHONPATH不兼容（预测同环境两者都失败）。在修复前对**同冻结CLI、同环境，只换Python词法路径**执行`--help`：

| 07:04:15 CST实际命令（共同suffix为冻结`runtime/scripts/run_terminal_repair_grade_v2.py --help`） | 结果 |
|---|---|
| `artifacts/tools/python/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12` | RED，rc1，同一harbor metadata错误，0.095秒 |
| `artifacts/envs/harbor/bin/python` | GREEN，rc0，包含`--original-result`/`--cpu-offset`帮助，0.245秒 |

没有启动native环境、模型、verifier或取global锁。原6份claim/state/log SHA前后一致。actual帮助stdout/stderr及差分JSON保留于80原prepared下`bootstrap-recovery-20261017/`，不会覆盖旧证据。

最小代码修复保留venv**词法路径，不resolve**，并新增显式`--bootstrap-recovery`：仅允许旧exact851972/start868587717已退出、finished/rc1、无native目录/result、原log exact metadata错误、固定6旧文件SHA与原source/restore/delta全未变时进入。新的claim/state/log位于上述子目录，旧claim不删除；普通`--execute`仍因旧claim存在而拒绝。新入口默认只是pure checks，仍需另加`--execute`及root批准。

8个人工临时文件算例通过：exact可进、原parent活着拒绝、旧rc0拒绝、native目录存在拒绝、候选变化拒绝、非同一bootstrap错误拒绝、旧证据变化拒绝、旧scope排空不成立拒绝。07:06:41实际默认preflight通过；当时新claim不存在、未取锁、未启动verifier。代码SHA为`ff0df32c67c95d78b16503148fe94009b54cbab4f5d148a748ce3ab99ad28ee3`。

## root批准的唯一恢复实际结果：仍是setup失败

root随后独立审阅并于 **07:07:39** 启动唯一parent1209420/start869108324；本agent没有第二次启动它。07:07:46自然结束，child1209421 rc0仅表示runner写出了捕获异常的result，**不表示任务或verifier成功**：

- 独立`native-grade/result.json`存在，native verifier/reward仍null，exception=`RuntimeError: Baseline bootstrap failed`。
- **0条restore-command结果、无test stdout/reward，verifier从未开始**；没有恢复候选、安装或启动nginx。
- 新claim绑定的原source/restore/delta及旧6份证据全未变。两次07:07:44.385828/07:07:46.457999 UTC+8 scope均空；锁07:07:46.461136已释放，后续只读92–95也无scope。
- 原result/归档和第一轮失败记录保留。新失败result也保留；其继承的原agent/environment时间字段属于候选来源，不能当新solver运行记录。

当时未接入任何正式summary。该root启动的parent运行期间源码未改；由于native目录已经存在，旧`--bootstrap-recovery`会拒绝再次准入。后续采用单独显式入口和新输出，不存在自动循环重试。

## 第二层：relative CPU offset引起EINVAL

保留下来的server log为`/data/caoqinlu/apex-terminal250-tmp/apex_baseline_staging_xln34_n9/server.log`（472B，SHA=`07637fa86387ce6ef62d9452055c3c36779f9f4b10d43b2d7d1357d24a176c20`）。精确栈指向冻结`baseline_exec_limits.py:21`：

```python
available = sorted(os.sched_getaffinity(0))
os.sched_setaffinity(0, available[args.cpu_offset:])
```

之后`asi_baseline_limits.affinity_filter(cpus)`选择剩余mask的前4核并禁止子进程扩大affinity。这里offset是**当前mask内的位置**，不是物理CPU编号。外层已经`taskset92-95`，再传92将得到空列表。

按root新授权，07:09:37只运行独立stdlib内核映射探针，未建容器/claim/取锁/运行题目：

| 实际available | 逻辑offset | 实际slice / sched_setaffinity结果 |
|---|---:|---|
| [92,93,94,95] | 92 | []；errno22 RED |
| [92,93,94,95] | 0 | [92,93,94,95]；GREEN，实际after仍同4核 |

这验证了机制；原失败wrapper本身没有打印其mask，不能冒称原log直接记录了available。候选最小修复是**保持物理taskset92–95、逻辑offset改0**。它不增加CPU或放宽4CPU/8GiB/900秒，也不需要改冻结runtime。

## 同SIF合成bootstrap：保留observer失败，再验证GREEN

root授权在同global EX锁内做无候选的start→exec→stop反馈，不属于正式答卷或one-shot verifier。07:14第一轮已成功启动和exec，但observer把`environment._scope_unit`直接交给systemctl，遗漏`.scope`，拿不到ControlGroup，查询内存文件时失败。其`passed=false`收据保留，没有包装为GREEN或评分；stop和双scope排空后正常解锁。

只修observer后，第二轮于 **07:15:22–07:15:28 CST** 完成：同冻结nginx SIF、物理taskset92–95、逻辑offset0，实际Harbor exec返回affinity `[92,93,94,95]`；实际scope `memory.max=8589934592`、`memory.swap.max=0`。停止后07:15:26.443100/28.518132两次scope为空，07:15:28.520599释放global锁。24项候选和旧attempt绑定全未变；**0候选恢复、0 tests/verifier、0模型调用**。

两轮独立小收据在80原prepared下`cpu-bootstrap-smoke-20261017/smoke.json`及`cpu-bootstrap-smoke-observer2-20261017/smoke.json`；后者SHA=`9765981266c185d9691b89c2cd83fdf821b663679de828bd8e719f5b13b9c962`。完整必要字段已收进本doc对应tracked快照。

## 显式CPU恢复入口与默认preflight

新增`--bootstrap-cpu-recovery`，只接exact parent1209420/start869108324已经退出、原失败result仍为pre-restore RuntimeError/null且目录仅有result、server log为固定SHA的affinity EINVAL；固定第一轮6份与第二轮5份旧证据、失败result、server log、GREEN smoke，以及原source/restore/delta。源码不接受其他错误；任何restore/test证据、原bytes变化、parent/child未退出、新输出存在均拒绝。它不删除旧claim/result，也不改变旧入口。

新claim/state/log和native输出全部进入独立`bootstrap-cpu-recovery-20261017/`，native为该目录的`native-grade/`。生产argv只改变新`--output`及相对`--cpu-offset 0`；Python仍为真实Harbor venv词法路径，物理taskset/global锁/PATH/XDG/DBus/冻结runtime/cache、4CPU8GiB900秒均保持。等待锁和spawn前两处1800秒core runway门不变，即10/18 01:50后不得新准入。

9个人工文件夹具通过：exact通过，旧parent活着、已有restore、新输出存在、候选变化、旧证据变化、不同错误、旧scope不空、smoke核错均拒绝。07:18:31本agent默认purechecks通过，没有claim/取锁/启动native；root独立复核的最新preflight为07:18:59。代码SHA=`eccfce88c679cace936b4824ba3a99901646ee1c573a1afa0ab40e6f3de167ca`。root随后执行，运行期间及此后本agent不再改parent。

## root批准的一次CPU恢复：真实native0，尚未接summary

root独立审阅diff和purechecks后于 **07:18:59** 启动唯一parent1240267/start869176365，child1240269。07:19:21自然结束。6条原恢复命令均rc0：仅处理原archive已证明的app/tmp/aptlog与小型etc差分和必要目录；不安装或启动nginx，不全量恢复etc，继续排除runtime `/etc/resolv.conf`。

原官方测试实际运行 **8项、0通过、8失败、4.81秒**，native reward=0，无Harbor exception。安全证据为`AssertionError: Nginx is not installed`（stdout:88）、`Nginx is not running on port 8080`（:762）、`FileNotFoundError ... 'nginx'`（:2254）。这与原archive未提供所需产品状态一致；不是setup错误或900秒compute timeout。result继承的原`started_at`是旧候选来源，不能把它当本次grade walltime。

80精确输出根为`/data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal250-nginx-grade-only-20261017/bootstrap-cpu-recovery-20261017/native-grade/`：

- `result.json` SHA=`0807af5e6c27d2e04d605007d9c3e31747457cd463b999a606d746968417f5c0`。
- `verifier/test-stdout.txt` SHA=`9865f031dea1e9eb66046d4fb5085603e90c179a4ac51e05a5489c8db2fe0413`；`reward.txt`原字节为`0\n`，`ctrf.json`确认8/0/8。
- `restore-command-{0..5}.json`各自均`return_code=0`，没有额外恢复命令。

07:19:28独立只读核验26项claim绑定SHA全未变（包括原result/archive、restore/delta和两次旧失败证据）。07:19:19.813667/21.891014双scope为空，07:19:21.894525已解锁，07:19:28额外scope读取仍空。本agent没有重启parent或修改正式summary；截至该收据，**原raw null不变，独立native0待root验收和决定是否接入**。

预防措施是保留生产argv/venv身份，并在实际资源wrapper这一层建立小型bootstrap反馈；`--help`能验证导入，不能证明cgroup/offset语义。无需扩大成新launcher框架。
