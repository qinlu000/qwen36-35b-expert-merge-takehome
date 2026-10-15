# ASI-Bench 判分 API 调用量：固定版本静态审计

更新：2026-10-15。固定框架 `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`，open seed31415 数据 revision `0fa14219cafdbab634d8b3cfbce238a8735a214f`。本次复用框架缓存和 task_eval 白名单元数据，补查通用 text/VLM scorer；对 NNLS 自定义 scorer 只做 AST 调用点与参数传递提取，没有阅读/输出 rubric、实际数值参考、正式题面、答案或参考图，没有执行 scorer/API，也没有访问任何凭据。

## 可用于预算的结论

**一次完整 ASI 评测（60任务×B1–B4=240条件），已核的 Judge 配置展开为约 132 个正常请求槽：56 次文本、76 次视觉。Base、交互执行专家、最终合版三模型共 720 条件，对应 396 槽：168 次文本、228 次视觉。**

这里“请求槽”指相关评分步骤均被执行、所需产物存在、Judge 单次成功且不重试时的静态请求次数；不是对运行后实际调用数的测量，也不是绝对最低值。模型可能缺图、缺文件或未通过硬 gate，从而跳过后续 Judge；实际请求可更少。已核范围还未证明全部自定义 scorer 传递依赖都没有额外 API，因此 396 也不能称全局严格上限。

被测 Qwen 的作答生成使用 HPC 本地服务，与本文件估算的远程评分 API 分开。本文件不包括 HLE 判分、开发集评分、teacher 采集或重复执行整轮评分。

| 范围 | 文本 Judge | 视觉 Judge | 合计正常请求槽 |
|---|---:|---:|---:|
| 60任务，只跑一个 B 层，一个模型 | 14 | 19 | 33 |
| 完整四层，一个模型 | 56 | 76 | **132** |
| Base + 交互专家 + 合版，完整四层 | 168 | 228 | **396** |
| 上述三模型，通用外层每槽最多3次尝试的预算展开 | ≤504 | ≤684 | **≤1188 外层调用尝试** |

最后一行只覆盖这些已核调用点的 scorer 自己的 retry 循环，不能把它当作底层 HTTP 请求次数或收费 token 的严格上限。SDK/网关自身重试、整批重评分、自定义 scorer 额外调用需另计；失败请求是否计费取决于网关，不能统一填零。

来源：[完整任务与条件元数据清单](source_snapshots/protocol/asi_task_ids.json)、[文本 Judge 单次/num_judges 循环](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/llm_judge.py#L239-L269)、[视觉 Judge num_judges 循环](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L200-L234)、[MAX_RETRIES=3](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py#L22-L23)。

## 逐任务展开，不能按“每题一次”估算

所有未列出的47项均没有显式 judge model 配置；本次没有把47项 custom scorer 全部展开，不能据此证明其绝无外部请求。下表列出13项显式 `openai/gpt-5.5` 配置所对应的已核调用点。每项四个 B 层；表中次数已包含 num_judges。

| task_id | 每B层文本槽 | 每B层视觉槽 | 四层/单模型合计 | 四层/三模型合计 |
|---|---:|---:|---:|---:|
| biology.calcium_ip3_dyk_oscillations | 0 | 1 | 4 | 12 |
| biology.contextual_dna_regime_mapping | 0 | 1 | 4 | 12 |
| biology.protein_folding_go_model | 0 | 1 | 4 | 12 |
| chemistry.metadynamics_for_dipeptide_in_vacuum | 1 | 0 | 4 | 12 |
| chemistry.sapt_water_dimer | 1 | 0 | 4 | 12 |
| chemistry.vtst_tunneling_corrections | 0 | 1 | 4 | 12 |
| earth_science.2_e_soil_carbon_nitrogen_cycling | 0 | 1 | 4 | 12 |
| electrical_engineering.cmos_opamp_design | **12** | 0 | **48** | **144** |
| materials.ising_domain_growth | 0 | 3 | 12 | 36 |
| math.nnls_modulus_deblur | 0 | **3** | 12 | 36 |
| physics.ag_strip_dielectric_inference | 0 | 1 | 4 | 12 |
| physics.ks_2d_anisotropic | 0 | **6** | 24 | 72 |
| physics.paired_nanorod_negative_index_retrieval | 0 | 1 | 4 | 12 |
| 合计 | **14** | **19** | **132** | **396** |

具体展开：

- 通用 `multimodal` 出现于9个任务、10个 scoring 配置；其中 KS 有两组各 num_judges=3，Ising 有一组3，其余7组各1，共16槽/B层。四层单模型64槽，三模型192槽。
- 通用 `llm_judge` 出现于3个任务、6个配置。CMOS 的一个 gate 和三个 scoring 配置各 num_judges=3，共12槽/B层；另两个任务各1槽，共14槽/B层。四层单模型56槽，三模型168槽。
- NNLS 的 `nnls_modulus_multimodal_quality` 不是通用 scorer 名称。仅用 AST 核查固定代码：类 `NnlsModulusMultimodalQuality` 在第789行恰有一次 `MultimodalScorer().score(pred_dir, ref_dir, config)` 委托，原 config 直接传入，类内无循环；task_eval 该项 num_judges=3，故可确定上述单次委托额外3槽/B层。四层单模型12槽，三模型36槽。类中的后续文件质量 gate及其他 helper 没有展开；不据这个局部检查宣称所有自定义逻辑都没有其他 API。
- 合计为通用360槽/三模型，加已核 NNLS 委托36槽，即396。不能再把 num_judges=3 额外乘一次。

硬 gate 行为：官方框架会评所有 gates，若任何 hard gate 失败，整个 weighted scoring 阶段不执行。故 CMOS gate 的 Judge 可能执行而后续9个 scoring Judge槽不执行。文本预测文件/视觉预测图不存在时，通用 scorer 提前返回有效零分，不会继续相应 Judge 调用。

来源：[CMOS固定评分配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/electrical_engineering/cmos_opamp_design/task_eval.yaml)、[KS固定配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/physics/ks_2d_anisotropic/task_eval.yaml)、[NNLS固定配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/math/nnls_modulus_deblur/task_eval.yaml)、[NNLS仅AST核过的委托点](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/math/nnls_modulus_deblur/custom_scorer.py#L784-L790)、[gates及scoring控制流](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/scoring.py#L114-L180)、[文本缺文件提前返回](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/llm_judge.py#L63-L109)、[图像缺失提前返回](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L149-L172)。

## token 与图像：哪些可静态求出，哪些不能

**已核396槽在无重试、完整到达所有调用时，配置的输出 token 总上限为291,888（约0.292M）**。这是请求参数 max_tokens 的展开，不是实测输出，也不能保证替代模型/网关对该字段、推理 token 的处理与原模型完全相同。

| 类型 | 三模型正常槽 | 每次输出cap | 无重试输出cap合计 |
|---|---:|---|---:|
| 两个单Judge文本任务 | 24 | 1024 | 24,576 |
| CMOS 文本 | 144 | 两组250、两组220，分别各3次/B层 | 33,840 |
| 通用视觉 + NNLS视觉委托 | 228 | 1024 | 233,472 |
| 合计 | **396** | — | **291,888** |

单模型对应97,296输出 token cap。官方3次外层尝试展开后约0.876M输出token cap，但实际失败是否生成了输出、生成了多少、是否收费必须取provider usage，不以此代替实际消费记录。

图像附件计数：

- 通用192个视觉槽每次声明预测图+参考图，若两者均存在，则384份图像附件。
- NNLS 的36个视觉槽只声明预测图，无 ref_image，故36份附件。
- 三模型合计 **420份图像附件**；单模型140份。它们含多Judge对同一图的重复输入，不能称420张独立图片。
- 预测图不存在时该槽不请求；参考图缺失时通用实现可能只发预测图。实际尺寸、分辨率、图像token规则和网关转码都未测；不得按PNG字节数/base64字符数直接换算成模型token，也不假设多次请求共享免费图像缓存。

文本输入：已核6个通用文本Judge配置各只声明一个预测文本文件，没有 ref_file/extra_pred_files/extra_ref_files；每次最多读取10,000字符预测内容，再添加任务rubric、系统提示和固定包装。三模型168个文本槽对应预测内容上限1.68M字符，**字符不是token**；完整输入量还取决于模型输出文件长度及rubric长度。本次不打开rubric或实际模型产物来估算token。

费用应按网关实际价格、倍率、usage计算：`cost = input_tokens/1e6 × input_price + output_tokens/1e6 × output_price`，图像的等效输入token和失败重试另计。约400次请求说明ASI的判分量级；无法仅凭“可调用某模型”得出精确金额，先用自造图文样例核对网关usage与计费即可，不必先评分正式任务。

来源：[文本默认1024 token / 10000字符及文件读取](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/llm_judge.py#L63-L109)、[文本截断实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/llm_judge.py#L171-L219)、[视觉默认输出及双图构造](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L129-L193)、[文本外层重试](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/llm_judge.py#L271-L318)、[视觉外层重试](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L243-L287)。

## GPT-5.5 原协议与 GPT-5.6 Luna 替代实验

本次审计**没有修改任何评分配置**。固定原配置的模型是 `openai/gpt-5.5`，不能因HKUSTGZ网关可用GPT-5.6 Luna便声称已具备原Judge，也不能把替代Judge结果写成该版本原评分模型的完全复现。网关的实际模型ID、视觉能力、兼容性、倍率与余额由另一路自造样例核验。

如果决定使用GPT-5.6 Luna作为本实验替代Judge，应在正式Base评分前冻结真实模型ID、网关、prompt/rubric、temperature、num_judges、token、retry和图像处理；同一benchmark内所有模型沿用同一替代配置。上述396槽在保持scorer调用结构和num_judges时仍可作为预算基数，评分语义与金额均不能直接等同原GPT-5.5配置。不要用额外正式题目调Judge以追求更高分。

尚未静态精确的部分：其他自定义scorer/API传递依赖；图像实际token；替代网关的推理token/重试/计费；评价失败后的整批重跑。因此文档给出“已核调用槽与输出cap”，不伪造总账精确值。

来源：[默认模型与别名](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py#L87-L102)、[endpoint override保留task model](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py#L197-L204)。

安全派生审计存于 ignored `artifacts/protocol_sources/asi/judge_budget_config_allowlist.json`（配置字段、文件是否存在的声明及数量，无具体文件内容）和 `nnls_judge_delegation_ast_allowlist.json`（调用名、行号、原config传递，无评分算法/参考值）。
