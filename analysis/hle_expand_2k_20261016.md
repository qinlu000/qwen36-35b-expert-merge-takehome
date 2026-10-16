# HLE 强教师 2k 扩量（2026-10-16）

状态：数据准备完成，16并发High滚动生成中；交接时最新实读**153/1183 accepted**，21条gold不匹配拒收，另有4个切换时在途用量未知请求。带历史与未知费用上界累计保守**¥17.86745232**。生成PID2603822与后续PID2611502均alive，后续phase为`waiting_for_high_generation`。尚未宣称2k可训文件完成。本分支不提交新GPU作业或Git，不更改历史500/100导出；数据全部确认后仅释放已获授权的held HLE作业726344。

新目录：`artifacts/data/candidates/night_hle_20261016/expanded_2k/`。80项目根为`/data/caoqinlu/projects/apex-takehome`；最终文件完成后同步Mac与HPC。

| 类别 | 2k目标 | 教师来源 |
|---|---:|---|
| Math | 817 | Math-v4现成DeepSeek-V4-Pro High；保留原204，新增613 |
| Biology/Medicine | 224 | 新API DeepSeek-V4-Pro High，独立生成后对比公开gold |
| Computer Science/AI | 193 | 同上 |
| Other | 186 | 同上 |
| Physics | 184 | 同上 |
| Humanities/Social Science | 175 | 同上 |
| Chemistry | 132 | 同上 |
| Engineering | 89 | 同上 |
| 总计 | 2000 | Math817 + 新High金标解答1183 |

七类有gold的独立训练题池分别足够，最小池是Computer Science/AI369题；Other430题，其余均超过800题。MMLU-Pro原生为评测题，本项目沿用此前已冻结的题干分族train分区，不冒称上游发布了train。原296个非思考模式题均找到，优先重新用High解答；不复用旧答案正文。若High选项与gold不符，保留拒收记录并用同类别独立题替补。原500历史文件保持，新的主训全部使用High教师。

数学候选保留原生无工具COT，移除独立reasoning字段及开头think段；完整保留可见答案。新数学扫描遇到1个与正式公开题面或固定val的13-gram重合项，未纳入。所有新增题仅读取正式HLE的`question`用于排除，不读正式HLE/ASI答案。Science-v2此前135条无独立gold样本继续hold。

已准备的817条数学完整序列合计562,304 token、最长1940，assistant正文最长1883。这是自然统计结果，没有2K筛选；全2k最终最长仍待教师生成完成后计算。

教师显式使用`thinking.type=enabled`、`reasoning_effort=high`，单次`max_tokens=65536`容纳隐藏推理加最终可见JSON。训练仅取最终`solution/answer`，消息仅`role/content`；学生训练/评测仍用非思考模式。最终可见答案按8K、完整序列按64K检查，超限拒收而不截断；不沿用旧2K长度筛选。新训练窗口在完成后按完整最长序列确定。[官方High参数](https://api-docs.deepseek.com/guides/thinking_mode/)、[官方completion输出上限及usage字段](https://api-docs.deepseek.com/api/create-chat-completion/)

费用保守采用峰值输入$1.32/M、输出$3.96/M，并以8 CNY/USD作为内部预算安全系数；所有completion token（包含reasoning）计入费用。发起前对在途请求合计预留最大输出成本，无usage失败按全额预留计账。历史学术分支carry为¥2.62661616。本轮只读账户余额¥212.40，分支内部护栏¥80。[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)

首批仅4条真实待训练题，4并发；**4/4 gold匹配、finish_reason=stop**。输入1247、全部输出2162 token，其中reasoning1731；新增保守费用**¥0.08166048**，带历史账累计¥2.70827664。总墙钟18.24秒，逐题2.9–18.2秒。合格输出直接续用，没有额外synthetic探针或重复校准。

因4并发实际延迟变长，根任务授权直接切至16并发。旧PID2570638已停止，54次落盘调用/53条accepted全部保留；至多4个未返回请求身份和usage未知，逐条写入同一账本，按全题池最大输入加完整64K输出保守预留合计**¥8.55482496**，没有按0计费。未返回题后续可能重试及重复计费；不冒称调用从未发生或输出已验收。

当前80生成PID为**2603822**，日志`expanded_2k/high_generation_16.log`，总尝试上限2200、16并发、High目标1183条。80护栏包含所有在途最大reserve及上述未知费用；后续可写`expanded_2k/STOP_ADMISSION`停止新增请求并自然排空在途。完整实际用量待最终账本更新。

## 已常驻的一次性后续

根任务进一步授权：生成完成后构建Mixed并释放**仅726344**，不操作其它作业。已在80以nohup启动[后续脚本](../scripts/finish_hle_2k_and_mixed.py)，PID **2611502**；状态`expanded_2k/followup_state.json`，日志`expanded_2k/followup.log`，当前phase为`waiting_for_high_generation`。不依赖Mac或人工守日志。

固定顺序：等16路生成自然退出 → 必须High且1183条配额齐全 → 导出HLE **2000 train / 100原val** → HLE/SWE/Terminal/ASI各一次构建Mixed **7073 train / 249 val** → rsync HLE及Mixed两目录到HPC → 远端行数、summary、原100val三个文件逐字节确认 → 仅`scontrol release 726344`。任何步骤失败会写`phase=failed`并保留held，不释放半成品。预提交HLE作业已明确64K窗口、world2/global8/r16/1epoch，不使用旧2048长度设置。

最终HLE路径为`artifacts/data/candidates/night_hle_20261016/expanded_2k/train.messages.jsonl`，val同目录；Mixed为`artifacts/data/candidates/mixed_expanded_20261016/`。最终是否ready与是否已release以状态文件和最终summary为准，本阶段不把后台运行说成已完成。

实现：[准备及导出脚本](../scripts/expand_hle_sft_2k.py)、[High教师及共享账本脚本](../scripts/generate_hle_2k_high.py)。没有新搭任务环境或运行生成代码。
