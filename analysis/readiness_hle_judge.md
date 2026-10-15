# HLE图文与Judge准备检查

2026-10-15 21:25 CST左右。仅使用自造输入，不读取HLE逐题题面/答案，不加载模型权重或执行正式评测。当前完整HLE图文/no-tools是候选协议，尚未冻结正式端点与Judge。

## 图文processor：CPU自造图片检查通过

固定基座revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，在80下载5个元数据/tokenizer文件共12,836,540B；tokenizer.json SHA-256与HF LFS一致，其余按固定revision、字节数和本地SHA留回执。未下载71.9GB权重。

用已有 `/data/caoqinlu/envs/datamind-vllm/bin/python`，显式 `CUDA_VISIBLE_DEVICES=''`、HF/Transformers offline，加载 `Qwen3VLProcessor`。自造32×32纯色图片加短文本，固定chat template、thinking开启，成功生成input_ids [1,81]、pixel_values [256,1536]、image_grid_thw [1,3]等输入。仅证明预处理通路，未证明vLLM图文HTTP、模型回答、长上下文、显存或吞吐。

运行环境：Python3.12.13、Transformers5.15.1、Torch2.13.0+cu132、tokenizers0.22.2、vLLM0.27.1。加载时出现两条video processor参数docstring诊断，图像处理未失败；暂不修改用户安装。回执：`artifacts/models/hle_processor_preflight.json`；固定文件回执：`artifacts/models/base_metadata/995ad96eacd98c81ed38be0c5b274b04031597b0/receipts.json`。

## DeepSeek：16次合成接口调用，发现并修正JSON字段提示

采用固定官方HLE判分criteria的原始user prompt，使用8个自造案例：正确/错误、分数等价、答案改正、拒答、歧义、单位等价、回答内夹带评分指令。无HLE数据、无被测Qwen作答。固定请求 `deepseek-flash`，thinking disabled、temperature0、max_tokens800、并发2、无自动重试。

- 第一版8次：JSON可解析，yes/no与confidence预期8/8；但只2/8返回官方schema要求的常量字段strict=true，另外6条缺失。证明JSON mode不等于schema约束；不能直接代替官方structured parse。
- 明确列出五个必需字段、补完整JSON例子后重做同8例：schema、yes/no、confidence联合8/8通过，全部finish_reason=stop。未伪造补齐strict字段；保留第一版失败记录。
- 本轮共16次generation，合计prompt_tokens=6066、completion_tokens=951，共7017 token。未按余额差或未经核实的单价估算费用。API原始response/usage留档，不包含密钥。

这只是小规模接口/基本行为验证，不是HLE正式判分，不证明与官方默认o3-mini等价，也不是专家级科学题准确性校准。正式若采用DeepSeek，需明确作为本实验Judge协议、固定完整prompt/参数和验证失败处理；不得悄悄改为默认官方Judge。服务仅报告模型alias，内部revision未暴露，需披露日期与返回model。

日志在Mac与80的 `artifacts/preflight/hle-judge-20261015T132438Z/`；`summary.json`保留v1，`summary_v2.json`保留修正后检查。两版都保存请求、响应、request id、usage和时间，不含Authorization字段。官方prompt SHA-256：`0f0023ee579b8c134f1834ed8952778b9e01460e31d47c242ee3629da9d44835`。

## 凭据与待解决事项

本机项目外私有配置仅有HF与DeepSeek变量，权限0600；本轮只检查变量名，没有输出或迁移密钥。未找到本项目可用的OpenAI/GPT-5.5配置；这不代表穷尽用户其他位置。ASI固定评分配置的GPT-5.5/视觉Judge缺口仍未解决，不能用本轮DeepSeek文本检查替代。

HLE还需真实被测模型端点的图文HTTP/输出/usage冒烟、固定推理和thinking预算；正式Judge完整版本/错误处理也待冻结。若继续使用DeepSeek，应在独立、许可清楚的更广学科样例上校准，不用正式HLE反馈选judge或prompt。

一手依据：[固定HLE预测代码](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)、[固定HLE判分代码](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)、[DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode/)。

后续纠正（2026-10-15）：当前官方deepseek-flash支持图像，已有key一次双图HTTP200且内容正确，见deepseek_vision_verification.md。上文早期文本测试不能推出不支持视觉；推荐HLE/ASI统一Flash替代Judge，原GPT5.5复现与具体模型支持是两回事。
