# 夜间学术与科研执行数据进展及未决问题

更新时间：2026-10-16 北京时间。此分支遵循“只用新版轨迹；已删除的旧 OpenR1 / OpenScienceReasoning-2 / Qwen3 D3 轨迹不回退”的决定。只做数据构建、公开任务来源核验、CPU 静态检查和获授权的有界教师生成；没有 GPU 训练或四项正式 benchmark 运行；新增的两条 SciCode 教师程序只在断网、限 CPU/内存沙箱执行，未在宿主运行。

**已完成并冻结可训版本：204 Math-v4 + 296 新版 Pro，500 train / 100 独立代理 val。** Science-v2 的 135 条无独立 gold 候选移到 hold，原 339+161 清后文件保留为 `train.with_publisher_science.hold.jsonl`，没有删除或静默覆盖证据。跨生物/物理/化学各 4 题的 Flash 模型批评给出 1 accept / 8 needs_review / 3 reject；这不是独立真值，其中一个 reject 自身有矛盾，但暴露出题目缺唯一性、结构/条件缺失等风险。根任务批准用同类别有公开 gold 的独立 MMLU-Pro 任务生成新版 Pro 解答替换后，七类新教师配额全部达标；第二阶段 PID 2664847 已退出，旧阶段总结与全部 API ledger 均保留。下面关于 135 Science 的段落是第一版候选及其发现经过，不再是最终可训数据配方。

## 最终可训文件与验收

80 文件目录：`/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/night_hle_20261016/swift_ready/`。HPC 同路径相对项目根：`/data/user/qinlucao/projects/apex-takehome/artifacts/data/candidates/night_hle_20261016/swift_ready/`。Mac ignored artifacts 也已同步。五个数据文件在 HPC 逐一核对 SHA256 与行数，5/5 一致。

| 文件 | 行数 | SHA256 |
| --- | ---: | --- |
| `train.messages.jsonl` | 500 | `66dbd5012b560bc7b2358bdd05001fb0fa95e56f56498685288cb5ed7f649b38` |
| `train.provenance.jsonl` | 500 | `b490c60ddbebc3907966418c1a1e93f1be15934f328b12df1cd1d8700788ba9b` |
| `val.messages.jsonl` | 100 | `dca83f108ab2d33b5d9ac6c308b09b673d588d5a5d5122e505fc0c5a6b6ff59d` |
| `val.tasks.jsonl` | 100 | `b096203887a82b835da069f0162373e162bf4a89ebb3415f19910f3743dcd517` |
| `val.provenance.jsonl` | 100 | `082b41e6c756a3a2d3ae9debc0e6304eeddd32bd1b075fa839388fb72773bbd6` |

训练与 val-loss 文件均只有标准 `messages`，每条 user → assistant，原始多余空工具/名称字段已去除，确认固定模板渲染 token 数完全不变。正文没有隐藏思考字段或 think tag；Qwen 固定模板仍可能自行添加空 think 壳。训练 500 条共 **243,140 完整序列 token，最大 1,531**；最大 assistant 正文 1,423 token。val-loss 100 条共 16,562 token、最大 582，因此 **2K 窗口容纳全部数据**，没有截断或丢弃样本。这不是实际 Swift labels / processed tokens；训练栈还需检查 user mask，再启动 GPU 训练。[最终回执](source_snapshots/night_hle_swift_ready_20261016.json)

全 500 对正式 HLE 输入及固定 100 val 进行 exact / 13-gram 检查，无重合；所有角色、完整输出、源题和题族定位保留。val-loss 只使用原 `expected_answer` 或选项字母，未生成假解释；`val.tasks.jsonl` 独立保存题面、参考与答案类型，供准确率评测使用。验证集无任何教师调用。最终训练有 **296/500 MCQ（59.2%）**，高于 HLE 的 23.64%；仍无图像训练，不能将粗类别数量相同理解为难度/形式/模态完全匹配。

总教师调用 **362**：296 金标选项匹配、65 不一致拒收、1 请求/协议错误；Pro 输入 96,772、输出 47,785 token，单次最大输出 933。加上 12 条科学答案批评，按峰值及保守预算系数累计 **¥2.58201072**，低于 ¥20 分支硬限；错误调用未知 usage 时按最大预留记账。选项匹配不证明每句解释正确。[最终 API 回执](source_snapshots/night_hle_teacher_final_20261016.json)、[最终模板/排除回执](source_snapshots/night_hle_materialization_final_20261016.json)

本次实际遇到 transformers 5.15 的接口差异：`apply_chat_template(tokenize=True)` 默认返回 `BatchEncoding`，直接 `len(...)` 是字段数。最终统计统一采用 `tokenize=False` 渲染后 `encode(add_special_tokens=False)`，并逐条核对 messages-only 导出前后长度一致；没有将字段数误报为 token 数。

## 已落地：HLE 八类 100 题代理验证集

已在 80 生成 `artifacts/data/candidates/night_hle_20261016/proxy_val_100.jsonl`，不是待下载的数量计划：

| HLE 粗类别 | 500 题训练目标 | 100 题代理验证集 | 新教师训练补齐目标 |
| --- | ---: | ---: | ---: |
| Math | 204 | 41 | 0 |
| Biology/Medicine | 56 | 11 | 56 |
| Computer Science/AI | 48 | 10 | 48 |
| Other | 47 | 9 | 47 |
| Physics | 46 | 9 | 46 |
| Humanities/Social Science | 44 | 9 | 44 |
| Chemistry | 33 | 7 | 33 |
| Engineering | 22 | 4 | 22 |
| 合计 | 500 | 100 | 296 |

配额按固定 HLE 2,500 题的八类数量使用最大余数法分配。验证集的 41 道数学来自新版 Math-v4 的独立候选保留族，使用发布者 `expected_answer`；其余 59 题来自固定 [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/blob/b189ec765aa7ed75c8acfea42df31fdae71f97be/README.md) 的公开参考答案。MMLU-Pro 卡声明 MIT、经专家复核，源标签 `src` 和原题 ID 均保留；不能将其现成 CoT 当作本项目的新教师解答。这里没有使用四项正式评测答案生成训练标签。

固定 MMLU-Pro revision 为 `b189ec765aa7ed75c8acfea42df31fdae71f97be`，两个 Parquet 均完整下载并与 LFS SHA256 一致。实际扫描 12,102 行，保守去掉 391 个重复题干、11 个疑似缺图或外部上下文条目、2 个与正式 HLE 题干 exact / 13-gram 重合条目，以及 599 个没有强行映射到目标类别的条目。正式 HLE 只读取 `question` 用于排除，没有读取 answer / rationale / 模型结果。源文件、逐行定位和引用保存于清单中。[完整选择回执](source_snapshots/night_hle_proxy_selection_20261016.json)

这份验证集仍有明确边界：

- **类别数量对齐，难度没有对齐。** MMLU-Pro 是难于原 MMLU 的大学/专业知识问答，不能冒称与 HLE 研究级题同等难度。它可用来检查训练退化、类别覆盖及合版方向，不能替代正式 HLE 全量结果。
- **0 道图像、59 道 MCQ**；正式 HLE 是 342/2,500 图像、591/2,500 MCQ。其余 41 个数学参考也仍需验收答案匹配器。公开数学参考部分来自上游模型共识/参考匹配流程，并非全部人工真值。
- **Other 的具体内容不完整。** 固定 HLE 的 Other 主要包含 trivia、musicology、art history、games、chess、ballet 等；本版只用 MMLU 的 miscellaneous、geography、formal logic、logical fallacies 子源。经济、法律、心理等放 Humanities/Social Science，没有塞到 Other 凑数。验证集保留每条 `ori_source`，细分缺口待讨论。
- **题族识别仍有限。** 新旧数学上游已有家族映射保留；MMLU-Pro 没有完整原考试/论文族 ID，本版只能按规范化题干分族，再对教师训练候选与 MMLU 验证题做 13-gram 排除。未声称完成语义改写、全部教材/考试同族隔离。

## 教师生成经过（现已完成）

第一阶段保留新版 Math-v4 / Science-v2 的 339 个训练候选，其中数学 204 个有发布者参考匹配证据，Science 135 个标记“教师解答、无独立 gold，待答案核验”。另外从独立训练候选中构建 322 个有公开 gold 的 MMLU-Pro 备用题，先补齐缺失四类的 161 个目标。随后依据上述质量信号把 135 Science 留 hold，第二阶段对同类别 gold 任务补齐新解答；没有重新采集全部 2,000 条轨迹。

教师使用 `deepseek-v4-pro`；[官方价格页](https://api-docs.deepseek.com/quick_start/pricing/) 当前映射到 **DeepSeek-V4-Pro-0813**。显式传 `thinking={"type":"disabled"}`，单次最大 8,192 输出 token，要求 JSON `solution` / `answer`。正确选项不会写入教师请求，生成后才与发布者 gold 比较；不一致保留拒收记录，不改提示强迫教师输出 gold。最终 SFT 候选保存可见解释与最终答案，隐藏 reasoning 不保留。[官方 thinking 开关](https://api-docs.deepseek.com/guides/thinking_mode/)

首批 8 题覆盖四个缺失类别：协议 8/8 返回可解析 JSON、`finish_reason=stop`、无非空 `reasoning_content`；5 题答案匹配、3 题拒收，最大实际输出 200 token。输入共 2,197、输出共 964 token。按峰值未缓存输入 $1.32/M、输出 $3.96/M 保守核算，$0.00671748；内部按 8 CNY/USD 安全系数记预算 **¥0.05373984**，这不是实时汇率或账单扣款。[首批回执](source_snapshots/night_hle_teacher_preflight_20261016.json)

第一阶段续跑 80 PID **2056062** 已退出，其累计尝试上限 240；第二阶段 PID 2664847 也已退出，累计上限 480。全分支 API 预算硬上限始终 **¥20**，每次调用前预留本次最大潜在费用，未知 usage 的失败也按预留费用记账。两阶段均因目标配额完成而停止。验证题不调用教师。日志、逐次 usage、返回模型名、累计保守费用和拒收理由位于：

```
/data/caoqinlu/projects/apex-takehome/artifacts/data/candidates/night_hle_20261016/
  teacher_generation.log
  teacher_api_ledger.jsonl
  teacher_raw_responses.jsonl
  new_teacher_accepted.jsonl
  teacher_generation_summary.json
```

凭据只从 80 私有文件读入内存，没有打印、复制进上述日志或提交 Git。固定 Qwen 模板渲染、完整序列 token 统计和最终 train/val 交叉检查现已通过，标准 messages 已移交根任务；本分支没有启动训练。

## 新发现的科研执行源：NatureBench 有真实成功证据，但还不能当 ASI 主池

一手 [NatureBench 轨迹卡](https://huggingface.co/datasets/FrontisAI/NatureBench-traces/blob/40beb74d21412655a5471b1032ec91256b40e55b/README.md) 和 [配套任务卡](https://huggingface.co/datasets/FrontisAI/NatureBench/blob/27e2dc304464257d2884fa6996bc8ca5d4a2256b/README.md) 提供原生日志、逐次分数、有效性判决和可执行任务入口。两者固定 revision 分别为 `40beb74d21412655a5471b1032ec91256b40e55b` / `27e2dc304464257d2884fa6996bc8ca5d4a2256b`。

实读索引共 1,440 个模型-任务组合，实际只有 **90 个独立论文任务**。限制教师为 DeepSeek-V4-Pro、GLM-5.2/5.3、Kimi-K3、MiniMax-M3、Qwen3.8-Max 后，442 个组合有评分、有效判决及完整文件。进一步保守要求达到/超过论文 SOTA，163 条仅覆盖 **45 个论文族**。每族取一条后，45 组判决、评分 sidecar 与索引分数均完成核对；这不意味着低于 SOTA 的其他程序都是失败程序。[实测回执](source_snapshots/night_naturebench_audit_20261016.json)

45 族分布为 cellular omics 18、protein biology 7、biomedical modeling 5、physical modeling 7、molecular design 4、relational reasoning 4。资源标签 39 `gpu_low`、4 `gpu_high`、只有 **2 CPU**。这与 ASI 的 11 类项目分布及本项目 4 CPU / 无任务 GPU 沙箱有明显差异。不能把 163 条当 163 个独立任务，也不能从 90 个任务中同时切出 500 train 和 100 val。

已实际下载八条原生日志及 45 族 sidecar/元数据，共约 17.3 MB，并验证固定文件身份；没有运行其中代码。八条都没有 `<think>` / `reasoning_content` 字符串，却全部带结构化 `content.type="thinking"`，每条 3–258 块。清理必须覆盖这种内容块。工具是 Claude Code 的 Read/Bash/Write/Edit/TaskOutput 等；一条包含图片，两条包含发布者保留的坏 JSON。不能静默删坏行后声称轨迹仍完整，也不能把它们直接当 ASI `direct_llm` 的单次完整 Python 程序。

目前 45 族全部保持 `candidate_hold`，训练与 task-dev 发布数均为 0。原因：逐任务数据许可未验收、完整任务环境未恢复、与正式 ASI 的原始来源关系未证明、产物/工具协议需适配。只对 60 个正式 ASI 的公开 `prompt_b1.md` 做 DOI 字符串投影，结果没有 DOI；这不能证明来源独立。NatureBench 总卡 CC BY 4.0 也不替代逐任务第三方许可及模型服务条款。

Mac ignored 证据：`artifacts/data/_metadata/night_academic_asi_20261016/`。80 已同步的候选与八条轨迹：`artifacts/data/audits/night_academic_asi_20261016/naturebench/`。没有下载 NatureBench 全量大数据包。

## 没有采用的线索与理由

- [D3-Gym-Trajectories](https://huggingface.co/datasets/osunlp/D3-Gym-Trajectories/tree/b21b5006956d7d246cf3e35277b13323780a45b2)：当前固定版本仍只有原 Qwen3 4B/8B/14B/32B 四分区，没有核到新版强教师发布；不重下已删除旧轨迹。
- [AutoResearchEval 固定卡](https://huggingface.co/datasets/PrentisAI/AutoResearchEval/blob/412fb4908a3a7b98dd50cfa3e5c6cd40750d2d4f/README.md)：实际公开文件是 70 开放任务/560 rollout、30 优化任务/240 rollout，与卡中 559/31/247 不完全一致。开放任务 397 条为 `judge_unavailable`；优化有 173 条非空分数，不等于 173 个新任务。与 NatureBench 至少一个 DOI 重合，优化 21/30 没 DOI，不能当完全独立补齐池。
- [SPARK 原论文配置](https://arxiv.org/html/2608.30214v1#A6)：题由 DeepSeek-V4-Flash 构造，**答案实际是 Qwen3.5-27B**，不能因题目生成器较新就当作 V4 强教师解答；本轮不下载其 2.6GB 全库。
- [r0b0tlab 新多教师池固定许可](https://huggingface.co/datasets/r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation/blob/7a3473446840bcc397928cd8183d4b3ba3ca13a7/LICENSE) 明示仅限受控非商业研究、含混合上游条款，且开发 holdout 是 benchmark 衍生；当前不纳入主池。UltraData-2605 没有足够逐条教师/金标映射；SimScholar 是论文检索工具环境，不能替代 HLE no-tools 或 ASI 程序交付。

## HLE 移交后的 ASI 新线索

核到 2026 年修订的 [SciCode-Verified v2](https://huggingface.co/datasets/shhu2001/SciCode-Verified/blob/eea11a866be6860725258702b39ef8651ed26abd/README.md)，Apache 2.0。固定任务 JSONL、README、manifest 已下载并核对 Git/LFS 文件身份，任务 JSONL 的 MD5 也与发布 manifest 一致。实读 **64 个主任务、290 个子步描述**；作者记分协议是 287 个 scored 子步，不能混为 290 个独立任务。所有主任务 `general_solution` 和 290 个 `ground_truth_code` 均为 null，因此它是带数值验证器的新任务包，**不是现成强教师 SFT 程序**。[元数据实测回执](source_snapshots/night_scicode_verified_source_20261016.json)

其[官方执行代码](https://github.com/flyingwagner/scicode-verified/tree/ddab4a92f8d80a7113ab946628e994b52354d838/eval_clean) 固定为 `ddab4a92f8d80a7113ab946628e994b52354d838`。已实际下载完整数值 target HDF5 **1,108,078,257 B**；80 通过镜像读取同一固定 revision，最终 SHA256 `8fb6e575b7b6dda5e48b04dea338fc6af4fe185774b8f19221c96945df9b4142`、MD5 `2b41a7df40ddc23ce651ec05b8ecb6f8` 分别与官方 LFS 和发布 manifest 完全一致。下载曾在约 952MiB 中断，使用 range 续传后对整个文件重新校验，没有接受不完整文件。

### 两个独立主任务的实际校准

获授权后先固定两个 train-calibration 主族，再生成新答案：5 `Lanczos`（数学/数值线性代数）与 8 `Spatial_filters_III`（物理/激光傅里叶光学），两题各只有一个子步骤。正式 ASI 只读取 **240 个公开 agent-input prompt** 做排除，没有读取正式 gold、参考代码或评分结果；64 个源主任务与其题面 exact / 13-gram 均无命中。选中两族额外搜索 SciCode、Lanczos/Krylov、空间滤波/傅里叶光学方法名，也无命中。源 JSONL 没有每题原始论文/作者 ID，因此这些检查不能冒称已经证明全部来源族独立。[选择证据](source_snapshots/night_scicode_selection_20261016.json)

新教师仍为 `deepseek-v4-pro`、显式关闭思考、单次上限 8,192，只发题面/背景/函数签名与依赖，没有发测试用例或冻结数值目标。两次 API 输入共 **1,569**、输出 **885** token，全部 `finish_reason=stop`，无非空 reasoning / think tag。根据当次重新读取的[官方峰值价格](https://api-docs.deepseek.com/quick_start/pricing/)，两次最多费用预留为 ¥0.607644；实际保守记账 **$0.00557568 / ¥0.04460544**，本学术分支累计 **¥2.62661616 / ¥20**。没有重试生成、反馈修答案或追加 API。

| 独立主族 | 冻结数值测试 | 完整主任务结论 | 沙箱耗时 |
| --- | --- | --- | ---: |
| 5 Lanczos | 3 / 3，通过全部输出；最大绝对误差 1.12e-15 | 合格科学函数程序候选 1 条 | 0.501 秒 |
| 8 激光空间滤波 | 1 / 4 完整测试通过；前三个 filtered image 数值相符，但二值 mask 失败 | 拒收，保留代码/原始响应和失败证据 | 0.624 秒 |

光学样本的第一例掩码有 **2,880 个像素**不一致：参考排除了带宽边界频率，新答案在边界仍置 1。输出图像在当前离散输入上碰巧一致，也不能跳过掩码检查给它贴“正确”标签。

复用原有冻结 `asi_baseline_limits.py` 和 `asi_bwrap.py`，未修改另一会话 helper：CPU 为 **124–127 共 4 核**，内存 **8GiB、swap=0**，`bwrap --unshare-all` 断网；程序只能看到自己的 workspace 与只读科学依赖，看不到 HDF、私有凭据或正式参考。代码由沙箱执行后输出 NPZ 数值，控制器在沙箱外以 `allow_pickle=False` 读取数值并与 HDF 比较。冻结 helper 的前后身份 SHA256 为 `1a32b603cb4ff3594f32d16560045ab3b462b15cccf6d08b1eaa9e2c7db9279f`，cgroup、CPU 和 mount 回执均保留。新增脚本只做准备、有界生成和独立验收，没有在宿主执行生成代码。[完整回执](source_snapshots/night_scicode_calibration_20261016.json)

### 与 ASI 协议接近及不相同的部分

SciCode 的 CPU NumPy/SciPy 数值科学环境、单个 Python code block 和无工具的代码生成，比 NatureBench 长程 GPU/Claude-Code 轨迹接近当前 ASI direct_llm。可是 **SciCode 要函数返回值，ASI 要无命令行参数的完整程序读工作区输入并写指定产物**。本轮的验证包装器是评分控制器，不会自动把教师函数变成教模型按 ASI 文件契约运行的样本。已物化的 `accepted.function_program.messages.jsonl` 只有 1 条带 provenance 的科学函数候选，标记 `ready_for_asi_main_training=false`；没有当作现成 ASI 主训练池，也没有创建假的 val reference。

SciCode 官方还是累计子步骤生成、每步 1,800 秒、2024/2025 双环境 OR 计分。本轮两题改为完整函数程序、180 秒、当前单一 ASI NumPy 环境、额外严格检查输出 shape；所以这里只能称数值质量校准，不是官方 SciCode 或正式 ASI 分数。固定 Verified 仓库的 vendor 缺少测试所需 `scicode.compare.cmp`；已另外读取[上游固定比较器](https://github.com/scicode-bench/SciCode/blob/e3158ea011d4235245a547460d3688d7ccbf9900/src/scicode/compare/cmp.py)，确认数组采用 `rtol=1e-5, atol=1e-8`，独立比较器保留同容差并更严格核 shape，而不是在宿主运行原始 exec 型 grader。

### 可扩数量、时间和划分边界

**不能从两道简单题外推整个池的通过率或总耗时。** 64 个主任务仅 4 个单子步，另外 60 个需要完整程序整合，最长 15 子步；部分官方测试含 Monte Carlo、PDE、特征值及复杂科学依赖。这个源的硬上限是 64 个独立主族，不是 290/287 道独立题，无法单独提供 500 train + 100 val。

如果讨论后扩展，合适的起点是按真正科学领域与主族切 **约 50 train / 14 dev**，当前两个校准族固定在 train，所有子步骤与派生 I/O 包装必须留在同一侧，不能重新随机拆子步。此划分**尚未执行**，还需要主任务领域标注、跨来源同族关系及文件产物适配。正式 ASI 的 11 类是 math12 / CS9 / physics8 / robotics7 / chemistry6 / biology6 / earth4 / astronomy3 / electrical2 / materials2 / biostat1；本源偏数学/物理材料，不能称分布已经匹配。

即使每主题只调用一次、每次输出最多 8K，对全部 64 主题的 UTF-8 字节极保守输入上界加满输出，费用预留约 **¥23.2529**，已超过本分支剩余预算，因此没有直接放开全量生成。实际费用可能低很多，但要按逐题最大费用预留及实测时长控制；多子步一口气输出还可能超 8K，不能为凑数量静默截断。80 目录为 `artifacts/data/candidates/night_scicode_20261016/`，Mac 已同步小证据/候选文件；1.1GB HDF 只留 80，所有下载、教师与执行进程已退出。

## 需要继续讨论的实质问题

1. 是否接受当前 100 题 HLE 代理 dev 的难度、0 图像、59% MCQ 和 Other 细类偏差；它先满足可运行/可核参考，不能冒称正式分布完全复现。
2. Science 135 个新版教师答案已移至 hold、从主训替换；若以后恢复，需真正可核参考或领域审查，而不是仅凭模型批评的一致性。
3. 新版 ASI 程序数据仍不足：EcoCoder 仅 31 Python 生态方法候选且未执行验证；NatureBench 有质量信号但多数需 GPU、偏生物、原生工具不同。暂不为凑 500/100 复制同族或回退旧教师。
4. 轨迹清理要同时覆盖 `reasoning_content`、think tag 和结构化 thinking 块。LoRA r16 / alpha32 / dropout0.05 与相同 target 已由用户确认；HLE 2K 数据已准备，实际 Swift loss mask 与正式训练由根任务训练栈验收。

所有新来源固定版本的索引见 [版本回执](source_snapshots/night_academic_source_revisions_20261016.json)。执行脚本为 `scripts/audit_night_science_sources.py`、`scripts/prepare_night_hle_proxy.py`、`scripts/generate_night_hle_supplement.py`。本分支不提交 Git，由主任务统一更新总进展文档及 `claud.md`。
