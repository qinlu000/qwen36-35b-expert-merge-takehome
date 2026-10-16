# ASI 任务来源复查与本轮数据决定（2026-10-16）

## 决定

用户本轮要求“ASI 你调研一下，找一下有没有相关的任务；实在没有就不管了”。有相关公开任务；本次没有找到能在当前已验环境中直接组成完整、可信、低适配成本的 ASI 训练集。因此**本轮不追加 ASI 专项训练数据，也不再为 500 train / 100 val 目标展开采集工程**。ASI 必交正式全量评测保留；没有独立 ASI dev 时，不用正式 ASI 的答卷/得分来挑训练样本或合版参数。

以下是数据决策，不是宣称这些来源不能使用，也不是取消 ASI benchmark。已有学术/SWE/Terminal 数据及其训练继续；三专家方案中的执行专家若只用 Terminal 数据，报告中明确其数据范围，不能把它称为已专门训练过 ASI。

## 与当前协议的比较基准

固定 ASI 协议为单次生成完整 Python 程序、框架执行一次、读取沙箱中的输入并写声明产物，非交互工具轨迹；4 CPU / 8 GiB / 无任务 GPU / 20 分钟总预算。来源的代码需能实际取得，输出契约、依赖、来源族隔离与执行检查须有证据。任务总行数、同一论文的子题、期望输出文件都不能直接当作相同数量的独立正确程序。

[项目冻结协议](../configs/eval/protocol_v2_unified64k8k.json)、[ASI 官方任务说明](https://github.com/apexin-ai/ASI-Bench#overview)。本次未读取正式 ASI gold 或正确性结果来选训练数据。

## 最相关候选

| 来源 | 可核到的任务与标签 | 与 ASI 的关系 | 本轮处理 |
|---|---|---|---|
| ScienceAgentBench verified | 官方 2026-04-30 verified 版，102 题来自 44 论文；HF 是任务注释，官方完整包声明含 gold_programs / eval_programs | 完整 Python、读数据、写 CSV/PNG 等文件，形式最接近；多领域依赖及图像评分仍须筛 | 最优条件备选。作者 SharePoint 完整包本次 302 后401，未拿到参考正文；不把文件名当作已取得答案，不继续绕登录或扩工程 |
| SciCode-Verified v2 | 实核64主族/290子步描述；解答字段为空；数值目标已在先前核验下载 | CPU 数值程序近似，但主要函数返回值，不是 ASI 文件产物 | 已有两题新教师校准1通过1拒收；本轮不扩量，也不把子步算独立题 |
| D3-Gym 任务/环境 | 作者声明565任务/239科学仓库，有依赖环境、输入数据、验证脚本及参考实现；metadata未提供逐题参考程序正文 | solution.py 读取 datasets 并写 pred_results，与 ASI 文件工作流相近 | 只复查任务包，没有恢复已删除旧Qwen轨迹；镜像/参考代码获取与CPU成本尚未核实，不新建采教师流水线 |
| DS-1000 | 实读1000题均有 reference_code / code_context，论文源自451个StackOverflow原题 | 参考标签可取，但多为短科学Python库片段 | 留作未来基础库辅助源，不用其数量冒称ASI科研工作流覆盖 |
| DA-Code / DataSciBench | 分别500 /222任务；有产物评测、部分GT，但未证明逐题完整人工程序 | CSV/统计/绘图文件流较近，仍需补完整解题与执行验证 | 本轮不新增 |
| NatureBench / ScienceIDE / DiscoveryWorld | 分别是论文研究、科学代码修复、虚拟科学世界环境 | 长程GPU/ClaudeCode、C++/Fortran修改与编译、世界动作等协议差异较大 | 本轮不作为ASI direct_llm主池 |

ScienceAgentBench 的102题不能不加分组地随机拆成独立论文 train/dev；须按论文/仓库整体隔离。候选公开题面与正式 ASI 的 exact / 13-gram 排除即使零命中，也不证明语义/论文来源完全独立，scanpy/scRNA 等相近方法族继续保守hold。完整包可访问之前，不声明它已达到本项目训练验收。

一手来源：[ScienceAgentBench 官方 verified 更新与包结构](https://github.com/OSU-NLP-Group/ScienceAgentBench#updates)、[其 HF verified 注释](https://huggingface.co/datasets/osunlp/ScienceAgentBench)、[SciCode-Verified 固定数据卡](https://huggingface.co/datasets/shhu2001/SciCode-Verified/blob/eea11a866be6860725258702b39ef8651ed26abd/README.md)、[D3-Gym 官方任务接口](https://github.com/OSU-NLP-Group/D3-Gym#using-d3-gym-environments)、[DS-1000 作者项目](https://ds1000-code-gen.github.io/)、[DA-Code 作者仓库](https://github.com/yiyihum/da-code)、[DataSciBench 作者仓库](https://github.com/THUDM/DataSciBench)。

## 本线额外核查：D3、ScienceIDE、Fisher-R1

- **D3**：本机只读 shallow clone 固定 `OSU-NLP-Group/D3-Gym@5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb`。`workflow/execute_programs.py` 要求已有 `gold_program.py`，但该仓库没有发布565份参考程序正文或任务数据目录。公开 metadata 描述字段是 instruction/previews/eval_script/original_repo/discipline，不能据 README 的参考实现声明认证逐题参考正文已获取。仓库的 `training/convert_trajectories_to_alpaca.py` 使用完整 Python 程序，并把源 thinking 包进 think 标签；它证明一种可参考的数据格式，不证明存在新的强教师分区。本次没有运行该脚本、没有下载旧轨迹、没有拉565镜像。
- **ScienceIDE**：作者当前公开的是15/64环境和30/85 Hard任务预览，主要是修改已有科学模拟器源码、重编译后比较数值；不是给独立数据写Python产物。全任务银行仍在逐步公开。没有因为论文称2,812任务就把它当作2,812个当前可下载训练样本。[作者仓库](https://github.com/aitofound/ScienceIDE)、[作者项目页](https://aitonomy.org/projects/scienceide)。
- **Fisher-R1/P-Bench**：本轮实际作者仓库已增加evaluation/training和数据链接，不能沿用旧搜索摘要“只有README”的结论。HF当前425条benchmark记录有问题、p_value、decision、数据路径等字段，没有公开参考程序字段；任务集中统计假设检验，原生标签/框架包含R，不能直接冒称广泛科学Python程序SFT。[作者仓库](https://github.com/jmu27/FisherR1)、[作者数据卡](https://huggingface.co/datasets/May2222/P-Bench)。本轮未下载其数据或调用API。

## 可复核证据与停止点

- [ScienceAgentBench/DiscoveryBench主来源报告](asi_task_sources_followup_20261016.md)。
- [DS-1000/DA-Code/DataSciBench/DiscoveryWorld四源报告](asi_task_sources_alternatives_20261016.md)。
- [先前SciCode数值校准与NatureBench记录](night_academic_asi_20261016.md)。
- 本轮仅调研和小型文本/元数据读取，没有新增付费API、GPU作业、源任务执行或大体积输入下载；D3源码clone留在ignored artifacts。没有改冻结train/val、正式benchmark协议或正式参考。
- 若以后恢复ASI专项数据，首选解决ScienceAgentBench verified参考包访问并挑少量CPU文件任务；先验少量参考脚本再决定扩量。不能在包不可取时假造gold或为了目标数量复制同族。
