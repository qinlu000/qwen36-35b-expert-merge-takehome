# 一页阶段性中文报告草稿

产物：[progress_report_20261017.pdf](../output/pdf/progress_report_20261017.pdf)。这是阶段性草稿，不是最终`report.pdf`，没有替代完整正式评测、20案例或最终成本交付。

重画脚本：[render_progress_report.py](../scripts/render_progress_report.py)。只读仓库中已保存的训练、合版、249条loss-only、正式汇总、HF与GitHub收据，无网络、API、GPU或队列操作。固定4×6矩阵仅在某单项的原收据`complete=true`且有主分时显示数字；其他目标项为“待齐备”，非目标专家为“未评”。未用coverage推算主分；当前仅Base ASI完整240条件显示1.571%，宏平均/提升/CI仍待齐备。正式结果快照为2026-10-17 02:29 CST，页尾标明来源，不能当作实时进度。

同249条CE表从原回执读取：Base2.105976、AVG641.357921、AVG161.379223、Mixed8831.672463，明确不是benchmark准确率。页面同时披露Terminal缩减协议、替代Judge、模型容量和调度差异，并保留“完整有效评分 / 至少20个真实合版失败案例 / 最终成本”一行剩余项。

本轮使用[PDF skill](</Users/caoqinlu/.codex/plugins/cache/openai-primary-runtime/pdf/26.1013.11914/skills/pdf/SKILL.md>)，在首次authoring前成功执行marker一次。使用本机`/System/Library/Fonts/Supplemental/Arial Unicode.ttf`生成嵌入式TrueType子集，未依赖接收端CJK字体替换；不将系统字体文件另行分发。

```bash
/Users/caoqinlu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/render_progress_report.py
mkdir -p /tmp/apex-progress-report-20261017
/Users/caoqinlu/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm \
  -png -r 140 output/pdf/progress_report_20261017.pdf /tmp/apex-progress-report-20261017/page
```

`--output`可更换PDF路径，脚本每次写入实际北京时间；需ReportLab与pypdf，默认字体路径为上述mac字体。脚本没有安装依赖或复跑实验的步骤。

核验结果：本次生成时间 **2026-10-17 03:08:10 CST**；pypdf核实 **1页A4**。摘要按汉字范围`U+3400–U+4DBF/U+4E00–U+9FFF`计 **178个中文字符**，含标点共190字符，满足150–200中文字符。所有使用字符均有字体glyph；PDF两份ArialUnicodeMS子集均存在`FontFile2`，中文文本可正常提取。140dpi渲染至`/tmp/apex-progress-report-20261017/page-1.png`并已实际打开目视：标题、摘要、4×6矩阵、CE小表、协议和页脚均清晰，无黑方块、缺字、重叠、截断或额外页。

唯一owned提交文件为PDF、该重画脚本与本文。临时PNG仅在`/tmp`，未修改README、claud、共享日志、Base、配置或运行队列，未执行Git操作。
