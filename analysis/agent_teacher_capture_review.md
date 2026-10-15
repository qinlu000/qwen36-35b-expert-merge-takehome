# Codex 子代理教师轨迹采集：试点边界

2026-10-15。先检查项目既有数据结构说明和当前工具接口，随后在授权隔离目录完成一个真实仓库修复试点。solver 未查找正式评测题、答案、修复 PR 或参考补丁；发现侧的答案接触边界见末尾说明。未运行本地教师模型或付费 API。

结论：子代理可以独立求解真实任务，留下可验证的命令、修改和测试结果，适合小规模补充。当前工具没有已经核实的“一键导出完整 Codex 原始训练轨迹”接口；不能只保存最终答案，再回填虚构的中间过程。没有额外 DeepSeek 教师调用费，不等于没有 Codex 额度、执行与审核成本。

## 能采集什么

- 在任务执行前，保存子代理实际看到的任务说明、可见文件/测试范围、公开指令及工具契约；不加入隐藏验证器或 gold patch。
- 显式记录每次公开 assistant 动作及其对应工具参数。当前 `exec_command` 返回合并的 `output`、`exit_code`、耗时，长命令另有 `session_id`；它本身不保证独立 stdout/stderr，也可能截断。
- 后续试点应在自身隔离目录分别落盘 stdout、stderr 与退出码，再向子代理反馈真实结果，避免依赖 UI 中可能截断的文字。交互式会话还需完整记录每次输入、输出增量、顺序与终止状态。
- 保存 agent 提交时的实际 patch/产物及已执行的可见测试。独立验证在新环境重放，结果与教师行为分开记录；`task_complete` 或最终文字不能当成功标签。
- 不把不可见的内部推理补写成 CoT。可以使用当时公开的简短计划、工具动作及最终答复；模型精确版本、token、logprob 等接口未提供的字段标记 unavailable。

## 最小任务 manifest

`task_id`、`task_family_id`、`split`、来源 URL、抓取时间、原仓库许可、仓库 URL、完整 base commit、任务说明原文及 hash、可见测试清单、环境/依赖版本、允许网络/工具范围、初始工作树 hash、教师标识（仅记录可核信息）、采集工具及协议版本。

发现任务、求解任务与独立验证分别管理。solver 只接收无答案的任务包；同源 issue、PR、变体、多个 rollout 按任务族整组分 train/val，且在生成轨迹前固定 split。

## 每步原始账本

每个 step 保存一行索引，命令与输出另存原文件：

| 字段 | 含义 |
|---|---|
| run_id / step_id / parent_call_id | 任务运行和严格交互顺序 |
| event_type | assistant_visible、tool_call、tool_result、final 等 |
| timestamp_start / timestamp_end | 实际时间；另存 elapsed_seconds |
| assistant_visible_path | 当时公开输出的原文，不能事后改写成当时推理 |
| tool_name / arguments_path | 实际工具和完整参数，命令保留原始字节 |
| cwd / shell / session_id | 工作目录、shell 与会话状态；是否新 subshell |
| stdout_path / stderr_path / exit_code | 原始文件与实际退出码；超时、信号单独记录 |
| observation_path / observation_sha256 | 实际反馈给模型的观察，包括截断规则与被截断标记 |
| worktree_before / worktree_after | 代码状态引用；避免每步复制全仓库 |
| artifact_paths / artifact_sha256 | patch、生成文件和测试日志引用 |

通用目录建议：`artifacts/agent_teacher_pilot/<task_id>/<run_id>/`，其中 `manifest.json`、`events.jsonl`、`steps/0001/`、`submission.patch`、`verification/` 分开保存。下述试点已实现最小命令账本；完整 Codex 消息导出和目标 harness 自动适配尚未实现。

## 转为 SFT 的限制

| 目标 | 可复用部分 | 必须核实的差异 |
|---|---|---|
| Qwen/ms-swift messages | 显式 user/assistant/tool 边界、真实工具调用和返回；由固定 tokenizer/template 渲染 | Codex 本地工具名和格式并非 Qwen 原生接口；只监督公开 assistant 内容，观察不作 assistant 标签；缺失内容不补造 |
| mini-SWE 的 bash(command) | 单命令、工作目录、stdout/stderr、退出码、提交 patch | 新 subshell、权限、输出 JSON 与截断、结束标记必须一一对应；现有 Codex 工具历史不能直接改名后称原生 mini 轨迹 |
| Terminus-2 | 任务目标、真实产物、测试结果可复用 | 持续 tmux、keystrokes/duration、屏幕观察与 task_complete 有实际语义差异。普通 shell 轨迹不能机械改写为同 harness；需要从一开始通过该终端状态机执行，并保存当时的动作与观察 |
| ASI CLI | 真实科研实现、工具执行与验证工件可作能力补充 | Codex 采集不等于已锁定 OpenCode adapter 原生消息；需保留原协议标注，不能冒充目标 adapter 轨迹 |

因此，先做一个有完整 command/output/测试证据的独立任务，验收采集链路及协议对应关系，再决定是否扩量。不要以“子代理最终解对”推断已得到可直接训练、与目标 harness 一致的完整轨迹。

## 已执行的首题试点

- 来源：Textualize/rich，MIT，固定 base `9d8f9a372cc5916fd4781fec207ced7ddac2f08f`；solver 仅接收“cwd 不可读时 import rich 不应崩溃”的无答案任务包，不搜索 issue、PR 或修复历史。浅取该 SHA，没有读取正式 benchmark 题或答案。
- 位置：80 的 `/data/caoqinlu/projects/apex-takehome/artifacts/agent_teacher/pilot_rich_4201/`。原始 checkout、测试、隔离 HOME、逐步账本、补丁和新 base 重放全部在此目录；未向上游提交内容。
- 审阅 `rich/__init__.py` 与其唯一 eager 子模块后，才执行 import。子进程使用最小 env；不安装依赖、不执行 setup、无 API/GPU/Slurm。
- baseline：原复现新进程退出码 1，确认 `PermissionError` 从 `os.getcwd` 传播。独立编写的五项 fresh-process 检查在修复前为 3 pass / 2 fail。
- 修改：仅 `rich/__init__.py` 的 cwd fallback，将 `except FileNotFoundError` 改为 `except OSError` 并更新注释。正常 cwd 保留实际绝对路径；OS cwd 错误使用原有空字符串 fallback；无关 `RuntimeError` 继续传播。
- 修复后：原复现退出码 0；五项检查 5/5；重新导出固定 base、应用保存补丁后再运行五项检查，最终 5/5。未运行完整上游测试套件；验证是 solver 自编的回归/边界检查与新 base 重放，尚无盲测第三方独立验证。
- 完整保留 15 个命令步骤，包括隔离 PATH 无 `rg` 的失败，以及首次重放未建立 `.git` 边界而导致 patch 没有应用到导出目录的失败。后者建立隔离 `.git` 后重放通过；最初 outcome 曾提前写入重放成功，现已纠正并明确保留该报告错误，不删除失败记录。
- patch SHA-256：`722e4c9221dff832f8bab509ba832a0dfb847ed431943e011b472d6dab977f90`。原树为 clean detached checkout，最终仅一个 tracked 源文件修改，没有 source commit。
- 每步 `command.sh`、`assistant_visible.txt`、`stdout.txt`、`stderr.txt`、`result.json` 与聚合 `events.jsonl` 均保存。stdout/stderr 按各自字节流完整保存；跨流交错时序、完整 Codex 消息 transport、隐藏推理、精确教师 build、token/logprob 均 unavailable。账本不是完整原生 Codex/mini/Terminus2 消息流，不能直接认定为可开训数据。

项目依据：`analysis/readiness_data.md`（实际消息结构）、`analysis/data_expert_recommendation.md`（harness 语义边界）、`analysis/dev_ablation_plan.md`（任务族隔离与独立验证）。本文件不改变正式评测或训练配置。

## 协调者追加的重放验证

协调者另外定义七项 cwd 导入边界用例，从同一固定 base 只导出两个已审阅的 import 文件，在独立 `.git` 边界应用所存 patch；修复前 3/7、修复后 7/7。证据保存在试点目录 `root_verification/summary.json` 及各次 stdout/stderr/退出码。它是另行编写检查和 fresh-base 重放，仍不是完整上游测试或盲测第三方验收。发现代理及协调者读过原 issue 中带修复线索的内容，因此不能将整个发现流程称为未接触答案；solver 的输入已剥离这些线索，未获 gold patch。没有将这些检查伪装成官方 benchmark 成绩。
