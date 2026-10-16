# 一页阶段性中文报告草稿

07:28再次生成并验收一页阶段PDF：采用07:26:42双视图，加入完整ASI专家0.378991%及对Base真实退化/配对区间、完整HLE五组3.96/6.92/5.84/4.68/4.04%，TIES2499/1invalid仍不报完整分。摘要181中文字符、含标点199字符；页数1、字体嵌入/缺字0、内容底y123.49、PNG逐页目视无裁切或重叠。成本取07:26固定账本（6卡、已结束227.570GPUh、API15.0291CNY另0.3283USD），仍不是最终report.pdf。

## 07:14更新：完整AVG64 HLE及真实区间

本轮[阶段PDF](../output/pdf/progress_report_20261017.pdf)于2026-10-17 **07:14:04 CST**重画，采用[07:12:42双视图](source_snapshots/formal_aggregation_20261017_0713.json)。主4×6矩阵新增AVG64 HLE **4.680%**；完整HLE表列Base3.96%、专家6.92%、Mixed5.84%、AVG4.68%。AVG对Base+0.72pp、配对95%CI[-0.20,1.64]，不能确认稳定提升；与Mixed的-1.16pp及其区间详见正式收据，不按反馈改冻结主模型。无答1445/30/41/1196及服务差异继续披露，不能作纯权重因果判断。

TIES只写2500生成/2499有效/1项缺correct未决，不报完整方法分差。新增07:03已结束GPU220.989h、active8卡22.477h与API预算核算14.9502CNY另0.3283USD，注明非发票/单价未知；后续消费不回写旧时点。原生成/判分预算及协议偏离仍在。摘要181汉字/含标点199字符；pypdf重开1页A4、font嵌入/glyph通过；实际PNG目视无重叠/截断，内容底部y123.49。编辑marker本轮首次编辑前只运行一次；首次文本替换因编码退出未改源码，后以apply_patch重画的最终PDF已核验。它仍为阶段稿，非最终report.pdf。

以下05:37及其旧快照说明保留历史，不覆盖上述更新。


产物：[阶段报告](../output/pdf/progress_report_20261017.pdf)，生成于**2026-10-17 05:37:42 CST**。它仍是阶段稿，不是最终`report.pdf`，没有把完整评测、TIES任务对照或最终成本标成完成。

[重画脚本](../scripts/render_progress_report.py)只读仓库固定收据，无网络/API/GPU。真实矩阵采用[05:22双视图快照](source_snapshots/formal_aggregation_20261017_0522.json)的strict；主表仅完整范围显示主分。Base SWE19.608%、HLE3.960%、ASI1.571%，HLE专家6.920%；其余目标项待齐备，非目标专家未评。strict Terminal仍442/445，预算视图独立一行20.224719%、442native+3审计超时派生0，raw null不变。

原大幅loss表改为**真实HLE训练对照**：同2500题/342图，Base3.96%、HLE专家6.92%、Mixed5.84%。专家对Base差+2.96pp，逐题配对95%CI[1.80,4.12]。页面同时披露Base无答1445、专家30、Mixed41的历史队列/服务混杂；配对区间不能单独证明权重因果效应。八项截断Judge的一次compact恢复沿原答卷，明确是两次上限之外例外。

过程保留原train/诊断留出条数、统一SFT参数、AVG64固定身份；AVG16只作辅助压缩。TIES真实层SVD64回投影误差30%-57%，该近似未导出，Dense完整权重已导出并验收，BF16相对更新误差10.53%；不声称任务方法对照已完成或与r64同参数化容量。已完成20个真实失败/3项后续实验，剩余清单修正为完整评分、TIES任务对照、最终成本/离线资产。

本次按[PDF技能](</Users/caoqinlu/.codex/plugins/cache/openai-primary-runtime/pdf/26.1013.11914/skills/pdf/SKILL.md>)在首次编辑前成功运行edit marker一次。实际使用本机Arial Unicode字体生成嵌入式TrueType子集，不另分发字体文件。

```bash
/Users/caoqinlu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/render_progress_report.py
/Users/caoqinlu/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm \
  -png -r 140 output/pdf/progress_report_20261017.pdf /tmp/apex-progress-report-0529/page
```

核验：pypdf重新打开为**1页A4**，摘要按汉字范围计182个中文字符、含标点共199字符；所有字符有glyph、ArialUnicodeMS子集存在FontFile2。PNG已实际打开目视，标题/摘要/4×6矩阵/HLE表/边界/页脚无重叠、缺字、截断或额外页。内容底部y161.59高于页脚。数字、来源时点及未完成状态均与收据相符；临时PNG仅在`/tmp`，没有额外实验。
