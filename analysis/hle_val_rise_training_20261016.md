# HLE validation-loss rise: training-side evidence

Run: `artifacts/runs/hle-existing2k-sft-r16-726664` on HPC. This is an analysis
of existing records; no model/API calls, re-encoding, retraining or configuration
changes were made. Loss below is supervised cross entropy, not HLE accuracy.

## What the completed run shows

The observed pattern is falling training loss and rising loss on the fixed
validation targets. It is consistent with a training/validation objective or
distribution mismatch, and possibly overfitting. It is not evidence of a
numerical/software failure by itself, nor proof that generated answers became
less correct.

| Optimizer steps | Mean logged training-batch loss |
|---|---:|
| 1–16 | 0.694638 |
| 17–64 | 0.525876 |
| 65–128 | 0.498130 |
| 129–192 | 0.484749 |
| 193–250 | 0.478752 |

These are descriptive means of different batches, not a fixed training-set
evaluation. Validation loss is 2.002192 at step16, 2.836297 at32, 3.181840 at48,
peaks at3.537828 at112, then fluctuates around3.44–3.51; final250 is3.497519.
The first measured checkpoint16 is best. There was no step0/Base evaluation on
the same validation set, so the gain/loss relative to Base is unknown.

`training/args.json` records AdamW, learning rate1e-4, cosine decay,
`warmup_ratio=0.03`, one epoch, LoRA r16/alpha32, weight decay0.1,
gradient clipping1.0, two GPUs × microbatch1 × accumulation4 = global batch8.
The native logs show eight warmup steps: LR1.25e-5 at step1 and1e-4 at8;
it then falls to approximately0 by249–250. Mean logged gradient norms across
the five windows above are0.666/0.498/0.523/0.479/0.501. There is no observed
NaN or sustained exploding-gradient signature in these records.

## Fixed validation set and loss route

Native `training.log:556–562` shows train2000/val100, without preprocessing
deletions. The configured validation file is
`artifacts/data/candidates/hle_existing_2k_20261016/swift_ready/val.messages.jsonl`:
100 physical JSONL records,56315 bytes, current modification time19:10:48
Beijing, before the job started19:53:32. The run constructs its encoded
validation dataset once and reuses it; no reloading/change evidence was found.
This is evidence of a fixed set, not a newly computed content hash guarantee.

Both train and val use `enable_thinking=false`, `preserve_thinking=false`,
`loss_scale=default+ignore_empty_think`, no label smoothing/DFT/channel loss,
router auxiliary coefficient0. The same binary mask implementation supervises
assistant response/suffix tokens and sets prompt/ignored tokens to-100:

- HPC package `swift/loss_scale/base.py:114–130`: assistant-only default strategy.
- `swift/loss_scale/config/ignore_empty_think.json`: masks empty thinking prefixes.
- `swift/template/base.py:1214–1239`: binary weights become labels/-100;
  no separate nonbinary loss-scale tensor remains.
- `swift/trainers/seq2seq_trainer.py:126–158` and
  `swift/template/base.py:879–888`: shared model loss and token normalization.
- Project `scripts/sft_eval_loss.py:7–17`: labelled evaluation explicitly uses
  the same existing Liger fused CE route; training already selects it.

Training normalizes supervised tokens across the accumulation batch; validation
reports aggregated per-example loss with microbatch1. They are different samples
and aggregation contexts. Their absolute values are not directly comparable as
a generalization gap magnitude. No obvious changing train/val mask or CE-path
asymmetry was found that explains the curve.

## Sampling does not establish a short-sample bias

Swift overrides the generic HF training sampler:
`swift/trainers/mixin.py:1407–1448` passes `group_by_length=true` and encoded
lengths into `swift/dataloader/shard.py:45–67`. This sampler starts from a seeded
random permutation, groups by length and shards indices across ranks. It calls
`transformers/trainer_pt_utils.py:486–518`, which sorts descending within random
mega-batches and places the longest item first. For this run's microbatch1 and
world2 the grouping uses100-item mega-batches. This changes local order and
batch composition; it does not preferentially repeat short samples or leave
the input-source file in its original concatenation order. All2000 rows are
loaded for the one-epoch run. The exact realized source/length mix per step was
not logged, so a length-correlated source-order effect remains unmeasured.
Validation explicitly disables length grouping in
`swift/trainers/mixin.py:1485–1494` and retains the same100 items.

## Three falsifiable hypotheses

1. **Answer-format/objective mismatch.** The training pool contains worked
   explanations, whereas the preserved val references are short expected
   answers/option letters. A model becoming more likely to begin an explanation
   can assign lower probability to a terse reference at the same position even
   when its eventual extracted answer is correct. This is plausible from the
   recorded data policy, but the curve alone cannot establish it. Prediction:
   Base/cp16/cp250 generation on this same val will show longer explanation
   prefixes, while extracted-answer accuracy may remain stable despite rising
   short-reference CE. It is weakened if formatting-aligned scoring also
   worsens similarly, or generated formats do not differ. No such generation
   comparison has been run here.

2. **Excessive adaptation or proxy-domain overfitting.** Loss falls on training
   batches while fixed-val loss worsens early, during the high-LR portion.
   A1e-4 peak LR is a candidate contributor, not demonstrated to be too high.
   Prediction: deterioration should remain in per-item, format-aligned
   validation, and a lower-update-magnitude control or earlier checkpoint should
   preserve more of that performance. It is weakened if only reference-format
   CE changes and answer accuracy does not. No LR ablation, step0 CE, or paired
   generation assessment exists, so do not diagnose catastrophic forgetting or
   choose a new LR solely from this curve.

3. **Length-correlated source/batch order modulates the curve.** Length grouping
   can cluster sources when their response lengths differ; supervision token
   counts also differ by example. Prediction: logged/reconstructed batch-source
   composition would correlate with local loss excursions and per-domain val
   changes; a shuffle-only control would alter those transient excursions.
   Exact batch IDs/source histograms were not retained, and the persistent val
   rise across many random mega-batches is stronger evidence than a single
   unlucky batch. This is a weaker modifier hypothesis, not an established
   short-sample oversampling mechanism or the primary explanation.

For reporting, retain cp16 as the observed minimum-loss checkpoint and cp250 as
the completed final checkpoint. Their relative task quality remains unmeasured.
