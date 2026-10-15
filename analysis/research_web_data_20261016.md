# 数据与训练样本：联网方法调研（2026-10-16）

范围：Qwen3.6-35B-A3B / Qwen3-8B，同基座三专家 LoRA SFT，仓库修复 / 交互执行（TB+ASI）/ 学术推理，四张 H100 与短交付窗口。已读本项目计划、数据建议及来源清单；本轮以 ego-browser 实际访问官方论文、GitHub、HF 数据卡，并用 web 检索补充核验。没有运行任务、模型、训练或 API 教师采集，没有访问正式题答案。

**建议优先复用已公开的任务环境构建方式和对应监督，先解决可恢复与可验证，再扩大样本。** 同样使用 Docker 不等于同一种环境；SWE 的仓库状态与回归、TB 的持续终端状态、ASI direct_llm 的完整程序交付、HLE 的学术回答应分别保留。以下“作者报告”均非本项目实测；具体配额与迁移建议均为本项目推断。

## 1. 五个优先方案

| 顺序 | 借鉴方案 | 对本项目的具体价值 | 当前边界 |
| --- | --- | --- | --- |
| 1 | Terminal-Task-Gen / Nemotron：技能分类→共享镜像→pytest→Terminus2 轨迹 | TB 的环境、动作与训练过程最直接；现成 skill-based 轨迹可先用，任务包可做独立 dev 或补采 | 本项目已下载不等于镜像恢复、评分与任务映射通过；不需要重建生成平台 |
| 2 | SWE-smith 环境与验证 + Open-SWE mini 现成轨迹 | 前者提供任务/容器恢复入口，后者更接近目标 mini 工具行为；复用成熟测试而非手工造几十个 issue | 两者不是同一任务池；必须分别保存任务映射与原 harness，不能把 SWE-agent 轨迹改名成 mini |
| 3 | D3-Gym：完整科学程序→执行产物→领域评价 | 若 ASI 选 direct_llm，D3 的单次完整程序监督是合理主候选，资格不依赖“是否多轮” | 上游许可和任务映射是实质缺口；静态程序对多轮终端纠错的帮助未证实 |
| 4 | SWE-Prime：选代表性轨迹，保留上下文、选择监督片段 | 在有限 token 中控制重复、无效操作与错误模仿；比“成功字段=整条都好”更细 | 完整方法增加 embedding/LLM 标注成本；局部 loss mask 不会同比减少 processed token |
| 5 | OpenScienceReasoning-2 + OpenR1：广域题型覆盖与逐回答验证 | HLE 以跨学科为主，数学提供少量可验证信号；按主题、长度与答案类型组织 | 多数投票不是真值；文本不覆盖 HLE 图像；难度标签不是目标模型真实难度 |

这里的优先级是落地价值排序，不是主源已全部合格，也不是建议增加五条训练分支。建议三专家与混训使用同一组事先冻结的 manifest；不因新论文增加在线 RL。

## 2. 关键一手来源与适配

### A. Nemotron-Terminal：最值得复用的是环境契约和数据消融

来源：[论文 v1](https://arxiv.org/html/2602.21193v1)、[固定 Corpus 数据卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/blob/a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9/README.md)、[固定任务环境卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/blob/7e53648e183cee7bcb0aed623cc91a121d37fa38/README.md)。

- **已核方法：**技能组合生成任务，领域共享 Docker，tmux 持续会话，pytest 检查文件、格式和数值；使用 Terminus2 收集轨迹。公开任务包和轨迹包分开，卡片许可 CC BY 4.0。
- **作者报告：**Qwen3-8B 的 synthetic no-filter 为 264,207 条、TB 12.4±2.29；complete-only 为 104,603 条、6.74±2.20；success-only 为 83,448 条、5.06±2.11。skill-based 单源优于 seed-based，简单混合不要求复杂课程。
- **解释限制：**三种过滤的样本数相差很大，不是等任务数、等 token 的“失败样本价值”因果实验；不能据此认定本项目必须无筛选。作者先做质量与污染处理，no-filter 不意味着接受损坏消息或泄漏。
- **本项目适配：**保留 skill-based 与原工具语义，终端/科研分别记配额；完整成功轨迹内部的失败→检查→恢复应保留。不按一次非零退出就删整条，也不把最终失败程序直接当正确科研答案。
- **污染限制：**作者执行 TB2 题面 14-gram 排重，只覆盖该检测定义；本项目仍需任务/模板家族、跨源衍生关系与四项正式来源的排除。不能把上游已去重写成我们已完成去污染。

### B. SWE-smith：现成任务环境比从空仓库造题更适合当前窗口

来源：[固定官方 README](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/README.md)、[论文](https://arxiv.org/abs/2504.21798)、[现成轨迹卡](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/blob/08e109b4a59eaeebf80e4675cd125d42e7ac99a4/README.md)。本轮重新核验 README 的环境与构造入口；轨迹卡沿用项目已有固定来源。

- **已核方法：**建立 repo 环境，注入变更，仅保留打破至少一个单元测试的任务，再生成 issue 描述；公开 `registry.get_from_inst(task)` 与 `rp.get_container(task)` 环境恢复入口，工具代码 MIT。
- **本项目适配：**从已下载 Python/Go 任务中挑少量独立仓库家族作为 dev / 缺口补采，用目标 mini harness 解题；记录“原始通过→注入后失败→修复后通过”的验证路径。
- **限制：**官方说明依赖 Docker，主要在 Ubuntu 测试；本机 macOS 不应成为恢复全部环境的主路径。合成 bug 及已有测试不能完全代表真实 issue 或隐藏回归；任务包仍需教师过程才能成为 agent SFT。
- **划分：**同一 repo、相同原变更/变异家族及跨格式同题必须归组再切 split。公开工具 MIT 不能替代原代码库许可或保证 SWE Pro 来源独立。

### C. Open-SWE-Traces：同 mini 谱系可用，但成功与来源版本要分开

来源：[固定 v1.1/mini 数据卡](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)、[论文 v1，尤其表5与§4](https://arxiv.org/html/2606.16038v1)。

- **已核数据：**固定卡包含 `instance_id/repo/license/language/messages/tools/resolved/metadata`，mini/Qwen3.6 分区来自 Scale-SWE 与 SWE-rebench-V2；`resolved=-1` 是未知，不能当失败或成功。CC BY 4.0，同时列上游 MIT/Apache/BSD。
- **作者报告：**论文表5的 full（含 unresolved）优于 resolved-only，SWE-M no-think 为 49.6→57.1；跨 OpenHands/SWE-agent harness 转移存在下降。这里研究的是论文早期教师/框架，不能直接归因到已下载的 v1.1 mini/Qwen3.6。
- **本项目适配：**优先原 mini 消息、工具定义与原始任务映射；先来源/结构/泄漏筛选，再在各语言与长度桶中选择完整轨迹。success-only 可作为短窗口的审计简化，但不能写成已证实最优。
- **新核版本风险：**固定 README 说明 v1.0 曾在 08/26 删除 git-hacking 轨迹，由约207K变约151K。应固定已下载 revision，并在 manifest 记录行为审计；旧论文总数不能代替当前分片实际统计。git history 泄漏、改测试凑通过与空补丁都需要区别于正常检查。
- **限制：**上游 `resolved` 不是 fresh replay 证明；数据卡称可用不等于针对本题全部 repo/PR/fork 做过排除。无须全量重跑教师，但可追溯的代表性重放仍有价值。

### D. D3-Gym：与完整程序式 ASI 相近，许可与评分质量比“多轮”更关键

来源：[固定官方 README](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)、[论文 v1](https://arxiv.org/html/2604.27977v1)、[公开轨迹卡](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories)、[固定转换脚本](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/training/convert_trajectories_to_alpaca.py)。

- **已核方法：**每个任务带数据/预览、依赖镜像、参考产物和自动评价器；`solution.py` 写入 `pred_results/` 后评分。转换脚本输出 instruction/input/output，output 是可选 think + 完整程序，证明这不是 Terminus2 式多轮工具轨迹。
- **本项目适配：**若采用 ASI direct_llm，按完整程序、输入路径、输出工件与数值要求对齐；这个适配是接口相近的判断，不是 ASI 提升证据。TB 的 shell 监督与 D3 的程序监督可在交互执行专家内分桶。
- **作者报告：**Qwen3-8B 在 ScienceAgentBench 平均 SR 为 Base 6.5、RFT-Self 10.1、Distill 8.5；摘要所称32B +7.8 对应 best-of-three，平均 SR 提升为 +4.2。不能将前者写成 pass@1 增益，更不能当作 ASI 增益。
- **评价器限制：**银标 evaluator 与人工金标总体一致率87.5%，recall66.1%、specificity91.0%；“脚本通过”并非科学正确性的充分证明。可借其先计划评价指标/容差、再编码评价器的方法，避免仅检查程序退出码。
- **重要许可缺口：**239个源 repo 中 MIT99、BSD29、Apache22、ISC1；另有 GNU43、无许可39、Custom2及CC4。作者对无许可内容仅作研究使用假定，不能当授权依据。公开代码/轨迹卡 MIT 不覆盖全部上游；优先可映射的明确许可子池，GNU/CC按具体条款处理，无许可/Custom暂不纳入公开可复用池。
- **实际恢复缺口：**README 的镜像内同时列出 `eval_script.py/gold_results`。收集训练解题时，solver 只应看到任务数据；独立评分侧保留参考材料。此为本项目隔离建议，未实际改镜像或证明恢复成功。
- **配方陷阱：**公开 [qwen3_8b.yaml](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/training/configs/qwen3_8b.yaml) 仍指向 AutoSDT 数据、`finetuning_type: full`；不能当作现成 D3 LoRA 可运行 recipe。转换后若丢失 task/repo ID，要先补回可靠映射再分组。

### E. SWE-Prime：新发现，适合借原则，不适合直接扩成新平台

来源：[论文 v1，§SWE-Prime、表1](https://arxiv.org/html/2608.27449v1)，2026-08-27。此次没有找到作者官方可复用代码；搜索到的同名 `SWE-bench/SWE-prime` 不据名称认定为该论文资源。

- **已核方法：**先按过程、补丁范围与代表性选轨迹，再按语义段价值构造 mask；完整轨迹保留作上下文，只监督选择段中的 assistant token。作者使用 Qwen3-Embedding-8B、HDBSCAN 和 LLM 段评分，部分评分依赖独立训练任务的参考 patch。
- **作者报告：**10%精选轨迹胜过全部成功轨迹，也给出随机10%对照；Qwen3-30B-A3B 的 SWE Pro 为16.83→18.88，Verified36.8→39.6。相对提升、特定模型与其协议不应变成我们预期的绝对提升。
- **本项目适配：**先借轻量规则：相同任务限制重复 rollout，保留观察→修改→验证与有效恢复，避免连续重复命令占满监督。必要时对无效段设mask，保留后续行为所需上下文，不删除状态依赖后拼接不真实轨迹。
- **成本限制：**mask改善的是监督内容，输入仍参与前向/必要反向，processed token不自动减少。当前预算若主要卡在序列长度，先选择能容纳的完整轨迹并保留难度覆盖；不在本轮新增大规模 LLM 打分或训练 PRM。

### F. OpenScience / OpenR1：用学科覆盖与回答验证，避免把长链或“brutal”标签当质量

来源：[固定 OpenScience 卡](https://huggingface.co/datasets/nvidia/OpenScienceReasoning-2/blob/174b02c9cdf231f220765b2a1d5ece4550921894/README.md)、[官方生成流程](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/docs/releases/openreasoning/dataset.md)、[固定生成 prompt](https://github.com/NVIDIA-NeMo/Skills/blob/bcf059af55c20a89f797724598f9908d126153e6/recipes/openreasoning/prompts/science_question_generation_prompt.yaml)、[固定 OpenR1 卡](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k/blob/e4e141ec9dea9f8326f4d347be56105859b2bd68/README.md)。

- **已核方法：**OpenScience 按 topic/subtopic/difficulty 合成并增广问题，再由 R1-0528 生成回答、做多数投票；卡片包含STEM、法律、经济、人文学科，文本，CC BY 4.0。难度 prompt 的 intermediate→borderline-unsolvable 是生成要求，不是学习者测得的难度。
- **本项目适配：**HLE 保持广域主池，数学为辅；同原问题及所有改写、同题多回答统一归组；按学科、题型、实际 token分层。多数票保留为标签来源，不改写成“已验证真值”。few-shot 内容与增广原题也属于污染检查范围。
- **OpenR1补充：**卡片提供逐 generation 的符号/LLM正确性、完整性、finish reason及uuid；每题至少有一个正确候选，不代表全部候选正确。优先明确验证且完整的回答，避免随手取 `generations[0]`。default优于extended是作者特定设置，不是普遍越难越好。
- **长度限制：**OpenR1作者使用16K生成，称仅75%的问题能在8K内解决。若我们取8K，先统计“完整答案是否装得下”，不能截去答案后仍标正确；分段会改变监督和processed token账本。纯文本数据对HLE图像能力不构成覆盖证据。

## 3. 两个可借鉴但不进入本轮主线的新方法

- [SciDisco / SciThèque](https://arxiv.org/html/2607.28990v1)：从数据集+分析模板建立隐藏证据DAG，执行验证后才接受中间步骤，训练转换时移除调度器、隐藏节点、参考值和容差。可借“生成侧知道验收标准，solver侧只看到合法观察”的分离方式；此次未找到已核验的官方发布/许可/可直接运行代码，不列为可用训练主池，也不引入其RL。
- [SWE-TRACE](https://arxiv.org/html/2604.14820v1)：先利用测试到函数的映射约束bug注入，再用生成侧oracle筛动作、压缩冗余。可借“在已测覆盖区域造bug”，减少不可验证任务；完整多候选oracle采样额外消耗很大，且涉及隐藏构造信息，不适合本轮从头建设。

## 4. 既有计划最应补的缺口

1. **把“同构建方式”和“环境已恢复”分别验收。** 最小证明是固定训练任务在目标协议能读输入、产生产物、评分并重新开始；仅下载任务元数据/轨迹或同属Docker不够。D3的单次程序有资格对齐ASI direct_llm，不需先强造多轮。
2. **构建任务—轨迹—环境关联。** 最少保留 source/revision、原task/repo/template家族、image digest/入口、harness、verification状态、split、processed/supervised token。没恢复环境的现成轨迹可保留“上游验证”，不能标“本项目执行成功”。
3. **别把成功筛选变成唯一质量标准。** 上述正反证据均受数据量、模型和环境影响。当前不扩候选数；先用简单可审计规则，对无信息循环、泄漏、协议损坏严格处理，对真实错误与有效恢复保留上下文。
4. **配比是约束，不是论文结论。** 原0.9M/1.2M/0.9M及终端/科研子配额仍是预算候选；先按通过资格的实际token统计，防止长工具观察、数学或某repo吃掉预算。混训复用同样本/次数/mask，不能因mask变少就当算力对照一致。
5. **独立dev先按家族划分，再抽样/分段/增广。** 同源跨教师、跨harness、同task多程序都必须共同分组。正式题/答案/测试及派生任务不进入train；新来源的官方去污染声明不能替代本项目检查。
6. **D3许可、HLE图文、8K长度偏差应列为显式边界。** 这三个缺口比继续下载第六个大数据集更优先。当前文件只形成讨论与执行验收依据，不把建议写成已冻结或已开跑。
