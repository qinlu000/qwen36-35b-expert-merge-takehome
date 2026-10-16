"""Audit two pinned new SWE shards on CPU; no task execution or training export."""
import argparse
import ast
import copy
import hashlib
import json
import os
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

REV = '1db674173119d71df45c22007af99e214600711a'
MODEL_REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'
FILES = [f'data/minisweagent/qwen38_flash_next/{p}' for p in [
    'scale-swe/train-00000-of-00007.parquet',
    'swe-rebench-v2/train-00000-of-00009.parquet']]
BEGIN, END = '__APEX_ASST_AUDIT_BEGIN_b2eb__', '__APEX_ASST_AUDIT_END_b2eb__'
SEED = 20261016


def observation_features(messages):
    counts = Counter()
    for m in messages:
        if m['role'] != 'tool':
            continue
        text = m.get('content') or ''
        try:
            obs = json.loads(text)
            counts['json_object' if isinstance(obs, dict) else 'json_other'] += 1
            if isinstance(obs, dict):
                counts['json_head_tail'] += 'output_head' in obs and 'output_tail' in obs
                counts['json_returncode_output'] += 'returncode' in obs and 'output' in obs
            continue
        except ValueError:
            counts['non_json'] += 1
        if text.startswith(('<exception>', '<returncode>')) and '<returncode>' in text:
            counts['xml_returncode'] += 1
            counts['xml_full_output'] += '<output>' in text
            counts['xml_head_tail'] += '<output_head>' in text and '<output_tail>' in text
            counts['xml_exception'] += '<exception>' in text
            continue
        try:
            obj = ast.literal_eval(text)
            counts['python_repr' if isinstance(obj, (dict, list)) else 'plain_text_or_unknown'] += 1
        except (ValueError, SyntaxError, TypeError):
            counts['json_like_unparsed' if text.lstrip().startswith(('{', '[')) else 'plain_text_or_unknown'] += 1
    return counts


class CapturedLongOutput:
    """Expose only the original visible head/tail and original length to templates."""
    def __init__(self, head, tail, elided):
        self.head, self.tail, self.elided = head, tail, elided

    def __len__(self):
        return 10000 + self.elided

    def __getitem__(self, index):
        if index == slice(None, 5000):
            return self.head
        if index == slice(-5000, None):
            return self.tail
        raise ValueError('unavailable_middle')


def xml_bridge_probe(messages, xml_template, json_template):
    """Roundtrip field extraction only; does not rewrite stored messages."""
    counts = Counter()
    prefix = r'\A(?:<exception>(?P<exception>.*?)</exception>\n)?<returncode>(?P<rc>-?\d+)</returncode>\n'
    short = re.compile(prefix + r'<output>\n(?P<output>.*)</output>\Z', re.S)
    long = re.compile(prefix + r'<warning>.*?</warning><output_head>\n(?P<head>.{5000})\n</output_head>\n<elided_chars>\n(?P<elided>\d+) characters elided\n</elided_chars>\n<output_tail>\n(?P<tail>.{5000})\n</output_tail>\Z', re.S)
    for m in messages:
        text = m.get('content') or ''
        if m['role'] != 'tool' or not text.startswith(('<exception>', '<returncode>')):
            continue
        counts['xml_observations'] += 1
        match = short.fullmatch(text)
        if match:
            output = match['output']; kind = 'short'
        else:
            match = long.fullmatch(text)
            if not match:
                counts['unrecognized_outer_layout'] += 1
                continue
            output = CapturedLongOutput(match['head'], match['tail'], int(match['elided'])); kind = 'head_tail'
        obs = {'returncode': int(match['rc']), 'exception_info': match['exception'], 'output': output}
        if xml_template.render(output=obs) != text:
            counts['native_xml_roundtrip_mismatch'] += 1
            continue
        mapped = json.loads(json_template.render(output=obs))
        assert mapped['returncode'] == obs['returncode']
        assert mapped.get('exception_info') == (obs['exception_info'] or None)
        if kind == 'short':
            assert mapped['output'] == output
        else:
            assert (mapped['output_head'], mapped['output_tail'], mapped['elided_chars']) == (output.head, output.tail, output.elided)
        counts['native_xml_exact_roundtrip_' + kind] += 1
        counts['target_json_visible_fields_preserved_' + kind] += 1
    return counts


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def family(repo, instance_id):
    return hashlib.sha256((repo.strip().lower() + '\0' + str(instance_id)).encode()).hexdigest()


def normalize(messages, clean):
    out, counts = [], Counter()
    for original in messages:
        m = {k: copy.deepcopy(v) for k, v in original.items() if v is not None}
        m.setdefault('content', '')
        for call in m.get('tool_calls', []):
            args = call['function']['arguments']
            if isinstance(args, str):
                call['function']['arguments'] = json.loads(args)
            if not isinstance(call['function']['arguments'], dict):
                raise ValueError('non_mapping_tool_arguments')
        if m['role'] == 'assistant':
            counts['reasoning_nonempty_messages'] += bool((m.get('reasoning_content') or '').strip())
            content = m['content']
            if not isinstance(content, str):
                raise ValueError('non_string_assistant')
            if '<think>' in content or '</think>' in content:
                match = re.match(r'\A\s*<think>.*?</think>\s*', content, re.S)
                if not match or '<think>' in content[match.end():] or '</think>' in content[match.end():]:
                    raise ValueError('unbalanced_or_nonleading_think')
                counts['leading_think_messages'] += 1
                if clean:
                    m['content'] = content[match.end():]
            if clean:
                m.pop('reasoning_content', None)
        out.append(m)
    return out, counts


def chain_issues(messages, tools):
    names = {t.get('function', t).get('name') for t in tools}
    issues, pending = Counter(), 0
    for m in messages:
        role = m['role']
        if role == 'assistant':
            if pending:
                issues['calls_without_response_before_assistant'] += pending
                pending = 0
            calls = m.get('tool_calls', [])
            pending = len(calls)
            for call in calls:
                if call['function']['name'] not in names:
                    issues['undefined_tool'] += 1
        elif role == 'tool':
            if pending:
                pending -= 1
            else:
                issues['tool_without_call'] += 1
        elif role not in ['system', 'user']:
            issues['unexpected_role'] += 1
    if pending:
        final_calls = messages[-1].get('tool_calls', [])
        # Published mini trajectories end at the submit action, without a fabricated result.
        terminal_submit = len(final_calls) == pending == 1 and (
            'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in
            final_calls[0]['function']['arguments'].get('command', ''))
        if not terminal_submit:
            issues['final_calls_without_response'] += pending
    return issues


def render(messages, tools, preserve, template, marked):
    kwargs = dict(messages=messages, tools=tools, add_generation_prompt=False,
                  enable_thinking=False, preserve_thinking=preserve)
    full = template.render(**kwargs)
    tagged = marked.render(**kwargs)
    assert tagged.replace(BEGIN, '').replace(END, '') == full
    bodies = []
    for part in tagged.split(BEGIN)[1:]:
        body = part.split(END, 1)[0]
        assert body.startswith('<|im_start|>assistant\n')
        bodies.append(body.removeprefix('<|im_start|>assistant\n'))
    assert len(bodies) == sum(m['role'] == 'assistant' for m in messages)
    return full, bodies


def synthetic_check(template, marked, tokenizer):
    tools = [{'type': 'function', 'function': {'name': 'bash', 'parameters': {
        'type': 'object', 'properties': {'command': {'type': 'string'}}}}}]
    messages = [
        {'role': 'user', 'content': 'Synthetic task'},
        {'role': 'assistant', 'content': '<think>PRIVATE_INLINE</think>Do action',
         'reasoning_content': 'PRIVATE_FIELD', 'tool_calls': [{'id': 'c1', 'type': 'function',
            'function': {'name': 'bash', 'arguments': '{"command":"printf STATE"}'}}]},
        {'role': 'tool', 'content': 'STATE'},
        {'role': 'assistant', 'content': 'Finished'}]
    raw, _ = normalize(messages, False)
    cleaned, counts = normalize(messages, True)
    assert cleaned[2] == raw[2]
    assert cleaned[1]['tool_calls'] == raw[1]['tool_calls']
    assert not chain_issues(cleaned, tools)
    full, bodies = render(cleaned, tools, False, template, marked)
    assert 'PRIVATE_INLINE' not in full and 'PRIVATE_FIELD' not in full
    assert '<function=bash>' in bodies[0] and 'printf STATE' in bodies[0]
    assert 'STATE' in full and len(bodies) == 2
    assert len(tokenizer.encode(full, add_special_tokens=False).ids) > sum(
        len(tokenizer.encode(b, add_special_tokens=False).ids) for b in bodies)
    try:
        normalize([{'role': 'assistant', 'content': '<think>unclosed'}], True)
    except ValueError as e:
        assert str(e) == 'unbalanced_or_nonleading_think'
    else:
        raise AssertionError('malformed thinking was not isolated')
    return {'passed': True, 'checks': ['both_thinking_representations_removed',
        'structured_tool_call_preserved', 'tool_state_preserved',
        'assistant_body_marker_matches_unmodified_template', 'malformed_think_isolated'],
        'synthetic_clean_tokens': len(tokenizer.encode(full, add_special_tokens=False).ids)}


def distribution(values):
    if not values:
        return {'n': 0}
    v = sorted(values)
    n = len(v)
    return {'n': n, 'mean': sum(v) / n, 'median': v[(n - 1) // 2],
            'p90': v[min(n - 1, int(n * .9))], 'p95': v[min(n - 1, int(n * .95))],
            'max': v[-1], 'fraction_le': {str(t): sum(x <= t for x in v) / n
                for t in [8192, 16384, 32768, 65536]}}


def summarize(rows):
    out = {'n': len(rows)}
    for key in ['raw_total', 'clean_total', 'clean_assistant_body_proxy', 'largest_clean_assistant_body']:
        out[key] = distribution([r[key] for r in rows])
    out['clean_assistant_body_fraction_of_full_tokens'] = (
        sum(r['clean_assistant_body_proxy'] for r in rows) / sum(r['clean_total'] for r in rows)) if rows else None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--per-shard', type=int, default=128)
    args = ap.parse_args()
    assert 1 <= args.per_shard <= 128
    import pyarrow as pa
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    import yaml
    from jinja2 import Template
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    root = args.root
    outdir = root / 'artifacts/data/audits/new_swe_20261016'
    outdir.mkdir(parents=True, exist_ok=True)
    rawroot = root / 'artifacts/data/raw/open_swe' / REV
    tokenizer_path = root / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'
    template_path = root / 'analysis/source_snapshots/model_chat_template.jinja'
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.no_truncation(); tokenizer.no_padding()
    source_template = template_path.read_text()
    template = _compile_jinja_template(source_template)
    modified = source_template.replace('{%- elif message.role == "assistant" %}',
        '{%- elif message.role == "assistant" %}{{- "' + BEGIN + '" }}')
    modified = modified.replace('{%- elif message.role == "tool" %}',
        '{{- "' + END + '" }}{%- elif message.role == "tool" %}')
    marked = _compile_jinja_template(modified)
    native_config = root / 'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent/config/benchmarks/swebench.yaml'
    target_config = root / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml'
    xml_template = Template(yaml.safe_load(native_config.read_text())['model']['observation_template'])
    json_template = Template(yaml.safe_load(target_config.read_text())['model']['observation_template'])
    synthetic = synthetic_check(template, marked, tokenizer)
    blocked = {s.lower() for s in json.loads((root / 'configs/data_exclusions.json').read_text())['swe_pro_repositories']}
    receipts = json.loads((outdir / 'download_receipts.json').read_text())
    expected = {r['file']: r for r in receipts}
    start = time.monotonic()
    metadata, samples, quarantined, newfamilies = [], [], [], set()
    rowpath = outdir / 'metadata_rows.jsonl'
    with rowpath.open('w') as output:
        for item in FILES:
            path = rawroot / item
            assert path.stat().st_size == expected[item]['bytes']
            assert sha(path) == expected[item]['upstream_sha256']
            pf = pq.ParquetFile(path)
            source = 'scale-swe' if '/scale-swe/' in item else 'swe-rebench-v2'
            counts = {k: Counter() for k in ['resolved', 'language', 'category', 'teacher', 'thinking', 'reasoning_effort', 'license', 'dataset']}
            families, repos, excluded, allowed_success = set(), set(), 0, 0
            offset = 0
            # Nested projection intentionally excludes reference_patch/model_patch.
            columns = ['repo', 'instance_id', 'trajectory_id', 'resolved', 'language', 'license',
                       'metadata.category', 'metadata.teacher_model', 'hf_dataset_name']
            for batch in pf.iter_batches(batch_size=256, columns=columns, use_threads=False):
                for j, row in enumerate(batch.to_pylist()):
                    repo = (row['repo'] or '').strip().lower()
                    key = family(repo, row['instance_id'])
                    families.add(key); newfamilies.add(key); repos.add(repo)
                    is_excluded = repo in blocked
                    excluded += is_excluded
                    allowed_success += row['resolved'] == 1 and not is_excluded
                    teacher = (row.get('metadata') or {}).get('teacher_model') or {}
                    for k, v in [('resolved', row['resolved']), ('language', row['language']),
                        ('license', row['license']), ('dataset', row['hf_dataset_name']),
                        ('category', (row.get('metadata') or {}).get('category')),
                        ('teacher', teacher.get('name')), ('thinking', teacher.get('enable_thinking')),
                        ('reasoning_effort', teacher.get('reasoning_effort'))]:
                        counts[k][str(v) if v is not None else '<missing>'] += 1
                    output.write(json.dumps({'file': item, 'row': offset + j, 'repo': repo,
                        'instance_id': row['instance_id'], 'trajectory_id': row['trajectory_id'],
                        'family_sha256': key, 'resolved': row['resolved'],
                        'exact_repo_excluded': is_excluded, 'language': row['language']}) + '\n')
                offset += len(batch)
            metadata.append({'file': item, 'rows': pf.metadata.num_rows, 'columns': pf.schema_arrow.names,
                'unique_families': len(families), 'unique_repositories': len(repos),
                'repeated_families_within_shard': pf.metadata.num_rows - len(families),
                'exact_repo_excluded_rows': excluded, 'source_success_after_exact_repo_exclusion': allowed_success,
                'counts': {k: dict(v) for k, v in counts.items()}})
            indexes = set(random.Random(SEED + FILES.index(item)).sample(
                range(pf.metadata.num_rows), min(args.per_shard, pf.metadata.num_rows)))
            offset = 0
            for batch in pf.iter_batches(batch_size=16, columns=['messages', 'tools', 'repo', 'resolved', 'instance_id', 'language', 'metadata.category'], use_threads=False):
                wanted = sorted(i - offset for i in indexes if offset <= i < offset + len(batch))
                for j in wanted:
                    row = batch.slice(j, 1).to_pylist()[0]
                    base = {'file': item, 'source': source, 'row': offset + j,
                        'family_sha256': family(row['repo'], row['instance_id']),
                        'language': row['language'], 'category': row['metadata']['category'],
                        'resolved': row['resolved'], 'exact_repo_excluded': row['repo'].lower() in blocked}
                    try:
                        tools = [json.loads(t) if isinstance(t, str) else t for t in row['tools']]
                        raw, clean_counts = normalize(row['messages'], False)
                        cleaned, _ = normalize(row['messages'], True)
                        issues = chain_issues(cleaned, tools)
                        if issues:
                            raise ValueError('action_chain:' + json.dumps(dict(issues), sort_keys=True))
                        raw_text, raw_bodies = render(raw, tools, True, template, marked)
                        clean_text, clean_bodies = render(cleaned, tools, False, template, marked)
                        lengths = [len(e.ids) for e in tokenizer.encode_batch(
                            [raw_text, clean_text, *clean_bodies], add_special_tokens=False)]
                        system = '\n'.join(m.get('content', '') for m in raw if m['role'] == 'system')
                        prompt = system + '\n' + next((m.get('content', '') for m in raw if m['role'] == 'user'), '')
                        observations = observation_features(raw)
                        samples.append({**base, 'raw_total': lengths[0], 'clean_total': lengths[1],
                            'clean_assistant_body_proxy': sum(lengths[2:]),
                            'largest_clean_assistant_body': max(lengths[2:], default=0),
                            'assistant_turns': len(clean_bodies), 'messages': len(raw),
                            'observations': dict(observations),
                            'xml_bridge_probe': dict(xml_bridge_probe(raw, xml_template, json_template)),
                            'multi_call_assistant_turns': sum(len(m.get('tool_calls', [])) > 1 for m in raw),
                            'tool_names': sorted({t.get('function', t).get('name') for t in tools}),
                            'tool_signatures': tools,
                            'system_hints': {hint: hint.lower() in system.lower() for hint in
                                ['/testbed', '/workspace', 'docker', 'bash', 'submit', 'persistent', 'separate shell']},
                            'prompt_hints': {hint: hint.lower() in prompt.lower() for hint in
                                ['/testbed', '/workspace', '/app', 'new subshell', 'patch.txt', 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT']},
                            'system_sha256': hashlib.sha256(system.encode()).hexdigest(), **dict(clean_counts)})
                    except (ValueError, TypeError, KeyError, AssertionError) as error:
                        quarantined.append({**base, 'reason': str(error).split(':', 1)[0]})
                offset += len(batch)
            print(json.dumps({'event': 'audited_shard', 'file': item, 'metadata_rows': offset,
                'sample_valid_so_far': len(samples), 'sample_quarantined_so_far': len(quarantined)}), flush=True)
    oldroot = rawroot / 'data/minisweagent/qwen36_27b'
    oldfamilies, oldrows, oldfiles = set(), 0, []
    for path in sorted(oldroot.rglob('*.parquet')):
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=512, columns=['repo', 'instance_id'], use_threads=False):
            for row in batch.to_pylist():
                oldfamilies.add(family(row['repo'], row['instance_id'])); oldrows += 1
        oldfiles.append(str(path.relative_to(root)))
    (outdir / 'sample_numeric_rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in samples))
    (outdir / 'quarantined_rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in quarantined))
    groups = {}
    for name in ['all_two_shards', 'scale-swe', 'swe-rebench-v2']:
        subset = [r for r in samples if name == 'all_two_shards' or r['source'] == name]
        groups[name] = {'all_valid': summarize(subset), 'source_success_after_exact_repo_exclusion': summarize(
            [r for r in subset if r['resolved'] == 1 and not r['exact_repo_excluded']]),
            'bugfix_source_success_after_exact_repo_exclusion': summarize(
            [r for r in subset if r['resolved'] == 1 and not r['exact_repo_excluded'] and r['category'] == 'bug-fix'])}
    report = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': {'repo_id': 'nvidia/Open-SWE-Traces', 'revision': REV, 'partition': 'minisweagent/qwen38_flash_next'},
        'files': [{k: r[k] for k in ['file', 'bytes', 'sha256', 'upstream_sha256']} for r in receipts],
        'model_revision': MODEL_REV, 'tokenizer_sha256': sha(tokenizer_path), 'template_sha256': sha(template_path),
        'cpu_workers': 1, 'pyarrow_threads': 1, 'seed': SEED, 'sample_per_shard': args.per_shard,
        'sampling': 'Independent fixed-seed uniform row sample within each of two preselected shards. Combined summary unweighted; not full-partition estimate.',
        'synthetic_check': synthetic, 'metadata': metadata,
        'metadata_total_rows': sum(m['rows'] for m in metadata), 'unique_new_families': len(newfamilies),
        'new_old_family_join': {'old_rows': oldrows, 'old_files_scanned': len(oldfiles),
            'old_unique_families': len(oldfamilies), 'shared_unique_families': len(newfamilies & oldfamilies)},
        'length_sample_valid': len(samples), 'length_sample_quarantined': len(quarantined),
        'quarantine_reasons': dict(Counter(r['reason'] for r in quarantined)),
        'sample_reasoning_nonempty_records': sum(r.get('reasoning_nonempty_messages', 0) > 0 for r in samples),
        'sample_leading_think_records': sum(r.get('leading_think_messages', 0) > 0 for r in samples),
        'sample_multi_call_records': sum(r['multi_call_assistant_turns'] > 0 for r in samples),
        'sample_tool_names': dict(Counter(n for r in samples for n in r['tool_names'])),
        'sample_tool_signature_unique': list({json.dumps(r['tool_signatures'], sort_keys=True) for r in samples}),
        'sample_system_hints': {h: sum(r['system_hints'][h] for r in samples) for h in
            ['/testbed', '/workspace', 'docker', 'bash', 'submit', 'persistent', 'separate shell']},
        'sample_prompt_hints': {h: sum(r['prompt_hints'][h] for r in samples) for h in
            ['/testbed', '/workspace', '/app', 'new subshell', 'patch.txt', 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT']},
        'sample_observation_counts': dict(sum((Counter(r['observations']) for r in samples), Counter())),
        'sample_xml_bridge_probe': dict(sum((Counter(r['xml_bridge_probe']) for r in samples), Counter())),
        'observation_template_sha256': {'native_swebench_config': sha(native_config), 'target_mini_toolcall_config': sha(target_config)},
        'sample_unique_system_prompts': len({r['system_sha256'] for r in samples}),
        'groups': groups, 'seconds': time.monotonic() - start,
        'scope': 'Two files only, full lightweight metadata and at most 128 message rows each. No task/patch/test execution, no formal benchmark task content, no split or training export. Exact repo exclusion only; forks/renames/cross-source semantic task lineage pending. resolved=1 is publisher metadata, not replay verification. Clean full sequence includes all roles and tool observations, no truncation/packing. Assistant body proxy includes empty think wrappers/tool XML/end tokens, excludes role header; not actual ms-swift labels or training processed tokens. P/S depends on final window, repeat histories and loader/mask.'}
    (outdir / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'event': 'complete', 'rows': report['metadata_total_rows'], 'sample_valid': len(samples),
        'sample_quarantined': len(quarantined), 'seconds': report['seconds'], 'summary': str(outdir / 'summary.json')}), flush=True)


if __name__ == '__main__':
    main()
