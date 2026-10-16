# ASI128 执行状态只读审计

对象：80 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/asi128_asi240_20261017/`。用户最初快照为100终态（96 failed / 4 completed）；本次03:38:38 CST薄读已为 **101终态：97 failed / 4 completed，8 active**。后续归类固定这101份已存在文件（mtime不晚于该时刻），不随队列后续新增条目滚动。详细白名单元数据、精确路径与有限错误例见[小收据](source_snapshots/asi_execution_status_audit_20261017.json)。

**这不是4%准确率。** `asi_v2_run.json`记录`produce_only_unscored`、`judge_calls=0`；runner为`score=False`。101项虽各有一个`score_results`，但全部是`unscored_submission`、`max_score=0`占位项，`final_score=0`亦不是科学判分。`completed`只表示程序执行阶段完成，`failed`亦不能直接代替正式评分或环境invalid裁决。

## 已有证据可统计什么

101项均有HTTP200响应、`generation_complete`事件及`execution_count=1`；selected code均非空，没有观测到“完全没有提取出代码”这一失败路径。全部limits收据为8GiB。原生`error_message`、`process_exit_code`、`timeout_phase`均为null，单靠summary无法可靠归因；以下由已有request事件、selected code形态及stderr末条错误归类，不重新运行程序。

| 97个failed的互斥观察分组 | 数量 | 解释 |
|---|---:|---|
| 8192输出上限 + 未闭合fence | 12 | 全部`finish_reason=length`、completion_tokens8192；无闭合Python代码块，native fallback保留整段响应，selected首行仍是markdown fence，随后SyntaxError |
| task runtime未声明的模型import | 36 | pandas26、receptor_kinetics2、Bio1、networkx1、sklearn3、scipy3；对应官方`task_meta.yaml.runtime.packages`未声明所需包，不能自动算环境供给失败 |
| 已声明父包、模型引用错误子模块路径 | 1 | `pyscf.cphf`；实际隔离cache已安装pyscf2.14.0，`pyscf/scf/cphf.py`存在，顶层`pyscf/cphf.py`不存在 |
| 其他程序/API/数据/CLI错误 | 48 | 变量名、字段、形状、数值、文件路径、API符号及命令行契约等错误；仅按当前报错归类，不推断所有反事实原因 |

因此不能把97个failed统称为无代码、模型API错误或框架故障。**本快照没有证明框架或官方已声明依赖供给失败的条目**；这不替代逐条件评分审计，也不保证其他未观察到的环境问题不存在。12项是模型输出预算与官方提取规则的交互，保留为原失败，不修代码、不补闭合fence、不重试。

stderr错误类型完整计数：SyntaxError13、ModuleNotFoundError37、TypeError8、KeyError13、NameError4、IndexError2、ValueError6、UnboundLocalError2、ImportError2、OverflowError1、AttributeError3、OpenMMException1、FileNotFoundError3、LinAlgError1，以及1项argparse缺必需参数。其余4个completed没有stderr。上述类型与互斥观察分组是两个统计维度，不能相加。

## 最短安全错误例与来源

根目录以下记为`E=artifacts/eval/asi128_asi240_20261017`。每个key的原结果为`E/<task_id>/<key>.json`，stderr为同前缀`.agent_stderr.log`，事件为`E/audit/<key>.request.json`；小收据保存实际完整相对路径，无题面、回答正文或完整traceback。

| key | 最短错误证据 |
|---|---|
| astronomy.nbody_close_encounters__seed31415__b1 | `SyntaxError: invalid syntax`；length8192，selected首行是fence |
| astronomy.nbody_close_encounters__seed31415__b3 | `ModuleNotFoundError: No module named 'pandas'`；task只声明numpy/scipy |
| astronomy.planet_activity_sep__seed31415__b3 | `TypeError: string indices must be integers, not 'str'` |
| chemistry.sapt_water_dimer__seed31415__b1 | `ModuleNotFoundError: No module named 'pyscf.cphf'`；父包实际存在 |
| computer_science.euclidean_tsp_tour_optimization__seed31415__b1 | `required: --input, --output, --seed, --time-limit-seconds` |

冻结官方提取逻辑见`artifacts/benchmarks/asi/ai4sci_bench/adapters/direct_llm.py:381-413`：仅匹配闭合fence；未匹配时直接返回`content.strip()`。`runner/orchestrator.py:405`起的`score=False`分支产生上述未判分占位项。现有hook见`scripts/run_direct_asi_formal.py`，不修改官方提取策略，每条件仅一次执行并保留失败。

## ASI128选择边界

训练确实完成134步；历史选用128是原生SFT留出交叉熵最低点 **0.5826834440**，最终134为 **0.5828790069**，不是任务级验证的task-best。证据为`configs/train/four_experts_v1.json`、`curves/training_20261017/source/asi_loss.json`、对应`asi.csv`及`analysis/source_snapshots/model_card_training_evidence_20261017.json`。公开card `models/cards/apex-asi-r16.md`和合版配方`configs/merge/four_experts_avg_v1.json`均明确使用128。

按用户新规则，loss不能作为val判据；上述历史选择不能据此声称有效任务验证或任务最佳。此次只披露该边界，**未擅自换134**，未重选、重训或新增评测。loss也不能解释为上述执行成功率或科学正确率。

本次只新增本文与小JSON；无模型/API/容器/任务执行，无hash扫描，无原结果、队列、配置或checkpoint修改。没有改变任何评分。
