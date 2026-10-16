# SWE 独立任务 validation 执行

更新：2026-10-16 22:35 CST。用户已授权将完成 SFT 的模型跑 validation。这里是现有留出集的真实修复任务，独立于正式 SWE Pro HARD-51；不是把 87 条 teacher-forced val loss 当成功率。

当前 80 常驻控制器 **PID 584499**，输出为 `/data/caoqinlu/projects/apex-takehome/artifacts/eval/validation_swe_20261016/`。100 题已全部物化；`pallets__click-1852` 的 674,586,624 字节现有 SIF 已从 HPC 复制。**22:28:06，首题公开 gold patch 在新的 CPU125/4GiB fresh sandbox 中通过原生测试，reward=1.0、无异常。** 这只验证源任务运行与评分适配，不是模型 validation 成绩；当前模型请求为 0，正在等 direct 各模型生成块结束。

## 任务与监督隔离

- 固定源：`nebius/SWE-rebench-V2@10483de0f50fe5da545942705a76c6150171af7f`。
- 既有 100 题留出集，Python39 / Go39 / JS20 / TS2，95 个仓库。与当前 SWE2k train 的 repo、instance_id 交叉均为 0；和固定正式 HARD51 的11仓库精确交叉也为0。保守 fork/rename 全血缘独立性仍沿用原数据审计局限，不作新保证。
- 100 题均有 `image_name/base_commit/install_config/test_patch/FAIL_TO_PASS/PASS_TO_PASS`，FTP 非空。现有 87 条 SFT val 是 100 题中完整轨迹不超过 64K 的子集；**执行验证仍保留全部 100 题**，模型新轨迹并不受教师整条轨迹长度限制。
- solver 输入仅原任务 `problem_statement/interface`，由固定 mini 模板包装；不提供 gold patch、测试 patch、参考轨迹或期望测试列表。
- gold patch 放任务目录之外的 `gold_patches/`，只用于独立 source environment acceptance。评分材料放 `tests/`，仅 fresh replay 的 verifier 阶段上传；生成阶段 `verifier.disable=true`，避免同一任务重复跑完整测试。

## Harness 与判分

固定官方代码：[SWE-rebench evaluator](https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/scripts/eval.py)、[log parsers](https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/lib/agent/log_parsers.py)。实际完整副本保存在 80 `artifacts/validation/swe_rebench_source_20261016/`，并随每题评分包保存。

复用本项目 mini-swe-agent2.4.6/LockedMiniSwe、工具 schema、原生 task PATH、离线私有 mini 安装、日志 relay、1800秒总求解时钟、1740秒 mini 子进程预算、64K 总上下文、8K 单次输出、seed0、非思考模式。Base 和 SWE249 同条件，独立输出目录。

源镜像工作目录是 `/<repo_name>`，setup 验证原始 HEAD 并在没有现存路径时链接 `/testbed`；不改真实仓库内容。只将 solver 捕获的 `model.patch` 放入新的干净 sandbox，按源 evaluator 的 `git reset --hard HEAD`、`git apply -v --3way --recount --ignore-space-change --whitespace=nowarn` 应用，然后应用源 `test_patch`、执行源完整 `test_cmd`，调用固定原生 parser 与 normalize 函数。官方 evaluator 的条件确实是排序后 **`passed == expected FTP+PTP`**，不是本项目额外发明的严格条件。两者均保留测试退出码和原始日志。

首个 gold 实际有111 PASSED，与111 expected完全一致；另有1个非目标FAILED，测试总退出码1。固定源 evaluator 的 `passed_match` 仍为True，因此按源规则reward1；不擅自另加整套命令退出码0要求。

空日志、parser 没解析出任何测试时保存 `grading_invalid.json` 并保留无有效 reward 的基础设施待审项，不编造 0 分。源环境/模型编译失败的最终归因仍需看原日志，不能自动把所有无 parsed tests 都断言为纯环境错误。

## 等待式调度

1. 先 CPU125 单路，每个容器 1CPU/4GiB。该核明确与轻量 collector/I/O client 共享；不占 0–124、126–127 的既有 Base 环境。镜像拉取与转换也固定 CPU125、单线程，源镜像下载就绪一题即可准入，不等 100 镜像全部就绪。
2. 等 `validation_direct_20261016/` 下 Base HLE、Base ASI、HLE16、HLE250、ASI128 的 5 份生成 `summary.json` 全部保存，才开始模型调用；不等待 Judge。避免与单 GPU-resident LoRA 的 direct 生成块交替争用。
3. 按 Base100 → SWE249100 的模型块执行，同题、同预算。缺镜像或无有效评分保留覆盖缺口，完整指标为 null，不缩题或选最好重答。
4. root 常驻门闩产出 `validation_direct_20261016/shared_cpu_ready.json`，必须为 `ready/cpu_consumers_finished=true`，并实时复核 0–15 无现存 Base scope 后，才扩至 16 路。125 在途任务排空，过渡只开 0–14 避免超过 16 路；125 退出后加入15，最终固定 0–15。ASI 后续保留112–115，互不抢占。

## 启动与保留记录

自有代码：`prepare_swe_validation.py`、`grade_swe_rebench_validation.py`、`swe_validation_runtime.py`、`run_swe_validation.py`。语法检查已通过；首题真实 source gold checker 已 GPU 无关地通过。没有增加合成模型 smoke。

首个控制器559578在任何模型请求/测试之前失败：父进程先缩为 affinity `{125}`，已有 `baseline_exec_limits.py` 又按可用 CPU 列表切 offset125，得到空集合并报 `EINVAL`。原 `environment_acceptance/`、`launch_before_affinity_fix.json` 和 `*.bootstrap-infra1` 全保留。仅停止自有零模型控制器；修正为轻量父编排保留原可见 CPU，重 CPU sandbox 仍由既有后端严格限到125，镜像转换仍 taskset125。新 source gold 在 `environment_acceptance_v2/` 通过。未修改 Base 后端/在途任务/训练源码。

镜像网络随后实查：80直接Docker鉴权连接失败，而现有本地HTTP代理38080对同请求返回200。控制器567158仍0模型请求时只重启自有准备进程；当时575416仅为imagepull补该现有代理，gold原件复用，未重复执行gold/model。原launch与下载尝试记录保留。没有更改benchmark网络策略或任何Base队列。

HPC CPU-only 方案已实际核过：`acd_u --test-only` 被集群拒绝，要求 `--gres=gpu:N`；debug4CPU/25分钟返回不可用配置。HPC direct Docker auth 10秒超时。因此不把 HPC CPU-only 当现成备用，不申请额外 GPU 做容器任务。

尚待观测：其余99镜像网络与转换吞吐、首个真实模型修复任务、Base/专家完整100题评分；目前不能估计镜像总就绪时间或声称已有成功率提升。

服务727113的12小时allocation实际到期为10月17日10:05:32 CST；延长请求被Slurm拒绝，不能按24小时排期。当前控制器584499已显式记录到期时间，并在每次新任务准入检查至少剩2100秒：**09:30:32后停止新模型任务**，在途求解与CPU评分自然排空，未开始项保留pending和service_expiring，不能让到期变成模型0分。此守卫在仍0模型请求时部署，原launch_before_expiry_guard.json保留；不申请新GPU服务。22:35镜像cache已实际下载约1.20GB（非SIF就绪数量），当前仍1个已就绪镜像。
