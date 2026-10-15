# ASI 环境安装与验收

> 当前正式路线（2026-10-16）：[v2](evaluation_protocol.md)选定官方`direct_llm`；下文OpenCode安装、262K和假端点交互记录属于已完成的候选环境验收。direct_llm的执行隔离回执见本文后段；正式生成参数、共享1200s、资源限额和真实端点仍待接线，不能直接用OpenCode配置替代。

更新：2026-10-16。执行主机为 `10.123.4.80`，项目 `/data/caoqinlu/projects/apex-takehome`。只安装环境、核对依赖元数据并运行自造烟测；未运行正式 ASI 作答或判分，未读取正式题面、reference、solution、隐藏测试或评分 rubric，付费 API 调用为 0，未使用 GPU。

## 已完成

- 固定源码：`artifacts/benchmarks/asi`，commit `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`，checkout 无修改；安装包 `asibench==0.2.0`。
- 独立 Python 3.12.13 环境：`artifacts/envs/asi-py312`，已安装官方 `[full]` 依赖，77 个包的 `uv pip check` 通过。`asibench --help`、`run --help`、`score --help` 均能启动。
- OpenCode 1.17.15：`artifacts/tools/opencode-1.17.15/node_modules/.bin/opencode`；使用系统 Node 22.23.1，未做全局 npm 安装。精确 npm 版本、下载完整性及所有平台可选包记录在 `configs/asi/package-lock.json`。
- 官方 task_meta 的依赖/资源字段清点：60 个正式任务、240 个 B1–B4 条件、45 组不同 runtime 声明，`requires_gpu` 均为 false。仅输出依赖及资源字段；没有加载 task_eval。
- 独立安装 Ubuntu ngspice 36 的解压版本于 `artifacts/tools/ngspice`，没有修改系统包；wrapper `artifacts/tools/ngspice/bin/ngspice` 使用本地重定位后的 code models。自造 1 V 电阻分压电路实测输出 0.5 V。
- 全依赖导入与自造 NumPy/SciPy 线性方程、Matplotlib 无界面出图通过；未初始化 Taichi GPU backend。
- PySCF 2.14.0、OpenMM 8.6.1 的 CPU platform、scikit-learn 1.8.0/1.9.1 自造线性回归、CVXPY 1.9.3 + SCS 自造凸优化、Numba 0.68.0 自造 CPU JIT、SymPy 1.14.0 导入均通过。
- 固定 Torch 2.5.1（实际二进制版本 `2.5.1+cu124`）的自造张量求和和 NumPy 转换通过，显式 `device=cpu`，没有运行 GPU 计算。

Python 精确依赖在 [requirements-asi.lock](../scripts/requirements-asi.lock)。主要实装版本为 NumPy 2.5.4、SciPy 1.18.1、Pandas 3.0.6、Matplotlib 3.11.2、Pillow 12.3.0、LiteLLM 1.105.1、OpenAI 2.54.0、Taichi 1.7.4。

## CLI 自造交互验收

[smoke_asi_opencode.py](../scripts/smoke_asi_opencode.py) 启动仅监听 localhost 的假 OpenAI endpoint，用官方 adapter 的真实命令启动固定 OpenCode。每次使用全新 workspace、HOME 和 XDG 目录，不加载用户日常配置。模型只返回预先编写的简单工具调用，没有接入真实模型或正式题。

最新烟测通过：3 次本地请求，包含辅助 title 请求及两轮主 agent 请求；执行 `bash` 写文件，下一轮收到工具反馈后终止。保留原生 stdout JSONL、模拟 usage 和请求 JSON。线上真实 Qwen 的工具调用与长上下文仍未验证。

[opencode.json](../configs/asi/opencode.json) 被烟测直接加载：主模型及辅助模型统一；主/辅助请求实测传递 `temperature=0.7`、`top_p=0.8`、`max_tokens=8192`，实际工具列表只有 `bash/edit/glob/grep/read/write`。配置声明 context 262144、input 253952、output 8192、build.steps 100；这次短烟测只证明配置可加载，没有测试达到 100 步时的终止或真实 262K 上下文。`top_k`、thinking 和其余生成参数必须在真实 Qwen 服务接入时继续验收。

使用原 adapter 时需将 `OPENCODE_CONFIG` 指向本项目 JSON，同时由运行器为每个条件提供独立 HOME/XDG。JSON 的 endpoint/key 仅通过 `APEX_ASI_MODEL_BASE`、`APEX_ASI_MODEL_KEY` 环境变量解析；文件没有凭据。此配置没有替代操作系统层面的网络隔离。

2026-10-16 补齐图片能力声明：固定 OpenCode 对新自定义模型默认 `attachment=false`、`input.image=false`。根据 [harness 兼容核查](harness_compatibility_asi_hle.md) 与已安装版本源码，在 `provider.bench.models.apex-qwen` 补入 `attachment=true`、`modalities.input=["text","image"]`、`modalities.output=["text"]`。

已用固定 OpenCode 1.17.15 的真实 `debug config` 和 `models bench --verbose` 做离线解析：修改前两个图片能力开关均为 false，修改后均为 true；叠加官方 ASI adapter 生成的 inline provider 配置后仍保留这两个声明。检查使用新 HOME/XDG、假 endpoint/key，并在独立 network namespace 内运行，没有模型调用。自造 32×32 PNG 经 `debug file read` 的 base64 结果可还原为原文件。这里只验收配置和本地文件读取；真实 Qwen 的图片工具反馈、HTTP 传输与视觉理解仍待服务接入验收。回执为 `artifacts/preflight/asi/offline-image-config-eb0kr3uq/summary.json`。

## 输入与任务依赖

- 通过官方 `TaskEnvironmentManager.ensure_env` 完成 **45/45 组独立任务依赖、60/60 任务** 的安装和 `uv pip check`，安装并发最高为 2。逐组保存 `requirements.lock.txt`；完整回执在 `artifacts/preflight/asi/task_env_install.json`，汇总为 `task_env_summary.json`。45 组精确版本另存到 [task_requirements.json](../configs/asi/task_requirements.json)，准备脚本通过 `UV_CONSTRAINT` 使用这些版本。任务依赖及源码安装过程中均没有运行 GPU。
- 固定 open revision `0fa14219cafdbab634d8b3cfbce238a8735a214f` 的 **657 个 agent-facing 文件已下载完成**，60 实例、完整 240 条件；仅限实例根级 B1–B4 prompt、task_info/framework_task_info 和 data。排除 reference/solution/answers，下载后只检查路径存在性，不打开题面或数据内容。路径为 `artifacts/asi/instances_seed31415`，回执为 `artifacts/preflight/asi/agent_input_download.json`，其中 `reference_material_downloaded=false`。
- HF 初次请求遇到代理断连，改为 2 个下载线程、HF CDN 直接连接后继续；Python/PyPI 官方下载可直连。代理仅用于本次下载进程，不修改用户全局网络设置。

## 仍然阻止正式运行的条件

1. **合规隔离执行 backend 尚未就绪。** 官方 `linux_ns` 在 80 上确实能启动，自造 smoke 成功；但工作目录外的自造 sentinel 仍可读取，源码也未创建 network namespace。它不能证明 reference/凭据不可见，也不能落实仅允许模型 endpoint 的网络策略，不能把它标为正式隔离验收通过。Docker `os` 的镜像尚未构建/启动，缺少可用 Docker backend。
2. CMOS 任务有自定义 `Dockerfile.os`，额外需要 ngspice。宿主机的本地 ngspice 及 Python runtime 已做准备，不等价于该 Dockerfile 镜像构建成功；正式应记录实际 image digest 和容器内 smoke。
3. 真实 Qwen endpoint、工具/生成参数透传、端点白名单尚未做验收。Base 下载成功也不能替代服务接入测试。
4. 本次未配置或核验原 `openai/gpt-5.5` 及图像评分入口；未修改评分模型。公开 references 尚未下载到本次 agent 输入目录，后续应由独立评分流程准备并对 agent 隐藏。

本实验继续采用已选的 `seed31415 / open / local / single run` 协议，没有改成 protected seed42，也没有运行任何正式条件。

2026-10-16核过无sudo路线并实现下述可选候选：`RunConfig.agent`可接受`OpenCodeCLIAdapter`子类，覆写`_build_command()`/`_build_run_env()`可给原生命令加受限挂载与network namespace，保留官方solve、JSONL、usage与collector。CPU/RAM实际限额仍未验收。CLI的`--agent-cmd`会退到generic并丢失原生解析；`OSSandbox.egress_whitelist_port`在固定源码中没有执行引用，两者都不能直接当作现成解决方案。不移植整套Docker backend。

## 无sudo隔离候选：合成验收通过

新增`scripts/asi_bwrap.py:BwrapOpenCodeAdapter`，继承固定官方OpenCode adapter，不替换solve、stdin、JSONL或usage解析。80的bwrap0.6.1创建独立user/mount/PID/net namespace，仅挂当次workspace、精确Python/task venv、OpenCode ELF及公共OS库；prompt/task_info/data只读，HOME/XDG/tmp独立。项目根、host HOME、reference、controller进程环境和外网均在自造哨兵检查中不可见。

`scripts/asi_fixed_relay.py:FixedModelRelay`仅允许一个固定模型的`POST /v1/chat/completions`，真实key留在controller，隔离内仅有窄token及Unix socket。SSE和工具反馈通过；拒绝其他路径、query、absolute URL、CONNECT、错模型/错token，以及会触发服务端抓取的远程图片/视频。图片只接受内嵌data:image，未递归改写文本或tool arguments。

最终全边界回执`artifacts/preflight/asi/bwrap-candidate-ctlr5g31/summary.json`为passed=true，覆盖新增OS与ngspice只读挂载；原生8.072秒timeout后，自造脱离session子进程的heartbeat停止，同PID namespace无剩余进程，relay socket删除。

另以原生TaskEnvironmentManager的24/15/17三组既有缓存执行纯自造科学算例，原生solve实际使用各自task env，未挂默认env：SciPy解[2,3]、SymPy/PNG、Pandas/sklearn系数2截距1、CPU Torch矩阵乘/NumPy互转通过。可选ngspice_root仅挂公共工具精确目录，原wrapper/code models分压实得0.5V。没有读取正式题面、数据或reference；这3组不冒充全45组在新launcher逐个验收。

重放只使用本地假模型端点：

```bash
artifacts/envs/asi-py312/bin/python scripts/asi_smoke_bwrap.py
artifacts/envs/asi-py312/bin/python scripts/asi_smoke_bwrap.py --task-env
```

安全聚合回执与脚本SHA在`analysis/source_snapshots/asi_bwrap_smoke_20261016.json`。该adapter未替换正式协议或选定OpenCode/direct_llm；后者若最终选中也需验收对应隔离入口。CPU/RAM没有强制限额，真实Qwen图文/参数透传与全量任务bootstrap仍待验收，不标记正式ready。

后续权威v2协议已选择`direct_llm`。新增42行`scripts/asi_direct_bwrap.py:BwrapDirectLLMAdapter`只覆写原生`_execute`，复用显式namespace builder；生成在controller，程序执行空间不挂OpenCode、relay、socket或模型凭据。原生solve、一次completion、程序提取与code/data collector保持。没有新增执行反馈后再次生成。

直接模式合成验收4/4通过：三组原生task env的科学计算及ngspice0.5V，另一次8.014秒超时后无残留namespace进程；每例generation_count=execution_count=1，提取程序逐字一致，声明输出正常收集。所有哨兵、host proc/reference/home/key与外网隔离通过。共享builder重构后，OpenCode原边界/工具往返/8.066秒超时也重新验收通过。新回执为`analysis/source_snapshots/asi_direct_bwrap_smoke_20261016.json`，原始结果在`artifacts/preflight/asi/direct-bwrap-73aw4_ks/summary.json`。

该DirectLLM候选只完成执行隔离；正式64K/8K请求参数、共享1200秒deadline、CPU/RAM限额及真实vLLM链路仍未实现或验收。重放自造程序用`artifacts/envs/asi-py312/bin/python scripts/asi_smoke_direct_bwrap.py`，不读取正式题或调用真实模型。

## 重放入口

在 80 项目根目录运行 [setup_asi.sh](../scripts/setup_asi.sh) 可重放框架、精确依赖、OpenCode 和本地 ngspice 安装；所有产物均在 `artifacts/`。源码初次 clone 和 npm 可经已有进程代理，PyPI 建议直连。

```bash
bash scripts/setup_asi.sh
artifacts/envs/asi-py312/bin/python scripts/check_asi_environment.py
artifacts/envs/asi-py312/bin/python scripts/smoke_asi_opencode.py
PATH="$PWD/artifacts/tools/uv:$PATH" \
  CUDA_VISIBLE_DEVICES='' \
  artifacts/envs/asi-py312/bin/python scripts/prepare_asi_task_envs.py
```

输入下载入口是 [download_asi_agent_inputs.py](../scripts/download_asi_agent_inputs.py)，固定 revision，可复用已有下载缓存；在当前网络需进程内已有 HTTP/HTTPS proxy，并设置 `NO_PROXY='.hf.co,.xethub.hf.co'`。以上命令均不包含正式 `run/score`。

证据目录：`artifacts/preflight/asi/`。主要回执为 `task_runtime_inventory.json`、`task_env_summary.json`、`opencode_smoke.json`、`linux_ns_smoke.json`、`scientific_import_smoke.json`、`special_dependency_smoke.json`、`synthetic_ngspice/output.log`、`setup_replay.log`。
