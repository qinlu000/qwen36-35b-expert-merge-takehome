# ASI 任务来源复查与本轮数据决定（2026-10-16）

## 最新纠正与决定

用户指出 HF ScienceAgentBench 可以直接取得，已据此纠正先前过早的放弃建议：**102条 verified 公开任务已在80落地，完整人工参考包也已下载成功（1,769,478,786字节），可读取gold/checker。** 没有再计算整包hash；按用户要求优先速度。

真实浏览器已进入作者公开 `benchmark_verified.zip`，随后完成下载并打开955条归档目录项。因此旧curl `302→401`只是该命令行访问方式的失败，不能当作资源不可取得的结论。任务92的原始gold、checker、期望结果和4个NumPy输入已单独同步80，供最小运行验证；整包同步进行中。

**用途说明纠正：官方gold文件头有避免进入训练语料的声明及canary，README明确其目的是防止SAB测试污染；不能据此直接认定许可证禁止训练。** 官方README声明多数任务CC BY 4.0、仓库代码MIT，少数任务保留上游许可。SAB不是本题四项正式评测之一，因此不应仅凭这句话永久排除它作为辅助训练来源；仍需区分作者防污染意愿、具体素材许可与本项目数据隔离。若选作训练数据，同源SAB任务不得又作为独立dev，且需排除与正式ASI的重叠并披露来源。当前SFT导出仍为0；此前“一律不进入SFT”的决定撤回。参考：[官方防污染说明](https://github.com/OSU-NLP-Group/ScienceAgentBench#benchmark-access)、[官方许可说明](https://github.com/OSU-NLP-Group/ScienceAgentBench#licensing-information)。

以下其它来源的不适配结论保留；对ScienceAgentBench的旧“本轮不补”建议已由本节覆盖。无需为了500/100复制102题或拆同族凑数。

## 与当前协议的比较基准

固定 ASI 协议为单次生成完整 Python 程序、框架执行一次、读取沙箱中的输入并写声明产物，非交互工具轨迹；4 CPU / 8 GiB / 无任务 GPU / 20 分钟总预算。来源的代码需能实际取得，输出契约、依赖、来源族隔离与执行检查须有证据。任务总行数、同一论文的子题、期望输出文件都不能直接当作相同数量的独立正确程序。

[项目冻结协议](../configs/eval/protocol_v2_unified64k8k.json)、[ASI 官方任务说明](https://github.com/apexin-ai/ASI-Bench#overview)。本次未读取正式 ASI gold 或正确性结果来选训练数据。

## 最相关候选

| 来源 | 可核到的任务与标签 | 与 ASI 的关系 | 本轮处理 |
|---|---|---|---|
| ScienceAgentBench verified | 官方 2026-04-30 verified 版，102 题来自 44 论文；完整包含输入、gold/checker | 完整 Python、读数据、写 CSV/PNG 等文件；作者有防污染声明，多数任务CC BY 4.0 | 完整包已在80解压，92号原始gold/checker通过；保留辅助数据候选，不把canary等同于许可证禁训 |
| SciCode-Verified v2 | 实核64主族/290子步描述；解答字段为空；数值目标已在先前核验下载 | CPU 数值程序近似，但主要函数返回值，不是 ASI 文件产物 | 已有两题新教师校准1通过1拒收；本轮不扩量，也不把子步算独立题 |
| D3-Gym 任务/环境 | 作者声明565任务/239科学仓库，有依赖环境、输入数据、验证脚本及参考实现；metadata未提供逐题参考程序正文 | solution.py 读取 datasets 并写 pred_results，与 ASI 文件工作流相近 | 只复查任务包，没有恢复已删除旧Qwen轨迹；镜像/参考代码获取与CPU成本尚未核实，不新建采教师流水线 |
| DS-1000 | 实读1000题均有 reference_code / code_context，论文源自451个StackOverflow原题 | 参考标签可取，但多为短科学Python库片段 | 留作未来基础库辅助源，不用其数量冒称ASI科研工作流覆盖 |
| DA-Code / DataSciBench | 分别500 /222任务；有产物评测、部分GT，但未证明逐题完整人工程序 | CSV/统计/绘图文件流较近，仍需补完整解题与执行验证 | 本轮不新增 |
| NatureBench / ScienceIDE / DiscoveryWorld | 分别是论文研究、科学代码修复、虚拟科学世界环境 | 长程GPU/ClaudeCode、C++/Fortran修改与编译、世界动作等协议差异较大 | 本轮不作为ASI direct_llm主池 |

ScienceAgentBench 的102题不能不加分组地随机拆成独立论文 train/dev；须按论文/仓库整体隔离。候选公开题面与正式 ASI 的 exact / 13-gram 排除即使零命中，也不证明语义/论文来源完全独立，scanpy/scRNA 等相近方法族继续保守hold。完整包已确认浏览器可访问；实际参考程序和输入完成检查之前，不声明训练验收通过。

一手来源：[ScienceAgentBench 官方 verified 更新与包结构](https://github.com/OSU-NLP-Group/ScienceAgentBench#updates)、[其 HF verified 注释](https://huggingface.co/datasets/osunlp/ScienceAgentBench)、[SciCode-Verified 固定数据卡](https://huggingface.co/datasets/shhu2001/SciCode-Verified/blob/eea11a866be6860725258702b39ef8651ed26abd/README.md)、[D3-Gym 官方任务接口](https://github.com/OSU-NLP-Group/D3-Gym#using-d3-gym-environments)、[DS-1000 作者项目](https://ds1000-code-gen.github.io/)、[DA-Code 作者仓库](https://github.com/yiyihum/da-code)、[DataSciBench 作者仓库](https://github.com/THUDM/DataSciBench)。

## 本线额外核查：D3、ScienceIDE、Fisher-R1

- **D3**：本机只读 shallow clone 固定 `OSU-NLP-Group/D3-Gym@5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb`。`workflow/execute_programs.py` 要求已有 `gold_program.py`，但该仓库没有发布565份参考程序正文或任务数据目录。公开 metadata 描述字段是 instruction/previews/eval_script/original_repo/discipline，不能据 README 的参考实现声明认证逐题参考正文已获取。仓库的 `training/convert_trajectories_to_alpaca.py` 使用完整 Python 程序，并把源 thinking 包进 think 标签；它证明一种可参考的数据格式，不证明存在新的强教师分区。本次没有运行该脚本、没有下载旧轨迹、没有拉565镜像。
- **ScienceIDE**：作者当前公开的是15/64环境和30/85 Hard任务预览，主要是修改已有科学模拟器源码、重编译后比较数值；不是给独立数据写Python产物。全任务银行仍在逐步公开。没有因为论文称2,812任务就把它当作2,812个当前可下载训练样本。[作者仓库](https://github.com/aitofound/ScienceIDE)、[作者项目页](https://aitonomy.org/projects/scienceide)。
- **Fisher-R1/P-Bench**：本轮实际作者仓库已增加evaluation/training和数据链接，不能沿用旧搜索摘要“只有README”的结论。HF当前425条benchmark记录有问题、p_value、decision、数据路径等字段，没有公开参考程序字段；任务集中统计假设检验，原生标签/框架包含R，不能直接冒称广泛科学Python程序SFT。[作者仓库](https://github.com/jmu27/FisherR1)、[作者数据卡](https://huggingface.co/datasets/May2222/P-Bench)。本轮未下载其数据或调用API。

## 可复核证据与后续边界

- [ScienceAgentBench/DiscoveryBench主来源报告](asi_task_sources_followup_20261016.md)。
- [DS-1000/DA-Code/DataSciBench/DiscoveryWorld四源报告](asi_task_sources_alternatives_20261016.md)。
- [先前SciCode数值校准与NatureBench记录](night_academic_asi_20261016.md)。
- 本轮仅调研和小型文本/元数据读取，没有新增付费API、GPU作业、源任务执行或大体积输入下载；D3源码clone留在ignored artifacts。没有改冻结train/val、正式benchmark协议或正式参考。
- 完整包已取得；先用已有NumPy环境验任务92，不为87/21安装重依赖，不扩采教师、不凑样本数量。用途边界见本页顶部最新决定。
