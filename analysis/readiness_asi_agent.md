# ASI agent 接入准备：推荐 OpenCode，备选 pi

更新：2026-10-15。只读研究，未安装 CLI、未访问参考答案、未调用模型、未启动任务或评分。ASI 固定代码 `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`。以下命令是待执行草案。

## 结论与选择

**推荐官方内置 `opencode_cli`，固定 OpenCode 1.17.15；备选内置 `pi_cli`，固定 pi 0.84.3。** 两者已有多轮 terminal/file 工具循环和原生 JSONL 观测，不需要先写一个科研 agent，也不需要为复用 D3 静态答案而退化成单次生成。官方适配器会生成 OpenAI Chat Completions 自定义 provider，可连接自部署 Qwen endpoint；这只证明代码具备接入口，尚未验证本次 Qwen 的工具调用、thinking 和长上下文。

- [OpenCode 适配器：构造器、provider、命令](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/opencode_cli.py#L110)
- [pi 适配器：模型配置和无会话命令](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/pi_cli.py#L112)
- [OpenCode 官方自定义 provider 说明](https://opencode.ai/docs/providers/#custom-provider)

| 方案 | 接入与工具 | 选择理由／局限 |
|---|---|---|
| `opencode_cli` 推荐 | `api_base_env`、`api_key_env`、`api_protocol=openai`；原生 bash/文件工具；`opencode run --format json --auto -m bench/<model>` | 直接使用 ASI 内置代码，无协议代理转换；保留每步 JSONL、reasoning、工具与 token 记录。该适配器未暴露采样和总 token/步数预算，必须补齐后才能正式冻结。 |
| `pi_cli` 备选 | 同样支持自定义 OpenAI provider；read/bash/edit/write/grep/find/ls；`--no-session` | 工具少、状态边界直观；生成的模型声明默认 262144 context / 32768 maxTokens，不代表服务实际支持，且 `effort` 是 pi 参数，不等于 Qwen thinking 开关。 |
| 现成 mini-swe-agent + `agent-cmd` 薄封装 | 让已有 agent 读 workspace、产出文件 | 能统一部分 SWE 数据协议，但需要自己补轨迹／成本记录、科研产物提示与隔离；generic 模式只支持 `none`/`linux_ns`，不能直接产出 seed42 官网要求的 `os` 来源证明。当前不优先。 |
| `direct_llm` | 一次 LiteLLM completion 后提取 Python 并执行 | 没有向模型返回执行反馈的多轮循环，不适合作为科研交互执行主方案；可以独立报告为单次生成基线，但不为节省数据适配而取代主方案。 |

[generic 与内置边界](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/getting-started.md#plugging-in-your-agent)；[direct_llm 实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py#L128)。

## 推荐命令草案：不含密钥值

前提：已另行准备固定 commit 的 ASI 源码 checkout、Python 3.11+ 与 full 依赖、相应版本 CLI、确定的实例目录及计算资源。这里不以 PyPI 最新版替代固定源码。

进程环境预先提供：

- `APEX_ASI_MODEL_BASE`：从 agent 执行环境可访问的完整 `http://<hpc-endpoint>:<port>/v1`，不得写容器内不可达的宿主机 `127.0.0.1`。
- `APEX_ASI_MODEL_KEY`：本地模型服务的鉴权值；适配器要求非空，即使服务不校验，也使用独立的占位值，不复用 HF／DeepSeek／judge 密钥。
- endpoint 的 served model ID 固定为 `apex-qwen`；同一配置轮流装载 Base、专家、合版，并在外部 manifest 记录实际权重 revision。也可用不同 model ID，但其余模型能力配置必须完全相同。

```bash
asibench run \
  --instances-dir /data/caoqinlu/projects/apex-takehome/artifacts/asi/instances_seed31415 \
  --tasks-dir /path/to/ASI-Bench/tasks \
  --agent opencode_cli \
  --agent-config '{"model":"apex-qwen","api_base_env":"APEX_ASI_MODEL_BASE","api_key_env":"APEX_ASI_MODEL_KEY","api_protocol":"openai"}' \
  --prompt-levels b1,b2,b3,b4 \
  --seed 31415 \
  --sandbox linux_ns \
  --tool-mode restricted \
  --timeout 10800 \
  --parallel 1 \
  --retries 1 \
  --output-dir /data/caoqinlu/projects/apex-takehome/artifacts/asi/results/base
```

`--parallel 1` 仅为首轮通路草案，正式并发须按 CPU、RAM、GPU 任务占用和模型吞吐测定。`linux_ns` 仅是公开 seed31415 本地运行候选；若决定 seed42 官网评分，必须改为 `--sandbox os` 并先落实 Docker、任务镜像及 endpoint 网络。两条路线不得混报。

备选命令只将 `--agent` 和 config 换成：

```text
--agent pi_cli
--agent-config '{"model":"apex-qwen","api_base_env":"APEX_ASI_MODEL_BASE","api_key_env":"APEX_ASI_MODEL_KEY","api_protocol":"openai","reasoning":true,"effort":"medium"}'
```

这里 `reasoning=true` / `effort=medium` 仍是待验证草案，不能声称已控制 Qwen enable_thinking／preserve_thinking。若使用 pi 的 `pi_config_dir` 自定义 context/output 声明，须保留隔离的配置目录并锁定 hash；不能沿用用户日常 agent 配置。[pi 默认模型声明](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/pi_cli.py#L221)。

## 环境、预算和产物契约

1. 框架准备 `prompt.md`、agent-facing `task_info.json` 和 `data/`；agent 在 workspace 写任务声明的全部输出文件。官方 collector 仅收集 `metadata.output.files` 中实际存在的文件，日志里说完成不能替代文件。不得向 agent 挂载参考／判分目录。[接口](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/core/agent_interface.py#L20)、[collector](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/subprocess_base.py#L67)。
2. `linux_ns`/`task` 构造 task environment；Docker `os` 有任务镜像路径。不能以宿主机统一 Python 环境取代各任务声明依赖。namespace/容器网络和 GPU 暴露仍需实际资源核对。
3. `--timeout` 默认 10800 秒并统一应用；本题没有要求 ASI 必须照搬 TB 的 32 CPU／48 GB。总步数、单次最大输出、全任务 token、context 压缩策略、重试／失败规则需要在训练前冻结，同 benchmark 的模型相同。[CLI 参数](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/cli.py#L1460)。
4. OpenCode constructor 不接 `max_tokens`、`temperature`、`max_steps`；不能把这些字段直接塞 `--agent-config`。需要检查固定 CLI 的模型/agent 配置或使用可审计的服务／调用网关预算控制。不得默认为 endpoint 默认值就完成预算对齐。
5. `restricted` 的 OpenCode 适配器关闭内置 `webfetch`/`websearch`，不等于 bash 已物理断网。正式网络权限应由 sandbox 和 endpoint 白名单落实；同时保证模型 endpoint 可达。pi 工具白名单也不代替网络隔离。
6. 保留原生 stdout JSONL、normalized trajectory、model-call lifecycle、token/成本、运行版本、输入清单、产物目录和最终 result。以 `step_finish` 原生 usage 为主；缺失记录标未知，不能填 0。逐模型结果目录独立，禁止恢复前一模型会话。
7. OpenCode host-side 基类没有查到自动的一次性 HOME；相较 Claude/Codex 的专门 home 隔离代码，其主机模式会话／全局配置隔离还需补验。Docker 一次性容器更清晰。pi 使用 `--no-session`，其配置目录和 extensions 也需要隔离。

## 本地评分与 Judge：先记录，不能默改

**高优先级口径问题：固定官方代码明确将 seed31415 本地 score 标为 non-official；seed42 只能使用 Docker `os` 产物提交官网私有参考评分。** 本项目之前暂定 seed31415 60×4 是可复现公开口径，但不能把其分数写成官网官方分数。题面要求按固定版本官方流程提交官方主指标，究竟接受官方实现的本地指标，还是要求官网 score，需要讨论确认；此处不自行换 split。[评分边界](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/README.md#how-scoring-works-and-stays-fair)。

本地评分草案（只在决定 seed31415 路线并具备所需 judge 后执行）：

```bash
asibench score --repo seed31415 \
  --results-dir /data/caoqinlu/projects/apex-takehome/artifacts/asi/results/base \
  --instances-dir /data/caoqinlu/projects/apex-takehome/artifacts/asi/instances_seed31415 \
  --tasks-dir /path/to/ASI-Bench/tasks \
  --parallel 1 \
  --judge-api-base https://<approved-judge-gateway>/v1 \
  --judge-api-key-env APEX_ASI_JUDGE_KEY \
  --judge-api-protocol openai
```

- 固定 task scoring 配置决定 judge 模型；endpoint override 不是模型替换许可，DeepSeek 的 key/余额不能证明它支持所要求的 VLM judge。
- task 分数为 0 与 evaluator unavailable/invalid 不同；后者必须单列，报告其分母处理，不能选择性删除失败以提高成绩。
- judge credential 用独立变量，仅评分进程持有；不向 agent 暴露 reference 或 judge key。详细模型/图像能力还需按固定 task_eval 配置清点，当前没有读取任务答案。

## 未决事项与最小下一步

| 优先级 | 未决问题 | 能做的最小验证／决定 |
|---|---|---|
| P0 | seed31415 本地口径是否满足题目；或必须 seed42 官网 | 写入问题清单；讨论后冻结一条路线。不能为躲 Docker 擅自选择 split。 |
| P0 | Docker／user namespace／GPU task runtime 不明 | 只读检查主机能力、任务 runtime 元数据；确定执行节点及模型 endpoint 网络。 |
| P0 | Judge provider、VLM能力和额度缺口 | 核对固定评分配置模型清单；按模型落实凭据或正式确认替代规则。 |
| P1 | Qwen tool-call / reasoning 多轮兼容 | 后续允许工程验证时，用完全自造的临时文件任务做 2–3 次调用，不碰 60 正式任务；核对工具反馈、终止、usage、thinking replay。 |
| P1 | context、单次／总 token、步数和压缩未锁 | 检查固定 OpenCode 模型配置并实际抓取请求；选最少变更方式统一控制，不能只靠 CLI 默认。 |
| P1 | host home/session、端点网络权限 | 首选隔离容器；如用 namespace，验证每 run 的 HOME/XDG 和配置只来自冻结文件。 |
| P2 | D3 与 OpenCode 协议不同 | D3 作为科研程序 SFT 辅助，不能标注为 OpenCode 原生交互轨迹；先不为此更换 ASI 主 agent。 |

建议先完成无模型的运行环境预检，再做自造任务的 endpoint/tool smoke，最后才冻结正式 ASI 配置。当前仅完成入口和约束研究，尚不满足正式评测 ready。
