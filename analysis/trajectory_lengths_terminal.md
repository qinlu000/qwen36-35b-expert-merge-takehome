# Terminal-Corpus 轨迹实际 token 长度（2026-10-16）

固定 Qwen3.6 tokenizer 的实测结果表明：全库分层加权样本的整条轨迹，保留源思考文本时 median 17,246 / p95 28,380；去显式 think 后 median 12,694 / p95 22,537。优先考虑的 mixed 池另外完成全量 5,689 条：clean 最大 24,810，raw 最大 28,488，所有已存轨迹都在 32K 内。这些是源轨迹长度证据，不能据此承诺正式 Terminal-Bench 2 在 32K 下的成绩不变。

## 数据与测量口径

- 源版本 `nvidia/Nemotron-Terminal-Corpus`：`a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`，已下载 26 个 `synthetic_tasks/skill_based/{difficulty}/{domain}/data_filtered.parquet`，footer 总计 **139,841 条**。
- 26 片 schema 相同：`conversations:list<struct<content:string,role:string>>`，另有 `agent/model/model_provider/date/task/episode/run_id/trial_name:string`、`enable_thinking:bool`。**没有自带 token 长度字段**。
- 使用本地固定 `Qwen3.6-35B-A3B` tokenizer revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。`transformers=4.55.0`、`tokenizers=0.21.1`、`pyarrow=25.0.1`。chat template SHA256：`e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`。
- **raw**：原始所有消息；Qwen 模板 `enable_thinking=true,preserve_thinking=true`，防止模板自动去除旧思考文本。
- **clean**：只从 assistant 消息开头删除显式成对 `<think>...</think>`；再用 `enable_thinking=false,preserve_thinking=false` 渲染。**Terminus JSON 的 `analysis`、`plan`、commands 等协议内容全部保留**，user/tool 观察文本全部保留。没有按字段名字删除推理。
- headline 为整条已存 conversation 的 Qwen 模板 token 数，包含所有观察及 role/header 等模板 token；`add_generation_prompt=false`、`add_special_tokens=false`、`truncation=false`。另存不带模板的原始内容总数，见 JSON 的 `*_content_sum`。
- 单次 assistant output 统计其 content，不含 role/header/EOS framing；按当前 Qwen tokenizer 重新计数，**不是原教师计费 token**。assistant 累计为一条轨迹内所有 assistant content 之和，不是单次输出上限。

## 抽样与算力

全库每片取包含首尾的等距 128 行，共 **3,328 条 / 26,219 次 assistant 输出**，不是只取前 128 行。全库、difficulty、domain 汇总按每片 `N_file/n_sample_file` 加权；输出分布中每次输出继承该条轨迹的权重。分位数使用加权经验分布，未做置信区间。

该次计数在 80 服务器用 8 个单线程 CPU worker 完成，耗时 **74.15 秒**。按每片速度与源行数估算，全 139,841 条约 **41 分钟**，因此没有启动全库 census。mixed 六片另外用 6 个单线程 worker 扫描全部 **5,689 条 / 34,817 次 assistant 输出**，耗时 **94.83 秒**。全流程无 GPU、无 API、没有运行轨迹命令或任务环境。

全库样本删除 26,159 个 paired leading think；mixed 全量删除 34,697 个。两组均未发现清理后仍以未闭合 `<think>` 开头的 assistant。其余没有该 wrapper 的消息原样保留。

## 整条轨迹（含所有观察与模板）

全库行是分层加权估计；mixed 行是当前下载小池的全量实测。全库 max 是**样本最大值**；mixed max 才是该池实际最大值。

| 范围 | 口径 | 实测条数 | mean | median | p90 | p95 | p99 | max observed |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 全库分层抽样 | raw | 3,328 | 17,246.81 | 17,246 | 25,086 | 28,380 | 34,200 | 73,505 |
| 全库分层抽样 | clean | 3,328 | 13,144.68 | 12,694 | 20,104 | 22,537 | 28,605 | 59,334 |
| mixed 全量 | raw | 5,689 | 13,429.27 | 12,557 | 19,675 | 21,378 | 23,985 | 28,488 |
| mixed 全量 | clean | 5,689 | 10,367.59 | 9,937 | 15,727 | 17,543 | 20,362 | 24,810 |

| 范围 | 口径 | ≤8,192 | ≤16,384 | ≤32,768 | ≤65,536 | ≤131,072 |
|---|---|---:|---:|---:|---:|---:|
| 全库分层抽样 | raw | 6.6610% | 43.7923% | 98.4921% | 99.9988% | 100.0000% |
| 全库分层抽样 | clean | 19.8784% | 73.8273% | 99.8254% | 100.0000% | 100.0000% |
| mixed 全量 | raw | 6.0468% | 76.1294% | 100.0000% | 100.0000% | 100.0000% |
| mixed 全量 | clean | 28.4233% | 92.1427% | 100.0000% | 100.0000% | 100.0000% |

32K 总 context 还要预留新输出。直接从已保存数值增加两个**保守余量代理**，未重新 tokenize：

| 范围 | clean 整条 ≤28,672（32K−4K） | clean 整条 ≤24,576（32K−8K） |
|---|---:|---:|
| 全库分层加权样本 | 99.0329% | 96.9704% |
| mixed 全量 | 100.0000% | 99.9824%（5,688/5,689） |

该代理把已存最后一次实际 output 也算在整条里，又额外预留一次完整 output，因而偏保守；它不是逐 prefix 精确峰值测量，也没有计算运行时新增 system 提示、generation prefix 或摘要请求等额外内容。**整条 ≤32K 不自动表示每个请求还能 reserve 4K/8K**。

## assistant 输出长度

| 范围 | 口径 | 实测输出次数 | mean | median | p90 | p95 | p99 | max observed | ≤4,096 | ≤8,192 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 全库分层抽样 | raw | 26,219 | 1,157.74 | 760 | 2,739 | 3,438 | 4,527 | 7,175 | 97.8881% | 100.0000% |
| 全库分层抽样 | clean | 26,219 | 649.83 | 370 | 1,700 | 2,408 | 3,403 | 5,696 | 99.7998% | 100.0000% |
| mixed 全量 | raw | 34,817 | 1,161.97 | 714 | 2,766 | 3,418 | 4,658 | 8,522 | 97.8746% | 99.9885% |
| mixed 全量 | clean | 34,817 | 661.06 | 374 | 1,837 | 2,405 | 3,296 | 5,196 | 99.8305% | 100.0000% |

mixed 全量 raw 有 **4/34,817 次**输出超过 8K（最大 8,522）；clean 则全部在 8K 内，其中 **59/34,817 次**超过 4K。全库样本的 raw 输出 ≤8K 为 100% 并不代表源库所有 raw 输出都满足 8K，mixed 全量已发现反例。

如果按「一条轨迹是否至少有一次 clean 输出超过 4K」统计，全库样本的加权比例为 **1.5655%**，mixed 全量为 **1.0371%（59/5,689）**。小的单次输出超限比例仍可能影响更多整条轨迹；不能把 per-output 覆盖率直接当成整轨迹适配率。

每条轨迹的 assistant 累计 token：

| 范围 | 口径 | mean | median | p90 | p95 | p99 | max observed |
|---|---|---:|---:|---:|---:|---:|---:|
| 全库分层抽样 | raw | 9,359.40 | 9,284 | 13,907 | 15,894 | 18,415 | 34,160 |
| 全库分层抽样 | clean | 5,253.34 | 4,925 | 8,574 | 9,688 | 12,406 | 24,952 |
| mixed 全量 | raw | 7,111.31 | 6,589 | 10,725 | 11,396 | 12,223 | 13,963 |
| mixed 全量 | clean | 4,045.71 | 3,852 | 6,507 | 7,286 | 8,663 | 10,388 |

## difficulty / domain

下列全库两表仍为 N/n 加权样本；mixed 单独 census 表在后面，不能混称全 139,841 条实测。

| difficulty | 源条数 | 样本条数 | raw median | raw p95 | clean median | clean p95 | clean p99 | clean ≤32K |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| easy | 44,809 | 1,152 | 12,624 | 23,106 | 8,758 | 17,139 | 22,233 | 100.0000% |
| medium | 89,343 | 1,408 | 18,723 | 29,356 | 14,574 | 24,161 | 29,588 | 99.7268% |
| mixed | 5,689 | 768 | 12,513 | 21,371 | 10,009 | 17,614 | 20,483 | 100.0000% |

| domain（跨 difficulty） | 源条数 | 样本条数 | raw median | raw p95 | clean median | clean p95 | clean p99 | clean ≤32K |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| data_processing | 9,287 | 384 | 13,855 | 22,295 | 10,330 | 17,884 | 20,580 | 100.0000% |
| data_querying | 9,535 | 256 | 15,944 | 28,915 | 11,332 | 21,942 | 26,829 | 100.0000% |
| data_science | 17,565 | 384 | 17,047 | 29,138 | 14,163 | 25,051 | 31,528 | 99.4821% |
| debugging | 17,382 | 384 | 18,673 | 31,707 | 13,160 | 23,585 | 30,221 | 99.4846% |
| dependency_management | 9,935 | 256 | 16,558 | 24,157 | 12,114 | 20,526 | 23,263 | 100.0000% |
| file_operations | 16,096 | 384 | 17,144 | 27,366 | 12,666 | 22,287 | 24,188 | 100.0000% |
| model_training | 214 | 128 | 32,674 | 57,719 | 27,148 | 48,035 | 53,805 | 70.3125% |
| scientific_computing | 19,482 | 384 | 16,381 | 24,996 | 11,260 | 20,772 | 27,820 | 100.0000% |
| security | 17,010 | 384 | 17,877 | 27,202 | 13,260 | 23,134 | 26,900 | 100.0000% |
| software_engineering | 15,559 | 256 | 17,493 | 31,597 | 13,220 | 24,026 | 31,014 | 100.0000% |
| system_administration | 7,776 | 128 | 18,477 | 28,217 | 15,028 | 23,083 | 28,756 | 100.0000% |

`model_training` 仅 214 条、抽了 128 条，属于稀小长尾：clean median 27,148、p95 48,035，样本加权 ≤32K 仅 70.3125%。总体 99.8254% 覆盖不能掩盖这个域；按类别选数据时需单独处理。

mixed 全量：

| domain | 全量条数 | raw median | raw p95 | raw max | clean median | clean p95 | clean p99 | clean max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| data_processing | 957 | 13,428 | 21,755 | 25,929 | 10,508 | 17,681 | 20,137 | 22,090 |
| data_science | 944 | 13,675 | 22,814 | 28,488 | 11,433 | 19,611 | 21,838 | 24,810 |
| debugging | 950 | 13,414 | 22,316 | 28,071 | 9,814 | 17,874 | 21,277 | 24,021 |
| file_operations | 851 | 13,638 | 21,481 | 26,930 | 10,752 | 17,708 | 19,556 | 22,223 |
| scientific_computing | 1,000 | 11,213 | 16,702 | 25,520 | 8,840 | 13,647 | 16,848 | 22,145 |
| security | 987 | 11,709 | 18,994 | 27,416 | 8,896 | 15,144 | 18,282 | 23,903 |

各 difficulty×domain 文件的完整统计（含 mean/p90/coverage 和 content-sum 等口径）保存在聚合 JSON 的 `groups.file/...`。mixed 全量完整统计在同一 JSON 的 `mixed_full_census`，未替换全库抽样 group，也没有把两组重叠记录当独立样本相加。

## 对方案的含义与边界

- 若要以 clean 口径训练完整序列，8K 整轨迹只覆盖全库估计 19.88%、mixed 实测 28.42%；直接截到 8K 会截掉大量轨迹。应选完整短记录，或另行讨论按完整交互窗口切分。此次没有做训练切分或过滤。
- mixed 的完整源记录在 32K 内有充分 token 余量，是优先小池的长度证据；原始任务与轨迹映射、split 联合去重、动作合法性和训练样本合格性仍按已有审计另行处理。**源数据不等于已验收训练集**。
- 本测量拼接的是存储记录，不一定是教师整个 episode 的所有历史；也不模拟实际 harness 的摘要/压缩，所以不能把该长度直接当模型实际峰值 context。没有读取正式 benchmark 题面、答案或 tests，没有复跑或用 completion 字段推断成功率。
- 这些长度不能证明目标 Terminal-Bench 2 正式任务也能用 32K、4K 输出获得相同分数，不能替代题定 256K context / 80K output 的正式协议。运行预算是否调整需单独决定，本次未修改运行配置。

## 产物与复现

- `scripts/audit_terminal_lengths.py`：CPU 只读计数脚本，固定本地模型和数据 revision，最大 8 个 worker，每 worker 限 1 线程，不自动下载。
- `analysis/source_snapshots/trajectory_lengths_terminal_20261016.json`：全库分层加权结果 + `mixed_full_census`，只有数字和环境元数据，没有任务/命令/观察正文。
- 80 服务器 ignored numeric JSONL：`artifacts/data/audits/terminal_lengths_20261016_sample128/` 与 `artifacts/data/audits/terminal_lengths_20261016_sample0_mixed/`；只含行号、token 数组及长度，不含正文。可从这些行级数值重算阈值，无需重新 tokenize。
- 复现命令（80 repo 下，已有环境）：

```sh
/data/caoqinlu/envs/datamind-sft/bin/python scripts/audit_terminal_lengths.py "$PWD" --samples-per-file 128 --workers 8 --output artifacts/data/audits/terminal_lengths_20261016_sample128.json
/data/caoqinlu/envs/datamind-sft/bin/python scripts/audit_terminal_lengths.py "$PWD" --samples-per-file 0 --difficulty mixed --workers 6 --output artifacts/data/audits/terminal_lengths_20261016_mixed_full.json
```

本次未安装包、下载数据、运行 GPU/模型/任务/API，未改主协议或 `claud.md`，未执行 Git 操作。
