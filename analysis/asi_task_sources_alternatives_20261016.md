# ASI 专项任务替代来源：四个独立来源的有界核查

日期：2026-10-16。结论用于剩余时间内的数据决策，不改变冻结的 ASI 正式评测范围、协议或必交要求。

**建议本轮不再补一套专门的 ASI 训练数据。** 本次四个来源中，DS-1000 已能确认逐题完整参考代码和测试，但主要是短代码片段；DA-Code 的文件工作流最接近，现有 gold 却不能直接证明有逐题完整人工解法；DataSciBench 的 GT 为半自动生成并人工复核；DiscoveryWorld 则使用虚拟世界动作协议。没有一个来源已同时证明「足够独立任务族、完整可信 Python 标签、直接生成文件、4 CPU／8 GB 可执行」全部成立。DS-1000 可以作为未来的通用 Python 辅助源，不能用它替代 ASI 科研执行能力的证据。

本支只访问作者仓库、论文、项目页与 HF 元数据；未调用付费 API，未安装环境，未执行数据程序，未下载外部任务输入大包或模型轨迹。唯一读取的压缩题库为 DS-1000 的 418,089 字节 JSONL，仅读取文本/元数据；没有执行其中程序。未读取正式 ASI gold、参考图、评分结果或隐藏测试。ASI 侧只参考本项目已冻结的公开任务 ID、范围及协议元数据，**没有完成逐题输入去重，不能称为已通过 ASI 去污染**。

## 1. 总览与固定版本

| 来源 | 本次固定的一手版本 | 实际数量与独立性 | 可直接监督训练的内容 | 本轮建议 |
|---|---|---|---|---|
| DS-1000 | `xlang-ai/DS-1000@b39aab71da6d23ef8d3cac59a7c5f834516ab334` | 实读 1,000 行；论文称源自 451 个 StackOverflow 原题；原题/改写不能按 1,000 个独立族划分 | 每行均有非空 `prompt`、`reference_code`、`code_context` | 留作通用短 Python 辅助源；本轮不新增 ASI 专项训练 |
| DataSciBench | `THUDM/DataSciBench@84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`；HF `zd21/DataSciBench@f15d3e4043498febc26d7bcb7562b7e344b514f2` | Git `data/` 实数 222 目录：167 BCB、20 CSV/Excel、10 DL、25 human；519 是 GT/测试数量，不是独立主任务 | 任务提示、TFC 检查与 GT 产物；本次未证明每题均发布完整人工 Python 标签 | 放弃本轮；不把论文里的 519 GT 或示例 `is_success` 当高质量训练标签 |
| DA-Code | `yiyihum/da-code@b211daf51fdc9b52d5087c9df28ac50191bcabed` | 实读任务与评测配置各 500 行、500 个唯一 ID；共享输入数据产生的家族关系尚未核清 | 任务输入、gold 产物和比较器；本次未找到足以确认逐题完整人工参考程序的证据 | 文件工作流最接近，但现在需补解题与验证，故本轮不新建专项数据 |
| DiscoveryWorld | `allenai/discoveryworld@fd591323920be0d3786ef350955de1945aa571e5` | 8 个科学主题；配置名义上每主题 3 难度×5 seed，约 120 个变体，不能称 120 个独立族 | 人类游戏动作日志、程序化环境与 scorecard，不是科研 Python 程序 | 放弃作为本轮 ASI SFT 源 |

四个 Git HEAD 均由只读 `git ls-remote ... HEAD` 解析；数量来自固定源码/数据的静态读取。DataSciBench HF revision 来自公开数据集 API。代码与数据许可仍分别遵循各自来源及上游材料。

## 2. DS-1000：标签最完整，但任务尺度明显较短

作者项目页明确描述 1,000 题来自 451 个 StackOverflow 问题，带人工构建的参考解、执行测试及 API/表面约束。固定简化版实读每一行的三个核心字段均非空；`code_context` 定义 `test_execution`、必要时 `test_string`，不是仅给一个期望数值。[作者项目页](https://ds1000-code-gen.github.io/)、[固定 README 的字段说明](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/README.md)、[实际题库](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/data/ds1000.jsonl.gz)。

实际题例：Pandas `problem_id=0` 给出 DataFrame 和指定行顺序，要求按列表重排行；目标是补一段代码并得到 `result`。这类标签能直接构成「问题→参考代码」SFT；通常没有 ASI 那种完整的科学建模、输入目录管理和多个文件产物。Matplotlib 题有绘图，但作者已把原始问题中的图示改写成独立文字要求，不能把“有图产物”直接理解为模型必须读图。[项目页的例题说明](https://ds1000-code-gen.github.io/)。

实际库分布为 Pandas 291、NumPy 220、Matplotlib 155、SciPy 106、sklearn 115、PyTorch 68、TensorFlow 45。固定环境显式使用 `cpuonly`、`tensorflow-cpu`，所以整套没有必需 GPU 的安装声明；若排除 PyTorch/TensorFlow 则剩 **887 行**。但这不是对 4 CPU／8 GB／1200s 的逐题运行证明，完整安装仍包含多套科学计算依赖。[固定 environment.yml](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/environment.yml)。

家族划分不能简单随机行切分：固定数据的 `(library, perturbation_origin_id)` 有 **453** 个不同键，Origin 行 452；与论文“451 个 StackOverflow 原题”存在计数口径差异，本次未追溯原始题链接来消解。排除 PyTorch/TensorFlow 后有 414 个这种代理键。它们只是可审阅的分组线索，不能认证为真实独立题族。数据为 CC-BY-SA-4.0，未来若用需保留来源与许可；**没有引入发布时的 Codex 等旧模型生成答案**。

与 ASI 同源风险：来源为公开 StackOverflow，存在常用算法/库操作与科学任务输入重合的可能；没有发现作者声明从 ASI 构造，但发布年份或主题不同不能证明无重合。若未来采用，需先按 ASI 公开输入做题面/家族排查；不得对照 ASI gold 选样。本轮建议只保留来源，不增加训练工作。

## 3. DataSciBench：文件契约较近，GT 不等于人工完整程序

固定仓库 `data/` 实数 222 个目录，与论文 222 prompts 一致；其中 **167 个目录直接标为 `bcb*`**，说明与 BigCodeBench 上游有明确依赖，不能把两者一起计为独立供给。论文的 519 GT 是不同检查/输出目标，不是 519 个独立任务。[固定任务目录](https://github.com/THUDM/DataSciBench/tree/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33/data)、[论文 §3.2–3.3](https://arxiv.org/html/2502.13897v1#S3.SS2)。

实际题例 `human_0`：从 `data.csv` 读取多个股票日收盘价，计算日百分比变化最相关的 ticker 对，写 `most_corr_output.csv`。`bcb1011` 则读取 CSV，按一个字段分组计算另一字段均值，输出柱图与均值表对象；它仍是函数式接口，不保证写文件。抽核两者目录都仅有 `prompt.json`，未把题面中的 starter code 当作参考解。[human_0 公开输入](https://github.com/THUDM/DataSciBench/blob/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33/data/human_0/prompt.json)、[bcb1011 公开输入](https://github.com/THUDM/DataSciBench/blob/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33/data/bcb1011/prompt.json)。

GT 构造并非纯人工写完整程序：作者先采样 LLM 生成并执行代码；BCB 部分用上游测试和人工复核，其余用 self-consistency 加六名作者验证；TFC 评估代码亦有 GPT-4o-mini 参与。它能提供经过检查的目标，但本次没有证据证明可直接取出 222 份完整人工参考 Python。[论文 §3.3](https://arxiv.org/html/2502.13897v1#S3.SS3)。README 的日志示例甚至含 `File not found` 却记录 `is_success=true`，因此该字段不能直接作正确性标签。[固定 README 示例](https://github.com/THUDM/DataSciBench/blob/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33/README.md)。

资源与获取：HF 当前 auto gated、CC-BY-4.0；公开索引列出 GT ZIP **86,227,707 字节**，本次未接受新增访问条款或下载。固定依赖含 TensorFlow、wandb、MetaGPT，10 个 `dl*` 任务不能直接默认 CPU 轻量；论文亦使用 VLM 判断部分图像产物。筛出 CPU 文件任务后仍需核输入数据、完整实现、检查器与执行上限。[官方数据仓库](https://huggingface.co/datasets/zd21/DataSciBench)、[固定 requirements](https://github.com/THUDM/DataSciBench/blob/84ef3d4d94d7362a5149cf14a73dc168fc4f2f33/requirements.txt)。

与 ASI 同源风险：已知来源混合 BCB、CodeGeeX 用户提示、人工与 LLM 合成；没有逐题 provenance 可以证明与 ASI 科学任务独立。即便未来复用 BCB167，也要按上游任务 ID 去重，不复用旧 Data Interpreter 模型日志。本轮放弃补充。

## 4. DA-Code：最像读输入、写产物，但还不是可直接训练的解法库

固定 `configs/task/all.jsonl` 与 `configs/eval/eval_all.jsonl` 各实读 500 行、500 唯一 ID；任务类型实数为 Data Insight 79、Data Manipulation 73、Data Wrangling 100、ML Classification 46、ML Clustering 21、ML Regression 33、Statistical Analysis 70、Data Visualization 78。500 个 instruction 字符串互异，**不证明 500 个输入数据/问题家族独立**。[任务配置](https://github.com/yiyihum/da-code/blob/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/configs/task/all.jsonl)、[评测配置](https://github.com/yiyihum/da-code/blob/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/configs/eval/eval_all.jsonl)。

实际题例 `data-sa-001`：给出男子/女子国际足球赛结果，检验两组平均进球数是否相同，在 10% 显著性水平下给出 p 值与拒绝/不拒绝结论，写两列 `result.csv`。公开 source 目录列出 `men_results.csv`、`women_results.csv`、README 与示例结果；抽核 gold 目录仅有结果 `result.csv`，**没有对应的完整 Python 解法文件**。[该任务输入目录](https://github.com/yiyihum/da-code/tree/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/source/data-sa-001)、[该任务 gold 文件目录](https://github.com/yiyihum/da-code/tree/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/gold/data-sa-001)。这里只核文件名与布局，没有读取 gold CSV 数值。

作者有人工设计的产物评测套件；框架根据配置调用文件/数值比较函数。它的原生 evaluator 还读取 DA-Agent 的 `dabench/result.json` 轨迹元数据，不能认为拿来就能无修改评 ASI `direct_llm` 产物。[作者项目说明](https://da-code-bench.github.io/)、[固定 evaluator](https://github.com/yiyihum/da-code/blob/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_agent/evaluators/evaluation.py)。

获取和成本仍有实际工作：README 称仓库含 100 examples、其余走外部 Drive；固定提交下实际 source 根目录为 **62 个任务目录**、gold 为 **59 个任务目录**，不可把文档数量当作当前全量文件已就绪。README 也存在旧配置路径示例，实际路径以固定源码为准。官方依赖 Docker；没有本次 4 CPU／8 GB 的运行记录或逐任务数据量清单。表格统计任务很可能可 CPU 执行，这是推断；不能据此承诺全部 500 题的时长/内存。可把评测默认 timeout 看作上限参数，不能当实际耗时。[固定 README](https://github.com/yiyihum/da-code/blob/b211daf51fdc9b52d5087c9df28ac50191bcabed/README.md)、[实际 source 目录](https://github.com/yiyihum/da-code/tree/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/source)、[实际 gold 目录](https://github.com/yiyihum/da-code/tree/b211daf51fdc9b52d5087c9df28ac50191bcabed/da_code/gold)。

本轮建议不补：它值得作为将来新生成解法的首选任务源，但现有“题目+gold 产物”不足以无推理成本形成可信程序标签。代码仓库 MIT 不自动覆盖所有外部原始数据的许可。与 ASI 的共同统计分析主题不是同源证明，仍须输入数据与任务家族排查；本次未取得来源闭环。

## 5. DiscoveryWorld：有人工行为数据，但协议与科学代码产物不同

固定 `ScenarioMaker.py` 的八个完整科学主题包括 Proteomics、Plant Nutrients、Reactor Lab、Archaeology Dating 等；每主题配置三种难度和五个 nominal variations。另有 tutorial 和小技能测试，不能计入 120 个独立科学任务族。[固定场景定义](https://github.com/allenai/discoveryworld/blob/fd591323920be0d3786ef350955de1945aa571e5/discoveryworld/ScenarioMaker.py)。

任务例 Proteomics 要在虚拟世界中操作仪器、收集实验观测、推断规则。模型逐步输出 `USE`、`PICKUP`、移动/对话等 JSON 动作；它没有“生成一个 Python 程序、读取给定文件并写科研产物”的原生契约。环境提供任务完成度和程序化 scorecard，也可返回图像，但图像是可选观测。[官方 API 与例子](https://github.com/allenai/discoveryworld/blob/fd591323920be0d3786ef350955de1945aa571e5/README.md)。

作者确有 **human scientist action history 和 notes**，这与旧模型轨迹不同；然而它们不是人工参考 Python。原始日志记录逐步完整世界状态，作者明确提示提取可能耗几小时和较多内存；知识评分还使用 GPT-4o。单环境依赖 Pygame、NumPy 等，未声明必需 GPU，但没有 4 CPU／8 GB 日志重建成本证明。[原始数据说明及已知日志缺失](https://github.com/allenai/discoveryworld/blob/fd591323920be0d3786ef350955de1945aa571e5/data/README.md)、[依赖文件](https://github.com/allenai/discoveryworld/blob/fd591323920be0d3786ef350955de1945aa571e5/requirements.txt)。

它与 ASI 都涉及科学概念，但这种概念相似不会减少状态模拟、动作协议和标签转换工作；不建议为了使用人类日志再搭一套专门转换流程。本轮放弃，且没有下载已有模型轨迹。

## 6. 决策与后续边界

1. **本轮不补 ASI 专项训练；正式 ASI 全量评测照常保留。** “没找到可立即用的标签”不等于取消评测，也不把其他专家训练数据改名为 ASI 数据。
2. DS-1000 是最明确的未来辅助选项：若后来有余量，先按原题家族隔离并做公开输入去重，再小量验证 CPU 环境；保留完整参考代码与原测试。它只能支持“科学 Python/库使用辅助训练”的主张。
3. 若未来需要真实文件任务，先考虑 DA-Code 的小型统计/表格子集，再补完整参考程序并执行验证；现在不新开解题流水线。
4. 本次没有给出任何“4 CPU／8 GB 全量可跑”的认证或时长报价。可由静态依赖确认的 CPU 能力、未测量的运行成本、尚未闭环的来源家族，已分开记录。没有把参考产物、starter code、模型 self-report 或半自动 GT 当作全量成功轨迹。

本支仅新增此文档；未修改主进展、冻结数据、`claud.md` 或提交 Git。由 root 汇总最终数据决策。
