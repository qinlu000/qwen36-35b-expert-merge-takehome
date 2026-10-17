# SWE追加cohort：自然收尾与root原生评分审核

root于2026-10-17 10:15:55及随后只读复核。机器[收据](source_snapshots/swe_additional_grade_final_review_20261017.json)保留原父状态、全部3×38绑定、SIF stat及各原生结果身份；原生结果与原答卷不修改。

## 完整自然收尾

唯一parent1765416/start869931371已退出，最终finished_pending_root_review；NodeBB自然到达原3000秒verifier上限后退出，没有提前kill或放宽时限。10:15:01.470/03.531两次native scope空→停止自有guard→10:15:03.597/05.657两次完整scope空→10:15:05.711释放global92–95锁。root再次实核池空、Terminal未接管，原3×38小文件和SIF stat均保持。没有写ASI或Terminal完成marker。

## 分别接受两份自身T2原生0

| 模型 | 新原生结束CST | reward / exception | 独立结果SHA前缀 |
|---|---|---|---|
| SWE专家 | 09:33:54.206 | 0 / null | c8172f34350ee745 |
| AVG64 | 09:33:50.217 | 0 / null | 4a6ae703fec7403a |

root分别重读各自原task、官方test patch、实际run-script stdout/stderr及资源事件：题面明确要求`Complete`返回三值、新增`NewAsynchronousTokenCounter`与`defaultTokenizer`；各自原0B patch仍保留两值/缺符号，官方编译精确到达对应接口错误。两项原cache复制和Go workspace prep成功，原生reward文件0且无Harbor异常；14个必需测试没有通过，**编译被阻断，并非14个测试均实际执行失败**。保存的4GiB/swap0事件OOM/OOMkill均0，max事件/内存回收压力仍照录。

两项独立原结果、generation模型、原patch、原测试/SIF以及1CPU/4GiB/3000秒保持；不因空patch相同而借另一模型评分。root已把各自exact结果接入专家/AVG的native-zero manifest，批准计数变为8/5；旧timeout或missing-reward原件继续保留。这里只解决评分有效性，不按reward选答案或checkpoint。详见[完整测试与产品契约审阅](swe_additional_grade_review_20261017_1010.md)。

## NodeBB另作完整官方报告审核

NodeBB新result为VerifierTimeoutError、原生reward null（SHA a7109bb07f12df02…），不能加入native-zero名单。其Mocha已输出335条、331通过/4失败，但必须按原官方parser去重并核对完整required集合、失败映射和同Base规则，才能判断是否可单独审定；原退出异常始终保留。本收据采集时该解析审核仍pending，不根据EXIT trap的reward1判成功，也不把缺失填0。

本轮没有模型/Judge调用或再次原生评分。初次长TMPDIR启动失败的3份null和冻结源码仍留在独立历史目录，不能混作本次原生成绩。
