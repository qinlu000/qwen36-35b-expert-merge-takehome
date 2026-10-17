# Invalid 修复状态

更新时间：2026-10-18 01:45 CST。目标是修复有证据的工程性 invalid，不通过重生答案、盲目重试或手工填 0 制造完整分数。

## 已完成或已接受的精确修复

- HLE Judge：符合固定格式恢复条件的历史 invalid 已按一次 compact Judge-only 例外处理，HLE 专家、Mixed、AVG16、AVG64 的 HLE 结果已完整；TIES-Dense 的 1 条缺 `correct` 不符合该例外，仍保留 invalid。
- ASI 专家 CMOS B1：冻结 runtime 只追加正确的 ASI repo root，导入恢复后使用原候选和既有 cache 完成一次评分；不生成新答案。
- SWE 专家/AVG64：Vuls、NodeBB 等部分原答案经过逐项 source/test/资源审计后接受 exact native0 或完整官方报告审计；原 raw invalid 和答案保持不变。
- Terminal：nginx/seed0、git-leak/seed1 的可追溯原答案已分别有精确 grade-only overlay；不修改候选、不安装任务服务、不重新调用模型。

## 当前不能直接修复的项

- Base Terminal 的 3 条计算型 verifier timeout：独立预算视图可记录派生 0，但 strict native 仍 invalid，不能把派生值写回原 reward。
- Terminal 专家当前 7 条 invalid、AVG64 Terminal 当前 6 条异常：其中包括 cleanup guard、依赖/输入供应异常和缺少完整归档。没有完整原环境或明确恢复证据的项继续 null；不能套用另一模型的 archive、patch 或白名单。
- TIES-Dense HLE 1 条 HTTP 完整 JSON 缺少 `correct`：不符合长度/parse 恢复条件，完整方法分仍 null。
- SWE 新 LR retry23：节点 `NODE_FAIL`，没有有效任务结果；服务已取消，不把它当模型 invalid，也不重跑。

## 修复准入规则

只有同时具备原 task/model/seed 绑定、原候选或答卷完整快照、同一 SIF/依赖、原预算、独立资源租约和完整排空证据时，才允许 grade-only 恢复。恢复结果另存 overlay/manifest，原始 result、invalid 原因和协议差异全部保留。未知、网络策略、缺少输入或缺少 live 状态的项目不自动修复。
