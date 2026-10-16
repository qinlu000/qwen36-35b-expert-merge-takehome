# 已完成专家的实际 validation

2026-10-16 22:36 CST。本轮已部署独立推理与持久化验证队列，没有重训，也没有修改另一会话的正式 Base 评测。

## 本次比较

| 验证任务 | 每模型题数 | 比较权重 | 实际状态 |
| --- | ---: | --- | --- |
| HLE 代理验证 | 100 | Base、HLE checkpoint16、checkpoint250 | Base 已真实答题、评分，后两份顺序接续 |
| SWE 留出任务 | 100 | Base、SWE checkpoint249 | 首题源环境 gold 测试通过；下载镜像，等待 direct 生成块结束 |
| ASI 代理验证（SAB） | 20 | Base、ASI checkpoint128 | 科学依赖已就绪，生成及独立执行队列已部署 |

这些是既有训练外留出任务，不是四项正式 benchmark 的完整评测。HLE 为41题数学和59题MMLU-Pro选择题，不能声称等同正式HLE难度。ASI实际留出只有20题，不补入训练题凑100。Terminal新训练尚未完成，本轮未将其列作已完成专家。

## 服务与执行

- HPC job727113，ACD1-24，2H100，BF16/TP2；Base和四份LoRA均通过实际生成验收，SWE工具调用通过。完整620张A/B权重的层号和投影覆盖已核对，没有发现被忽略权重；未做逐层PEFT merge数值等价测试。
- 所有真实请求保持64K上下文、8K输出、关闭thinking，按模型块依次运行。80独立桥为127.0.0.1:28089，不重启现有Base服务。
- HLE和SAB生成、评分分开保存；求解输入不含金标、checker或参考程序。HLE与SAB评分各设¥10上限。
- SWE100题与当前SWE训练的仓库、任务交叉为0；与正式HARD51的11仓库精确交叉为0。首题公开gold在fresh sandbox中按原生源评分通过，仅是环境验收，不是模型成功率。
- SWE先CPU125单路。独立CPU释放监控在旧Base及repair队列排空、所有相关CPU scope退出后放行：SWE用0–15，SAB用112–115。未凭GPU退卡标记抢占CPU。
- SAB采用离线生成后执行，扣除生成耗时的1200秒预算；排队时间另记。它是Base与专家相同的分段代理验证，不能冒称正式ASI连续walltime协议。
- 服务实际于10月17日10:05:32 CST到期，Slurm拒绝延长。SWE在09:30:32后停止准入新求解，已有任务与CPU评分自然结束，剩余项保留pending，不能转换成模型0分。

22:36的持久进程均存活：独立隧道4182990、direct块4183881、HLE评分4183925、SAB执行576253、CPU释放553293、SWE控制器584499。PID仅是本次启动回执，不用作可重复启动命令。

## checkpoint16与重训判断

当前HLE726664连续完成250步；第16步正常验证后保存checkpoint16，之后继续训练至250，最终COMPLETED/0:0，没有OOM或resume记录。第16步OOM的是Terminal726345，且那次没有保存checkpoint。旧500条HLE也正常训完63步，同时出现后期val loss上升。

因此不因“16”这个编号重复原配方训练。先比较Base、checkpoint16、checkpoint250的真实正确率，再决定是否调整监督格式或学习率。当前尚无完整生成准确率；不将部分题或teacher-forcing loss作为最终能力结论。超时、服务/环境失败及评分失败分别保留原始记录与归因。

22:37抽查的3条HLE未答卷均为本地300秒deadline，tokenize成功，但没有完整response/usage，不能称8K输出正常截断。同期服务整体健康、Running8/Waiting0；正常答卷约10token/s/题，慢decode最吻合现象，仍缺少超时逐题对应的服务请求证据。最终应分列已答题正确率、deadline无答卷及预算限定成功率，不能把未答卷说成judge判错，也不能用当前部分题断言HLE权重退化。

## 详细记录

- [HLE checkpoint来源核对](hle_checkpoint16_origin_20261016.md)
- [HLE与SAB执行、评分及限制](validation_direct_execution_20261016.md)
- [SWE环境、原生评分及队列](validation_swe_execution_20261016.md)
- [推理服务及LoRA验收](validation_serving_plan_20261016.md)

80结果目录为 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/validation_direct_20261016/` 与 `validation_swe_20261016/`。原始请求、响应、usage、时长、程序、测试日志和逐题判分持续写盘，之后据完整覆盖率汇报。
