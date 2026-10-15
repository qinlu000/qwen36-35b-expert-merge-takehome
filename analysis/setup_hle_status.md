# HLE 环境配置回执

2026-10-15，实际执行主机 `10.123.4.80`，项目根目录 `/data/caoqinlu/projects/apex-takehome`。已完成固定源码、独立环境、完整 test 文件核验和自造数据检查；没有执行正式题推理或判分。

| 项目 | 已落盘状态 |
| --- | --- |
| 官方源码 | `artifacts/benchmarks/hle/source`，HEAD `22ed3074b1e7b134bcbc09028d0ba320839b0655`，工作区干净，未修改官方文件 |
| Python 环境 | `artifacts/envs/hle`，Python 3.12.13，不继承 system-site-packages |
| 依赖锁 | `scripts/requirements-hle.lock`，44 包；与实装 `artifacts/benchmarks/hle/requirements.freeze.txt` 完全一致；`uv pip check` 通过 |
| 完整数据 | `artifacts/benchmarks/hle/5a81a4c7271a2a2a312b9a690f0c2fde837e4c29/test-00000-of-00001.parquet` |
| 版本及 ID 清单 | 原协议 `analysis/source_snapshots/protocol/hle_task_ids.json` 保留；本轮额外生成同数据目录下 `setup_manifest.json`，ID 集合与原协议一致 |
| 机器回执 | `artifacts/benchmarks/hle/setup_receipt.json`，含版本、源码文件哈希、数据哈希、依赖锁哈希与检查结果 |

完整数据已经由前序步骤下载，本轮复用现有文件并重新核验：274,276,147 bytes，SHA-256 `6d0ee0602e8aea6b159509577e884f48ecac7b8e3f6822a35f51335a446c726a`。只投影读取 `id/image` 两列，得到 2,500 个唯一 ID、342 图像题、2,158 文本题；没有读取真实数据的 question、answer、rationale 或预览图。数据目录权限 0700，Parquet 权限 0600，均在 Git 忽略的 artifacts 中。本轮没有读取、复制或迁移任何凭据。

官方 requirements 固定 `numpy==1.26.4`、`openai==1.57.0`、`datasets==3.2.0`，但未锁传递依赖。直接安装时真实遇到 PyArrow 26 import 报错：要求 NumPy 2，与官方 NumPy 1.26.4 冲突。本环境保留三个官方版本，固定 PyArrow 18.1.0、Hugging Face Hub 0.27.1、Pandas 2.2.3，并补 Pillow 11.0.0；其余依赖全部锁定。锁文件 SHA-256 为 `70dd1b4528c2b7ee18b06a789eb56a132d69c6f2ad4ae15dba1253d19d356fe7`。[官方依赖文件](https://raw.githubusercontent.com/centerforaisafety/hle/22ed3074b1e7b134bcbc09028d0ba320839b0655/requirements.txt)

已通过的检查：

- 官方预测与判分脚本的模块导入、`--help`；检查时只注入假 API key 和不可用的本机地址，没有调用模型。
- 自造两行 Parquet 的 `datasets.load_dataset(...).to_dict()`，以及自造 32×32 PNG 的 Pillow 解码。真实 HLE 数据未经过这一内容读取流程。
- 官方 `format_message` 的文本与图像消息结构。
- 官方 Judge schema 接受有效合成结果，拒绝缺失 strict、非法 correct、strict=false 三种结果；官方 criteria 的合成字符串格式化通过。
- 依赖一致性、完整数据字节数和 SHA-256、全量 ID/图像题计数。

在 80 项目根目录可重放配置或单独复核；命令本身不执行正式评测：

```bash
python3 scripts/setup_hle.py
artifacts/envs/hle/bin/python scripts/setup_hle.py --check-only
```

脚本使用本项目 `artifacts/tools/uv/uv`；首次克隆 GitHub 如需代理，可加 `--proxy http://127.0.0.1:38080`，只影响该进程和子进程。若在新主机缺少 gated 数据，可用 `--credentials <项目外私有文件>` 提供 HF_TOKEN；已有数据时不读该文件。本轮实际没有使用该选项。

当前就绪范围是安装与离线预检。正式运行仍需连接 Base 的图文端点，并把冻结数据 revision、采样参数、每题总 deadline 接入实验 runner。原官方 CLI 未传 dataset revision，temperature 传参被注释，不能直接运行漂移的数据或默认采样后称为本项目冻结协议。候选 DeepSeek Judge 还需实验 JSON adapter；官方 native schema 的 confidence 只有 int 类型，没有 0–100 范围约束，实验 runner 应按既有协议验证。Judge 模型及当前执行规范以 [protocol_v2_unified64k8k.json](../configs/eval/protocol_v2_unified64k8k.json) 与 [evaluation_protocol.md](evaluation_protocol.md) 为准；`protocol_hle_review.md`保留设计依据，v1为历史。本轮没有变更协议或调用付费 API。[官方预测实现](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_model_predictions.py)、[官方判分实现](https://github.com/centerforaisafety/hle/blob/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval/run_judge_results.py)
