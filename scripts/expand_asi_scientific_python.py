"""Add original human scientific-Python references; preserve frozen SAB train/val."""

import argparse
from collections import Counter, defaultdict
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from jinja2.sandbox import ImmutableSandboxedEnvironment
from tokenizers import Tokenizer

DS_REV = 'b39aab71da6d23ef8d3cac59a7c5f834516ab334'
SCI_REV = '4510f6a6aa27c43fad7b43da2c59602a86e88480'
MODEL_REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'
SYSTEM = ('You are an expert scientific Python programmer. Solve the original task and '
          'return only one Python code block. Follow the requested interface: a code '
          'completion may be a snippet or an indented function body rather than a '
          'standalone program. Preserve the required indentation. No tools are available.')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def words(text):
    return re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKC', text).lower())


def grams(text):
    tokens = words(text)
    return {tuple(tokens[i:i + 13]) for i in range(len(tokens) - 12)}


def scicode_prompt(row):
    parts = [row['problem_description_main'], row['problem_background_main'],
             'Input/output specification:\n' + row['problem_io'],
             'Scientific dependencies:\n' + row['required_dependencies']]
    for step in row['sub_steps']:
        parts += [step['step_description_prompt'], step['step_background'],
                  'Required interface:\n' + step['function_header'], step['return_line']]
    return '\n\n'.join(part for part in parts if part)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    raw = root / 'artifacts/data/raw/scientific_python_aux'
    frozen = root / 'artifacts/data/candidates/scienceagentbench_verified_9c6e96c9/swift_ready'
    output = root / 'artifacts/data/candidates/asi_sft_expanded_20261016'
    output.mkdir(parents=True, exist_ok=True)

    # Read public formal inputs only. No formal answers, tests, or score files.
    formal_paths = sorted((root / 'artifacts/asi/instances_seed31415').glob('*/prompt_b*.md'))
    assert len(formal_paths) == 240
    protected = {str(p.relative_to(root)): p.read_text() for p in formal_paths}
    validation = rows(frozen / 'val.messages.jsonl')
    assert len(validation) == 20
    for i, row in enumerate(validation):
        protected[f'sab_val:{i}'] = '\n'.join(m['content'] for m in row['messages'] if m['role'] == 'user')
    index = defaultdict(set)
    for key, prompt in protected.items():
        for gram in grams(prompt):
            index[gram].add(key)

    ds = [json.loads(line) for line in gzip.decompress((raw / 'ds1000.jsonl.gz').read_bytes()).splitlines()]
    sci = rows(raw / 'scicode_problems_dev.jsonl')
    assert len(ds) == 1000 and len(sci) == 15
    candidates = []
    for row in ds:
        meta = row['metadata']
        candidates.append({'source': 'DS-1000', 'source_revision': DS_REV,
            'source_split': 'test_repurposed_for_auxiliary_training',
            'source_id': str(meta['problem_id']), 'teacher': 'human_original_reference',
            'family': f"ds1000:{meta['library']}:{meta['perturbation_origin_id']}",
            'language': 'Python', 'library': meta['library'],
            'perturbation_type': meta['perturbation_type'], 'prompt': row['prompt'],
            'reference': row['reference_code'], 'license': 'CC-BY-SA-4.0',
            'scope': 'original_library_code_completion_not_ASI_file_workflow'})
    for row in sci:
        candidates.append({'source': 'SciCode', 'source_revision': SCI_REV,
            'source_split': 'validation_repurposed_for_auxiliary_training',
            'source_id': row['problem_id'], 'teacher': 'human_original_reference',
            'family': 'scicode:' + row['problem_id'], 'language': 'Python',
            'problem_name': row['problem_name'], 'prompt': scicode_prompt(row),
            'reference': row['general_solution'], 'license': 'Apache-2.0',
            'scope': 'original_main_problem_function_reference_not_ASI_file_workflow'})

    blocked_families, overlaps = set(), []
    for row in candidates:
        hits = sorted({key for gram in grams(row['prompt']) for key in index.get(gram, ())})
        if hits:
            blocked_families.add(row['family'])
            overlaps.append({'source': row['source'], 'source_id': row['source_id'],
                             'family': row['family'], 'protected_input_hits': hits})

    tokenizer = Tokenizer.from_file(str(root / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    def raise_exception(message):
        raise ValueError(message)
    env.globals['raise_exception'] = raise_exception
    template = env.from_string((root / 'analysis/source_snapshots/model_chat_template.jinja').read_text())
    accepted, provenance, excluded = [], [], []
    for row in candidates:
        meta = {k: v for k, v in row.items() if k not in {'prompt', 'reference'}}
        if row['family'] in blocked_families:
            excluded.append(dict(meta, reason='protected_input_13gram_family_overlap'))
            continue
        # The original label stays byte-for-byte inside the code fence. No new solution.
        answer = '```python\n' + row['reference'] + '\n```'
        messages = [{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': row['prompt']},
                    {'role': 'assistant', 'content': answer}]
        rendered = template.render(messages=messages, tools=None, add_generation_prompt=False,
                                   enable_thinking=False, preserve_thinking=False)
        full, assistant = tokenizer.encode_batch([rendered, answer], add_special_tokens=False)
        meta.update(full_sequence_tokens=len(full.ids), assistant_content_tokens=len(assistant.ids))
        if len(full.ids) > 65536 or len(assistant.ids) > 8192:
            excluded.append(dict(meta, reason='complete_sample_exceeds_64k_or_8k'))
            continue
        assert '<think>' not in answer and '</think>' not in answer
        accepted.append({'messages': messages})
        provenance.append(dict(meta, row=82 + len(accepted) - 1))

    original_train = (frozen / 'train.messages.jsonl').read_bytes()
    assert len(original_train.splitlines()) == 82 and original_train.endswith(b'\n')
    auxiliary_bytes = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in accepted).encode()
    (output / 'train.messages.jsonl').write_bytes(original_train + auxiliary_bytes)
    for name in ['val.messages.jsonl', 'val.tasks.jsonl']:
        shutil.copyfile(frozen / name, output / name)
        assert (output / name).read_bytes() == (frozen / name).read_bytes()
    assert (output / 'train.messages.jsonl').read_bytes().startswith(original_train)
    for name, records in [('auxiliary.provenance.jsonl', provenance),
                          ('excluded.jsonl', excluded), ('protected_input_overlap.jsonl', overlaps)]:
        (output / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    sab_manifest = json.loads((frozen / 'candidate_manifest.json').read_text())
    sab_train = [r for r in sab_manifest['records'] if r['split'] == 'train']
    assert len(sab_train) == 82
    prefix_provenance = [{'row': i, 'source': 'ScienceAgentBench',
        'source_revision': '9c6e96c9e74572e979b0930ee735041cef528cb7',
        'source_id': r['task_id'], 'family': 'sab_repo:' + r['repo_group'],
        'teacher': 'human_original_reference', 'language': 'Python',
        'license': r['license'], 'original_code_unmodified': True}
        for i, r in enumerate(sab_train)]
    (output / 'train.provenance.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n'
        for r in prefix_provenance + provenance))

    # One fixed-template token measurement of the retained frozen SAB prefix and val.
    token_counts = {'train': [], 'val': []}
    sab_assistant_max = {}
    for split, samples in [('train', rows(frozen / 'train.messages.jsonl')), ('val', validation)]:
        assistant_sizes = []
        for sample in samples:
            rendered = template.render(messages=sample['messages'], tools=None, add_generation_prompt=False,
                                       enable_thinking=False, preserve_thinking=False)
            bodies = [m['content'] for m in sample['messages'] if m['role'] == 'assistant']
            encoded = tokenizer.encode_batch([rendered, *bodies], add_special_tokens=False)
            token_counts[split].append(len(encoded[0].ids))
            assistant_sizes.extend(len(x.ids) for x in encoded[1:])
        sab_assistant_max[split] = max(assistant_sizes)
    train_counts = token_counts['train'] + [r['full_sequence_tokens'] for r in provenance]
    summary = {'training_started': False, 'base_revision': MODEL_REV,
        'frozen_sab_train_rows': 82, 'frozen_sab_val_rows': 20,
        'sab_train_prefix_byte_identical': True, 'sab_val_files_byte_identical': True,
        'source_candidates': dict(Counter(r['source'] for r in candidates)),
        'accepted_auxiliary': dict(Counter(r['source'] for r in provenance)),
        'accepted_auxiliary_families': dict(Counter(source for source, family in
            {(r['source'], r['family']) for r in provenance})),
        'ds1000_published_original_problem_count': 451,
        'ds1000_actual_library_origin_metadata_groups': len({r['family'] for r in candidates if r['source'] == 'DS-1000'}),
        'excluded': dict(Counter(r['reason'] for r in excluded)),
        'protected_formal_input_files_read': len(formal_paths), 'formal_gold_read': False,
        'protected_sab_val_prompts': len(validation),
        'train_rows': 82 + len(accepted), 'val_rows': 20,
        'train_complete_tokens': sum(train_counts), 'train_max_complete_tokens': max(train_counts),
        'auxiliary_complete_tokens': sum(r['full_sequence_tokens'] for r in provenance),
        'auxiliary_max_assistant_content_tokens': max(r['assistant_content_tokens'] for r in provenance),
        'sab_train_complete_tokens': sum(token_counts['train']),
        'val_complete_tokens': sum(token_counts['val']), 'val_max_complete_tokens': max(token_counts['val']),
        'frozen_sab_train_max_assistant_content_tokens': sab_assistant_max['train'],
        'frozen_sab_val_max_assistant_content_tokens': sab_assistant_max['val'],
        'token_method': 'fixed original Qwen Jinja template + tokenizer.json, no truncation/padding; assistant content proxy, not Swift label count',
        'new_model_generated_solutions': 0, 'ecocoder_included': False,
        'limitations': ['DS-1000 contains task variants, not 1000 independent original questions.',
            'Scientific Python function/library auxiliary references are not ASI file-workflow trajectories.',
            '13-gram public-input exclusion does not prove semantic or paper lineage independence.',
            'No code execution or new correctness verification; original human references preserved.',
            'SciCode validation and DS-1000 test repurposed as training are not held-out evaluation sets here.']}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
