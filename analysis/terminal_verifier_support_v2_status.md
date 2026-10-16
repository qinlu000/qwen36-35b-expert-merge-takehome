# Terminal verifier离线缓存与原状态复评分支持

只支持官方测试环境与已记录状态恢复，不生成新答案、不执行求解搜索、不改官方test.sh／要求／被测模型prompt。Terminal owner独占native runtime7/8及curl wrapper，本文所列缓存与恢复目录由本子任务独立维护。

## 原uv installer缓存

80目录：`artifacts/tools/terminal_verifier_offline_20261016/uv-installer/`。

- `install.sh`：原`https://astral.sh/uv/0.9.5/install.sh`，65983字节。
- `uv-x86_64-unknown-linux-gnu.tar.gz`：原`https://github.com/astral-sh/uv/releases/download/0.9.5/uv-x86_64-unknown-linux-gnu.tar.gz`，21370871字节，成员仅原uv／uvx及目录。
- `url_map.json`精确对应上述2个原URL，`download_receipt.json`记录来源与字节。Mac canonical HTTPS下载后scp原tar，无重打包、假成功、额外执行或hash。

原生installer在多条正式grader里卡在无超时GitHub下载。owner的评分专用runtime8按URL返回原bytes，仍运行原installer、原test.sh和原指定版本。extract-moves-from-video和dna-assembly的正式grade3已走通并完成native pytest；不是合成fixture。

## 实际依赖cache

89个原test.sh只读提取：82项使用uv0.9.5／uvx；相同声明合并为32组，其余7项非uvx单独披露。先实际安装pytest8.4.1、pytest-json-ctrf0.3.5、numpy2.3.0及4个依赖，独立冻结`core-uv-cache`，没有把新评分工具挂给solver。wheel→archive链接转为相对路径，选中msgpack未发现原宿主/data路径，供verifier阶段私有copy。

共享预取`uv-cache`由PID2387411、CPU87–88独立后台填充；`freeze_terminal_verifier_cache_v2.py`的PID2405106按成功安装metadata导出各任务小cache，`task_cache_map.json`给task→group／Python／cache／ready／missing条目。core不再写，重包不会扩进core；不复制全部共享重包到每题tmpfs。

16:21前已实际准备74/82 uvx任务，未声称82全齐或offline fixture通过。video-processing的opencv-contrib一次60秒下载超时、mteb组下载失败留原log；重Torch／3.11组继续。实时状态以`dependency_manifest.json`、`group-*.json`、`task_cache_map.json`为准。完全保留官方pinned packages／原index选项，无默默降级版本。

稳定源码：`scripts/cache_terminal_verifier_v2.py`、`scripts/freeze_terminal_verifier_cache_v2.py`。缓存过程未执行pytest／额外fixture、模型、API或hash。

## 三条原求解超时状态恢复

原trial分别为`extract-moves-from-video__seed0__first`、`crack-7z-hash__seed0__manual1`、`dna-assembly__seed0__manual1`。这些原记录实际为1800s AgentTimeout，而非native_return。逐条读取原66／49／18个command及terminal记录：video与crack从未写要求的`/app/solution.txt`；DNA从未写`/app/primers.fasta`，只做输入分析／依赖尝试。

恢复目录独占`artifacts/recovery/terminal-v2/<task>__seed0/`，保留`assistant_commands.json`、`terminal_history.txt`、`restore.json`及原here-doc文件。video无写入文件；crack恢复1个确认的/tmp分析脚本；DNA恢复8个确认脚本，最后未确认完成的precise.pl未重放。`commands=[]`，未执行原分析／破解／搜索程序。full-rootfs byte_identical明确false，仅记录文件payload保持原文；verifier相关终态为要求答案文件始终未创建，不猜造答案。

使用owner原生grader-only CLI：恢复阶段deny，随后public执行原verifier；无Agent对象／模型，仍4CPU8GiB。首次grade1因我的外层taskset叠加offset导致启动EINVAL，保留失败；grade2已进入官方apt但卡GitHub uv tar，收到SIGINT后保留Cancelled infra记录并清理。grade3使用缓存原installer、并行CPU104–107／116–119／120–123，不加外层taskset、不重答。owner只读引用成功新结果并在安全点并入汇总，不改原attempt。

稳定恢复源码：`scripts/prepare_terminal_transcript_restore_v2.py`；并行精确命令与PID见`regrade_three_native3_launch.json`。三项结果各为`native_grade3/result.json`。**三项现已全部原native reward0、无评分异常**：extract原pytest实际执行2项、crack2项、DNA1项，均因原要求的答案文件未创建而失败；CTRf／stdout和原attempt均保留。完整receipt `artifacts/recovery/terminal-v2/three_final_receipt.json`，本地镜像 `analysis/source_snapshots/terminal_transcript_restore_three_20261016.json`。Terminal owner已收到各result路径，可逐项在安全点并入，不等生成cohort完成。

uv原bytes单独回执：`analysis/source_snapshots/terminal_uv_installer_cache_20261016.json`。全部复评分只CPU原生verifier，没有新增模型／搜索／答案或篡改测试。

## HLE与总汇总器

HLE已自然drain旧两slot后切rolling source `scripts/score_hle_baseline_v2_rolling.py`，PID2446501，2并发，FIRST_COMPLETED逐条补位、30秒独立collect新生成终态，原417缓存／账本／协议不变。见`analysis/baseline_hle_scoring_v2_status.md`和`hle_judge_v2_rolling_upgrade_20261016.json`。

四项汇总器`collect_baseline_final_v2.py`、PID2380282每30秒读权威summary，已实际接入TB final_summary，不采旧伪0 coverage。HLE／SWE／TB未完整时主分null，ASI240完整1.5709884069%；四项全齐才整体complete并退出。无新增Judge校准／生成／测试／hash，未改claud或根索引。
