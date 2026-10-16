"""Expand complete new-teacher SWE trajectories; keep the frozen validation export."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import shutil
import time

for name in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[name] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from audit_new_swe_cpu import REV, MODEL_REV, normalize
from candidate_selection import normalized_text, proportional_quotas
from prepare_new_swe_night import convert_observation

OLD_SUBMIT = ('Step 3: Submit (EXACT command required)\nYou MUST use this EXACT command to submit:\n\n'
    '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt\n```\n\n'
    'If the command fails (nonzero exit status), it will not submit.\n')
NEW_SUBMIT = ('Step 3: Submit (EXACT command required)\nSubmit your changes and finish your work by issuing this command:\n\n'
    '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```\n\n'
    'Do not combine it with any other command. After this command, you cannot continue working on this task.\n')
SOURCE_SYSTEM = 'You are a helpful assistant that can interact with a computer shell to solve programming tasks.'
FINAL_COMMANDS = {
    'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt',
    'cd /testbed && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt',
    'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat /testbed/patch.txt',
}
BEGIN, END = '__APEX_ASST_BEGIN_2K__', '__APEX_ASST_END_2K__'


def process_shard(spec):
    root_s, file, records = spec
    root = Path(root_s)
    import pyarrow as pa
    import pyarrow.parquet as pq
    import yaml
    from jinja2 import Template
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    tokenizer = Tokenizer.from_file(str(root / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    text = (root / 'analysis/source_snapshots/model_chat_template.jinja').read_text()
    text = text.replace('{%- elif message.role == "assistant" %}', '{%- elif message.role == "assistant" %}{{- "' + BEGIN + '" }}')
    text = text.replace('{%- elif message.role == "tool" %}', '{{- "' + END + '" }}{%- elif message.role == "tool" %}')
    template = _compile_jinja_template(text)
    source_config = root / 'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/config/benchmarks/swebench.yaml'
    target_config = yaml.safe_load((root / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml').read_text())
    xml = Template(yaml.safe_load(source_config.read_text())['model']['observation_template'])
    target = Template(target_config['model']['observation_template'])
    system = target_config['agent']['system_template']
    wanted = {r['row']: r for r in records}
    output = root / 'artifacts/data/candidates/new_swe_20261016/expanded_2k/work' / (file.replace('/', '_') + '.jsonl')
    rejected = []
    good = 0
    with output.open('w') as destination:
        offset = 0
        pf = pq.ParquetFile(root / 'artifacts/data/raw/open_swe' / REV / file)
        for batch in pf.iter_batches(batch_size=32, columns=['messages', 'tools'], use_threads=False):
            for index in sorted(i for i in wanted if offset <= i < offset + len(batch)):
                record = wanted[index]
                raw = batch.slice(index - offset, 1).to_pylist()[0]
                try:
                    messages, cleaning = normalize(raw['messages'], True)
                    tools = [json.loads(t) if isinstance(t, str) else t for t in raw['tools']]
                    pending = []
                    for turn, message in enumerate(messages):
                        if message['role'] == 'assistant':
                            pending = []
                            for n, call in enumerate(message.get('tool_calls', [])):
                                call['id'] = f"call_{record['family_key'][:12]}_{turn}_{n}"
                                call['type'] = 'function'
                                pending.append(call['id'])
                        elif message['role'] == 'tool':
                            message['tool_call_id'] = pending.pop(0)
                            message['content'], _ = convert_observation(message['content'], xml, target)
                    systems = [m for m in messages if m['role'] == 'system']
                    users = [m for m in messages if m['role'] == 'user' and OLD_SUBMIT in m['content']]
                    command = messages[-1]['tool_calls'][0]['function']['arguments']['command']
                    if len(systems) != 1 or systems[0]['content'] != SOURCE_SYSTEM or len(users) != 1 or command not in FINAL_COMMANDS:
                        raise ValueError('unknown_contract_wrapper')
                    systems[0]['content'] = system
                    users[0]['content'] = users[0]['content'].replace(OLD_SUBMIT, NEW_SUBMIT)
                    messages[-1]['tool_calls'][0]['function']['arguments']['command'] = 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'
                    rendered = template.render(messages=messages, tools=tools, add_generation_prompt=False,
                        enable_thinking=False, preserve_thinking=False)
                    bodies = []
                    for part in rendered.split(BEGIN)[1:]:
                        payload = part.split(END, 1)[0]
                        assert payload.startswith('<|im_start|>assistant\n')
                        bodies.append(payload.removeprefix('<|im_start|>assistant\n'))
                    assert len(bodies) == sum(m['role'] == 'assistant' for m in messages)
                    full = rendered.replace(BEGIN, '').replace(END, '')
                    sizes = [len(x.ids) for x in tokenizer.encode_batch([full, *bodies], add_special_tokens=False)]
                    meta = dict(record, full_sequence_tokens=sizes[0],
                        max_assistant_output_tokens=max(sizes[1:], default=0),
                        assistant_output_tokens=sum(sizes[1:]), reasoning_cleaning_counts=dict(cleaning))
                    if sizes[0] > 65536:
                        rejected.append(dict(meta, reason='complete_sequence_over_65536'))
                    elif meta['max_assistant_output_tokens'] > 8192:
                        rejected.append(dict(meta, reason='complete_assistant_reply_over_8192'))
                    else:
                        destination.write(json.dumps({'messages': messages, 'tools': tools, 'metadata': meta}, ensure_ascii=False) + '\n')
                        good += 1
                except (ValueError, AssertionError, KeyError, IndexError) as exc:
                    rejected.append(dict(record, reason=str(exc)))
            offset += len(batch)
    return str(output), good, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    root = args.root
    source = root / 'artifacts/data/candidates/new_swe_20261016'
    old = source / 'night_v2'
    output = source / 'expanded_2k'
    (output / 'work').mkdir(parents=True, exist_ok=True)
    frozen = old / 'swift_ready64k'
    old_train_ids = {json.loads(s)['family_key'] for s in (frozen / 'train.manifest.jsonl').read_text().splitlines()}
    val_repos = {json.loads(s)['repo'] for s in (old / 'val.manifest.jsonl').read_text().splitlines()}
    all_rows = [json.loads(s) for s in (source / 'ranked_candidates.jsonl').read_text().splitlines()]
    rows = [r for r in all_rows if r['split'] == 'train' and r['repo'] not in val_repos]
    weights = {'python': 20, 'go': 20, 'js': 10, 'ts': 1}
    desired = proportional_quotas(2000, weights)
    planned = []
    for language in weights:
        pool = [r for r in rows if r['language'] == language]
        # Include broad headroom, and all Go candidates because its supply is below quota.
        limit = min(len(pool), desired[language] + 500)
        source_quotas = proportional_quotas(limit, Counter(r['source'] for r in pool))
        for kind, n in source_quotas.items():
            planned += sorted((r for r in pool if r['source'] == kind), key=lambda r: r['rank_key'])[:n]
    byfile = defaultdict(list)
    for row in planned:
        byfile[row['file']].append(row)
    start = time.monotonic()
    (output / 'plan.json').write_text(json.dumps({'desired': desired,
        'planned': dict(Counter(r['language'] for r in planned)), 'rows': len(planned)}, indent=2) + '\n')
    rejected, paths = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for path, good, bad in executor.map(process_shard, [(str(root), f, r) for f, r in sorted(byfile.items())]):
            paths.append(Path(path))
            rejected.extend(bad)
            print(json.dumps({'event': 'shard_complete', 'file': path, 'eligible': good, 'rejected': len(bad)}), flush=True)
    accepted = []
    for path in paths:
        for line in path.open():
            accepted.append(json.loads(line)['metadata'])
    pools = {lang: sorted((r for r in accepted if r['language'] == lang),
        key=lambda r: (r['family_key'] not in old_train_ids, r['rank_key'])) for lang in weights}
    quotas = {lang: min(desired[lang], len(pools[lang])) for lang in weights}
    # Redistribute only unavailable quota, among the other original target languages.
    while sum(quotas.values()) < 2000:
        spare = {lang: weights[lang] for lang in weights if quotas[lang] < len(pools[lang])}
        if not spare:
            break
        addition = proportional_quotas(2000 - sum(quotas.values()), spare)
        for lang, n in addition.items():
            quotas[lang] += min(n, len(pools[lang]) - quotas[lang])
    chosen = []
    for lang, n in quotas.items():
        available = pools[lang]
        mix = proportional_quotas(n, Counter(r['source'] for r in available))
        for kind, count in mix.items():
            chosen += [r for r in available if r['source'] == kind][:count]
    chosen.sort(key=lambda r: (r['language'], r['rank_key']))
    ids = {r['family_key'] for r in chosen}
    assert len(chosen) == len(ids) == 2000
    old_eligible_ids = old_train_ids & {r['family_key'] for r in accepted}
    assert old_eligible_ids <= ids
    val_ids = {json.loads(s)['family_key'] for s in (frozen / 'val.manifest.jsonl').read_text().splitlines()}
    assert not ids & val_ids
    assert not {r['repo'] for r in chosen} & val_repos
    val_text = {normalized_text('\n'.join(m.get('content', '') for m in json.loads(s)['messages'] if m['role'] == 'user'))
        for s in (frozen / 'val.messages.jsonl').read_text().splitlines()}
    export = output / 'swift_ready64k'
    export.mkdir(exist_ok=True)
    selected_data = {}
    for path in paths:
        for line in path.open():
            row = json.loads(line)
            if row['metadata']['family_key'] in ids:
                text = normalized_text('\n'.join(m.get('content', '') for m in row['messages'] if m['role'] == 'user'))
                assert text not in val_text
                selected_data[row['metadata']['family_key']] = {'messages': row['messages'], 'tools': row['tools']}
    with (export / 'train.messages.jsonl').open('w') as handle:
        for row in chosen:
            handle.write(json.dumps(selected_data[row['family_key']], ensure_ascii=False) + '\n')
    (export / 'train.manifest.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in chosen))
    for filename in ['val.messages.jsonl', 'val.manifest.jsonl', 'val.excluded_over64k.jsonl']:
        shutil.copyfile(frozen / filename, export / filename)
        assert (frozen / filename).read_bytes() == (export / filename).read_bytes()
    (output / 'excluded.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rejected))
    summary = {'source': 'nvidia/Open-SWE-Traces', 'revision': REV, 'teacher': 'Qwen3.8-Flash-Next',
        'max_length': 65536, 'max_assistant_output': 8192, 'scanned': len(planned), 'eligible': len(accepted),
        'desired_language_quotas': desired, 'actual_language_quotas': quotas,
        'quota_policy': 'Keep fixed hard51 language proportions where supply allows; redistribute unavailable quota among original target languages.',
        'train': {'rows': len(chosen), 'total_full_sequence_tokens': sum(r['full_sequence_tokens'] for r in chosen),
            'previous_train_rows': len(old_train_ids), 'previous_train_rows_retained': len(old_eligible_ids),
            'max_full_sequence_tokens': max(r['full_sequence_tokens'] for r in chosen),
            'assistant_output_tokens': sum(r['assistant_output_tokens'] for r in chosen),
            'max_assistant_output_tokens': max(r['max_assistant_output_tokens'] for r in chosen),
            'repositories': len({r['repo'] for r in chosen}), 'sources': dict(Counter(r['source'] for r in chosen))},
        'val': dict(json.loads((frozen / 'summary.json').read_text())['splits']['val'], byte_identical_to_previous=True),
        'train_val_family_overlap': 0, 'train_val_repo_overlap': 0, 'train_val_exact_normalized_user_overlap': 0,
        'excluded': dict(Counter(r['reason'] for r in rejected)), 'seconds': time.monotonic() - start,
        'scope': 'CPU-only preparation; complete trajectories and replies, no truncation/repetition/task execution/API/GPU. Frozen val copied unchanged, including its existing length-policy exceptions. Full-token counts use pinned original Qwen template; native Swift may differ slightly.'}
    (export / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
