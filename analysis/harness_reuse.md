# 环境构建相似性与harness代码复用

2026-10-16。按用户明确的方法分别检查：环境看轨迹sandbox如何构建、与benchmark是否相似；harness看公开实现能否直接复用。以下为固定源码和已有环境文件的判断，没有运行模型/任务或改变正式配置。

## 环境：构建方式比较

| 目标与数据 | 轨迹任务环境怎样构建 | benchmark环境怎样构建 | 判断与最小适配 |
| --- | --- | --- | --- |
| SWE / Open-SWE | 上游逐任务/仓库Docker环境，初始化到base commit并安装语言工具链与项目依赖 | 官方逐题Docker镜像，已准备repo/base/deps，再用mini/bash修改工作区 | 构建范式相似。关联同源image/base/cwd/setup，核路径与网络政策；原NVIDIA版本/启动参数不完整是配置取证缺口，不是无环境或无harness代码 |
| Terminal / Nemotron | Harbor任务包，领域Dockerfile预装CLI/Python库，COPY逐题输入到/app | 同为Harbor任务包，各题Dockerfile准备系统/依赖和文件；基底有Ubuntu、Debian/Python slim | 文件布局与执行形态接近。可复用构建文件并锁本次环境；逐题files、依赖和权限需验收，不能把领域共享镜像误当所有题初态相同 |
| ASI / D3 | 科学Python依赖环境，完整程序执行并保存表格/图片等；发布逐题Docker环境 | 官方科学Python/任务Docker环境，读取data并生成指定产物，原生支持多个agent adapter | 环境用途相近；/task与/workspace、依赖、非root可写和输入输出需接线。静态程序与多轮工具的差异归harness选择单独比较 |
| HLE / 学术QA | 静态文本问答/推理，无逐题工具执行环境 | 固定文本/图片生成客户端，无工具 | 统一模型模板与图文输入；重点是题源/质量与图像覆盖，不需要逐题shell sandbox |

构建信息与未公开字段见[sandbox总报告](trajectory_sandbox.md)。上述“相似”不等于已逐题恢复成功，也不以Linux/Docker名称代替依赖和初始化核验。

## harness：已有代码能直接复用什么

| 项目 | 已确认公开实现 | 建议复用方式 | 尚需接线 |
| --- | --- | --- | --- |
| SWE | mini-swe-agent v2.4.6、Harbor MiniSweAgent、SWE Pro LockedMiniSwe和PatchReplay | 直接复用agent循环、bash工具、观察/错误处理、官方补丁捕获和fresh replay | 模型端点/版本/生成设置、独立训练任务image/base/cwd/setup；不重写SWE agent |
| Terminal | 固定Harbor内置Terminus2、JSON parser、tmux、Chat、LiteLLM和TB2 registry | 训练补采与评测优先沿用同一公开Terminus2主干 | 本地Qwen参数、容器backend、输入恢复和训练格式；不引入新planner或整套NeMo训练栈 |
| ASI | 官方DirectLLMAdapter和OpenCodeCLIAdapter；D3有静态生成客户端与SFT转换代码 | 把D3+direct_llm列为匹配候选，与多轮OpenCode路线比较后再冻结 | direct_llm生成参数/总deadline，模型可见输入与产物契约；OpenCode路线另需对应工具行为数据 |
| HLE | 官方run_model_predictions生成客户端 | 复用官方生成主干，使用固定题集/模态和模型模板 | revision/采样/超时/判分接线 |

mini官方tag指向 `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`，其DefaultAgent及actions_toolcall.py与80已装包SHA完全相等。[mini代码](https://github.com/SWE-agent/mini-swe-agent/tree/a83fcae82d2a08f0ee0c688f9d137b3566c097f8)、[官方SWE适配](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/locked_mini_swe.py)、[Terminus2代码](https://github.com/harbor-framework/harbor/blob/f527f8e447038fd242d08ecfa8aaa8029100da97/src/harbor/agents/terminus_2/terminus_2.py)。NVIDIA完整批量采集launcher/精确配置未核到，不妨碍复用公开标准harness；仍要记录源提示与版本差异。

直接复用是复用现有循环、parser、执行与日志代码，补任务/模型连接配置；不表示当前机器已经原样端到端验收。Docker→Apptainer的启动、输入、权限/网络与资源问题属于environment backend，不需要因此重写mini或Terminus2。

## ASI：按数据形态选择代码，OpenCode仍只是候选

此前“D3只能做辅助”的判断以选择OpenCode为前提。固定官方[direct_llm实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/adapters/direct_llm.py)已有“官方prompt→一次生成完整Python→代码提取→官方sandbox执行→产物收集→原grader”主干，与D3监督形态更接近。它保留科学程序执行，但模型不能探索文件、读取执行错误后修复；当前消息只含文本prompt，也没有图片附件或read工具。程序本身仍可处理数据和图像文件，不能把它等同于模型获得图片视觉观察。

因此D3可否成为ASI主要程序监督，应与最终harness一起确定；不能先锁多轮OpenCode再断言必须重采所有数据。direct_llm不是完整NVIDIA/D3原采集器，但已有相近生成/执行代码可以复用，不需另造任务/评分系统。原生代码还缺显式生成参数和生成+执行总deadline接线，需独立小任务验收。是否选择它，应在正式Base与SFT之前结合独立dev、工程成熟度和多轮/图文能力取舍决定，不依据正式成绩选择。

详细代码入口：[SWE复用清单](harness_reuse_swe.md)、[Terminal复用清单](harness_reuse_terminal.md)、[ASI/HLE复用清单](harness_reuse_asi_hle.md)。下一步围绕现成实现验证“环境构建相近、同harness能接官方任务”，再确定主训练清单；本轮没有修改现有OpenCode配置、执行比较或启动训练。
