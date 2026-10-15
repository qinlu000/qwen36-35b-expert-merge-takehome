# SWE harness：可直接复用的公开代码

更新：2026-10-16。**有完整可用的 mini-swe-agent harness、Harbor 接入和 SWE-bench Pro 官方适配代码；不需要重写 Agent。**“尚未找到 NVIDIA mini 的完整数据采集流水线/精确配置”不能解释为“没有 harness 代码”。本轮只读源码和版本信息，未安装、运行任务/模型/API或修改评测配置。

## 已核到的版本

- mini 官方 `v2.4.6` tag 指向 **`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`**，本轮用 `git ls-remote --tags` 实查。其 `DefaultAgent`、`actions_toolcall.py` 与80已装2.4.6包源码 SHA-256 完全相同，可直接定位到公开实现。[固定 mini 源码](https://github.com/SWE-agent/mini-swe-agent/tree/a83fcae82d2a08f0ee0c688f9d137b3566c097f8)
- Harbor 固定 `f527f8e447038fd242d08ecfa8aaa8029100da97`；SWE-bench Pro 固定 `66f92766bba642462d4bbe5479e83f91f9211862`。两者已有完整源码 checkout，以下均是它们的现成实现。

## 哪些直接复用

| 部分 | 现成实现 | 我们需要做什么 |
|---|---|---|
| 解题循环与日志 | mini `DefaultAgent`；CLI 使用其 `InteractiveAgent`，可设 yolo 和直接退出 | 直接调用，不另写 planner、命令循环或提交解析。[Agent](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/agents/default.py) |
| 模型接口 | mini `LitellmModel`，已有 OpenAI-compatible chat/tool calls 和观察格式化 | 配置本地 Qwen 的模型名、端点、认证和采样参数；不重写模型客户端。[模型层](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/litellm_model.py) |
| bash 工具与反馈 | `BASH_TOOL`、`parse_toolcall_actions`、`format_toolcall_observation_messages` | 直接使用现有 schema、parser、格式错误反馈与观察渲染，不创造新工具协议。[工具层](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/utils/actions_toolcall.py) |
| 执行环境 | mini 已有 Local / Docker / Singularity 等环境实现 | 正式 Harbor 链由 Harbor 管理 sandbox，mini 在 sandbox 内用 LocalEnvironment；独立直接运行时可选已有 DockerEnvironment，不能无意中在 Harbor 内再套 Docker。[Local](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/environments/local.py)、[Docker](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/environments/docker.py) |
| Harbor 接入 | `MiniSweAgent` 已负责安装 mini、传递端点/config、执行 CLI、保存并转换日志 | 复用原 adapter；选择 backend、任务路径和 agent 参数。[Harbor MiniSweAgent](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/installed/mini_swe_agent.py) |
| SWE Pro 官方保护层 | `LockedMiniSwe` 继承上述类，增加超时和模型补丁捕获，并处理任务镜像的工具安装 | 直接选择该类，不自行实现另一套 SWE agent。[LockedMiniSwe](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py) |
| 官方提交复评 | `PatchReplayAgent` 将捕获的 diff 应用到干净任务镜像，由官方 verifier 评分 | 直接复用 replay 流程，正式任务/镜像/判分不替换。[PatchReplayAgent](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/patch_replay.py) |

## 接入口：配置与薄适配，而非修改 Agent

正式入口已有官方说明：让 `v2/tooling` 可被导入，选择 `locked_mini_swe:LockedMiniSwe`，传 `config_file=v2/tooling/configs/mini_toolcall.yaml`；Harbor 已有 `--ak version=2.4.6` 对应安装版本参数。本地 Qwen 需填 OpenAI-compatible endpoint、模型名、认证、输出预算等连接配置；官方 YAML 中的 `reasoning_effort: high` 不直接照搬给本地 Qwen，prompt/bash/观察模板可以保持官方内容。[官方使用说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)、[官方 mini 配置](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)、[Harbor 安装版本选项](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/options.py#L59)

若要补采，优先也沿用 **Harbor → LockedMiniSwe → mini-swe-agent → bash** 这条链，只把独立训练任务的 image/base/cwd/初始化和 grader 输入做成任务适配；正式评测继续使用官方任务。上游训练任务与 SWE Pro 都提供预构建仓库环境、初始 checkout、依赖和 shell 执行，构建方式属于同类；具体环境字段恢复见[已有 sandbox 调研](trajectory_sandbox_swe.md)，无需因此重做 Agent。

## 仍缺什么

缺的是**源 NVIDIA mini 的精确采集版本/参数和逐题运行政策**，不是 mini harness 源码；也还需把上游任务字段接到运行器、做训练消息转换和小规模环境/端点检查。此前624条结构检查已支持 bash/JSON 观察接近、原生解析19项通过，但这些不替代真实环境验收或 SFT 收益评估。[兼容性审计](harness_compatibility_swe.md)

本轮仅新增本报告，未修改 claud.md、Git、配置或 agent 源码。
