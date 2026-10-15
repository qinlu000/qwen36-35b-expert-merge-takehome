# HLE 协议与完整任务清单核验

2026-10-15。固定数据cais/hle@5a81a4c7271a2a2a312b9a690f0c2fde837e4c29，代码centerforaisafety/hle@22ed3074b1e7b134bcbc09028d0ba320839b0655。本文是设计依据，不是正式成绩。

固定test Parquet已下载到80的ignored artifacts/benchmarks/hle/下，274,276,147B，SHA256为6d0ee0602e8aea6b159509577e884f48ecac7b8e3f6822a35f51335a446c726a，与上游LFS一致。仅读id/image列；image只计算非空标志，不打印图像值。实得2500唯一ID、342图像题、2158纯文本题；未读question/answer/rationale。HLE ID与图像ID分项清单见source_snapshots/protocol/hle_task_ids.json。

官方预测入口使用system固定Explanation/Answer/Confidence格式，问题含image时发送image_url；本项目采用完整图文、no-tools、每题单次生成。Qwen基座原生有vision encoder，CPU预处理已过但完整图文服务尚未验证；当前不删除342图像题。

本实验非思考候选为temperature=.7/top_p=.8/top_k20/max_tokens32768、context262144、seed0。thinking偏好尚待确认。单次HTTP600s、最多一次传输重试沿用官方客户端量级，另设计每题1800s总墙钟，实际外层deadline需实现验收。官方入口没有生效temperature参数（传参行被注释），也未把dataset revision传进load_dataset；实施时必须显式注入冻结参数和HF revision，不能靠默认值就宣称已固定。

主指标为完整2500题准确率，图像/纯文本分项另列。官方脚本以数据总n作分母，缺结果不偷偷删题；评分链故障须单列并修复，不能把只完成若干题的均值称完整成绩。

候选Judge为已有DeepSeek官方deepseek-flash，温度0、thinking关闭、max_tokens4096、JSON mode。使用官方criteria原文，另加本项目五字段JSON system约束；max_tokens从合成接口测试的800提高是本实验设计值，不是新的正式测试结果。JSON必须实际包含extracted_final_answer/reasoning/correct/confidence/strict=true，不能在解析后捏造缺失strict。固定prompt已保存configs/eval/prompts/，源hash见source_snapshots/protocol/hle_prompt_hashes.json。

该Judge区别官方脚本默认o3-mini-2025-01-31，只有8例合成接口检查，不能称等价或专家学科校准通过；模型alias背后不可变revision未公开，记录日期和返回model。若后续改用HKUST Luna，必须在正式评分前版本化、独立校准，并对全部模型统一，不能与DeepSeek评分混报。

协议过程中仅下载固定二进制数据并读取安全列、提取通用prompt字符串，没有正式题推理或Judge调用。下载最初走Mac较慢后改80直连签名CDN；保留读取边界与完整性回执，不保存或输出HF密钥。原始gated数据不提交Git。

来源：[固定数据元信息](https://huggingface.co/api/datasets/cais/hle/revision/5a81a4c7271a2a2a312b9a690f0c2fde837e4c29?blobs=true)、[官方预测源码](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)、[官方评分源码](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)、[Qwen图文说明](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)。此前接口证据见readiness_hle_judge.md。
