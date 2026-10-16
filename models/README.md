# Model delivery bundle

These are the published model cards and verified release manifest for four independently fine-tuned experts and the fixed primary AVG64 adapter. The original task attachment takes precedence over later changes to the online template README: deliver an independent GitHub repository based on the template and five public Hugging Face model repositories. This work does not introduce the later template's second-stage/private-assignment requirements. The GitHub repository may initially be private while delivery materials are reviewed; the five requested model repositories are public and ungated.

| Artifact | Card to copy as HF `README.md` | Selected source checkpoint | Rank / alpha | FP32 parameters | Published HF repository |
| --- | --- | --- | --- | ---: | --- |
| SWE | [SWE card](cards/apex-swe-r16.md) | `swe2k-sft-r16-726335/training/checkpoint-249` |16 /32|21,166,080|[csminion/apex-qwen36-swe](https://huggingface.co/csminion/apex-qwen36-swe)|
| Terminal | [Terminal card](cards/apex-terminal-r16.md) | `terminal-retry-sft-r16-726665/training/checkpoint-250` |16 /32|21,166,080|[csminion/apex-qwen36-terminal](https://huggingface.co/csminion/apex-qwen36-terminal)|
| Academic/HLE | [Academic card](cards/apex-hle-r16.md) | `hle-existing2k-sft-r16-726664/training/checkpoint-250` |16 /32|21,166,080|[csminion/apex-qwen36-hle](https://huggingface.co/csminion/apex-qwen36-hle)|
| Scientific Python/ASI | [ASI card](cards/apex-asi-r16.md) | `asi-expanded-sft-r16-726336/training/checkpoint-128` |16 /32|21,166,080|[csminion/apex-qwen36-asi](https://huggingface.co/csminion/apex-qwen36-asi)|
| Four-expert AVG64 | [AVG64 card](cards/apex-avg-r64.md) | `four-experts-avg-v1-20261017/avg-r64` |64 /64|84,664,320|[csminion/apex-qwen36-avg64](https://huggingface.co/csminion/apex-qwen36-avg64)|

Expert source paths above are relative to the retained `artifacts/runs/` tree; the merge path is relative to `artifacts/merges/`. They identify source builds, not public download locations. The five public model repositories below were read back anonymously at their immutable commits. [release_manifest.json](release_manifest.json) is the machine-readable publication inventory. AVG-SVD-r16 and Mixed-r16 are controls/ablations, not replacements for any of the five requested artifacts.

## Reproduction facts

The public base is [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), revision `995ad96eacd98c81ed38be0c5b274b04031597b0` for model, tokenizer and multimodal processor. Each artifact requires these base weights; adapters do not contain the full model. Keep the conditional-generation/vision architecture and processor, including for HLE images.

All expert adapters have 620 FP32 A/B tensors over 310 language attention, linear-attention and shared-MLP projections. Routed experts, router, vision encoder and aligner are frozen. Each rank16 adapter file is 84,760,832 bytes. AVG64 is 338,754,768 bytes and represents the exact factor concatenation of equal-weight deltas, before serving dtype casts. It has four times the adapter capacity of rank16; this is an explicit comparison limitation.

SFT used one epoch, batch 8, LR1e-4/cosine/warmup0.03, AdamW/weight_decay0.1, BF16, ZeRO-3, SDPA/Liger, gradient checkpointing and seed20261016. SWE/Terminal used4 GPUs with accumulation 2; ASI/HLE used2 GPUs with accumulation 4. Context limit65,536, no packing, delete overlength sequences, nonthinking template and `default+ignore_empty_think`. Native loaded train/validation counts are SWE 1993/87, Terminal 2000/42, HLE 2000/100, ASI 1073/20. SWE's7 native role-pairing rejections are disclosed. Per-card details distinguish reference snippets, complete trajectories, source quality claims and incomplete lineage evidence.

Use the self-contained PEFT example in each card. Installed-source compatibility was checked against Transformers5.15.1/PEFT0.20.0: `AutoModelForImageTextToText` maps this base to `Qwen3_5MoeForConditionalGeneration`; `PeftModel.from_pretrained` accepts the explicit base and adapter directory. This was source verification, not another large-model execution. The tested training stack is recorded in `scripts/requirements-sft-runtime.lock`; no claim is made that a minimal fresh CPU environment can load or run the full base. Per-rank trainer memory reporting is not an all-GPU peak measurement.

Relevant reconstruction entry points are `scripts/run_sft.py`, `configs/train/lora_r16_shared_v1.json`, `scripts/merge_expert_adapters.py` and `configs/merge/four_experts_avg_v1.json`. The historical recipe's HLE native best16 differs from the frozen delivered250; the cards and release manifest record the actual choice. Do not infer delivered checkpoints from a stale planning summary.

## Dataset attribution inventory

| Source | Frozen revision | Included training rows | Recorded source license |
| --- | --- | ---: | --- |
| [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces) |`1db674173119d71df45c22007af99e214600711a`|2000 exported,1993 loaded|CC-BY4.0 dataset; underlying Apache/MIT/BSD notices|
| [TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K) |`45f1e98e317d3639437f0eb02f4e8bc5825732f3`|1107|Apache2.0 publisher card|
| [Terminal-Pivot](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1) |`eaef26944643644c8a3dbbf361ce6128142f5976`|893|CC-BY4.0, NVIDIA Corporation|
| [Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4) |`84d42ad0cb960f07f951b9baa9ed2b46a5a18c66`|817|CC-BY4.0|
| [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) |`b189ec765aa7ed75c8acfea42df31fdae71f97be`|884|MIT dataset card|
| [Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2) |`6536a5021222a94126968e8c92f29ee47fc8a7df`|201|CC-BY-SA4.0|
| [V4-Pro-Reasoning-8000x](https://huggingface.co/datasets/trjxter/DeepSeek-V4-Pro-Reasoning-8000x) |`7329257a28babc5998be072a3d8add1dd8ad0fda`|82|Apache2.0 publisher card; question lineage incomplete|
| [GLM-5.1-Reasoning-1M-Cleaned](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned) |`f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d`|16|Apache2.0 publisher card; question lineage incomplete|
| [ScienceAgentBench verified](https://huggingface.co/datasets/osunlp/ScienceAgentBench) |`9c6e96c9e74572e979b0930ee735041cef528cb7`|82|76 CC-BY4.0; 6 original upstream licenses (matminer1, rasterio5)|
| [DS-1000](https://github.com/xlang-ai/DS-1000) |`b39aab71da6d23ef8d3cac59a7c5f834516ab334`|976|CC-BY-SA4.0|
| [SciCode](https://huggingface.co/datasets/SciCode1/SciCode) |`4510f6a6aa27c43fad7b43da2c59602a86e88480`|15|Apache2.0|

Labels above report retained provenance, not a blanket legal conclusion about all underlying questions/code or derivative model weights. In particular, share-alike and original-license rows need their own notices; a teacher/model license does not replace dataset/source obligations. The five cards use `license: other`, `license_name: apache-2.0-adapter-contributions-plus-upstream-notices`, and `license_link: LICENSE`. [LICENSE](LICENSE) grants Apache-2.0 only for original adapter contributions the publisher can license; the [standard text](licenses/APACHE-2.0.txt) is included. Each artifact has a prepared [NOTICE.md source](notices/) listing its actual datasets and unchanged upstream terms. This is a scoped contribution grant with source notices, not a new restrictive license or a claim that all training inputs are Apache-2.0. Raw training/evaluation corpora are outside this model bundle. Preserve source attribution and corpus canaries in retained records; do not reupload the original benchmark bundles.

## Reproducible publication procedure

1. Confirm the five intended HF IDs and create only the authorized public model repositories. The attached license/notice proposal is concrete; no unspecified universal source clearance is being claimed. Preserve original template attribution in the independent GitHub repository; do not overwrite the original task with later template requirements.
2. Stage a release copy per adapter containing its card as `README.md`, `adapter_model.safetensors`, `adapter_config.json`, and `models/LICENSE` as `LICENSE`, the artifact-specific prepared notice as `NOTICE.md`, plus `models/licenses/APACHE-2.0.txt` at `licenses/APACHE-2.0.txt`. Keep source artifacts and active services unchanged.
3. In the release copy only, replace `base_model_name_or_path` with `Qwen/Qwen3.6-35B-A3B` and explicitly set `revision` to the frozen base commit. The four native expert configs have `revision: null` because training used the frozen local directory; the AVG64 export already records the frozen commit. Preserve rank, alpha, target regex, weights and all other behavior-affecting settings. Review merge manifests before including any; omit machine paths.
4. Exclude credentials, raw/private logs, optimizer/scheduler states, `training_args.bin`, training/evaluation question-answer bundles, hidden references and base weight shards. Git's ignored `artifacts/` tree is not an upload allowlist.
5. Validate that staged configs and safetensors match the manifest, and parse all card YAML. Read back public file metadata and record each actual repository URL and immutable HF commit. The verified publication receipt records the actual IDs and commits.
6. Add formal benchmark results only from complete, valid fixed-denominator reports with protocol and replacement judges disclosed. No placeholder score table or publisher-score substitution is included here.

Credential identity and publication readiness are recorded separately in `analysis/model_delivery_readiness_20261017.md`; this document contains no credential material. The authorized publishing step created and verified the five public model repositories below.

The source checkout has no root LICENSE/NOTICE or origin to establish a project-wide inherited grant. The adapter contribution grant above therefore stands on its own and does not silently relicense template/repository code. The original template attribution must be preserved in the independent GitHub delivery.

## Staging and verification commands

```bash
# Offline staging only; this is the default and does not read a token or create repositories.
python3 scripts/publish_hf_adapters.py

# Explicit publication mode; use only for the authorized five-model delivery.
python3 scripts/publish_hf_adapters.py --mode publish
```

The script retains its publication receipt in ignored release artifacts so reruns recognize this delivery's repositories. An existing name without that receipt is treated as a collision and is never overwritten. The only uploaded files are the six manifest entries; `.gitattributes`, when present, is platform metadata. Each artifact is checked by anonymous, revision-pinned full downloads, file sizes, streaming comparison to staged files, a second weight comparison to the frozen source, and a safetensors-header comparison. No independent large-file hash scan or GPU generation is added. Public evidence is stored in `analysis/source_snapshots/hf_publication_20261017.json`.

## Verified public revisions

| Model | Immutable HF revision |
| --- | --- |
| [csminion/apex-qwen36-swe](https://huggingface.co/csminion/apex-qwen36-swe) | `cf6f5bd1a9f6ee13a9e760640dd509b7b2d80c65` |
| [csminion/apex-qwen36-terminal](https://huggingface.co/csminion/apex-qwen36-terminal) | `79110026fe20fc7c64a8afc8abcedd94a676c37e` |
| [csminion/apex-qwen36-hle](https://huggingface.co/csminion/apex-qwen36-hle) | `026d926ae6ff639b7cdd540863b6c527467f1a36` |
| [csminion/apex-qwen36-asi](https://huggingface.co/csminion/apex-qwen36-asi) | `abe468e5531abe8a51fd3b3a110f29159464d31c` |
| [csminion/apex-qwen36-avg64](https://huggingface.co/csminion/apex-qwen36-avg64) | `53fbd83b8c6d56d9b24dfccbe58789063f7ca853` |

Each of the six release files was downloaded in full with `token=False` at the recorded revision. Sizes and streaming byte comparisons matched; safetensors headers and source weight bytes matched. Repositories are public and ungated. No additional manual large-file hash pass or model generation was run; normal Hub transfer integrity checks remain part of the SDK.
