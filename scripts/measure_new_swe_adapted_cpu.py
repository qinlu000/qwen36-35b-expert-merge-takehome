"""Measure the exact, untruncated target-contract candidate sequences on CPU."""
import json
import os
from pathlib import Path

for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from tokenizers import Tokenizer
from transformers.utils.chat_template_utils import _compile_jinja_template
from audit_new_swe_cpu import MODEL_REV, sha, distribution

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/data/candidates/new_swe_20261016/night_v2'
tokenizer_path = root / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'
template_path = root / 'analysis/source_snapshots/model_chat_template.jinja'
tokenizer = Tokenizer.from_file(str(tokenizer_path))
tokenizer.no_truncation()
tokenizer.no_padding()
template = _compile_jinja_template(template_path.read_text())
rows = []
for split in ['train', 'val']:
    for line in (out / f'{split}.target_contract.candidate.jsonl').open():
        row = json.loads(line)
        rendered = template.render(messages=row['messages'], tools=row['tools'], add_generation_prompt=False,
            enable_thinking=False, preserve_thinking=False)
        rows.append({'family_key': row['metadata']['family_key'], 'split': split,
            'full_sequence_tokens': len(tokenizer.encode(rendered, add_special_tokens=False).ids)})
(out / 'adapted_token_lengths.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in rows))
report = {'splits': {split: {'rows': sum(x['split'] == split for x in rows),
        'total_full_sequence_tokens': sum(x['full_sequence_tokens'] for x in rows if x['split'] == split),
        'full_sequence_tokens': distribution([x['full_sequence_tokens'] for x in rows if x['split'] == split])}
        for split in ['train', 'val']},
    'tokenizer_sha256': sha(tokenizer_path), 'template_sha256': sha(template_path),
    'input_sha256': {f'{split}.target_contract.candidate.jsonl': sha(out / f'{split}.target_contract.candidate.jsonl') for split in ['train', 'val']},
    'lengths_sha256': sha(out / 'adapted_token_lengths.jsonl'),
    'scope': 'Complete sequences after fixed system/submission adaptation. Exact pinned Qwen tokenizer/template, non-thinking; no truncation, windows, packing, GPU or Swift-label claim.'}
(out / 'adapted_token_summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2))
