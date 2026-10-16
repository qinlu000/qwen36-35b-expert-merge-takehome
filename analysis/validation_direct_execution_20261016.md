# 已完成 SFT 模型的独立题目验证

2026-10-16 22:30 CST。用户明确要求把已完成 SFT 的专家跑 validation。**已启动真实 HLE 答题和评分；不是继续看 teacher-forcing loss。** 不重训，不修改冻结训练数据、验证金标或另一会话的正式 Base 评测。

## 当前固定范围

| 比较 | 独立题数 | 权重 | 评分 |
|---|---:|---|---|
| HLE proxy | 每模型100，合计300 | Base、HLE checkpoint16、HLE checkpoint250 | 原 HLE criteria + 已使用的 DeepSeek-V4-Flash JSON judge |
| ASI proxy（ScienceAgentBench） | 每模型20，合计40 | Base、ASI checkpoint128 | 8题原机械checker、12题原图像checker（每题3次judge，均值阈值60） |

HLE 100题来自已冻结 `hle_existing_2k_20261016/swift_ready/val.tasks.jsonl`：41题数学 exactMatch、59题 MMLU-Pro 选择题，八大类比例固定，**没有图像，且不声称具有正式HLE难度**。59题 question 已确认包含完整 A–J 选项。验证模型只接收 system + question，参考 answer 只进入独立评分进程。

ASI 当前真正可恢复、且未进训练的冻结 task-dev 是 **20题**，原计划100题没有落实，不用重复题/训练题补齐。其任务ID为4/5/6/7/8/10/14/18/19/21/23/27/33/40/41/47/71/72/73/74。8个机械题是5/18/19/21/40/41/71/72；其余12题输出图像。它是SAB独立代理验证，不是正式ASI的60×4任务。

## 已运行的服务与进程

专属推理为 hpc3 job **727113**，ACD1-24:18000，经80独立桥 `http://127.0.0.1:28089` 使用。别名为 `apex-val-base` / `apex-val-hle16` / `apex-val-hle250` / `apex-val-asi128` / `apex-val-swe249`。四个adapter各620个tensor的投影覆盖、无missing/unexpected、真实五别名生成与SWE tool调用已经由root完成验收；本支没有再发重复验收请求。

80根目录 `/data/caoqinlu/projects/apex-takehome`：

- `scripts/run_direct_validation_blocks.py`，PID **4183881**，taskset125，输出 `artifacts/eval/validation_direct_20261016/blocks.log`。先等已验收门闩，随后顺序执行 Base-HLE100 → Base-ASI20 → HLE16-100 → HLE250-100 → ASI128-20，避免不同adapter混batch。
- 子进程 `scripts/run_direct_validation.py`，当前 Base-HLE PID **534891**，每次8路、64K上下文/8K输出、非思考、不保留thinking、seed0、temperature0.7/top_p0.8/top_k20。HLE每题300s，ASI生成/执行总计算预算1200s。完整请求响应、usage、finish_reason和时长保存在各模型 `questions/`。
- `scripts/score_direct_hle_validation.py`，PID **4183925**，taskset125，2个轻量HTTP线程，独立 `hle_scores/` 账本，HLE硬限 **¥10**，最多每答2次judge尝试。未评分/基础设施错误保持null，不通过重生原答案修评分失败。

服务验收门闩在80 `artifacts/eval/validation_direct_20261016/service_ready.json`，来自HPC `artifacts/validation/lora-service-727113/acceptance.json`，root于22:18实际验收并放行。22:22首个 Base-HLE 答案已171.039s完成，原评分器成功返回；账本1次请求、¥0.00180825。这只证明完整生成→评分链路可用，不把首条当准确率结论。

## SAB 的程序执行阶段

生成只发送原 prompt，不发送 gold_program、checker或参考文件。当前先持久化代码，再按原ASI direct_llm代码块提取方式执行；执行预算采用 `max(0, 1200 - generation_elapsed)`，排队等待CPU的离线间隔另记。**这种分段验证并非正式ASI连续1200s walltime协议**，Base和ASI128采用相同办法。

80的102任务完整输入包约3.8G已在盘。新建独立 `artifacts/envs/sab-validation-py310`，不修改共享Base/训练环境；固定科学依赖与CPU版torch均已就绪。程序执行只能看到自身workspace、只读输入数据与科学依赖；参考/checker只在评分阶段可见，API凭据不进入代码沙箱。每次4CPU/8GiB、无任务GPU、无网络，沿用现有bwrap/seccomp/cgroup限制。

当前CPU125已分配SWE单路，API薄client可共用；SAB的4CPU执行须等TB全部相关CPU消费者永久结束后使用112–115。常驻队列已等待独立 `sab_cpu_ready.json` 门闩（ready=true、cpus=[112,113,114,115]），不凭GPU退卡标记抢占仍在评分的CPU。root已部署CPU释放监控PID553293，检查repair32转交、pending/active空、旧无admitted、所有相关Base scope退出并连续两轮满足后才放行，不依赖手工回来写文件。

常驻进程与运行方式：

- `scripts/finish_sab_validation_env.py`，原80 PID **561478**，taskset125，已成功结束。首批54个固定科学依赖与CPU版torch2.3.0均已安装，`sab_env_ready.json` 已生成并记录版本：numpy1.26.4/pandas1.5.3/scipy1.13.1/matplotlib3.7.5/sklearn1.3.2/rdkit2023.9.5/geopandas0.14.4/rasterio1.3.11/mlxtend0.23.1/oggm1.6.1/torch2.3.0+cpu。新venv仅修正自身Python symlink/home到同一个系统Python3.10，便于断网命名空间挂载，没有改变共享env。依赖安装完成不是20题环境已全部执行通过，仍以实际程序/checker记录为准。
- `scripts/run_sab_validation_queue.py`，80 PID **576253**（原561543在0任务时修正凭据路径；564978同样在0任务、CPU门闩尚未放行时，为加入文件名str规范化而替换，旧等待日志保留），等待CPU与env两个门闩后才扩大自身affinity到112–115。固定40个生成结果逐个执行，使用 `scripts/sab_validation_sandbox.py` 及原bwrap/seccomp/cgroup限制；输出 `artifacts/eval/validation_direct_20261016/sab_scores/{results,workspaces,graders,vision_calls}/` 和summary。原 `DirectLLMAdapter._extract_code` 负责代码提取，保持原fallback行为。helper按绝对cpu-list选择当前允许的112–115，不再把125单核父affinity切offset112；门闩前不扩大affinity。
- 启动命令为 `PYTHONPATH=artifacts/benchmarks/asi artifacts/envs/asi-py312/bin/python -u scripts/run_sab_validation_queue.py --tasks=artifacts/data/candidates/asi_sft_expanded_20261016/val.tasks.jsonl --generations=artifacts/eval/validation_direct_20261016 --output=artifacts/eval/validation_direct_20261016/sab_scores --env-dir=artifacts/envs/sab-validation-py310 --ready-file=artifacts/eval/validation_direct_20261016/sab_cpu_ready.json --env-ready-file=artifacts/eval/validation_direct_20261016/sab_env_ready.json`。控制器按root分配CPU125轻等待；放行后专占四核，超时按systemd scope终止所有后代，API密钥不进入子程序环境。

SAB视觉评分保留官方 [gpt4_visual_judge.py](https://github.com/OSU-NLP-Group/ScienceAgentBench/blob/c26e151ed601ba109dc4d35e057ff8e73fec469d/gpt4_visual_judge.py) 的原rubric、三次评分及均值≥60规则。当前DeepSeek官方 `deepseek-flash` 已有真实图像校准成功证据，不能沿用早期“纯文本无法看图”的错误判断。模型替换将明确披露，SAB API单独上限¥10，与HLE合计不超过root分配¥20。原上游 `n=3` 可等价拆成三次独立调用，保持temp0.2/top_p0.95/max1000与评分聚合。

评分路径已逐一静态核对：**全部12个视觉checker均没有Path/exists/open等直接相对文件访问，只有两次encode_image＋score_figure＋int(score≥60)**，因此没有因host cwd错误而提前返回假0的分支。shim将预测图映射到该任务绝对workspace、gold映射到固定benchmark_root，12个gold实际文件全存在；参数都是str常量，入口另加 `str(filename)` 兼容Path。没有必要新增chdir或复制gold进模型workspace。详情见 `analysis/source_snapshots/sab_visual_checker_paths_20261016.json`；本次无模型生成、执行或API调用。沿用官方行为：一次judge没有匹配 `[FINAL SCORE]: 整数` 时该次分数为0，三次取平均；HTTP/结构失败则最多一次重试，仍失败保留scoring_invalid。

## 自有文件及待闭环

- 新增 `scripts/run_direct_validation.py`、`run_direct_validation_blocks.py`、`score_direct_hle_validation.py`、`run_sab_validation_queue.py`、`sab_validation_sandbox.py`、`finish_sab_validation_env.py`，均已同步80；compile与100题prepare-only通过，prepare未调用模型/API。
- 下一步让300份HLE生成与判分自然完成；比较总准确率、Math/MCQ分项、输出长度和格式，之后才选择HLE权重。cp16目前只是最低loss候选，不先断定优于Base或最后cp250。
- SAB补完专属环境与4CPU执行队列，逐条保存执行/评分原始日志；环境未就绪、评分服务失败不算模型错误零分。
- 本支不Git提交共享文件，根任务统一更新claud.md并提交自有变更；不触碰另一会话Base正式结果。

22:37只读超时归因：Base已28题终态（7完整回答、21本地300s超时）。抽查3条均先/tokenize成功（精确输入100/120/164token），后以TimeoutError在300.021–300.051s结束，无raw_response/usage/finish_reason，**没有达到8192输出上限的证据**。同窗服务持续Running8/Waiting0、约79–84输出token/s；已完成回答示例772token/76.6s、2299token/234.2s，慢解码触发预算是最吻合的解释，未见HTTP错误、adapter错误或队列积压。但服务禁用了逐请求日志，不能将aggregate运行状态当每个超时的逐题处理证明；也没有请求ID对应的主动断开记录。当前脚本将这些预算内无完整答卷计0，只能解释为固定300s预算下的成功率约定，须单列timeout，不是judge认定答案错误，更不是8K正常截断。若严格能力准确率要求逐题已处理证据，应将超时归因未确认单列，暂不发布该口径主分；本次没有改预算、重生成、追加探针或变更评分。
