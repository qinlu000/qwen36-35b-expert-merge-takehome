"""CPU regression for Qwen3.5-MoE Liger loss routing, not a GPU OOM replay.

Run with the SFT environment. The real Liger forward and label-shifting code
execute on tiny tensors; only the Triton kernel is replaced by CPU chunked CE.
"""
import argparse
from types import SimpleNamespace

import torch
from torch import nn
from torch.nn import functional as F
from transformers.loss.loss_utils import ForCausalLMLoss

from liger_kernel.transformers.model import qwen3_5_moe
from liger_kernel.transformers import functional as liger_functional


class DecoderOutput(SimpleNamespace):
    def __getitem__(self, index):
        assert index == 0
        return self.last_hidden_state


class Decoder(nn.Module):
    def forward(self, inputs_embeds, **kwargs):
        return DecoderOutput(last_hidden_state=inputs_embeds, past_key_values=None,
                             hidden_states=None, attentions=None, rope_deltas=None,
                             router_logits=None)


class CountingLinear(nn.Linear):
    def __init__(self):
        super().__init__(8, 17, bias=False)
        self.calls = 0

    def forward(self, inputs):
        self.calls += 1
        return super().forward(inputs)


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = Decoder()
        self.lm_head = CountingLinear()
        self.config = SimpleNamespace(text_config=SimpleNamespace(hidden_size=8, vocab_size=17),
                                      return_dict=True, use_return_dict=True)
        self.loss_function = ForCausalLMLoss


def cpu_chunked_ce(inputs, weight, target, reduction='mean', ignore_index=-100, **kwargs):
    # Exercise the real Liger label shift/normalization using a CPU CE backend.
    total = sum(F.cross_entropy(F.linear(inputs[start:start + 3], weight).float(),
                                target[start:start + 3], ignore_index=ignore_index,
                                reduction='sum') for start in range(0, len(inputs), 3))
    return total if reduction == 'sum' else total / (target != ignore_index).sum()


@torch.no_grad()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unpatched', action='store_true')
    args = parser.parse_args()
    if not args.unpatched:
        from sft_eval_loss import enable_liger_eval_loss
        enable_liger_eval_loss()

    torch.manual_seed(20261016)
    torch.set_num_threads(1)
    liger_functional.liger_fused_linear_cross_entropy = cpu_chunked_ce
    model = TinyModel().eval()
    hidden = torch.randn(2, 11, 8)
    labels = torch.randint(0, 17, (2, 11))
    labels[:, :4] = -100  # Mask user/prompt tokens.
    labels[0, -2:] = -100  # Mask padding.
    forward = qwen3_5_moe.lce_forward_conditional_generation
    # Swift calls the native Liger apply function after this worker hook.
    from liger_kernel.transformers.monkey_patch import apply_liger_kernel_to_qwen3_5_moe
    from transformers.models.qwen3_5_moe.modeling_qwen3_5_moe import Qwen3_5MoeForConditionalGeneration
    apply_liger_kernel_to_qwen3_5_moe(rope=False, rms_norm=False, swiglu=False,
                                    cross_entropy=False, fused_linear_cross_entropy=True)
    assert Qwen3_5MoeForConditionalGeneration.forward is forward

    dense = forward(model, inputs_embeds=hidden, labels=labels, skip_logits=False)
    model.lm_head.calls = 0
    actual = forward(model, inputs_embeds=hidden, labels=labels)
    assert actual.logits is None and model.lm_head.calls == 0, (
        'labelled eval materialized full-vocabulary logits instead of using FLCE')
    torch.testing.assert_close(actual.loss, dense.loss, rtol=1e-6, atol=1e-6)

    # Changing states whose next-token targets are masked must not affect loss.
    targets = F.pad(labels, (0, 1), value=-100)[..., 1:]
    changed_hidden = hidden.clone()
    changed_hidden[targets == -100] += 100
    changed = forward(model, inputs_embeds=changed_hidden, labels=labels)
    torch.testing.assert_close(changed.loss, actual.loss, rtol=1e-6, atol=1e-6)

    # The real Liger frontend also preserves explicit global-item normalization.
    for reduction_items in [None, int((targets != -100).sum()) + 3]:
        expected = ForCausalLMLoss(F.linear(hidden, model.lm_head.weight), labels, 17,
                                   num_items_in_batch=reduction_items)
        from liger_kernel.transformers.model.loss_utils import LigerForCausalLMLoss
        actual_loss = LigerForCausalLMLoss(hidden, model.lm_head.weight, labels, 8,
                                          num_items_in_batch=reduction_items)
        torch.testing.assert_close(actual_loss, expected, rtol=1e-6, atol=1e-6)

    # The label-free generation path must still return logits.
    generated = forward(model, inputs_embeds=hidden, logits_to_keep=1)
    assert generated.logits.shape == (2, 1, 17)
    model.train()
    trained = forward(model, inputs_embeds=hidden, labels=labels)
    assert trained.logits is None
    torch.testing.assert_close(trained.loss, actual.loss, rtol=1e-6, atol=1e-6)
    print('PASS: labelled eval skips logits; causal CE, -100 masks, normalization agree; generation unchanged')


if __name__ == '__main__':
    main()
