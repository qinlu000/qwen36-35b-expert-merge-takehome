# Qwen3.6-35B-A3B：4 H100 的上下文与请求容量估算

更新：2026-10-16。**从固定模型结构看，4卡不构成必须把262,144上下文降到131,072的显存依据；TP2/TP4、并发1/2/4均值得按实际容量检查。**下表只是权重与逻辑状态的估算，不能证明某个设置已跑通或达到所需吞吐；2/4活跃请求是验收档位，不是已确定的最终并发。

## 固定输入与实际边界

- 模型revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；发布张量合计71,903,645,408 B，即 **66.9655 GiB**。35B总参数都要存放，3B activated不意味着只加载3B。理想均分：TP2每卡33.4827 GiB，TP4每卡16.7414 GiB；实际模块复制、分片对齐及未加载的可选模块会改变占用。[固定config](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/config.json)、[本地固定config](source_snapshots/model_config.json)
- 固定config是40层，**10层full attention、30层linear Gated DeltaNet**；full层2个KV头、head_dim256；BF16 KV。不能按40层全部常规KV计算。
- HPC现装vLLM **0.20.2**、Torch2.11/cu130；723693已有日志实测两卡为 **H100 80GB HBM3，各81559 MiB = 79.6475 GiB**，驱动610.43.02。四卡下一次实际分配仍需核型号/可用显存；不假设正好80 GiB。[当前runtime状态](setup_base_runtime_status.md)
- 723693在架构inspection阶段失败，尚未加载权重；修复缓存路径后的723706在本轮可见文档中仍待结果。本轮读取HPC现有summary只找到723693失败回执，**没有GPU加载、HTTP或长上下文成功证据**。未启动任何作业/模型/请求。

## TP2和TP4为何每卡KV相同

vLLM的full-attention实现：TP超过KV头数时复制KV头，`num_kv_heads = max(1, 2 // TP)`。所以TP2和TP4每卡均有1个KV头，TP4不能把这部分每卡显存再减半；TP4的主要空间收益来自权重更充分分摊。[固定vLLM实现](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/model_executor/models/qwen3_next.py#L210)

每卡full-KV字节数 = `10层 × 2(K,V) × 1个KV头 × 256 × 2字节 × 总序列tokens × 活跃序列数`，即 **10,240 B/token**。没有计入视觉激活、linear state、pool padding、CUDA graph、prefill/decode激活或通信workspace。

| 每序列总上下文 | 活跃请求 | 每卡full-KV（TP2/TP4相同） | TP2理想权重+full-KV/卡 | TP4理想权重+full-KV/卡 |
|---:|---:|---:|---:|---:|
| 131,072 | 1 | 1.25 GiB | 34.73 GiB | 17.99 GiB |
| 131,072 | 2 | 2.50 GiB | 35.98 GiB | 19.24 GiB |
| 131,072 | 4 | 5.00 GiB | 38.48 GiB | 21.74 GiB |
| 262,144 | 1 | 2.50 GiB | 35.98 GiB | 19.24 GiB |
| 262,144 | 2 | 5.00 GiB | 38.48 GiB | 21.74 GiB |
| 262,144 | 4 | 10.00 GiB | 43.48 GiB | 26.74 GiB |

按已见79.6475 GiB卡和候选 `gpu_memory_utilization=0.85`，vLLM目标预算约 **67.70 GiB/卡**；这不是可用KV额度，需先扣实际权重、非Torch占用及profile峰值。最重的表内262K×4档，理想权重+full-KV后仍有约24.22 GiB（TP2）/40.96 GiB（TP4）的目标预算差额，**不能全部视为安全余量或可增加并发的额度**。

## 30层linear state与框架分配

vLLM固定实现从config取16个K头、32个V头、K/V head_dim128、conv kernel4；SSM cache根据该模型的 `mamba_ssm_dtype` 保持FP32，conv state按BF16估算。单层每份state的元素量为：conv `(8192/TP)×3`，recurrent `(32/TP)×128×128`；不是随历史长度保存每token的40层KV。[state shape/dtype计算](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/model_executor/layers/mamba/mamba_utils.py#L213)、[Qwen dtype配置处理](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/model_executor/models/config.py#L606)

全部30层、每个活跃序列每份逻辑state约 **30.70 MiB/卡（TP2）或15.35 MiB/卡（TP4）**。`none`模式约一份，`align`工作状态按两份估为61.41/30.70 MiB；并发乘以序列数，speculative decoding会另加state，本次估算未启用。Qwen3.5实现不支持`all`模式，不能把其他Mamba模型的全token state缓存设置照搬。[MambaSpec内存逻辑](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/v1/kv_cache_interface.py#L521)、[Qwen模式约束](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/model_executor/models/qwen3_5.py#L470)

上述只是**逻辑活跃state**：hybrid cache manager需统一page大小、对齐和group pool，padding、保留的prefix状态、分配器及预留缓存都可能提高物理占用。不能将30层linear state完全忽略，也不能简单加完这几十MiB就宣称得到了最终GPU占用。vLLM通常预分配缓存池，NVML占用也不会等于当前活跃请求的逻辑KV；应看启动报告的实际缓存容量和运行时cache占用。[固定hybrid分组/内存池源码](https://github.com/vllm-project/vllm/blob/v0.20.2/vllm/v1/core/kv_cache_utils.py#L1052)

发布权重已包含视觉部分，权重表没有额外再加一次完整vision权重；真正额外要检查的是视觉激活/encoder cache及多模态profile、chunked prefill workspace、MoE路由/通信、CUDA graph和其他进程显存。现有eager smoke不代表启用graph的正式设置；85%util和chunked prefill8192仅候选。chunk8192是调度时一批prefill tokens的上限，不是把上下文改成8192，也不会删除历史KV。

## context包括输入和输出

`max_model_len`是**完整输入（含system/tool模板、历史和图像tokens）+实际生成**的总长度，既不是另给同样长的输出，也不是每次tool调用重新累计一份独立总预算。每次请求还须保证输入tokens加本次requested max_tokens不超限，必要时由agent做原生摘要或动态clamp，不能等服务返回400后静默丢任务。

| 单次输出上限 | 131,072上下文最多给输入 | 262,144上下文最多给输入 |
|---:|---:|---:|
| 81,920 | 49,152 | 180,224 |
| 32,768 | 98,304 | 229,376 |
| 8,192 | 122,880 | 253,952 |

这些输入额度仍含所有模板及视觉tokens；原生摘要请求本身也要留空间。上限不意味着每轮都会生成到该长度。TB题面256K不应仅凭名义4卡就预先缩减；若以后确需降低，须按已确认评测口径披露，而不是称作原配置。[固定模型卡及官方部署说明](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)

## 必要验收，控制在少量合成检查

1. 先看现有smoke真实结果；确认分配GPU总/可用显存、实际权重占用、cache dtype/mode、HMA、block size和可用KV容量，不重跑已经通过的短文本/图片/tool检查。
2. 在最终选用TP上，从单活跃长请求开始，用合成输入验证接近131K/262K总长度时短输出、tool往返，以及动态输出预算；仅当需要对应并发时再增加到2和4个活跃请求。记录OOM/preemption、cache占用、prefill首token延迟和decode吞吐，而非只看HTTP健康。
3. 带代表性合成图像复核同一服务的视觉额外峰值；若正式启用CUDA graph，再按最终设置补一次峰值检查。按观察到的余量选择服务并发与agent摘要阈值，保证同benchmark所有模型使用同一冻结政策。

当前结论限于**结构和容量估算**；不承诺TP2/TP4吞吐优劣、不将2/4活跃请求定为最终并发，也未改变协议/配置。
