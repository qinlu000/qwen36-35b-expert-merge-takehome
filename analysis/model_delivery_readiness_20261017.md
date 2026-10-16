# 模型交付就绪核对（2026-10-17）

本分支已完成配置/来源核对、五份模型卡与许可材料，并在主线程审核和明确授权后创建、上传并验收了5个Public HF仓库；没有修改源训练产物或运行中的模型服务。原始用户HTML附件的要求优先于后来变化的线上模板README：以模板为来源建立独立GitHub仓库，并交付四专家与合版共5个Public HF模型仓库；不将现有工作改成线上后来加入的stage2。主线程计划先用Private独立GitHub仓库保护审核材料；这不改变5个模型Public的交付目标。

## 已形成的可审阅材料

- `models/README.md`：五产物索引、实际来源、加载说明边界、许可来源表和发布清单。
- `models/cards/apex-{swe,terminal,hle,asi}-r16.md`：四份已发布HF README的本地副本。
- `models/cards/apex-avg-r64.md`：固定主合版已发布HF README的本地副本。
- `models/release_manifest.json`：源adapter相对目录、实际rank/alpha/参数量/文件字节数、真实HF ID/immutable revision、允许公开文件和config改写项。
- `analysis/source_snapshots/model_card_training_evidence_20261017.json`：从实际四run的`training_config.json`、原生`training/args.json`、选定checkpoint的`adapter_config.json`与完成`summary.json`提取的核对记录；机器路径已转为项目相对路径，无训练正文或凭据。

5个正式HF ID均未发生同名冲突，已使用原拟定名称公开发布。实际URL、immutable revision与匿名读回记录见文末及`models/release_manifest.json`。独立GitHub仓库创建由主线程负责，本文不虚构尚未登记的GitHub地址。

## 实际权重与训练核对

| 产物 | 实际选中 | 原生best /最终 | 导出train /加载train /SFT val | 完成steps | GPU数 /GA |
| --- | --- | --- | --- | ---: | --- |
| SWE |249|249 /249|2000 /1993 /87|249|4 /2|
| Terminal |250|250 /250|2000 /2000 /42|250|4 /2|
| HLE |250|16 /250|2000 /2000 /100|250|2 /4|
| ASI |128|128 /134|1073 /1073 /20|134|2 /4|
| AVG64 |固定四源合版|不涉及新优化器选择|继承上述四份；加载行数合计7066|0新增|CPU合版|

SWE的7条是原生Swift角色配对删除，不是额外epoch、重复补齐或超长截断。Terminal/HLE实际日志的首个Dataset计数分别为2000/42与2000/100，未沿用旧报告“Terminal待确认”。HLE250沿用已完成独立dev：48 correct；cp16为43 correct+2 invalid，upper bound45。该选择与AVG64固定配方均先于正式benchmark反馈。没有重新跑task-val。

四个专家实际均为ordinary LoRA r16/alpha32/dropout0.05，310语言目标模块、620张量、21,166,080参数，safetensors全部FP32、各84,760,832字节。目标仅attention、linear attention与shared expert投影；router/routed experts/vision/aligner未新增训练目标。实际recipe为BF16、global8、一epoch、LR1e-4、cosine/warmup0.03、weight_decay0.1、AdamW、ZeRO-3、SDPA/Liger、gradient checkpointing、seed20261016、不packing、完整窗口65536，overlength delete。非思考配置与隐藏reasoning清理在卡片单列，未把原始High/thinking教师改称Non-Think教师。

AVG64实际r64/alpha64/scaling1、84,664,320 FP32参数、338,754,768字节。数学为每矩阵`M=Σ0.25×(32/16)BiAi=0.5ΣBiAi`；`A64=0.5 stack(Ai)`、`B64=concat(Bi)`，无交叉项、无SVD截断。rank64的adapter容量是单个rank16专家/Mixed的4倍。AVG16是另一个压缩消融，不冒充五产物中的主合版。既有serialization/dense诊断来自`analysis/merge_execution_20261017.md`和`analysis/source_snapshots/merge_export_20261017.json`，本轮未重新哈希或重做合版。

未把原生约61GiB等trainer内存字段改称所有GPU同步实测peak，也未给出未验证的显存需求保证。

## 数据与许可事实

核对实际train provenance与summary，未读取或公开原始问题/答案正文。主要证据：`analysis/training_data_report_20261016.md`、`analysis/data_audit_swe_20261016.md`、`analysis/hle_existing_2k_execution_20261016.md`、`analysis/asi_expand_20261016.md`、`configs/data/scienceagentbench_sft_v1.json`。

- SWE：Open-SWE固定revision，2000导出/1993加载；发布方CC-BY4.0，原仓库Apache/MIT/BSD许可单独保留。
- Terminal：Horizon1107（Apache2.0）＋Pivot893（CC-BY4.0），实际1303来源任务族；原生released completion并不补造未发布确认尾部，未称本地全量replay已通过。
- HLE：Math-v4 817（CC-BY4.0）＋MMLU-Pro884（MIT dataset card；其中722已接受High回答、162参考短答案）＋Science-v2 201（CC-BY-SA4.0）＋个人发布者V4-Pro82/GLM16（Apache2.0卡片声明）。Science/broad未知effort与题源追溯缺口均披露。
- ASI：SAB82中76条CC-BY4.0，6条保留原许可（matminer1、rasterio5）；DS-1000 976为CC-BY-SA4.0；SciCode15为Apache2.0。原始code canary/归属须保留，不能统称82条全CC-BY。辅助函数/库补全未称近千个完整科研环境。
- DS-1000 test、SciCode validation、项目重分区的MMLU-Pro已用作训练，不再作为独立同名held-out评测。exact/13gram/族排除不等于完整语义无污染。

卡片仅报告已有来源标签，不推出一份统一模型许可或所有上游可自由重传的法律结论。已形成可直接stage的方案：五份HF卡均使用`license: other`、`license_name: apache-2.0-adapter-contributions-plus-upstream-notices`、`license_link: LICENSE`。`models/LICENSE`仅对发布者可授予的原创adapter贡献使用标准Apache-2.0；`models/licenses/APACHE-2.0.txt`附官方全文；`models/notices/`分别准备五份NOTICE，原base及源条款不变，不另设research-only/非商业限制，不把全部材料套一份Apache。原始训练包、benchmark包及私有原生日志不在发布文件清单内。

## 加载API核验与边界

只读核了已装Transformers5.15.1 `modeling_auto.py`：`MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING_NAMES`将`qwen3_5_moe`映射到`Qwen3_5MoeForConditionalGeneration`；PEFT0.20.0 `PeftModel.from_pretrained`实际接受显式base model、model_id、is_trainable与autocast_adapter_dtype等参数。卡片示例使用固定base revision＋`AutoModelForImageTextToText`＋`AutoProcessor`＋`PeftModel.from_pretrained(base, ".", is_trainable=False)`，保留多模态。

这是API源码核验和文档代码语法检查，不冒称另做了全权重PEFT推理验收。已知vLLM实际alias/图像验收在正式部署证据中，rank16与rank64服务上限区别已披露；服务BF16会cast原FP32因子。

原checkpoint的`base_model_name_or_path`含训练机器位置；四份原生expert配置的`revision`实际为null，冻结由所用base目录与run记录建立；AVG64导出配置已含冻结revision。发布副本已只将该字段改成公共base ID，显式填写冻结revision并保持其余行为配置；当前训练产物和服务没有修改。模型卡和发布清单不包含机器绝对路径、密钥或私有日志。

## 只读身份与权限核验

| 平台 | 当前身份 | 可确认权限 | 核验时间与来源 |
| --- | --- | --- | --- |
| GitHub CLI |`qinlu000`|OAuth scopes含`repo`（另有gist/read:org/workflow），支持个人公开/私有repo写入；未以创建仓库作测试|2026-10-17，本机`gh api --include user`只读响应；只保留身份和scopes|
| Hugging Face |`csminion`|`write`，非fine-grained；支持授权后的模型repo写操作|主线程官方`whoami-v2`验证，约`2026-10-16T18:25:20Z`，CST02:25:20；精确传输receipt未另存，不伪造更高精度|

HF默认cache未发现token的早期观察已被主线程对既有用户凭据的官方验证更新；当前不再把HF身份/写权限列为未知。本文不记录凭据值或其显示名。

身份与scope支持独立GitHub＋五Public HF的技术步骤。主线程随后审核卡片与许可方案并明确授权本分支执行HF发布；已完成下表五仓创建、上传与匿名验收。GitHub操作仍由主线程统一负责；正式分数须等完整有效报告再补。

所有模型卡明确：正式分数待完成、无性能或正确性承诺；SFT loss、独立dev计数、synthetic验收与正式benchmark分开。64K/8K非思考、短solver预算、CPU/RAM限制、替代judge、ASI public-local评分与历史Base调度差异均披露，未将其冒称原榜单协议。


## 已落实的license/NOTICE方案与具体边界

本checkout未找到根LICENSE/NOTICE，Git也没有origin；不能从模板名推导项目代码已有Apache许可。模型发布副本采用上述明确的原创贡献Apache grant＋不变上游条款的`other`元信息。此方案只分发LoRA权重、config、模型卡、LICENSE、NOTICE与标准Apache文本；不分发原始训练/基座权重，因而没有在本次上传中打包需要逐文件复制版权头的数千份代码/问答。

| 明确事实 | 未确认的具体项 | 此次发布处理 |
| --- | --- | --- |
| Qwen固定模型卡明确Apache2.0 |不推出训练源也Apache |保留固定base归属；随包附Apache全文|
| SWE所选导出记录均有MIT/Apache/BSD许可标签；Open-SWE总卡CC-BY4.0 |未逐文件审计所有源repo版权头与fork/改名链 |NOTICE列总卡与原许可分布；原代码/轨迹不上传；不声称逐文件覆盖已核|
| Horizon Apache2.0、Pivot CC-BY4.0均有发布方声明 |完整终端任务/依赖的上游版权链未恢复 |NOTICE保留两个来源、版本与NVIDIA归属；不上传task pack/原历史|
| HLE五源都有卡片/行级许可标签，Science-v2包含CC-BY-SA4.0 |Math/Science部分论坛题目归属与两个人发布者原题lineage不完整；发布卡不能替代上游授权 |NOTICE明确这些范围，保留source revisions/links；不上传题目/回答；不假定未知来源全Apache|
| SAB76条CC-BY4.0，另6条指定matminer/rasterio原许可 |6条参考所对应的精确上游commit/许可文本版本未固定；matminer当前许可含额外enhancement段，不简化成全CC-BY |NOTICE保留1/5条的原链接和版本缺口，不上传原参考代码/canary|
| DS-1000 CC-BY-SA4.0、SciCode Apache2.0明确 |训练参数是否在特定法律下构成CC的Adapted Material，本项目未作确定判定 |CC原条款不变；不宣称SA一定或一定不适用于全部LoRA；原参考代码不上传|
| AVG64是固定四adapter的delta平均 |合版不会消除任一来源边界 |合版NOTICE合并全部四专家来源，不“平均许可证”|

这是具体来源事实披露，不是以抽象不确定性无限阻止发布。源码/题目版权的尚未核项仍保留，不能靠模型卡补造许可。若将来需要公开原训练包，才需按逐来源、逐版权材料另行完成原文再分发notice与条款核对；它不在本次五adapter文件范围内。

条款事实核对仅用于区分范围：[Apache2.0第4条](https://www.apache.org/licenses/LICENSE-2.0)要求保留其适用作品的许可/修改/归属，且NOTICE不改license；[CC BY4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en)与[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en)分别保留适用的attribution与share-alike条件。这里没有从这些原文推导“所有训练权重自动同一许可”。当前[matminer](https://github.com/hackingmaterials/matminer/blob/main/LICENSE)与[rasterio](https://github.com/rasterio/rasterio/blob/main/LICENSE.txt)链接仅补充当前上游文本，不冒充SAB参考的精确历史版本。

上传严格使用manifest的6个文件白名单，已移除卡片的unpublished/draft/pending-creation描述并登记真实repo/commit。正式评测结果仍待完成，未填占位分数。

本轮检查结果：5份卡片均经已装huggingface_hub的ModelCard本地YAML解析；5个PEFT Python例子均经AST语法检查；发布清单5条均有对应README/NOTICE，标准Apache文本11358字节。检查只核文档/metadata，不运行模型、程序或评分。

## 已发布结果与匿名验收

`scripts/publish_hf_adapters.py`默认prepare离线stage；显式`--mode publish`才读取既有凭据并执行官方API创建/上传。逐仓先确认名称不存在；既有非本项目资源不会覆盖。本次五仓均直接使用原拟定名称。receipt支持重复执行识别本次已完成产物；stage只改发布副本的两个base config字段。


| Public HF仓库 | 实际immutable revision | 匿名验证 |
| --- | --- | --- |
| [csminion/apex-qwen36-swe](https://huggingface.co/csminion/apex-qwen36-swe) | `cf6f5bd1a9f6ee13a9e760640dd509b7b2d80c65` | 六文件完整下载、字节与header通过 |
| [csminion/apex-qwen36-terminal](https://huggingface.co/csminion/apex-qwen36-terminal) | `79110026fe20fc7c64a8afc8abcedd94a676c37e` | 六文件完整下载、字节与header通过 |
| [csminion/apex-qwen36-hle](https://huggingface.co/csminion/apex-qwen36-hle) | `026d926ae6ff639b7cdd540863b6c527467f1a36` | 六文件完整下载、字节与header通过 |
| [csminion/apex-qwen36-asi](https://huggingface.co/csminion/apex-qwen36-asi) | `abe468e5531abe8a51fd3b3a110f29159464d31c` | 六文件完整下载、字节与header通过 |
| [csminion/apex-qwen36-avg64](https://huggingface.co/csminion/apex-qwen36-avg64) | `53fbd83b8c6d56d9b24dfccbe58789063f7ca853` | 六文件完整下载、字节与header通过 |

官方匿名API对上述5个commit确认`private:false`、`gated:false`、`library_name:peft`、`pipeline_tag:image-text-to-text`、公共base ID与`base_model_relation:adapter`，license metadata与发布方案一致。只存在6个白名单文件及Hub自动`.gitattributes`；服务器记录的权重尺寸为四专家各84,760,832字节、AVG64为338,754,768字节。

全部完整匿名下载完成时间不晚于`2026-10-16T18:42:34.981500+00:00`；独立官方匿名metadata读取时间为`2026-10-16T18:42:29.550610+00:00`。逐文件尺寸、与stage的stream compare、源权重第二次stream compare、safetensors header均一致。发布config只含既定两个字段改写；未上传原始文本、私有日志、optimizer或base shards。没有额外手动大文件哈希扫描或模型生成，SDK正常上传/下载完整性处理照常执行。

公开可审计receipt：`analysis/source_snapshots/hf_publication_20261017.json`；忽略目录内保留prepare/publication receipt及完整匿名下载副本。模型卡YAML与示例AST通过，不将源码API核验冒称另一次PEFT全模型推理。Git与共享`claud.md`由主线程统一提交，本分支未操作。
