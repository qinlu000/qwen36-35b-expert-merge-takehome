# CMOS科学评分import恢复准备（未执行评分）

本轮按[diagnosing-bugs技能](/Users/caoqinlu/.codex/skills/diagnosing-bugs/SKILL.md)建立精确导入反馈环。[只读准备脚本](../scripts/prepare_asi_import_recovery.py)和[单条件恢复/未来runtime安装wrapper](../scripts/grade_asi_import_recovery.py)已同步80；[固定输入/cache及选择收据](source_snapshots/asi_cmos_import_recovery_prep_20261017.json)包含实际默认入口检查。两个脚本本轮都只准备；没有执行评分、候选代码、模型/Judge请求或生产runtime安装，原239有效+1异常报告、答卷和marker均未改。

## 已复现的原因与最小修复

在80实际asi-py312解释器、项目cwd、CPU92，临时非阻塞领取已有92–95全局lease后运行精确语句：

```python
from tasks.electrical_engineering.cmos_opamp_design import cmos_eval_runtime
```

07:05:17仅`PYTHONPATH=<original scoring/runtime>`时RED：`ModuleNotFoundError: No module named 'tasks'`。排序假设为缺ASI repo root、缺实际模块/依赖、同名包冲突；仅追加冻结`artifacts/benchmarks/asi`后07:05:26 GREEN，实际`module.__file__`正是原repo的cmos_eval_runtime.py，支持第一个原因而排除另两项。可重复命令：

```bash
python3 scripts/prepare_asi_import_recovery.py --project /data/caoqinlu/projects/apex-takehome --probe-imports
```

该脚本再次通过RED/GREEN及临时sitecustomize GREEN，所有probe先禁止socket connect，只导入模块，不运行native evaluator或候选。lease随probe退出释放，未写生产runtime。未来最小预防是在评分前做这条纯import检查，无需任务级val。

## 原字节与paid缓存

固定条件仅`electrical_engineering.cmos_opamp_design__seed31415__b1`。原source result为5925B，SHA256 `0515dfd5628e9c9d3b7f697a2497692a932e85983389b1939c80453271aa3608`；其solver原status=failed保持，不能借import修复重新生成。三个persisted outputs（simulation.py、opamp_netlist.cir、tran_testbench.cir，18,044/2,127/1,105B）当前SHA/大小**全部匹配generation时写入result的原记录**；workspace对应文件也吻合。后续应以稳定persisted目录为评分输入，不能重建/替换答卷。参数metadata、原条件评分record和原journal的小文件身份也已固定。

原`frozen_inputs`各hash因skip-hashes是null。因此不能声称全部reference/data拥有历史checksum证明；现有强证据是generation记录的三个输出checksum，以及准备阶段固定的原result/参数metadata等身份，后续恢复必须逐项前后复核。

该条件原paid cache为`scoring/judge_calls/<condition>.grading1/`，9个request与9个response均存在；9个request JSON按原transport的sort_keys/ensure_ascii=False规范hash均匹配文件key及occurrence。原15次paid调用中该条件9次，其余CMOS b2/b3各3次。直接运行原CLI `--retry-invalid`会把attempt1变成2、namespace变grading2，导致错过原cache，**不能盲目照用**；原CLI的selection也要求完整240条件，不适合直接冒充单条件恢复。

可复用的是原request hash/occurrence对应的既有response。仅import成功不能证明重建native流程每个后续prompt均相同：修复后新增analytic metadata可能改变prompt。root已审核采用一次native恢复：将9对cache原字节复制到独立恢复输出的**grading2** namespace，既有hash+occurrence命中直接复用；原grading1缓存不动。新native步骤确需的新prompt允许首次Judge调用，所有`started/completed/failed/cache_reused`追加到**原scoring/judge_calls.jsonl**，共用已有15次调用/原reserved和396次、20元总上限。没有新增独立20元额度。已有同logical condition/hash/occurrence的started请求即使跨grading namespace也拒绝重发；unknown不自动重试。原journal旧字节前缀须逐字节保持，仅允许append。这取代早期cache-only提案，不先执行一次cache-only评分。

## 待审核的once grade-only固定方案

1. 仅选择收据中该b1原result及同三个persisted outputs，源字节与原条件record保持；不读取奖励作选择，不重生成，不修改另外239项。
2. 使用原native `_prepare_score_jobs`/worker/evaluator、原任务/参数/instance、原ngspice和submission runtime，修复仅为import路径。独立输出固定`artifacts/eval/asi128_asi240_20261017/import_recovery_20261017/`，新cache namespace固定`<condition>.grading2`。独占目录claim防止不确定结果后再执行。
3. 获取原92–95 global grader lease，workers1，外层7200秒；原native CPU/内存/子程序wall budgets不变。严格只允许一次grade pass。不得另开与AVG未来grader重叠的owner。
4. 原9对cache复制并核byte identity；transport仅将journal根指向原scoring目录，原冻结reserve/flock预算逻辑原样复用。新增首次调用计入原预算，cache reuse不计为新消费。复制原invalid条件、完整原report/config/identity/journal、source与3个输出留完整备份。原cache、本体答卷和条件record不改。
5. 只写独立`native_result.json`和`receipt.json`；记录newcalls/cachereuses、原journal前缀SHA/bytes及不变、预算前后、源/原完整report/冻结runtime/criteria前后身份，以及相隔2秒的两次实际CPU92–95 scope交集为空。即使native抛异常也先在lease内等实际scope排空；失败claim保留，不自动再次评分。**不覆盖原report、条件record或allCPU marker**，由root独立审核是否纳入。

这是固定方案与原字节/cache准备，尚未恢复评分。wrapper默认仅prepare；只有显式`--execute`或`--install-avg-runtime`才分别进入评分或安装，两个flag互斥。原native evaluate的spawn/7200秒、worker/criteria/parser和子程序预算均不改。07:19:22最终实机默认入口、AST、3个输出/9对cache核验通过，actions为空；纯合成替身spawn检验通过（共享journal、跨namespace拒绝已started请求），没有native评测/API。`load_native`显式加入runtime根/scripts及原ASI repo root，父/子导入都禁止写pyc。额外纯import预检在禁止socket连接、仅probe采用LiteLLM本地costmap时成功载入实际冻结native/transport模块，没有调用evaluate。实际新prompt数和最终评分仍未知。

## 不打断AVG生成的后续评分环境方案

AVG coordinator1126014已加载旧代码，generator1126055在途；不能假设修改磁盘pipeline源码会热生效。07:17:01只读实核progress.state=running、pipeline.state=asi_generation，其中state.pid=1126055是**generator**（starttime ticks868933000，非zombie），并非coordinator；未来`avg64_asi240_20261017/scoring/runtime`、score-launch、generation-finished、安装receipt均尚不存在。CPU import已证明临时runtime首层sitecustomize追加repo root能在原runtime-only环境下GREEN。

root批准后可用**原全局grade_lock保护的完整预置**，无需停止任何在途PID：

1. 非阻塞获取现有92–95 global grade_lock；若已有合法owner，等其自然释放，不抢占。
2. 在锁内复制完整冻结scoring runtime到同目录的独立staging；核原文件bytes不变，仅新增sitecustomize.py，内容只将固定ASI repo root追加sys.path。
3. 目标runtime必须仍不存在，再将完整stage原子rename到未来runtime；禁止只创建一个空目录/单shim，因为旧parent看到目录存在就会跳过copytree。若目标已出现，停止准备并审实际状态。
4. 释放grade_lock。旧parent源码在取同锁之后才检查runtime/copy并构造PYTHONPATH和启动新解释器，所以它会见到完整runtime；新scorer及spawn worker启动时自动加载sitecustomize，不依赖parent热重载。生成进程不读取该未来runtime，保持运行。
5. 记录原文件一致性/新shim、CPU import GREEN和future child实际命令。保持workers1及7200/396/20等所有参数；不改全局asi-py312解释器、现有专家runtime、模型路由或GPU。

锁也封闭了“生成恰好结束、旧parent正在copy runtime”的竞态：安装者与旧parent共享原评分lease。当前锁为空，并已由import probe成功领取再释放；这不等于已安装修复，**仍待root审核后执行**。

root首次安装在rename前的树一致性assert安全失败，未激活target、未写安装receipt。精确原因是冻结runtime下`ai4sci_bench`为绝对目录symlink，默认copytree展开后stage多168项（源13个普通文件，stage181；同名文件0changed）。失败stage `runtime.stage-4090043b74204fd799640bc7c36c5a00`保留原样。现改为`copytree(..., symlinks=True)`，身份检查包括link文本、resolved target及目标内小源文件SHA。07:18:59持同global lease，在独立临时stage实际完整复制、仅加shim、禁止socket的纯import GREEN，source/link targets前后不变；临时stage清理、生产target未激活。此预检不是再次安装或评分。

## Root审后命令（本轮未执行flags）

```bash
# 默认只准备；已实际通过。
artifacts/envs/asi-py312/bin/python scripts/grade_asi_import_recovery.py --project /data/caoqinlu/projects/apex-takehome
# Root先执行未来runtime安装，再独立执行唯一native grade；保留原user bus环境。
artifacts/envs/asi-py312/bin/python scripts/grade_asi_import_recovery.py --project /data/caoqinlu/projects/apex-takehome --install-avg-runtime
artifacts/envs/asi-py312/bin/python scripts/grade_asi_import_recovery.py --project /data/caoqinlu/projects/apex-takehome --execute
```

执行环境应有原`XDG_RUNTIME_DIR=/run/user/1012`和`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1012/bus`；wrapper的唯一评分parent将自身affinity固定92–95，领取同原global lease，workers1，绝不触碰AVG生成96–127。安装独立receipt为`artifacts/eval/asi-import-fix-installation-20261017/receipt.json`；评分独立claim/output为上述`import_recovery_20261017`。

交付wrapper本机/80一致：17,817B，SHA256 `3e31c1e98676c5c7b0d59705c0a7166c868cb53f1821a8d6d2a480966f84421a`。本agent未执行两个生产flags，后续由root审核后执行。
