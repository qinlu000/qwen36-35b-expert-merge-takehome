# SWE原答案grade-only：Vuls两项已唯一准入

**root后续执行08:18 CST**：源码/manifest完整审阅、默认prepare和真实grader租约核验后，root唯一提交`swe249/vuls` parent1520240/start869530503与`avg64/vuls` parent1520241/start869530503。[启动收据](source_snapshots/swe_vuls_grade_only_launch_20261017.json)保留exact command/源码身份。08:18:11前者持global90775088、child1520253已运行，后者等待同锁且尚无child；一项一个attempt1，不同时native。真实guard92–95/32MiB/swap0，native scope只CPU92/4GiB/swap0，原29bindings/SIF元数据未变；无新模型调用。新结果须root独立审日志、OOM/test证据后才可接只读overlay，目前主SWE仍各48/51、原raw null不改。script/manifest在两父完全终态前冻结，不能为其他4项修改或重复submit。08:23:29读到专家原Go workspace preparation rc0/53.93秒、原cache磁盘复制rc0，仍native_running；AVG仍等锁，无新有效分。

以下保留**08:15准备阶段**的原过程和零执行声明，仅描述当时本agent动作；当前准入以上述root执行为准。未宣称OOM/transport根因已修复。

本轮按root审核的[只读方案](swe_remaining_grade_only_plan_20261017.md)准备，应用[diagnosing-bugs](</Users/caoqinlu/.codex/skills/diagnosing-bugs/SKILL.md>)。已读skill，未找到本项目CONTEXT/相关ADR。**0 native、0模型/API、0执行claim、0 guard、未取global锁**；没有修改原Base、答案、结果、评分summary、队列、marker、网络或Git/claud。小收据见[preparation JSON](source_snapshots/swe_remaining_grade_only_preparation_20261017.json)。文件名含execution，但本轮仅prepare。

## 假说与本轮能证明的范围

已捕获的RED是两模型Vuls的RemoteProtocolError；专家另有03:28:13对应scope OOM记录，AVG没有同等因果证据。原result/patch/tests身份见新manifest，旧详细证据在`analysis/source_snapshots/swe_remaining_scoring_audit_20261017.json`。本轮先公布四个可证伪假说：

1. tmpfs/Go cache写入增加内存压力；原内容搬到磁盘副本后若OOM显著减少则支持，但本轮未跑native，未验证。
2. 原候选有编译或任务实现错误；资源恢复后仍可能得到原生0，不能预先按空patch判0。
3. native server/transport故障独立于内存；需要同一次评分的server日志与memory.events/peak区分。
4. venv、模块导入或relative CPU offset错误会造成新bootstrap失败；本轮用真实CLI和小元数据/内核反馈检验这类准备缺口。

root当前只授权准备，因此没有原OOM路径的真实GREEN，也不声称memory/transport根因已修复。这里完成的是可进入root执行审核的准备反馈，不是bug已解决或评分已补齐。

## 实现与不可准入的项

[脚本](../scripts/run_swe_remaining_grade_only_20261017.py)默认prepare-only；[六项manifest](../configs/eval/swe_remaining_grade_only_20261017.json)绑定每项13个原小文件（generation/config/result、patch、原replay、task/tests）及16个所用源码身份。仅`swe249/vuls`、`avg64/vuls`在代码和manifest同时允许；E/N、E/T2、A/T2、A/T774均禁用，T774没有实现网络route。两项各29个binding在真实default prepare通过。

worker复制自己的原replay config，保持原task、PatchReplay source_job、SIF、tests、1CPU/4096MiB/0GPU、verifier3000秒；只换独立output、物理92/逻辑offset0和Vuls磁盘/日志环境。Go workspace prep的单次exec cap1800保留在原3000秒verifier总timer内，不能另加评分时间。现有Base DiskScratchAndLogs只作最小实现参考，未调用其硬编码Base CLI；新scratch属于自己的attempt1，不修改原依赖、Go版本或测试。

`--execute`必须显式给一个精确item，独立`attempt1`已有即拒绝，无自动retry。parent持同`artifacts/eval/direct_asi_grader_cpu92_95.lock`，实查grader池未移交Terminal、实际scope为空后创建自有`apex-baseline-swe-grade-PID.scope`可见sleep guard；核实际CPU affinity92–95、MemoryMax32MiB/swap0后才启动native单核92。guard仅保留调度租约，不增加native的1CPU/4GiB预算。默认检查**没有执行这些步骤**。

监控/日志/读取异常也不会提前解锁：finally先等已启动child自然结束，再两次native scope空（只排除自有guard）；随后stop guard，再两次完整busy_scopes空并确认0自有guard才LOCK_UN。SIGTERM/SIGINT只阻止尚未准入的native，不缩短已经准入的原预算。两处core runway检查为7200秒，保留原build/patch/verifier上限及cleanup窗口；10/18 00:20后不新准入，已准入继续原预算。

所有新native结果只写pending_root_review和raw reward/exception、source bytes、原Go cache复制收据、live stdout/stderr、server log、memory.events/peak；不调用`collect_swe_final.score`自动决定有效性，不接任何主summary。内存日志缺失也不等价于无OOM。

## 真实准备反馈

08:15:49 CST实际5项CLI检查均按预期：

| 检查 | 实际结果 |
|---|---|
| 解析到底层的Python运行同脚本`--help` | RED，rc1，`PackageNotFoundError: No package metadata was found for harbor`，重现既有venv身份缺口 |
| 保留`artifacts/envs/harbor/bin/python`词法路径运行`--help` | GREEN，rc0；只证明导入/CLI可用 |
| 显式请求disabled NodeBB | RED，拒绝；无claim |
| 在独立临时manifest中仅改一条source SHA | RED，`Frozen input changed`；未改真实source |
| 真实默认prepare两项Vuls | GREEN，各29 bindings、原1CPU4GiB/3000s、命名module/scratch绑定通过；两attempt1均不存在 |

首次default prepare还发现**新manifest的纳秒mtime经过JS数字转换损失末位精度**，SIF身份检查正确拒绝。比较实际stat后，仅把新manifest的纳秒值改为精确十进制字符串，SIF没有变化；之后GREEN。原/实际mtime及差值保存在收据，不将其描述成原候选或SIF损坏。

纯kernel元数据探针实际在CPU10运行：available=[10]时offset92得到errno22，offset0仍为[10]。这是relative-index seam验证，**没有探测92上的native资源**。父session实际有效cgroup为0–127，未设AllowedCPUs10；故普通metadata affinity10不妨碍未来child申请92。真实4GiB/native affinity仍须首次获批运行时核验，不能用这次probe或`--help`冒称已经验证OOM修复。

默认prepare显式导入Harbor将使用的`run_swe_remaining_grade_only_20261017.VulsDiskLogs`，验证类来源/继承和其scratch绑定，处理CLI `__main__`与named module两份class的差别。现parent源码SHA=`a0eb0e252e27b56d3c615324c83a3fe0831ba1c85565ce9413c4782c27edfd10`，manifestSHA=`19f6c69a335d68fcc75369f962daaf8c0fabe49f265db8939aab324287311717`。

## 精确生产环境与待root审核的launch

80根`R=/data/caoqinlu/projects/apex-takehome`。root启动parent时须采用以下环境，脚本也会为guard/child显式重建同一env；不能用SSH默认PATH/DBus。Vuls是glibc cohort，**不插musl shim**；原musl shim仅在未来另行审核T2时按原cohort使用，当前T2被硬拒绝。

```sh
cd /data/caoqinlu/projects/apex-takehome
env PYTHONDONTWRITEBYTECODE=1 \
  XDG_RUNTIME_DIR=/run/user/1012 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1012/bus \
  TMPDIR=/data/caoqinlu/apex-swe-grade-only-20261017-tmp \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PATH=/data/caoqinlu/projects/apex-takehome/artifacts/tools/apptainer-1.4.5/rootfs/usr/bin:/data/caoqinlu/projects/apex-takehome/artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  PYTHONPATH=/data/caoqinlu/projects/apex-takehome/scripts:/data/caoqinlu/projects/apex-takehome/artifacts/benchmarks/swe-bench-pro/v2/tooling:/data/caoqinlu/projects/apex-takehome/artifacts/benchmarks/harbor/src \
  /data/caoqinlu/projects/apex-takehome/artifacts/envs/harbor/bin/python \
  scripts/run_swe_remaining_grade_only_20261017.py --item swe249/vuls
```

以上仍是prepare-only；只有root独立审完源码/真实租约并明确决定执行后，才在同一精确环境为单项加`--execute`。AVG另一项用`--item avg64/vuls`，也须独立准入；不能自动连跑六项。当前08:15快照中两Terminal未接92–95且scope空，只是观察，不是本分支已授租；root/direct仍在核跨grader契约。若Terminal已接管92–95，即使flock暂空也停止，不抢回。

准备收据原件在80 `artifacts/recovery/swe-remaining-grade-only-20261017/{preparation.json,preflight-probes.json,preflight-probes/}`；独立/data TMPDIR已建空目录。没有新native结果、执行PID或执行claim。本轮owned仅新脚本、六项manifest、本md及小JSON，等待root审核，不再加测或准入。
