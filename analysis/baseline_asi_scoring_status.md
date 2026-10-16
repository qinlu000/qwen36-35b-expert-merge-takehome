# ASI v2 本地评分最终状态

2026-10-16 **15:50:52 CST**：在用户授权收敛完整结果后，仅修复soil b2的空预测gate崩溃并重评这一条。固定240条件现为 **240有效、0 evaluator-invalid、0 pending，complete=true**。其余239条结果原样保留。实际报告为 `artifacts/asi/scoring_v2_formal_params_20261016/local_score_seed31415.json`。

- 完整主 `mean_percent=1.5709884069083986%`，累计377.03721765801566／24000分。
- 本轮之前的239有效子集为1.5775615801590612%；该历史不完整报告仍保存，未用其替代完整主结果。
- 原唯一异常是 `earth_science.2_e_soil_carbon_nitrogen_cycling__seed31415__b2`：两预测均为`(3650, 0)`，原file_match对空数组执行min而崩溃。公开`prompt_b2.md:43–44`明确要求两数组`(n_days, 5)` float64；`task_eval.yaml:21–30`规定value_range/min0 hard gate。YAML本身没有shape gate。本次仅在该条件两指定文件size==0时返回正常hard-gate fail，沿用原hard-fail零分聚合；未改rubric／阈值／gold／官方源码，也未把其他评分器异常泛化为零。
- 原invalid条件和完整旧报告分别保存在`soil_empty_prediction_repair/condition_before.json`、`report_before.json`；新评分、独立adapter源码patch、receipt并存。本地回执为`analysis/source_snapshots/asi_soil_empty_prediction_repair_20261016.json`，完整240条件报告为`analysis/source_snapshots/asi_scoring_final_20261016.json`。
- 正式Judge API **0次、¥0**。原生gates未触发付费Judge；网络不是当前评分阻塞。此前所有模型答案继续冻结，不重生、不回流训练。

## 依赖缺失的最小只读核查

对固定选集的203执行失败中，找到了49条No-module条件：pandas37、sklearn4、scipy4、numpy3、markdown1。**49条对应导入全部未由该task官方TaskEnv声明；没有“已声明却漏装”的证据。** 原结果provenance.packages与官方声明一致。16个相关cache的当前pip metadata显示，其全部声明依赖均已安装并满足版本约束；相应未声明导入的distribution当前不存在。

例：Gillespie仅声明numpy>=2.0／scipy>=1.11，对应缓存实际numpy2.5.4／scipy1.18.1，未声明pandas；biostat仅声明scikit-learn>=1.4；BCI／DP-forensics仅numpy／matplotlib；sparse interaction仅numpy；UCB的packages为空。故这37条pandas不能归为“官方声明环境漏装”，本轮不据此补包或重执行。

逐条件声明、原runtime cache key、当前pip metadata及分类回执：`artifacts/asi/scoring_v2_formal_params_20261016/dependency_declaration_audit.json`。核查只读声明／metadata，未导入执行答卷、未重跑、未hash、未调用API。

## Judge真实校准、费用与校内路由

独立自造DeepSeek科学语义校准已完成14次真实生成，0失败、0同请求重试；事前锁定正确≥8／错误≤2且排序正确。实际正确／错误文本10／0、科学阻尼振子图10／0、官方CMOS vector schema12／0。原native text3／vision1／vector3次、caps220／250／400均保留。

输入9031、输出854 token；按峰价input0.3／output1.2 USD/M及预算换算8计，费用上界估算 **¥0.0298728**；按每调用8192输入和native输出cap事前保守预留 **¥0.3157632**。回执 `artifacts/preflight/asi-real-calibration-20261016/summary.json`。14次returned model均为deepseek-flash、fingerprint均为aeb56401ca74e127821c4f9126dcb669；不声称provider内部权重revision不可变。

已完成正式评分配置的endpoint为 `https://api.deepseek.com`，请求模型deepseek-flash；本次正式0调用，没有迁移／混用Judge。root另从HPC执行校内 `https://aigc-api.hkust-gz.edu.cn/v1/models` 返回200，精确ID含DeepSeek-V4-Flash／DeepSeek-V4-Pro；80直连不可达。此为一次纯metadata查询、0生成。路由见 `configs/eval/hkust_api_route.json`，后续必要API可从HPC使用校内入口；不得静默把不同provider/model/version当作此前已冻结身份。未新增proxy、测试或校准。

## 选集、reference与原生执行接线

固定选集是 `base_asi_v2_20261016_infra1/first_valid_selection.json`，237 infra1＋3旧冻结答案，按首次收到的有效答案选取，包括原执行失败答案，未按分数换答案。公开reference **60/60实例、809/809文件、52957623字节**早已准备完成，grader专用，solver旧树0 reference目录。此后遵用户速度优先指令，不重做hash或全量验收。

评分复用固定ASI源码cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc的原gate/scorer、rubric、weights、num_judges、native caps、MAX_RETRIES3及聚合。produce-only结果parameters为空时，只给grader内存记录补入原framework_task_info.json中的冻结public参数；没有该metadata文件时保留原参数，不修改任何答案或gold。

CMOS固定ngspice命令用grader专属Debian13 ngspice44.2+ds-1执行，原deck／提取公式／timeout+30保持；自造分压0.5V、RC在tau0.6321203624V、错误返回码／超时子孙清理已通过。当前解析的官方floating python3.12-slim amd64 digest为sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe，不声称重建未知历史镜像。回执 `artifacts/preflight/asi-ngspice-phx9p21t/summary.json`。

Max3SAT／TSP原二阶段SubmissionRunSpec映射到bwrap＋systemd scope，继承原stage／只读输入／allowlist收集／log／timeout流程，保持原Python命令、CPU1／RAM3GiB／pids／fsize、UID/GID65534、原tmpfs上限及断网。使用满足官方声明的原TaskEnv缓存Python3.12.13，不声称与历史Docker字节一致。自造验收回执 `artifacts/preflight/asi-submission-n6ovup0i/summary.json`。原Max3SAT1800秒、TSP3600秒验证预算不缩短；外层安全余量7200秒。

正式最多4way grader曾限CPU72–75，未占TB0–63／SWE64–71／76–83；当前进程已退出。潜在Judge132原native轮、全部重试上限396；事前保守估计≤¥5.7539952，授权硬限396次／¥6，跨进程flock逐请求预留、失败不释放、缓存0新增。正式实际0调用，预算文件仍由root统一维护。

这些是seed31415公开本地替代Judge实验结果，不是Portal认证成绩。所有原始logs、选集、执行产物、评分attempt和最终JSON继续保存；未stage／commit／修改claud或根索引。

## 空数组修复的可重放入口

`scripts/repair_asi_soil_empty_prediction.py`只评soil b2，禁止Judge调用；已完成目录再次运行会直接返回现有receipt。80实际执行命令：

```bash
taskset -c 72 artifacts/envs/asi-py312/bin/python scripts/repair_asi_soil_empty_prediction.py \
  --project /data/caoqinlu/projects/apex-takehome \
  --output /data/caoqinlu/projects/apex-takehome/artifacts/asi/scoring_v2_formal_params_20261016
```

如需独立重新评这一个条件，使用新的输出目录，链接原`runtime`，复制原`scoring_config.json`，将`soil_empty_prediction_repair/report_before.json`放为`local_score_seed31415.json`、`condition_before.json`放为`conditions/earth_science.2_e_soil_carbon_nitrogen_cycling__seed31415__b2.json`，再把`--output`指向新目录。无需复制或重评另外239条condition文件，完整旧报告已包含它们。仅公开冻结产物被读取，不再执行／生成答案，不读取API凭据，不做新hash。
