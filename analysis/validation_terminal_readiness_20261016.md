# Terminal 专家训练与独立 task validation 的准备状态

2026-10-16 22:54 CST 只读训练快照；23:02 完成缺失源包恢复。本轮不提交 GPU 作业、不改 Base 服务、不运行模型或 verifier，不修改共享 SFT 进度文档。

**最新状态：独立 task-val100 的源包已全部拿齐，仍未构建/验收环境，不能称为可直接运行。** 第8片下载与静态提取完成，新增11包中有1个Compose任务，因此当前为88个单Dockerfile + 12个Compose；runtime验收仍为0，分母保持100。

## 当前实际训练

| 项目 | Terminal `726665` | Mixed 对照 `726666` |
| --- | --- | --- |
| 原生加载 train / loss-val | 2000 / 42 | 7066 / 249 |
| optimizer 进度 | 167 / 250，66.8% | 381 / 883，43.1% |
| 已完整通过的 GPU loss-val | **10 次**，到 step160 | **23 次**，到 step368 |
| 最新 checkpoint | 160 | 368 |
| 最新 val loss | 0.42458877 | 1.65768003 |
| 最佳 checkpoint / val loss | **160 / 0.42458877** | **64 / 1.21849561** |
| native 当前估计剩余 | 40分20秒，约23:34 | 3小时42分，约17日02:36 |
| 当前 native 日志 OOM 数量 | 0 | 0 |

ETA 是训练器当时的滚动估计，不是完成承诺。Mixed 的7066是原7073条经过 Swift 预处理后加载的数量，仍为此前同7条 SWE 角色配对失败，不是本轮新删数据。两项目前尚无最终 `summary.json`。

**Terminal 自身已实际通过旧失败点。** 上一轮在首次 step16 验证发生显存溢出；本轮 step16 验证成功，之后继续完成到160的10次全量42条验证并保存checkpoint。结合 Mixed 的23次全量249条验证，可确认 fused-linear-CE 验证显存修复已在真实 GPU 路径通过，不再只是 CPU 检查或其他模型的推断。这里的 loss 仍不等于任务成功率。

原始进度记录见 `analysis/source_snapshots/validation_terminal_sft_status_20261016.json`。

## 独立 Terminal task-val 与正式评测的隔离

保留的是 **100 个任务 / 100 个家族**，位于80：

`artifacts/data/candidates/new_terminal_horizon_20261016/proportional_candidates/val_tasks.provisional.jsonl`

文件名沿用 provisional，当前是已保留的 task-dev 清单；它不是正式 TB2.0 test，也不是训练 loss-val42。20:16补入第100题 `integrate-idr-s-as-a-petsc-krylov-solver`，原99题与现有训练数据不改。

来源：`shunzou05/TerminalHorizon-Environment@e55b3e99927ed6b9b2e4abf2fa93e965dd0503ef`。对应训练轨迹主源为 `TerminalHorizon-3K@45f1e98e317d3639437f0eb02f4e8bc5825732f3`，补充为 NVIDIA Terminal Pivot。最初89个 task 包与新恢复11包均从该独立环境来源提取，**最初89这个数量与正式 Terminal-Bench 的89题只是数量相同**。

本轮对实际文件重新核对，未只沿用旧summary：

- task-val100 / 已提取包89，与正式 TB89 的 task ID 交集分别均为0；标准化题面精确交集也为0。
- 已提取89包全在保留100内，没有包外ID；89份 `instruction.md` 与来源索引对应题面完全匹配，必需的task.toml、Dockerfile、tests/test.sh、solution/solve.sh均存在。
- 23:02又确认新增11包的题面与来源索引匹配、必需文件齐全；因此全部100包均具备这项静态证据，ID与题面隔离结论不变。
- 与当前 Terminal train2000（1303个来源任务）的任务ID、家族键和实际首轮题面精确交集均为0；train实际题面与正式TB题面精确交集也为0。
- 比较采用既有 `candidate_selection.normalized_text`：NFKC、空白折叠、casefold；不新增文件hash。这是精确隔离证据，不是已证明不存在任何语义改写或源任务谱系交集。既有近似题面/正式公开输入片段审计另行保留。

详细100个ID、实际包ID和交集检查见 `analysis/source_snapshots/validation_terminal_readiness_20261016.json`。

## harness 对齐与环境缺口

**2000条训练数据的首user协议前缀全部相同（2834字符），并与当前Harbor原生Terminus JSON plain模板逐字一致。** JSON包含analysis、plan、commands/keystrokes/duration、task_complete；目标使用持久tmux终端。Pivot发布者声明Terminus2 v2.0.0 / Harbor；当前执行链使用项目固定Harbor Terminus2。不把相同协议前缀夸大成所有历史观察与结束确认细节均已逐条证明等价。

原生环境源配置与项目目标需区分：100包的来源配置都是8 CPU / 16 GiB / agent 18,000秒（5小时），目标项目协议为 **4 CPU / 8 GiB / 1,800秒（30分钟）**，推理仍为64K / 单回复8K / 非思考。正式运行时应在独立运行配置中明确覆盖和记录，不篡改来源 `task.toml`，也不把结果称为来源默认5小时配置的成绩。

**当前 task-success validation 尚未就绪，原因是环境未构建与验收：**

- 已保留100题目前100个完整源包，最初的11题缺包已恢复；始终保持100分母与ID。
- 100包中 **88个单Dockerfile，12个Compose任务**；没有预构建SIF，原生runtime验收0。Compose涉及多服务/网络，不能假设当前单SIF backend可完整替代，也不能仅列文件便宣称环境ready。
- 部分Dockerfile需要原始源码编译和网络依赖。需要先完成镜像构建、初态/挂载/权限/tmux可用性与verifier接线，再运行Base和专家。构建失败、缺包与执行异常单列，保留原100个任务清单。
- 42条teacher轨迹只提供SFT loss诊断，不能拿其续写或动作匹配当100题真实任务成功率。

最初11个缺包ID及恢复后状态见快照。第8个源tar `tasks-00007-of-00008.tar.gz.part`在22:56检查时为0字节、从03:52起未增长、无下载进程；固定来源元数据总量 **864,087,916B（约824MiB）**，磁盘空间充分。22:57只恢复这一片，约2分25秒完成，最终长度与固定元数据完全一致；没有重下其他7片、重算hash或构建环境。随后用既有Python3.12读取完整tar流（193个来源任务），仅对保留清单缺的11题作 `filter=data` 静态提取，23:02:43完成。11题现在均确认在第8片内，并核验必需文件和题面一致；新增Compose题为 `integrate-vault-dynamic-database-credentials-with-kubernetes-workloads`。

恢复回执：`analysis/source_snapshots/validation_terminal_part7_recovery_20261016.json`。80原始回执 `.../environments/part7_extract_20261016.json`；原 `val_environment_summary.json` 和7片时代的下载/manifest记录未覆盖，里面89包数字属于历史状态，后续以新回执和实际100个task目录为准。回执没有将仅长度验证标成LFS hash验证。旧全池inspect入口硬性依赖LFS hash回执，本轮没有用伪造hash绕过，也不为刷新旧summary重算全池。

## 训练完成后的推理服务安排

专属 `727113` 仍运行于ACD1-24:18000，两卡，80独立桥28089；Base/SWE249/ASI128/HLE16/HLE250已通过真实验收，当前给direct validation使用。本轮没有重复模型smoke或做数值等价测试。

当前服务没有开启 `VLLM_ALLOW_RUNTIME_LORA_UPDATING`。原生vLLM `entrypoints/serve/lora/api_router.py:27` 在开关关闭时不注册load/unload路由，所以**不能在不重启的情况下向727113热加新的Terminal checkpoint**；已有四别名不能冒充Terminal模型。

推荐后续在Terminal完成、四卡释放后，由主agent统一检查16卡预算并申请一份独立两卡服务，静态注册Terminal候选checkpoint及Base；不打断当前direct或正式Base服务。另一选择是等现有direct批次全部结束后再明确重启727113加入Terminal/Mixed，属于后续协调，当前不执行。新服务本身无需merge-export（当前r16完整projection已被vLLM支持），真实val的主要前置工作仍是100题环境构建与Compose适配。候选checkpoint在训练完成后按既定验证规则选择，不预先把当前best160称作最终模型。
