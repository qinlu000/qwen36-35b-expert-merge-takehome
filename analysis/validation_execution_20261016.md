# 已完成专家的实际 validation

2026-10-16 23:05 CST。独立推理与持久化验证队列已部署。用户随后取消SWE独立val，并明确只跑训练完成的SWE专家最终benchmark，复用已有Base结果；没有重训或重复跑SWE Base。

## 本次比较

| 验证任务 | 每模型题数 | 比较权重 | 实际状态 |
| --- | ---: | --- | --- |
| HLE 代理验证 | 100 | Base、HLE checkpoint16、checkpoint250 | Base已完整完成，之后的权重顺序接续 |
| SWE 留出任务 | 100 | 取消执行 | 0模型请求；控制器和镜像进程已退出，记录保留 |
| ASI 代理验证（SAB） | 20 | Base、ASI checkpoint128 | 科学依赖已就绪，生成及独立执行队列已部署 |

HLE和SAB是既有训练外留出任务，不是四项正式benchmark的完整评测。HLE为41题数学和59题MMLU-Pro选择题，不能声称等同正式HLE难度。ASI实际留出只有20题，不补入训练题凑100。Terminal新训练尚未完成，本轮未将其列作已完成专家。SWE改为专家checkpoint249直接跑固定最终51题，不用该测试集反复调参或挑checkpoint；Base由另一会话正在收尾，直接复用，不再生成。

22:56:50，HLE Base代理验证100题全部终态：62份完整答卷、38份本地300秒deadline无完整答卷，54正确；已答卷正确率54/62=87.10%（存在按能否及时回答的选择偏差），预算限定成功率54/100=54.00%。Math7/41、MCQ47/59；无生成基础设施错误、无Judge失败。这不是正式HLE成绩，也不是训练效果比较，须等16和250采用同配置完成。

## 服务与执行

- HPC job727113，ACD1-24，2H100，BF16/TP2；Base和四份LoRA均通过实际生成验收，SWE工具调用通过。完整620张A/B权重的层号和投影覆盖已核对，没有发现被忽略权重；未做逐层PEFT merge数值等价测试。
- 所有真实请求保持64K上下文、8K输出、关闭thinking，按模型块依次运行。80独立桥为127.0.0.1:28089，不重启现有Base服务。
- HLE和SAB生成、评分分开保存；求解输入不含金标、checker或参考程序。HLE与SAB评分各设¥10上限。
- 已取消的SWE100题及首题gold验收保留，仅是历史准备记录，不计任何模型成功率。取消发生在0模型请求时。
- SWE专家最终51题将复用正式缓存与当前Base修复环境，独立输出；只调用apex-val-swe249。独立CPU释放监控在旧Base及repair队列排空、所有相关CPU scope退出后放行：SWE用0–15，SAB用112–115。未凭GPU退卡标记抢占CPU。
- SAB采用离线生成后执行，扣除生成耗时的1200秒预算；排队时间另记。它是Base与专家相同的分段代理验证，不能冒称正式ASI连续walltime协议。
- 服务实际于10月17日10:05:32 CST到期，Slurm拒绝延长。SWE专家最终队列同样须在09:30:32后停止准入新求解，已有任务与CPU评分自然结束，剩余项保留pending，不能转换成模型0分。

22:36的direct持久进程为独立隧道4182990、模型块4183881、HLE评分4183925、SAB执行576253、CPU释放553293。SWE独立val最后控制器750633及4个镜像进程组已于22:58:58按用户要求退出；取消标记阻止原输出目录再准入。PID仅是本次启动回执，不用作可重复启动命令。

## checkpoint16与重训判断

当前HLE726664连续完成250步；第16步正常验证后保存checkpoint16，之后继续训练至250，最终COMPLETED/0:0，没有OOM或resume记录。第16步OOM的是Terminal726345，且那次没有保存checkpoint。旧500条HLE也正常训完63步，同时出现后期val loss上升。

因此不因“16”这个编号重复原配方训练。先比较Base、checkpoint16、checkpoint250的真实正确率，再决定是否调整监督格式或学习率。当前尚无完整生成准确率；不将部分题或teacher-forcing loss作为最终能力结论。超时、服务/环境失败及评分失败分别保留原始记录与归因。

22:37抽查的3条HLE未答卷均为本地300秒deadline，tokenize成功，但没有完整response/usage，不能称8K输出正常截断。同期服务整体健康、Running8/Waiting0；正常答卷约10token/s/题，慢decode最吻合现象，仍缺少超时逐题对应的服务请求证据。最终应分列已答题正确率、deadline无答卷及预算限定成功率，不能把未答卷说成judge判错，也不能用当前部分题断言HLE权重退化。

## 详细记录

- [HLE checkpoint来源核对](hle_checkpoint16_origin_20261016.md)
- [HLE与SAB执行、评分及限制](validation_direct_execution_20261016.md)
- [SWE独立val准备及用户取消记录](validation_swe_execution_20261016.md)
- [SWE取消回执](source_snapshots/validation_swe_cancelled_20261016.json)
- [推理服务及LoRA验收](validation_serving_plan_20261016.md)

80结果目录为 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/validation_direct_20261016/` 与 `validation_swe_20261016/`。原始请求、响应、usage、时长、程序、测试日志和逐题判分持续写盘，之后据完整覆盖率汇报。
