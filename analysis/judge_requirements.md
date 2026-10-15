# 判分 API 与凭据核验

核验日期：2026-10-15。凭据仅保存在本机项目外的私有配置中，本文件不包含密钥或账户余额。本文件初次鉴权之后新增过一次六个自造样例的 DeepSeek 接口检查（717 token，见 claud.md），未执行正式 benchmark 判分；用户最新要求先讨论方案，当前停止执行。

## 当前鉴权结果

- HF 账号 `csminion` 的鉴权成功，token role 为 write，HLE 数据访问检查返回 200。
- DeepSeek 官方模型列表和余额接口均返回 200，余额状态可用；返回模型为 `deepseek-flash`、`deepseek-v4-pro`。这些是早期鉴权证据；后续已有文本JSON与双图真实请求通过，最新见deepseek_vision_verification.md，仍非科学评分校准。[模型列表接口](https://api-docs.deepseek.com/api/list-models)、[余额接口](https://api-docs.deepseek.com/api/get-user-balance)
- 用户尚未指定 API 总费用上限；账号余额不等于本实验授权支出。

## HLE

官方脚本可通过 `--judge` 指定模型，默认 `o3-mini-2025-01-31`，使用 Pydantic 结构化 parse。若改用 DeepSeek，需要适配其输出协议、用独立合成样例校准字段与匹配规则，并在训练前冻结模型名、服务报告版本、日期、prompt、thinking、预算和重试规则。所有评测对象沿用同一设置，报告应注明为本实验的 DeepSeek judge 协议，不能声称与默认 judge 的官方结果等价。[HLE 官方脚本](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)、[DeepSeek JSON 输出](https://api-docs.deepseek.com/guides/json_mode)

## ASI-Bench：60 项正式配置审计

范围为 HF seed31415 固定 metadata 的 60 个 `task_ids`，逐一核验代码 commit `cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc` 下对应 `task_eval.yaml`。只提取模型、provider、scorer 等白名单元数据，跳过 rubric block，没有读取参考答案或参考图。[正式范围](https://huggingface.co/datasets/Apexintelligence-AI/ASI-Bench-seed31415/blob/0fa14219cafdbab634d8b3cfbce238a8735a214f/metadata.json)

- 60/60 配置成功检查；13 项显式指定 `openai/gpt-5.5`，这是配置中唯一显式 judge 模型；47 项没有模型字段，也未出现通用 `llm_judge` / `multimodal` 标签。
- 通用 judge 代码的默认模型同样为 `openai/gpt-5.5`；API base、key-env 和 protocol 的 transport override 会保留任务配置声明的模型名。因此 DeepSeek 官方 endpoint 不能直接履行这些 GPT-5.5 评分请求。[路由与默认模型](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/_judge_common.py)
- 原始配置包含视觉评分；保留GPT5.5原模型需其图像API凭据，替代实验则可用已有deepseek-flash图文接口，经独立校准并披露，不要求因此新增OpenAI凭据。[视觉评分配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/biology/calcium_ip3_dyk_oscillations/task_eval.yaml)、[文本评分配置](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/tasks/chemistry/metadynamics_for_dipeptide_in_vacuum/task_eval.yaml)、[VLM 实现](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py)
- OpenAI 官方模型页列出 GPT-5.5 的图像输入、Chat Completions 和结构化输出支持；具体账号权限、速率和调用成功率仍须用后续凭据验证。[官方模型文档](https://developers.openai.com/api/docs/models/gpt-5.5)
- README 中的 Gemini 示例不是这 60 个实际任务的 judge 清单；不能据示例要求用户配置 Gemini。47 项的 custom scorer 尚未逐一追踪所有传递依赖，不能声称它们绝无外部 API 需求。

显式指定 GPT-5.5 的 13 项：

```text
biology.calcium_ip3_dyk_oscillations
biology.contextual_dna_regime_mapping
biology.protein_folding_go_model
chemistry.metadynamics_for_dipeptide_in_vacuum
chemistry.sapt_water_dimer
chemistry.vtst_tunneling_corrections
earth_science.2_e_soil_carbon_nitrogen_cycling
electrical_engineering.cmos_opamp_design
materials.ising_domain_growth
math.nnls_modulus_deblur
physics.ag_strip_dielectric_inference
physics.ks_2d_anisotropic
physics.paired_nanorod_negative_index_retrieval
```

将上述任务换成DeepSeek会改变评分模型；可作为明确披露替代Judge的本实验结果，不能冒称原GPT5.5配置复现。当前deepseek-flash已双图实测通过，技术能力与原模型等价性应分开；见deepseek_vision_verification.md。[ASI 评分契约](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/docs/guide/how-scoring-works.md)
