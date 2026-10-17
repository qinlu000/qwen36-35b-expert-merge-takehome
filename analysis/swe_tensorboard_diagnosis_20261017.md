# TensorBoard训练诊断：2026-10-17

已将四专家和Mixed共五组原生`log_history`导入本机TensorBoard2.20.0：[SWE训练曲线](http://127.0.0.1:6006/#scalars&tagFilter=%5Etrain%2F&regexInput=%5Eswe%24&_smoothingWeight=0)。原训练没有直接写TensorBoard；这是已有标量的事后导入，没有新训练或模型forward。服务session75430保留运行，绑定127.0.0.1:6006；TensorFlow未安装不影响本次scalars。

|SWE原生日志|实际观测|解释边界|
|---|---|---|
|学习率|249步，第8步达到1e-4，最终0|3% warmup、cosine；不能仅凭此认定LR过大|
|梯度范数|中位数0.15028，最大0.53184，全部有限且非零|无明显梯度爆炸，不能排除行为过度适应|
|训练交叉熵|首步0.44775，末步0.36872|训练诊断，不是任务分数|
|已有teacher-forced eval交叉熵|16次记录，0.38588→0.31768|保留历史诊断，不能用于checkpoint优劣或合版效果判定|
|完整词表Shannon entropy|未记录|不是0；不能由交叉熵倒推，也不能从现有TensorBoard补出|

EventAccumulator逐项核对了249条LR/梯度/loss和16条历史eval记录。页面语义读取确认五组及scalar图已载入，并设置SWE、train标签、smoothing0；ego task58已完成并保留页面。截图超时，未宣称截图目视验收；Codex面板打开状态仅queued。

**用step横轴。** 导入事件的wall_time均为导出时刻，不代表原训练逐步耗时。现有teacher-forced eval只作历史诊断，不恢复已取消的独立task validation，也不按loss选checkpoint。

复现导入：

```bash
python3 scripts/export_training_tensorboard.py --output artifacts/diagnostics/tensorboard-native-training-NEW
python3 -m tensorboard.main --logdir artifacts/diagnostics/tensorboard-native-training-NEW --host 127.0.0.1 --port 6006 --load_fast=false
```

输出目录须全新；如当前6006服务仍在，直接查看已有页面。原JSON日志不变。脚本依赖TensorBoard，源码不训练模型、不填造entropy。精确来源和标量统计见[收据](source_snapshots/swe_tensorboard_diagnosis_20261017.json)。

目前更明确的训练侧发现是[真实样本的模板差异](swe_serialization_parity_20261017.md)：原Swift删除工具链中7个空think壳，HF保留；只在CPU诊断实例调整preserve_thinking后token/label一致。还没有重训，也没有证明该差异解释0/51。下一版如获推进，先扩大编码一致性检查，再在相同修正模板下以2e-5对1e-4做单变量LR对照，不能把模板与LR同时变化后的收益全归给LR。

原生配方为global batch8、1epoch、1993有效样本、r16/alpha32。官方ms-swift的[Qwen3.5-35B-A3B示例](https://github.com/modelscope/ms-swift/blob/main/examples/models/qwen3_5/transformers.sh)也使用1e-4，但该OCR短序列示例不能证明1e-4适合本次64K工具轨迹；2e-5是保守候选，尚未运行。Entropy和相对Base的KL需要额外forward；准备的六固定前缀探针未提交GPU，现先按用户要求看TensorBoard。
