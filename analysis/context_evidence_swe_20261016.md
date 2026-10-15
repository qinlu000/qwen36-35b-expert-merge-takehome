# SWE-bench Pro：32K/64K/128K context 与 output 的网上证据

调研：2026-10-16，实际使用 ego-browser 阅读官方页面/图表，并以 web 搜索交叉定位；未运行题目、模型/API或GPU，未读取正式题答案。**32K总上下文能让Agent运行，但没有找到证明它足够覆盖本题V2 HARD-51的实测；最接近的Qwen3.6+mini复现反而显示32K明显受损。**

## 1. 最接近模型与harness的上下文曲线：有数字，但不是V2

在Qwen官方仓库的[issue #179](https://github.com/QwenLM/Qwen3.8/issues/179)，实验作者报告官方Qwen3.6-27B、mini-swe-agent、bash-only的实测：

| Agent working context | 作者报告pass@1 |
|---:|---:|
| 约32K | 约9% |
| 约64K | 约24% |
| 约81K | 约27% |
| 约114K | 约28% |

成功轨迹的peak context：**p90约67K、最大约113K**；200K配置在约100K附近开始收益趋缓。原帖后续另报告114K raw 27.8%、200K raw 31.3%，说明不能把首张近似表理解成稳定且严格单变量的统一消融结论。[原帖与后续更新](https://github.com/QwenLM/Qwen3.8/issues/179)

**适用边界：**这是旧版731题Pro public、27B模型、2小时预算、联网sandbox，且作者自报；不是Qwen3.6-35B-A3B、V2 HARD-51或当前离线50分钟协议。可支持“32K对Qwen+mini有显著风险、约100K更稳妥”，**不能预测本题会从9%变成28%，也不是官方对结果的背书**。原复现每turn `max_tokens`未设置，不能拿其32K working context当32K输出实验。

## 2. 真正V2的官方执行统计

Scale/Reflection在[2026-09-22官方V2发布文章](https://labs.scale.com/blog/swe-bench-pro-v2)报告GLM-5.3、Kimi K3、Inkling分别使用mini/Pi/OpenCode，覆盖全部642题、离线锁定预算；文章说明未施加有意义的turn/token硬限。下面数字从浏览器渲染的SVG label直接读取，**不是按柱图高度猜值**：

| mini-swe-agent模型 | 每题中位steps | 每题中位分钟 | 每题中位completion总量 | 每题中位prompt累计量 |
|---|---:|---:|---:|---:|
| GLM-5.3 | 61 | 13.2 | 26K | 2.20M |
| Kimi K3 | 48 | 15.6 | 27K | 1.70M |
| Inkling | 85 | 8.6 | 28K | 4.12M |

这些是**整题多次模型调用累加**的tokens；26–28K不是每turn output，1.7–4.12M不是瞬时context，不能据此要求百万上下文。它说明长多轮过程和反复prefill确实存在；该文章没有给Qwen、HARD-51单独轨迹长度或32K/64K/128K上下文消融。[同一官方文章第4节图表](https://labs.scale.com/blog/swe-bench-pro-v2)

## 3. 模型卡与代码真正规定的内容

- [固定Qwen3.6-35B-A3B模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)：SWE系列用**200K context**、内部bash+file-edit scaffold，并修订部分Pro任务；因此不是官方V2 HARD-51可比结果。模型卡建议OOM可降context、为保留思考能力建议至少128K；这不是非思考32K必败的定理，也没有提供各context得分消融。
- [本题固定V2 README](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)：**50分钟Agent预算**、离线和fresh replay；没有指定32K/64K/128K统一context，也没有证明某档足够。
- [官方mini_toolcall.yaml](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tooling/configs/mini_toolcall.yaml)：`step_limit=0`，单次工具观察达到**10,000字符**后保留头尾各5,000字符；**这是字符截断，不是10K tokens，也不是历史压缩**。
- [mini 2.4.6 DefaultAgent](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/agents/default.py)不断追加messages，[LitellmModel](https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/models/litellm_model.py)将历史交给服务，`ContextWindowExceededError`在abort列表；这条固定入口**没有已启用的自动摘要/滚动历史**。把总context直接缩成32K会增加提前中止风险，不能说它会像其他Agent自动压缩。

## 4. 对本项目的结论与省时办法

**是否能用32K：**可以作为明确受限的工程/快速对照设置，但现有证据不足以称“正式SWE已够用”。64K有较直接的同族实测支撑为折中档；若希望保留较完整SWE能力，**128K比32K有更强依据**，仍不是对当前模型/V2 HARD-51的保证。没有找到该精确组合的context/output消融，不应虚构一个“足够”的固定值。

**context与output分开：**总context32,768若同时请求32,768输出，则没有输入空间；32K context配8K output只剩24,576给system、工具和全部历史。128K context配8K output剩122,880，配32K output剩98,304；前者是我们非思考、多轮工具调用可先验证的省时候选，**8K每turn并无此精确benchmark的已发表不掉分证据**。

省时优先减少实际重复prefill和无效等待：复用已存在的10,000字符工具输出限制、验收prefix cache及适当请求并发，避免重试导致整段prefill反复计算；每turn输出上限降低只限制极端生成，不会让原本提前结束的调用按比例变快。不要为省时私自缩官方测试/Agent超时，也不要把新增摘要当无代价字段转换；若加摘要，须作为显式harness配置在正式运行前统一冻结并在独立任务验收。

本轮只新增本报告，未改协议、配置、claud或Git。
