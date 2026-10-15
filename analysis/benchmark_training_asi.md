# 面向 ASI 的训练数据：官方边界与三个近邻

核验日期：2026-10-15（Asia/Shanghai）。仅查作者 README、论文、HF 数据卡／文件索引／schema 元数据；未读数据 rows、gold 文件或本题参考答案，未安装、运行任务、下载训练文件或恢复已有下载。这里区分“已有 SFT 样本”“有可执行环境但交互轨迹需自己生成”“只有 benchmark”，不把论文宣称的数据发布等同于已找到可下载训练池。

## 结论

**新发现中，D3-Gym 最值得补入候选清单：已有小型科研程序 SFT 集，也有明确的可执行环境与 verifier。** 但其现成 trajectories 是 `instruction/input/output`，论文定义为完整推理与最终程序，不能冒充带多轮命令／执行反馈的 agent 消息。若我们需要这样的交互轨迹，仍要另外在独立任务环境上采集。现有 Terminal-Corpus 科学子池继续提供多轮终端行为；两者可互补，不能称作“同 ASI harness 的现成训练数据”。

| 来源 | 已公开的可复用对象 | 真正缺少的内容 | 当前建议 |
| --- | --- | --- | --- |
| ASI 官方 | 60 正式项目两个 seed、5 个 sample、runner／scorer | 没找到独立训练池或训练轨迹发布 | 正式项目与衍生一律排除；sample 仅做协议了解，默认不转训练 |
| D3-Gym | 565 科研任务环境；Qwen3 成功推理＋程序 SFT 集 | 现成可核的逐轮工具消息；SFT 与 task_id／repo 的逐条映射 | 首选新候选，先确认来源映射与许可可筛；无需先重演全池 |
| AutoSDT-5K | 科研 instruction→程序、原文件／repo URL、逐条 license | 稳定配套环境与替代解答 verifier、多轮执行反馈 | 静态科研代码补充；较 D3 次选，不优先新造轨迹 |
| SciAgentGym／SciForge | 真实科学工具环境与闭环 runner；论文有 SFT 轨迹方法 | 未定位到作者可下载、版本固定的 SciForge SFT 训练池 | 借环境／生成思路；目前不写成“现成轨迹已可用” |

## ASI 作者是否提供训练数据

固定代码 `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc` 的 README 把资源列为 benchmark、runner、榜单和两个 seed 数据。HF 作者组织 API 此次仅返回 `ASI-Bench-seed42` 与 `ASI-Bench-seed31415`；因此准确结论是**在本次官方公开入口中没发现独立训练池**，不推断作者从未发布／永远不会发布。60 项两 seed 属于同一评测任务家族，公开参考材料不变成训练许可；5 个 fully-public sample 也不是已验证独立的训练集。[固定官方 README](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md)、[作者 HF 数据集列表 API](https://huggingface.co/api/datasets?author=Apexintelligence-AI)

## 1. D3-Gym：科研程序主候选与可执行任务池

### 实际发布、格式与验证

- 作者代码固定 `5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb`。README 列出 565 个任务、239 个原始科研 repo；任务 Docker 内有输入、preview、instruction、预装依赖、输出目录与 eval。接口是 `solution.py` 读取数据并写 `pred_results/`，`run_and_eval` 返回 pass/fail 与简短解释。环境不是任意论文复现任务的通用 harness。[固定 README](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)
- `osunlp/D3-Gym` revision `8499689ac98882a7cac9b5ef9e93365cc37df57e` 是任务 metadata，不是实际输入环境；schema 含 `task_id/task_instruction/dataset_previews/eval_script/original_repo/discipline`，train=565；Docker Hub 才是完整环境。此次没有读取 eval_script 行内容。[固定任务卡](https://huggingface.co/datasets/osunlp/D3-Gym/blob/8499689ac98882a7cac9b5ef9e93365cc37df57e/README.md)
- `osunlp/D3-Gym-Trajectories` revision `b21b5006956d7d246cf3e35277b13323780a45b2` 明确发布论文训练数据。元数据 schema 为 `instruction/input/output`，Qwen3_32B=2,153 条，14B=1,788、8B=1,306、4B=1,126；四个模型 JSON 总 201,974,682 字节，其中 32B 文件 72,175,135 字节。数据卡 MIT。**不需要为了获得这份现成 SFT 集先自己采样 16 次。**[固定训练卡](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/blob/b21b5006956d7d246cf3e35277b13323780a45b2/README.md)、[作者 HF 文件元数据](https://huggingface.co/api/datasets/osunlp/D3-Gym-Trajectories/revision/b21b5006956d7d246cf3e35277b13323780a45b2?blobs=true)、[schema／行数](https://datasets-server.huggingface.co/info?dataset=osunlp%2FD3-Gym-Trajectories)

论文的 trajectories 是完整推理＋最终解答，执行后由 silver verifier 筛成功；没有证据证明这些 JSON 已包含逐轮 shell/tool 观察。覆盖生信、计算化学、地理信息、心理与认知神经四学科。作者排除 ScienceAgentBench 原 repo，未声明针对 ASI 去污染。silver 判分与人类 gold 的一致率为 87.5%，不是每个训练答案事实正确率。作者正文的“每任务16次、共6780”与565任务相乘不一致，因此本项目按发布 metadata 核规模，不用其采样总量反推唯一训练题数。[作者论文 §2、§4、Appendix E](https://arxiv.org/html/2604.27977v1)

### 许可、来源与怎么用

任务卡声明 MIT，但作者同时列出 39 个无许可 repo、43 个 GPL／AGPL／LGPL repo 与其他许可。作者把无许可假设为 research 可用，不能替代我们自己的逐源许可判断；优先明确 MIT／BSD／Apache 等可满足发布条件的来源。任务 metadata 有 `original_repo`，训练 JSON 的公开 schema 没有 task_id／repo／license，**要做按 repo 白名单筛选必须先建立可靠映射**，不得只过滤任务 metadata 就宣称训练 trajectories 同步清洗完。[作者许可说明](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md#disclaimer)

建议将 32B 成功科研代码＋推理小池作为 E_exec 科研程序补充；如果后续要训练自调试／多轮交互，在排除 ASI 同源的 D3 独立任务上用最终确定的 agent 协议采少量轨迹。环境中的 reference／eval 保持 verifier 侧，不能让 agent 通过读 gold 取巧。此次未运行，所以不承诺 Docker 环境在 80 可用，也不承诺其银标过滤等于本项目已复验。

## 2. AutoSDT：已有科研代码 SFT，缺闭环环境

作者 `osunlp/AutoSDT-5K` 固定 revision `659b60f3fabdfc5d6b80ef08176f602f4cfb24a6`，发布 `AutoSDT_5k_with_license.json`（61,366,662 字节）。card 为 MIT；schema 有 `instruction/input/output/discipline/source_file_url/repository_url/license`，适合按源仓库和许可选择。数据卡／论文称5,404任务，当前 viewer 非partial metadata 为5,148；没有读 rows确认去重／删改原因，实际以固定文件 manifest为准。它是 instruction→程序，不能写成 shell feedback 轨迹。[固定数据卡](https://huggingface.co/datasets/osunlp/AutoSDT-5K/blob/659b60f3fabdfc5d6b80ef08176f602f4cfb24a6/README.md)、[schema／行数](https://datasets-server.huggingface.co/info?dataset=osunlp%2FAutoSDT-5K)

作者开源造题／改编和 SFT 流程，4学科，与 D3 共享 AutoSDT 构造路线，不能当作完全独立来源随意堆叠。原池包含 GNU、定制非商用和317个未给许可的repo，卡片总 MIT不替代逐条上游条件。D3作者明确指出 AutoSDT 缺配套 execution environment／evaluation script，因此无法直接验证任意替代解答。对我们而言它比从头搜论文造任务快，但闭环轨迹需求优先 D3，而不是先重建几千个AutoSDT环境。[作者仓库与 disclaimer](https://github.com/OSU-NLP-Group/AutoSDT)、[D3论文相关工作](https://arxiv.org/html/2604.27977v1)

## 3. SciAgentGym：方法与环境存在，现成训练发布未确认

固定代码 `e9dbbea4369d67694e38bf8be67bedbcaf9e9300`，仓库 Apache-2.0；README给出科学tool注册、OpenAI function schema、filesystem、database与Python环境，以及多轮执行／抽取／判分入口。它公开的259任务／1134子问是 **SciAgentBench benchmark**，不是可直接默认用于训练的SciForge数据；README的“Data & Models”当前链接为`#`，本次没有定位到独立版本固定的作者 SFT 数据下载。不是据此断言完全没有，准确状态为**尚未核到**。[固定README](https://github.com/CMarsRover/SciAgentGYM/blob/e9dbbea4369d67694e38bf8be67bedbcaf9e9300/README.md)、[固定代码许可](https://github.com/CMarsRover/SciAgentGYM/blob/e9dbbea4369d67694e38bf8be67bedbcaf9e9300/LICENSE)

论文 SciForge 按工具依赖图构造可运行调用链，再从执行结果反推任务，SFT目标含tool_call/tool_response与答案；这在行为上贴近需要的科研工具链。它的学科专用函数协议与 ASI CLI/terminal不相同，不能无适配搬用。若未来采集，应使用独立工具组合任务并明确源许可，避免直接拿其评测gold/refined答案生成训练。论文给的方法参考，不等于我们已经拿到现成训练文件。[作者论文 §5、Appendix E.2](https://arxiv.org/html/2602.12984v1)

## 不把 ScienceAgentBench 本身当默认训练池

ScienceAgentBench 提供102评测任务、self-debug／OpenHands runner和日志保存，并不意味着作者已经发布可自由再分发的独立训练轨迹。其README还要求不要在线再分发解压的benchmark文件。之前保留的“借recipe、自己选独立任务”边界继续成立；若要现成训练数据，本轮D3比直接搬ScienceAgentBench参考程序更合适。[固定说明](https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/c26e151ed601ba109dc4d35e057ff8e73fec469d/README.md)

## 与当前方案怎么接

1. **现成优先。** Terminal科学子池提供通用终端交互；D3成功推理＋程序补科研实现。OpenScience/OpenR1仍只承担知识／推理，不能作为已经补齐ASI工作流的证据。AutoSDT作静态备选；SciForge不进入当前“已拿到训练数据”表。
2. **独立性检查到原论文／repo。** 对候选保留原repo、文件URL、任务族和论文标识，与允许使用的ASI目录／来源metadata检查同源、变体和改写；D3排除ScienceAgentBench不代表ASI干净。没有映射的条目不宣称已做repo级排除。正式ASI 60任务及公开参考和同源衍生不用于训练或dev。
3. **harness尚未冻结。** ASI direct_llm不是现成多轮反馈agent，CLI适配器各有协议；当前不能承诺这些数据与ASI“同harness”。先决定最终ASI适配器与工具协议，再决定是否把独立D3环境用于少量同协议采集；这个选择无需强制重演全部已有SFT样本。
4. **当前只交候选证据。** 用户跳过抽样复验不等于数据已验证成功、无污染或已适配；本次未新增下载计划、未下载新池，未新增执行或采集。
