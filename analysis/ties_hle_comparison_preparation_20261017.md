# Dense TIES HLE2500方法对照接入准备

本文件替代TIES-SVD64方案。真实pilot的SVD64相对残差约0.30–0.57，root决定不导出/评测SVD64，改用保留真实TIES更新的完整BF16 snapshot；TA仍撤回。728007已导出完成，本owner实际HPC纯metadata guard已通过。准备时未启动controller/TP2或模型请求；05:43后已执行并正式准入，见[实际执行记录](ties_dense_hle_execution_20261017.md)。

## 产物及服务

完整HF目录为`artifacts/merges/four-experts-ties-dense-v1-20261017/`根，无子目录；alias为`apex-ties-dense`。merge owner冻结rho0.2/total/ones/λ1、Δ=2BA只计一次scale、不做SVD。310矩阵更新、735个tensor保持。实际BF16 effective-update偏差相对FP32 delta为**10.5310%**，不可称数值无损；完整global_rounding会写入服务及controller admission，详见[dense可行性](ties_dense_export_feasibility_20261017.md)。这不再是与AVG64匹配的r64参数化容量对照。

[serve入口](../scripts/serve_direct_experts.py)新增`ties-dense`，复用原Slurm wrapper与TP2/BF16/64K/maxseq50/batched8192/vision配置。完整目录直接作为model，真实served alias为apex-ties-dense，不传任何LoRA enable/rank/modules/targets开关；旧LoRA profiles保留。

分配GPU前及服务内使用同一轻量guard：EXPORT_COMPLETE.json必须passed/full_hf_model/冻结source revision，指向merge_report.json；report必须finished、310target、735非目标bitwise验证、1045tensor/26shard、sources_unchanged/reload_verified=true、real_weight_svd_calls0、selected_final=false。新index与原Base weight_map逐项相同，原merge报告310精确key全部命中；config及必要HF小文件存在。不扫描大权重hash或加载tensor。

HPC实际Python3.6.8已执行`--check-dense-export`：imports及语法兼容，初次因marker缺失拒绝，728007完成后同一guard已通过，未触及CUDA/API；GPU服务仍用容器Python3.12。

## 独立资源与controller

新[driver](../scripts/run_ties_dense_hle_control.py)和[固定配置](../configs/eval/ties_dense_hle_control_20261017.json)默认仅打印prepare plan，0网络/0GPU。`--execute`由root审阅后启动；输出为`artifacts/eval/ties_dense_hle2500_20261017`，controller为其controller子目录。

不必等AVG16。root允许普通nice1000额外TP2：最近快照10GPU，新方法后12、临时export1后13；提交时重新计入本项目所有RUNNING/pending ReqTRES并要求+2≤16。独立ASI不复建，AVG HLE→ASI28095不动。

1. 独立controller.lock及唯一controller-claim；已有claim/答卷拒绝盲目重启。先通过HPC完整export guard，再核GPU总数与唯一job name。
2. sbatch前排他写submit-intent。显式acd_u/Nice1000覆盖Slurm默认，TP2原规格；目前请求4小时，且不晚于10/18 02:20 CST。实际提交/准入重核至少3小时余量；未知结果needs_attention、不重提，第二controller在任何网络前拒绝。
3. 新port18006/独立bridge28097；旧controls也用18006，故显式exclude ACD1-59及其tunnel节点（当前ACD1-30），避免同节点bind冲突，不改旧route。PermitOpen只追加精确新node:18006，使用现HPC flock/完整管理SSH key；新tunnel config/supervisor只写本controller目录。
4. RUNNING后按实际StartTime/EndTime收紧TimeLimit；健康等待封顶20分钟。一次text+image synthetic只核真实alias、token计数/vision、completion≤32、nonthinking、schema及非空assistant文本，**不按red/42内容是否正确准入**。raw输出保留，无择优/重试。
5. 独立manual_retry_manifest固定原2500 ID/342图；复用原generator/scorer各启动一次并记录intent/PID。每题仍连续300秒、64K8K、50并发及原sampling，generator不读gold，不重生成已有started/result。
6. 实际EndTime前300秒STOP_ADMISSION，在途自然走完原300秒、不signal生成器。它退出且无started未终态后等native running/waiting0，核自有job并只取消新job；等squeue消失后写独立consumer marker。若job已自然过期，如实记录metrics不可再观察、job离队，不伪造native0。外部Judge继续，不杀grader。
7. 异常记needs_attention；正式准入前可取消已知自有job，准入后保留所有答卷、不自动重答，交root审计。本版本是一次持久运行，不提供盲目重启恢复。

旧watcher3321991只跟踪原migration jobs；新job不写旧字段，不复用28096，所以不改watcher。727857的rank16引擎不能hot-load完整dense模型，本方案从未这样操作。

## 固定协议与比较边界

复用原run_direct_hle_formal.py/score_direct_hle_formal.py：完整2500/342图、原source/manifest/system/sampling，50并发、65536/8192、300秒、thinking/preserve_thinking=false；真实alias进入tokenize/chat transport。

Judge仍同学校DeepSeek-V4-Flash身份/TLS/seed0/temp0/nonthinking/4096、原criteria/schema、2 workers，**每模型总20CNY/5000calls**。两次原Judge均200+length且parse失败的invalid适用已披露的显式2+1 compact恢复：最多额外一次，与Base wrapper逐字一致，原source/user criteria不变，原reservation加独立recovery计入总cap；仍失败null，不依correct选择。当前专家/Mixed固定8项脚本不能直接套用TIES，须固定其实际符合条件的名单和唯一claim。

仅HLE方法对照，不恢复task-val/loss选择，不据正式分数选主模型，不称四项macro。报告披露dense-vs-LoRA表示、非r64容量及舍入差异；仅2500全部有效时给最终分数，否则报coverage/invalid。

## 检查与待执行

纯本地小fixture通过：有效marker接受；passed/source revision/SVD calls/310/735/reload错误拒绝；dense命令无LoRA、model/alias正确；原expert16及AVG64-r64命令回归；重复submit-intent拒绝；GPU统计含全部requested项目jobs。假SSH模拟sbatch超时：一次尝试、needs_attention、第二controller在网络前拒绝。真实模型/GPU/网络调用0；默认prepare输出0调用；Python/JSON及内嵌远程Python语法通过。

待root完整export验收并批准启动，示例仅供审阅，本轮未执行：

```sh
artifacts/envs/hle/bin/python scripts/run_ties_dense_hle_control.py \
  --project /data/caoqinlu/projects/apex-takehome --execute
```

接入owned：serve_direct_experts.py、run_ties_dense_hle_control.py、ties_dense_hle_control_20261017.json及本文件；另有dense feasibility分析。merge owner的export脚本/config/slurm未改。
