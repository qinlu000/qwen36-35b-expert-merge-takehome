# SWE固定51任务对照与生成退出元数据

只读更新于**2026-10-17 11:14:44 CST**，来源canonical汇总时点为**11:14:04 CST**，按冻结51个task ID字典序列出全部任务。Base **10/51=19.607843%**，SWE249专家 **0/51=0%**，两者均51有效；**Base原通过的10题在专家中全部退化为有效0**。负面结果保留，不改变checkpoint、训练配方或主AVG64身份。

AVG现为**51/51有效、4通过、0项null，完整主分4/51=7.843137%**。最后T7744仅使用root批准的同原答案native0，未借用专家结果或重新生成。机器可读数据见[JSON](swe_task_comparison_20261017.json)与[CSV](swe_task_comparison_20261017.csv)。

## 配对结果

|比较|双方通过|仅参考通过|仅候选通过|双方未通过|有效配对/未配对|
|---|---:|---:|---:|---:|---|
|专家（候选）vs Base|0|10|0|41|51/0，完整|
|AVG（候选）vs Base|2|8|2|39|51/0，完整|
|AVG（候选）vs 专家|0|0|4|47|51/0，完整|

AVG与Base共同通过的是Ansible e9e60012、Qutebrowser e70f5b03；新增通过的是Navidrome bf2bcb12、Qutebrowser c09e1439。Base其余8个通过项在AVG为0。Teleport7744现为root核审的有效0，故全部51题均完成配对。该题通过原TLS通路后，空候选未声明原题要求的netlinkv1.6.0，动态依赖解析至v1.11.2并因原Go缺少iter而编译阻断；TestSendEvent未执行，不能称功能断言失败。

专家−Base **-19.607843个百分点，95% CI [-31.372549,-9.803922]**；AVG−Base **-11.764706个百分点，95% CI [-23.529412,0]**。均直接引用80已有`artifacts/eval/final_aggregation_20261017/summary.json`（03:14:04.716305 UTC，即11:14:04 CST；各自`comparisons.<模型>_vs_base.benchmarks.swe`），本轮**不重跑bootstrap**。固定任务的配对CI不消除历史环境、并发、排程及已披露评分恢复差异，不能据此认定纯权重因果。

## 专家生成元数据

51份已捕获`agent/model.patch`均存在：**43空、8非空**。它只描述保存产物的字节数；非空不证明每个差分都由模型显式编辑，也不把空patch与某个终止原因等同。

|捕获patch|exit_status=BadRequestError|exit_status=unknown|合计|
|---|---:|---:|---:|
|空|30|13|43|
|非空|4|4|8|
|合计|34|17|51|

34个BadRequestError均有自己的最后一条request元数据明确记录`status=rejected/error=context_budget_exceeded`。这是固定上下文预算guard拒绝继续准入的记录，不能说所有工具调用都400，也不是把0 resolved倒推为infra。其余17个trajectory.info.exit_status实际为空，规范化为**unknown**，没有猜成Submitted。

原generation **trial** 的exception_info统计为：none32、NonZeroAgentExitCodeError17、VerifierTimeoutError1、RewardFileNotFoundError1。17个unknown exit_status对应17个NonZeroAgentExitCodeError，但没有据此推断更细根因；trial异常还可能发生在后续verifier阶段，不能一概当agent终止原因。只解码每个trajectory开头的info元数据，未复制消息、题面或答案；详细原路径和每项最后request引用保留在JSON/CSV。

## 全部固定任务

1=resolved、0=有效未解决、null=未判/invalid。AVG“升/降”仅指当前已有效配对的同题观察差异。

|task_id|Base|专家|AVG|AVG对Base|专家patch字节|专家exit_status|
|---|---:|---:|---:|---|---:|---|
|instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e|0|0|0|同为0|7422|BadRequestError|
|instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf|0|0|0|同为0|0|BadRequestError|
|instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86|0|0|0|同为0|0|unknown|
|instance_ansible__ansible-c1f2df47538b884a43320f53e787197793b105e8-v906c969b551b346ef54a2c0b41e04f632b7b73c2|0|0|0|同为0|0|BadRequestError|
|instance_ansible__ansible-d33bedc48fdd933b5abd65a77c081876298e2f07-v0f01c69f1e2528b935359cfe578530722bca2c59|1|0|0|降|10153|unknown|
|instance_ansible__ansible-d62496fe416623e88b90139dc7917080cb04ce70-v0f01c69f1e2528b935359cfe578530722bca2c59|1|0|0|降|0|unknown|
|instance_ansible__ansible-d72025be751c894673ba85caa063d835a0ad3a8c-v390e508d27db7a51eece36bb6d9698b63a5b638a|0|0|0|同为0|0|unknown|
|instance_ansible__ansible-de5858f48dc9e1ce9117034e0d7e76806f420ca8-v1055803c3a812189a1133297f7f5468579283f86|0|0|0|同为0|0|unknown|
|instance_ansible__ansible-e9e6001263f51103e96e58ad382660df0f3d0e39-v30a923fb5c164d6cd18280c02422f75e611e8fb2|1|0|1|同为1|0|BadRequestError|
|instance_element-hq__element-web-5dfde12c1c1c0b6e48f17e3405468593e39d9492-vnan|0|0|0|同为0|26149162|unknown|
|instance_element-hq__element-web-66d0b318bc6fee0d17b54c1781d6ab5d5d323135-vnan|0|0|0|同为0|0|unknown|
|instance_element-hq__element-web-772df3021201d9c73835a626df8dcb6334ad9a3e-vnan|0|0|0|同为0|24350422|BadRequestError|
|instance_element-hq__element-web-ecfd1736e5dd9808e87911fc264e6c816653e1a9-vnan|0|0|0|同为0|26134805|BadRequestError|
|instance_flipt-io__flipt-2ca5dfb3513e4e786d2b037075617cccc286d5c3|0|0|0|同为0|0|unknown|
|instance_flipt-io__flipt-3d5a345f94c2adc8a0eaa102c189c08ad4c0f8e8|0|0|0|同为0|0|BadRequestError|
|instance_flipt-io__flipt-524f277313606f8cd29b299617d6565c01642e15|0|0|0|同为0|0|BadRequestError|
|instance_flipt-io__flipt-c1728053367c753688f114ec26e703c8fdeda125|0|0|0|同为0|0|BadRequestError|
|instance_flipt-io__flipt-c188284ff0c094a4ee281afebebd849555ebee59|0|0|0|同为0|0|BadRequestError|
|instance_flipt-io__flipt-cd18e54a0371fa222304742c6312e9ac37ea86c1|0|0|0|同为0|0|BadRequestError|
|instance_flipt-io__flipt-e2bd19dafa7166c96b082fb2a59eb54b4be0d778|1|0|0|降|0|BadRequestError|
|instance_future-architect__vuls-5af1a227339e46c7abf3f2815e4c636a0c01098e|0|0|0|同为0|0|BadRequestError|
|instance_future-architect__vuls-ca3f6b1dbf2cd24d1537bfda43e788443ce03a0c|1|0|0|降|0|BadRequestError|
|instance_future-architect__vuls-e1fab805afcfc92a2a615371d0ec1e667503c254-v264a82e2f4818e30f5a25e4da53b27ba119f62b5|0|0|0|同为0|0|BadRequestError|
|instance_future-architect__vuls-ef2be3d6ea4c0a13674aaab08b182eca4e2b9a17-v264a82e2f4818e30f5a25e4da53b27ba119f62b5|0|0|0|同为0|0|BadRequestError|
|instance_gravitational__teleport-1316e6728a3ee2fc124e2ea0cc6a02044c87a144-v626ec2a48416b10a88641359a169d99e935ff037|1|0|0|降|26655|unknown|
|instance_gravitational__teleport-2b15263e49da5625922581569834eec4838a9257-vee9b09fb20c43af7e520f57e9239bbcf46b7113d|0|0|0|同为0|0|BadRequestError|
|instance_gravitational__teleport-65438e6e44b6ce51458d09b7bb028a2797cfb0ea-vce94f93ad1030e3136852817f2423c1b3ac37bc4|1|0|0|降|0|unknown|
|instance_gravitational__teleport-7744f72c6eb631791434b648ba41083b5f6d2278-vce94f93ad1030e3136852817f2423c1b3ac37bc4|0|0|0|同为0|0|BadRequestError|
|instance_gravitational__teleport-eda668c30d9d3b56d9c69197b120b01013611186|0|0|0|同为0|0|unknown|
|instance_gravitational__teleport-f432a71a13e698b6e1c4672a2e9e9c1f32d35c12|0|0|0|同为0|87741142|BadRequestError|
|instance_internetarchive__openlibrary-0dc5b20fa186f9714f8a838178597e69f549d026-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59|0|0|0|同为0|0|BadRequestError|
|instance_internetarchive__openlibrary-322d7a46cdc965bfabbf9500e98fde098c9d95b2-v13642507b4fc1f8d234172bf8129942da2c2ca26|0|0|0|同为0|0|BadRequestError|
|instance_internetarchive__openlibrary-53d376b148897466bb86d5accb51912bbbe9a8ed-v08d8e8889ec945ab821fb156c04c7d2e2810debb|0|0|0|同为0|0|BadRequestError|
|instance_internetarchive__openlibrary-630221ab686c64e75a2ce253c893c033e4814b2e-v93c53c13d5f9b383ebb411ee7750b49dcd1a34c6|1|0|0|降|0|unknown|
|instance_internetarchive__openlibrary-6e889f4a733c9f8ce9a9bd2ec6a934413adcedb9-ve8c8d62a2b60610a3c4631f5f23ed866bada9818|0|0|0|同为0|0|BadRequestError|
|instance_internetarchive__openlibrary-7cbfb812ef0e1f9716e2d6e85d538a96fcb79d13-vfa6ff903cb27f336e17654595dd900fa943dcd91|0|0|0|同为0|0|BadRequestError|
|instance_internetarchive__openlibrary-a48fd6ba9482c527602bc081491d9e8ae6e8226c-vfa6ff903cb27f336e17654595dd900fa943dcd91|1|0|0|降|0|BadRequestError|
|instance_internetarchive__openlibrary-b67138b316b1e9c11df8a4a8391fe5cc8e75ff9f-ve8c8d62a2b60610a3c4631f5f23ed866bada9818|0|0|0|同为0|0|BadRequestError|
|instance_navidrome__navidrome-69e0a266f48bae24a11312e9efbe495a337e4c84|0|0|0|同为0|0|BadRequestError|
|instance_navidrome__navidrome-874b17b8f614056df0ef021b5d4f977341084185|0|0|0|同为0|0|BadRequestError|
|instance_navidrome__navidrome-bf2bcb12799b21069f137749e0c331f761d1f693|0|0|1|升|0|unknown|
|instance_protonmail__webclients-08bb09914d0d37b0cd6376d4cab5b77728a43e7b|0|0|0|同为0|0|BadRequestError|
|instance_protonmail__webclients-5f0745dd6993bb1430a951c62a49807c6635cd77|0|0|0|同为0|0|BadRequestError|
|instance_protonmail__webclients-715dbd4e6999499cd2a576a532d8214f75189116|0|0|0|同为0|0|BadRequestError|
|instance_protonmail__webclients-c5a2089ca2bfe9aa1d85a664b8ad87ef843a1c9c|0|0|0|同为0|0|BadRequestError|
|instance_protonmail__webclients-e65cc5f33719e02e1c378146fb981d27bc24bdf4|0|0|0|同为0|0|BadRequestError|
|instance_qutebrowser__qutebrowser-3e21c8214a998cb1058defd15aabb24617a76402-v5fc38aaf22415ab0b70567368332beee7955b367|0|0|0|同为0|19834|unknown|
|instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af574386e277dd2388d094-v2ef375ac784985212b1805e1d0431dc8f1b3c171|0|0|1|升|0|unknown|
|instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd503a7cef07462bd16b4-v363c8a7e5ccdf6968fc7ab84a2053ac78036691d|0|0|0|同为0|0|unknown|
|instance_qutebrowser__qutebrowser-e70f5b03187bdd40e8bf70f5f3ead840f52d1f42-v02ad04386d5238fe2d1a1be450df257370de4b6a|1|0|1|同为1|0|BadRequestError|
|instance_tutao__tutanota-f373ac3808deefce8183dad8d16729839cc330c1-v2939aa9f4356f0dc9f523ee5ce19d09e08ab979b|0|0|0|同为0|0|unknown|

## 来源与边界

- base：`artifacts/results/base-gap-completion-20261017/swe51_summary.json`，逐题score仅使用该owner有效行；各summary SHA与as_of记录于JSON。
- swe249：`artifacts/eval/swe249_audited_hard51_20261017/summary.json`，逐题score仅使用该owner有效行；各summary SHA与as_of记录于JSON。
- avg64：`artifacts/eval/avg64_swe_audited_hard51_20261017/summary.json`，逐题score仅使用该owner有效行；各summary SHA与as_of记录于JSON。

固定ID manifest为`analysis/source_snapshots/protocol/swe_hard_task_ids.json`。逐题原生/审计结果路径在JSON/CSV；Base/专家/AVG均51有效、0null，与各source summary一致。NodeBB显式parsed-report审定与raw timeout/null、EXIT-trap文件1分开保留，本表不重判它。

本轮0生成、测试/native、Judge/API、collector及bootstrap；不改来源评分、原轨迹、模型、checkpoint或主模型。

10:29的50有效/1null历史由Git版本保留。本次仅更新最后AVG T7744的有效性、原生结果/审定来源与完整配对汇总；51项专家patch字节数、退出诊断和其余逐题行保持不变。来源owner summary和canonical的当前时点/SHA记于JSON，CSV固定LF行尾。
