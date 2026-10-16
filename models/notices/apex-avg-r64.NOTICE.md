# Base model and distribution scope

Base: Qwen/Qwen3.6-35B-A3B, revision `995ad96eacd98c81ed38be0c5b274b04031597b0`, by the Qwen team. The [base card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) declares Apache-2.0. The standard text accompanies this release as `licenses/APACHE-2.0.txt`.

The adapter is a modification produced by SFT or the documented parameter-delta merge. Original adapter contributions are offered under the accompanying LICENSE. This release does not include the full base weights or raw source training/evaluation corpora. Dataset/source licenses below are preserved provenance, not a claim that the publisher owns or relicenses all source material. No upstream publisher or teacher endorses this adapter.

# Four-expert merge

Equal-weight parameter-delta merge of SWE 249, Terminal 250, ASI 128, HLE 250. No raw training corpora or base weights are redistributed. The merge does not erase or average away any source notice. All four input source disclosures follow.

## SWE training sources

- NVIDIA, [Open-SWE-Traces](https://huggingface.co/datasets/nvidia/Open-SWE-Traces/blob/1db674173119d71df45c22007af99e214600711a/README.md), revision `1db674173119d71df45c22007af99e214600711a`; dataset card: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Qwen3.8-Flash-Next is the recorded teacher, not the license owner of every repository excerpt.
- Original repository code represented in the 2,000 exported records retains its recorded source license: Apache-2.0=598, MIT=1,127, BSD-3-Clause=227, BSD-2-Clause=48. These are export counts; 7 role-pairing exclusions leave1,993 native loaded rows. Raw code/trajectories and their copyright blocks are not redistributed in this model repository. Source-level provenance remains in the retained manifests.
- Preparation removed hidden reasoning, aligned observation/submit wrappers and selected source-family/length-qualified records. It did not establish exact fork/rename lineage or independently audit every upstream file's copyright. The dataset-card CC grant does not replace those original code licenses.

## Terminal training sources

- shunzou05, [TerminalHorizon-3K](https://huggingface.co/datasets/shunzou05/TerminalHorizon-3K/blob/45f1e98e317d3639437f0eb02f4e8bc5825732f3/README.md), revision `45f1e98e317d3639437f0eb02f4e8bc5825732f3`; publisher card: Apache-2.0; 1,107 training histories. Teacher identity is publisher-declared DeepSeek-V4-Pro-0813.
- NVIDIA Corporation, [Nemotron-RL-Agentic-Terminal-Pivot-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Terminal-Pivot-v1/blob/eaef26944643644c8a3dbbf361ce6128142f5976/README.md), revision `eaef26944643644c8a3dbbf361ce6128142f5976`; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); 893 training histories. Recorded teachers: GLM-5.1 and GLM-5.1-FP8.
- Original task/code dependencies retain their source terms. A complete per-task upstream copyright chain was not reconstructed. The release distributes no raw task packs, terminal histories, omitted confirmation tails or dependency files. Preparation removed hidden reasoning while retaining visible planning and released histories through completion; it did not fabricate withheld tail observations.

## Academic training sources

- NVIDIA, [Nemotron-SFT-Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4/blob/84d42ad0cb960f07f951b9baa9ed2b46a5a18c66/README.md), revision `84d42ad0cb960f07f951b9baa9ed2b46a5a18c66`; 817 selected rows; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- TIGER-Lab, [MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/blob/b189ec765aa7ed75c8acfea42df31fdae71f97be/README.md), revision `b189ec765aa7ed75c8acfea42df31fdae71f97be`; 884 selected rows; MIT dataset-card declaration. Supervision combines722 previously accepted DeepSeek-V4-Pro High responses and162 original reference short answers.
- NVIDIA, [Nemotron-SFT-Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/6536a5021222a94126968e8c92f29ee47fc8a7df/README.md), revision `6536a5021222a94126968e8c92f29ee47fc8a7df`; 201 selected rows; [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- trjxter, [DeepSeek-V4-Pro-Reasoning-8000x](https://huggingface.co/datasets/trjxter/DeepSeek-V4-Pro-Reasoning-8000x/blob/7329257a28babc5998be072a3d8add1dd8ad0fda/README.md), revision `7329257a28babc5998be072a3d8add1dd8ad0fda`; 82 selected rows; Apache-2.0 publisher-card declaration.
- Jackrong, [GLM-5.1-Reasoning-1M-Cleaned](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned/blob/f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d/README.md), revision `f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d`; 16 selected rows; Apache-2.0 publisher-card declaration.
- Changes: hidden reasoning removal, final-answer extraction, project grouping/length checks and academic quota selection. No source text is included in this adapter repository. Forum/question attribution and original question lineage are incomplete for parts of Math/Science and the personal-publisher pools. Publisher dataset licenses do not establish that every underlying question is free of separate rights. Share-alike terms remain applicable to covered material; this notice makes no categorical determination that trained weights are, or are not, Adapted Material under those terms.

## Scientific Python training sources

- OSU NLP Group and contributors, [ScienceAgentBench verified](https://huggingface.co/datasets/osunlp/ScienceAgentBench/tree/9c6e96c9e74572e979b0930ee735041cef528cb7), revision `9c6e96c9e74572e979b0930ee735041cef528cb7`; 82 training references. The retained per-row record assigns76 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and6 original-upstream licenses:1 [matminer](https://github.com/hackingmaterials/matminer/blob/main/LICENSE),5 [rasterio](https://github.com/rasterio/rasterio/blob/main/LICENSE.txt). The selected reference-code canaries and original notices are retained in the private source corpus, not stripped or relabeled CC-BY.
- xlang-ai and contributors, [DS-1000](https://github.com/xlang-ai/DS-1000/blob/b39aab71da6d23ef8d3cac59a7c5f834516ab334/data/ds1000.jsonl.gz), revision `b39aab71da6d23ef8d3cac59a7c5f834516ab334`; 976 selected references; [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- SciCode authors, [SciCode](https://huggingface.co/datasets/SciCode1/SciCode/blob/4510f6a6aa27c43fad7b43da2c59602a86e88480/problems_dev.jsonl), revision `4510f6a6aa27c43fad7b43da2c59602a86e88480`; 15 main validation references repurposed for training; Apache-2.0.
- Original reference code and indentation were preserved; 24 DS variants in 6 input-overlap families were excluded. Raw reference programs, benchmark files, tests, data and canaries are not redistributed in this adapter repository. SAB's six source-repository licenses were retained by URL; the exact original upstream commit/license text was not pinned in that source metadata. Current linked license texts are supplementary provenance, not proof of the exact historical source version.
- CC share-alike applies to covered material according to its terms; this notice does not presume that every trained parameter is, or is not, Adapted Material. It does not relabel human-reference source code Apache-2.0.
