"""Compare one preserved real SWE row with native Swift and the served HF template; CPU only."""
import argparse
import ast
import copy
import difflib
import faulthandler
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  USE_HF='1', TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1')
REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def difference(left, right):
    index = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), min(len(left), len(right)))
    return {'equal': left == right, 'first_difference': None if left == right else index,
            'left_length': len(left), 'right_length': len(right)}


def audit_saved(output):
    """Align the already saved native IDs; no Swift/torch import or re-encoding."""
    report = json.loads((output / 'report.json').read_text())
    native = json.loads((output / 'swift_ids.json').read_text())
    hf = json.loads((output / 'hf_ids.json').read_text())
    labels = json.loads((output / 'labels.json').read_text())
    expected = [-100] * len(hf)
    for row in report['rounds']:
        start, end = row['target_token_start'], row['target_token_end_exclusive']
        expected[start:end] = hf[start:end]
    opcodes = difflib.SequenceMatcher(None, native, hf, autojunk=False).get_opcodes()
    aligned = [None] * len(native)
    hf_to_native = {}
    edits = []
    for tag, i, j, k, l in opcodes:
        if tag == 'equal':
            aligned[i:j] = expected[k:l]
            hf_to_native.update((k + n, i + n) for n in range(j - i))
        else:
            edits.append({'operation': tag, 'swift_span': [i, j], 'hf_span': [k, l],
                          'swift_ids': native[i:j], 'hf_ids': hf[k:l],
                          'hf_tokens_masked': expected[k:l] == [-100] * (l - k)})
    rounds = []
    for row in report['rounds']:
        start, end = row['target_token_start'], row['target_token_end_exclusive']
        mapped = [hf_to_native[z] for z in range(start, end) if z in hf_to_native]
        complete = len(mapped) == end - start
        rounds.append({'message_index': row['message_index'],
            'hf_generation_prefix_tokens': start, 'native_training_prefix_tokens': min(mapped),
            'hf_prefix_extra_empty_think_blocks': (start - min(mapped)) // 4,
            'target_tokens': end - start, 'all_target_tokens_mapped': complete,
            'target_labels_match': complete and all(labels[z] == native[z] for z in mapped),
            'native_target_span': [min(mapped), max(mapped) + 1]})
    result = {'native_report_sha256': sha((output / 'report.json').read_bytes()),
        'audit_script_sha256': sha(Path(__file__).read_bytes()),
        'method': 'Exact equal-token runs; compare HF assistant-body+EOS mask in native coordinates. Raw round mask checks use different coordinates and are not verdicts.',
        'edits': edits, 'only_seven_omitted_empty_think_blocks': len(edits) == 7 and all(
            e['operation'] == 'insert' and not e['swift_ids'] and
            e['hf_ids'] == [248068, 271, 248069, 271] for e in edits),
        'every_native_token_mapped': all(x is not None for x in aligned),
        'aligned_full_label_mask_equal': aligned == labels,
        'removed_hf_tokens_all_masked': all(e['hf_tokens_masked'] for e in edits),
        'expected_supervised_tokens': sum(x not in (-100, None) for x in aligned),
        'actual_supervised_tokens': sum(x != -100 for x in labels), 'rounds': rounds}
    (output / 'alignment.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--line', type=int, default=681)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--audit-saved', type=Path)
    parser.add_argument('--swift-preserve-thinking', action='store_true',
                        help='Counterfactual Swift flag; HF reference remains preserve_thinking=False.')
    args = parser.parse_args()
    if args.audit_saved:
        audit_saved(args.audit_saved)
        return
    assert args.project and args.output
    root = args.project
    started = time.monotonic()
    faulthandler.enable()
    faulthandler.dump_traceback_later(30, repeat=True)
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    data = root / 'artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k'
    with (data / 'train.messages.jsonl').open('rb') as stream:
        raw = next(line for i, line in enumerate(stream, 1) if i == args.line)
    with (data / 'train.manifest.jsonl').open() as stream:
        provenance = next(json.loads(line) for i, line in enumerate(stream, 1) if i == args.line)
    row = json.loads(raw)
    assert provenance['full_sequence_tokens'] <= 6000 and provenance['multi_call_assistant_turns'] > 0
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'source_sample.json').write_bytes(raw)
    print('STAGE source_sample_saved', time.monotonic() - started, flush=True)
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from swift import get_processor, get_template
    print('STAGE torch_swift_imported', time.monotonic() - started, flush=True)
    processor = get_processor(str(root / 'artifacts/models/Qwen3.6-35B-A3B' / REV),
                              model_type='qwen3_5_moe', use_hf=True, download_model=False)
    print('STAGE native_processor_ready', time.monotonic() - started, flush=True)
    tokenizer = processor.tokenizer
    template = get_template(processor, template_type='qwen3_5', max_length=65536,
        enable_thinking=False, preserve_thinking=args.swift_preserve_thinking, add_non_thinking_prefix=True,
        padding_free=False, loss_scale='default+ignore_empty_think', truncation_strategy='delete')
    template.set_mode('train')
    encoded = template.encode(copy.deepcopy(row))
    print('STAGE real_row_encoded', time.monotonic() - started, flush=True)
    swift_ids, labels = encoded['input_ids'], encoded['labels']
    assert len(swift_ids) == len(labels)
    # Execute only vLLM's pure wire-tool-argument normalization function, without importing its engine.
    source = root / 'artifacts/envs/base-inference/lib/python3.12/site-packages/vllm/entrypoints/chat_utils.py'
    source_text = source.read_text()
    tree = ast.parse(source_text)
    candidates = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and 'json.loads(content)' in ast.get_source_segment(source_text, node)
                  and 'item["function"]["arguments"]' in ast.get_source_segment(source_text, node)]
    assert len(candidates) == 1
    function = copy.deepcopy(candidates[0])
    function.returns = None
    for arg in function.args.args + function.args.kwonlyargs:
        arg.annotation = None
    normalizer = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 str(source), 'exec'), {'json': json}, normalizer)
    wire = copy.deepcopy(row['messages'])
    for message in wire:
        for call in message.get('tool_calls', []):
            call['function']['arguments'] = json.dumps(call['function']['arguments'], ensure_ascii=False)
    normalizer[function.name](wire)
    assert wire == row['messages']
    def render(messages, generation=False):
        return tokenizer.apply_chat_template(messages, tools=row['tools'], tokenize=False,
            add_generation_prompt=generation, enable_thinking=False, preserve_thinking=False)
    def tokenize(text):
        return tokenizer.encode(text, add_special_tokens=False)
    hf_text = render(wire)
    hf_ids = tokenize(hf_text)
    swift_text = tokenizer.decode(swift_ids, skip_special_tokens=False)
    (args.output / 'swift.txt').write_text(swift_text)
    (args.output / 'hf.txt').write_text(hf_text)
    (args.output / 'swift_ids.json').write_text(json.dumps(swift_ids))
    (args.output / 'hf_ids.json').write_text(json.dumps(hf_ids))
    (args.output / 'labels.json').write_text(json.dumps(labels))
    expected_labels = [-100] * len(hf_ids)
    rounds, boundaries = [], []
    previous_end = 0
    tool_query_token = None
    for index, message in enumerate(wire):
        if message['role'] != 'assistant':
            continue
        prompt_text = render(wire[:index], True)
        through_text = render(wire[:index + 1])
        prompt_ids, through_ids = tokenize(prompt_text), tokenize(through_text)
        prefix_ok = hf_text.startswith(prompt_text) and hf_ids[:len(prompt_ids)] == prompt_ids
        end_ok = hf_text.startswith(through_text) and hf_ids[:len(through_ids)] == through_ids
        start, end = len(prompt_ids), len(through_ids)
        boundaries.append(prefix_ok and end_ok)
        if prefix_ok and end_ok:
            expected_labels[start:end] = hf_ids[start:end]
            if index > 2 and start > previous_end:
                tool_query_token = previous_end
        calls = message.get('tool_calls', [])
        rounds.append({'message_index': index, 'history_message_count': index,
            'history_tool_observations': sum(m['role'] == 'tool' for m in wire[:index]),
            'tool_calls_this_round': len(calls), 'visible_content_empty': not bool(message.get('content')),
            'prefix_token_and_text_match': prefix_ok, 'through_assistant_match': end_ok,
            'target_token_start': start, 'target_token_end_exclusive': end,
            'target_sha256': sha(tokenizer.decode(hf_ids[start:end]).encode()),
            'observed_labels_match_this_target': labels[start:end] == hf_ids[start:end] if prefix_ok and end_ok else None,
            'preceding_query_and_empty_think_masked': all(x == -100 for x in labels[previous_end:start]) if prefix_ok and end_ok else None})
        previous_end = end
    label_check = difference(labels, expected_labels) if all(boundaries) and swift_ids == hf_ids else None
    stripped = copy.deepcopy(wire)
    del stripped[next(i for i, message in enumerate(stripped) if message['role'] == 'tool')]
    missing_history_detected = tokenize(render(stripped)) != hf_ids
    shifted = [-100] + expected_labels[:-1]
    controls = {'removed_real_tool_observation_detected': missing_history_detected,
                'one_token_shifted_label_targets_detected': shifted != expected_labels}
    if tool_query_token is not None:
        wrong = expected_labels.copy()
        wrong[tool_query_token] = hf_ids[tool_query_token]
        controls['tool_observation_supervision_leak_detected'] = wrong != expected_labels
    report = {'scope': 'One real preserved row; tokenizer/template/labels only; no weights, forward, model/API, training or task execution.',
        'script_sha256': sha(Path(__file__).read_bytes()), 'source_jsonl': str(data / 'train.messages.jsonl'),
        'source_line_1based': args.line, 'source_line_sha256': sha(raw), 'source_line_bytes': len(raw),
        'provenance': {k: provenance[k] for k in ('family_key', 'instance_id', 'trajectory_id', 'file', 'row', 'teacher',
                                                   'full_sequence_tokens', 'message_count', 'multi_call_assistant_turns')},
        'cpu_affinity': sorted(os.sched_getaffinity(0)), 'cuda_initialized': torch.cuda.is_initialized(),
        'model_weights_loaded': False, 'packages': {name: metadata.version(name) for name in
            ('torch', 'transformers', 'ms-swift', 'tokenizers')},
        'tokenizer_class': type(tokenizer).__name__, 'chat_template_sha256': sha(tokenizer.chat_template.encode()),
        'template_flags': {'enable_thinking': False, 'preserve_thinking': args.swift_preserve_thinking,
                           'add_non_thinking_prefix': True},
        'hf_reference_flags': {'enable_thinking': False, 'preserve_thinking': False},
        'swift_loss_scale': 'default+ignore_empty_think',
        'vllm_wire_normalizer': {'source': str(source), 'name': function.name,
            'line_start': function.lineno, 'line_end': function.end_lineno, 'source_sha256': sha(source.read_bytes()),
            'wire_json_arguments_recovered_identically': wire == row['messages']},
        'hf_renderer': 'Original model tokenizer.apply_chat_template; same HF rendering backend used by vLLM. No live endpoint was called.',
        'full_text': {**difference(swift_text, hf_text), 'swift_sha256': sha(swift_text.encode()),
                      'hf_sha256': sha(hf_text.encode())},
        'full_tokens': difference(swift_ids, hf_ids), 'label_target_identity': all(y == -100 or x == y for x, y in zip(swift_ids, labels)),
        'expected_all_assistant_target_mask': label_check, 'rounds': rounds, 'negative_controls': controls,
        'history_tool_observations': sum(m['role'] == 'tool' for m in wire),
        'assistant_tool_calls': sum(len(m.get('tool_calls', [])) for m in wire),
        'supervised_tokens': sum(x != -100 for x in labels),
        'empty_think_blocks_in_hf_text': hf_text.count('<think>\n\n</think>'),
        'im_end_tokens_in_hf_text': hf_text.count('<|im_end|>'),
        'elapsed_seconds': time.monotonic() - started}
    report['passed'] = (report['full_text']['equal'] and report['full_tokens']['equal']
        and label_check is not None and label_check['equal'] and all(boundaries)
        and report['label_target_identity'] and all(controls.values()) and not report['cuda_initialized'])
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    faulthandler.cancel_dump_traceback_later()
    print(json.dumps({k: report[k] for k in ['passed', 'source_line_1based', 'source_line_sha256',
        'full_text', 'full_tokens', 'expected_all_assistant_target_mask', 'negative_controls',
        'supervised_tokens', 'elapsed_seconds', 'cuda_initialized']}, indent=2))


if __name__ == '__main__':
    main()
