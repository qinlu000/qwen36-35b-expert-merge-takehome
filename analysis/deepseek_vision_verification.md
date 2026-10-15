# DeepSeek Flash 图像输入核验与先前判断纠正

2026-10-15。用户质疑“DeepSeek API不支持图片”后，重新查当前官方文档并实测。结论：已有官方deepseek-flash支持图像，可以作为HLE文本判分与ASI文字/图像判分的统一替代Judge候选；此前将其说成纯文本API、不适合ASI图片是未经核验的错误判断，不能再据此索要新增GPT/Luna凭据。

## 文档事实

- 当前[官方模型表](https://api-docs.deepseek.com/quick_start/pricing/)列deepseek-flash为DeepSeek-V4.1-Flash，Vision支持；deepseek-v4-pro列Not supported。支持情况要按具体模型/服务判断，不能笼统说整个DeepSeek API不支持。
- [Chat Completions接口](https://api-docs.deepseek.com/api/create-chat-completion/)支持user.content数组中的text和image_url，后者可用http(s)或base64 data URL。[Vision指南](https://api-docs.deepseek.com/guides/vision/)说明具体限制。
- 固定[ASI通用视觉scorer](https://github.com/apexin-ai/ASI-Bench/blob/cf07cb89d8590d958ff42db7ae3d6608f5eb9dbc/ai4sci_bench/scorers/multimodal.py#L149-L193)正是这种格式：预测图/参考图编码后放user.content.image_url；它不是只向模型传本地文件名。因此当前没有已证实的“ASI图片接口格式写错”故障。

## 一次真实的双图接口检查

用本机项目外已有DeepSeek官方key，base_url=https://api.deepseek.com，POST /chat/completions，model=deepseek-flash；thinking disabled、temperature0、max_tokens1024、JSON mode、无自动重试。密钥没有输出、复制或提交。

两张512×512自造PNG：第一张左红右蓝，第二张左蓝右红，一次请求包含两块image_url（detail=high）。期待JSON记录各图两侧颜色及same=false；实际完全匹配。HTTP200、finish_reason=stop、耗时1.274s，prompt466/completion35/total501 token。返回model=deepseek-flash及system_fingerprint已保存。

安全摘要：source_snapshots/protocol/deepseek_vision_preflight.json。原始合成图片、请求、响应与usage在Mac及80的ignored artifacts/preflight/deepseek-vision-20261015/。无HLE/ASI正式题、参考图或答案，不是科学Judge质量校准。

## 对协议的影响

建议统一HLE和ASI使用现有DeepSeek官方deepseek-flash，Luna保留备选；SWE与TB仍由官方自动测试判分。ASI的task_eval原始模型是openai/gpt-5.5，endpoint override不会自动替换model：需要显式的模型映射/配置，并检查LiteLLM/响应解析、JSON/schema、原num_judges/输出cap/重试与图像完整传递。

统一替代Judge时保留原rubric、预测/参考图、scorer权重、num_judges与聚合口径；所有受测Qwen版本用同一冻结Judge。原模型不同要明确披露，不能冒称原GPT-5.5设置完全复现。这里的差异是评分模型替换，不是DeepSeek缺图像能力。原始task_eval未被修改。

已有8例HLE文本接口检查与此次简单双图检查支持技术可用性；仍需独立的科学文字/图表样例验证评分行为，不能把颜色识别当专家级图表校准。API别名的不可变后端revision未提供，应保留返回model、日期和fingerprint并在整批评分中监控变更。
