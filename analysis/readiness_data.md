# 训练候选数据就绪检查（2026-10-15）

2026-10-16长度更新：[已下载轨迹实测](trajectory_lengths.md)已覆盖SWE39片4992条加权样本、Terminal26片3328条加权样本＋mixed5689条全量、D3 2153条全量和OpenR1 2000条分层样本。后文早期两例长度只作历史检查，不用于估算全库。当前SWE来源成功子样本仅约0.12%整条≤8K，工具轨迹不能默认直接截尾为8K训练；长度合格与环境/成功/去污染资格仍分开。

本次只检查已经下载完成且下载日志包含 SHA-256 校验收据的文件。未读取 .part，未执行轨迹命令、样本代码、任务验证器或模型 API。各来源最多检查两条固定记录的结构；这是格式检查，不是成功率或质量抽样复验。

检查工具使用已有环境，无新增依赖：
- Parquet：/data/caoqinlu/envs/datamind-code/bin/python（pyarrow 20.0.0）。
- 可用 tokenizer 环境：/data/caoqinlu/envs/datamind-sft/bin/python（transformers 4.55.0、tokenizers 0.21.1、pyarrow 25.0.1）；已成功仅本地加载固定 Qwen tokenizer；没有加载权重或推理模型。
- 结构审计：artifacts/data/audits/readiness_structure_20261015.json（ignored，无消息正文、命令或补丁）。

下载在检查期间继续，因此以下计数是本次检查快照，不是最终下载清单。

## 已查到的结构

| 来源 | 检查覆盖 | 结论 |
|---|---|---|
| Terminal-Corpus | 6 个完整 Parquet，合计 68,534 行；首片 2 条结构 | 与 Terminus-2 的 JSON 动作族相符；精确版本、模板、观察与状态规则仍未锁齐。 |
| OpenR1-Math | 3 个完整 Parquet，合计 28,119 行；首片 2 条结构 | 静态 user/assistant 问答，含 think 标记；有 source、uuid 和多个正确性字段，可进一步做来源及候选解筛选。 |
| Open-SWE | 后续到达 7 个完整片，元数据合计 17,500 行；首片 2 条结构 | 原生 bash(command)、returncode/output、提交标记与新 subshell 提示均核到。原始嵌套结构需要规范化后才可渲染 Qwen 模板。 |
| OpenScienceReasoning-2 | 完整文件 1,600,812 行；前 2 条结构 | 实际只有 input/output/expected_answer，静态问答；没有来源或正确性元数据。 |
| D3-Gym Qwen3-32B | 完整 JSON 共 2,153 条；前 2 条结构 | 实际只有 instruction/input/output 三列，为单次推理与程序解答；不是结构化多轮交互。 |

固定 revision 及来源级许可声明见 data_sources.json。这里没有审计各原始题源的许可，也没有完成四项 benchmark 的重叠清理。

### Terminal：动作结构吻合，但不能自动当作已验证成功数据

实际 schema：
- conversations: list<struct<content:string, role:string>>
- agent、model、model_provider、date、task、episode、run_id、trial_name: string
- enable_thinking: bool

两条均为 user/assistant 交替，分别 18 和 22 条消息；无独立 system 或 tool 角色。assistant 内容内检测到 JSON 顶层 analysis、plan、commands、task_complete；commands 条目含 keystrokes 和 duration。没有 native tool_calls 列；这不是原生 bash(command) 工具调用数据。

该动作表达与 Terminus-2 的持续终端 JSON 交互相近，不能因此证明 tmux 状态、提示、超时、反馈渲染、context 截断及版本全部一致。两条中未解析到 observation JSON；只代表本检查未得到该结构，不等于观察缺失。

两条均未检测到 task_complete=true，也未检测到 SWE 的提交标记。样本较少，不能据此断言整库不完整、失败或成功。schema 没有 resolved/result 列，因此不能直接按成功标签筛选；需核作者筛选规则及其他可验证的元数据后定训练用途。

来源可筛字段有 task、episode、run_id、trial_name、enable_thinking；没有 repo/repository、license、instance_id、source 或 uuid。来源级许可来自固定模型卡，而不是逐行字段。不能仅凭现有列宣称完成正式评测去重。

### 长度问题需要在训练前解决

两条 Terminal 轨迹总内容分别为 79,825、105,850 字符；最长单消息为 10,068、14,252 字符，assistant 内容合计为 36,136、48,916 字符。字符数不等于 token；随后已使用固定 tokenizer 实测，结果见下表。

拟议的 8K 训练窗口不能不经统计就直接整条截断。已使用固定 Qwen tokenizer 计算有限样本长度；接下来决定保留完整短轨迹、按完整交互边界构造窗口或调整窗口长度。不得切断 JSON 动作后仍把它当完整监督样本。当前没有生成训练窗口。

两条 OpenR1 消息总长度分别为 16,092、15,402 字符，assistant 为 15,781、15,097 字符。真实 tokenizer 长度见下表，不能用这两条外推全库长度分布。

### OpenR1：筛选字段较全，但监督与验证标签的对应要核实

除 problem、solution、answer、messages 外，真实 schema 包含 problem_type、question_type、source、uuid、is_reasoning_complete、generations、correctness_math_verify、correctness_llama、finish_reasons、correctness_count。

两条是 user/assistant 两消息，assistant 带 think 标记。多候选 generations 及对应正确性列表不自动证明 messages 内的答案恰好对应某个已验证候选。后续生成训练集时要核对对应关系；本次未打印或评判答案内容。

## 待讨论问题

1. Terminal 精确 agent revision、prompt、反馈格式及状态规则还需与目标设置对齐。
2. Terminal 没有逐行 success/resolved 字段，不能默认全库为成功轨迹；如何保留非最终成功的有用过程需单独制定。
3. 8K 上下文与真实交互轨迹长度可能冲突，先测 token 再定窗口，不直接截尾。
4. OpenR1 messages 与 generations/验证标签的对应关系要核实，source/uuid 仅提供筛选入口。
5. Open-SWE 的嵌套消息格式需要结构规范化；OpenScience 缺少来源 ID 和正确性字段，不能直接按元数据去重或筛成功。
6. 四源的正式评测重叠清理、跨来源去重和许可证边界都尚未完成。
7. D3 实际缺少 task_id/source 等来源映射字段。与其 565 个环境的对应如何建立、是否需要由官方 direct adapter 接入，仍需确定。

## 固定 tokenizer 的有限样本计数

本地使用 Qwen/Qwen3.6-35B-A3B revision 995ad96eacd98c81ed38be0c5b274b04031597b0 的 tokenizer 与模板，local_files_only=True、trust_remote_code=False；没有模型权重或网络调用。实际加载 Qwen2TokenizerFast 成功，模板显式包含 preserve_thinking 控制。参数为 enable_thinking=True、preserve_thinking=True、add_generation_prompt=False。

| 来源 | 原始 content token 和（2 条） | 渲染 chat 后 token（2 条） | assistant token 和（2 条） |
|---|---:|---:|---:|
| Terminal | 21,085 / 29,576 | 21,174 / 29,685 | 9,268 / 13,115 |
| OpenR1 | 5,457 / 4,630 | 5,467 / 4,640 | 5,373 / 4,546 |
| D3 | 6,635 / 7,853 | 6,650 / 7,868 | 4,402 / 6,226 |

D3 计数临时映射 instruction→system、input→user、output→assistant，仅用于量长度；尚未确定最终训练模板，更不能因此认定其匹配 ASI agent 协议。两条均检测到 think 标记及 Python fenced code，但没有独立工具调用与反馈结构。

Terminal 两条整轨迹和 assistant 监督总量均超过 8K，8K 窗口决策需要处理交互边界及历史上下文。OpenR1、D3 本次两条在 8K 内，不能据此声称来源整体都能装入 8K。

## D3 来源筛选的实际限制

固定候选 osunlp/D3-Gym-Trajectories revision b21b5006956d7d246cf3e35277b13323780a45b2，Qwen3_32B_trajectories.json 完整文件共 2,153 条。结构仅 instruction、input、output 三个字符串字段；没有 task_id、instance_id、source、uuid、逐行 license、resolved/result 或多轮 messages。需要从作者任务定义另建映射，不能假定现成 ID 可直接关联环境。来源级成功筛选声明与逐行可核标签是不同的证据。

## 追加：Open-SWE 实际协议已核到（后续完成文件）

补查时元数据范围为 7 个完整 Parquet、17,500 行；仅首个 scale-swe/train-00007-of-00017.parquet 的前两条检查结构。

- 可筛字段确有 repo、license、instance_id、trajectory_id、resolved、hf_dataset_name。尚未执行这些字段的全量筛选、许可证审计或正式评测排除。
- messages 是 role/content/reasoning_content/tool_calls 嵌套结构；tools 为 JSON 字符串列表。
- 两条工具定义和实际调用均只有 bash，参数键 command。
- tool 消息实际 JSON 键为 returncode、output。
- 结束命令均检测到 COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT。
- 新 subshell、不持续 shell 状态及提交标记的提示在首个 user 消息中检测为 true；system 消息未匹配这三种短语，不能仅在 system 角色中检索。
- 两条分别 107、75 条消息；角色计数分别 system 1/user 1/assistant 53/tool 52 和 system 1/user 1/assistant 37/tool 36。

这些是支持 mini-swe-agent 协议接近的直接结构证据。仍未证明源 agent 与目标精确 commit、工具权限、截断规则和任务环境完全一致。

### Qwen 模板的小适配与长度

将原始记录直接传入固定 Qwen apply_chat_template，两条均出现 TypeError。仅做消息结构规范化——省略 None 可选字段、None content 改为空串、function.arguments 从 JSON 字符串解析为字典——后即可成功渲染。没有改写命令、工具返回或动作语义；本次仅在内存试模板，没有生成训练文件。

| 样本 | 仅 content tokens | reasoning_content tokens | 加工具定义和模板后的 tokens |
|---|---:|---:|---:|
| 1 | 31,335 | 0 | 40,320 |
| 2 | 11,913 | 0 | 18,933 |

工具参数和消息模板占用显著，不能只按 content 字符或 token 统计训练长度。两条也都超过拟议 8K 窗口；不能把样本长度证据外推全库比例。

## 追加：OpenScience 实际结构已核到

完整 Parquet 元数据为 1,600,812 行；schema 仅 expected_answer:string、input:string、output:string。没有 source、uuid、instance_id、repo、license、resolved 或可验证正确性列。

前两条 output 均检测到 think 标记。临时映射 input→user、output→assistant，保留 thinking 的模板长度分别 3,411、5,802 tokens（原始 content 和为 3,401、5,792）。没有把 expected_answer 作为额外监督输入，没有打印答案内容。

这证明其是静态推理训练格式，不是工具交互轨迹。来源追踪、题目独立性、答案质量及图像覆盖仍不能由该 schema 直接证明。


## 本轮结束时的完整下载与元数据统计

原四源全部81文件/24,982,461,699B通过固定revision、字节数与SHA核验，失败0；新增D3候选2文件/72,176,365B也完成。原始文件不入Git；最终回执artifacts/data/download_receipts.json，候选回执candidate_download_receipts.json。文件完整性不代表训练质量、许可/去污染或复现已通过。

| 来源 | 完整Parquet片 | metadata行数 |
| --- | ---: | ---: |
| Open-SWE mini/Qwen3.6 | 39 | 95,291 |
| Terminal skill-based | 26 | 139,841 |
| OpenScienceReasoning-2 | 1 | 1,600,812 |
| OpenR1 default | 10 | 93,733 |

OpenR1这里是已选default的完整文件，不能将名称220k误当该config行数。D3 JSON为2,153行。以上都是原始发布行数，不是独立任务数或最终合格训练样本数。

额外执行scripts/audit_swe_metadata.py，仅读repo/license/instance_id/resolved列，不读messages、patch、测试。全39片得到39,540个不同(repo,instance_id)组合，另55,751行重复这些任务组合；不等于重复轨迹，应按任务族分组后再切dev。resolved=1有32,231行，0有53,622行，-1有9,438行。许可字段均为MIT/Apache-2.0/BSD-2/3-Clause，仍需保留来源并核上下游条件。

从官方固定V2全部642个任务目录名提取11个repo，规则存configs/data_exclusions.json。当前训练文件与这些repo大小写不敏感精确匹配为0，缺repo行0；这只完成exact-repo初筛，**不证明fork/改名/PR同源及跨其他benchmark的污染排除**。源行数/完整性/元数据结果快照见source_snapshots/preparation_checks_20261015.json。

## 2026-10-16：扩大harness结构验收

后续[sandbox介绍专项](trajectory_sandbox.md)进一步确认环境恢复入口：SWE上游有镜像/初态/安装字段，Terminal mixed有环境构建与输入资产，D3作者报告2,153条32B程序经对应环境silver判分保留。后者是来源级验证依据，仍不是本项目逐条执行回执，也不是OpenCode多轮工具过程。环境打包默认值和原teacher实际运行参数分开记录。

新增实际检查见[harness兼容性报告](harness_compatibility.md)：SWE39片624条全部单bash，36,400个非终止观察可唯一配对；原始模板输入全部报错、规范化后624条均渲染。Terminal26片260条，共2,058条assistant消息；去额外think后1,930可被目标parser接受，128报错，且parser本身仍有容错，不能当成功率或严格合格率。

日志/N体两个训练例子已找到题面SHA256相同的mixed记录，但无完成标记/逐条grader结果；不同difficulty同ID存在题面碰撞，不能按裸ID连接任务/轨迹或独立切dev。固定Qwen模板的两个false开关不会清除所有已有teacher推理，非思考数据需显式规范化；JSON analysis/plan与可见Explanation保留。D3依然是静态程序候选；ASI OpenCode的图片能力声明缺口已记录。此次没有训练文件导出、轨迹命令执行、模型/API调用或正式评测。
