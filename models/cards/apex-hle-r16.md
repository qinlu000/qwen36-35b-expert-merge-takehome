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
- qwen3_5_moe
- research
- hle
---

# APEX Academic r16

An academic-answering LoRA adapter intended for broad reasoning evaluation. Training supervision is text-only; the base visual encoder and multimodal processor remain unchanged.


## Artifact and base

This repository contains a PEFT LoRA adapter; full base weights are not included. Base: [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), frozen model/tokenizer/processor revision`995ad96eacd98c81ed38be0c5b274b04031597b0`. Selected checkpoint: 250. The saved adapter contains 620 FP32 tensors across 310 modules, 21,166,080 parameters (84,760,832-byte safetensors file).

LoRA configuration:`r=16`, `lora_alpha=32`, scaling`alpha/r=2`, dropout 0.05, bias`none`, ordinary LoRA (no DoRA/RS-LoRA), task type`CAUSAL_LM`, no `modules_to_save`. Targets are language self-attention q/k/v/o projections, linear-attention in_proj_qkv/in_proj_z/in_proj_b/in_proj_a/out_proj, and shared-MLP gate/up/down. Router, routed-expert weights, visual encoder and aligner are frozen. Exact target regex:

```text
model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))
```

## Training and checkpoint choice

The native minimum-loss checkpoint was 16, but the frozen delivered checkpoint is 250. An already completed independent 100-question development comparison gave checkpoint 250: 48 correct versus checkpoint 16: 43 correct with 2 invalid (upper bound 45). That fixed choice precedes formal HLE evaluation; no new task validation or formal feedback selected it. These development counts are not a formal HLE 2500 score.

Native run: 2 H100 GPUs, gradient accumulation 4, global batch 8; 250 completed optimizer steps. Exported train 2000; native loaded train 2000; native loaded SFT validation 100.

All experts used one SFT epoch, global batch 8, per-device batch 1, AdamW (`adamw_torch`), learning rate 1e-4, cosine decay, warmup 0.03, weight decay 0.1, gradient checkpointing, DeepSpeed ZeRO-3, SDPA and Liger. Seeds were 20261016 for training and data. Packing and padding-free mode were disabled; length grouping was enabled. Full sequences exceeding 65,536 tokens were deleted rather than silently truncated. Data preparation also checked an 8,192-token assistant-output ceiling. Native eval/save occurred every 16 steps and at the final step. Exported-row counts and native loaded-row counts are reported separately; neither is a per-batch exposure trace.

The native recipe set `enable_thinking=false`, `preserve_thinking=false`, `add_non_thinking_prefix=true`, and `loss_scale=default+ignore_empty_think`. Hidden reasoning fields and closed leading `<think>` blocks were removed during preparation; legitimate visible explanations, tool observations, and Terminal analysis/plan fields were retained. Original teacher collection modes remain recorded separately: converting supervision to nonthinking does not mean every teacher was collected in nonthinking mode.

## Data and cleaning evidence

All 2,000 exported rows were loaded; SFT validation contains 100 fixed rows. Composition:

| Source and frozen version | Rows | Supervision |
| --- | ---: | --- |
| [Nemotron-SFT-Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/README.md),`84d42ad0cb960f07f951b9baa9ed2b46a5a18c66` |817|Publisher DeepSeek-V4-Pro High, no-tool final/reference match|
| [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/blob/b189ec765aa7ed75c8acfea42df31fdae71f97be/README.md),`b189ec765aa7ed75c8acfea42df31fdae71f97be` |884|722 previously accepted DeepSeek-V4-Pro High answers plus 162 publisher reference short answers|
| [Nemotron-SFT-Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/6536a5021222a94126968e8c92f29ee47fc8a7df/README.md),`6536a5021222a94126968e8c92f29ee47fc8a7df` |201|DeepSeek-V4-Pro finals; effort unrecorded|
| [DeepSeek-V4-Pro-Reasoning-8000x](https://huggingface.co/datasets/trjxter/DeepSeek-V4-Pro-Reasoning-8000x/blob/7329257a28babc5998be072a3d8add1dd8ad0fda/README.md),`7329257a28babc5998be072a3d8add1dd8ad0fda` |82|Personal-publisher teacher claim; effort undisclosed|
| [GLM-5.1-Reasoning-1M-Cleaned](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned/blob/f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d/README.md),`f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d` |16|Personal-publisher teacher claim; original question lineage incomplete|

Categories are Math 817, Biology/Medicine 224, Computer Science/AI 193, Other 186, Physics 184, Humanities/Social Science 175, Chemistry 132, Engineering 89. Public input exact/13-gram and family exclusions were used; no formal HLE answers were used as training supervision. This is an academic proxy mix, not a claim to match HLE difficulty or image distribution. MMLU-Pro test/validation was repurposed into project train/validation and cannot also be called a held-out MMLU-Pro evaluation here. No new teacher API generation was needed for this final 2,000-row assembly. The 162 short references are not complete reasoning trajectories. Complete source-template tokens total 1,125,593, max 4,043; no truncation was used.

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

For vLLM use the full multimodal base and `--enable-lora --max-lora-rank 16`, plus a named alias for this adapter and the supported fused projection mapping. The project's BF16 serving casts saved FP32 factors to BF16; that runtime precision differs from the stored files.

## License and attribution

The [frozen base model](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) declares Apache-2.0. The source disclosures below retain their separate licenses and provenance limits; a dataset-card label does not replace upstream code/question attribution. Original adapter contributions are offered under Apache-2.0 to the extent the publisher holds those rights; the accompanying LICENSE and NOTICE.md preserve the separate base/source terms. The HF `other` label describes that scoped grant plus upstream notices, not a blanket Apache license for all training sources. Raw training corpora, evaluation answers, private logs, credentials and base-model weight files are excluded from the adapter delivery.

Recorded source labels: Math-v4 CC-BY-4.0 (817 rows); MMLU-Pro MIT dataset card (884); Science-v2 CC-BY-SA4.0 (201); the two personal-publisher datasets declare Apache-2.0 (98). Original forum/question lineage is incomplete for parts of these sources, so publisher licenses must not be presented as proof that every underlying question can be freely redistributed. Preserve attribution and review share-alike/source obligations before release.

Model repository: [csminion/apex-qwen36-hle](https://huggingface.co/csminion/apex-qwen36-hle).
