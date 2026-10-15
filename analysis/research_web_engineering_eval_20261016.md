# 联网调研：工程与评测可借鉴的方法

2026-10-16，北京时间。面向三专家 LoRA＋固定合版、4 H100，以及 SWE Pro V2 HARD-51、TB2 89×5、HLE2500、ASI open60×4。仅调研和文档，没有运行模型/任务/API探针、改变配置或提交 Git。

已读项目计划、评测协议、harness 复用、Base readiness，以及 `claud.md` 最新状态。最新记录显示权重已完整落盘、Apptainer/root-map 已有一例 TB 合成闭环；较早 readiness 的“权重未下载、无容器后端”不能作为当前状态。本文新增信息集中于恢复语义、服务正确性、调度公平、Judge 与统计，SWE mini/Terminus2 公开代码复用结论沿用现有报告。

## 先给结论

本次最值得借鉴的是**保留原生 agent/评分器，补一层很薄的运行与证据管理**。当前没有必要换整套训练/评测平台。更应优先排除“运行成功但评测实际不对”的问题：恢复丢日志、MoE adapter 布局误声明、工具约束解码改变原 agent 行为、队列等待挤占时间预算、替代 Judge 未校准。

| 新核实的信息 | 对本项目的直接意义 | 不能据此推定 |
|---|---|---|
| 固定 Harbor `resume` 会删除指定错误 trial；缺 `result.json` 的目录也会被删除 | 恢复前保存原 attempt 与费用证据 | `resume` 自动保留所有失败历史 |
| vLLM 稳定文档已有本次 Qwen3.6 的 2D/3D MoE LoRA 示例 | 可以优先核实原生服务，避免自写 adapter 路由 | 本机已装版本、PEFT 导出布局一定兼容 |
| vLLM 在线生成仅给 seed 不保证复现 | 固定版本、硬件、调度，并明确随机性边界 | 设 seed=0 后每次逐 token 相同 |
| root-map 是 fakeroot 的较弱模式；资源限制还依赖 cgroup delegation | UID/权限与每 trial 限额要分别验收 | 合成 shell 成功即等价 Docker 全部语义 |
| 原生重判可只消费已保存产物 | 外部 Judge 错误无需重新生成答案 | 任意旧 trial 都有足够文件可重判 |

## 1. 恢复评测：复用原生队列，但先保存被替换的 attempt

固定 [Harbor CLI 源码](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/cli/jobs.py#L2203) 中，`harbor job resume -p ...` 默认过滤 `CancelledError`，匹配后调用 `shutil.rmtree(trial_dir)`。固定 [Job 恢复源码](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/job.py#L237) 还会删除没有 `result.json` 的 trial 目录，再按配置匹配已有结果、补齐剩余项；配置不一致会拒绝恢复。

可直接借鉴：同一冻结 job 按原配置恢复，原生结果作为真值来源；**每次恢复前先将原目录归档到不被 runner 扫描的位置，并保存 attempt 索引**。索引至少包含 task/seed/model/protocol hash、退出原因、是否已调用模型、usage、旧目录和新目录。这样可继续使用现成 CLI，同时满足本项目“失败及费用全留档”的要求。

必须分清三件事：

- job resume：补完缺少或被过滤的 trial。
- native session resume：从 agent 的中断会话继续；[Harbor 当前能力表](https://docs.harborframework.com/agents/pre-integrated-agents) 没有为 Terminus2 列出此能力，不能把 job resume 写成终端任务原地续跑。
- regrade：对原回答/工件重新评分；[官方文档](https://docs.harborframework.com/jobs/regrade) 要求保存足够 artifacts，更新后的任务采用 separate verifier，不重新启动 policy agent。

建议按 `pending / running / answered / graded / infra_failed / judge_failed` 记录状态；这只是小 manifest，不需要新增数据库或工作流平台。Judge 失败只补评分。模型耗尽预算、错误动作、缺工件按原 grader 处理，不能列入“基础设施重跑”。

[官方错误策略](https://docs.harborframework.com/jobs/error-classification) 把 agent 超时/context/output 耗尽与 sandbox/provider/verifier 故障分开，前者仍是有效评价。可以借鉴这个分类思想，但当前网页策略与项目固定代码仍应核对；不能直接把网页的 `reward_valid` 自动排除行为用作本项目主分母规则。完整分母与缺项披露按本项目协议执行，未决规则须在正式运行前冻结。

## 2. vLLM：最有价值的新信息是 MoE LoRA 布局和工具语义

[vLLM LoRA 稳定文档](https://docs.vllm.ai/en/stable/features/lora/) 已直接展示 `Qwen/Qwen3.6-35B-A3B` 的 2D Megatron 与 3D PEFT adapter 混合服务。文档同时说明：启用 mixed layout 后，`is_3d_lora_weight` 由调用者声明，框架不检查实际布局；误声明可能正常加载却产生错误输出。PEFT 风格示例是按 experts 维度堆叠的 tensor，不可只看到文件后缀就决定布局。

对本项目的最小借鉴：记录实际导出 key、shape、target module、rank、alpha、base revision，再确认当前 serving 版本的支持。若训练只覆盖 attention、没有 MoE expert 参数，此混合格式开关可能根本不需要；不要为“支持本模型”盲开新功能。LoRA 多模态 tower/connector 支持仍有实验性质，语言模块 LoRA 与视觉模块 LoRA 需区分。

静态注册 Base/各 adapter 的服务名比运行中覆盖同名 adapter 更容易审计。每个 task 绑定不可变 artifact hash；一个长 agent 的中途不得因热更新切到新权重。原生 multi-LoRA 可减少重复加载，但其存在不证明本题 4 卡显存、长上下文与并发达标，也不保证最终合版仍是可热载的同 rank adapter。

[vLLM 工具文档](https://docs.vllm.ai/en/stable/features/tool_calling/) 区分 auto、named、required：named/required 会使用结构化输出约束，auto 则依赖模型格式与 parser。保证合法 JSON 不等于工具选择正确。**不能为了让 smoke 通过，给原本普通文本输出的 Terminus2 JSON agent 加 `tool_choice=required`，或给原生 bash loop 强加函数调用。** 这会改变被测 scaffold，也改变训练—评测一致性。

应按最终 harness 分别核对：原始 response、parser 接受结果、实际执行动作、观察回写、结束信号及截断。SWE mini 的 bash、Terminus2 的命令 JSON、ASI direct_llm 的完整程序分别保留原生契约；只有采用原生函数工具的 agent 才需要配置该模型真正匹配的 vLLM parser。不要凭 Qwen 家族名称猜 `hermes/qwen3_xml` 一定适合本次模板。

[vLLM 复现文档](https://docs.vllm.ai/en/stable/usage/reproducibility/) 说明默认不保证结果复现，在线服务需启用 batch invariance 才能消除批次/调度影响，并仍限定同硬件、同版本。[对应功能文档](https://docs.vllm.ai/en/stable/features/batch_invariance/) 标为 beta，会牺牲部分性能；已验证列表未列本次 Qwen3.6。可以将其作为独立验收候选，不能直接开启后宣布严格复现；若不采用，则明确 seed 固定不等于逐 token 确定，靠统一服务政策与 TB 重复运行报告实际波动。

## 3. 并发优化：同时看 CPU 与模型队列，保持同项公平

[vLLM 原生指标](https://docs.vllm.ai/en/stable/usage/metrics/) 已提供 waiting/running、queue time、prefill/decode、TTFT、KV 使用、preemption、LoRA 请求统计；无需先搭完整监控栈。定期保存 endpoint 指标与每 trial 墙钟/CPU/RSS 的小表，即可判断瓶颈。

适合本项目的决策规则如下，属于基于官方能力的工程建议，而非实测结论：

- CPU 利用率低、模型 waiting/queue time 上升：继续加 sandbox 通常只会增加等待，应限制同时进入 agent 阶段的 trial。
- CPU/IO 拥塞、模型空闲：减少环境 build/解包/验证并发，预构建固定镜像；不要削减单任务题定 CPU/时间。
- KV/preemption 上升：先降低请求并发，区分长输入与长输出；不能仅凭权重 71.9GB 判断服务容量。
- 生成完成的 replay/verifier/Judge 可独立排队，减少 GPU 等评分；但 verifier 也需自己的 CPU 槽位。

同项各模型使用同一 admission/并发政策，因为模型排队会消费 agent 的墙钟预算。若 Base 使用空闲独占服务、合版承受大量 HLE 请求，名义相同的 3h 也可能产生不同可用行动次数。调度调整只看吞吐/资源/基础设施错误，不看哪批任务分数较低。

GPU 训练与服务目前优先按冻结模型分块，切换前停止接新 trial、等在途任务结束、落盘后再切换；这里不引入在线 RL 的权重同步或分布式调度平台。是否可同时 2 卡服务＋2 卡训练仍须另行验收，文档不构成可行证明。

## 4. Apptainer：root-map、权限、网络与资源是四个不同验收项

[Apptainer fakeroot 文档](https://apptainer.org/docs/user/latest/fakeroot.html) 将完整 subuid/subgid rootless、只映射 root UID 的 user namespace、以及额外 `fakeroot` 命令分开。root-map 模式模拟不完整；文件 ownership、降权用户和包管理行为不能从一次 root shell 成功外推。宿主 HOME 默认挂载也应显式控制，避免环境依赖用户已有缓存/配置。

[资源限制文档](https://apptainer.org/docs/user/latest/cgroups.html) 明确：非 root 的每容器 cgroup 限额要求 cgroups v2 与适当 systemd delegation；scheduler 父 cgroup 可限制整个 job，但不自动等于 job 内每个 trial 各自具备 32CPU/48GiB 限制。root-map 成功不能证明资源与网络隔离成功。

因此当前真实镜像闭环的后续最小验收应分别记录 UID/可写目录、独立 HOME/挂载、实际 cgroup 限额、网络阶段策略。SWE 解题断网只放行模型、fresh replay 与 ASI 评分侧隐藏材料隔离仍需单独落实。不能因 Docker→SIF 改变格式便要求全部重采 teacher；关键是模型可见环境语义是否保持。

固定 [Harbor factory](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/environments/factory.py#L99) 已注册 `SingularityEnvironment`；可优先沿用已有 backend 接点，而非重写 mini/Terminus2。registry 存在不证明该 backend 对本次网络、Compose、权限和 resource guarantee 的完整支持。

## 5. 替代 Judge：校准评分质量，保留原回答后异步重判

[MT-Bench Judge 论文](https://arxiv.org/abs/2306.05685) 讨论位置、冗长、自偏好与推理能力限制。其人类偏好实验结论不能外推为 DeepSeek 对 HLE 严格答案或 ASI 科学图的等价性，也不能把图像输入接口成功当作评分正确。

建议在独立材料上先做一个小而有针对性的校准包，覆盖：

- HLE 式答案：同义表达、等价数学形式、单位/有效数字、正确过程但错最终答案、拒答/无答案、格式不合但实质正确。
- ASI 工件：正确图、轴/单位/legend 错、曲线形似但数值错、缺面板、空图/损坏图、科学结论相反但措辞流畅。
- 稳定性：相同原回答重复评分，必要时交换 predicted/reference 附件顺序并同步 prompt 标签，检查输出解析和 rubric 是否稳定。

这里建议先用约 40–60 个独立文本/图像案例作工程质量门槛，**不是文献保证的充分样本量，也不证明与原 Judge 可互换**。以人工核定标签为准，报 JSON/schema 成功率、二元混淆矩阵（尤其误判正确）、ASI 分数误差及不一致实例；若可用原 Judge，则对同一批工件盲比并披露差异，不能只报两模型总体相关系数。

可完全离线于 policy 保留问题、原回答/图像、rubric hash、Judge版本、raw JSON、解析结果与usage。无论换 Judge 还是解析修复，都只重判相同工件。正式分数若采用替代 Judge，统一所有模型并明确 `local + replacement judge`；校准与原生官方认证是两件事。

## 6. 统计：沿用任务簇配对，再补清方法与失败分母

[rliable 官方库](https://github.com/google-research/rliable) 的可借鉴点是报告区间、任务/运行变异与性能分布；无需将其 RL 的 IQM 替换成题定四项主指标。[SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) 默认 `paired=False`、`method=BCa`，而本项目要求模型配对；仅写“bootstrap10000”仍不足以复现。

现有任务簇设计合理：SWE51/HLE2500 按 ID 配对，TB89 保留各题五 seed，ASI60 保留四 B 条件。实现时直接对各簇的模型差值使用相同抽样索引；不要把 TB445 或 ASI240 行视为独立题，也不要把9708运行直接池化平均。跨四项先各自算百分制提升再等权聚合。

还应冻结 percentile/basic/BCa 的选择与随机数实现，保留重采样 seed；SWE51 很小且二元，必要时同时给“修好/退化/共同成功/共同失败”配对计数，区间跨0如实描述。TB 五轮 SD 是运行波动，任务簇区间是另一层不确定性。任务 bootstrap 不覆盖训练种子、Judge系统偏差、污染或更换 scaffold 的影响。

主表必须同时有 expected/completed/valid/error 数。任务预算耗尽是模型有效失败；基础设施/评分缺失不能静默丢弃后冒称完整。若附固定分母缺失按0的保守分，应与完整有效官方式主结果分列。资源受限 proxy 或独立 dev 仅支持其范围内结论，不得用于声称题定完整提升。

## 当前最优先的五项动作建议

| 顺序 | 具体动作 | 完成标志 |
|---|---|---|
| P0-1 | 给原生恢复加一次归档＋attempt索引，不重写队列 | Cancelled/缺result情况下旧日志与usage仍可追溯；恢复不选最好答案 |
| P0-2 | 固定一次真实模型请求与adapter导出契约 | serving版本、keys/shapes、模板、parser、采样、thinking、结束语义均有证据；不把可加载当正确 |
| P0-3 | 用独立短任务验收CPU槽位＋endpoint等待，并分别核root-map限额/网络 | 得到持续吞吐、queue time、CPU/RSS与实际限额；同项全模型同政策 |
| P1-4 | 冻结ASI direct_llm或OpenCode，再用匹配训练形态；同时校准替代Judge | 单程序/多轮和视觉能力取舍明确，Judge有独立错误矩阵；不依据正式分数换路线 |
| P1-5 | 汇总表先按冻结manifest建完整空表，结果逐项填充 | 9708个预期运行均有唯一位置；任务簇配对、CI方法、缺失/重试规则可复算 |

以上是可执行借鉴而非执行授权或新实验结果。`stable/latest` 文档属于调研时网页，实际使用仍应锁版本；Harbor 源码链接已固定到项目 commit。本轮 ego-browser 完成网页取证；raw 源码 fetch 失败后以 web 工具核固定一手源码，没有访问正式答案或隐藏测试。
