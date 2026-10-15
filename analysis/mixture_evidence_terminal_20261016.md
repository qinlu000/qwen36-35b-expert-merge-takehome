# Terminal-Bench：SFT 配比、筛选与提分证据

2026-10-16。联网读取一手论文／作者发布材料；本轮只调研，不下载训练集、不生成轨迹、不跑模型或任务。
适用前提以 [预算重设计](sft_budget_redesign_20261016.md) 为准：最终量由覆盖、合格供给及实测成本约束，旧 15M 不是默认目标。
当前模型是已有充分后训练的 Qwen3.6 MoE，评测使用非思考、64K 上下文／单次输出 8K、受限资源协议；下列旧模型或其他 harness 结果不能视作预期收益。

## 1. 核心判断

- 有可用的数据组成与消融经验，但没有研究证明我们的 Terminal＋ASI 应按某个固定比例混合，也没有“四 benchmark 最优配比”。
- 对现代 Qwen，最重要的反例是“加更多旧 SFT 轨迹可能倒退”，不能把老 Qwen3 的大幅增益直接外推。
- 终端任务需要多种操作与环境覆盖；只堆数学／代码问答、简单 bash 或仓库修复，无法替代完整终端交互。
- 论文大多报告**轨迹条数**而非 token／监督 token；不同来源长度、重复任务数与 epochs 不同，配方中的百分比不能直接当成本配比。

## 2. Nemotron-Terminal：广覆盖有效，但样本量混杂很强

主源：[On Data Engineering for Scaling LLM Terminal Capabilities](https://arxiv.org/html/2602.21193v1)，2026-02-24，表 5–9、§5。

- 同一 DeepSeek-V3.2 教师、Terminus 2 生成与 TB2.0 评测；主消融底座 Qwen3-8B，另有 14B／32B。
- 默认 SFT 配置为 2 epochs、32,768 最大长度、global batch 128、LR 2e-5；不是我们的 LoRA 一遍数据配额。
- Dataset adapters：数学 162,692 条、代码 31,960、SWE 31,661，总计 226,313；约 **71.9%／14.1%／14.0%（按轨迹）**。
- 该三类单独训练 TB2.0 分别为 5.39／6.29／7.02；三类合用 9.66。全量比单域规模大，没有同 token／同 updates 控制，因此只能支持“此组合有用”，不能证明 72:14:14 最优。
- Synthetic：seed-based 124,366 条得 6.18；skill-based 139,841 条得 12.4；合计 264,207 条仍为 12.4。
- 适配＋合成原始计数约 **46.1%／53.9%**；最终 8B 得 13.0，14B 20.2，32B 27.4。该近半分配是供给配方，不是比例搜索结论。
- 合成任务按 9 域构造，涵盖数据处理／查询／科学计算／调试／文件／安全／软件工程等；每任务组合 3–5 个技能。它支持覆盖设计，不要求复刻 9 域比例。

筛选消融（表 7，Qwen3-8B，TB2.0）：

| 合成轨迹筛选 | 条数 | 分数 |
| --- | ---: | ---: |
| 全部保留 | 264,207 | 12.4 ± 2.29 |
| 仅完成 | 104,603 | 6.74 ± 2.20 |
| 仅成功 | 83,448 | 5.06 ± 2.11 |

- **不能据此断言失败轨迹更好**：全量分别多 2.53／3.17 倍，训练 2 epochs 也改变 exposure／updates；没有同量抽样或同 token 失败占比实验。
- 可借鉴的是保留有意义的错误反馈与成功恢复，避免把“中途报错”误判成坏样本；不可因此把无验证、循环、状态缺失的失败结果全部监督。
- 混合单阶段 13.03 ± 2.16，比“先 adapters、后 synthetic”10.39 ± 1.71 更高；同组成下没有支持增加课程阶段的理由。
- 长度消融：32K 训练／40,960 评测得 13.0；64K 训练／64K 评测不加 YaRN 得 10.3；加 YaRN 得 11.9。延长窗口没有带来收益，不能当成“长轨迹一定更好”的证据。
- 32B 科学计算 2.9→0.0、数学 0→0，而数据处理 5→50、模型训练 0→50（均为论文分域百分比，小题数）。**总体终端提升不意味着 ASI 科研程序也会提升**。

## 3. TMax：现代 Qwen 的旧数据负迁移反例最相关

主源：[TMax: A simple recipe for terminal agents](https://arxiv.org/html/2606.23321v1)，2026-06-22，§3.3、§4.1、表 7、14、15。

- TMax-SFT：约 2.2K 独立环境，每环境采 8 次；教师 Qwen3.6-27B，除未解析工具调用后剩 16,496 条，其中约 8K 成功；不另过滤失败／未完成。
- large SFT 共 327,299 条：Nemotron 237,874、SERA 47,464、TerminalTraj 16,748、OpenThoughts-Agent 8,717、TMax 16,496。
- 上述是**轨迹计数**；Nemotron 约 72.7%（计算值）。没有按 token 配平，也没有固定训练曝光控制；TMax 同任务多 rollout 也不是 16K 独立任务。
- 两个 SFT 配方均训练 2 epochs，LR 2e-5；Qwen3.5 为 64K、Qwen3 为 32K。mini-SWE-agent persistent shell 是默认 harness，非我们的 Terminus-2 原生协议。

表 7（均值 ± stderr，3 次评测；TB2.1 而非 TB2.0）：

| 底座／训练 | TB-Lite | TB2.1 |
| --- | ---: | ---: |
| Qwen3.5-9B | 41.9 ± 2.7 | 16.1 ± 3.7 |
| ＋TMax SFT | 35.5 ± 4.5 | 15.0 ± 3.0 |
| ＋large SFT | 31.3 ± 3.5 | 16.9 ± 0.9 |
| Qwen3-8B | 7.3 ± 1.0 | 1.1 ± 0.9 |
| ＋TMax SFT | 11.5 ± 0.1 | 6.0 ± 1.4 |
| ＋large SFT | 16.4 ± 2.3 | 7.9 ± 3.3 |

- **准确表述**：现代 Qwen3.5 的 TB-Lite 下降；TB2.1 没有可靠增益，large 数值还略升，不能写成“两项均明显下降”。老 Qwen3 却两项增益。
- 作者推测旧弱教师数据会覆盖更强的后训练能力；这是解释，尚未通过教师强度同量实验确认。强一些的 Qwen3.6-27B 教师单独也未改善 Qwen3.5。
- 对我们的边界：不保证 Qwen3.6 MoE 会同样退化，但比“Qwen3-8B 提升五倍”更值得作为风险先验；不以老数据体量或教师名气决定比例。
- 主打约 27% TB2.0／28.8% TB2.1 的 TMax-9B 是 **RL 结果**；Qwen3.5／3.6 直接 RL，没有前置 SFT，不能归因于这个 SFT 配方。
- 默认 RL 使用中间轮保留 thinking；不能直接拿这些结果预测我们的非思考模式。
- 作者明确指出后端安装速度与推理速度会影响 per-task timeout；使用统一单 A100 节点、保持默认 timeout，并重复 3 次。我们的受限资源协议必须独立报告，不直接贴论文成绩作为可达目标。

## 4. LiteCoder：相对均衡是可用起点，逐域删减并不推出 TB2 最优权重

主源：[LiteCoder-Terminal](https://arxiv.org/html/2605.29559v1)，2026-05-28，§3.3–4.1、表 1–3、附录 E。

- 11,255 条、10 域，约 27.4 turns；轨迹组成 Terminus-2 86.6%、OpenHands 7.1%、Claude Code 6.3%，教师 MiniMax M2／M2.1。
- 域按轨迹大致均衡：build tools 12.0%，system administration／networking 各 11.6%，scientific computing 7.3%。没有比较均匀 vs 最优权重。
- 行为过滤：循环而不改策略、忽略真实反馈／未经验证宣告成功、遇错即放弃、显式拒绝。未给有无过滤的严格消融，故这是一套可审计规则，不是已证明的最优阈值。
- Qwen3-30B-A3B 的 TB2.0 从 5.34 ± 1.69 到 12.36 ± 2.75；Qwen2.5-Coder-32B 从 4.49 ± 1.72 到 18.54 ± 3.40；都是 SFT、Terminus-2、4 次均值。
- SFT 为 3 epochs、64K、LR 5e-6；不能凭“11K 条能提分”直接推出我们的最少任务数。
- 4B leave-one-domain-out 的三 benchmark 均分：full 13.66，去 games 11.16、去 security 11.51。**但 TB2 单项去 games 4.78→5.60，去 system admin 4.78→7.86**；支持多域整体能力，不支持“多加这些域就一定提高 TB2”。
- 该删域实验同时减少样本，未报告同 token 补齐；小模型和小 TB2 题数进一步限制可迁移性。
- TB2 4B 从 4.78→6.10 是额外 DMPO，不能计入 SFT 收益；pass@4 也不能与 pass@1 混为一谈。

## 5. OpenThoughts-Agent：先挑来源／教师，再谈精确比例

主源：[作者发布](https://www.open-thoughts.ai/blog/agent)、[数据卡](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-v1-SFT)，2025-12-05 发布，2026-10-16 读取。

- 15,209 条 SFT 来自 NL2Bash 合成命令任务＋InferredBugs 的 C#／Java 修复；作者未在正文公布两桶精确混合比或 token 比例。
- 来源消融尝试 15 种 instruction sourcing，每来源约 10K 任务、统一 GPT-5-Nano 解一次后训练，在独立 OpenThoughts-TB-Dev 上比较。
- 这比跨论文拼 leaderboard 更接近来源质量比较，但仍没有相同 token／监督 token 控制；泛用普通 Ubuntu 环境也限制真实任务复杂度。
- 教师消融中 GPT 家族强弱没有持续改善学生，GLM-4.6 教师的 downstream dev 表现近两倍（作者正文描述）；不能用教师 TB leaderboard 排名替代学生效果。
- 最终 GLM-4.6-AWQ＋Terminus-2、最多 32 turns、64K 采样；数据卡训练 7 epochs。最终模型的 TB2.0 4.9／SWE 15.7 是 SFT＋RL 后成绩，不能当纯 SFT 消融。

## 6. 对当前 Terminal＋ASI 桶的可执行结论与证据边界

1. 不给 70:30 等伪精确比。先分别统计 Terminal 操作覆盖与 ASI 科研程序／产物覆盖，记录独立任务 N、完整长度 L、实际窗口 P、监督量 S、训练成本；两桶均保留合格覆盖。
2. Terminal 候选优先对齐 Terminus-2 的输入、JSON／keystrokes、执行反馈、结束依据；Mini／OpenHands 轨迹不能仅改字段名当同分布。
3. 留真实错误及有效恢复，排循环、反馈不一致和缺必要状态；没有“失败样本应占几成”的同量依据，也不能用 task_complete 代替 verifier 成功。
4. 新 Qwen 上不以旧弱教师数据填满预算；先做 source／清理后监督内容审计，正式前用冻结独立 dev 聚合诊断覆盖缺口；不增加配比搜索分支。
5. ASI 需要完整程序、文件产物与科研源任务，Terminal 中的科学计算只是可能邻近，不是已验证替代；本次四项研究均无 Terminal∶ASI 混合消融或 ASI 分数证据。
6. 专家和 Mixed 使用同一窗口 multiset、出现次数与 mask；配比报告至少并列任务比／processed token 比／监督 token 比，以免长轨迹隐性支配梯度或成本。
