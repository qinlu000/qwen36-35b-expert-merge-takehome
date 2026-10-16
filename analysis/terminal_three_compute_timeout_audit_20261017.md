# Terminal 三项计算超时：双口径审定

2026-10-17 03:01 CST，只读核实原始结果、官方测试、预评分文件快照和实运行冻结Harbor源码。没有运行模型或测试，没有修改原result、reward或summary。

结论：这三项均可在**固定预算下的Harbor默认聚合**中记作未成功0，独立记为 `derived_budget_reward: 0`；**native reward继续null，严格原生有效覆盖不能因此增加**。其它六项恢复成功后，应同时报告原生有效评分442/445，以及445项固定预算聚合。不能写成445项都获得原生reward。跨模型比较必须使用同一聚合政策并披露各自原生覆盖、超时和基础设施失败。

## 源码证据

实运行冻结源码根目录为80 `artifacts/runs/base-terminal-724242/runtime2/scripts/harbor/`，JSON证据保留了实际文件路径、行号和原文：

- `trial/trial.py:855–865`：对 `verifier.verify()` 做 `asyncio.wait_for`，超时抛 `VerifierTimeoutError`，不返回0。
- `verifier/verifier.py:257–268`：只有读取到 `reward.json` 或 `reward.txt` 才返回 `VerifierResult`，不存在时抛异常。三项都没有reward文件，`verifier_result`仍为null。
- `metrics/base.py:14–35`，特别25行：默认聚合将 `reward is None` 映射0；`metrics/mean.py:5–12`调用它并按完整输入列表长度计算mean。因此预算聚合0有实际源码依据，与伪造测试reward是两回事。
- 本项目原生有效筛选见 [run_terminal_independent_repair32.py](../scripts/run_terminal_independent_repair32.py:44)：要求实际reward为0/1且异常在solver失败白名单；verifier超时不在名单。其每seed完整89项才产主分的逻辑位于143–163行，不能据默认聚合更改“原生有效”含义。

这里的Harbor默认聚合本身也会把其它null计0，但本审定只允许以下三个已核实的候选计算超时键；它不授权将依赖缺失、网络、磁盘、测试未启动等基础设施失败补0。

## 固定三项证据

| 键 | 实际官方测试与候选计算 | 原生日志 |
|---|---|---|
| `feal-differential-cryptanalysis/seed0` | pytest收集1项并开始 `test_feal_differential_cryptanalysis_attack`；官方测试29行调用候选 `attack.attack()`、30行才核对密钥；候选包含65536外层、65536内层搜索 | verifier运行900.101206秒，明确 `VerifierTimeoutError: ...900.0 seconds`，无reward |
| `feal-differential-cryptanalysis/seed4` | 同一官方测试实际开始；候选 `k5_seed` 和 `k4_seed` 均为65536层级枚举 | verifier运行900.061156秒，同一900s原生异常，无reward |
| `model-extraction-relu-logits/seed4` | pytest收集1项并进入官方 `test_stolen_matrix_matches`；测试46行同步运行候选 `steal.py`，之后才读矩阵并assert；候选10维×10000点，每点11次forward，随后双层聚类 | verifier运行900.101949秒，同一900s原生异常，无reward |

三份stdout均显示uv/pytest依赖已安装、pytest正式会话与1项收集，未见磁盘满、TLS下载、命令缺失或收集/导入失败。预verifier快照均return_code0且 `captured_before_verifier=true`，包含被评分的 `/app/attack.py` 或 `/app/steal.py`。上述动态证据和候选静态循环支持计算预算耗尽分类；不宣称证明程序永不终止，也不虚构被中断测试已执行末尾assert。

FEAL任务描述虽要求attack少于30秒，官方pytest没有独立30秒计时assert；原task.toml verifier为1800秒，本实验实际冻结override900秒。modelExtract原task.toml verifier本身为900秒，测试内部也没有独立子进程截止。二者都由本实验900秒外层截止中断；本审定没有扩大或改写预算。

## 供只读collector使用

[固定audit JSON](source_snapshots/terminal_three_compute_timeout_audit_20261017.json)有且仅有这三项，每项包含：

- `exact_original_result_path`、task、seed，禁止将派生判定套用到其它trial或后续重跑。
- `native_reward:null`、`native_grade_unchanged:true`、`strict_valid_scored:false`。
- `aggregation_default_none_to_zero:true`、`derived_budget_reward:0`、`derivation:0`。
- 900秒时间、测试开始、无reward、完整快照、未匹配基础设施错误标记，以及具体原stdout/原trial.log/候选源码片段。

collector仅在原result路径、task、seed、native null和900s证据均一致时读取派生0，保持原评分与严格覆盖不变。预算聚合不能当作原takehome所需3小时/32CPU/48GB等完整资源协议结果。
