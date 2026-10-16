"""Use the existing Liger fused loss for labelled evaluation as well as training."""
from functools import wraps


def enable_liger_eval_loss():
    from liger_kernel.transformers.model import qwen3_5_moe

    original = qwen3_5_moe.lce_forward_conditional_generation

    @wraps(original)
    def forward(self, *args, **kwargs):
        has_labels = kwargs.get('labels') is not None or kwargs.get('shift_labels') is not None
        if not self.training and has_labels and kwargs.get('skip_logits') is None:
            kwargs['skip_logits'] = True
        return original(self, *args, **kwargs)

    qwen3_5_moe.lce_forward_conditional_generation = forward
