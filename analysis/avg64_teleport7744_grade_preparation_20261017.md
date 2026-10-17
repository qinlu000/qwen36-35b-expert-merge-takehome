# AVG64 Teleport7744：原答案grade-only准备

结论：**原AVG输入可以精确绑定，但旧public proxy链当前不可复用；尚不具备直接启动条件。** 2026-10-17 10:13 CST只读采集与一次主机HEAD检查，均使用metadata CPU10。只写本文件及[小JSON](source_snapshots/avg64_teleport7744_grade_preparation_20261017.json)，没有native、claim、锁、容器、新SSH转发、模型/API请求或旧专家修复脚本执行。

## 当前38443链路不存在

80 `ss -lntp sport=:38443`只有表头，无listener；80没有对应SSH进程，本机也没有带该端口`-R/-L`映射的SSH转发。旧[专家审计记录](swe_formal_scoring_audit_20261017.md)已记录当次修复结束后关闭SSH reverse和38443；当前没有owner/peer可供认证为仍存活的旧链路。

只执行一次原URL的主机连通性检查：

```text
HEAD https://proxy.golang.org/github.com/mdlayher/netlink/@v/list
--connect-to proxy.golang.org:443:127.0.0.1:38443
--noproxy '*' --proto '=https' --max-time 10 --connect-timeout 5
--output /dev/null
```

未使用`-k`、未跟随redirect、未下载正文；URL/Host/TLS SNI配置仍指向原FQDN。实际在0.0084秒返回curl7：127.0.0.1:38443连接被拒，HTTP000。**TCP/TLS握手都未发生，不能把curl输出的ssl_verify_result=0当成证书验证通过**。只证明这条既有路由当前不可用，没有追加第二个网络probe或尝试直连替代。

旧脚本receipt常量的origin IP是142.251.34.209，而AVG自己原日志是142.250.73.145；不能称两者为同一个原IP。未来若获批恢复固定路由，必须明确其实际上游，并继续验证原`proxy.golang.org`身份、SNI和证书，不能因为端口重新可连就认为路线同源。

## AVG自己的源与失败证据

固定task为`instance_gravitational__teleport-7744f72c6eb631791434b648ba41083b5f6d2278-vce94f93ad1030e3136852817f2423c1b3ac37bc4`，source为`artifacts/eval/avg64_swe_hard51_20261017`，generation模型`openai/apex-avg64`。原patch 0B，SHA `e3b0c442…b855`；原PatchReplay source_job指向该AVG的generation，不能借专家patch或结果。

原config SHA `44a88ab0…6d90`，原result SHA `1d68a517…7b27`，task checksum `793a666f…0194`；完整值和13个原config/result/replay/patch/task/tests小文件绑定均在JSON，实际核验全部匹配。原SIF为`sha256-83645a1c5565267675a19af0916ba1eed14131c315d92cedb05abea398a03527.sif`，1659310080B、mtime_ns1792093481285011650，与原记录一致；未重hash大镜像。

另核16个现有公共runtime绑定及9个已冻结musl/兼容helper身份，合计**38个小文件绑定**均匹配；未修改旧disabled选择manifest `19f6c69a…1717`。原环境是`SweCleanMuslScoreEnvironment`、1CPU/4096MiB/0GPU、verifier3000秒、PatchReplay1800秒，原setup启动上限300秒。task的setup/verifier为public、agent为no-network，不需要扩大solver网络权限。

AVG自己原日志记载：Go解析`github.com/mdlayher/netlink`时，原URL连接142.250.73.145:443超时。原cache/workspace preparation已return_code0，随后原测试patch应用成功，但TestSendEvent未运行通过；原native文件虽reward0/exception=null，当前仍应按public dependency infra保留null，不能把raw0自动当有效候选0。

其题面79行明确要求正常`require github.com/mdlayher/netlink v1.6.0`，禁止vendor或手写replace；原test patch34/35行导入netlink及nlenc，唯一必需测试为TestSendEvent。空patch没有补全题面要求，但网络先阻断实际build/test；本次不据空patch或专家后续错误直接裁0，也不代候选添加依赖版本、升级Go或改go.mod/go.sum。

## 10:13初始方案（历史，CPU部分已被下文独立124方案替代）

已读`scripts/swe_score_original_proxy_repair.py`（SHA `a44b797d…be22`）。该脚本硬编码专家SOURCE/OUTPUT、CPU10和`/tmp/apex-swe249-original-proxy.sock`，不适用于直接运行AVG。它的连接边界可保留：只准`CONNECT proxy.golang.org:443`，namespace loopback→独立Unix socket→80 loopback38443→原public TLS；只有原verifier命令接收HTTPS_PROXY，候选/全局环境不改。旧脚本没有被执行，也未导入其main或nodebb probe。

未来应是一个独立固定单项入口，复用已稳定的全局租约/自然排空helper，仅新增AVG参数化环境及proxy relay；现在不写200行driver。建议契约：

- 独立输出`artifacts/recovery/avg64-teleport7744-original-proxy-20261017/attempt1`，新claim/日志/namespace；私有Unix socket使用`/data/caoqinlu/apex-grade-tmp/a-teleport7744/p.sock`，不碰专家socket或输出。
- child TMPDIR固定短目录`/data/caoqinlu/apex-grade-tmp/a-teleport7744`；派生control.sock长度84B、私有proxy socket51B，均低于108B。此处仅计算，未创建socket或目录。避免再次出现完整taskID临时路径问题。
- 仍用原musl入口、词法Harbor venv、musl shim、DBus/PATH/私有ABI helpers、原SIF和task；不覆盖镜像Go工具链或其模块缓存内容，不修改测试/parser。现有原runtime的GOSUMDB/GOTOOLCHAIN与Go prep行为保持，不新增GOINSECURE或关闭校验。
- 原URL host/URI、TLS SNI/CA验证及Go模块校验不变；仅修传输路由。若后续需要sumdb/CDN等额外host，先失败并报告，不能顺手扩大CONNECT allowlist。主机HEAD可达也不能替代同原musl环境的原URL验收。
- native必须等待既有global92–95 EX租约、可见guard和实际scope空，由root明确分配一物理CPU、logical offset0；不使用旧脚本CPU10，不抢未来ASI评分或Terminal临时窗口。保留1CPU/4GiB/3000秒、原Go准备计入既有计时、7200秒core runway。
- 完成后保持原答案/原config绑定，独立native结果只pending root review；全部在途自然结束→双native scope空→停自有guard→双完整scope空→解锁，不生成模型、不自动retry/valid。

当前阻塞仅准备层面已明确：38443路由已关闭且无当前上游/TLS证明。重建转发与唯一native执行均需root另审，本轮没有占用已交接评分核或改变任何正式队列。

## 10:30：独立CPU124入口已准备，未execute

root随后授权准备默认只读的[固定单题driver/adapter](../scripts/run_avg64_teleport7744_grade_only_20261017.py)和[新manifest](../configs/eval/avg64_teleport7744_grade_only_20261017.json)。前述原source和10:13一次失败HEAD不变，本阶段**没有新增网络probe、SSH转发、native、claim或锁**。不再建议使用92–95共享grader池；新代码也不打开该旧锁，不等待ASI科学评分完成，不修改任何源marker或Terminal stage2。

CPU124交接仅条件成立。10:22只读审计时AVG ASI为已保存205/240、8active，generation marker尚无。10:30默认prepare虽然观察124–127当前scope为空，仍返回generation_released=false、route_ready=false，**不会仅凭瞬时空scope认领**。

已独立核两live parent489933/489934的argv，均使用各自冻结runtime中的`run_terminal_expert_benchmark.py`（SHA `20fbbfd0…7b5c`）。其代码只从initial_cpu_offsets及expansion_stages创建worker；启动experiment、当前output/config及summary lease的CPU字段与固定契约相符：

| Terminal native池 | 初始offset | stage1 | stage2 | 最末CPU |
|---|---|---|---|---:|
| 专家 | 12,16,…48 | 0,4 | 92,96,100,104 | 107 |
| AVG64 | 52,56,…88 | 8 | 108,112,116,120 | 123 |

两管理parent的宽affinity不等于native租约；固定任务池及所有已声明扩容都不含124–127。新driver在默认prepare、等待期间、spawn前重新核这些窄CPU契约及summary lease子集，若有改动则拒绝。真实其他项目scope若仍有affinity覆盖124–127，也继续等待，不把未经证明的后台空闲当交接。

新入场条件是原AVG `generation_cpu_finished.json`同时为state=finished、completed_conditions=240、worker_pool_shutdown=true、active_owned_scopes=[]、owned_scope_count=240、原八组96–127 cpu_sets；随后还要124–127实际scope空。使用独立`artifacts/eval/avg64_teleport7744_cpu124_127.lock`及可见`apex-baseline-avg-t7744-PID.scope` guard（124–127、32MiB、swap0），native child仅taskset124、logical offset0、**1CPU/4GiB/3000秒**。它与ASI grader92–95及Terminal最终至123的native池可并行；实际scope检查仍是准入条件。

原SIF/AVG patch/tests、PatchReplay1800秒、musl原入口/Go/模块校验保持；仅复用已冻结的中立DiskScratch日志类和纯metadata helpers。41个真实小文件绑定包含13个原source、25个既有runtime/musl/helper身份、冻结7da源码及两个live Terminal launcher。新模块没有import旧专家proxy脚本，其host relay、namespace relay、OUTPUT和Unix socket都在新模块/新namespace中；默认路径只prepare，不启动内部relay。

新专用上游为80 loopback **38444**，固定原AVG origin **142.250.73.145:443**；私有Unix socket为`/data/caoqinlu/apex-grade-tmp/a-teleport7744/p.sock`。root以后建立实际HPC SSH local-forward并留下独立不可变route receipt，本代码不会调用ssh创建转发。receipt路径为新output根`route-receipt.json`，必需字段：

```text
schema = avg64_teleport7744_original_route_v1
state = ready
origin_host = proxy.golang.org
origin_ip = 142.250.73.145
origin_port = 443
upstream_bind_host = 127.0.0.1
upstream_bind_port = 38444
original_url = https://proxy.golang.org/github.com/mdlayher/netlink/@v/list
ssh_pid = 80上实际SSH整数PID
ssh_startticks = 对应/proc/PID/stat的实际starttime字符串
```

driver只读核实际活SSH进程、startticks、精确`-L 127.0.0.1:38444:142.250.73.145:443`映射及38444 listener PID。未来native会在同原musl环境中、同一次claim下对原URL进行既有20秒curl验收，保留原Host/URI/SNI/CA校验，成功才继续原答案replay/verifier；没有升级工具链或扩展CONNECT allowlist。namespace relay先真实bind后写自身ready receipt，环境读取同PID的ready才发这次native probe，避免固定短sleep产生启动竞争。当前未运行这些路径。

唯一attempt目录创建即占一次root执行机会；claim先绑定源码/manifest，admission再绑定原generation marker及root route receipt SHA。SIGTERM仅停止未来准入，在途不缩预算；正常或错误都等待child自然结束，双native空（只排自有guard）→停guard→双完整pool空→解锁。observer错误不能作排空证据。原canonical评分仍不改，所有新结果pending root review，失败不自动重试。core runway保持7200秒。

10:30:01 CST实际词法Harbor CLI --help/defaultprepare通过，41绑定、schema、named环境、Terminal契约及84B/51B短路径检查通过；当时generation和route gate均未满足，没有创建attempt或私有锁。五个纯metadata离线夹具实测：完整240+shutdown+空source GREEN；239、不shutdown、Terminal stage申请124、误用专家IP142.251.34.209均RED。夹具没有native、HTTP/socket或生产文件改动，不能声称实际隧道或原生评分已成功。

冻结待审身份：script SHA256 **8151eadc02727350d86eabf1f033c4fd6a8f012f5589fd6a6e8c4deb8e7eb311**；manifest **8cff408195321efd151b16eaeb42eae0bb55cf4c78670cebd2b6d9addb4f2abd**。本机和80均已同步；root另审资源/路由后才可唯一execute，本agent未execute。现owned四文件为新script、新manifest、本md与对应source_snapshots JSON。

## 10:33：root指定的HPC固定IP HEAD不可达

root另授权仅一次HPC主机HEAD尝试。通过本机既有`/tmp/apex-baseline-hpc-ctl` master进入hpc3，实际执行curl `--head --max-time 20 --connect-timeout 10 --resolve proxy.golang.org:443:142.250.73.145`，URL仍为原`https://proxy.golang.org/github.com/mdlayher/netlink/@v/list`；`--noproxy '*'`确保未借环境代理，未`-k`、未跟redirect、输出正文到/dev/null。**没有建立新SSH转发**。

10:33:54 CST结果为curl rc7、HTTP000、remote_ip空，stderr为`Failed to connect to proxy.golang.org port 443: Connection timed out`；Python墙钟约7.133秒，curl time_total6.206秒。没有建立TCP连接，因而没有TLS握手/实际远端IP或证书验证成功证据；ssl_verify_result=0仍不能当作验证通过。只执行了这一次实际curl；最初元数据launcher因HPC Python3.6不支持capture_output在Popen前报错，没有发起curl，改为兼容stdout/stderr PIPE后才执行该唯一probe。

另在80仅执行`ssh -G hpc3login.hpc.hkust-gz.edu.cn`，rc0：配置peer为**10.120.81.30:22、user qinlucao、identityfile ~/.ssh/id_ed25519_hpc3_hkustgz**，未配置proxycommand。只读取上述元信息，未读密钥内容，也没有由此建立连接或转发。

当前不能将HPC固定IP方案标为可用，故未建立80 localhost38444的-L。若root改用Mac固定IP+reverse方案，需要另审并适配当前route checker：8151版本只接受80上活SSH进程的精确-L参数及同PID listener，不能拿它认证Mac reverse产生的80 listener。当前Mac到该AVG原IP的可达性未测，本轮不追加probe、不改冻结8151/8cff代码或配置，也没有native/claim/锁或成绩。

## 10:38：root建Mac reverse后，校验分支已适配（未准入）

root随后独立完成Mac固定原IP HEAD、专用SSH reverse和80同连接的原URL HEAD，报告HTTP200、TLSverify0、0正文；这些是**root操作**，本agent没有创建转发或追加网络probe。root一次x写的`route-receipt.json`实际SHA为`6d8f90eb63ba0104c2ff8782511ec9f22aa101b5dc8fe955413e9227cdfd0a7d`，原HEAD收据SHA为`ac661562dc38791a9365c6674c87a80b95a95c6b8551b0ebee4490b41a091d14`。原件均保留在新output根，未修改。

root授权修改尚无claim的driver后，**只为route_ready增加mac_ssh_reverse分支**；原无mode/local_ssh_L分支保留。generation240/worker shutdown/源scope、Terminal至123的CPU契约、独立124–127锁/guard、native124/1CPU/4GiB/3000秒和自然双排空逻辑不改。manifest仍为8cff；新script SHA为 **fb5a495bc3fceab502ce6983a905a846b58cf26ba885282849ec938b617292ce**，本机/80同步一致。

新分支只读核：

- mode=mac_ssh_reverse、root_reviewed严格为true；原host/IP/port/URI及127.0.0.1:38444保持。
- root记录的Mac SSH PID84416、ps lstart `Sat Oct 17 10:34:54 2026`、实际ps命令与argv一致；唯一-R精确为`127.0.0.1:38444:142.250.73.145:443`，-S精确为专用`/tmp/apex-t774-route-20261017.ctl`，Master-running PID记录一致。
- 80同连接root sshd PID2206906/startticks870351829/comm=sshd仍在；root同专用control channel采集的祖先链连续，并含user sshd2206946→该connection sshd。原HEAD收据SHA保持。
- 80该端口当前唯一listener严格是127.0.0.1:38444。root-owned sshd FD对当前user不可见，owner_fd_visibility=false；**这里是同连接祖先证据、活connection进程及唯一loopback绑定，不声称直接观测了listener FD归属**，也不要求ss输出不可见的pid字段。原native TLS probe仍必须成功才继续评分。

10:38:45 CST实际defaultprepare rc0、stderr空、41绑定一致：route_ready=true、generation_released=false、当前124–127 scope空，0claim/锁/guard/native。该结果只表明新route metadata门通过，不能替代尚缺的generation永久释放，也不是原生评分成功。

8个离线路由夹具全部通过：Mac正例及原local-L正例GREEN；错误reverse目标、root_reviewed=false、死sshd、实际wildcard listener、非loopback receipt、断裂connection祖先链均RED。首个legacy mock误用了八进制转义模拟cmdline，已仅将测试数据改为显式NUL分隔argv，生产代码/断言没有因此弱化。夹具未连接socket、未修改原route receipt或生产文件。

新版已交Terminal agent独立只读review，root将待两方审阅后决定唯一waiter。本agent没有execute、启动waiter、取得锁、调用ssh/probe或写源marker；当前仍没有native准入或恢复分数。
