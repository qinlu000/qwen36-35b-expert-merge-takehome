---
library_name: peft
license: other
license_name: apache-2.0-adapter-contributions-plus-upstream-notices
license_link: LICENSE
base_model: Qwen/Qwen3.6-35B-A3B
base_model_relation: adapter
pipeline_tag: image-text-to-text
tags:
- lora
- model-merge
- qwen3_5_moe
- research
---

# APEX Four-Expert AVG r64

This repository contains the fixed primary equal-weight merge of four independently trained domain LoRA adapters. It is a parameter-delta merge on one shared multimodal base, not a new token router or an ensemble of four inference services.


## Base, inputs and capacity

Base: [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), model/tokenizer/processor revision`995ad96eacd98c81ed38be0c5b274b04031597b0`. The four inputs are SWE 249, Terminal 250, ASI 128, HLE 250, each ordinary LoRA`r=16,alpha=32,scaling=2`, weight0.25. Native best-loss checkpoints are 249, 250, 128, 16 respectively; HLE 250 was frozen instead of 16 from the already completed independent development comparison (48 correct versus 43 correct+2 invalid, upper bound 45). No formal benchmark result or new task validation selected the merge.

Output:`r=64,alpha=64,scaling=1`, dropout 0, inference mode, true ordinary LoRA, bias`none`, task type`CAUSAL_LM`. It contains 620 FP32 A/B tensors across 310 language modules, 84,664,320 adapter parameters and 338,754,768 bytes of safetensors. The exact target regex is:

```text
model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))
```

No base/router/routed-expert/vision parameters were changed. The base visual processor remains available; training text does not establish image-specific improvement.

## Merge mathematics and verification

For each target matrix, the intended update is

`M = sum_i 0.25 * (32/16) * B_i A_i = 0.5 * sum_i B_i A_i`.

The delivered factors are`A64 = 0.5 * stack_rows(A1,A2,A3,A4)` and`B64 = concat_columns(B1,B2,B3,B4)`. Because output scaling is 1,`B64 A64 = M`; there are no cross terms and no rank truncation. Do not average A and B separately or apply the input scaling a second time. Output factors remain FP32. Serialization reload was bitwise equal to the generated factors; all 310 modules had source-block correspondence checked. A 16-row-per-module dense diagnostic gave global relative residual 1.6062e-7, consistent with floating-point calculation rather than an SVD truncation claim.

Rank 64 has four times the adapter parameter capacity of each rank 16 expert or the Mixed rank 16 control. Improvements, if established later, cannot be attributed solely to specialization. A separate AVG-SVD-r16 is a compression/capacity ablation, not the primary release: alpha16/scaling1, truncated-SVD relative Frobenius error 0.144715145. No rank, weight, density or scale search was performed. This merge adds no optimizer training or extra examples.

## Source training and data

Inputs share one epoch, global batch 8, learning rate 1e-4, cosine schedule, warmup 0.03, weight decay 0.1, AdamW, ZeRO-3, SDPA, Liger, BF16 and 65,536-token training window. SWE/Terminal used 4 GPUs and accumulation 2; ASI/HLE used 2 GPUs and accumulation 4. Seeds 20261016; no packing; gradient checkpointing; ordinary LoRA16/32/dropout 0.05. Nonthinking preparation/settings match the expert cards.

| Input | Exported / native loaded train | SFT validation | Data |
| --- | ---: | ---: | --- |
| SWE 249 |2000 /1993|87|Open-SWE Qwen3.8-Flash-Next success-labelled repository repair; 7 role-pairing rejections|
| Terminal 250 |2000 /2000|42|TerminalHorizon1107 +Terminal-Pivot893; 1303 source task/family keys|
| ASI 128 |1073 /1073|20|Human ScienceAgentBench82 +DS-1000 976 +SciCode15|
| HLE 250 |2000 /2000|100|Math-v4 817 +MMLU-Pro884 +Science-v2 201 +V4-Pro82 +GLM16|

The union has7,066 native loaded rows; these counts are not independent environment counts or exact batch-exposure counters. Hidden reasoning fields/closed leading think blocks were removed; visible explanations and native tool histories remain. Original teacher modes are retained as provenance. Full source-template tokens are not Swift label/compute counts. Dataset card/source attribution and frozen revisions are listed in each input card and the delivery README; the merge inherits every source limitation. In particular, DS-1000 test, SciCode validation and project-partitioned MMLU-Pro are training sources here and must not simultaneously be reported as held-out evaluations.

## Evaluation scope and limitations

All formal benchmark scores remain pending completion. No completed four-benchmark performance claim or performance/correctness guarantee is made in this card. Formal evaluation was launched separately; incomplete runs and SFT validation losses are not final benchmark scores. Frozen checkpoint choices were used; no new task-level validation benchmark selected this release.

The project comparison uses BF16, nonthinking, 65,536 total context /8,192 output per main or helper call. This is a resource-constrained protocol, distinct from publisher leaderboards. SWE uses Pro V2 HARD-51 with locked mini-swe-agent2.4.6,30-minute solver budget and fresh patch replay. Terminal uses 89 tasks×5 seeds, Terminus2, 30 minutes, 4 CPU/8 GiB and native summaries; this differs from larger official/publisher resource settings. HLE retains all 2,500 questions, including 342 images, no tools and 300s per question; its replacement judge is school-hosted DeepSeek-V4-Flash. ASI uses 60 public tasks×B1–B4, official instance seed 31415, native DirectLLM, 4 CPU/8 GiB and a continuous 1,200s generation+execution budget; public local scoring uses the existing external DeepSeek mapping rather than the official hosted scorer. Scorer infrastructure failures remain invalid/null rather than scored zeros. Scheduling changed across historical Base phases; per-run runtime records must accompany comparisons.

Training data length filtering, source quality labels and public-input overlap exclusions do not prove semantic independence or successful replay. The unchanged base visual encoder is not evidence of image-specific SFT gains. Generated code/commands require the same isolated execution and checking as other code models. No all-GPU peak-memory measurement is asserted: a trainer's per-rank memory log is not a synchronized peak across every card.

## Loading

Run from the downloaded adapter directory, containing `adapter_config.json` and `adapter_model.safetensors`:

```python
import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

BASE = "Qwen/Qwen3.6-35B-A3B"
REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"
processor = AutoProcessor.from_pretrained(BASE, revision=REVISION)
base = AutoModelForImageTextToText.from_pretrained(
    BASE, revision=REVISION, dtype=torch.bfloat16,
    device_map="auto", trust_remote_code=False,
)
model = PeftModel.from_pretrained(base, ".", is_trainable=False).eval()
messages = [{"role": "user", "content": "What is 17 + 25?"}]
inputs = processor.apply_chat_template(
    messages, tokenize=True, add_generation_prompt=True,
    return_dict=True, return_tensors="pt",
    enable_thinking=False, preserve_thinking=False,
).to(model.device)
torch.manual_seed(0)
with torch.inference_mode():
    output = model.generate(
        **inputs, max_new_tokens=8192, do_sample=True,
        temperature=0.7, top_p=0.8, top_k=20,
        min_p=0.0, repetition_penalty=1.0,
    )
new_tokens = output[:, inputs["input_ids"].shape[1]:]
print(processor.batch_decode(new_tokens, skip_special_tokens=True)[0])
```

The installed source was checked for Transformers5.15.1's `qwen3_5_moe` → `AutoModelForImageTextToText` mapping and PEFT0.20.0's `PeftModel.from_pretrained(model, model_id, is_trainable=False)` API. This example was source-checked; it was not a new full-weight PEFT generation test. Preserve the multimodal base/processor for image questions. Supplying the base explicitly avoids relying on a training-machine path in an unprepared export. The release copy must replace that config path with the public base ID and explicitly pin the frozen revision. The adapter alone cannot run without the base weights. Device placement and memory must fit the full base, not merely its activated MoE parameters.

For vLLM use the full multimodal base,`--enable-lora --max-lora-rank 64` and the supported fused projection mapping. A service limited to rank 16 cannot load this adapter. The project statically registered this artifact as`apex-avg64`; text, image tokenization and nonthinking generation were accepted on a dedicated BF16/TP2 service. Those synthetic transport checks are not performance benchmarks. BF16 serving casts the stored FP32 factors.

## License and attribution

The [frozen base model](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) declares Apache-2.0. The source disclosures below retain their separate licenses and provenance limits; a dataset-card label does not replace upstream code/question attribution. Original adapter contributions are offered under Apache-2.0 to the extent the publisher holds those rights; the accompanying LICENSE and NOTICE.md preserve the separate base/source terms. The HF `other` label describes that scoped grant plus upstream notices, not a blanket Apache license for all training sources. Raw training corpora, evaluation answers, private logs, credentials and base-model weight files are excluded from the adapter delivery.

The merge inherits the four input source disclosures: Open-SWE CC-BY4.0 plus underlying MIT/Apache/BSD code notices; Horizon Apache2.0 and Pivot CC-BY4.0; SAB CC-BY4.0 plus 6 original-license rows, DS-1000 CC-BY-SA4.0, SciCode Apache2.0; Math-v4 CC-BY4.0, MMLU-Pro MIT, Science-v2 CC-BY-SA4.0, and personal-publisher Apache2.0 declarations with incomplete underlying question lineage. No aggregate license is inferred by averaging weights.

Model repository: [csminion/apex-qwen36-avg64](https://huggingface.co/csminion/apex-qwen36-avg64).
