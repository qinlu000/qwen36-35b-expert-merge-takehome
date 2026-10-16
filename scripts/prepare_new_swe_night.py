"""Select 500/100 new SWE families and audit cleaned, untruncated traces on CPU."""
import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from audit_new_swe_cpu import REV, MODEL_REV, CapturedLongOutput, normalize, chain_issues, sha, distribution
from candidate_selection import proportional_quotas, text_hash


def convert_observation(text, xml_template, json_template):
    if not text.startswith(('<exception>', '<returncode>')):
        assert isinstance(json.loads(text), dict)
        return text, 'json_unchanged'
    prefix = r'\A(?:<exception>(?P<exception>.*?)</exception>\n)?<returncode>(?P<rc>-?\d+)</returncode>\n'
    match = re.fullmatch(prefix + r'<output>\n(?P<output>.*)</output>\Z', text, re.S)
    if match:
        output = match['output']
        kind = 'xml_short'
    else:
        match = re.fullmatch(prefix + r'<warning>.*?</warning><output_head>\n(?P<head>.{5000})\n</output_head>\n<elided_chars>\n(?P<elided>\d+) characters elided\n</elided_chars>\n<output_tail>\n(?P<tail>.{5000})\n</output_tail>\Z', text, re.S)
        assert match, 'unknown_xml_layout'
        output = CapturedLongOutput(match['head'], match['tail'], int(match['elided']))
        kind = 'xml_head_tail'
    obs = {'returncode': int(match['rc']), 'exception_info': match['exception'], 'output': output}
    assert xml_template.render(output=obs) == text, 'native_xml_roundtrip_mismatch'
    result = json_template.render(output=obs)
    mapped = json.loads(result)
    assert mapped['returncode'] == obs['returncode']
    assert mapped.get('exception_info') == (obs['exception_info'] or None)
    if kind == 'xml_short':
        assert mapped['output'] == output
    else:
        assert (mapped['output_head'], mapped['output_tail'], mapped['elided_chars']) == (output.head, output.tail, output.elided)
    return result, kind


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.root
    out = root / 'artifacts/data/candidates/new_swe_20261016/night_v2'
    out.mkdir(parents=True, exist_ok=True)
    candidates_path = out.parent / 'ranked_candidates.jsonl'
    candidates = [json.loads(x) for x in candidates_path.read_text().splitlines()]
    assert len(candidates) == 9436
    fixed_metadata_path = root / 'artifacts/data/_metadata/night_swe_20261016/fixed_hard51_language.json'
    target = json.loads(fixed_metadata_path.read_text())
    assert target['exact_ids_match'] and target['rows'] == 51
    weights = Counter(target['language_counts'])
    assert sum(weights.values()) == 51
    quotas = {'train': proportional_quotas(500, weights), 'val': proportional_quotas(100, weights)}
    # Use published task environments from rebench for the execution-dev candidate pool.
    # Reserve whole repositories; never make an executable-val claim from a trace alone.
    selected = []
    val_repos = set()
    for language, quota in quotas['val'].items():
        pool = sorted((x for x in candidates if x['split'] == 'val' and x['source'] == 'swe-rebench-v2' and x['language'] == language), key=lambda x: x['rank_key'])
        counts = Counter()
        chosen = []
        for row in pool:
            if counts[row['repo']] >= 8:
                continue
            counts[row['repo']] += 1
            chosen.append(dict(row, selection_split='val', val_use='heldout_loss_only_until_environment_and_grader_verified'))
            if len(chosen) == quota:
                break
        assert len(chosen) == quota, (language, quota, len(chosen))
        selected.extend(chosen)
        val_repos.update(x['repo'] for x in chosen)
    for language, quota in quotas['train'].items():
        pool = [x for x in candidates if x['split'] == 'train' and x['language'] == language and x['repo'] not in val_repos]
        source_quota = proportional_quotas(quota, Counter(x['source'] for x in pool))
        for source, count in source_quota.items():
            available = sorted((x for x in pool if x['source'] == source), key=lambda x: x['rank_key'])
            assert len(available) >= count
            selected.extend(dict(x, selection_split='train') for x in available[:count])
    assert len(selected) == 600
    train = [x for x in selected if x['selection_split'] == 'train']
    val = [x for x in selected if x['selection_split'] == 'val']
    assert not ({x['repo'] for x in train} & {x['repo'] for x in val})
    assert not ({x['family_key'] for x in train} & {x['family_key'] for x in val})
    for split, rows in [('train', train), ('val', val)]:
        (out / f'{split}.manifest.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in rows))
    print(json.dumps({'event': 'selected', 'quota': quotas, 'val_repositories': len(val_repos)}), flush=True)

    import pyarrow as pa
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    import yaml
    from jinja2 import Template
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    tokenizer_path = root / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    template_path = root / 'analysis/source_snapshots/model_chat_template.jinja'
    template = _compile_jinja_template(template_path.read_text())
    native_config = root / 'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/config/benchmarks/swebench.yaml'
    target_config = root / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml'
    xml_template = Template(yaml.safe_load(native_config.read_text())['model']['observation_template'])
    json_template = Template(yaml.safe_load(target_config.read_text())['model']['observation_template'])
    byfile = defaultdict(dict)
    for row in selected:
        byfile[row['file']][row['row']] = row
    lengths, quarantined, observation_counts, cleaning_counts = [], [], Counter(), Counter()
    output_files = {split: (out / f'{split}.cleaned.candidate.jsonl').open('w') for split in ['train', 'val']}
    start = time.monotonic()
    for file, wanted in sorted(byfile.items()):
        pf = pq.ParquetFile(root / 'artifacts/data/raw/open_swe' / REV / file)
        offset = 0
        for batch in pf.iter_batches(batch_size=32, columns=['messages', 'tools'], use_threads=False):
            for index in sorted(i for i in wanted if offset <= i < offset + len(batch)):
                record = wanted[index]
                raw = batch.slice(index - offset, 1).to_pylist()[0]
                try:
                    messages, cleaning = normalize(raw['messages'], True)
                    tools = [json.loads(t) if isinstance(t, str) else t for t in raw['tools']]
                    assert not chain_issues(messages, tools)
                    counts = Counter()
                    pending = []
                    for turn, message in enumerate(messages):
                        if message['role'] == 'assistant':
                            pending = []
                            assert 'reasoning_content' not in message
                            assert '<think>' not in message['content'] and '</think>' not in message['content']
                            for n, call in enumerate(message.get('tool_calls', [])):
                                assert call['function']['name'] == 'bash'
                                assert set(call['function']['arguments']) == {'command'}
                                call['id'] = f"call_{record['family_key'][:12]}_{turn}_{n}"
                                call['type'] = 'function'
                                pending.append(call['id'])
                        elif message['role'] == 'tool':
                            message['tool_call_id'] = pending.pop(0)
                            message['content'], kind = convert_observation(message['content'], xml_template, json_template)
                            counts[kind] += 1
                    text = template.render(messages=messages, tools=tools, add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)
                    clean_tokens = len(tokenizer.encode(text, add_special_tokens=False).ids)
                    # Count complete-prefix deltas for assistant turns as an audit proxy, not Swift labels.
                    assistant_body_tokens = []
                    for m in messages:
                        if m['role'] == 'assistant':
                            body = m['content'] + json.dumps(m.get('tool_calls', []), ensure_ascii=False)
                            assistant_body_tokens.append(len(tokenizer.encode(body, add_special_tokens=False).ids))
                    user_text = '\n'.join(m.get('content', '') for m in messages if m['role'] == 'user')
                    measured = {**record, 'clean_total_tokens': clean_tokens,
                        'assistant_content_tool_json_tokens_proxy': sum(assistant_body_tokens),
                        'max_assistant_content_tool_json_tokens_proxy': max(assistant_body_tokens, default=0),
                        'user_text_sha256': text_hash(user_text),
                        'observation_conversion_counts': dict(counts),
                        'reasoning_cleaning_counts': dict(cleaning),
                        'ids': 'generated_from_source_order; source_order_not_independently_verified',
                        'export_status': 'cleaned_candidate_not_training_released',
                        'environment_status': 'not_restored', 'ms_swift_labels': 'not_verified'}
                    output_files[record['selection_split']].write(json.dumps({'messages': messages, 'tools': tools, 'metadata': measured}, ensure_ascii=False) + '\n')
                    lengths.append(measured)
                    observation_counts.update(counts)
                    cleaning_counts.update(cleaning)
                except (ValueError, AssertionError, KeyError, IndexError) as exc:
                    quarantined.append({**record, 'reason': str(exc)})
            offset += len(batch)
        print(json.dumps({'event': 'converted_shard', 'file': file, 'rows_done': len(lengths), 'quarantined': len(quarantined)}), flush=True)
    for f in output_files.values():
        f.close()
    (out / 'lengths.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in lengths))
    (out / 'quarantined.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in quarantined))
    cross_exact = {x['user_text_sha256'] for x in lengths if x['selection_split'] == 'train'} & {x['user_text_sha256'] for x in lengths if x['selection_split'] == 'val'}
    assert not cross_exact
    report = {'source_revision': REV, 'source_teacher': 'Qwen3.8-Flash-Next',
        'candidate_input_sha256': sha(candidates_path), 'fixed_hard51_metadata_sha256': sha(fixed_metadata_path),
        'selection': {'target_tasks': 51, 'fixed_official_repo_language_counts': dict(weights),
            'language_basis': 'Fixed official HF hard/test repo_language, exact match to locked HARD-51 IDs. This is the published task metadata label. No problem statements, hidden tests, reference patches or formal outcomes read.',
            'supersedes': 'night_v1 used current GitHub repo primary language proxy (JS1/TS10), which disagrees with fixed official JS10/TS1. night_v1 is not the selected dataset.',
            'official_issue_category_combinations': target['category_counts'],
            'quotas': quotas, 'source_mix': 'Within train language, proportional to eligible source counts; all val from rebench to prioritize published task environments.',
            'val_repository_count': len(val_repos), 'train_repository_count': len({x['repo'] for x in train}),
            'train_val_repository_overlap': 0, 'train_val_family_overlap': 0,
            'train_val_exact_user_text_overlap': len(cross_exact), 'val_tasks_per_repository_cap': 8,
            'type_scope': 'publisher successful bug-fix only, per explicit user approval; not a general SWE task distribution'},
        'converted': len(lengths), 'quarantined': len(quarantined),
        'observation_conversion_counts': dict(observation_counts), 'cleaning_counts': dict(cleaning_counts),
        'splits': {split: {'rows': sum(x['selection_split'] == split for x in lengths),
            'languages': dict(Counter(x['language'] for x in lengths if x['selection_split'] == split)),
            'sources': dict(Counter(x['source'] for x in lengths if x['selection_split'] == split)),
            'total_full_sequence_tokens': sum(x['clean_total_tokens'] for x in lengths if x['selection_split'] == split),
            'full_sequence_tokens': distribution([x['clean_total_tokens'] for x in lengths if x['selection_split'] == split]),
            'assistant_content_tool_json_proxy_tokens': sum(x['assistant_content_tool_json_tokens_proxy'] for x in lengths if x['selection_split'] == split),
            'max_assistant_content_tool_json_proxy': distribution([x['max_assistant_content_tool_json_tokens_proxy'] for x in lengths if x['selection_split'] == split])} for split in ['train', 'val']},
        'sha256': {p.name: sha(p) for p in out.glob('*.jsonl')},
        'tokenizer_sha256': sha(tokenizer_path), 'chat_template_sha256': sha(template_path),
        'seconds': time.monotonic() - start,
        'scope': 'CPU candidate preparation. No trajectory commands, containers, model API, training, GPU backward or formal evaluations run. No truncation, packing or windows selected. Publisher resolved label not replayed. Tool IDs assigned in source order, whose source collector revision/order remains unproven. XML conversion preserves visible fields and exact native roundtrip; source warning wrapping changed and unseen elided text never reconstructed. Val only heldout loss until task runtime and independent grader verified. Actual Swift supervision masks remain pending.'}
    (out / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'event': 'complete', 'converted': len(lengths), 'quarantined': len(quarantined), 'seconds': report['seconds']}), flush=True)


if __name__ == '__main__':
    main()
