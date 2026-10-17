# SWE追加三项：10:10只读审阅

实际采集时间为2026-10-17 **10:09:35–10:10:05 CST**（JSON中的UTC时间为02:09:35–02:10:05）；metadata命令taskset CPU10，未新建native、claim或模型/API请求。只新增本文件和[小收据](source_snapshots/swe_additional_grade_review_20261017_1010.json)，不改live脚本、manifest、原source或canonical分数。

**两项T2已有原生0且有明确产品契约失败证据；NodeBB尚在途，不能提前接0或1。** 全cohort尚未自然收尾，guard及92–95 global锁仍应保留。

| 项 | 原生状态 | 已存reward / exception | 审阅结论 |
|---|---|---|---|
| SWE专家 / Teleport2b | 09:33:54结束 | 0 / null | 题面要求的接口与计数符号未实现，候选编译测试失败；待root独立接纳 |
| AVG64 / Teleport2b | 09:33:50结束 | 0 / null | 同上，独立原生结果；待root独立接纳 |
| SWE专家 / NodeBB | 仍在途 | 无result、无reward | 原Mocha四项必需测试失败，但进程未退出；保持pending/null |

## 两项T2：题面、官方测试与实际编译错误相互对应

分别读取两项自己原task的`instruction.md`和`tests/test_patch.patch`。两者instruction SHA同为`8a9aeafd…afb2`，test patch为`0b40b83b…3df9`；不是借用另一模型的结果。题面11/13行明确要求`Chat.Complete(...)(any, *TokenCount, error)`且可解构恰好三个返回值；17行要求`NewAsynchronousTokenCounter`，21行要求包级`defaultTokenizer`。原官方test patch的37/53/60/69行相应改为三个返回值调用，146/148行调用新增counter及tokenizer。这些是任务要求的产品接口，并非仅由编译失败倒推题意。

两份原`run-script-stderr.txt`均记录：`chat_test.go:118/155/161/173`调用接收三值而`chat.Complete`仍返回两值；`tokencount_test.go:68/84`缺`NewAsynchronousTokenCounter`，70行缺`defaultTokenizer`。原答案均为0B，PatchReplay明确应用nothing；官方test patch应用成功后，14个必需测试0通过，`output.json`为tests=[]，原reward文件为0，Harbor exception=null。因此证据支持**未完成题目要求导致的候选编译失败**，而非将任何编译错误一概当作模型0。

两项原Go workspace preparation均return_code0（专家105.707秒、AVG100.136秒），原cache复制return_code0。原生verifier各运行493.634秒和489.811秒，未耗尽3000秒上限；实际stderr是上述产品接口/符号错误，未见此次失败由DNS、下载或OOM引起的证据。没有修改Go、依赖、测试、原答案或资源预算。

| 资源收尾记录 | 专家T2 | AVG T2 |
|---|---:|---:|
| memory.max | 4294967296B | 4294967296B |
| memory.swap.max | 0 | 0 |
| memory.peak（原生记账） | 4295327744B | 4295540736B |
| memory.events.max | 18038 | 19532 |
| oom / oom_kill | 0 / 0 | 0 / 0 |

接近上限及max事件说明发生过回收压力；不能把max事件当成OOM。两项native scope均已消失。其Harbor child1765422/1765423的`/proc`状态为**Z（zombie，已退出未reap）**，不是仍在执行的评分消费者；parent仍等NodeBB，所以cohort的pending-root-review收据尚未统一落盘。两份原生result SHA分别为`c8172f34…6ee3`和`4a6ae703…4a9a`，完整值保存在JSON。

## NodeBB：四个必需测试已失败，原生退出尚未完成

原7422B patch apply_rc0，原测试patch应用成功。留存Mocha JSON解析通过：335测试、331通过、4失败、0 pending；统计时间为09:25:03.875至09:25:29.613，耗时25.738秒。四个失败恰好是原`fail_to_pass`全部四项：

- group cover移除后文件仍存在，断言true应为false。
- user cover清理调用`User.getLocalCoverPath`，该函数不存在。
- cropped avatar清理调用`User.getLocalAvatarPath`，该函数不存在。
- account删除后残余文件4个，断言应为0。

原NodeBB题面16/33行明确要求两个本地路径函数，18/27行要求清理磁盘文件至0；上述错误与产品要求一致。335项总数包含额外测试，不能把331通过解释为四项必需测试通过。

但10:10采样时`test.sh`→`npm exec mocha`→`node`仍在，node状态S、wchan=ep_poll，原run_script尚未返回；原生result/reward均未出现。**JSON reporter输出测试结果不等于原生评分完成**。已有证据支持候选测试失败，同时存在测试进程长挂的退出问题；准确未关闭handle尚未证明，不改`--exit`、测试或进程。保留原3000秒预算自然终态，约10:15附近可能到达上限，本轮不等待或干预。

NodeBB当前scope实际进程CPU均92，memory.max=4GiB、swap0；采样memory.current782024704B、memory.peak876376064B，max/oom/oom_kill事件均0。此次长挂没有4GiB OOM证据。

## 源身份与租约尚未释放

三项各38个绑定实际SHA均未变，原SIF大小/mtime保持；冻结script SHA仍`7da575a63c408d49727ff52493a0b8b203cd139456db8bdd17bae32b32ea8ace`，manifest仍`b6dcd8442b336e9916d443e4ca7afe80fce2b3252723b00e8c2bc65c1fe2a138`。旧长TMPDIR失败attempt1及其归档保留，不据旧bootstrap异常重写原答卷。

parent1765416/start869931371仍在，NodeBB child1765421仍在。global92–95 FLOCK WRITE实际holder为1765416，剩余scope为`apex-baseline-649dae5c3168.scope`和自有`apex-baseline-swe-additional-1765416.scope`。guard仍32MiB/swap0、CPU92–95。尚无全cohort finished、双native空、guard停止、双完整scope空或unlock证据；本轮不写任何CPU-finished marker，也不宣布租约可领。

原生路径均在80 `artifacts/recovery/swe-additional-short-tmp-20261017/{swe249,avg64}/<原task_id>/attempt1/native/<原task_id>/`；准确output与result identity见JSON。root可独立审原生终态决定overlay，本agent未接分、未重试。
