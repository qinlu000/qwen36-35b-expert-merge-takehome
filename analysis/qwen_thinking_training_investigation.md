# Qwen3.6 thinking在ms-swift训练中的实际处理

核验：2026-10-16，北京时间。仅阅读固定官方源码/文档；没有安装、训练、推理、付费API或GPU操作。本报告针对候选ms-swift commit `a01a3ae004e0b1071814a3d357666184211ed178`，不把候选源码等同当前实际训练栈已验收。

## 核心结论

1. 对本模型，`<think>`/`</think>`是消息序列中明确的格式/控制边界。它们不是另一套被单独开启的神经网络。推理模板用前缀选择继续生成思考正文，或预填一个空思考块后开始答案；这与在训练文件中删除或保留teacher思考是不同决定。
2. **把`--enable_thinking false`传给SFT，不会自动删除已有teacher思考正文，也不自动把这些token的loss置零。** 训练时的监督目标主要来自已有assistant content、history保留策略与loss mask。
3. 固定标准messages数据加载路径没有自动把`reasoning_content`合成到`content`；通用校验会丢弃该额外字段。HF原模型Jinja能读该字段，不代表ms-swift标准SFT loader同样保留。项目ETL需显式决定保留/删除/分段，不能依赖字段名称自动生效。
4. 混合思考模型经正常CLI参数路径时，默认会自动加`ignore_empty_think`：**空think块仍在input_ids里，但通常不计loss**。非空思考正文不因此被忽略。直接调用`get_template()`不必经CLI这一步，须显式查看真实loss_scale。
5. “删除思考正文”和“保留正文作条件但mask掉它的loss”是不同训练问题。后者答案预测仍看到了teacher思考，若部署关闭思考而不再提供这段条件，会出现条件差异；它也不会省去这部分前向/上下文长度。

## 为什么本项目使用Qwen3.5模板

固定模型注册把`Qwen/Qwen3.6-35B-A3B`和FP8变体映射到`TemplateType.qwen3_5`，不是通用qwen3模板。[注册L1642–1661](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/model/models/qwen.py#L1642)

`qwen3_5`注册为混合思考：`is_thinking=True`、thinking prefix是`<think>\n`，non-thinking prefix是`<think>\n\n</think>\n\n`。[模板注册L709–717](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/templates/qwen.py#L709)

`Qwen3_5Template._swift_prepare_inputs()`会对assistant已有think块规范化空白/换行，以及trim其他角色；它读取的是`message['content']`，没有在此将`reasoning_content`拼进去。[Qwen3.5类L617–653](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/templates/qwen.py#L617)

本报告不以Qwen3.8自己的`_jinja_encode`特例推断3.6训练行为。

## reasoning_content：标准SFT加载链与HF推理模板不同

标准自定义messages数据的证据链为：

- `DatasetMeta.preprocess_func`默认是`AutoPreprocessor()`；local文件loader调用选定preprocess_func。[默认元数据L182–186](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/dataset_meta.py#L182)、[文件loader L46–69](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/loader.py#L46)
- AutoPreprocessor遇到messages列选择MessagesPreprocessor；后者规范provider消息/role/content，没有通用reasoning转think步骤。[自动分派L739–764](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L739)、[messages预处理L692–716](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L692)
- RowPreprocessor.__call__执行dataset.map(batched_preprocess)；batched_preprocess先preprocess，再对结果调用`_check_messages`。[map L346–400](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L346)、[必经校验L220–242](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L220)
- `_check_messages`只保留role/content/loss/loss_scale（tool额外保留name），删除reasoning_content等其他消息字段。[字段白名单L83–102](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/dataset/preprocessor/core.py#L83)
- 若assistant同时有native tool_calls，`normalize_openai_tool_calls`也会将正文和tool calls转成canonical消息，正文只复制这几个字段；没有把独立reasoning拼成think。[标准化L14–61](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/template_inputs.py#L14)

边界：已注册的专用预处理器/用户插件可以在校验前自行把reasoning写入content，本轮未穷尽所有来源专用适配器。因此结论限定为本项目拟用的通用messages导入；不声称所有Swift输入方式都不支持reasoning，更不据字段消失推断模型没有内部推理能力。

直接`Template.encode(dict)`不一定经过dataset校验；但qwen3_5的swift encoder主要拼接content，未核到自动使用reasoning_content。Jinja分支会把消息交给tokenizer.apply_chat_template，属于不同接口。[Jinja分支L1264–1286](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1264) 官方明确Jinja backend只支持推理、不能用于确定训练loss范围。[固定CLI文档L136–143](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/docs/source/Instruction/Command-line-parameters.md#L136)

因此root已做的HF tokenizer验证（field/inline渲染等价、双写重复、清掉正文仍有空think）可以证明模型Jinja的序列化行为，不能代替真实Swift训练loader与label验收。

## enable_thinking / preserve_thinking / add_non_thinking_prefix

| 设置 | 固定源码实际作用 | 不能据此声称 |
| --- | --- | --- |
| enable_thinking | `_get_response_prefix()`在待生成assistant末尾选thinking/non-thinking prefix；有已知response的训练回合直接用response | false会自动删除已有非空teacher思考；或让思考token loss=0 |
| preserve_thinking=True | 保留所有轮次已序列化思考 | 所有保留内容必然监督，仍取决loss_scale |
| preserve_thinking=False | 删除最后一个user之前assistant的思考部分，只保留末轮思考 | 清除了全部思考；末轮teacher思考仍在 |
| add_non_thinking_prefix=True | 对不以think开头的assistant正文补空think块；训练默认针对所有监督回合，last_round时主要末轮 | 插入空标记就会生成长思考正文 |

源码：前缀选择[base L167–204](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L167)，训练已有response与推理待生成分支[base L1444–1496](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1444)，补空块与移除历史[base L1300–1410](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1300)。

实际默认：qwen3_5有non_thinking_prefix，Template.__init__在enable_thinking=None时解析为False；不过训练默认loss_scale非last_round时，preserve_thinking可解析为True。两者并不矛盾：推理默认前缀和训练数据历史保留是两件事。[base L132–139](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L132)、[历史默认L173–190](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L173)。同commit参数类英文注释一处仍称hybrid默认True，故以执行代码和固定CLI中文说明为准，不能只摘旧注释。

## loss mask：标记存在不等于参与监督

- default基础策略计算assistant response/suffix，默认不监督system/user/tool response；last_round只算最后user之后的assistant，all才将其他部分纳入。[LossScale L114–130](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/loss_scale/base.py#L114)
- 权重>0的片段复制token为labels；权重0的片段labels=-100，但input_ids中token仍保留。推理则清掉labels/loss_scale字段。[编码L1214–1239](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1214)、[训练/推理输出L1642–1656](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1642)
- 正常SFT CLI中`disable_ignore_empty_think=False`，已解析为hybrid的template会自动追加`+ignore_empty_think`。[参数解析L150–178](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/arguments/base_args/template_args.py#L150)
- ignore_empty_think匹配开头空`<think>\s*</think>\s*`等片段，loss=0；不会mask非空thinking正文。[精确配置](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/loss_scale/config/ignore_empty_think.json)
- ignore_think_prefix只mask开头`<think>`（可含一个换行），正文与`</think>`仍监督。名称不能理解为忽略整个思考。[精确配置](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/loss_scale/config/ignore_think_prefix.json)、[CLI解释L124–133](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/docs/source/Instruction/Command-line-parameters.md#L124)

本轮核到的loss_scale注册表没有`skip_think`策略，不把它当现成可用CLI参数。[固定映射表](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/loss_scale/mapping.py#L7)

如果某处方案写“skip_think=True”，必须回到其所属库和版本核语义；本项目不能凭这个名字声称已实现“保留thinking条件但不监督”。官方支持相邻assistant片段分别设置loss=False/True，随后swift会合并content/loss列表；这可以表达需要的遮罩思想，但仍需对多轮工具序列真实验收。[数据格式示例L85–110](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/docs/source/Customization/Custom-dataset.md#L85)、[相邻assistant合并L1389–1396](https://github.com/modelscope/ms-swift/blob/a01a3ae004e0b1071814a3d357666184211ed178/swift/template/base.py#L1389)。

## 三种数据处理方案不能混称关闭thinking

| 方案 | 训练input中teacher思考 | thinking正文loss | 结果与限制 |
| --- | --- | --- | --- |
| 保留并监督 | 保留，通常序列化为think块 | 通常>0 | 直接模仿教师显式思考；部署关thinking会改变生成路径，收益需测 |
| 保留但mask | 保留 | 0；答案/动作仍>0 | 答案仍以teacher思考为条件；保留上下文/前向成本，不等同无思考蒸馏 |
| 删除正文 | 不保留；按正式非思考模板可有空think块 | 正文不存在 | 学习任务/历史工具观察→答案或动作；节约序列长度，但删除关键计划/摘要是否伤害轨迹可理解性需检查 |

删除时只处理可靠边界内的独立reasoning或think正文；不能把Terminus JSON的analysis/plan字段、普通assistant解释、命令、文件写入、tool结果一并当“思考”删掉。协议必需的可见analysis/plan和模型专用reasoning字段不是同一概念。保留/删除策略需三专家与混训一致记录，不根据正式test挑规则。

## 仍需验收的最小证据

在最终训练栈中仅用合成无敏感样例检查，不依赖正式题或跑GPU：

1. 对同一个小样例分别构造inline think、reasoning_content、无思考、空think、native tool_calls及多轮历史，检查dataset loader前后字段；确保ETL处理没有双写、漏写或silent drop。
2. 保存实际模板、enable/preserve/add_non_thinking_prefix、最终loss_scale和disable_ignore_empty_think值；对照CLI和直接get_template路径，不能只看HF apply_chat_template字符串。
3. 同时decode input_ids与labels（-100显示占位），统计思考/答案/命令/工具观察各部分的监督token。验证空块是否mask、非空思考是否保留或删除、用户/tool观察是否mask。
4. 验证三专家、混训、adapter重载与合版服务使用同一已定thinking协议。若选择非思考评测，不因训练仍含teacher正文就声称已证明无退化。

以上是待验收清单，没有在本轮执行。模型tokenizer、训练预处理器、loss策略和部署解析器各有作用，单个标签检查不能代替全链一致性。
