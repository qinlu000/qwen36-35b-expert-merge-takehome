# Terminal 独立修复运行环境

本轮用户已授权清理故障临时产物并重新运行未评分项。新入口与原 native11 分开，不修改任何在途 driver、原答案、正式测试或评分预算。

- Environment：`terminal_repair_environment_v2:TerminalRepairEnvironment`。继承已有 native / verifier cache / apt transport 实现，额外从每题 SIF 读取原生 PATH，工具仍位于私有目录；CPU 池使用明确的 offset / slots，不采用旧 16→30 自动扩池。
- Agent：`terminal_repair_agent_v2:TerminalRepairAgent`。保持原 Terminus、模型参数和 1800 秒求解预算。只将已经丢失 tmux session 的特定 `send-keys` 错误转为原生 `NonZeroAgentExitCodeError`，使当前候选状态继续进入官方评分；不创建新终端继续求解，也不吞掉其他运行错误。
- 归档前移到 agent `finally`，发生在上传 tests、配置 verifier、恢复评分网络之前。原环境直到首次 `/tests/` exec 才归档，因此 tests 上传 ENOSPC 会先终止，最终状态来不及保存。
- 归档包含 workdir、完整 `/etc`、存在的 `/var/www`、官方测试静态引用的输出路径，以及求解开始后 ctime 变化的其他根文件。扫描仅用文件元数据，不读内容 hash；挂载目录、系统虚拟目录和私有 harness 排除。保存清单、tar 返回码和进程列表，取消时等待原归档任务结束再继续退出。
- tar 记录文件状态，不宣称自动重建存活服务、删除语义或完整执行环境；新运行仍在原容器内直接进行 native verifier。后续若只能从 tar 恢复，仍需审核实际评分依赖状态。
- 原 chess/seed0 cleanup 日志显示 `killed=[]` 但末尾仍有新生 PID 794/795。新清理在原基线进程集合以外反复 TERM/KILL，要求两次空集，保留剩余命令行；没有放松未确认清理时禁止恢复公网的条件。
- 评分继续使用原官方 900 秒和现有逐题缓存。未修改官方测试、轮子版本、CPU/GPU依赖类型或正常失败分数；新的固定 cohort 与原运行分开记录，不据重跑得分择优。

两个模块和两段容器内 Python 已通过 AST 语法检查。本说明不表示已经完成模型调用、native verifier、依赖预取或生产启动；这些由 root 统一编排、记录。

生产回执与后续修复见 `terminal_independent_repair32_20261016.md`。首运行已真实完成两个补评分并启动新生成；22:09冻结runtime-v2对所有ready逐题UV缓存显式设置离线，避免过期索引重验证经原hosts发生TLS失败。只作用于verifier，原native依赖版本、候选和预算保留；原在途求解子进程保留。
