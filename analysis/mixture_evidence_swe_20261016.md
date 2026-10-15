# SWE 数据配比与提分：一手实证核查

2026-10-16；范围：仓库修复、SWE-bench Pro，补充 Verified 的可迁移证据。
本轮用 ego-browser 实读论文 HTML 与数据卡；只读方法和统计，未读取正式测试答案／补丁、下载样本或运行模型。
遵循 [最新预算重设计](sft_budget_redesign_20261016.md)：不恢复旧 6M／15M 默认值，不增加正式训练分支。

## 结论与证据等级

- 有可参考经验，但尚无“我们的四 benchmark 应按某固定百分比混合”的直接受控证据。
- 对 SWE，优先级更明确：评测接口匹配、干净有效行为、独立任务覆盖，再考虑来源／语言／难度配比。
- 本次找到的直接 Pro 选样消融以 SWE-Prime 最有用；Orchard、SWE-smith 的主要配比消融在 Verified，不能写成 Pro 提升。
- 多篇论文的“同超参数”不是等训练 token／等优化步数；样本百分比也不能当 token 百分比。

## 1. Orchard：与 mini 接口适配，比现成来源百分比更可靠

一手：[论文 §3、表5／9／10](https://arxiv.org/html/2605.15040v1)、[官方仓库](https://github.com/microsoft/Orchard)。
底座 Qwen3-30B-A3B-Thinking；SFT 5 epoch、batch 128、64K，推理扩到 128K；之后另有 RL，须分开报告。
最终 SFT 数据 107,185 条、19,287 个独立任务，平均约 21K token；不是 107K 独立题。

| 来源／教师／harness | 成功 | 失败（仅有效片段监督） | 合计 |
| --- | ---: | ---: | ---: |
| Scale-SWE／MiniMax-M2.5／mini | 33,527 | 20,591 | 54,118 |
| SWE-rebench／MiniMax-M2.5／mini | 13,364 | 10,099 | 23,463 |
| SWE-rebench／Qwen3.5-397B／mini | 15,545 | 1,846 | 17,391 |
| SWE-rebench／MiniMax-M2.5／OpenHands | 12,213 | 0 | 12,213 |

这些按记录数约为 50.5／21.9／16.2／11.4%，是收集结果；论文没有证明该比例最优，也没有等 token 的比例搜索。
SWE-rebench V2 被完整留给 RL；不能把表5解释为三个来源都在 SFT 混合。

表10：12K 成功轨迹、SWE-rebench、MiniMax-M2.5、同 SFT 配方，评测为 Verified 500：

| 训练 harness | 评测 mini | 评测 OpenHands |
| --- | ---: | ---: |
| mini | 57.9 | 19.0 |
| OpenHands | 28.0 | 53.5 |

同一行只切换评测 harness，最直接表明接口敏感；两种训练 harness 的轨迹不应冒称逐 token 相同。
文中未钉这张表的 harness commit／版本、等 processed-token 预算，不能外推为我们 mini 版本的预期分数。
主 SFT 模型在 mini Verified 为 64.3，SFT+RL 67.5；该差值不是数据配比效果。

表9固定配方，只改样本量／选择器：随机 512／1,024／2,048 条得 45.8／50.3／52.8。
同 512 条，集中仓库 47.9、分散仓库 44.0；到 2,048 条为 53.4／52.2。
这说明极小预算下“每仓库薄薄一点”未必最好；不能一概宣称最大仓库多样性最优。这里固定记录数，未证等 token。
失败片段实验：32K 成功得 59.3，增加约 32K 失败有效片段后 61.2。
虽作者称 scale-matched，实际总记录从 32K 到约 64K，未等 token／步数，不能把 +1.9 单独归因 mask。

对我们：优先检查 mini 工具语法、观察、结束方式；来源百分比只作候选构成信息。Thinking 教师内容必须按当前 no-think 规则清理后重新计量。

## 2. SWE-Prime：直接 Pro 证据支持“挑好过程”，不支持随机砍到 10%

一手：[论文主表与 Experimental Setup／RQ2](https://arxiv.org/html/2608.27449v1)。
训练池为 Nebius SWE-rebench OpenHands 的 67,074 条 Qwen3-Coder-480B 轨迹，其中 32,161 条成功。
10% 指成功轨迹记录数，约 3,216 条；不是 10% token、10%训练时长或 10%独立任务。
两阶段同时做：过程／补丁质量与 issue 聚类选样；保留完整上下文，仅高价值语义片段进入 loss。

| Qwen3-Coder-30B-A3B-Instruct | Verified | Pro public 731 |
| --- | ---: | ---: |
| 原模型 | 44.8 | 29.55 |
| 成功全池 SFT | 51.0 | 31.05 |
| 随机 10% SFT | 41.2 | 27.22 |
| 精选 10%，仅阶段1 | 50.2 | 30.92 |
| 精选 10%＋片段 mask | 53.2 | 34.75 |

同样的随机 10% 能比原模型更差；“少量一定足够”无依据。
最终 Pro 比全池高 3.70 个百分点，是 quality＋代表性＋mask 的复合结果；阶段1单独没有超过全池 Pro。
训练 max length 131,072、batch32、峰值 LR4e-6；评测 max100 turns／131K。
论文写相同训练配置，但未明确等总 token／步数／epoch预算；评测段未钉具体 harness 版本，不能默认我们的 mini。
10% 与阈值7是在 Verified 上选出的，再冻结用于 Pro；Verified 本身不是完全独立的调参外测试。
结果支持有用段监督，而非机械截尾；其补丁范围／片段打分使用训练任务 reference patch。
对我们：先用简单规则去空转／非法工具／泄漏，保留定位→编辑→验证与有效恢复过程；不立即复制复杂 LLM 打分管线。
若采用局部 mask，应在共同 manifest 中一致作用于专家与 Mixed；不可用正式 Pro 补丁选样或评分。

## 3. Open-SWE-Traces：语言覆盖有证据，但数据已更新，旧比例不可沿用

一手：[v1论文表5](https://arxiv.org/html/2606.16038v1)、[当前官方 README](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/main/README.md)。
旧论文：Qwen3-30B-A3B 系列，训练131K／3 epoch，评测256K／250 turns；Verified／Multilingual／Pro均三次均值。
表5 no-think：Python-only→全语言，Verified 58.6→59.8、Multilingual 43.1→57.1。
成功-only→全池，Verified 57.7→59.8、Multilingual 49.6→57.1；这里没有 Pro 的对应配比消融。
两类比较增加了数据量，未给等 token 控制；不能据此断言失败轨迹本身或特定语言比例是收益原因。
旧池九语言，MiniMax thinking／Qwen3.5 non-thinking，约 51.7% thinking 是记录占比，不是最优混合比。
当前 README 的 v1.0 已在 08/26 删 git-hacking，从旧 207K 变约151K；旧论文统计不代表当前下载内容。
v1.1 有 Qwen3.6-27B／DeepSeek-V4-Flash-0731，v1.2 有 Qwen3.8；均增加 mini 来源，须固定 revision/config。
当前卡的 resolved 可为 -1（未知）；不可把未知当成功。许可 CC-BY-4.0，仓库另有许可。
对我们：按 Pro 涉及的 Python／Go／JS／TS 做覆盖审计；不只喂 Python，也不直接照九语言全池比例。
先按来源、teacher、harness、清后长度统计；论文 no-think 优势不等于删 teacher think 后仍有同样收益。

## 4. SWE-smith：别重复简单题，也没有“越难越好”的单调证据

一手：[论文 §4.1、表4／5与 §2.1](https://arxiv.org/html/2504.21798v1)。
主要消融为 Qwen2.5-Coder-Instruct-7B、Claude3.7 teacher、SWE-agent、Verified；不是 Qwen3.6／Pro。
不同造题策略最终各用507条成功轨迹：PR Mirror9.2、LM Rewrite8.8、Procedural8.6、LM Modify5.7。
“#Trajs”原表列的是收集量，比较时实际按最少507封顶；是等记录数，未证等 token。
等500条、难度混合均值2／4／6／8，Verified为12.4／10.8／13.6／12.2；没有越难越强的趋势。
正式5,016条配方对每原任务最多保留3条成功轨迹，避免重复易题占满；这是配方启发，非已证明最优上限。
等700条多仓库实验支持增加仓库覆盖，但与 Orchard 小规模集中仓库结果不同，受池／底座／任务形态影响。
对我们：保留短中长、不同修复行为；先每任务族一条，优先增加独立题，而非给同易题大量teacher变体。

## 执行边界

- 上述数据源与正式评测仍需按 repo／PR／原 issue／版本关系去同源；来源自称去污染不等于通过我们的四项过滤。
- no-think、64K评测／8K单次输出与这些论文并不等价；清理后记录 L、窗口processed P、监督 S、独立任务 N。
- 不用正式 Base 失败题反推训练配比；仅用已冻结独立 dev 的聚合弱项和公开任务形态调整优先级。
- 当前最可行动的是：合格 mini 轨迹优先、四语言覆盖、过程质量过滤、任务去重；最终规模仍由可用供给和训练成本决定。
- 未发现可直接支撑“把三个专家固定按某 token 百分比混合即可提高四 benchmark”的 SWE 侧证据。
