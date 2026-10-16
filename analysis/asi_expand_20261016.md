# ASI 科学 Python 辅助 SFT 扩量

2026-10-16。本轮只做 CPU 文本整理、公开输入重叠排除和固定 Qwen 模板 token 计数；没有模型生成、付费 API、GPU、程序执行或新环境安装。保留原始人工参考代码，不把函数补全伪称 ASI 文件产物工作流。

## 最终数据

目录：`artifacts/data/candidates/asi_sft_expanded_20261016/`。

| 来源 | 训练条数 | 任务族与监督性质 |
| --- | ---: | --- |
| ScienceAgentBench | 82 | 原 82 条训练完整保留为文件前缀，人工参考程序；原 val20 不变 |
| DS-1000 | 976 | 人工库使用参考，447 个 `(library, perturbation_origin_id)` 元数据族；包含改写变体，不能说 976 个独立原题 |
| 原版 SciCode validation | 15 | 15 个科学主任务的完整人工 `general_solution`；不把其 50 子步骤另算独立题 |
| **合计** | **1073** | 新增辅助 991 条，其中 DS447 族＋SciCode15 族 |

DS-1000 候选原始 1000 条中，13 条 prompt 与 SAB val13/14 的公开输入有连续 13-token 匹配，保守按 6 个源任务族排除，共排除 24 条。匹配只说明文本相似，不宣称已经确认真正同源；没有为凑整数补复制样本。对正式 ASI 的 240 个公开 prompt 文件未发现该匹配，未读取正式答案、评分结果或测试代码。SciCode15 个主任务均保留。连续片段排除不能证明全部语义和论文来源独立。

DS-1000 论文声明源自 451 个 StackOverflow 原题；此次固定精简 JSONL 实际有 452 条 `Origin` 记录、453 个上述 metadata 族，其中 Sklearn:53 只存在 Surface 变体、没有 Origin 行。因此实际 provenance 使用库名和 origin ID，明确区分发布论文计数与本文件分组计数，不称它们为 1000 个独立原题。

新增 DS 库分布为 Pandas291、NumPy208、Matplotlib155、SciPy103、Sklearn111、PyTorch68、TensorFlow40；没有按训练前能否装环境过滤。EcoCoder 未加入：虽为 DeepSeek-V4-Pro High，已有样本存在用随机模拟替代真实科学要求的质量风险，本轮人工源已足够，无需强行混入。

## 输入、答案与预算

- 新增样本统一无工具 `system → 原题 → 单 Python code block`。DS 原始 `prompt` 与 `reference_code` 内容保留；有些参考本来是带缩进的函数体补全，既不补造函数或观察，也不按独立脚本 AST 误删。SciCode 使用原任务描述、依赖、接口、各子步骤描述作为题面，答案为原始完整 `general_solution`，不改代码、不附测试答案。
- 教师均为原始人工参考，不存在弱模型教师的准入问题；没有用先前两条非思考 SciCode 新生成程序替换人工答案。隐藏 think/reasoning 不进入新增监督；正常参考代码、说明和原缩进保留。
- 所有新增样本都在完整 64K/8K 预算内，未截断、未切回合、未为缩短序列手动改代码。SAB 原训练文件字节为新文件前缀；`val.messages.jsonl` 与 `val.tasks.jsonl` 与原文件逐字节一致。

| 固定 Qwen 原生模板计数 | 数值 |
| --- | ---: |
| train 完整序列总 token | 594,275 |
| train 最长完整序列 | 12,295 |
| 新增辅助完整序列总 token | 467,585 |
| 新增辅助最长 assistant 内容 | 3,110 |
| SAB82 完整序列总 token | 126,690 |
| SAB82 最长 assistant 内容 | 2,423 |
| val20 完整序列总 token | 77,236 |
| val 最长完整序列 | 23,056 |
| val 最长 assistant 内容 | 2,751 |

方法为固定 Base revision `995ad96eacd98c81ed38be0c5b274b04031597b0` 原始 Jinja 模板＋原始 tokenizer.json，非思考模板、无 padding/truncation。完整序列只做一次测量；assistant 内容是监督量代理，不冒称最终 Swift label token 数。实际训练如采用较小内部 cap，必须同时容纳 23,056-token 的 val；32K 能覆盖所有现有完整样本，64K 协议预算无须改变。选择训练 cap 由 root 决定，本脚本不提交训练。

## 来源与交付

- DS-1000：作者仓库固定 [`b39aab71da6d23ef8d3cac59a7c5f834516ab334`](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/data/ds1000.jsonl.gz)，CC BY-SA4.0；官方 `test` 此处明确重新用途为训练辅助，因此不再作独立评测。
- SciCode：官方 [SciCode1/SciCode](https://huggingface.co/datasets/SciCode1/SciCode/blob/4510f6a6aa27c43fad7b43da2c59602a86e88480/problems_dev.jsonl)，revision `4510f6a6aa27c43fad7b43da2c59602a86e88480`，Apache2.0；官方 validation15 此处转训练，不再作为本项目 held-out dev。没有读入无参考的 test65。
- SAB：原固定 revision `9c6e96c9e74572e979b0930ee735041cef528cb7`，原逐条许可、代码 canary 与内容不改。
- 产物：`train.messages.jsonl`、原样 `val.messages.jsonl` / `val.tasks.jsonl`、全 1073 行 `train.provenance.jsonl`、新增 `auxiliary.provenance.jsonl`、`excluded.jsonl`、`protected_input_overlap.jsonl`、`summary.json`。每条 provenance 含来源、版本、human teacher、Python、任务族和原题标识。
- 可复现入口：`scripts/expand_asi_scientific_python.py`。输出已同步本地、80 `/data/caoqinlu/projects/apex-takehome/` 和 HPC `/data/user/qinlucao/projects/apex-takehome/` 的上述相对目录。未改 Mixed、训练配置、Git 或 shared claud，由 root 统一整合。

本轮新增训练主要教科学 Python 函数与库使用，不能把条数扩大解释成新增了近千个 ASI 同型科研交付环境，也没有新增完整程序正确性的执行证据。
