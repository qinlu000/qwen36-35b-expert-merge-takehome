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
- swe
---

# APEX SWE r16

A repository-repair LoRA adapter trained on complete public bash-tool trajectories. The underlying model remains the same multimodal MoE base; this adapter does not add a new router or routed expert.


## Artifact and base

This repository contains a PEFT LoRA adapter; full base weights are not included. Base: [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), frozen model/tokenizer/processor revision`995ad96eacd98c81ed38be0c5b274b04031597b0`. Selected checkpoint: 249. The saved adapter contains 620 FP32 tensors across 310 modules, 21,166,080 parameters (84,760,832-byte safetensors file).

LoRA configuration:`r=16`, `lora_alpha=32`, scaling`alpha/r=2`, dropout 0.05, bias`none`, ordinary LoRA (no DoRA/RS-LoRA), task type`CAUSAL_LM`, no `modules_to_save`. Targets are language self-attention q/k/v/o projections, linear-attention in_proj_qkv/in_proj_z/in_proj_b/in_proj_a/out_proj, and shared-MLP gate/up/down. Router, routed-expert weights, visual encoder and aligner are frozen. Exact target regex:

```text
model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))
```

## Training and checkpoint choice

Checkpoint 249 is both the final checkpoint and native minimum-validation-loss checkpoint of the 249-step run. The saved artifact is the selected output; no formal benchmark feedback was used to pick a later answer.

Native run: 4 H100 GPUs, gradient accumulation 2, global batch 8; 249 completed optimizer steps. Exported train 2000; native loaded train 1993; native loaded SFT validation 87.

All experts used one SFT epoch, global batch 8, per-device batch 1, AdamW (`adamw_torch`), learning rate 1e-4, cosine decay, warmup 0.03, weight decay 0.1, gradient checkpointing, DeepSpeed ZeRO-3, SDPA and Liger. Seeds were 20261016 for training and data. Packing and padding-free mode were disabled; length grouping was enabled. Full sequences exceeding 65,536 tokens were deleted rather than silently truncated. Data preparation also checked an 8,192-token assistant-output ceiling. Native eval/save occurred every 16 steps and at the final step. Exported-row counts and native loaded-row counts are reported separately; neither is a per-batch exposure trace.

The native recipe set `enable_thinking=false`, `preserve_thinking=false`, `add_non_thinking_prefix=true`, and `loss_scale=default+ignore_empty_think`. Hidden reasoning fields and closed leading `<think>` blocks were removed during preparation; legitimate visible explanations, tool observations, and Terminal analysis/plan fields were retained. Original teacher collection modes remain recorded separately: converting supervision to nonthinking does not mean every teacher was collected in nonthinking mode.

## Data and cleaning evidence

The exported2,000 rows came from [nvidia/Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md), revision`1db674173119d71df45c22007af99e214600711a`, Qwen3.8-Flash-Next teacher (publisher metadata: thinking enabled, xhigh). Selection used publisher `resolved=1` bug-fix trajectories, structural checks, source-family grouping and formal repository exclusions. Full bash actions and observations were preserved; observation/submit wrappers were aligned to the locked mini contract without inventing missing environment states.

Native Swift rejected 7 exported rows because a source tool→user format-feedback pattern violated its role pairing. Actual training loaded1,993 rows: SWE-rebench-v2=1,224 and Scale-SWE=769; languages Python952, Go517, JavaScript477, TypeScript47. The 87-row SFT validation partition remained held out. The retained complete-sequence token estimate is 67,446,810 under the frozen original source template, not a native label-token or compute counter. Publisher success is not a local replay receipt; source collection revisions and fork/rename lineage are not completely established.

## Evaluation scope and limitations

This card records the frozen SFT adapter. Evaluation is target-scoped and resource-constrained; the complete result matrix is in the candidate repository. On SWE-bench Pro v2-hard, this adapter scored **0/51 = 0%** under the disclosed 30-minute, nonthinking protocol. HLE, ASI-Bench and Terminal scores are not claimed for this expert. The project completed one BF16 LoRA SFT epoch only; no full-parameter training, DPO, RL or second-stage optimization was run because the available GPU/CPU window and judge budget were limited. Null and invalid items remain disclosed rather than treated as official complete scores.

The project comparison uses BF16, nonthinking, 65,536 total context /8,192 output per main or helper call. This is distinct from publisher leaderboards. Protocol deviations, resource limits, historical coverage and raw evidence are recorded in the candidate repository; these cards do not make a general performance or correctness guarantee.

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

The Open-SWE dataset card declares CC-BY-4.0. Exported source rows separately record Apache-2.0 (598), MIT (1,127), BSD-3-Clause (227), BSD-2-Clause (48); those counts describe2,000 exported rows, not1,993 native loaded rows. Preserve source/project notices and per-row attribution when distributing covered material.

Model repository: [csminion/apex-qwen36-swe](https://huggingface.co/csminion/apex-qwen36-swe).
