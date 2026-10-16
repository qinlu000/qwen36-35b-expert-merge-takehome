# HLE现成2k落地与训练接续

2026-10-16 19:14 CST。用户授权寻找更多现成回答并继续。本轮未恢复教师API；原已生成722份合格High回答直接复用。

| 来源 | 训练条数 | 答案依据 |
|---|---:|---|
| NVIDIA Math-v4 |817|V4-Pro High；发布者最终答案参考匹配 |
| 原已接受MMLU-Pro教师回答 |722|此前V4-Pro High；选项与公开gold匹配 |
| NVIDIA Science-v2 |201|明确V4-Pro完整final；effort未记录，无独立gold |
| V4-Pro 8k |82|个人发布者声明教师；工程/人文逐题筛选 |
| GLM-5.1清理池 |16|个人发布者声明教师；原题源追溯不完整 |
| MMLU-Pro参考答案 |162|公开reference短答案监督，不是模型生成或完整推理 |
| 合计 |2000|已物化、0截断 |

八类严格保持原配额：Math817、Biology224、CS193、Other186、Physics184、Humanities175、Chemistry132、Engineering89。现成跨学科池仅11条合适人文，加已生成High2条后，剩162使用原训练储备题的参考选项文字，保留学科覆盖并披露监督形式差别，不编造解释。

MMLU-Pro上游为test/validation；本项目沿用此前冻结的题面分族train/val分区，未冒称上游有官方train。正式HLE只读question排除重合，未读答案选题/训练。Science和broad沿用题面exact/13gram排除及候选holdout；reference来自原已排除的teacher_reservoir。上述不证明完整语义题族独立。

数据相对目录：`artifacts/data/candidates/hle_existing_2k_20261016/swift_ready`，含train.messages/provenance、原val.messages/tasks/provenance及summary；Mac、80、HPC均已落地。80项目根`/data/caoqinlu/projects/apex-takehome`；HPC根`/data/user/qinlucao/projects/apex-takehome`。

完整序列 **1,125,593 tokens /max4043**；正文793188/max3977。按Base非思考template计数，64K/8K内自然保留，0截断；原100val三个文件逐字节相同。训练文件只有role/content，无隐藏reasoning或think正文。

实现：[Math/Science材料化](../scripts/materialize_hle_existing_math_science.py)、[跨学科固定筛选清单](../scripts/materialize_hle_existing_broad.py)、[组合及长度检查](../scripts/prepare_hle_existing_2k.py)。Science补读16MiB；broad缓存V4约547MB＋GLM四段48MiB。逐条来源revision/ID、助手逐题排除及未披露effort保留，无新增数据hash工程。

训练安排：HLE726647双卡/180G/12CPU，world2/global8/r16/一epoch/64K，当前排队无optimizer。Mixed实际7073/249，四份新分区各一次，新目录`mixed_existing_hle2k_20261016`，旧5573未覆盖；旧held且0步726346取消，新726649四卡afterok:SWE726335。

Terminal原726345在16步首次验证OOM，无checkpoint；最小FLCE eval包装CPU红→绿，完整数据和预算不变。新726648四卡afterany:HLE726647及旧Base服务725705，不操作Base，仅以自然释放作资源依赖。真实GPU首次完整验证尚待完成。[修复证据](terminal_eval_oom_fix_20261016.md)

资源覆盖Base迁移短暂重叠：Base至多10＋SWE4＋HLE2≤16；旧B释放后Base至多8＋Terminal4＋SWE/Mixed4≤16。只取消本轮0步旧Mixed，未改其他项目或Base作业。

保留的不确定项：162条人文短答案缺少完整过程监督；Science/broad缺独立gold或effort，不能称全部High或逐题正确；工程偏电化学/材料/水文，题源/语义题族不完整；类别匹配不保证难度/小类匹配。GLM官方HLE31.0/GPQA86.2对Base21.4/86.0仅为跨发布方支持性证据，非同预算实测。GPU显存结果仍待新作业eval。
