# Terminal SFT validation loss memory fix

## Observed failure

Job 726345 completed optimizer steps 1–16 of 250 on four H100s. Its first
validation pass failed at `torch.nn.functional.cross_entropy`: a 21.06 GiB
allocation was requested with 19.39 GiB free. No checkpoint was saved because
evaluation precedes saving at that interval. Training itself had reached a
reported 55.05 GiB peak.

## Executable feedback loop

Run with the existing HPC SFT environment, without GPUs or loading base weights:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  artifacts/envs/sft/bin/python scripts/check_sft_eval_loss.py --unpatched
```

Observed red result (exit 1):

```text
AssertionError: labelled eval materialized full-vocabulary logits instead of using FLCE
```

This invokes the installed Liger conditional-generation forward on tiny CPU
tensors. Its real label shift and normalization execute; only the final Triton
kernel is replaced by an actual CPU chunked cross-entropy implementation. This
reproduces the allocation-routing defect, **not the physical GPU OOM**. The
formal resumed/restarted job must provide the GPU feedback.

## Cause

Liger 0.8.2 `transformers/model/qwen3_5_moe.py` defaults to:

```python
skip_logits = self.training and (labels is not None or shift_labels is not None)
```

Training therefore uses fused linear cross entropy. Validation sets
`self.training=False`, so the same forward instead materializes full-vocabulary
logits, then calls ordinary CE. `prediction_loss_only=True` controls Trainer's
returned predictions; Swift's actual `Template.compute_sft_loss` does not pass
`skip_logits=True` into this model. This explains why a successful training
batch did not establish validation memory safety.

The previously ranked alternatives were padding-dependent growth and retained
training allocations. Those may affect free memory, but neither is needed to
explain the observed full-logits branch; the minimal CPU case has neither.

## Minimal fix

`scripts/sft_eval_loss.py` wraps Liger's conditional-generation forward only in
the independent SFT worker process. Labelled evaluation with no explicit
`skip_logits` value now sets `skip_logits=True`, reusing the official FLCE loss.
Training, explicit `skip_logits=False`, and label-free generation retain their
existing behavior. The wrapper preserves the forward signature. Liger's native
apply function imports that wrapped forward when configuring the model.

`scripts/swift_sft_from_config.py` installs the wrapper before native Swift
argument/model initialization when the existing Liger configuration is enabled.

No installed package, running SWE process, base benchmark, dataset, sequence
limit, validation subset, or batch setting is changed. Root owns job submission
and final GPU validation.

## Validation scope

The same CPU script without `--unpatched` checks labelled-eval routing against
ordinary CE, causal shift, ignored prompt/padding targets, item normalization,
native Liger model patch installation, and preservation of generation and
training behavior, under `torch.no_grad()` as in validation. This was run after
the fix and exited 0:

```text
PASS: labelled eval skips logits; causal CE, -100 masks, normalization agree; generation unchanged
```

The masked-position check changes hidden states at ignored next-token targets
and confirms loss is unchanged. Dense and chunked CPU losses agree within
`rtol=1e-6, atol=1e-6`, including explicit item-count normalization. Native
`apply_liger_kernel_to_qwen3_5_moe` installs the wrapped class forward. The final
CPU run also checks training still uses the same fused path. Local Python
compilation passed for all three scripts.

GPU feedback remains pending root's formal job. No claim of physical GPU OOM
resolution or benchmark improvement follows from the CPU check alone.

The missing preflight was a labelled validation pass through the actual model
loss route; a successful backward pass did not test it. The small regression
locks down that routing distinction without adding an architecture layer.
