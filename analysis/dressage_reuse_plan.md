# 四张H100的简化专家合版方案（讨论稿v2）

状态：仅规划，未批准恢复实验代码或执行。2026-10-15约18:32 CST，按最初约15:20的71h倒计时估计，保留最后12h后，核心时间约55–56h；真实截止以平台倒计时为准。本稿更新初稿的12M token与6候选预算，其余题面硬要求不变。数字是预算起点，不是吞吐实测或提升承诺。

## 1. 主线

借鉴Occamy“同底座、不同专长分支、参数合成一个模型”的结构。采用Qwen3.6-35B-A3B、三个独立SFT LoRA专家、一个同数据混训对照、AVG/TIES两种合版。训练执行用ms-swift，正式评测用各自官方runner。Dressage不作为整套运行依赖。

领域专家指三个独立微调checkpoint，不是给底座内部256个MoE专家重新分工或新增推理路由。最终产物只有一套参数，保留完整视觉权重与processor。

## 2. 逐项复用边界

Dressage源码固定于 `3e3142fe8ea07e4504c3b20a936a4c201a3de44c`。以下可拆用判断基于源码职责/依赖，尚未运行验证；若抽取源码保留相应上游许可和来源。

| 部分 | 分类与处理 | 本项目仍需完成 |
| --- | --- | --- |
| [TrajectorySegment](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/trajectory_store.py#L44) | 借用字段设计，不引入完整内存会话store | 离线messages/tools、来源、任务/轨迹/段ID、结束状态及训练清单映射 |
| [Qwen36TITOTokenizer](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/tito/tito_tokenizer.py#L216) | 轻依赖辅助，可参考/抽取token一致性校验；离线SFT本身不需要增量TITO | 使用固定官方tokenizer/chat template一次渲染，校验thinking/tool边界；图文processor路径另验 |
| [prompt_assistant_mask](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/last_step/prompt_assistant_mask.py#L206) | 参考“mask不改变原始token”的校验思路，不能原样用；默认注册是qwen3_5，未匹配时可能仅监督最后输出 | 优先训练框架assistant-only loss，按离线轨迹实现必要mask，并用独立样例核对labels |
| [multi_segment](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/multi_segment.py#L118) | 借用段顺序/父轨迹/完整状态思路；代码含Slime Sample与anchor reward语义，不直接导入 | 长轨迹按工具回合切段，保留必要前置状态，仅监督新增输出，避免重叠前缀重复计loss |
| [Harbor artifacts](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/integrations/harbor/artifacts.py) | 可借用稳定ID、失败阶段、attempt、原始产物索引；完整模块不整体搬入 | 保存简单JSONL/原始runner目录，保留所有失败和重试，无需proxy会话持久化系统 |
| [convert_samples](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/convert_samples.py#L89)、[Harbor在线接口](https://github.com/Accio-Lab/Dressage/tree/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/integrations/harbor) | 本轮不用；转换、DataSource和rollout用于Slime在线RL、奖励及分组归一化 | 离线SFT reader与正式评测分别用各框架现有入口，不把RL接口当通用评测wrapper |
| [ms-swift四卡近邻示例](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/examples/models/qwen3_5/transformers.sh) | 直接复用训练器、优化器、保存/恢复、数据入口与导出能力，适配配置 | 换准确base/revision、目标模块、模板、数据、长度、batch与Slurm启动；现成示例不是目标模型四卡实测 |
| [TIES实现](https://github.com/prateeky2806/ties-merging/tree/44e7891fc84f3de7e4caa52664cd864ca3715e91) / PEFT | 复用标准LoRA语义与TIES数值核心，不自创合版算法 | 同base的dense delta构造、模块映射、归一化/scale与完整模型导出 |
| 四项官方runner | 直接复用固定官方实现与原始产物格式 | endpoint、judge、资源与种子配置、启动薄封装和结果归档；不统一改为Dressage agent/奖励 |

不引入：HDPO、SAO、GRPO、在线教师rollout、Ray/Megatron迁移、TransferQueue、旧策略logprob/advantage、路由重放、第四专家、KnOTS/DARE额外方法或合版后再训练。不是断言这些不能四卡运行，而是本题当前窗口没有必要为其适配付出成本。[Dressage公开35B示例](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/examples/scripts/run_dressage_claw_qwen3.6_35b_a3b_sync_4_node.sh)本身是32卡GRPO，并非Occamy全套配方。

## 3. 自己实现的范围

以下名称只是后续拟建入口，目前没有创建实验代码。

| 拟建部分 | 最小职责 |
| --- | --- |
| prepare_data | 来源/许可/污染审计，按repo/问题/模板家族切train与两类dev，统一messages/tools/mask，计算token与manifest；训练数据验证只使用独立训练任务 |
| merge_experts | 恢复带实际scaling的dense delta，执行AVG/TIES，加回同一base；保留视觉/processor/chat template，记录配方与hash |
| run_eval + 配置 | 调用官方runner，固定模型服务、agent、预算、容器、judge和五组TB种子，保存全部任务状态；不开发新的agent平台 |
| summarize | 逐任务对齐、四项宏平均、配对bootstrap、TB/ASI分簇、成本、曲线与至少20例失败分析；原始结果保持可追溯 |

训练配置和Slurm脚本只做薄封装；权重上传/下载、adapter保存、推理API服务使用现成工具。Judge若需要不同供应商适配，属于评测接入，必须独立校准并披露，不能改变正式参考答案或用结果选参数。

## 4. 数据与训练预算

| 训练对象 | 目标项 | processed token起点 |
| --- | --- | ---: |
| E-code | SWE Pro | 0.9M |
| E-terminal | TB2 | 0.9M |
| E-science | HLE + ASI | 1.2M |
| 混训对照 | 四类独立dev | 3.0M |
| 累计 | 四次真实训练 | 6.0M |

三个专家均从相同base独立开始。混训使用与专家累计训练相同的样本及出现次数、格式和mask；共同保留样例若重复计入专家训练，对照同样计入。不能仅匹配监督token而忽略工具观测的计算量，同时记录processed与supervised token、padding和实际GPU时间。

该token划分仅为时间预算：不保证足够形成专长或达到+3pp。冻结训练数据前，根据长度分布上的实测吞吐统一缩放专家与混训token，不把某个对象降为smoke test。原12M不再是默认。本轮不做大规模在线数据生成；修复/终端优先审计公开轨迹，科学既需多学科问答也需工具工作流，数学数据不能代表全部HLE/ASI。

候选训练设置：BF16 LoRA、统一r=16、一轮、文本full/linear attention投影与shared MLP；冻结视觉、router、routed专家、embedding/head。保持各分支目标布局一致。训练长度以8K上限讨论，按回合组织长轨迹，不能机械截掉答案或凭空生成缺失状态。实际module、学习率/batch/长度由环境与独立dev确定，不能照抄旧q_proj/v_proj名单。只保存少量checkpoint，固定间隔记录train/val loss。

按8h训练段并预留20%验证/保存开销，6M processed token要求训练时约261非padding token/s；12M则约521。吞吐须按实际长度/格式测量，不以无loss的工具观测token不计计算。4卡训练串行完成四次，不同时再默认分出四卡做推理。

## 5. 两种合版，最多四个候选

实际更新为 `Delta_i = scaling_i * B_i * A_i`；不分别平均A/B。未训练的base参数原样保留。

- 起点仅两候选：AVG等权平均、TIES（预设density=0.2、符号一致的disjoint mean），均以global scale=1为起点。
- 若时间允许，两法各追加scale=0.5，总计最多四候选；不继续搜索density或层级系数。
- 固定四类独立merge-dev的宏平均与退化规则，选唯一最终模型；记录delta范数/方向冲突用于解释。
- 不压缩SVD，不增加推理时投票/adapter路由。最终可导出完整BF16权重，各专家发布adapter与base引用；预留导出及上传时间。
- 混训对照先在独立dev比较，若不做四项正式全评，结论仅限dev。相同rank的混训与三专家合版仍有有效更新秩差异，不能声称已完全隔离容量因素。

## 6. 正式评测保留题面要求

| 模型 | SWE | HLE | ASI | TB2 |
| --- | --- | --- | --- | --- |
| Base | 全量 | 全量 | 全量 | 全量×5 |
| E-code | 全量 | — | — | — |
| E-terminal | — | — | — | 全量×5 |
| E-science | — | 全量 | 全量 | — |
| 最终合版 | 全量 | 全量 | 全量 | 全量×5 |
| 混训/其他候选 | 独立dev | 独立dev | 独立dev | 独立dev |

SWE V2 HARD-51/locked protocol并fresh-image replay；HLE建议完整2500含图无工具；ASI建议open seed31415的60任务×四层、一次run并披露与榜单重复数差异；TB89任务×五组种子，保留题定32CPU/48GB/3h等全部预算。更详细版本与协议见原笔记。

最低正式量仍为SWE153次并另做replay、HLE7500次生成/判分、ASI720个条件、TB1335 trials。三专家主要节省训练/管理，不能减少这些全量任务。训练前冻结协议与manifest，独立dev选checkpoint和合版；固定全部最终权重后再查看正式成绩，不从测试反馈迭代方案。

## 7. 剩余时间与资源门槛

| 后续阶段 | 条件预算 |
| --- | ---: |
| 环境、数据、协议与可行性验证 | 3h |
| 四次训练、验证及保存 | 8h |
| 合版、独立dev及最终冻结 | 3h |
| 正式全量评测 | 36h |
| 统计、失败分析、上传及报告 | 5h |
| 合计 | 55h，另保留原最后12h |

这是条件排期，不是已经证明的耗时。CPU镜像准备/数据处理可在训练期间进行；共享四卡的训练和推理时间不可重复计算。正式评测按冻结checkpoint组织模型加载，同一模型下并行调度不同benchmark，不依赖未验证的adapter热切换。

### 必须落实的三个条件

1. **容器与CPU沙箱资源。** 80当前未找到运行时，128逻辑CPU即使全可用，TB每trial32CPU也至多保障4路。1335 trials要在36h完成，假设平均30min，理想最低约19路/608CPU/912GB RAM，尚未计长尾、其他任务和错误；80不能单独承担这个承诺。需落实额外兼容CPU节点/沙箱，或者讨论资源/时限。
2. **四卡与稳定端点。** 本机SSH到hpc3已验证，但实际计算节点训练/推理尚未验证；80到HPC账号鉴权、评测容器到模型服务链路及稳定外网仍未确认。80现有外网代理依赖Mac。ASI需要GPU的任务仍在四卡内安排，不能与推理各默认占满四卡。
3. **数据与评分。** 数据逐源清洗与独立dev仍未完成；ASI当前固定评分配置的GPT-5.5图文调用尚未落实，已有DeepSeek接口检查不替代它。HLE judge方案也需锁定和校准。

若这些条件未成立，简化训练框架仍不能保证完成本题。压缩的是数据规模、方法网格和工程实现，不压缩正式题量、TB五次或规定预算。优先在正式执行前判明这些资源条件；不以降低模型规模自动解决CPU瓶颈。

## 8. 工程落点与交付

80主开发目录沿用 `/data/caoqinlu/projects/apex-takehome`，中间产物放 `artifacts/`。HPC持久盘缓存base/adapter与当前评测完整权重；固定git commit、依赖、数据manifest和run_id。正式所需日志/曲线/逐任务结果整理到可提交位置或带校验值的归档，不能因临时artifacts被忽略就漏交日志。最终提供各专家与合版公开HF revision、复现命令、损失曲线原始数据、统计/失败分析和一页报告。

本稿只列复用/适配/自实现边界与资源门槛；没有创建上述实验脚本、安装依赖、调用模型API、下载训练数据/权重或启动GPU任务。
