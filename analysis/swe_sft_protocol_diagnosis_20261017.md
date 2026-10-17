# SWE SFT与mini评测协议只读诊断

2026-10-17。核对保留的实际2000条训练导出、87条val、原生训练args/summary、数据构建和Swift源码；首份数据扫描时间12:28:03 CST。**没有发现已证实的“只学最后一轮”、工具动作未监督、thinking开关反向或工具串化完全不兼容错误。发现了适配不完整和7条预处理损失，但尚不能把0/51归因于其中任何一项。**

本轮仅新增本文和[JSON证据](swe_sft_protocol_diagnosis_20261017.json)，无训练、模型/API、评分、重生、协议修改或自动化重启。

## 已证实的训练事实与排除项

实际教师为**Qwen3.8-Flash-Next，thinking=true、reasoning_effort=xhigh**，2000条均如此；不是早期Qwen3.6-27B池。固定源revision为1db674173119d71df45c22007af99e214600711a。发布者成功bug-fix标签不等于本地已重新执行验证。

原生作业726335确已完成：Dataset加载**1993 train/87 val**，4卡/global8，**249 optimizer steps、1epoch**，r16/alpha32、lr1e-4、cosine/warmup.03。原生args的max_length65536、packing=false、padding_free=false、truncation_strategy=delete、dataloader_drop_last=false；没有为凑长度切窗或截掉对话尾部。加载样本数不是已保存的逐batch曝光计数，当前没有逐batch源ID或精确labels总量。

监督策略是`default+ignore_empty_think`，不是`last_round`。已安装Swift4.7.0.dev0的loss_scale/base.py:114–130将所有assistant RESPONSE/SUFFIX纳入default；保留的真实CPU验收明确：system/user/tool观察不参与loss，assistant可见正文、bash命令及后续assistant均被监督，空think壳不监督。[既有原生label验收](source_snapshots/sft_runtime_cpu_20261016.json)是两个人造样例，不能冒充全部训练batch逐token复核。

数据工具为唯一`bash(command:string)`；所有assistant仍有tool_calls，所有观察均可解析为JSON对象。2000导出有88445次bash调用和86445条tool观察，差额恰为每条最后的提交动作；全部最后一轮均已改成独立`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`，没有补造结束观察。Swift注册qwen3_5 agent模板，保留label中为function/parameter工具标签；服务使用qwen3_coder parser。训练与服务均enable_thinking=false、preserve_thinking=false，未发现此处相反开关。这里只核配置、源码及既有fixture，没有新做全数据逐字节train/service parity。

## 确证缺口一：格式纠错的7条轨迹被整条删除

7条源轨迹在tool观察后插入user角色的格式纠错反馈；Swift将连续query配成response，触发`response_role:user`并删除整条。输入行号223、239、279、1256、1462、1530、1972，故2000→1993；Mixed也丢同7条。它们不是超长、空assistant或token截断。

这是实际角色预处理不兼容，确实损失了这7条包含纠错恢复的样例；其占比仅0.35%，**没有证据证明它解释了大幅降分**。原生warning本身没有行ID；定位是已保存的角色模式与行对齐manifest相匹配，证据边界见[既有加载记录](source_snapshots/sft_actual_loaded_rows_20261016.json)。

## 确证缺口二：首user和路径契约只做了部分适配

构建器仅替换短system、已知Step3提交指导和末次echo+cat命令（[expand_swe_sft_2k.py:82](../scripts/expand_swe_sft_2k.py#L82)）。它保留了之前Step1/2“创建patch.txt、检查patch.txt”的指导，也保留了源/testbed路径与已有工具命令/观察。

|导出统计|train2000|val87|
|---|---:|---:|
|首user含/testbed|2000|87|
|首user含patch.txt及创建patch步骤|2000|87|
|全部bash命令|88445|4107|
|命令含/testbed|82857（93.68%）|3773|
|命令含patch.txt|2849|116|

这些计数针对导出，包含后来删去的7条；因全部2000首user都有该约束，保留的1993条也有。正式mini的instance_template要求分析、复现、修改、验证并独立echo提交，**没有额外patch.txt步骤或/testbed路径约定**。51个staged Dockerfile均无显式WORKDIR；Harbor singularity.py:180–193按实现默认工作目录为**/app**。本轮未证明各SIF里的/testbed是否不存在或是别名，因此不能仅凭路径文字判定命令必然失败。

尤其，root转来的direct独立实际轨迹审阅已给出反证：Ansible d624、Teleport654、OpenLibrary630均在/app，**0条/testbed命令、0条patch.txt命令**；分别有115/168/221个assistant回合、121/175/232个bash动作，其中118/175/228返回rc0，尾部反复cat/grep/ls，没有patch capture失败。**这3例不支持错路径或patch.txt是即时失败原因**；不能外推其他48题，也不能把这个适配风险写成0/51根因。

## 确证差异三：非thinking行为监督与可达历史长度

源manifest记录移除了69610段非空hidden reasoning。导出69611个assistant回合中39443个可见content为空，但**工具调用仍保留并监督**；不能把空content当成空labels。这是依照既定nonthinking协议做的清理，原可见正文并未一并删除。它使监督更偏行动模仿，是否影响计划/停止行为没有受控实证，不能称“删思考导致失败”。

导出使用完整序列≤65536、单助手回复≤8192；实测最大65424/4702，原生按整样本delete策略。134/2000条导出完整序列超过57344，val为10/87。正式[bridge guard](../scripts/swe_baseline_v2.py#L100)则始终检查精确prompt+8192≤65536，不滑窗，因此接纳prompt上限57344。**训练完整历史容许的范围与评测固定预留8K输出的可达前缀存在差异**，不表示这134条在实际Swift中都被截断，也不表示对应正式题必失败；这些是原模板完整序列计数，非每个前缀的原生精确labels。

工具观察XML→JSON转换有原XML roundtrip以及returncode/output/exception/head-tail字段相等检查（[prepare_new_swe_night.py:18](../scripts/prepare_new_swe_night.py#L18)）；没有恢复源已elide的中间文本。源工具动作未在本地重执行，所以不能把发布者成功标签理解为已证实在本评测环境同样可执行。

## 尚未证明的解释

lr1e-4、1993条样本、限定attention/linear-attention/shared-expert的r16更新、源任务分布及较长交互习惯，都可能与退化有关；当前没有对应受控对照来隔离其贡献。**不能直接称高LR、过拟合或教师不够强是根因。** 原生held-out loss从step16的0.3858819降到step249的0.3176805，只说明对同一适配源分布的teacher-forced预测改善，既不证明正式任务能力提升，也不能据此确诊或排除任务分布过专化。

当前能稳妥说的是：训练流程有可核实的非致命适配缺口，未查到一项足以机械解释0/51的mask/工具接口错误；真正的即时失败行为需结合已保存正式轨迹与上下文guard统计。本文不追加实验、不更换checkpoint或主AVG64，不按负面成绩回调训练配方。自动化取消保持。

## 固定来源

- 数据：80/HPC `artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k/{train,val}.messages.jsonl`及行对齐manifest、summary；实际source元数据而非旧报告标题。
- 原生run：HPC `artifacts/runs/swe2k-sft-r16-726335/{training_config.json,training/args.json,summary.json}`，小文件SHA完整保存在本文JSON。
- mask/工具源码：HPC `artifacts/envs/sft/lib/python3.12/site-packages/swift/{loss_scale/base.py,template/base.py,template/templates/qwen.py,agent_template/qwen3_coder.py}`；当前源码与保留CPU输出共同支持解释，不冒充已保存全部训练batch编码。
- 评测模板：`artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml`，SHA7275afa9…3a45；非思考/guard入口为`scripts/swe_baseline_v2.py`。基座revision995ad96e…b0，原HF模板SHAe84f32a2…4259。
