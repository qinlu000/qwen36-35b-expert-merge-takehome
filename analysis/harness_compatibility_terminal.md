# Terminal 轨迹与固定 Terminus-2 的兼容性核验

核验日期：2026-10-16。结论：**已下载 Terminal-Corpus 确有与目标同类的 Terminus-2 JSON 交互；刚介绍的游戏日志和 N 体两个任务也找到了题面完全相同的记录。无需因 harness 名称担心而把整个终端池重新采一遍，但当前不能原样整池训练，也没有证明这些记录是完整且评分通过的解题示范。**

## 范围与可复查证据

- 目标：80 上已安装 Harbor `0.24.0`，源码 commit `f527f8e447038fd242d08ecfa8aaa8029100da97`，Git 工作区无源码修改；安装包导入路径指向这份 checkout。
- 轨迹：`nvidia/Nemotron-Terminal-Corpus@a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9` 的全部 26 个 skill-based Parquet。读取全部 footer、全部 task 列；每分片固定前 10 条，共 260 条记录的消息结构与 parser 行为。该采样不是随机质量估计，不能外推总体正确率。
- 任务包：`nvidia/Nemotron-Terminal-Synthetic-Tasks@7e53648e183cee7bcb0aed623cc91a121d37fa38` 的 mixed 六类压缩包；列目录并仅在内存读取 instruction，用于训练任务的题面匹配，不读取 tests/solution。
- 额外逐题检查：mixed 中两个此前展示的例子；不把这两个额外记录加入 260 条分层统计。
- 没有执行轨迹中的命令、程序或验证器，没有启动终端/容器/GPU/模型或调用 API，没有读取四项正式评测的题面、答案或隐藏测试。报告与 JSON 不含实际训练题面、命令、工具输出、答案或 reasoning 正文。
- 复现脚本：[audit_terminal_harness.py](../scripts/audit_terminal_harness.py)。原始只含聚合计数、字段、哈希和通用 prompt 差异的证据：[terminal_corpus_compatibility_20261016.json](source_snapshots/harness/terminal_corpus_compatibility_20261016.json)。脚本临时部署于 80 的 `/tmp/apex_terminal_harness_audit_20261016.py`，用已有 `/data/caoqinlu/envs/datamind-code/bin/python` 运行。

目标 parser SHA256：`ba7eeaeb28e2f72ecdc5850617c77cc571692c68698306637cc2cfed41130688`；JSON prompt 模板 SHA256：`89a3dc3a15752b748a99fb907c9251ab31a464e13386583fb48476b078b54a34`。

## 目标模型实际看到什么

| 项目 | 固定源码行为 | 已下载记录的证据 |
| --- | --- | --- |
| 初始消息 | `run()` 将通用 JSON 协议、任务说明、当前终端状态拼成第一条 **user** 消息；`Chat` 初始为空。没有固定额外 system 消息。skills/MCP 若配置会增补任务说明。 | 260/260 为 user/assistant 严格交替；无 system/tool 角色；260/260 初始消息含 Task Description、Current terminal state 和 Current Terminal Screen 标记。 |
| 动作 | 普通 assistant 文本解析为 JSON：analysis、plan、commands 为必需，commands 每项为 keystrokes/duration，task_complete 可选。**不是 API native tool_calls。** | 260/260 agent 元数据为 terminus-2；动作结构匹配。不可把 Harbor 事后导出的 `terminal_exec` 工具分析字段误作模型调用时的 tool schema。 |
| 初始模板差异 | 目标要求每条命令以换行结束。 | 260 个初始通用前缀哈希相同；与目标渲染后的通用前缀只有这一行不同：源写“Most bash commands should end with a newline”，目标写“You must end every command with a newline”。所以 **0/260 字节级全模板相同，但仅发现一处通用措辞差异**。没有证据需要为此全量重采。 |
| 终端状态 | 一个持续 `bash --login` tmux session；cd、环境变量、交互程序等状态持续。默认 pane 160×40，history-limit 10,000,000。 | 观察文本的屏幕/增量标记匹配；仅凭记录不能验证源 pane、tmux 版本、history-limit、镜像和所有状态细节。 |
| 观察 | `get_incremental_output()` 返回 New Terminal Output 或 Current Terminal Screen，观察作为下一条 user 文本；不是 returncode/stdout JSON。常规输出超过 10,000 bytes 保留首尾并省略中段。 | 1,798 条后续 user 观察中，1,516 条以 New Terminal Output 开始、9 条以 Current Terminal Screen 开始，67 条有相同截取标记；其余含确认/报错等包装。不能把这些未互斥计数相加当覆盖率。 |
| 等待/超时 | agent 将 duration 限到最多 60 秒，`block=False` 调用 tmux；duration 是发送按键后的最少等待，不是命令完成期限，长程序可以继续运行。错误时有独立 timeout 模板，整任务外层另有 agent wall-time。 | 样本解析到空 keystrokes 的等待动作。不能把 duration、模型请求超时和题定 3 小时总预算混为一谈；未实测长程序/超时。 |
| 完成 | 首次 task_complete=true 后继续执行该批命令，再发确认提示；下一次再 true 才返回。其间 false 清除 pending 状态。 | 128 条观察含相同完成确认语句；剥显式 think 后 112/260 条记录以连续两次完成动作结束。完成标记是 agent 的声明，**不等于 grader 通过**。 |
| JSON 错误 | parser 可提取包裹文字中的 JSON，做有限缺括号/混合文本修复；解析错误作为 user 反馈要求纠正，警告会进入观察。 | 113 条观察有目标同类 parsing-error 标记，32 条有 warnings 标记。错误及恢复是实际历史，不应凭空改写成成功执行。 |
| 上下文压缩 | 默认启用；原生 proactive threshold 为剩余 8,000 tokens，超限可触发三步 summary/questions/answers，再替换模型历史；另有短摘要/无模型 fallback。 | 样本未检出当前源码的 summary/handoff 特征；这不证明源未压缩或与目标压缩规则一致。本项目候选 threshold=86,016 是另行实验设置，不能当源数据默认值。 |

源码位置：[Terminus2 主循环](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py) 的 `run`、`_handle_llm_interaction`、`_execute_commands`、`_run_agent_loop`、`_summarize`；[tmux 状态](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/tmux_session.py)；[Chat 历史](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/llms/chat.py)。这是已下载固定源码核验，不是仅依赖 agent 名称。

## Thinking 与动作 JSON 必须分开

260/260 样本元数据 `enable_thinking=True`；2,058 条 assistant 消息中 2,053 条含显式 think 结束标签。源的 assistant.content 把独立 reasoning wrapper 和动作 JSON 放在一起，而目标 parser 实际解析 `LLMResponse.content`，额外 `reasoning_content` 是独立字段；是否把后者带回后续上下文由 `interleaved_thinking` 控制，默认 false。

| 解析输入 | 目标 parser 接受 | 报错 | 有警告 |
| --- | ---: | ---: | ---: |
| 原始整个 assistant.content | 1,849 | 209 | 2,053 |
| 仅显式 `</think>` 之后的动作部分 | 1,930 | 128 | 143 |

剩余 128 个错误中，127 个为未找到有效 JSON，1 个为坏 JSON。这个检查只判断给定文本是否可由固定 parser 接受；**不是轨迹执行率、任务成功率或无损语义兼容率**。也未判断 127 个无 JSON 消息属于纯推理、截段、异常终止还是其他情况。

若采用 non-thinking SFT，需按固定模型模板处理独立 reasoning wrapper，并保留 JSON 内的 analysis/plan：后两者是任务协议规定的可见动作字段，**关闭模型思考不代表删除它们**。不能只设置 enable_thinking=false 就假定训练文本里的旧 reasoning 已被自动移除；[自造Qwen模板检查](harness_compatibility.md#qwen非思考模板的确定性问题)已确认两个false开关仍保留最近user之后的已有reasoning。含无 JSON/异常截断的 assistant 不应未经规则整池监督，已存在的报错与修正历史也不能伪造工具输出来“修好”。

## 任务包与 Corpus 的实际配对

全量 task 列统计：139,841 行、82,955 个不同 task 字符串。六包含 5,984 个 task ID；这些 ID 在 Corpus 某处均出现，合计命中 18,778 行，其中 easy 5,959、medium 7,130、mixed 5,689。

**ID 不能脱离 difficulty 使用。** 260 条样本中，84 条 ID 在本次 mixed 任务包出现，但只有 60 条题面匹配；这 60 条正是 mixed 六分片的全部 60 条样本。其余 24 条来自 easy/medium 且同 ID 的题面不匹配。故不能把 easy/medium 的同 ID 自动视为 mixed 同题，也不能根据 ID 命中数称 5,984 个题目都已有对应目标任务的完整成功轨迹。

本轮对两个具体示例读取 mixed 对应分片；行号为 **0-based**。剥固定 Task Description / Current terminal state wrapper 并 trim 后比较 instruction，没有打印正文：

| 示例 | 对应 Corpus 文件/行 | instruction 匹配 | 可解析动作 | 完成标记 |
| --- | --- | --- | --- | --- |
| 游戏事件日志 `data_processing_task_0459` | mixed/data_processing/data_filtered.parquet，第 738 行 | 字节完全相同；两侧 SHA256 `eed82b9e11bc86bc95256590dc6dd22a1f2b68220e10cc169c4901957a36f62e` | 去显式 think 后 4/4 | 未发现 true |
| N 体仿真 `scientific_computing_task_0939` | mixed/scientific_computing/data_filtered.parquet，第 184 行 | 字节完全相同；两侧 SHA256 `9b90813a02d1f461f340704492c7baf8fb8e1ac4a7d5c0fee157ae982d334df3` | 去显式 think 后 6/6 | 未发现 true |

这两道题**有对应现成过程记录**，推翻了“完全没找到同题轨迹”的不确定状态；但两条记录没有完成标记、没有逐行 grader result，尚不能认定为完整成功解。需要检查源 episode/run 组织和终局记录，再决定用为过程监督或改选完整轨迹。题面匹配也不证明环境镜像、输入文件和判分器版本相同。

后续 dev 必须跨任务包与 Corpus 联合分组：至少包含 source revision/config/difficulty/domain、规范 task ID、题面 hash/近重复和模板族；dev 同题的所有教师、episode 和重写轨迹共同排除。来源映射无法可靠完成的部分不能宣称已严格隔离。

## 原生 parser 的独立合成验证

9 个 fixture 全部由本次人工构造，与训练/评测内容无关，只调用已安装的 `harbor.agents.terminus_2.terminus_json_plain_parser.TerminusJSONPlainParser`，没有启动 session。安装环境结果与无修改源码导入结果一致。

| 独立合成输入 | 实际结果 |
| --- | --- |
| 合法动作 JSON | 无错误、无警告，解析 1 条动作 |
| 坏 JSON | 报错，不解析动作 |
| 缺 analysis/plan | 报错，不解析动作 |
| 合法完成 JSON、空 commands | 无错误，完成 true |
| JSON 前后附普通文字 | 接受并警告 |
| duration 缺失 | 接受并警告，补默认 1 秒 |
| duration=-1 | parser 接受，无警告；这不是执行安全性证明 |
| duration=120 | parser 接受 120；主循环随后才截为 60 |
| 完成 true 但 command 对象缺 keystrokes | parser 降为警告、返回完成 true 且空动作；不能以 parser 接受代替严格数据完整性规则 |

结果记录在同一 JSON 的 `synthetic_parser_fixtures`；另一次通过已安装 Harbor 0.24.0 环境调用原生 import 验证 9/9 与该记录相同，独立回执见 [terminal_installed_parser_fixtures_20261016.json](source_snapshots/harness/terminal_installed_parser_fixtures_20261016.json)，使用脚本的 `--fixtures-only` 可复现。测试 parser 不等于测试目标终端执行、完成双确认状态机或容器行为。

## 取舍建议

1. **可机械适配、优先复用的终端训练候选**：保留源 user 观察与 assistant 动作顺序；独立处理 reasoning wrapper，保留动作 JSON 的 analysis/plan/commands/task_complete；检验 parser、完成/截段状态与依赖上下文后再切窗口。Terminus-2 同类协议与两例题面对齐已有直接证据，不需全池重跑才可开展 SFT 准备。
2. **不能原样整池直接训练**：本轮已发现独立 thinking、部分非 JSON 响应、记录终局不明及 difficulty ID 碰撞。源没有逐行成功标签，260 样本的结构结果不提供成功筛选器；完整训练资格、许可/正式集去污染、全量长度与窗口规则仍未完成。
3. **只能作跨协议辅助的部分**：这些科学计算/数据科学终端轨迹可用于执行专家的终端子桶，但不能因此称为当前 ASI OpenCode 原生工具轨迹；持续 tmux 不能仅改字段名伪装为 OpenCode 的 bash/read/write 工具及观察。
4. **确需自己跑的部分**：独立 dev 环境与评分验证、少量可追溯任务的执行复验、确认缺失的目标协议/科研行为示范，以及只提供任务包而找不到可靠过程的新增题。不需要为每条现成轨迹全量重复教师生成。对只有部分过程的两个例子，可改选有可靠完整过程的其他题，或在缺口明确后补采，不能先承诺两题是成功训练样本。

未解决且不以猜测补齐：源 agent 精确 commit/所有运行参数、环境 digest 和文件状态、源压缩/截断规则、逐行 grader 结果、跨来源/正式评测同源排除，以及真实 Qwen 端点和容器回放。下一步应先完成小池的规则化整理与独立环境复验，而非大规模重采。
