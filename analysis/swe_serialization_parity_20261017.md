# 真实SWE样本的训练／推理序列化对照

2026-10-17。**原训练配置的完整序列parity为RED，差异严格为7个空think壳；按相同token对齐后，工具正文、观察和全部940个监督token为GREEN。没有发现上一轮动作被错当下一轮目标、只监督尾轮或工具观察参与loss。** 这是实际编码结果，不是旧的人造mask fixture；不能据此断言已找到SWE 0/51的根因。

仅做CPU tokenizer／template／labels诊断，无权重加载、forward、模型/API调用、训练、评分或任务执行；没有改训练数据、原训练配置、服务和正式协议。自动化取消保持。

## 样本和固定环境

取真实`train.messages.jsonl`第681行，`katex__katex-2459`，trajectory `1825108d-a10a-488e-98f8-0424a249e991`；原行21331字节，SHA256 `b57a903b794dcf9a97a8fa7ce0858cfd88925bf1c57da05fc7dd3f09ab8ba2bd`。20条message、8轮assistant、11次bash调用、10条tool观察，其中3轮多调用。来源manifest的`multi_call_source_order_unverified`仍是边界：本检查证明训练与HF保留同一输入顺序，不证明原教师执行顺序已独立复核。

使用HPC冻结`sft`环境：Swift4.7.0.dev0、Transformers5.15.1、Torch2.11.0+cu130、Tokenizers0.22.2，基座revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。调用原生`get_processor(..., model_type=qwen3_5_moe, download_model=False)`及`get_template(...).encode(real_row)`；`get_processor`固定走`load_model=False`（installed `swift/model/register.py:675–688`）。实际仅CPU127／1线程、CUDA未初始化。

Swift参数与原配方一致：qwen3_5／agent qwen3_5、max_length65536、非packing、`enable_thinking=False`、`preserve_thinking=False`、`add_non_thinking_prefix=True`、`default+ignore_empty_think`、整样本delete。HF参考始终为原基座`chat_template.jinja`，`enable_thinking=False,preserve_thinking=False`；使用原tokenizer的`apply_chat_template`。调用已安装vLLM `chat_utils.py:1583–1606`的纯JSON-arguments正常化函数，证实wire字符串参数还原后与真实row一致；没有启动或请求vLLM。故这是实际服务所用HF渲染后端的离线对照，不是抓取live endpoint输出。

## RED的精确含义

原生Swift为**5931 token／19676字符**；HF为**5959 token／19809字符**。首个不同token在1461，首个不同字符在6441。唯一token编辑是HF比Swift多7组`[248068,271,248069,271]`，即`<think>\n\n</think>\n\n`；133字符／28 token恰对应这7个壳。Swift只保留最后一轮的1个壳，HF保留全部8个。去掉HF前7个壳，文本及token均逐项一致：没有工具XML改写、参数损坏、历史观察遗漏、重复或EOS差异。

raw `report.json`中按HF坐标直接切Swift labels的逐轮检查为false，完整mask检查为null；因序列长度不同，它们**不能解释为mask错误**。独立`alignment.json`只用exact equal-token runs把HF目标区间映射回Swift坐标：每个Swift token均有唯一对应；删除的28个HF token全部本应masked。映射后全5931个位置的labels完全相同，8轮111/58/166/136/219/86/80/84个目标token全部监督，总940；system/user/tool、空think均不监督，assistant动作及EOS监督。`labels!=-100`处均严格等于同位置input_ids；没有预先错移一位。模型内部causal-loss shift没有执行forward，本检查不声称已单独测试其数值实现。

每轮HF `add_generation_prompt=True`的实际前缀，与**这次整条Swift训练编码在该动作前的前缀**比较如下；没有另做8次Swift子前缀编码：

|assistant message index|HF前缀token|Swift训练前缀token|HF多出的空壳|目标token／labels匹配|
|---:|---:|---:|---:|---:|
|2|1465|1461|1|111／是|
|5|2026|2018|2|58／是|
|7|3127|3115|3|166／是|
|10|4109|4093|4|136／是|
|12|4395|4375|5|219／是|
|15|5235|5211|6|86／是|
|17|5518|5490|7|80／是|
|19|5875|5847|7|84／是|

前7轮的差异既含历史空壳，也含当轮动作之前的空壳；最后一轮当轮壳存在，但历史7壳仍缺失。每轮HF前缀及through-assistant序列都与HF完整序列精确接合。移除真实观察、把期望labels错移一位、把观察token错误纳入loss的负控均被拒绝。

## 为什么两个后端不同

固定installed源码解释与实测完全吻合：

- `swift/template/base.py:1308–1332`：训练default策略给所有assistant补非thinking前缀；`1403–1410`随后在`preserve_thinking=False`时调用`_remove_history_thinking`。
- `base.py:1338–1350`以`get_last_user_round`划分历史；`swift/template/utils.py:181–185`默认`include_tool=True`，最后tool观察也算query，所以此前assistant空壳都被删除。
- 原HF `chat_template.jinja:67–75`寻找最后真实user，排除`<tool_response>`伪user；`:100–103`保留该user之后整个工具链assistant的think壳，`:147–153`给当前generation prompt也补空壳。`preserve_thinking=False`没有使同一真实user内的旧工具回合变成无壳。
- installed `swift/template/templates/qwen.py:627–653,709–717`做trim及qwen3_5 agent格式化；实测表明这些正文／工具处理在本样本没有额外差异。

源码SHA、原生报告SHA、真实逐轮目标区间及独立对齐结果见[小型JSON证据](swe_serialization_parity_20261017.json)。这里的来源均为固定安装和保留基座文件，不将在线最新版当成本次训练实现。

## 单参数反事实与边界

**同一真实样本的单参数CPU反事实已GREEN。** 只改Swift的`preserve_thinking=True`，HF参考仍False，`enable_thinking=False`和`ignore_empty_think`保持。原RED和候选使用相同源行SHA。候选Swift与原HF均为5959 token／19809字符，全文SHA同为`74dbd9d5214954a6a358f0ba13d8bb8f8c229d8106c9066e67bc8ea759f5ae53`；全部8轮generation prefix及through-assistant前缀一致，5959个位置的完整labels mask一致，仍仅940个监督token，三个负控仍全部检出。候选77.71s自然完成，CUDA未初始化。这里保留的是渲染空壳，没有启用思考模式。

前置的[全量输入审计](swe_training_repetition_audit_20261017.md)在13:02确认：train2000／160065 messages和val87／7400 messages只含role/content/tool_calls/tool_call_id；隐藏reasoning等字段、所有content中的think标签／空壳／非空块／孤立tag均为0。这批冻结导出没有会被`preserve_thinking=True`复活的隐藏思考。该结论不可无检查外推到其他数据集。

因此未来训练侧最小改动候选是保持`enable_thinking=False`、`add_non_thinking_prefix=True`和空壳mask，只把`preserve_thinking`设为True，避免Swift删除同一工具链的历史空壳。**这次只在独立诊断实例改参数，原训练、数据、服务和正式配置均未改。** 可以称“修复这条样本的序列化差异”；没有证明它会改善SWE成功率，也没有据此重训、改checkpoint或改正式分。不能无全量输入清理检查把该参数迁到其他数据。

## 复现与原件

脚本：[check_swe_serialization_parity.py](../scripts/check_swe_serialization_parity.py)。纯stdlib重放对齐（不导入Swift/Torch）：

```bash
python3 scripts/check_swe_serialization_parity.py --audit-saved artifacts/preflight/swe-serialization-parity-20261017/real681-native-instrumented
```

原生CPU命令使用冻结`artifacts/envs/sft/bin/python`，`--project`指定项目根、`--line 681 --output <全新目录>`；候选额外加`--swift-preserve-thinking`。两次均由外层`timeout 120s`约束、CUDA_VISIBLE_DEVICES为空、offline及OMP／BLAS线程1；默认原配置仍为False。原RED执行source SHA为`212a61b61c5922012853bc7f3893d2b61b042ab31e6bd5b0e17e96cebf9e82ae`，后来仅增加已保存结果对齐及显式候选参数；候选／最终脚本SHA为`faa534513f8896bc530ccf2bb832b204d473079d43aa81094e52ea2d75fe0830`。

HPC项目根及本地ignored目录`artifacts/preflight/swe-serialization-parity-20261017/`保留真实源行、两份文本、input_ids、labels、原始report和启动栈；RED子目录为`real681-native-instrumented`，GREEN为`real681-preserve-empty-think-candidate`。没有复制模型权重。原RED成功运行84.66s，其中Swift／Transformers import81.81s、processor ready82.87s、encode ready84.29s。30/60s faulthandler栈均在源码导入／读取，没有权重forward。初次120s超时无结果；一次普通rsync经代理失败导致旧版本bootstrap，已停止且确认专属进程清空后才原子写入独立instrumented路径；这次成功原生运行和后续候选均不把初始化超时冒充parity通过。两次真实编码均自然退出rc0，无持续诊断进程。
