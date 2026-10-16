# SWE / Terminal 当前 SFT 与目标 harness 对齐（2026-10-16）

**可以对齐；当前数据已经完成了相当一部分。SWE 的 system、bash schema、观察格式和提交动作已适配，Terminal 两个来源的原生元提示本身就与目标相同。下一步不应把所有轨迹的 system 粗暴换成同一句话，而应处理剩余的任务包装、结束状态和环境语义。**

本轮只读当前配置、实际执行入口、转换代码及80上的代表性训练样本；未修改数据、作业、评测、服务、共享文档或 Git，未调用模型 API，也未执行轨迹命令。旧兼容性报告的 Qwen3.6 / Terminal-Corpus 样本统计不冒充本轮新数据结论。

## 当前对象及证据

- 训练矩阵：[four_experts_v1.json](../configs/train/four_experts_v1.json)。SWE 为 `new_swe_20261016/expanded_2k/swift_ready64k/train.messages.jsonl`；Terminal 为 `terminal_sft_2k_20261016/train.messages.jsonl`。80 项目根目录 `/data/caoqinlu/projects/apex-takehome`。
- SWE 当前链：`run_swe_full_cohort_root.py` → `run_swe_baseline_v2_native.py` → `SweBaselineNativeV2` → `SweBaselineV2` → 官方 `LockedMiniSwe` / mini-swe-agent 2.4.6。模型桥保留原 messages/tools；官方 YAML 为 `artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml`。
- Terminal 当前链：`run_terminal_native7.py` / `run_terminal_full16.py` → `RecoveryTerminalBaselineV2` → [TerminalBaselineV2](../scripts/terminal_baseline_v2.py) → Harbor 原生 `Terminus2`。恢复控制器更换准入/基础设施处理，不更换原生 JSON/tmux/结束确认语义。
- 配置预算：[protocol_v2_unified64k8k.json](../configs/eval/protocol_v2_unified64k8k.json)，实际 request 代码为 SWE `mini_config()` 与 Terminal `TerminalV2LLM.call()`：non-thinking、64K 总上下文、8K 单次输出。配置文件中旧的“尚未启动”等状态文字不是本轮运行状态证据。

## SWE：已经做了什么，剩下什么

| 项目 | 当前训练与目标的实际关系 |
| --- | --- |
| system | 实际训练首条为 `You are a helpful assistant that can interact with a computer.\n`，与目标 YAML 相同。[扩量转换器](../scripts/expand_swe_sft_2k.py:82)逐条把固定旧 system 替换为目标 system。 |
| 工具 | 训练为原生 function tool `bash`，只有字符串 `command` 参数。读取实际 mini 2.4.6 `BASH_TOOL` 定义并与首条样本比较，**完全相等**。目标每个 action 开新 subshell，目录/环境变量不跨 action 持久化；mini `DefaultAgent.execute_actions()` 顺序执行同轮多个动作。不能改成持久 tmux 后还称相同协议。 |
| 观察 | 源 XML 观察通过 [convert_observation](../scripts/prepare_new_swe_night.py:27)转换为目标官方 JSON：`returncode/output`，或 `output_head/output_tail/elided_chars/warning`，异常信息保留。输出内容与已有 head/tail 不补造；目标长输出阈值是 **10,000 字符**。转换只解决包装，不证明源/目标当时的超时及环境完全相同。 |
| 提交 | 原来 `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt` 已改成单独 echo，并同步修改对应提交指导。目标官方 wrapper 从 `/app` 或 `/testbed` 的真实 git 工作区捕获 diff，再在新沙箱 replay；不会把训练里的 patch.txt 当作最终权威补丁。 |
| 首个 user 包装 | **仍有差异。**训练保留源 `<pr_description>`、创建/检查 patch.txt、只改非测试源文件等指导；目标 YAML 的 `instance_template` 是 `Please solve this issue: {{task}}`、鼓励创建复现脚本、测试边界、最后单独 echo。实际训练样本也确实先创建/检查 patch.txt。只换 system 不会消除此差异。 |
| 路径与环境 | 实际训练命令多次显式 `cd /testbed && ...`。目标 wrapper 支持 `/app` 与 `/testbed`，运行器保留任务镜像自己的 Python/PATH/工作目录；具体库、仓库初态、权限与网络不因 system 一致就相同。不能把所有 `/testbed` 文本替成 `/app`，却保留原路径相关的命令输出。 |

因此，**可以仅改的部分**是没有改变后续行为含义的通用角色描述、工具说明、确定的序列化字段与包装。当前已完成的 XML→JSON 映射和提交契约适配有明确代码，不需要全量重跑。

**不能只换 prompt 的部分**是新增/删除任务约束、把源“准备 patch 文件”行为说成目标原生工作流、替换文件路径/仓库或把独立 shell 改成持久终端。若进一步重建首 user，须保留原题与真实约束，核对后续动作仍有效；不会为了与目标文案相同而伪造观察或删掉实际执行的步骤。若独立开发集表明这些差异影响提交、测试或恢复，再用目标固定 harness 在独立训练题上补少量完整示范，不能由当前差异推断必须重采全部 2k。

## Terminal：元提示已相同，主要留意完成与长历史

当前 provenance 实数为 **TerminalHorizon 1,107 条 + NVIDIA Terminal-Pivot 893 条**，不是旧 Terminal-Corpus。两来源各查看首条（训练行0、1107）；它们都没有独立 system message，而是把协议放在**第一条 user**。

把当前官方 `terminus_2/templates/terminus-json-plain.txt` 中 `Task Description:` 前的模板格式化后，与两个实际样本前缀比较，**均逐字完全相等，都是 2,834 字符**。因此再添加统一 system 或把这段移到 system，反而会改变原生角色布局；本轮没有这样做。

| 项目 | 当前关系与边界 |
| --- | --- |
| 动作 | `tools=[]`；assistant 文本 JSON 必须有 `analysis/plan/commands`，命令项为 `keystrokes/duration`，`task_complete` 可选。末尾换行和 `C-c/C-d` 是真实按键语义，`duration` 是等待时间，原生执行会将单项等待上限压到60秒。它不是 SWE 的 `bash(command)` function call。 |
| 状态与观察 | 原生为持久 tmux，`cd` 和已启动程序可以保留。源样本的 `Current Terminal Screen:` / `New Terminal Output:` 与当前 [TmuxSession](../artifacts/benchmarks/harbor/src/harbor/agents/terminus_2/tmux_session.py:866)相同；目标 `Terminus2._limit_output_length()`按 **10,000 UTF-8字节**保头尾。源样本也有相同截断提示，但不能由两条样本证明全库每次截断均与当前 commit 相同。 |
| 结束 | 目标是两次 `task_complete:true`，中间官方确认消息。Horizon首样本含该确认与第二次完成；Pivot首样本截至公开的完成动作，前一条仍是执行观察。转换代码也明确记录 `publisher filters post-completion confirmations`。这893条可教完整工作过程与完成动作，不能声称都包含目标的第二次确认。**不能为补尾巴自行写一条“真实确认观察”。** |
| 长历史 | 目标启用原生 summarize，在剩余 token 阈值32768附近触发，主/辅助调用均8K；当前SFT保完整可用公开历史，没有人为切后半段。源教师原始上下文/压缩阈值未逐条核明，提示词相同不等于摘要触发时机相同。若后续开发集卡在摘要/续做，应单独补目标摘要与恢复示范。 |
| 工作目录/依赖 | 两个源样本起始均为 `/app`。目标保留各任务镜像的工作目录与依赖，Dockerfile中也可见 `/root`、`/workspace`、更深子目录；不能把整个 TB89 当成固定 `/app` 环境。源任务与目标题也无需相同仓库/文件，需相似工具能力和诚实的任务上下文。 |

隐藏 reasoning / think 包装可以删除；**JSON 内 analysis/plan 是可见的协议字段，必须保留**。SFT 不要求重新启动每个源容器，但若修改命令执行、路径、工具可用性、完成机制或压缩状态，就需要相应真实环境/轨迹证据；改一个 system 无法恢复这些信息。

## 对本项目的直接建议

保留已经对齐的两条原生协议。SWE 的下一优先项是核首 user 中源约束与目标工作流的残余差异；Terminal 的下一优先项是分别记录 Pivot 的完成确认缺尾和部署中的摘要恢复差异。先在独立验证任务观察是否产生失败，再定是否补少量目标 harness 轨迹。Base、专家、合版在**同一 benchmark**内始终使用同一冻结评测协议；跨 benchmark 不强行共用同一套 system、工具或终端状态机制。
