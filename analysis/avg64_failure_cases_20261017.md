# AVG64：20个已有效判错的描述性案例

取样快照：**2026-10-17 03:51:43 CST**（80已有终态；评分仍在滚动）。以下20例均为AVG64：Terminal/SWE逐项native reward为0且owner未标invalid；HLE为`evaluation_status=judged`且`correct=false`。未用pending、未评分或invalid凑数。原始结果与队列均未改动。

## 取样规则与解释边界

- 描述性分层配额：10个不同Terminal任务（任务内先取最小seed）、8个HLE文本题、1个HLE图像题、1个SWE任务；每层按固定task ID/key字典序取最前项。本轮选中Terminal均为seed0。配额为兼顾类型，不是随机样本，也不估计失败率。
- 取样扫描时可用：Terminal18个有效零分trial/18个不同任务；HLE44个文本、2个图像已判错；SWE1个有效零分。汇总文件与单项评分是滚动写入，逐例有效性以已保存单项为依据，不把这些数量当完整benchmark分。
- **20例同ID Base也均为0/判错，其中5个HLE Base为native_no_answer。** 这不是20例“合版相对Base退化”，也不能据此归因LoRA干扰、rank或训练数据。Base对照只说明这次固定条件下的并列现象。
- Terminal10例中8例有工具observation里的真实DNS/下载错误，9例solver约1800秒后终止；按已有效native0收录不代表没有环境/资源混杂。9个HLE样本均stop结束、7到1528输出tokens，不能称为长度截断。
- HLE沿用已披露的替代Judge；下面复述其固定判错，不独立裁决所有学术命题、法律史或图像算法。事实证据强与机制解释强分开标注。

完整来源与有限审计字段见[小JSON](source_snapshots/avg64_failure_cases_20261017.json)，以`cases[].case_id`对应下面编号。所有source绝对路径属于主机80；正文路径均相对`P=/data/caoqinlu/projects/apex-takehome`。Terminal每例native结果的同目录`verifier/test-stdout.txt`与`agent/trajectory.json`是测试/动作来源；JSON另保存Base同ID的精确source。没有复制完整题面、整批gold或完整模型轨迹，仅保留必要的短答案差异。

## F01 · TERMINAL · adaptive-rejection-sampler/seed0

**采样器实现与测试产物未完成。** 9个原生测试失败，包含函数/样本文件缺失；末尾仍在安装R。solver约1800.72秒后AgentTimeout。

可能原因与证据强弱：实际工具observation含Ubuntu源DNS失败；依赖获取与重复安装占用预算可能影响交付。不能据此分离环境、策略和能力影响。 **中：有工具网络错误和缺产物直接证据，因果份额未隔离。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/adaptive-rejection-sampler__seed0/result.json`。

## F02 · TERMINAL · bn-fit-modify/seed0

**DAG及干预/采样CSV未交付。** 9个测试失败，多项为目标文件不存在；最后两轮重写DAG枚举，agent自述cycle checking/变量复用有bug。约1801.40秒超时。

可能原因与证据强弱：轨迹同时有pgmpy/numpy下载DNS错误；算法重写和依赖受限均可能贡献。Base同ID也0，但其可见失败集中于DAG/干预数据断言，不能把两者说成完全相同轨迹。 **中：缺文件与重写可见；不能确定单一根因。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/bn-fit-modify__seed0/result.json`。

## F03 · TERMINAL · break-filter-js-from-html/seed0

**自称验证成功，原生浏览器判据未满足。** agent两次mark_task_complete并声称自测exit0；原生test_out_html_bypasses_filter却未检测到alert，334.09秒正常结束，native0。

可能原因与证据强弱：本地自测成功与官方端到端判据不一致，可能缺少对过滤后浏览器行为的可靠验证；未重放页面，具体浏览器机制不作断言。 **强于现象、机制中：原生断言与agent自述直接冲突。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/break-filter-js-from-html__seed0/result.json`。

## F04 · TERMINAL · build-cython-ext/seed0

**Cython扩展与导入不可用。** 原生9 failed/2 passed；多个扩展测试报ModuleNotFoundError。末尾仍搜索Cython/缓存包，约1801.27秒超时。

可能原因与证据强弱：工具observation直接记录Cython获取DNS失败；构建依赖与仓库准备未完成是明显混杂，不能把0分单独解释为代码合版退化。 **中：依赖错误和缺扩展均直接可见，未隔离环境影响。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/build-cython-ext__seed0/result.json`。

## F05 · TERMINAL · build-pmars/seed0

**源码来源与可执行程序均未满足。** 4项测试失败，包含pmars不可用、未找到要求的源码目录及来源检查；末尾还在查apt source元数据，约1800.76秒超时。

可能原因与证据强弱：下载/源码定位过程出现真实DNS错误，可能阻止构建交付；没有独立证据证明换模型即可成功。 **中：源码与程序缺失为强事实，策略与网络根因未分离。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/build-pmars__seed0/result.json`。

## F06 · TERMINAL · build-pov-ray/seed0

**渲染器和指定版本源码缺失。** 3个测试失败；/usr/local/bin/povray和/app/povray-2.2均不存在。末尾继续调整DNS相关环境，约1801.16秒超时。

可能原因与证据强弱：archive.org等访问的工具observation含Could not resolve host；源码获取受限与预算耗尽共同出现，不能确定是算法或合版能力失败。 **中：缺产物与网络错误直接存在，模型因果弱。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/build-pov-ray__seed0/result.json`。

## F07 · TERMINAL · caffe-cifar-10/seed0

**训练配置/模型与训练日志未产出。** 6个测试失败，含Caffe源码/版本、模型、配置、500次迭代完成及准确率验证；约1801.32秒超时。

可能原因与证据强弱：wget/pip/apt相关observation有DNS失败，末尾仍搜本地缓存源码；该受限环境中的准备失败不能与训练算法错误混同。 **中：缺失检查强，独立模型原因未识别。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/caffe-cifar-10__seed0/result.json`。

## F08 · TERMINAL · chess-best-move/seed0

**棋盘识别未走到落盘棋步。** 原生test_move_correct因/app/move.txt不存在失败；末尾仍在分析棋子像素轮廓，约1802.04秒超时。

可能原因与证据强弱：视觉到符号棋盘的转换未完成；工具中也出现python-chess获取失败。只能认为两条困难同时出现，不能确认哪条是决定性原因。 **中偏弱：输出缺失强；视觉识别和依赖影响的解释未隔离。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/chess-best-move__seed0/result.json`。

## F09 · TERMINAL · circuit-fibsqrt/seed0

**电路文件形式通过，函数行为不对。** 门文件存在与大小检查通过，test_sqrt_fib失败（1 failed/2 passed）；agent自述先前generator复杂且有bug并重写，约1801.70秒超时。

可能原因与证据强弱：更接近电路生成/算术逻辑或未完成重写的问题；未独立模拟电路，不能确定具体信号或公式错误。 **中：形式/行为分离和重写均可见，具体逻辑根因弱。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/circuit-fibsqrt__seed0/result.json`。

## F10 · TERMINAL · code-from-image/seed0

**图像到执行结果的链路未完成。** 2个测试失败，/app/output.txt未生成；末尾仍将RGB转文本并尝试图像工具，约1800.88秒超时。

可能原因与证据强弱：图像读取/OCR工具路径未完成，Pillow安装亦有真实DNS失败。不能把它仅归因于推理错误或仅归因于网络。 **中：缺文件与工具记录直接可见，根因混杂。**

Base同ID有效native0；不支持合版独有失败的结论。

主判分来源：`artifacts/eval/avg64_terminal_full445_20261017/trials/code-from-image__seed0/result.json`。

## F11 · HLE · 668825f80a642802bdfeadfa

**人口伦理条件映射。** 答复选择Non-Elitism；替代Judge按参考选项判错。完整stop结束，648 tokens。

可能原因与证据强弱：可能混淆不可能性定理中的条件映射。未独立核对原理论，不能将知识错误进一步定位为合版干扰。 **弱：判错有效，领域根因仅为假设。**

Base同ID亦被Judge判错。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/668825f80a642802bdfeadfa.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/668825f80a642802bdfeadfa.json`。

## F12 · HLE · 6696c3734c196f1af6a16fcb

**特殊数域上的椭圆曲线分类。** 最终回答16，Judge参考为不同数值18；stop，694 tokens。Base同题为native_no_answer。

可能原因与证据强弱：回答援引分类结论但数值不匹配，可能是特殊数域知识/分类边界混淆；未独立复核所引文献。 **弱：数值不符直接可见，理论原因未证。**

Base同ID为native_no_answer、固定0分。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/6696c3734c196f1af6a16fcb.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/6696c3734c196f1af6a16fcb.json`。

## F13 · HLE · 66b727d367968fa27f2dddda

**Gamma矩阵缩并的符号/项。** 输出(d-2k)(d-2k+1)，Judge记录的参考为-(d-2k)^2+d，两表达式一般不等价；stop，524 tokens。

可能原因与证据强弱：可能在换序/缩并中丢失符号或项；这来自回答推导与参考差异，未逐步重证Clifford代数。 **中：代数表达式差异强，具体推导错误位置未证。**

Base同ID为native_no_answer、固定0分。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66b727d367968fa27f2dddda.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66b727d367968fa27f2dddda.json`。

## F14 · HLE · 66ba5510db07a3a9151be0d2

**特定算子的函数空间归属。** 以通用阶数迁移论证给出A^(1+alpha)，Judge参考A^(alpha-)；stop，194 tokens。

可能原因与证据强弱：可能把一般算子阶数直觉套到题设特定映射性质。未独立证明该解析命题。 **弱：答案空间不一致明确，数学根因尚未复核。**

Base同ID亦被Judge判错。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66ba5510db07a3a9151be0d2.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66ba5510db07a3a9151be0d2.json`。

## F15 · HLE · 66e70c75bbb9b1754c0869ce

**法规名称记忆错误而非输出格式。** 仅7 tokens直接给出Contracts (General Part) Law，Judge参考为另一法规Sale Law；stop，非截断。

可能原因与证据强弱：更像知识检索/历史先后混淆；答案长度与格式不足以解释该名称差异。这里只复述固定Judge，不提供法律意见。 **中：实体名称差异直接可见，历史原因不重判。**

Base同ID亦被Judge判错。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66e70c75bbb9b1754c0869ce.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66e70c75bbb9b1754c0869ce.json`。

## F16 · HLE · 66e883265ab37f0a7da089be

**棋局可达性中以常见顺序支持必要结论。** 回答选择A；其论证使用redundant/unlikely与最直接解释，Judge参考为C；stop，1481 tokens。

可能原因与证据强弱：可能用常见发展顺序替代严格可达性/必要性证明。未独立验证两局面合法序列，保留为可能原因。 **中偏弱：推理措辞可见，正确棋理未独立复核。**

Base同ID为native_no_answer、固定0分。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66e883265ab37f0a7da089be.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66e883265ab37f0a7da089be.json`。

## F17 · HLE · 66e884515ab37f0a7da089bf

**游戏缩写/领域消歧。** 回答引入Warcraft III语境并给出Harpy；Judge目标答案为Shuriken；stop，194 tokens。Base也曾引入另一游戏语境而判错。

可能原因与证据强弱：可能未正确消歧BAR而串入其他游戏知识。文本显示跨语境引用，但本报告不额外查游戏资料。 **中：回答的语境迁移直接可见，触发原因未知。**

Base同ID亦被Judge判错。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66e884515ab37f0a7da089bf.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66e884515ab37f0a7da089bf.json`。

## F18 · HLE · 66e8967ae99ca52dd4b94441

**软标签原型数问题的约束简化。** 回答以每类至少一个原型为必要条件而得C；Judge参考D+1；stop，1528 tokens。

可能原因与证据强弱：可能将软标签/几何构造问题简化为每类独立代表。未重新证明最小性结论。 **中偏弱：额外必要性假设可见，定理未独立复核。**

Base同ID为native_no_answer、固定0分。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66e8967ae99ca52dd4b94441.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66e8967ae99ca52dd4b94441.json`。

## F19 · HLE · 66e932f00bd16d40d4bc4d81

**图像伪码到递归复杂度的解释差异。** 图像题回答按其转写的T(n)=2T(n-1)+O(1)选择指数阶E，Judge参考多项式阶D；stop，1405 tokens。

可能原因与证据强弱：可能是视觉转写或递归/分支语义理解偏差；未对原图做独立重读，因此不能断言是视觉模块错误。 **弱：判错与其递推式直接可见，视觉/推理根因未分离。**

Base同ID为native_no_answer、固定0分。

主判分来源：`artifacts/eval/avg64_hle2500_20261017/scoring/results/66e932f00bd16d40d4bc4d81.json`。
固定答卷来源：`artifacts/eval/avg64_hle2500_20261017/questions/66e932f00bd16d40d4bc4d81.json`。

## F20 · SWE · instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e

**只读定位阶段退出，目标图像清理修复未交付。** fresh replay无exception、native reward0；311个required中307通过，4个图片/cover清理相关required未通过。生成mini轨迹25个bash工具调用全是find/ls/cat/grep读取，随后exit_status=BadRequestError。

可能原因与证据强弱：模型尚在定位代码时退出，未见实现目标修复的写操作。捕获patch仅删除5个无关文件，删除来源未经本次审计证明，不能归为模型主动破坏；BadRequestError的具体拒绝层/原因此次未独立定位。 **中：测试/只读动作/未实现修复直接可见；退出根因与删除来源弱。**

Base owner同ID亦记0；其独立审计保留307/311通过及原始缺reward，不能改称该Base原始native reward0。

主判分来源：`artifacts/eval/avg64_swe_hard51_20261017/replay/instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e/result.json`。
轨迹/patch来源：`artifacts/eval/avg64_swe_hard51_20261017/generation/instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e/agent/mini-swe-agent.trajectory.json`；同目录`model.patch`。

## 这批案例能支持什么

可直接支持的现象包括：受限准备/工具链与缺产物共同出现；本地自测通过不等同官方行为通过；文件形式合规不等同函数正确；单轮知识/数学/语境解释错误可以在短而完整的回答中出现；SWE读代码定位尚未实现修复即退出。它们为后续完整结果报告提供案例，不构成新的主分、因果机制证明或模型选择依据。

## 三项后续实验建议（未执行）

以下是独立后续研究设计，不在本轮恢复task-val、不改变冻结AVG64或根据正式题成绩选配方。

| 实验 | 可证伪假设与控制 | 主要判据 |
|---|---|---|
| 环境与准备成本分离 | 在新的开发任务上，交叉比较固定断网且完整预置依赖、固定public网络；同模型、任务、CPU/RAM/时限与工具接口。若依赖供给是主要因素，应同时减少安装失败、准备耗时与缺产物，而非仅改变退出状态。缓存只含依赖/源码，不含参考答案或目标产物。 | 官方任务成功率、准备时间占比、运行故障率和成本；不能把旧0重标为成功。 |
| 最终交付监督 | 相同训练token、基座、rank与步骤，对照原轨迹SFT和增加真实产物检查/交付收尾的轨迹SFT；检查必须来自教师实际执行，不复制自称成功。用于检验F01–F10/F20中的未交付与“自测成功”问题。 | 新任务的官方成功率、正确产物交付率、自称成功但官方失败率；loss仅诊断。 |
| 等容量合版比较 | 同数据与训练token下增加rank64 Mixed，对照精确AVG64；再在共同rank16预算比较Mixed16与固定AVG16。预先固定配方与评测范围，区分专精组合收益、额外参数容量和SVD压缩效应。 | 完整目标任务成绩、同ID配对差值/簇bootstrap CI、各域退化及推理成本；不凭单项HLE推广四域结论。 |

本次仅新增本文及小JSON。无模型/API/判分/程序或容器执行，无大文件hash扫描，无资源、原始结果、Base、队列、Git或claud修改。
