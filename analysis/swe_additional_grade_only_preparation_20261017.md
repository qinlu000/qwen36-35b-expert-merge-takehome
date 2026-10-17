# SWE追加三项：单cohort准备（未执行）

已读原[六项方案](swe_remaining_grade_only_plan_20261017.md)、[Vuls执行记录](swe_remaining_grade_only_execution_20261017.md)和claud最新08:24段。root于09:09后授权准备追加三项，并改为一个cohort父并行三个原生child；本轮**仅prepare**，无claim、guard、global锁、native/container/model/API、网络probe或队列变更。原Base、Vuls源码`a0eb0e…fd10`和manifest`19f6c69a…1717`均未修改，真实前后hash检查仍一致。

新[脚本](../scripts/run_swe_additional_grade_only_20261017.py)和[固定manifest](../configs/eval/swe_additional_grade_only_20261017.json)已同步80，09:15:43实际默认prepare通过；[小收据](source_snapshots/swe_additional_grade_only_preparation_20261017.json)保留真实CLI/绑定反馈。源码SHA256 `197184f50fd10f92a46ed29bc10c50b88d4b5adfdec07f177790248d9dc38b6d`，manifest `7156a584a50340c2661efe6569d0c11528b90b6d871bcf4cf0557ce7406ac151`。本agent未执行--execute，root须独立审核后决定唯一启动。

## 固定三项与中立环境实现

| 精确select | 原环境 | 原异常 | 原patch | 未来物理CPU |
|---|---|---|---:|---:|
| swe249/nodebb | SweCleanGlibcRuntimeEnvironment | VerifierTimeoutError | 7422B | 92 |
| swe249/teleport2b | SweCleanMuslScoreEnvironment | VerifierTimeoutError | 0B | 93 |
| avg64/teleport2b | SweCleanMuslScoreEnvironment | RewardFileNotFoundError | 0B | 94 |

每项38个实际小文件绑定（25源码/固定metadata＋13原config/result/patch/task/tests），SIF只核已有精确size/mtime与路径，未重复hash大镜像。各自原generation模型、PatchReplay source_job、task checksum、SIF及原replay config保持，绝不跨模型借用原生0。新输出固定在80 `artifacts/recovery/swe-additional-grade-only-20261017/{swe249,avg64}/<原task_id>/attempt1/`；每项独立claim、native结果、host-tmp、scratch、child.log及pending-root-review，原输出保持。

从Base的DiskScratchAndLogs只复制中立必要实现：/tmp绑定自有/data scratch；若镜像确有Go，原GOCACHE/GOMODCACHE内容cp -a到该scratch副本后仅改变缓存位置；每10秒留存原run_script临时stdout/stderr，结束前留server/cgroup memory事件。新mixin分别派生glibc NodeBB与musl T2，不调用Base硬编码main，不monkeypatch旧类/旧Vuls。日志保存错误也经finally调用原server stop，避免因诊断日志失败留下server。复制缓存不是安装/改依赖，不宣称修好原OOM或超时。

NodeBB原非空patch、`.mocharc.yml`与产品状态不改，不加--exit，不凭EXIT trap的reward1接受成功。T2保留原musl shim在Apptainer之前、原镜像内PATH/Go/依赖/测试。Go workspace prep的原1800秒exec cap仍在原3000秒verifier总timer内，不给测试另加1800秒。所有结果只pending_root_review，不自动valid/0/1，不重试。

## 一父三child租约与预算

默认只验证metadata/导入/schema，不创建Trial或环境。显式--execute且重复--item选择后，父独占`…/cohort-attempt1/execution-claim.json`，取同92–95 global EX锁，确认Terminal未永久接管且真实scope空，再创建一可见`apex-baseline-swe-additional-PID.scope` guard（92–95、32MiB/swap0），实核affinity/cgroup后才能准入。

固定三个child分别taskset92/93/94；每child当前affinity内**logical offset0、1CPU/4096MiB/0GPU、PatchReplay1800秒、verifier3000秒**，合计最多3CPU/12GiB，不以guard额外增加native资源。musl shim只加给两个T2 child。每child重新绑定Harbor将导入的新named module scratch，解决CLI `__main__`与命名class不同的问题；词法`artifacts/envs/harbor/bin/python`、原DBus/XDG、Apptainer/fakeroot/PYTHONPATH原样。父可作metadata affinity10，不能用AllowedCPUs10封死将来的92–94。

cohort claim保留每项配置/CPU/原文件身份，启动后记录各唯一child pid/startticks；单项claim也独立。基础Popen三次后poll，无动态队列。一个child失败不取消别的在途；监控/日志异常也finally先等全部已准入child自然结束，连续两次native scope空（仅排自有guard），清guard，再双完整scope空/0自有guard，最后unlock。SIGTERM/INT只阻止还未准入的child，原在途预算不缩。共享锁等待前、guard后和每child准入前均要求**7200秒core runway**，截止10/18 02:20，00:20后不新准入。

## 已完成的低成本反馈与未知项

| 真实检查（CPU10、未设cgroup AllowedCPUs） | 结果 |
|---|---|
| 词法Harbor venv --help/import | GREEN rc0 |
| 显式select未实现AVG T774 | RED拒绝，无claim |
| 重复同一select | RED拒绝，无claim |
| 临时metadata只改一条原source SHA | RED Frozen input changed；原manifest/source不改 |
| 真实default prepare全部三项 | GREEN，各38绑定、schema/named scratch/物理92/93/94与logical0通过 |

反馈证明准备入口可导入、绑定能拒绝错源，**不是原超时/无reward根因的GREEN**。仍有可证伪假说：候选/测试退出行为、真实build/test耗时超过固定预算、tmpfs/cache资源压力、server/传输或日志丢失。只有原预算下的独立native结果及durable logs/events才能区分；本轮不据空patch或旧reward裁定。

## Root审后命令（本轮未执行）

80项目根`R=/data/caoqinlu/projects/apex-takehome`，初始parent保留原glibc工具路径：

```sh
R=/data/caoqinlu/projects/apex-takehome
env PYTHONDONTWRITEBYTECODE=1 XDG_RUNTIME_DIR=/run/user/1012 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1012/bus \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PATH=$R/artifacts/tools/apptainer-1.4.5/rootfs/usr/bin:$R/artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  PYTHONPATH=$R/scripts:$R/artifacts/benchmarks/swe-bench-pro/v2/tooling:$R/artifacts/benchmarks/harbor/src \
  $R/artifacts/envs/harbor/bin/python $R/scripts/run_swe_additional_grade_only_20261017.py
```

以上默认prepare-only。root审核及实核租约后才另加`--execute --item swe249/nodebb --item swe249/teleport2b --item avg64/teleport2b`唯一cohort；可只显式选子集，不自动扩成其他题。现场空scope不是永久使用权，Terminal已接管92–95时即拒绝；本轮没有领取该权利。

## AVG T774仅静态原proxy方案

T774不在新manifest/ALLOWED中。现有`swe_score_original_proxy_repair.py`40行只允许CONNECT `proxy.golang.org:443`，77行原probe URI为`https://proxy.golang.org/github.com/mdlayher/netlink/@v/list`；该脚本硬编码专家SOURCE/OUTPUT/CPU10，**不可直接给AVG运行**。未来若获批，先用独立namespace/socket和原musl入口做同URL轻量可达性验收，保留原URI/TLS校验，再单独审核同原AVG patch/tests/Go/依赖版本的grade。不改Go module、goproxy、测试或候选，不借专家后续工具链错误判AVG为0。

本轮未发该URL请求、未启动relay或改路由，当前public可达性仍unknown。这只是静态方案，A/T774没有新native入口或执行claim。

root后续已独立审完整脚本/manifest，09:16:29真实defaultprepare再次通过三项各38绑定；09:17资源核验报告仍6张普通H100、Terminal未接92–95、scopes空、新output不存在。源码和manifest现冻结，等待另一独立review后由root决定唯一execute；本agent未启动cohort，root资源观察不写成已准入结果。
