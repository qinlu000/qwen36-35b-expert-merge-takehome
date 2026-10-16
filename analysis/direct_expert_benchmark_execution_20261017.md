# Direct expert and AVG64 formal benchmark execution

The independent task validation is cancelled. These pipelines run the complete formal HLE2500 (including all342 image questions) and ASI240 (60 tasks × B1–B4, official instance seed31415). No Base answers are regenerated.

## Fixed checkpoints and service allocations

- HLE pure expert: `hle-existing2k-sft-r16-726664/training/checkpoint-250`, alias `apex-hle250`. Selection is frozen from already completed independent dev: Base54/100; checkpoint16 has43 correct and2 invalid (upper bound45/100); checkpoint250 has48/100. No additional task validation or formal result selects the checkpoint.
- ASI pure expert: `asi-expanded-sft-r16-726336/training/checkpoint-128`, alias `apex-asi128`. This historical selection used native SFT validation loss, not execution-based task validation; it does not establish the best ASI task score. Training finished at134; checkpoint128 loss0.5826834440 versus final134 loss0.5828790069. Existing serving, public release and AVG64 inputs remain128.
- Primary merged model: `artifacts/merges/four-experts-avg-v1-20261017/avg-r64`, alias `apex-avg64`; rank64/alpha64 exact FP32 concatenation merge.
- Pure experts: Slurm727643, ACD1-2,2H100, port18002, host80 bridge28090,24h, max LoRA rank16.
- Merged direct: Slurm727654, ACD1-36,2H100, port18001, host80 bridge28093,24h, max LoRA rank64.
- Dedicated HLE expert: Slurm727821, ACD1-1,2H100, port18004, host80 bridge28094,24h, max LoRA rank16, only `apex-hle250` registered.
- Dedicated AVG64 HLE: Slurm727822, ACD1-30,2H100, port18005, host80 bridge28095,24h, max LoRA rank64, only `apex-avg64` registered.

Both use the same multimodal Qwen revision995ad96eacd98c81ed38be0c5b274b04031597b0, vLLM0.20.2, BF16, TP2, eager, triton GDN/MoE, chunked prefill8192, GPU memory0.85, maximum50 active model sequences, native Qwen tool/reasoning parsers, and nonthinking template. Registered expert aliases are forwarded in the actual `/tokenize` and generation requests. All620 adapter tensors /310 language modules are checked; the base visual encoder remains active.

## Formal scheduling and preserved protocol

The initial coordinator serialized ASI before HLE. At03:39CST the main thread authorized two dedicated HLE TP2 services so both full HLE runs proceed independently of ASI generation or SFT loss work. `run_dedicated_hle_formal.py` owns one output-specific `formal_consumer.lock`, synthetic acceptance, the unchanged HLE generator and frozen rolling judge. The existing generator's model-block lock and scorer's controller/budget locks remain active. Each HLE block uses50 rolling admissions, matching the final Base HLE production profile in `deployment_hle_asi_seq50_v5.json`; each question has the same continuous300s budget. Existing terminal answers are not regenerated; interrupted started attempts require audit.

`run_direct_formal_pipeline.py` now manages the unchanged ASI generation/scoring and attaches to the external HLE controller; it never launches HLE on an ASI service. The merged ASI pipeline still waits for the expert ASI generation CPU release. Only old waiting coordinators2792243/2792244 received SIGTERM, after verifying they had no children. Replacement coordinators3237024/3237026 reuse the same acceptance receipts and resource gates; expert ASI PID2752099 and its process starttime were checked unchanged. No process group or admitted ASI worker was signalled.

ASI retains the actual Base eight-process condition schedule and continuous1200s generation+execution budget. Every generated program has4 immutable CPUs and8GiB/no-swap; the pool is CPU96–127, eight disjoint groups, instead of Base CPU0–31. This preserves native DirectLLM prompt building, one code extraction/execution and output collection. Program scheduling is not split into separately timed stages. Initial admission waits for the Terminal synthetic acceptance receipt and confirmed absence of native scopes on120–123.

The existing Base ASI timing records explain the pool decision:237 repaired conditions averaged659.72s total, of which646.14s was model generation; post-generation mean13.58s, median0.71s, p905.72s, sum0.894h, max715.50s. Eight post-generation cases exceeded60s and four exceeded300s. Eight workers avoid a potentially43h serial whole-condition schedule while keeping the per-condition resources unchanged.

Every evaluated model request uses65536 context /8192 output, temperature0.7/top_p0.8/top_k20/min_p0/presence_penalty0/repetition_penalty1, seed0, enable_thinking=false/preserve_thinking=false. Dataset, fixed manifest, official prompts, HLE images and exact visual/tokenizer guards are preserved. The new drivers derive from the frozen Base runners and inherit the latest bounded-admission infrastructure breaker. Existing terminal answers are retained; no automatic whole-trial regeneration occurs. Received responses are saved before execution/validation. Infrastructure failures remain invalid; genuine budget/context failures retain native classification.

Only minimal synthetic transport acceptance is used: one text request and one32px-image request per service, checking actual expert aliases, visual tokenization, usage equality and nonthinking responses. No HLE100 or SAB20 is launched.

## Persistent outputs, grading and CPU release

On host80 the persistent ASI expert pipeline is PID3237024 and merged pipeline PID3237026. Dedicated ASI tunnel supervisors are PID2704454 (expert) and2734828 (merged); the independent HLE tunnel supervisor is PID3236500. These have no laptop dependency. HLE controller/child PIDs and acceptance receipts are stored in each formal output's `controller/` directory.

Outputs:

- `artifacts/eval/asi128_asi240_20261017`
- `artifacts/eval/hle250_hle2500_20261017`
- `artifacts/eval/avg64_asi240_20261017`
- `artifacts/eval/avg64_hle2500_20261017`

Pipeline logs/state/commands live in `artifacts/eval/expert_direct_pipeline_20261017` and `artifacts/eval/merged_direct_pipeline_20261017`. `generation_cpu_finished.json` is written only after all240 terminal records, worker-pool shutdown and no owned ASI scopes. `all_cpu_consumers_finished.json` additionally waits for the ASI grader and its native program scopes. Terminal expansion waits for both model markers. ASI graders serialize on CPU92–95 via `direct_asi_grader_cpu92_95.lock`; Terminal initially uses0–91.

HLE scoring reuses the current rolling Base scorer, official criteria/JSON contract, school DeepSeek-V4-Flash through TLS28443 with original CA/SNI/Host verification. ASI scoring copies the existing frozen current Base scoring runtime and uses the existing external DeepSeek mapping, original references, parameter recovery, accepted ngspice and submission runtime, and native rubric/aggregation. No extra hash-tree walks. Per-model independent hard ledgers are HLE¥20/5000calls and ASI¥20/396calls. ASI retains native scorer limits and7200s outer safety bound. Unavailable or invalid evaluator results keep the primary metric null.

The controller launch is not a final score. Read native generation progress, each `scoring/summary.json` (HLE), and `scoring/local_score_seed31415.json` (ASI) for actual coverage/validity. The service/acceptance snapshots are appended after real health and generation succeed.

The parameterized existing Slurm wrapper accepts `scripts/serve_direct_experts.slurm <profile> <port>`; defaults preserve the original expert service. New profiles `hle-expert 18004` and `hle-merged 18005` select isolated aliases without restarting the old services. A `controls 18006` profile is implemented for the main thread, registering only `apex-mixed883` (r16/alpha32) and `apex-avg16` (r16/alpha16) with max_loras1/max_cpu_loras2; this agent does not submit or start that control job. The two new main services raise the existing10GPU allocation to14, leaving2 for the separately authorized actual task controls.

## Dedicated HLE admission receipt at03:47CST

Both new services passed exactly two synthetic requests (text and32px image), with actual solver aliases,22/87 exact tokenizer-versus-usage counts, nonthinking and expected42/red. Expert acceptance finished03:45:49CST; AVG64 acceptance03:46:53CST. Neither acceptance used a formal or task-validation question. Native service logs after acceptance contain zero ignored-adapter warning matches. The frozen language-only adapters leave the visual base active.

The expert formal controller3266640 launched generator3266684 and scorer3266685; its first frozen-manifest question was admitted03:46:02.891575CST. The AVG64 controller3269007 launched its independent generator/scorer and first admitted the same fixed-manifest question03:47:01.317767CST. The03:47:35CST snapshot has expert164 terminal/214 admitted/50 active and AVG64 4 terminal/54 admitted/50 active. Both model-block locks, both formal consumer claims and both scorer-controller locks were actually held. These are launch/coverage observations, not accuracy claims; both primary scores remain incomplete.

The two new SSH forwards initially received `administratively prohibited`: the existing restricted HPC key allowed only18000–18003. Only its existing `apex-baseline-forward-20261016` entry in `/data/user/qinlucao/.ssh/authorized_keys` was extended with exact `ACD1-1:18004`, `ACD1-30:18005` and, at the main thread's request, `ACD1-30:18006`. Existing restrict/port-forwarding options, forced release command and original permits remained unchanged, mode0600. Only this agent's two SSH forwarding children reconnected; the HLE supervisor and old ASI service were preserved. Actual accepted requests prove the new paths work; no key value is recorded.

ASI PID2752099 retained its original starttime through both parent handoffs and progressed to113/240 at this snapshot. Its eight workers, CPU96–127, original continuous deadline, later merged-ASI gate and serialized92–95 scoring lease remain unchanged. The current resource receipt lists seven running TP2 jobs,14GPU including root's controls727831: root released old SWE727113 at03:47:02 only after51 terminal and zero consumers, so there are2GPU of headroom under the16GPU cap. This agent starts no further job.

The [small first-admission receipt](source_snapshots/hle_dedicated_first_admission_20261017.json) contains actual service launch metadata, acceptance usage, first-admission timestamps, original-ASI process identity, six held consumer locks, parent-only handoff, precise forwarding authorization and the resource snapshot. No question text, answers, references or credential values are copied into that tracked receipt. Service/runtime files were syntax-checked; formal generation and grading use the existing frozen implementations. No summarize/final_results/README/claud file was changed by this handoff.

At02:12:31CST the expert service passed its two minimal synthetic checks: actual returned aliases `apex-asi128` and `apex-hle250`, prompt counts22(text) and87(image), exact token-guard/usage equality and no reasoning channel. No ignored-layer warning matches were found. Formal ASI generation PID2752099 admitted exactly8 initial conditions on the recorded96–127 CPU sets. Full run metadata lists the true served alias; no Base alias is sent by either driver. See `analysis/source_snapshots/direct_expert_acceptance_20261017.json`. Merged service startup/acceptance remains pending at this snapshot.

First production batch at02:15:03CST has2/240 terminal results,10 admitted total and8 active. Elapsed104.78s/144.56s, output839/1175 tokens. Both answers executed once and their native failed program results remain frozen. Actual limits receipts show8GiB,swap0, CPU104–107 and120–123, seccomp expansion blocked. Scientific scores remain pending. No new acceptance call was needed for this evidence.

Merged native service727654 became health200 and passed both minimal text and image requests at02:18:46CST. Both responses report actual model `apex-avg64`; counts22/87 exactly match generation usage, no reasoning content, and no ignored-layer warnings. Native rank64 service reports32.24GiB KV cache /3,177,503 tokens /48.48 simultaneous full65536 contexts with configured max_num_seqs50. The merged pipeline is now waiting for the expert generation CPU marker; its formal HLE and ASI sets are fully specified and no merged formal question has been admitted prematurely. See `analysis/source_snapshots/merged_direct_acceptance_20261017.json`.

At the earlier02:20CST handoff, the coordinator CPU-drain filter was corrected to cover native `ai4sci-submission-*` scopes as well as solver scopes. Parent expert2792243 attached to unchanged formal ASI generator2752099, while merged2792244 waited at the expert-generation gate. Those two parents were subsequently replaced at03:39CST as documented above. Existing ASI-service acceptance receipts are reused; no model call or benchmark attempt was repeated by either handoff. The all-CPU marker is withheld if any native scorer program remains on92–95.
