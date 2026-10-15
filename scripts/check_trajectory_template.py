#!/usr/bin/env python3
"""CPU-only Qwen template checks using synthetic conversations, without a model."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path

from transformers import AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_metadata, local_files_only=True, trust_remote_code=False
    )
    tools = [{'type': 'function', 'function': {
        'name': 'bash', 'description': 'Synthetic shell tool; never executed.',
        'parameters': {'type': 'object', 'properties': {
            'command': {'type': 'string'}}, 'required': ['command']}}}]
    mini = [
        {'role': 'system', 'content': 'Synthetic tool protocol fixture.'},
        {'role': 'user', 'content': 'Inspect the synthetic fixture.'},
        {'role': 'assistant', 'content': '', 'reasoning_content': 'REASONING_ONE',
         'tool_calls': [{'id': 'fixture-call', 'type': 'function', 'function': {
             'name': 'bash', 'arguments': {'command': 'echo fixture'}}}]},
        {'role': 'tool', 'tool_call_id': 'fixture-call',
         'content': json.dumps({'returncode': 0, 'output': 'fixture\n'})},
        {'role': 'assistant', 'content': 'SYNTHETIC_FINAL',
         'reasoning_content': 'REASONING_TWO'},
    ]
    action = {'analysis': 'JSON_ANALYSIS_FIELD', 'plan': 'JSON_PLAN_FIELD',
              'commands': [{'keystrokes': 'echo fixture\n', 'duration': 0.1}],
              'task_complete': False}
    terminal = [
        {'role': 'system', 'content': 'Synthetic JSON terminal protocol.'},
        {'role': 'user', 'content': 'Inspect the synthetic fixture.'},
        {'role': 'assistant', 'content': '<think>REASONING_ONE</think>\n' + json.dumps(action)},
        {'role': 'user', 'content': 'Synthetic terminal observation: fixture'},
        {'role': 'assistant', 'content': '<think>REASONING_TWO</think>\n' + json.dumps({
            **action, 'commands': [], 'task_complete': True})},
    ]
    qa = [{'role': 'user', 'content': 'What is 2 + 3?'},
          {'role': 'assistant', 'content': '<think>REASONING_TWO</think>\n5'}]
    results = []
    for name, messages, tool_defs in [('mini', mini, tools), ('terminal', terminal, None), ('qa', qa, None)]:
        for clean in (False, True):
            fixture = copy.deepcopy(messages)
            if clean:
                # Fixtures have known, balanced tags. This is not a production converter.
                for message in fixture:
                    if message['role'] == 'assistant':
                        message.pop('reasoning_content', None)
                        message['content'] = message['content'].split('</think>')[-1].lstrip('\n')
            rendered = tokenizer.apply_chat_template(
                fixture, tools=tool_defs, tokenize=False, add_generation_prompt=False,
                enable_thinking=False, preserve_thinking=False
            )
            results.append({
                'fixture': name, 'explicitly_removed_synthetic_reasoning': clean,
                'reasoning_one_retained': 'REASONING_ONE' in rendered,
                'reasoning_two_retained': 'REASONING_TWO' in rendered,
                'json_analysis_count': rendered.count('JSON_ANALYSIS_FIELD'),
                'json_plan_count': rendered.count('JSON_PLAN_FIELD'),
                'xml_tool_call_marker_count_including_instructions': rendered.count('<tool_call>'),
                'template_token_count': len(tokenizer.encode(rendered, add_special_tokens=False)),
            })
    by_key = {(r['fixture'], r['explicitly_removed_synthetic_reasoning']): r for r in results}
    assert by_key['mini', False]['reasoning_one_retained']
    assert by_key['mini', False]['reasoning_two_retained']
    assert not by_key['terminal', False]['reasoning_one_retained']
    assert by_key['terminal', False]['reasoning_two_retained']
    assert by_key['qa', False]['reasoning_two_retained']
    for name in ('mini', 'terminal', 'qa'):
        assert not by_key[name, True]['reasoning_one_retained']
        assert not by_key[name, True]['reasoning_two_retained']
    assert by_key['terminal', True]['json_analysis_count'] == 2
    assert by_key['terminal', True]['json_plan_count'] == 2
    prefix = tokenizer.apply_chat_template(
        qa[:1], tokenize=False, add_generation_prompt=True,
        enable_thinking=False, preserve_thinking=False
    )
    assert prefix.endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n')
    report = {
        'scope': 'Synthetic CPU tokenizer/template fixtures only; no source trajectory, model, API or shell execution.',
        'transformers': importlib.metadata.version('transformers'),
        'tokenizers': importlib.metadata.version('tokenizers'),
        'tokenizer_class': type(tokenizer).__name__,
        'chat_template_sha256': hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        'enable_thinking': False, 'preserve_thinking': False,
        'all_assertions_passed': True, 'generation_prefix_is_empty_think': True,
        'fixtures': results,
        'interpretation': 'False template flags do not remove existing latest-user assistant reasoning. Explicit normalization is needed for a non-thinking SFT profile; retain Terminus JSON analysis/plan fields.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
