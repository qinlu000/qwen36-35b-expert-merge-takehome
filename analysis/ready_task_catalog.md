# 可直接下载的独立训练任务包目录

更新：2026-10-15。范围为已有公开训练任务的 README、固定 revision 的文件索引与通用环境接口代码；没有打开四项正式 benchmark 的答案、补丁或隐藏测试，没有执行任务、teacher、API 或 Slurm，也没有拉取 Docker 镜像。本文只核对下载对象；实际下载回执由 root 统一记录。

## 下载结论

无需先从 GitHub 逐个找 issue 或自己编任务。已有三类任务池能直接下载任务说明、环境入口与验证器。优先取 SWE-smith 的 Python/Go 分仓、Nemotron mixed 六个小任务包与 D3-Gym metadata。Endless Terminals 另作可选池，不为得到环境而顺带下载其教师轨迹。

| 专长 | 固定来源 | 发布数量口径 | 本轮建议下载量 | 包含什么 | 仍需补齐 |
| --- | --- | ---: | ---: | --- | --- |
| 仓库修复 | SWE-bench/SWE-smith-py + SWE-smith-go | 卡片 train=50,908 / 8,212；不是已筛后数量 | 12 Parquet，227,135,442B，另加 README | instance_id、repo、image_name、problem_statement、patch、FAIL_TO_PASS、PASS_TO_PASS | 按 repo/任务分组与正式集排除；Docker 镜像/profile；目标 mini 执行接线及独立验证 |
| 终端＋部分科研执行 | nvidia/Nemotron-Terminal-Synthetic-Tasks 的 skill_based/mixed 六领域 | README 未给精确任务数，须下载后仅按目录结构统计 | 6 tar.gz，27,935,179B，另加 README | instruction、environment、tests/test.sh；共享领域 Docker 环境与 pytest 检查 | 核 task.toml、镜像版本、输入工件、验证器隔离；固定 Harbor/Terminus2 上真实执行 |
| 科研执行 | osunlp/D3-Gym | card train=565，来自239 repo | 1 Parquet，2,254,947B，另加 README | task_id、instruction、preview、eval_script、original_repo、discipline | 完整输入/依赖在 Docker 镜像；来源许可/ASI同源排除；目标 ASI adapter 接线 |
| 可选终端池 | obiwan96/endless-terminals | 文件索引确定2,492任务，不把约2,500写为精确数 | 排除 solution 后19,938文件、49,514,693B | 每任务 instruction.md、task.toml、environment四文件、tests两文件 | 大量小文件请求；镜像构建、验证器与目标Terminus2运行验收 |

表中 SWE 两分仓的条数不能机械相加为已去重独立任务数。下载完成也不等于来源/许可已审核、环境可运行、任务可解或可以直接开始 SFT。

## 1. SWE-smith：现成修复任务，不是现成目标 agent 轨迹

固定 HF 发布：

- [Python README](https://huggingface.co/datasets/SWE-bench/SWE-smith-py/blob/77cab9055d42ab4a5c25c89a8f937096db13558e/README.md)：`77cab9055d42ab4a5c25c89a8f937096db13558e`，11 Parquet，共220,645,767B；README 1,501B。
- [Go README](https://huggingface.co/datasets/SWE-bench/SWE-smith-go/blob/d2f6ecc2cf8ae1af00fc790801bbacfa2913e015/README.md)：`d2f6ecc2cf8ae1af00fc790801bbacfa2913e015`，1 Parquet `data/train-00000-of-00001.parquet`，6,489,675B；README 1,493B；Parquet SHA256 `6e5f18fc1e7c31af8f52923da81017dc6d63c96c1247dcf7129962aa93edd2e3`。
- [固定 toolkit README](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/README.md)、[profile registry](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/swesmith/profiles/__init__.py)、[RepoProfile](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/swesmith/profiles/base.py)。

作者接口 `registry.get_from_inst(task)` → `rp.get_container(task)` 会拉仓库镜像并 checkout 到 instance_id 对应初态。固定实现使用 Docker SDK，创建容器时默认 `mem_limit="10g"`；这不是本题 SWE 正式评测的1CPU/4GB配置，不能混用。仓库镜像与实际任务初始化仍需针对选中任务验收。

这类容器可以给 mini 的 bash 执行器提供环境，但不是已经和本项目 mini prompt/观察/结束动作自动兼容的完整训练管线。真实 teacher 必须实际运行命令并记录返回值；不能只把 reference patch 改写成对话。

Parquet 内有训练任务的参考 patch 与测试列表。可以存为独立训练任务资产，但之后用于 task-dev 的 gold 与验证逻辑只进入评分侧，agent 只拿任务说明与初态；train/dev 先按原任务/repo 分组，再采轨迹，不能先生成后随机按行切分。

语言分仓 card 均声明 MIT，上游 repo 许可仍需保留。先排除 SWE Pro 全部11个 repo 及其 fork/改名/PR/commit 同源，再做跨源分组。经典 SWE-bench 作者发布不等于它是本题 SWE Pro 测试集，也不等于已经完成本题去污染。

旧 monorepo `SWE-bench/SWE-smith@ea6d7173829c7ec8fa16c22055699ff2e9188091` 的卡片 metadata=59,136，正文50,137、toolkit README约52K，且已建议迁至语言分仓。本轮不再下载旧mono；以上不同版本数量分别记录，不混报。

## 2. Nemotron：优先下载 mixed 六个真实任务包

固定来源：[任务卡](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/blob/7e53648e183cee7bcb0aed623cc91a121d37fa38/README.md)，revision `7e53648e183cee7bcb0aed623cc91a121d37fa38`，CC BY 4.0，无门禁。它是任务包，和已下载的 `nvidia/Nemotron-Terminal-Corpus` 教师轨迹是不同发布物。

| 路径 | bytes | SHA256 |
| --- | ---: | --- |
| skill_based/mixed/data_processing.tar.gz | 3,426,312 | c063d69b65b39f7c26667d65c18e2c553291d1755514936eaca8c8bc48c7da0a |
| skill_based/mixed/data_science.tar.gz | 6,196,655 | 632bd4fd0898f46df0a3fc24ae2beab777bdf280e37fd2577e9d59d9b698ceb7 |
| skill_based/mixed/debugging.tar.gz | 6,885,891 | 5d230bc87b2300f7abac0965beef9edc57e3de2e834779dd8a70369e99ce43e9 |
| skill_based/mixed/file_operations.tar.gz | 3,752,713 | dd5a65652d30fa3965275ab58ad8c6a66b43f5e7d150dd0d3499b1cdf9a6eb72 |
| skill_based/mixed/scientific_computing.tar.gz | 3,080,893 | ace6c6815d48d394123e98fd1033f046901baad3c306e72b689e3cc37ebc5c1d |
| skill_based/mixed/security.tar.gz | 4,592,715 | df82414c48b95de59645a17a824c96f294d77412921ecce04201402614e697b7 |

其余 easy.tar.gz=110,525,687B；medium_shard1=704,025,716B、medium_shard2=188,396,953B，本轮不必为拿小试点先下全部约1.031GB。

任务卡明确提供自然语言 instruction、环境目录和 pytest 检查，使用9类共享领域镜像。[作者论文](https://arxiv.org/html/2602.21193v1)说明其终端轨迹用 Terminus2 生成；但目标固定 Harbor/Terminus2、模型消息协议与任务包恢复仍需实测，不能以卡片替代验收。

**任务与已下载 Corpus 轨迹可能是同一批或同任务族。** task-dev 不能简单从任务包随机留出，然后保留所有 Corpus 轨迹训练。必须跨这两个发布物联合对齐任务ID、prompt/模板族与源任务，dev 对应的所有轨迹一并排除。未能可靠映射的来源不能声称已严格隔离。

可参考已有一手 HPC 工程：[NVIDIA-NeMo/Gym harbor_agent README](https://github.com/NVIDIA-NeMo/Gym/tree/main/responses_api_agents/harbor_agent)。其文档有 Nemotron mixed/scientific_computing + Harbor/Terminus2 + custom Singularity 环境路线，以及镜像构建清单、rewrite_task_tomls 脚本。该文档此次读取的是 main，未额外固定代码版本，故只作为后续候选，不作为已安装/已兼容/可直接替代本题固定 Harbor 的证据；本轮只取任务资产，不扩装 NeMo 或 RL。

## 3. D3-Gym：565个科研任务的 metadata 很小，实际环境另取

固定来源：[任务卡](https://huggingface.co/datasets/osunlp/D3-Gym/blob/8499689ac98882a7cac9b5ef9e93365cc37df57e/README.md)，revision `8499689ac98882a7cac9b5ef9e93365cc37df57e`。单文件 `data/train-00000-of-00001.parquet`=2,254,947B，SHA256 `a749576292494b301093fb8f037e2cf61016d89ffab86f3482e7aa27557423a9`；README 2,579B。

这份 Parquet 是任务说明/数据预览/评估代码/来源目录，不包含完整输入数据、预装依赖和所有 gold 工件。[固定代码 README](https://github.com/OSU-NLP-Group/D3-Gym/blob/5c981359b0e1cde597e7f1142bb8ddc7ea0c3cdb/README.md)给出的完整环境位于 `hananemoussa/d3-gym:task_N` Docker Hub 镜像；接口是提交 solution.py，读取输入并输出 pred_results，由 run_and_eval 判分。镜像总体大小与各 tag digest 本轮未核，不全量拉565镜像。

它不是 ASI 原生任务包；要使用选定的 ASI CLI agent，还需要独立任务 wrapper/输入输出契约和真实工具反馈记录。镜像自带 eval_script/gold_results，运行时必须隔离评分资产，不能让 agent 读取 gold 后复制结果。

数据卡声明 MIT，但作者 README 同时列出39个无许可、43个GNU家族等原始 repo，不可用总 MIT 覆盖这些来源。metadata有 original_repo，后续按可信许可和 ASI 同源排除筛选。现有 D3-Gym-Trajectories 的 schema 没有 task_id/original_repo，因此不能只过滤 metadata 就宣称旧轨迹也同步去污染。

## 4. Endless Terminals：2,492个Harbor任务，跳过solution可节省88%下载量

固定[HF文件目录](https://huggingface.co/datasets/obiwan96/endless-terminals/tree/26ecf78458e7f756e4d06780d5fbf3dd78e91815)，revision `26ecf78458e7f756e4d06780d5fbf3dd78e91815`；[固定生成器 README](https://github.com/kanishkg/endless-terminals/blob/99f4c74b75faacf21e53d3dc01df170902e924cb/README.md)。

根据全部文件索引（未读取题面/答案内容）：2,492个唯一任务目录，每份恰有以下8个非solution文件：

- instruction.md、task.toml；
- environment/Dockerfile、container.def、task.json、test_initial_state.py；
- tests/test.sh、test_final_state.py。

加根目录 README/.gitattributes，共19,938文件、49,514,693B。仓库全量25,090文件、405,939,997B；其中 solution/ 下5,152文件、356,425,304B，含 solve.sh 和教师 summary JSON。因此不使用无过滤全量 snapshot，避免为拿任务同时拉一大批教师轨迹。

HF README 是普通文本后附 license:mit，API cardData=null；只记录 README 声明 MIT，不说成规范 frontmatter 已成功解析。生成器仓库则声明 Apache-2.0，二者分别保留归属。

HF包目录是Harbor形态，可用于目标Terminus2候选任务；生成器自己的agent动作是type/command/timeout_sec，不把它的解题轨迹当作原生Terminus2。没有找到已验证的官方整仓归档下载入口；大量小HTTP文件的成本高于6个Nemotron压缩包，因此本轮优先后者。环境构建与测试有效性仍未验收。

## 下载后最小处理顺序

1. 校验固定 revision、文件大小/SHA；只列归档成员和 Parquet schema/行数/来源字段，不展示或用 gold 来筛正式benchmark。
2. 跨任务包和已有教师轨迹，按 repo/原任务/模板族联合分组，排除正式评测同源；先决定 train/dev，再采示范。
3. 对选中独立任务核环境、镜像digest和验证器；任务可直接下载不代表无需环境准备。
4. task-dev只要任务与可信评分器；val-loss/训练才需要独立teacher解答。之后才用Codex子代理或其他teacher实际解题并保留真实操作记录，采样/判分开销另记。

本文件不改变正式四benchmark任务集、资源预算或评分协议，不把这些独立训练来源替换为新的正式测试集。


## 本次实际下载与结构审计完成

截至2026-10-15 22:36:40北京时间的下载回执，80的 `artifacts/tasks/download_receipts.json` 记录本轮选定4来源共23文件、257,332,473B，失败0；下载器记录了实际SHA256，并对有上游LFS SHA的资产核对一致。下载完成对象为SWE-smith Python/Go的12个Parquet＋各README、D3的1个Parquet＋README、Nemotron mixed六压缩包＋README。

`artifacts/tasks/structure_audit.json` 已核Parquet footer与六包tar成员目录，没有解压、读取任务/参考答案内容或执行验证器。SWE Python为50,908行、Go为8,212行；这些是任务记录，不是本项目已采集的teacher轨迹或已验收成功任务。D3为565行，仅metadata，完整输入数据/依赖环境仍在镜像。

| Nemotron mixed任务包 | instruction.md | task.toml | tests/test.sh basename | Dockerfile basename |
| --- | ---: | ---: | ---: | ---: |
| data_processing | 1,000 | 1,000 | 1,000 | 1,000 |
| data_science | 1,000 | 1,000 | 1,000 | 1,000 |
| debugging | 1,000 | 1,000 | 1,000 | 1,002 |
| file_operations | 997 | 997 | 997 | 997 |
| scientific_computing | 1,000 | 1,000 | 1,000 | 1,000 |
| security | 987 | 987 | 987 | 987 |
| 合计 | 5,984 | 5,984 | 5,984 | 5,986 |

六包共60,581个普通文件，成员声明未压缩字节合计104,042,096B。Dockerfile列是全部basename计数，debugging含2个额外同名文件，不能将Dockerfile总数当作任务数；任务数以instruction/task.toml一致的5,984条目录入口计。这里仅证明结构存在，未证明验证器有效、任务可解或runtime兼容。

本次任务包下载未拉取或构建任何容器镜像，也未启动包内teacher采集、模型API或训练；此前单独的Rich子代理试点见 agent_teacher_capture_review.md。Endless下载状态为 `partial_stopped`，仅有部分文件，不计作就绪任务包，也不混入上述23文件完成统计。


归档完整性：19个LFS数据文件的大小与上游SHA-256已匹配；4个README另外按Git blob SHA-1核对匹配。可版本控制的下载与结构摘要见 `analysis/source_snapshots/task_package_download_20261015.json`，原始包/完整回执留在80的ignored artifacts，不提交Git。
