# Base model and distribution scope

Base: Qwen/Qwen3.6-35B-A3B, revision `995ad96eacd98c81ed38be0c5b274b04031597b0`, by the Qwen team. The [base card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) declares Apache-2.0. The standard text accompanies this release as `licenses/APACHE-2.0.txt`.

The adapter is a modification produced by SFT or the documented parameter-delta merge. Original adapter contributions are offered under the accompanying LICENSE. This release does not include the full base weights or raw source training/evaluation corpora. Dataset/source licenses below are preserved provenance, not a claim that the publisher owns or relicenses all source material. No upstream publisher or teacher endorses this adapter.

## SWE training sources

- NVIDIA, [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md), revision `1db674173119d71df45c22007af99e214600711a`; dataset card: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Qwen3.8-Flash-Next is the recorded teacher, not the license owner of every repository excerpt.
- Original repository code represented in the 2,000 exported records retains its recorded source license: Apache-2.0=598, MIT=1,127, BSD-3-Clause=227, BSD-2-Clause=48. These are export counts; 7 role-pairing exclusions leave1,993 native loaded rows. Raw code/trajectories and their copyright blocks are not redistributed in this model repository. Source-level provenance remains in the retained manifests.
- Preparation removed hidden reasoning, aligned observation/submit wrappers and selected source-family/length-qualified records. It did not establish exact fork/rename lineage or independently audit every upstream file's copyright. The dataset-card CC grant does not replace those original code licenses.
