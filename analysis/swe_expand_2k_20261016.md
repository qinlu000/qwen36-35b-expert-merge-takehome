# SWE 训练轨迹扩至 2000 条（2026-10-16）

用户授权后，已用新的 Qwen3.8-Flash-Next 成功修复轨迹，将 SWE train 从 448 条扩至 **2000 条**；原 **87 条 val 原样保留**。独立新目录为 `artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k/`，没有覆盖旧训练目录，没有提交 GPU 作业。

## 数据与选择

- 固定源：`nvidia/Open-SWE-Traces`，revision `1db674173119d71df45c22007af99e214600711a`，`data/minisweagent/qwen38_flash_next/`。仍使用既有 9436 个独立成功 bug-fix 家族候选，不切回旧 Qwen3.6 教师。
- 保留已有 train 家族分区，排除原 100 条 val 所在的全部 95 个仓库，再从 Python、Go、JS、TS 四类选样。原 448 条 train 全部符合约束并全部保留，其余按既有稳定排名扩量。
- 以官方 hard51 的语言比例 Python20 / Go20 / JS10 / TS1 分配目标：784 / 785 / 392 / 39。可用 Go 原候选仅 597 个，处理后 520 个符合完整样本约束，无法填满 785 的目标；缺额按其余目标语言 20:10:1 重分配。
- 最终语言数为 **Python955 / Go520 / JS477 / TS48**。因此只能称参考 benchmark 比例，不能声称精确匹配该比例。
- 同一语言内按可用 source 比例选择；最终 SWE-rebench-v2 1229 条、Scale-SWE 771 条，覆盖 **946 个仓库**。仍全部是用户已批准使用的成功修复类，不声称覆盖所有软件工程任务类别。

## 完整长度与协议

| 项目 | Train |
|---|---:|
| 独立任务家族 | 2000 |
| 完整序列 token 总量 | 67,735,326 |
| 助手输出 token 总量 | 14,751,457 |
| 最长完整序列 | 65,424 |
| 最长单次助手回复 | 4,702 |
| 原 448 条 train 保留数 | 448 |

上述长度用固定原始 Qwen tokenizer/chat template 实测；助手输出包含生成后缀与结束标记，**不等同于原生 Swift 的精确 loss mask token 数**。原生 Swift 重渲染的完整长度可能略有不同。

CPU 处理了 3018 条候选，其中 284 条完整历史超过 65,536，2 条不符合已有可识别的固定提交外壳，整条排除；没有删除消息、切窗、压缩工具观察或截断回答来凑数。其余候选再按配额选 2000 条。没有候选因 8192 单回复上限被排除。

清理沿用既定方式：删除 `reasoning_content` 和显式开头 think 块，保留可见解题内容；工具观察沿用已有 XML→目标 JSON 的可见字段转换；只将已知固定 system/Step3 提交指导/末次 echo+cat 命令适配至目标 standalone echo。没有执行源轨迹命令或构造新观察。

## Val 与隔离

新目录的 `val.messages.jsonl`、`val.manifest.jsonl` 和 `val.excluded_over64k.jsonl` 均逐字节复制并相等。保留原 87 条 val、3,058,900 完整序列 token、最长 65,497；没有重新选 val 或改变原 val 长度政策。

Train 与保留 val 的任务家族、仓库、规范化用户输入交叉均为 0。额外排除了原 100 条 val 的全部仓库；这是沿用既有隔离，不是新增语义去重或血缘审计。

## 可复现入口与产物

- CPU 入口：`scripts/expand_swe_sft_2k.py`。80 使用 `/data/caoqinlu/envs/datamind-sft/bin/python`，4 个 CPU worker，实测 97.7 秒。
- 导出：新目录内 `train.messages.jsonl`、`train.manifest.jsonl`、原样复制的 val 文件及 `summary.json`。
- 外层 `expanded_2k/plan.json` 记录目标与处理规模，`excluded.jsonl` 记录整条排除原因。没有新增数据 hash。
- 不以环境恢复为 SFT 前置；未启动容器回放、教师 API、模型推理、训练或正式评测。

原始源：[固定 Open-SWE 分区](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/tree/1db674173119d71df45c22007af99e214600711a/data/minisweagent/qwen38_flash_next)。

## 正式 SFT 接续

用户已授权数据就绪即训练。确认旧 **726162** 为用户 held 的 PENDING 作业、运行时间 0 后取消，以防继续引用原 448 条池。新版正式作业 **726260** 已提交，名称 `apex-swe2k-sft`。

提交入口为 `scripts/run_sft.slurm`：`--time=16:00:00`、4 张 H100、world size4、data dir 使用上面的 `expanded_2k/swift_ready64k`、`--name swe2k`、`--max-length 65536`。保留 r16/alpha32/dropout.05、global batch8（GA2）、一 epoch、原优化器和原学习率；仅使用已 CPU 验证过的原生 Swift 真 dict 配置入口启用既定 fused-linear CE，不缩序列、不降 rank、不删数据。

提交前本项目 baseline 实际运行 6 张 GPU（725705、725539、726129 各2卡）；726100 为其他用户项目未动。未操作 baseline、Terminal、Mixed 或任何其他作业。新日志目录预计为 `artifacts/runs/swe2k-sft-r16-726260/`，外层 `artifacts/runs/expert-sft-726260.log`。**提交不代表首步已通过，实际运行状态随后追加。**

提交后读取状态为 **PENDING / Resources**，运行时间 0、尚未分配 GPU。调度器当时暂估启动时间为 2026-10-16 18:29:56，此估计会变化，不是训练完成时间。按主代理交接要求已停止仅为本作业启动的只读排队等待；没有新增监控或自动化。后续由主代理在下一轮核实 726260 的实际运行与原生日志。
