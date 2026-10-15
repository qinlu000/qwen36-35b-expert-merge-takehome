"""Small deterministic helpers for independent, stratified candidate manifests."""

import hashlib
import re
import unicodedata


SPLIT_SEED = 'apex-new-data-v1-20261016'


def normalized_text(text):
    text = unicodedata.normalize('NFKC', text)
    return re.sub(r'\s+', ' ', text).strip().casefold()


def text_hash(text):
    return hashlib.sha256(normalized_text(text).encode('utf-8')).hexdigest()


def family_rank(family_key):
    return hashlib.sha256((SPLIT_SEED + '\0' + family_key).encode('utf-8')).hexdigest()


def family_partition(family_key):
    # Candidate reserve only. The number of executable val tasks is chosen later.
    return 'val' if int(family_rank(family_key)[:16], 16) % 10 == 0 else 'train'


def proportional_quotas(total, weights):
    """Largest-remainder quotas, deterministic ties; report unavailable strata separately."""
    denominator = sum(weights.values())
    quotas = {key: total * count // denominator for key, count in weights.items()}
    order = sorted(weights, key=lambda key: (-(total * weights[key] % denominator), key))
    for key in order[:total - sum(quotas.values())]:
        quotas[key] += 1
    return quotas
