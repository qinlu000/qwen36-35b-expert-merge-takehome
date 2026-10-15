# SWE 训练轨迹与目标 harness 兼容性检查

检查日期：2026-10-16。结论：**Open-SWE mini/Qwen3.6 子集具有较强的动作/观察协议兼容证据，可继续做成功筛选和训练格式转换；不是已经验收完成的目标原生训练集，不需要因此重跑全部轨迹。**确定差异主要是源提示与提交指导、工具结果缺少关联 ID、训练消息序列化。源执行环境、超时和完整历史生成方式仍未核明。正式 benchmark prompt/config 未修改。

## 固定对象与证据范围

- 目标 SWE-bench Pro：`66f92766bba642462d4bbe5479e83f91f9211862`，官方 `v2/tooling/locked_mini_swe.py` / `configs/mini_toolcall.yaml`；源码 checkout 干净。[官方配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[LockedMiniSwe](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py)
- Harbor：`f527f8e447038fd242d08ecfa8aaa8029100da97`，checkout 干净；其 installed MiniSweAgent 先加载 `-c mini` 再叠加指定 YAML，走 `--yolo --exit-immediately`。不能把 packaged `swebench.yaml` 的 XML 观察格式误当为本项目目标。[实际入口源码](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/installed/mini_swe_agent.py#L767)
- mini-swe-agent：80 已安装包 `2.4.6`，源码位于 `/data/caoqinlu/projects/apex-takehome/artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/`；本报告对其真实 parser / observation formatter / completion detector 做无执行合成检查，不只依赖文档。
- 源数据：`nvidia/Open-SWE-Traces@1db674173119d71df45c22007af99e214600711a`，只含 `data/minisweagent/qwen36_27b/{scale-swe,swe-rebench-v2}` 固定目录的 39 片，原始 95,291 行。[固定数据卡与字段定义](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md)
- 实际检查 **624 条，39 片每片 16 条**：按每个 `resolved` 标签最多四种语言取首次出现，再用等距行补足。覆盖 Python 290、Go 71、Java 59、TS 48、JS 42、C 41、Rust 38、C++ 33、PHP 2；标签成功 212、失败 289、未知 123。这是有界、非随机的结构检查，**不能据此估算全库成功率、任务质量或兼容比例**。
- 仅投影读取 `messages/tools/language/resolved`，遍历元数据只读 `language/resolved`；未读取 `metadata.reference_patch/model_patch` 值、正式题目答案或 hidden tests，未执行任何轨迹命令/测试/容器/模型/API/Slurm。统计不输出原始题面、命令或工具返回。

## 逐项结果

| 检查项 | 已观察到的事实 | 结论与边界 |
|---|---|---|
| 工具 schema | 624/624 的工具定义与目标 `BASH_TOOL` 完全相等。37,024 次实际调用全部是 `bash`，参数恰为单个字符串 `command`；每个 assistant turn 恰好一个调用 | 可直接保留动作语义；不是 tmux keystrokes，也不应转换为持续终端协议 |
| 工具观察 | 36,400 条均为 JSON object，主形态 `returncode/output`；517 条有 `output_head/output_tail/elided_chars/warning`，80 条含异常信息，2,418 条返回码非零 | 与目标官方 JSON 观察同族，不能误称 XML 源格式；仅字段形态相容不证明源超时、异常实现、截断字节逐项相同 |
| 状态 | 624/624 初始提示明确新 subshell、目录/环境变量不跨动作持久化；目标 LocalEnvironment 每次新 `Popen(shell=True)`、保留文件系统改动、合并 stderr 到 stdout | 状态意图一致；源 Parquet 不带运行时 environment config，源真实 backend/工作目录/环境变量和跨动作进程行为尚未证明完全相同 |
| 工具结果 ID | Parquet message schema 没有 `tool_call_id`；assistant tool call 有 ID。全部 36,400 个非终止调用都有紧接且唯一的 tool 结果，未见 orphan 或 multi-call | 当前样本中的单调用结果可按相邻唯一调用补 ID。若全量遇到多调用，不凭顺序猜配；有可验证配对证据才恢复，否则排除主线或保留辅助 |
| 末尾提交 | 624/624 均以 assistant 提交动作结束，没有最终 tool/exit；同样的 marker 在所有初始提示中出现；未见最后 marker 后继续 assistant 行动 | 不能为凑齐消息伪造提交结果。目标检测到首行 marker 且返回码 0 即 `Submitted`，不会再请求模型。目标 InteractiveAgent 还可能记录 not-executed 工具占位再写 exit，源训练截断无需补造这些日志 |
| prompt/完成指导 | 源 624/624 使用相同 system hash，但均不等于目标 system。源首个 user 包含 PR wrapper、不可修改测试等边界、创建/检查 `patch.txt` 并 `echo … && cat patch.txt` 指导；目标官方提示仅要求单独 echo marker | 这是确定的上下文/行为差异。**不要将源 prompt 整体替换成目标 prompt，却保留遵从源补丁提交指导的动作。**原上下文保留时可用于迁移；确有需要再采少量目标提示闭环示范 |
| 提交机制 | 样本中没有恰为单独 echo marker 的提交命令；520 次 marker 命令还包含 `&& cat patch.txt`。目标纯 completion detector 只检查输出和返回码，不解析命令是否恰为单独 echo；LockedMiniSwe 最终另捕获真实 git 工作区补丁 | 源提交方式并非因此必然解析失败；但仍不同于目标提示要求。不能将改写提交命令称为纯序列化转换，也不能用源 patch 文件取代目标官方 fresh replay |
| 格式错误 | 另有 5 条后续 user 消息，均检测到格式错误反馈 | 保留真实反馈与后续恢复，不将其当作新的独立任务或 silently 删除；错误提示字面模板可能不同 |
| Qwen 模板 | 原始嵌套记录 624/624 模板渲染失败；去掉 None 可选键、字符串 arguments 解码为字典、补明确相邻工具 ID 后，624/624 成功，且序列化出 bash 调用 | 这是可机械处理的结构问题；渲染通过不等于服务端实际 tool parser/训练 loss mask 已验收 |
| thinking | 14 条记录的 17 个 assistant 消息有非空 `reasoning_content`；未见 content 内 think tags。关闭 `enable_thinking` 和 `preserve_thinking` 后，这 14 条仍渲染部分公开 reasoning | 固定 Qwen 模板对最后真实 user 后的 assistant 仍保留 reasoning。非思考 SFT 若需要移除须明确转换字段，不能仅依赖两个 flags；本次没有生成训练集或更改训练政策 |

以上样本统计见[无正文统计与逐分片样本行号](source_snapshots/harness/swe_harness_compatibility_20261016.json)。原始带结构特征行号的完整结果在80 `artifacts/data/audits/swe_harness_compatibility_20261016.json`，不含原始任务文字。

## 目标原生逻辑：19 个合成检查

使用真实 mini 2.4.6 的 `parse_toolcall_actions`、`format_toolcall_observation_messages` 和 `LocalEnvironment._check_finished`；**没有调用 `execute` / `_run`，fixture 里的命令仅作为字符串**。

19/19 通过：合法 bash 参数与 ID；空调用、未知工具、坏 JSON、缺 command 被拒绝；短输出、10,001 字符长输出（5,000 + 5,000 + elided 1）和异常 JSON 观察保留字段；marker 必须是输出首个非空行且 returncode=0。另有一项记录 parser 原样接受非字符串 command：这不是训练许可，应在训练转换检查中拒绝，当前 37,024 个源调用均为字符串。

检查摘要见[19 项 fixture](source_snapshots/harness/swe_harness_native_fixture_20261016.json)。脚本为 [audit_swe_harness_fixture.py](../scripts/audit_swe_harness_fixture.py)。该检查不证明网络隔离、资源配额、真实超时取消、模型端点或完整任务能成功。

## 可执行的数据处理结论

1. **可机械转换：**JSON 工具定义解码、None 字段规范化、JSON arguments 字符串转对象；只有单调用且结果唯一相邻时补工具 ID。保留原始命令、观察及源 prompt，不补造结果。
2. **主线先筛：**在原有去污染、任务族 train/dev 分离和许可审计之后，优先取 `resolved=1`；624 个样本中失败/未知标签不是成功示范。仍需全量结构检查与长度统计，不能由本次 624 条外推。
3. **隔离或排除：**工具参数坏/缺失、无法确定结果配对、非终止动作缺结果、依赖不可见历史的样本不进直接模仿主线。不同 source prompt 的完整上下文可保留用于迁移，不把它们重标为目标原生轨迹。
4. **少量补采而非全部重跑：**若独立 smoke/dev 显示模型难以遵循目标提交、超时恢复或工具规则，才在独立训练任务上用目标固定 prompt/harness 补闭环示范。现有证据不支持为了 harness 同名/同版本而重跑全部 Open-SWE。
5. **仍须验收：**源精确 agent revision、源 cwd/env/timeout、异常与观察截断细节、源压缩/上下文生成规则未包含在公开表结构中；目标模型真实 wire/tool parser、非思考训练字段策略、长轨迹窗口、loss mask 和 replay 在后续独立任务验收，不通过正式题目反馈调参。

## 复核入口与源码指纹

结构检查脚本：[audit_swe_harness.py](../scripts/audit_swe_harness.py)。在80用已有 `/data/caoqinlu/projects/dslighting/.venv/bin/python` 执行，不新增依赖。输出为项目 artifacts 下的 audit JSON。原生 fixture 用项目 `artifacts/envs/mini-swe/bin/python`。脚本为检查工具，不是训练转换器。

本地包源码指纹（SHA-256）：

| 80 安装包内相对路径 | SHA-256 |
|---|---|
| `models/utils/actions_toolcall.py` | `47b666412e4f838508b50009cf34c7f63fe15e9e40affc257a17c0829896526f` |
| `environments/local.py` | `01dd33ae6be897458611911cc0eee1389092ea9fc6788c7eb24773e7c6342b1c` |
| `agents/default.py` | `e8ef8aa365942d739c2ec5cb0879f60f377d2dc2de8ec670aaedf3bafb45a4c2` |
| `models/litellm_model.py` | `6df4483bcdc9620b2f9d7f8bb1027a7fb9729b739976cbcf1a9d18fb58c48227` |

官方 `mini_toolcall.yaml` SHA-256 为 `7275afa9920a6fb1b9ec66ab74cee44121db9b0276bb9fa90f5ec0597e523a45`。Qwen 固定 chat template SHA-256 为 `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`，对应 [已保存模板](source_snapshots/model_chat_template.jinja)，工具/推理规则主要在其 assistant 与 tool 分支。
