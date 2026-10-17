# SWE较低学习率与完整长轨迹过滤：执行记录

2026-10-17 13:50 CST。用户先授权“lr调小重新训一版吧”，随后允许“把太长的轨迹筛掉”。本次实际提交一个独立SWE候选，从原Base重新训练；不接旧adapter、不覆盖旧模型、不自动换入AVG64。

## 配方与数据

- 峰值learning_rate：原1e-4 → **2e-5**，cosine/warmup.03/weight_decay.1不变。
- 同节点4H100/global batch8/单卡1/累积2，1epoch，r16/alpha32/dropout.05；原ZeRO3、BF16、SDPA、grouped_mm、Liger融合线性CE保持。
- **完整序列不超过32768 token的整条训练轨迹**：1027条、23,353,670完整序列token、5,034,955 assistant输出token。排除973条，不改任何保留行bytes、工具观察或提交动作，不切窗/截断。该token口径来自原固定HF模板，不是本次实际监督token账本。
- max_length仍65536、truncation_strategy=delete、no packing/nonthinking；原preserve_thinking=False保持。此前空think壳序列化差异未在本候选改动，不能把降LR实验描述为该问题已修复。
- 原87条held-out逐字节保留，仅teacher-forced训练诊断；没有恢复task-level validation或按loss选择模型。1027为导出条数，原角色错误223/279仍在，实际Swift加载数与总步数须读新原生日志。
- 首先克隆实际726335的training_config，改变LR、train/val路径、独立output和TensorBoard日志。没有仅改静态共享JSON后误以为训练已生效。
- 新增report_to=TensorBoard（已安装2.21.0），只作原生训练诊断；不伪造entropy。最终按一epoch结束的最后checkpoint保存，不看best-loss。

本次同时改变LR、训练样本量/长度/来源比例及相应步数，属于**联合修复候选**，不能宣称严格LR单变量因果对照。筛选分布、原行映射和字节验收见[数据记录](swe_low_lr32k_data_20261017.md)。

## 唯一提交与启动修复

首个728711于13:47:11提交，13:47在ACD1-19仅1秒即FAILED/1:0，未创建训练输出目录、未执行Python或加载模型。集群`singularity`包装器扫描所有以/data开头的目录参数，把新脚本单独的`--project PATH`参数误认sandbox镜像。与原成功脚本一致改为`--project=PATH`，实际镜像仍原SIF，不绕过或替换容器。原源/日志/终态已归档在control/attempt1，原提交收据保留。

确认728711终态FAILED且squeue不存在、训练目录未建后，仅作启动修复，13:48:28唯一重提**728713**。claim位于`artifacts/runs/swe_lr2e5_max32k_control_20261017/attempt2/`，不得因排队或加载慢重复提交。普通**acd_u/Nice1000**、同节点4GPU/24CPU/256G、4小时walltime、排除已知SIF挂载故障节点59，无emergency回退。提交前实时只有原727912/727913两个TP2共4GPU，新候选获分配后合计8GPU，低于16。

13:49:56实际728713已 **RUNNING/ACD1-19**，占4GPU，运行1分24秒。原生配置已写、4-rank torchrun已启动，training.log仍0字节，属于初始化阶段，尚无optimizer更新证据。独立重新计算原/新配置全部字典diff，与保存config_changes完全一致，恰为预期7项，没有其他训练参数变化。预计导出1027经原Swift预处理后可能1025，必须等待实际日志，不将排队/配置写出当作训练成功。原版726335耗时7286秒约2小时，本次耗时待原生吞吐测量，未承诺固定时长。

## 路径与复现

- 计划：`configs/train/swe_lr2e5_max32k_20261017.json`
- 数据：`artifacts/data/candidates/swe_low_lr32k_20261017`
- 新作业：`scripts/run_swe_low_lr.slurm` → `scripts/run_swe_low_lr.py`
- 原生配置、命令、差异、数据统计、训练log和TensorBoard：`artifacts/runs/swe-lr2e5-max32k-728713/`
- TensorBoard相对目录：该run的`tensorboard/`；旧本机6006仍展示原五组导入日志，不能冒称新曲线已在那里同步出现。
- [首个失败收据](source_snapshots/swe_lr2e5_max32k_launch_20261017.json)、[唯一重提收据](source_snapshots/swe_lr2e5_max32k_resubmit_20261017.json)。

已经存在claim与作业，**不要再次运行sbatch**。复现时先用全新输出目录运行filter脚本，再审计资源/现有claim后提交新作业。原有持久评测、冻结四专家/主AVG64/ASI128、64K/8K正式协议和已取消自动化保持。本轮没有重生正式答卷、追加Judge或按正式成绩选checkpoint。
