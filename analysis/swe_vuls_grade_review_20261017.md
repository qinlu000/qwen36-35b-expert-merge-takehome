# 两项Vuls原答案grade-only：09:09只读复核

采集时间为2026-10-17 **09:09:57 CST**，09:10:57再次只读核实际scope/guard/global锁。两个parent都已自然结束，无需等待或新评分。脚本仍`a0eb0e252e27b56d3c615324c83a3fe0831ba1c85565ce9413c4782c27edfd10`，manifest仍`19f6c69a335d68fcc75369f962daaf8c0fabe49f265db8939aab324287311717`；本轮不修改这些冻结文件或任何结果、collector、队列、marker、进程、网络/GPU/API。小收据见[JSON](source_snapshots/swe_vuls_grade_review_20261017.json)。

## 原生结果及有效性证据

两项共同task ID：`instance_future-architect__vuls-5af1a227339e46c7abf3f2815e4c636a0c01098e`。80项目根`R=/data/caoqinlu/projects/apex-takehome`；独立恢复根为`R/artifacts/recovery/swe-remaining-grade-only-20261017/`。以下E/A分别对应其`swe249/ID/attempt1/`、`avg64/ID/attempt1/`，原件仍各自在`R/artifacts/eval/{swe249_hard51_20261016,avg64_swe_hard51_20261017}/`。

| 项 | parent / child | native结束 | raw结果 |
|---|---|---|---|
| E / SWE249 | 1520240 / 1520253 | 08:24:35.623370 | reward0，Harbor exception=null |
| A / AVG64 | 1520241 / 1558973 | 08:31:34.766944 | reward0，Harbor exception=null |

精确新result路径均为`恢复根/{swe249,avg64}/ID/attempt1/native/ID/result.json`。E的resultSHA=`fc42ad8b387209f00ce8fd1077997e9e6e8fdbc83d1be99ec8f0e8c37926e4e0`；A为`ec738c0dd2ab2b624f7c3b74342728adae352856bde62ca628896f2e589eafe3`。两份原始RemoteProtocolError仍保留，没有覆盖或重生成模型答卷。

**这不是仅据reward0或“build failed”判分。** 各自原`tasks/ID/instruction.md:118`明确要求`isRunningKernel(pack,family,release,kernel)`接受4参；冻结官方test_patch也调用4参。两模型自己的原patch均0B、SHA=`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`，fresh replay均明确apply nothing，保留旧3参实现。两份实际`verifier/run-script-stdout.txt:3–5`精确编译证据为：

```text
scanner/utils_test.go:170:94: too many arguments in call to isRunningKernel
have (models.Package, string, string, models.Kernel)
want (models.Package, string, models.Kernel)
```

这三行是安全缩写；完整Go类型包名前缀保留在原日志。两份stdout相同SHA=`8ebf1d206c0ee5f9f3e20c03e054cb3b33e3f37f5eeca67c24bf74aa9a090ae6`，stderr均0B。官方required为11、passed0，`output.json.tests=[]`。**编译阶段阻断，没有11个测试实际执行，更不能写成“11项均运行失败”。** config里的fail_to_pass/pass_to_pass是编码成字符串的Python list，按原test.sh的parse_tests解码后分别11/0；不把字符串字符数当测试数。

因此支持分别接受这两份**自身原候选**的原生0：未实现任务要求的产品接口，非runner依赖缺失的泛化推断。没有将专家结果借给AVG，也没有使用参考实现、补candidate代码或按reward选最好attempt。root已独立重读同一task/test_patch、native错误和资源证据；最终exact overlay仍由root更新审计manifest，本分支不改有效性来源。

## 环境、内存和source身份

原Go workspace准备分别rc0，E53.93秒、A64.45秒；原cache preseed均191 copied/36 kept。`verifier/native-go-disk-cache.json`记录原`/root/.cache/go-build`及`/go/pkg/mod`以`cp -a`原样复制至本attempt磁盘/tmp下，两次rc0。没有改Go工具链、依赖版本、校验或官方测试。只读比较原/新config，差异严格只有environment import_path、原物理slot→逻辑offset0、独立trials_dir；原1CPU/4096MiB/3000秒等字段一致。

| 保存的native cgroup字段 | E | A |
|---|---:|---:|
| memory.max | 4294967296 | 4294967296 |
| memory.swap.max | 0 | 0 |
| memory.events max | 25140 | 17624 |
| memory.events oom / oom_kill | 0 / 0 | 0 / 0 |
| memory.peak（原值） | 4295655424 | 4295925760 |

max事件很多，说明仍有内存上限压力；peak原值略高于max，照录不抹平。**本次保存的cgroup计数无OOM/OOM-kill**，不据此推翻历史专家OOM，也不把磁盘方案说成普适解决所有OOM。新server日志均启动成功，仅有预启动tmux缺失警告，没有保存到fatal/transport traceback；实际Go准备和编译已完成到明确产品错误。

每项claim的**29个binding独立重算全部一致**，各自原generation模型为`openai/apex-val-swe249`与`openai/apex-avg64`。共同task checksum仍`8f7e762cfc234f8889dcf110f78cdcf12c337f2fb24c1317fa03309308d233c5`。原SIF `R/artifacts/benchmarks/sif/sha256-ce030de85a57473a9b52d493fd023ab90871959e7129b4281edb1b2e5038d078.sif`的size/纳秒mtime与冻结manifest一致；未重hash大SIF，不将stat核对称为全内容hash证明。

## 排空、guard和global锁

| 证据顺序（CST） | E | A |
|---|---|---|
| 两次native scope空（只排除自有guard） | 08:24:38.117555 / 40.197303 | 08:31:38.332306 / 40.409533 |
| guard停止后的两次完整scope空 | 08:24:40.275837 / 42.353273 | 08:31:40.473678 / 42.536084 |
| 解锁时点 | 08:24:42.426957 | 08:31:42.591022 |

两parent state均`finished_pending_root_review`、child rc0、lock_held=false、guard_stopped=true、accepted_into_formal_summary=false；09:09 parent/child PID均不存在。A新native started_at为08:24:48.702761，晚于E完整排空并解锁，支持两项按同锁串行，没有同时占用native池。

两份guard创建时均实际观察affinity92–95、MemoryMax33554432/swap0，native命令分别为物理`taskset -c 92`及逻辑offset0。09:10:57额外读取两个`apex-baseline-swe-grade-{1520240,1520241}.scope`均`LoadState=not-found / ActiveState=inactive / ControlGroup空`；实际92–95 busy scopes为空，global锁inode90775088没有FLOCK记录。该瞬时空闲不是永久授租或新增claim许可；没有抢Terminal核或改ASI/Terminal marker。

**复核结论：两份exact native0均具备独立原候选产品契约失败和完整租约清理证据，可交root最终接受。** 本分支仍不接summary、不改manifest、不重启/再评分；本轮owned只有此md和小JSON。
