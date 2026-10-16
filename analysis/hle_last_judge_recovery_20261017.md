# HLE 最后一项 Judge 补齐

2026-10-17 **02:56:55 CST** 已完成：固定2500项全部有效评分，**99/2500 = 3.96%**，0 invalid、0 pending。评分使用已披露的 HKUST(GZ) DeepSeek-V4-Flash 替代 Judge，不能称为官方提供方成绩。

唯一缺口 `672ecc6946f619ca9b0495c5` 的两次原请求均 HTTP200、finish_reason=length、completion_tokens4096，但 JSON 在 reasoning 字符串中截断，缺少 correct/confidence/strict。两次返回相同 provider request ID；不能据不完整说明自行填 verdict。原失败请求、响应、预算和 solver 答案全部保留。

用户授权补齐全部 Base 缺口后，仅为该项新增一次 grader 请求。原 question、gold、solver response、官方 criteria/user message逐字不变；保留 temperature0、seed0、4096输出、nonthinking、JSON object schema、学校TLS证书/SNI/Host验证。仅在原 system wrapper 后追加 JSON 键顺序与一句话短说明要求，先输出 correct/confidence/strict，减少冗长说明截断。没有生成任何新 solver 答案，也没有重跑其它2499项。

新返回为完整五字段 JSON，correct=no，62 completion tokens；模型与 system_fingerprint 和原 Judge 一致。结果通过原 frozen scorer 的 `parse_judge` 校验后，才原子替换唯一 invalid 结果并从全部2500项重新汇总。该项属于原生 Judge 判错，没有把 invalid 直接当0。

新增一次调用 **¥0.00122625**；原1056次调用账本完全保留，新增独立 recovery 台账，合计1057 calls、**¥1.6010295**，低于原¥10/5000 calls上限。原 invalid result 和 incomplete summary 已复制保留。

80 canonical输出：`artifacts/runs/hle_judge_v2_20261016/summary.json`。独立回执/原失败结果/新增 request、response、result、budget 位于同目录 `single-judge-recovery-20261017/`。

执行脚本：[recover_hle_last_judge_20261017.py](../scripts/recover_hle_last_judge_20261017.py)；实际状态：[snapshot](source_snapshots/hle_last_judge_recovery_20261017.json)。脚本只允许这一个任务、一次请求，已有 request 后禁止再次发送。本轮没有修改其它正式专家/合版的 Judge 任务、账本或共享 collector。
