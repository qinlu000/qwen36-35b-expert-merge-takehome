# 新近强开源teacher的科研/学术训练轨迹候选

核验：2026-10-16，北京时间。通过ego-browser读取发布者一手数据卡、固定revision文件元信息与HF schema/size API；未下载大文件、读取正式HLE/ASI题面答案、运行任务、模型API或训练。这里“新近teacher”指可核到DeepSeek-V4-Pro/GLM-5.2等准确发布名，不能据此保证比本题准确Qwen3.6 checkpoint更强或一定带来增益，也不声称搜尽所有来源。

## 结论与精选四源

**HLE文本学术专家确有比原OpenScience R1-0528/OpenR1 R1更新的一手现成数据，优先核NVIDIA的Science-v2与Math-v4。** 科研程序侧找到DeepSeek-V4-Pro生成的生态R/Python小池，但无独立执行成功证据；尚未核到可直接替换D3的、同ASI产物契约且已验证成功的新代teacher大池。不要把Python TIR或一般工具对话直接当ASI科研程序交付。

| 优先级/来源 | 准确teacher与发布时间证据 | 可下载规模/格式 | 对项目作用与主要限制 |
| --- | --- | --- | --- |
| 优先：nvidia/Nemotron-SFT-Science-v2 | DeepSeek-V4-Pro、DeepSeek-V3.2、Kimi-K2-Instruct、GPT-OSS混合；HF建2026-05-26、改06-04，卡称创建05-13 | 作者称2,837,712行；4 JSONL实际文件总52,685,434,022B，约49.07GiB | 物/化/生，CoT/Python/Tavily；metadata.generation_model可筛teacher。不是全部V4，也不覆盖图像/全部人文学科；来源/成功过滤仍需核 |
| 优先：nvidia/Nemotron-SFT-Math-v4 | **DeepSeek-V4-Pro High**；HF建05-26、改08-12，卡称创建05-01 | **545,431行**，12 Parquet共5,537,896,707B；COT285,516、TIR259,915 | 参考答案匹配过滤、源字段较完整，可替代/补充旧数学池；需同源去重，不能把TIR改名为终端轨迹 |
| 备选：nvidia/Nemotron-Math-Proofs-v2 | **DeepSeek-V4-Pro Max**；HF建06-01、改06-16，卡称创建05-01 | 作者称82,737 traces/5,752 unique problems；1 JSONL 17,131,378,160B | 自然语言proof/verification/meta-verification；超长且任务重复多，不适合按行随机切；未证明全部是正确proof或可当答案示范 |
| 小量科研候选：alrobles/ecocoder-scientific-reasoning | **DeepSeek v4 Pro，reasoning_effort=high，temperature=.2**；HF建/改06-06，卡示例generation06-01 | **train1,268/validation159/test159**，3 JSONL总5,025,813B | 生态科学→推理→R/Python代码，73方法/18类；仅quality score筛选，未提供真实环境/独立执行成功，且约60% R不自动符合ASI Python产物 |

这四源有公开数据文件。teacher名来自发布者方法声明，并非本次重新验证调用日志或精确模型权重revision；特别是DeepSeek-V4-Pro没有标0813，GPT-OSS在Science卡只给系列名，不能擅自补成某一精确权重。HF最后修改日也不等于所有轨迹重生成日。

## 固定版本与真实文件证据

| 来源 | 固定revision | 发布者卡 / 可复核文件API |
| --- | --- | --- |
| Science-v2 | 6536a5021222a94126968e8c92f29ee47fc8a7df | [卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/6536a5021222a94126968e8c92f29ee47fc8a7df/README.md)、[固定文件元信息](https://huggingface.co/api/datasets/nvidia/Nemotron-SFT-Science-v2/revision/6536a5021222a94126968e8c92f29ee47fc8a7df?blobs=true) |
| Math-v4 | 84d42ad0cb960f07f951b9baa9ed2b46a5a18c66 | [卡](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/README.md)、[固定文件元信息](https://huggingface.co/api/datasets/nvidia/Nemotron-SFT-Math-v4/revision/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66?blobs=true) |
| Proofs-v2 | 7665d7f1d006fd89aa852a9dab8060c60b63f814 | [卡](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v2/blob/7665d7f1d006fd89aa852a9dab8060c60b63f814/README.md)、[固定文件元信息](https://huggingface.co/api/datasets/nvidia/Nemotron-Math-Proofs-v2/revision/7665d7f1d006fd89aa852a9dab8060c60b63f814?blobs=true) |
| EcoCoder | 09591b2b7b261aeb37d7db464f2af31eaa24baa0 | [卡](https://huggingface.co/datasets/alrobles/ecocoder-scientific-reasoning/blob/09591b2b7b261aeb37d7db464f2af31eaa24baa0/README.md)、[固定文件元信息](https://huggingface.co/api/datasets/alrobles/ecocoder-scientific-reasoning/revision/09591b2b7b261aeb37d7db464f2af31eaa24baa0?blobs=true) |

HF viewer元信息是核验时的当前版本，不支持在此URL中固定revision。Math-v4完整info的545,431和5,537,896,707B与固定卡/文件相符；EcoCoder完整split与卡相符。

Science与Proofs的dataset-server **size.partial=true**，各大JSONL的viewer约5GB截断，因此viewer Science1,186,516、Proofs23,799行不能当全库规模，也不能据此推翻卡。作者总行数本轮未通过完整扫描复验，后续以固定原文件计数为准，不用estimated_num_rows伪装精确值。[Science schema](https://datasets-server.huggingface.co/info?dataset=nvidia%2FNemotron-SFT-Science-v2)、[Science partial标记](https://datasets-server.huggingface.co/size?dataset=nvidia%2FNemotron-SFT-Science-v2)、[Proofs partial标记](https://datasets-server.huggingface.co/size?dataset=nvidia%2FNemotron-Math-Proofs-v2)、[Math schema](https://datasets-server.huggingface.co/info?dataset=nvidia%2FNemotron-SFT-Math-v4)、[EcoCoder schema](https://datasets-server.huggingface.co/info?dataset=alrobles%2Fecocoder-scientific-reasoning)。

Science固定文件字节：rqa9,534,379,615，so15,941,758,748，syn_mcq569,824,996，vendor26,639,470,663；不必为了使用少量训练token立即下载全部。

## prompt来源、可追溯字段和四项排除边界

### Science-v2

来源分四桶：Synthetic MCQ是合成4–10选项题；RQA是化学合成MCQ/OpenQ；SO是物理/化学/生物StackExchange问答改成MCQ；Vendor是非合成研究生/研究级开放STEM题。卡的行数为96,610/413,519/2,105,985/221,598；它不是2.8M不同任务，也未说全部解答经独立正确性验证。

实际schema共有uuid/messages/tools/license/used_in/metadata。metadata有topic/subtopic/question_format/generation_model；SO另有QuestionLink、QuestionOwnerLink/Name、AnswerOwnerLink/Name，便于按原题/作者归属追溯。RQA/syn_mcq/vendor没有schema可见的原论文/仓库/DOI或原始问题ID字段；uuid提供发布记录索引，不证明源任务独立。一个问题可有不同teacher/工具配置，切train/dev应先按原题族聚合。

发布卡没有给本题固定HLE split或ASI60项目的逐项去污染清单，未披露vendor题来源映射。teacher过滤只解决生成者，不解决测试同源。优先核来源透明、可验证的子集；vendor单独保留风险，不因写“graduate/research-level”就当HLE独立金标准。Python/search的messages来自科学解题，不是mini或Terminus2；ASI direct_llm若输出程序，仍需独立核产物格式、可执行代码、输入依赖与目标环境。卡/schema没有图像字段。

### Math-v4

prompt沿用[Nemotron-Math-v2固定卡](https://huggingface.co/datasets/nvidia/Nemotron-Math-v2/blob/8e793210e175b6406c752a870f585f62de98c0d3/README.md)，后者源于AoPS（经OpenMathReasoning）与MathStackExchange/MathOverflow，过滤proof/MCQ等并建立可核最终答案。v4用V4-Pro High重解，保留与参考答案一致的解答。**这证明参考一致，不证明每个参考是人工真值**；v2流程部分参考由模型多样本多数投票建立。

v4实际14列：uuid/problem/expected_answer/messages/tools/source/license/url/user_url/username/dataset/subset/used_in/metadata。MathSE的原url/归属较完整，AoPS url/user字段为空；metadata全部为空list，不含逐条teacher调用记录。messages保留reasoning_content、tool_calls及tool反馈，tools.parameters为JSON字符串；COT285,516与Python TIR259,915应分开，不把TIR转换成伪终端执行。

原卡泛称公开benchmark去污染，未列本题固定HLE/ASI版本；需要精确/近重复及原题家族排除，不读取gold来定采样策略。与原OpenR1/OpenScience/OpenMathReasoning可能同源，不能因teacher更换把同题当新增独立任务。

### Proofs-v2

只取Nemotron-Math-Proofs-v1的AoPS问题，用V4-Pro Max生成proof24,696、verification28,865、meta-verification29,176，共82,737轨迹/5,752任务。实际schema有uuid/problem/messages/tools/license/source/dataset/subset/used_in/metadata，但无原url/DOI；需按原问题分组，不按不同response类型切。

原始v1有Lean compiler闭环，不代表v2的自然语言proof/verifier/meta-verifier全被Lean或独立真值验证。v2卡未承诺每条证明正确或全部是成功解答；verification输入还可能包含待批判的错误证明，不能当“问题→正确答案”直接混训。schema中的subset值与真实任务类型是否一致也需实查，不能只信列名。卡总5,000,839,123 tokens/82,737，作者口径均值约60K tokens，明显需要长度筛选/回合窗口，不能无脑截8K。

上游[v1固定卡](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v1/blob/97229c590831adfe96202f5cd071d444d535bf91/README.md)声明语义去重与popular benchmark去污染，但同样未给本题HLE/ASI清单；更换teacher不解除排除责任。

### EcoCoder

EcoCoder来源声明PubMed/GBIF/arXiv，实际metadata有paper_title/paper_id/doi/language/quality_score/source/generated_at，能按论文家族与ASI论文/代码来源核重叠。73方法/18类是作者分类，不等于73独立任务环境；质量≥30/100、median85是作者评分，不是执行通过。只有messages、没有输入数据bundle/verifier或逐条环境，所以程序是否真可运行未验收；它更贴ASI direct_llm程序监督，但仍只是小候选。训练默认只用上游train且另核task族，不能把其test答案拉入我们task-dev。



## 许可和覆盖

- Science-v2为CC BY-SA4.0；Math-v4逐条AoPS CC BY4.0、SE CC BY-SA4.0；Proofs-v2为CC BY4.0。保留逐条许可与归属，不将总卡许可当全部prompt上游条件的替代。
- EcoCoder卡为Apache2.0；论文衍生题、原数据和图片的上游权利仍需查。数据集开放不等于teacher weights/license或API使用条件完全相同，本轮不作法律结论。
- 四源均为文本，没有可核图像训练字段/图像bundle。Science覆盖物化生，Math/Proofs覆盖数学，EcoCoder生态科学；它们不能单独补齐HLE图像、人文/法学等领域。
- 学术CoT/TIR可提升科学/编程基础，不自动教授ASI文档读取、文件交付、产物结构或沙箱执行。即使选direct_llm，输出代码是否在官方执行流程中生成合规产物仍需验证。

## 不优先采用的相关线索

- [ianncity/GLM-5.2-Science固定卡](https://huggingface.co/datasets/ianncity/GLM-5.2-Science/blob/e06a292e763631cf8232007cad5b81d6968d4ed0/README.md)：GLM-5.2 High、2026-07发布，686,351,568B JSONL，schema实际50,069行，Apache2.0。只有messages，没有逐条原题ID/来源URL/验证标签/teacher元信息，作者承认和其KimiK2.5 Science共享prompt；未给HLE/ASI排除。teacher虽新，来源证据不足，暂不扩进主推荐。

- [Jackrong/DeepSeek-V4-Pro-Distilled-200K固定卡](https://huggingface.co/datasets/Jackrong/DeepSeek-V4-Pro-Distilled-200K/blob/b3f5c9f69d9ea70fe7f10aef08969f61491490f8/README.md)：是上述NVIDIA三源选择/重包，188,027而非整200K，统一标teacher Max但原Math-v4为High；不是第四个独立数据来源。重包可能丢多轮工具/来源字段，不以美化teacher标签替代原卡方法。
- [OpenSciDER-SFT-8K固定卡](https://huggingface.co/datasets/leonardklin/OpenSciDER-SFT-8K/blob/7ef3ec38cabd3b7316f92b9481ff26d88dccc054/README.md)：Qwen3.6-27B/OpenSciDER加部分闭源模型，来自DataSciBench/DS1000/DSBench/ScienceAgentBench及其他benchmark评测轨迹。不是可直接默认干净的新训练池，需原任务/许可与ASI同源排除；本轮不拿这些benchmark解答直接入训。
- NVIDIA Agentic-v2用DeepSeek-V3.2/GLM4.6模拟普通工具调用、customer service和search；tool环境有模拟成分，不是已验证科学程序执行。不为“轨迹”名称把它当ASI闭环程序池。
- DeepSeek V4 Flash responses线索缺README/许可与成功验证，通用magpie/ultrachat答案不优先；纯ASI/HLE正式评测解题日志、重标注题、benchmark衍生推理全部排除。

## 对当前项目的建议

先把Science-v2与Math-v4列为优先新候选，保持“公开现成主池+小量补齐”的路线；比较其来源可追溯、成功/答案证据、可用token长度和本项目评测隔离，再决定替换哪些旧样本。没有依据预先固定比例或要求全量重跑teacher。

若要最少改动，HLE文本池优先核Math-v4 COT与Science中明确非目标题/可追溯、teacher记录清晰的子集；Python/search子池保留原协议上下文，不能强行改名。Proofs以正确性与超长策略验收后少量引入；EcoCoder先做来源/程序可执行性核验。任何候选都没有在本轮自动加入下载/训练配置或被标为最终可用。
