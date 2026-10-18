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
- terminal
---

# APEX Terminal r16

A terminal-agent LoRA adapter trained on public Terminus-style histories, including commands, observations, visible planning and completion actions.


## Artifact and base

This repository contains a PEFT LoRA adapter; full base weights are not included. Base: [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), frozen model/tokenizer/processor revision`995ad96eacd98c81ed38be0c5b274b04031597b0`. Selected checkpoint: 250. The saved adapter contains 620 FP32 tensors across 310 modules, 21,166,080 parameters (84,760,832-byte safetensors file).

LoRA configuration:`r=16`, `lora_alpha=32`, scaling`alpha/r=2`, dropout 0.05, bias`none`, ordinary LoRA (no DoRA/RS-LoRA), task type`CAUSAL_LM`, no `modules_to_save`. Targets are language self-attention q/k/v/o projections, linear-attention in_proj_qkv/in_proj_z/in_proj_b/in_proj_a/out_proj, and shared-MLP gate/up/down. Router, routed-expert weights, visual encoder and aligner are frozen. Exact target regex:

```text
model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))
```

## Training and checkpoint choice

Checkpoint 250 is both the final checkpoint and native minimum-validation-loss checkpoint of the 250-step completed retry run. An earlier training attempt failed during evaluation; it is not the delivered model. Selection uses the completed run, not a resumed task-level benchmark.

Native run: 4 H100 GPUs, gradient accumulation 2, global batch 8; 250 completed optimizer steps. Exported train 2000; native loaded train 2000; native loaded SFT validation 42.

All experts used one SFT epoch, global batch 8, per-device batch 1, AdamW (`adamw_torch`), learning rate 1e-4, cosine decay, warmup 0.03, weight decay 0.1, gradient checkpointing, DeepSpeed ZeRO-3, SDPA and Liger. Seeds were 20261016 for training and data. Packing and padding-free mode were disabled; length grouping was enabled. Full sequences exceeding 65,536 tokens were deleted rather than silently truncated. Data preparation also checked an 8,192-token assistant-output ceiling. Native eval/save occurred every 16 steps and at the final step. Exported-row counts and native loaded-row counts are reported separately; neither is a per-batch exposure trace.

The native recipe set `enable_thinking=false`, `preserve_thinking=false`, `add_non_thinking_prefix=true`, and `loss_scale=default+ignore_empty_think`. Hidden reasoning fields and closed leading `<think>` blocks were removed during preparation; legitimate visible explanations, tool observations, and Terminal analysis/plan fields were retained. Original teacher collection modes remain recorded separately: converting supervision to nonthinking does not mean every teacher was collected in nonthinking mode.

## Data and cleaning evidence

The 2,000 training episodes combine1,107 from [TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K/blob/45f1e98e317d3639437f0eb02f4e8bc5825732f3/README.md) (`45f1e98e317d3639437f0eb02f4e8bc5825732f3`, publisher-declared DeepSeek-V4-Pro-0813) and 893 from [Nemotron-RL-Agentic-Terminal-Pivot-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1/blob/eaef26944643644c8a3dbbf361ce6128142f5976/README.md) (`eaef26944643644c8a3dbbf361ce6128142f5976`). Pivot teachers are 332 `zai-org/GLM-5.1` and 561 `zai-org/GLM-5.1-FP8` episodes. These are 1,303 source task/family keys, not2,000 independent environments. Native training loaded all2,000; SFT validation contains 42 episodes.

Preparation retained complete released histories through a published `task_complete=true` action, removed hidden reasoning and checked the native JSON parser and 64K/8K limits. Publisher-withheld post-completion confirmations were not fabricated; selected unreleased tail counts are 797 with 1 turn,94 with 0,2 with 3. Public formal/task-val inputs were protected by the recorded overlap checks. The corpus was not locally replayed end-to-end; Pivot category balance remains unclassified. Source-template complete-sequence count71,660,040 is not the native supervised-token count.

## Evaluation scope and limitations

This card records the frozen SFT adapter. Evaluation is target-scoped and resource-constrained; the complete result matrix is in the candidate repository. On Terminal-Bench, the fixed seed=2 single-run exploratory result is **8/89 = 8.988764%** under 30 minutes, 4 CPU, 8 GiB, 64K context and 8K output. It is not the official five-seed mean. HLE, ASI-Bench and SWE scores are not claimed for this expert. The project completed one BF16 LoRA SFT epoch only; no full-parameter training, DPO, RL or second-stage optimization was run because the available GPU/CPU window and judge budget were limited. The extra no-network sandbox policy and all invalid/null items remain disclosed.

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

TerminalHorizon-3K declares Apache-2.0. NVIDIA Terminal-Pivot declares CC-BY-4.0 with NVIDIA Corporation attribution. Retain the separate dataset notices, original task/code notices and teacher provenance; publisher verifier-pass claims do not establish permission or a local execution guarantee.

Model repository: [csminion/apex-qwen36-terminal](https://huggingface.co/csminion/apex-qwen36-terminal).
