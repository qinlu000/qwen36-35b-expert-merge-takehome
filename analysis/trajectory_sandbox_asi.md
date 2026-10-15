# D3科研训练数据的sandbox与ASI适配边界

更新：2026-10-16。只读固定数据卡、通用工作流源码、论文方法段、Docker Hub标签元数据、固定ASI sandbox源码与当前候选配置。没有读取正式题／参考／隐藏测试，也没有读取D3程序答案或逐题eval_script；没有启动容器、任务、模型API、安装或训练，没有拉取镜像层。

## 核心结论

**D3介绍确实提供了执行环境信息，而且作者明确报告现成训练数据已经过环境验证。** 不能因为公开JSON只有静态程序，就说这些答案未经执行，或要求全部重新生成。

但要区分三个阶段：构建任务时执行原始程序、生成并筛选模型答案、向用户发布Docker任务环境。公开资料并未把三者的全部OS／镜像digest／用户／网络／配额逐条关联起来；也没有把现成静态SFT变成OpenCode多轮工具轨迹。

| 对象 | 已确认 | 仍不能确认 |
| --- | --- | --- |
| 已下载D3训练JSON | Qwen3-32B的2,153条；instruction/input/output；作者报告保留silver verifier通过的答案 | 每条对应哪个固定镜像digest、运行日志、用户／网络／资源；没有OpenCode动作反馈 |
| D3发布环境 | 每任务Docker镜像；solution.py→pred_results→run_and_eval；/task内同时有输入、gold和eval资产 | 对agent的gold可见性隔离、确切USER/WORKDIR/发行版及统一资源预算 |
| ASI候选运行 | 官方opencode_cli＋Docker os；/workspace、4CPU/8GiB、OpenCode1.17.15 | 本项目正式容器／网络隔离验收；D3镜像能否直接满足该CLI运行依赖 |

## 1. 已有轨迹怎样产生：有验证依据，但不是已发布多轮执行日志

已下载数据卡是[osunlp/D3-Gym-Trajectories](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/blob/b21b5006956d7d246cf3e35277b13323780a45b2/README.md)，固定revision `b21b5006956d7d246cf3e35277b13323780a45b2`。卡片说明这是论文使用的训练轨迹，按Qwen3模型拆split，但卡片本身没有完整采集命令或sandbox参数。

[论文v1 Appendix E](https://arxiv.org/html/2604.27977v1#A5)进一步说明：对每个模型、每个任务采16条，内容为模型推理和最终程序，在对应环境中使用silver evaluation script执行，只保留通过结果；32B成功数据为2,153条，与固定HF发布相符。作者用vLLM服务采集／评测，并给出通用采样设置temperature=.2、top_p=.95、max_tokens=16K。这是**作者报告的成功验证依据**，不是本项目已逐条复跑或已取得原始执行回执。

固定作者代码 `OSU-NLP-Group/D3-Gym@5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb` 的[Alpaca转换器](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/training/convert_trajectories_to_alpaca.py#L27)明确把instruction/thinking/response转换为：通用程序生成说明、任务输入、公开teacher推理加完整程序。没有tool_calls或工具观察。转换脚本自身只检查必要字段，不再次检查成功标记，所以成功性结论来自论文筛选流程，不能仅由该转换器推出。

因此可把它称为“作者报告经过环境验证的科研程序SFT数据”，不能称“OpenCode在容器内反复调用工具的原生轨迹”。作者的RFT是成功样本筛选后做SFT，不要求本项目再做在线RL，也不要求重新采16次才能使用已发布答案。

### 不把任务构建脚本误认为teacher采集sandbox

同一固定仓库的[execute_programs.py](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/workflow/execute_programs.py#L63)属于**任务构建阶段**：在worker Conda环境执行原始gold_program.py，默认Python3.9，cwd为任务目录，程序超时600秒，提取依赖后pip安装，成功产物保存到gold_results。这里检查的是通用执行代码，没有打开任何gold_program内容。

这份脚本没有Docker、文件系统边界、网络隔离、CPU或内存限额；Conda提供包环境，不自动提供OS隔离。因此不能据发布环境是Docker，就反推此构建步骤也是Docker；也不能把此处Python3.9／600秒当成所有teacher轨迹的确切采集参数。通用[vLLM引擎](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/workflow/engine/vllm_engine.py)是静态Chat Completions接口，不包含多轮工具执行循环，其默认值也不应替代论文采集设置。

## 2. D3发布的Docker环境提供什么

固定[README](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)给出镜像命名`hananemoussa/d3-gym:task_N`，举例task_1/task_151。生成的solution.py挂到`/task/solution.py:ro`，读取输入并写pred_results，再由run_and_eval执行和评分；另有inspect、eval和shell入口。

发布目录契约为：

| 路径 | 发布说明中的用途 | 本项目自采时应在哪一侧 |
| --- | --- | --- |
| /task/task_instruction.txt、datasets/、数据预览 | 题目与输入 | agent可见 |
| /task/solution.py、pred_results/ | 模型程序与待评输出 | agent写入／独立收集 |
| /task/eval_script.py、gold_results/ | 评分逻辑与参考结果 | 隔离评分侧 |
| /task/entrypoint.sh | inspect/shell/run_and_eval/eval路由 | 运行器控制，不能据名字推断已做权限隔离 |

**gold/eval被放在同一镜像，不等于agent不能读取。** README没有公开证明不同用户／权限／mount把这些资产对交互agent隐藏。静态模型只接收说明和预览，与把OpenCode接入同镜像shell是不同的暴露面；复用做交互采集时，需要独立agent视图与评分视图或等效的实际权限隔离，不能直接把整个/task给agent后仍称无参考可见。

README示例命令没有指定`--user`、`-w`、`--network`、`--cpus`、`--memory`或统一超时；文件都在/task也不等于已经核实镜像WORKDIR就是/task。此版本仓库目录未包含Dockerfile／镜像构建入口及完整teacher执行launcher，因此以下仍缺：镜像发行版/Python依赖锁、USER、WORKDIR、网络策略、资源和采集任务到digest的逐条映射。

### 只查标签元数据，不拉镜像层

本轮从Docker Hub公开JSON核查README的两个例子，均active、Linux/amd64：

| tag | registry报告压缩大小 | 本轮查得digest |
| --- | ---: | --- |
| task_1 | 254,347,952B | sha256:5a2c6bca74533927bb16ed83c52235cafca12f55aedb8812db5d553b635c91ee |
| task_151 | 445,386,972B | sha256:cf790c212b3cd9bc4a97ce08123965accd46d7267307a37fc4ac4dae2c653400 |

来源：[task_1元数据](https://hub.docker.com/v2/repositories/hananemoussa/d3-gym/tags/task_1)、[task_151元数据](https://hub.docker.com/v2/repositories/hananemoussa/d3-gym/tags/task_151)。这只确认两个tag当时可列及其架构／digest，不证明565个全部可用，不证明当前digest正是论文teacher采集时使用的digest；没有检查镜像内USER/WORKDIR或文件权限。

## 3. ASI OpenCode sandbox怎样运行，有哪些实质差异

固定ASI框架 `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc`，以下只核通用runner，不打开正式任务评分配置或reference。

| 维度 | D3发布环境 | ASI固定Docker os实现／本项目候选 |
| --- | --- | --- |
| 基础环境 | 每任务预装依赖镜像，两个例子Linux/amd64；发行版未核 | 通用base为python:3.12-slim，按任务依赖与agent叠加；自定义镜像可覆盖 |
| 工作目录 | 文件契约/task，WORKDIR未核 | 显式`-w /workspace`，只挂运行workspace，不把整个宿主目录挂入 |
| 用户 | README未锁 | base默认agent UID1000；Linux非root宿主时`--user 宿主UID:GID`，HOME=/home/agent |
| 资源 | README未锁 | 默认4CPU、8g内存、4096 pids、/tmp tmpfs 2g；CPU会按可见宿主核数下调 |
| 输入只读 | solution.py示例:ro；完整镜像权限未核 | readonly_data默认false，workspace默认rw；可选为data/prompt/task_info叠加ro挂载 |
| 网络 | README未锁 | OpenCode为API CLI，默认保留bridge/API网络；restricted只关闭web工具，不等于仅模型域名可达 |
| 参考隔离 | gold与eval同镜像，agent权限未证明 | workspace与reference目录分开；正式需要确认镜像和挂载未把reference／凭据额外暴露 |
| 交互 | 静态完整程序→运行→验证 | OpenCode读／写／编辑／搜索／shell、多轮工具反馈与原生压缩 |

出处：[task_image.py base与用户](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/task_image.py#L132)、[os_sandbox.py资源与挂载](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L759)、[网络分支](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L841)、[workspace/reference分离](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/orchestrator.py#L619)。

OS runner不继承全部宿主环境，只传白名单与extra_env；另外会把存在的OpenCode auth.json单文件只读挂入容器，而不是整个HOME。只读并不意味着agent无法读取其内容，所以实际运行应使用项目专用HOME／本地模型endpoint凭据，不能把Judge或HF凭据带到解题侧；当前配置文件本身只引用本地模型环境变量，不含密钥值。[认证挂载](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L513)、[环境白名单](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/os_sandbox.py#L825)

源码注释里“requires_network和allow_external_tools双开才联网”不适用于OpenCode的API例外；应以具体分支为准。`AI4SCI_DOCKER_NETWORK`选择Docker网络本身也不提供模型域名白名单，`egress_whitelist_port`在此固定文件只保存到实例字段，没有实现可据此宣称已生效的ACL。本项目要求的仅模型端点出网仍需执行backend落实并独立验证。

`linux_ns`也不是Docker等价替代：固定源码使用user/mount/pid namespace，但没有network namespace，memory_limit字段没有应用为cgroup或rlimit。之前自造烟测仍能读workspace外sentinel，所以不能用这个路径作为正式gold／宿主隔离已验收的证据。[linux_ns实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/linux_ns_sandbox.py)

### D3镜像接ASI不是只填一个image字段

ASI TaskImageBuilder确实允许`runtime.image`，但该优先分支直接返回现成镜像，不安装OpenCode overlay；只有相应Dockerfile/base路径会叠加CLI。因此不能把D3 tag塞进去就认为opencode/node/uv/git/用户目录已经具备。路径/task与/workspace、输入输出声明、entrypoint、依赖、非root可写性和gold隔离都需要小范围适配。[runtime.image分支](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/runner/task_image.py#L205)

当前80的`configs/asi/opencode.json`已声明OpenCode1.17.15自定义Chat Completions provider、六个本地工具、context262144/output8192及text/image能力；这是agent配置，不替代OS sandbox。正式网络和容器隔离仍需验收；图像声明也不代表实际模型图片请求已通过。

## 4. 复用与自采建议

1. **复用现成程序监督。** D3的2,153条已有作者执行验证依据，可继续作为静态科研程序SFT候选，处理来源映射／许可／正式同源与train-dev隔离，按最终thinking策略规范化。此用途不要求先拉565个镜像或重新采全部答案。
2. **复用任务和验证资产。** 已下载565条metadata可帮助选择任务；真正输入和依赖来自镜像。只对选中少量独立任务固定digest、验输入／输出／verifier和参考隔离，支持task-dev或补采；不要为建立小dev先重演全池。
3. **只为缺失能力补采。** 若需要OpenCode的多轮执行与错误恢复，从经过隔离的独立任务真实采动作／反馈，或补充已有可追溯工具轨迹。静态答案不能包装成伪执行反馈；但缺少OpenCode反馈不等于现成静态数据全部无用。
4. **train/dev先分组。** D3 JSON缺task_id/repo，不能只筛metadata就声称轨迹同步清洗；需可靠映射后按原repo／任务分组。dev不用预先采每题teacher示范，任务与可信评分器即可。

HLE当前是no-tools静态图文问答，不运行解题程序，因此没有与终端／科研执行相同的逐题执行sandbox；模型服务和独立Judge输入隔离仍需保留。

本轮只补充证据与适配判断，没有开始改造D3镜像、自采、训练或正式评测。
