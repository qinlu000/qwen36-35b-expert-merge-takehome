# Terminal 未评分项说明

21:28 的固定快照为204项有效、30项在途、177项待准入、34项终态但无有效评分，总分母仍为445。`infrastructure_unscored` 是这最后一组的历史字段名，不能据此断言34项都是基础设施故障。

| 原运行未得到有效评分的原因 | 项数 |
|---|---:|
| 求解阶段结束后，80服务器的 `/tmp` 写满，官方测试或评分资源无法复制进沙盒 | 25 |
| 评分依赖下载失败：pytest、CUDA wheel、TLS握手等，测试没有真正执行 | 3 |
| 官方评分已启动，但超过900秒评分预算 | 2 |
| tmux终端会话提前结束 | 2 |
| 求解进程清理未获确认，运行器拒绝切回公网评分 | 2 |
| 合计 | 34 |

30项顶层结果显示AgentTimeout，4项显示RuntimeError。正常1800秒预算结束本身可以有效计分：同一轮已接受过114个超时0分、6个超时1分。这里缺的是有效评分，不能仅凭超时猜0分。原日志还记录了顶层超时之后的AddTestsDirError，摘要只看顶层异常会漏掉真正的评分失败原因。

两项tmux中，qemu-alpine-ssh的轨迹记录了模型发送Ctrl-D、shell退出，随后会话消失；另一项large-scale-text-editing的会话消失原因尚不明确。因此也不能把这两项统一称为网络故障。

恢复条件与原始错误是两个维度：34项中7项有文件归档、27项没有。7项内5项已经完成仅评分的原生测试，但需核实归档是否完整覆盖评分依赖的文件/状态后才能采纳；1项configure-git-webserver缺少Nginx配置和服务状态，恢复被阻止；另1项model-extraction补评分仍超时。缺归档的任务不能直接在全新环境中评分，也不能把重新求解冒充原答案恢复。

本轮5项审核已完成：merge-diff-arc-agi-task/seed0、torch-pipeline-parallelism/seed0、break-filter-js-from-html/seed0的归档覆盖评分所需候选状态，已有原生0分可以采纳。make-doom-for-mips/seed1在原求解时修改过未归档的`/etc/apt`文件，rstan-to-pystan/seed1修改过未归档的`/etc/hosts` PyPI映射，均保持未评分。rstan的原TLS失败与这项域名映射修改有关，不能统一称为外部网络事故。未重新运行模型或测试，也没有手改分数。

因此原34项现有3项恢复有效评分，剩余31项为27项无归档、3项外部状态不完整、1项补评分900秒超时。巡检期间又有原集合外的pytorch-model-cli/seed2触发900秒评分超时，实时未评分总数需以最新summary为准，不能把这个新项混入上述固定34项根因分类。

常驻补评进程仍在，21:28时已执行43次历史补评尝试、当前空闲；它只处理有可用归档的任务，并不是34项都还在其待跑队列。33增至34来自rstan-to-pystan/seed1：20:24求解预算结束后，评分依赖下载发生TLS握手失败，包装器写出的0未被当作有效模型分数。

逐项证据：`analysis/source_snapshots/terminal_unscored_audit_20261016_current.json`；独立分类复核：`terminal_unscored_classification_20261016.json`。本轮未运行新模型、任务测试或重生成答案；只对既有评分结果补做原状态充分性审核。
