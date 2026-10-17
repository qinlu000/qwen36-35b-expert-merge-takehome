# Terminal专家新增invalid：git-leak-recovery/seed1

09:15–09:16 CST只读核验，唯一新增键为 **`git-leak-recovery/seed1`**，终态时间 **08:28:04.055193 CST**。它是solver预算结束后的cleanup guard阻断评分交接，**不是900秒verifier compute timeout，不能派生预算0**。旧nginx已由独立exact overlay接受0，本轮不重启。所有源、队列、marker、claim和评分配置均未改，无模型/API/native调用；additional SWE cohort的新文件未读未改，本轮不启动Terminal grade。

## 快照比较与计数边界

`execution_status_20261017_0810.json`（raw source08:09:14）只有nginx/seed0、torch-tensor-parallelism/seed0、train-fasttext/seed0三个raw invalid。本轮09:14:58 raw source为146 terminal、142 valid、4 raw invalid、12 active、287 pending，新增的第四个正是git-leak。raw仍保留nginx旧null；正式审计层另接受该原答案0，不能因此把它重复计为新增缺口。

实际存在的正式快照：

| 快照实际时间 | 专家valid / invalid / pending | AVG valid / invalid / pending |
|---|---|---|
| formal0810，08:08:08 | 110 / 2 / 333 | 103 / 3 / 339 |
| formal0915，09:13:51 | 141 / 3 / 301 | 131 / 3 / 311 |

本轮local/80 `analysis/source_snapshots`均未见`*0920*`，不虚构09:20采集；以上按实际0810→0915及当前raw区分。正式仍不完整，主分/CI为null。本分支没有刷新collector或汇总。

## 精确原生证据

80项目根`R=/data/caoqinlu/projects/apex-takehome`。原trial为`R/artifacts/eval/terminal250_full445_20261017/trials/git-leak-recovery__seed1/`。

- `result.json` SHA=`cb48b18ec0d4df51783385f475970120cc3a43932afbc6e7660dfc42314440ca`；model=`apex-terminal250`，seed1，task checksum=`da0aeda47b324bff84c67faa3d8bed3b3b5f1200e3b17cecbc7dc8f802fd366a`。
- top exception是`RuntimeError: Refusing public network after unconfirmed solver cleanup`。冻结`baseline_singularity.py:58`在恢复public policy时拒绝，调用链含`terminal_repair_environment_v2.py:89`；guard未被放宽或绕过。
- `trial.log:41`记录`shared 1800s solver deadline`；`:43`记录同一cleanup guard。agent execution从07:58:00.508249至08:28:01.596639，约1801.088秒；正式config override1800秒，task.toml默认agent900秒不覆盖该正式设置。
- native verifier result为null，verifier目录为空，无test stdout、reward或官方测试开始证据。solver预算耗尽是背景；当前无分的直接阶段是cleanup/网络策略交接，根因尚未闭合。既不能因AgentTimeout背景自动0，也不能把这个guard错误说成已证实某个包/网络服务故障。

完整小文件SHA、config和frozen guard路径在[JSON收据](source_snapshots/terminal_new_invalid_audit_20261017.json)，未复制轨迹内容或任何恢复出的密钥/答案。

## 候选归档可用，但还不能直接复放

同trial的`artifacts/logs/artifacts/final-task-state.tar`为829,440B，SHA=`1f8863211b0189c011fdd1bf39717c8ec9481a273c7e66ee45267b68c2b7dffd`，tar可读、561 members，app50/etc510/root1。app内46个.git成员，HEAD、objects文件、reflogs存在；**只检查结构，未验证完整对象引用闭包或复原可用性**，不能把“有.git”写成“已证实完整恢复全部Git历史”。

同级`final-task-state.json` SHA=`9ccbc62dae3761a3d4a7b3f95f13b7d9497b86a1862e7404d849c100adacec8c`，return_code0、无stderr，captured_before_verifier=true，complete_prefixes为app/etc，另记1个changed external文件；reason为CancelledError。采集时记录15个进程，live service/process状态不能仅靠tar重建。原`agent/trajectory.json`亦存在，126,314B；本轮只记身份，不输出内容。

原task为`R/artifacts/results/base-terminal-v2-724242-r2/tasks/git-leak-recovery/`。原image tag `alexgshaw/git-leak-recovery:20251031`对应实存symlink `R/artifacts/benchmarks/sif/alexgshaw_git-leak-recovery_20251031.sif`，解析到`sha256-62160e522a4238b8bcd522411ea97b5b200f811e5899d34947e66809bef7e586.sif`，92,987,392B；仅核stat/路径，未大文件重hash。

后续若root另审，先针对这个SIF做静态/etc差分和managed resolver排除，绑定该seed1的原result/config/checksum/archive；确认完整原.git及需要的artifact/外部路径可从原件恢复。必须保留Git历史和原候选状态，不能重新clone/reset、重构答案、补产品文件或盲恢复全/etc。不能借用nginx专用manifest、旧claim或它的exact restore delta。当前没有新增准备脚本、恢复清单或执行许可。

## 资源契约与新runway建议

只重放原候选的方向仍是冻结`run_terminal_repair_grade_v2.py`入口、原SIF/官方verifier、**4CPU/8192MiB/900秒verifier、0模型调用**；不再给solver任何时间。应使用原Harbor词法venv、原PATH/XDG/DBus/cache，物理taskset92–95配逻辑offset0。

只能等root明确授予真实grader租约，并在同`R/artifacts/eval/direct_asi_grader_cpu92_95.lock` EX及可见guard下启动，原消费者/新SWE cohort结束且真实scope排空后再申请。若92–95已经交给正式Terminal，不因flock或瞬时scope空取回。结束仍需双native空→停自有guard→双完整scope空→解锁；不写ASI/Terminal完成marker。

新项建议准入runway**不少于2400秒**，包括原fresh environment build上限600秒、原verifier900秒、明确恢复命令上限和清理余量；若最终restore/cleanup清单合计需要更久，应采用更大门槛。按core截止10/18 02:20，2400秒门意味着最迟01:40新准入；不能机械套nginx旧1800秒门或先启动再压缩原900秒预算。当前root即将审核的新SWE三child独占92–95优先，本轮仅保留证据，不启动/争抢资源，不承诺该Terminal补评分能在窗口内完成。

唯一owned为本md和`source_snapshots/terminal_new_invalid_audit_20261017.json`。
