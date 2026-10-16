# Base model and distribution scope

Base: Qwen/Qwen3.6-35B-A3B, revision `995ad96eacd98c81ed38be0c5b274b04031597b0`, by the Qwen team. The [base card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) declares Apache-2.0. The standard text accompanies this release as `licenses/APACHE-2.0.txt`.

The adapter is a modification produced by SFT or the documented parameter-delta merge. Original adapter contributions are offered under the accompanying LICENSE. This release does not include the full base weights or raw source training/evaluation corpora. Dataset/source licenses below are preserved provenance, not a claim that the publisher owns or relicenses all source material. No upstream publisher or teacher endorses this adapter.

## Terminal training sources

- shunzou05, [TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K/blob/45f1e98e317d3639437f0eb02f4e8bc5825732f3/README.md), revision `45f1e98e317d3639437f0eb02f4e8bc5825732f3`; publisher card: Apache-2.0; 1,107 training histories. Teacher identity is publisher-declared DeepSeek-V4-Pro-0813.
- NVIDIA Corporation, [Nemotron-RL-Agentic-Terminal-Pivot-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1/blob/eaef26944643644c8a3dbbf361ce6128142f5976/README.md), revision `eaef26944643644c8a3dbbf361ce6128142f5976`; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); 893 training histories. Recorded teachers: GLM-5.1 and GLM-5.1-FP8.
- Original task/code dependencies retain their source terms. A complete per-task upstream copyright chain was not reconstructed. The release distributes no raw task packs, terminal histories, omitted confirmation tails or dependency files. Preparation removed hidden reasoning while retaining visible planning and released histories through completion; it did not fabricate withheld tail observations.
