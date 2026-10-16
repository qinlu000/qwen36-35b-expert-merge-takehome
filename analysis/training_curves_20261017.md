# 四专家与 Mixed 的原生 SFT 曲线

截至2026-10-17 02:23 CST，五个原生训练任务均已正常完成。图、CSV和原生逐步loss由同一份`trainer_state`/run summary导出，没有平滑、删除波动或补造step0。这里的val是训练留出样本的监督交叉熵；独立任务级val benchmark已按用户要求取消。

| 模型 | 原生train/val条数 | 完成步数 | 最低val loss（step） | 最后val loss | 固定使用checkpoint | run wall小时 | run wall×GPU小时 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SWE | 1993 / 87 | 249 | 0.317680（249） | 0.317680 | 249 | 2.024 | 8.096 |
| Terminal | 2000 / 42 | 250 | 0.422917（250） | 0.422917 | 250 | 1.994 | 7.976 |
| HLE | 2000 / 100 | 250 | 2.002192（16） | 3.497519 | 250 | 1.548 | 3.095 |
| ASI | 1073 / 20 | 134 | 0.582683（128） | 0.582879 | 128 | 0.818 | 1.637 |
| Mixed | 7066 / 249 | 883 | 1.218496（64） | 1.672463 | 883 | 6.434 | 25.738 |

条数是native预处理后的Dataset行数，不是实际每行曝光次数。SWE原始2000条中7条被Swift的role配对检查过滤，Mixed继承相同过滤。四专家单次训练均为1epoch；Mixed使用同一四份数据的并集、相同global batch8和共享rank16配方，排除在合版输入之外。

HLE250的固定选择来自取消前已经完成的独立100题结果：48 correct；cp16为43 correct+2 invalid，即使两条全对也只有45，因此选择不依赖正式HLE反馈。最低CE的cp16仍保留。Mixed使用完整一轮的final883作为训练对照，不能把只训练64步的最小loss checkpoint说成完成同等训练量的对照。

HLE的train答案和val短gold格式不一致，因此CE升高不能单独解释为任务准确率下降。Mixed的CE同样受这100条HLE留出样本影响；跨域loss数值不直接比较能力。后续合版rank消融只使用既有249条SFT留出数据，不重新构造或运行任务级val。

## 图与原始数据

| 模型 | 图 | CSV | 原生记录 |
| --- | --- | --- | --- |
| SWE | [PNG](../curves/training_20261017/swe.png) | [CSV](../curves/training_20261017/swe.csv) | [JSON](../curves/training_20261017/source/swe_loss.json) |
| Terminal | [PNG](../curves/training_20261017/terminal.png) | [CSV](../curves/training_20261017/terminal.csv) | [JSON](../curves/training_20261017/source/terminal_loss.json) |
| HLE | [PNG](../curves/training_20261017/hle.png) | [CSV](../curves/training_20261017/hle.csv) | [JSON](../curves/training_20261017/source/hle_loss.json) |
| ASI | [PNG](../curves/training_20261017/asi.png) | [CSV](../curves/training_20261017/asi.csv) | [JSON](../curves/training_20261017/source/asi_loss.json) |
| Mixed | [PNG](../curves/training_20261017/mixed.png) | [CSV](../curves/training_20261017/mixed.csv) | [JSON](../curves/training_20261017/source/mixed_loss.json) |

来源索引为[manifest](../curves/training_20261017/source/manifest.json)，训练矩阵为[配置](../configs/train/four_experts_v1.json)。五份PNG均已生成；最终Mixed图已目视检查，原四专家图此前已检查。

## 计时边界与复现

`wall_seconds`来自`run_sft.py`启动native子进程到正常返回的monotonic计时，含该run的模型加载、训练、周期val和保存；不是完整Slurm分配时长。表中GPU小时只累计这五个成功run，合计约46.542；早期失败/被替代训练、推理服务和评测必须另加，不能据此宣称项目总成本。

日志`memory(GiB)`语义已核对运行时Swift源码：`trainers/patcher.py:27–29`历史取max，`utils/torch_utils.py:434–440`调用`torch.cuda.max_memory_reserved`；本轮torchrun的`LOCAL_WORLD_SIZE>1`使设备列表仅为当前设备，且只有rank0写日志。因此数值是**rank0当前CUDA设备的PyTorch allocator peak-reserved GiB，自最近reset计、四舍五入两位**，不是allocated、所有rank最大值或完整设备峰值。SWE/Terminal/HLE/ASI/Mixed分别为61.42/55.35/42.38/43.26/55.34 GiB；原始值保留在JSON。`skip_memory_metrics=true`下HF内存tracker不会重置该峰值。

在有训练产物的计算环境中导出，然后在装有matplotlib的环境绘图：

```bash
python scripts/export_training_histories.py --project . --output curves/training_20261017/source
python scripts/plot_sft_loss.py --result curves/training_20261017/source/mixed_loss.json \
  --output-prefix curves/training_20261017/mixed --title 'MIXED SFT: one epoch, nonthinking'
```

其他四份仅替换模型名。无需模型API、GPU或任务沙箱。
