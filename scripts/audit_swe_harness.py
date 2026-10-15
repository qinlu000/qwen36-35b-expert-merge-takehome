"""Bounded structural audit; never execute trajectory commands or read patches/tests."""
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
import yaml
from jinja2 import Environment

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
source = json.loads((ROOT / 'data_sources.json').read_text())['open_swe']
mini = ROOT / 'artifacts/envs/mini-swe/lib/python3.12/site-packages/minisweagent'
target = yaml.safe_load((ROOT / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml').read_text())
mod = ast.parse((mini / 'models/utils/actions_toolcall.py').read_text())
bash = next(ast.literal_eval(n.value) for n in mod.body if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == 'BASH_TOOL' for x in n.targets))
template_text = (ROOT / 'analysis/source_snapshots/model_chat_template.jinja').read_text()

def fail(message):
    raise ValueError(message)

template = Environment().from_string(template_text)
template.globals['raise_exception'] = fail
c = Counter()
roles = Counter()
langs = Counter()
labels = Counter()
obskeys = Counter()
sys_hash = Counter()
files = []
raw_errors = Counter()
normalize_errors = Counter()
record_features = []

def render(messages, tools):
    return template.render(messages=messages, tools=tools, add_generation_prompt=False, enable_thinking=False, preserve_thinking=False)

for item in source['files']:
    if not item['path'].endswith('.parquet'):
        continue
    path = ROOT / 'artifacts/data/raw/open_swe' / source['revision'] / item['path']
    pf = pq.ParquetFile(path)
    meta = pq.read_table(path, columns=['language', 'resolved']).to_pylist()
    strata = {}
    for i, r in enumerate(meta):
        strata.setdefault((str(r['resolved']), r['language'] or '<missing>'), i)
    chosen = set()
    # At most four languages per resolution label, then deterministic evenly spaced fillers.
    for label in ['1', '0', '-1']:
        chosen.update([i for (status, lang), i in sorted(strata.items()) if status == label][:4])
    for i in [round(k * (len(meta) - 1) / 15) for k in range(16)]:
        if len(chosen) < 16:
            chosen.add(i)
    selected = {}
    offset = 0
    for batch in pf.iter_batches(batch_size=128, columns=['messages', 'tools', 'language', 'resolved']):
        for j in sorted(i - offset for i in chosen if offset <= i < offset + len(batch)):
            selected[offset + j] = batch.slice(j, 1).to_pylist()[0]
        offset += len(batch)
        if offset > max(chosen):
            break
    fc = Counter()
    for row_idx, row in sorted(selected.items()):
        c['records'] += 1
        langs[row['language'] or '<missing>'] += 1
        labels[str(row['resolved'])] += 1
        ms = row['messages']
        tools = [json.loads(x) for x in row['tools']]
        c['exact_target_tool_definition_records'] += tools == [bash]
        c['system_then_user_records'] += [x['role'] for x in ms[:2]] == ['system', 'user']
        system = ms[0]['content'] or ''
        sys_hash[hashlib.sha256(system.encode()).hexdigest()] += 1
        c['exact_target_system_records'] += system == target['agent']['system_template']
        first_user = next((m['content'] or '' for m in ms if m['role'] == 'user'), '')
        for key, phrase in [('new_subshell_prompt', 'Every action is executed in a new subshell'), ('patch_txt_prompt', 'patch.txt'), ('cat_patch_submission_prompt', 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt'), ('no_modify_tests_prompt', 'DO NOT MODIFY')]:
            c[key + '_records'] += phrase in first_user
        has_marker = False
        marker_index = -1
        norm = []
        orphan = 0
        mismatched = 0
        pending = []
        reason_count = 0
        think_content_count = 0
        multi = False
        for mi, m in enumerate(ms):
            roles[m['role']] += 1
            role = m['role']
            nm = {k: v for k, v in m.items() if v is not None}
            if nm.get('content') is None:
                nm['content'] = ''
            if role == 'assistant':
                if pending:
                    mismatched += 1
                pending = []
                calls = m.get('tool_calls') or []
                multi |= len(calls) > 1
                c['assistant_messages'] += 1
                c['assistant_reasoning_content_nonempty'] += bool(m.get('reasoning_content'))
                reason_count += bool(m.get('reasoning_content'))
                c['assistant_content_think_tags'] += '<think>' in (m.get('content') or '') or '</think>' in (m.get('content') or '')
                think_content_count += '<think>' in (m.get('content') or '') or '</think>' in (m.get('content') or '')
                c['assistant_without_tool_calls'] += not bool(calls)
                c['assistant_null_content'] += m.get('content') is None
                for tc in calls:
                    c['tool_calls'] += 1
                    func = tc['function']
                    args = json.loads(func['arguments'])
                    valid = func['name'] == 'bash' and isinstance(args, dict) and set(args) == {'command'} and isinstance(args['command'], str)
                    c['valid_bash_command_tool_calls'] += valid
                    if 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in args.get('command', ''):
                        has_marker = True
                        marker_index = mi
                        c['marker_commands'] += 1
                        c['exact_marker_commands'] += args['command'].strip() == 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'
                        c['marker_and_cat_patch_commands'] += '&& cat patch.txt' in args['command']
                    pending.append(tc['id'])
                    func['arguments'] = args
                if calls:
                    nm['tool_calls'] = calls
            elif role == 'tool':
                c['tool_messages'] += 1
                c['source_tool_messages_with_call_id'] += bool(m.get('tool_call_id'))
                if pending:
                    nm['tool_call_id'] = pending.pop(0)
                else:
                    orphan += 1
                content = m.get('content') or ''
                try:
                    ob = json.loads(content)
                    if isinstance(ob, dict):
                        c['json_object_observations'] += 1
                        obskeys['|'.join(sorted(ob))] += 1
                        c['json_head_tail_observations'] += 'output_head' in ob and 'output_tail' in ob
                        c['json_exception_observations'] += bool(ob.get('exception_info'))
                        c['json_nonzero_returncode_observations'] += ob.get('returncode') not in [None, 0]
                    else:
                        c['json_nonobject_observations'] += 1
                except (ValueError, TypeError):
                    c['xml_returncode_observations'] += '<returncode>' in content
                    c['xml_head_tail_observations'] += '<output_head>' in content and '<output_tail>' in content
                    c['other_observations'] += '<returncode>' not in content
            elif role == 'user' and mi > 1:
                c['post_initial_user_messages'] += 1
                c['format_error_user_messages'] += 'Tool call error' in (m.get('content') or '') or 'Format error' in (m.get('content') or '')
            norm.append(nm)
        terminal_submission_without_tool = bool(pending) and marker_index == len(ms) - 1
        c['terminal_submission_without_tool_records'] += terminal_submission_without_tool
        c['single_call_nonterminal_pairing_ok_records'] += not multi and orphan == 0 and mismatched == 0 and (not pending or terminal_submission_without_tool)
        c['source_thinking_present_records'] += reason_count > 0 or think_content_count > 0
        mismatched += bool(pending)
        c['orphan_tool_messages'] += orphan
        c['unfinished_tool_call_groups'] += mismatched
        c['all_calls_have_tool_results_records'] += orphan == 0 and mismatched == 0
        c['multi_call_assistant_records'] += multi
        c['submission_marker_present_records'] += has_marker
        c['post_marker_assistant_records'] += marker_index >= 0 and any(m['role'] == 'assistant' for m in ms[marker_index + 1:])
        fc['records'] += 1
        try:
            # raw arguments are reconstructed above only in normalized copy below, so use reread originals.
            raw = [dict(m) for m in ms]
            for m in raw:
                if m.get('tool_calls'):
                    m['tool_calls'] = [{**tc, 'function': {**tc['function'], 'arguments': json.dumps(tc['function']['arguments'])}} for tc in m['tool_calls']]
            render(raw, tools)
            c['raw_template_render_ok'] += 1
        except Exception as e:
            raw_errors[type(e).__name__] += 1
        try:
            rendered = render(norm, tools)
            c['normalized_template_render_ok'] += 1
            c['normalized_tool_call_serialized_records'] += '<function=bash>' in rendered
            c['nonthinking_flags_still_render_source_reasoning_records'] += reason_count > 0 and any((m.get('reasoning_content') or '').strip() in rendered for m in ms if m.get('reasoning_content'))
        except Exception as e:
            normalize_errors[type(e).__name__] += 1
        record_features.append({'file': item['path'], 'row': row_idx, 'language': row['language'], 'resolved': row['resolved'], 'message_count': len(ms), 'submission_marker_present': has_marker, 'multi_call': multi, 'single_call_nonterminal_pairing_ok': not multi and orphan == 0 and (mismatched == 0 or (terminal_submission_without_tool and mismatched == 1))})
    files.append({'file': item['path'], 'population_rows': len(meta), 'sample_rows': sorted(selected), 'sample_count': len(selected)})

report = {'source_revision': source['revision'], 'scope': 'Structural inspection only; no source commands, task code, model/API requests or graders executed. metadata/reference_patch/model_patch and formal benchmark instructions/tests never loaded. Sample is deterministic stratified first occurrences plus evenly spaced fillers, not a random quality estimate.', 'selection': 'up to 16 rows per shard: first occurrence for up to four alphabetically sorted languages in each resolved label, then evenly spaced fillers', 'counts': dict(c), 'roles': dict(roles), 'languages': dict(langs), 'resolved': dict(labels), 'observation_key_sets': dict(obskeys), 'system_prompt_sha256_counts': dict(sys_hash), 'raw_render_errors': dict(raw_errors), 'normalized_render_errors': dict(normalize_errors), 'files': files, 'records': record_features}
out = ROOT / 'artifacts/data/audits/swe_harness_compatibility_20261016.json'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ['records', 'files']}, indent=2))
