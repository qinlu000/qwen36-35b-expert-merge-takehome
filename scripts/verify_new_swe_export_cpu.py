"""Verify cleaned SWE candidates against the installed native parser, without shell execution."""
import json
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace as N

import yaml
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions, format_toolcall_observation_messages
from audit_new_swe_cpu import CapturedLongOutput, sha

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/data/candidates/new_swe_20261016/night_v2'
config = root / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml'
template = yaml.safe_load(config.read_text())['model']['observation_template']
counts, problems = Counter(), []
for split in ['train', 'val']:
    with (out / f'{split}.cleaned.candidate.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            counts['rows'] += 1
            pending = []
            for message in row['messages']:
                if message['role'] == 'assistant':
                    calls = message.get('tool_calls', [])
                    actions = parse_toolcall_actions([N(id=x['id'], function=N(name=x['function']['name'], arguments=json.dumps(x['function']['arguments']))) for x in calls], format_error_template='{{error}}')
                    assert [a['command'] for a in actions] == [x['function']['arguments']['command'] for x in calls]
                    assert [a['tool_call_id'] for a in actions] == [x['id'] for x in calls]
                    pending = actions[:]
                    counts['native_parsed_assistant_turns'] += 1
                    counts['native_parsed_calls'] += len(actions)
                elif message['role'] == 'tool':
                    action = pending.pop(0)
                    assert message['tool_call_id'] == action['tool_call_id']
                    observed = json.loads(message['content'])
                    assert isinstance(observed['returncode'], int)
                    if 'output' in observed:
                        assert isinstance(observed['output'], str)
                        raw_output = observed['output']
                    else:
                        assert isinstance(observed['elided_chars'], int) and observed['elided_chars'] >= 0
                        assert len(observed['output_head']) == len(observed['output_tail']) == 5000
                        raw_output = CapturedLongOutput(observed['output_head'], observed['output_tail'], observed['elided_chars'])
                    rendered = format_toolcall_observation_messages(actions=[action], outputs=[{'returncode': observed['returncode'], 'output': raw_output, 'exception_info': observed.get('exception_info')}], observation_template=template)[0]
                    decoded = json.loads(rendered['content'])
                    assert rendered['tool_call_id'] == message['tool_call_id']
                    keys = {'returncode', 'output', 'output_head', 'output_tail', 'elided_chars', 'exception_info'}
                    if {k:v for k,v in decoded.items() if k in keys} != {k:v for k,v in observed.items() if k in keys}:
                        problems.append({'family_key': row['metadata']['family_key'], 'split': split, 'reason': 'target_native_observation_fields_differ'})
                    else:
                        counts['native_observation_visible_fields_match'] += 1
                    counts['tool_messages'] += 1
            final = row['messages'][-1]['tool_calls'][0]['function']['arguments']['command'].strip()
            exact = bool(re.fullmatch(r'echo\s+[\"\']?COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT[\"\']?', final))
            counts['final_standalone_echo' if exact else 'final_not_standalone_echo'] += 1
            if not exact:
                problems.append({'family_key': row['metadata']['family_key'], 'split': split, 'reason': 'final_command_not_standalone_echo'})
protocol_problems = [x for x in problems if x['reason'] == 'final_command_not_standalone_echo']
native_problems = [x for x in problems if x['reason'] != 'final_command_not_standalone_echo']
report = {'counts': dict(counts), 'problems': problems, 'target_config_sha256': sha(config),
    'scope': 'Installed mini-swe-agent 2.4.6 native parser and observation formatter, all selected traces; no shell commands executed. Ordering/IDs validated relative to saved source order only. No source collector ordering proof, runtime replay, grader, API, GPU or training.',
    'native_parser_and_observation_passed': not native_problems,
    'target_submit_prompt_conformance_passed': not protocol_problems,
    'passed_all_native_and_prompt_checks': not problems}
(out / 'native_verification.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'counts': dict(counts), 'problems': len(problems), 'passed': not problems}))
