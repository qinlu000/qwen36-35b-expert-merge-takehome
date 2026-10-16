"""Adapt only the fixed system/submission shell; preserve all task content and observations."""
import copy
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace as N

import yaml
from minisweagent.environments.local import LocalEnvironment
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.exceptions import Submitted
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions
from audit_new_swe_cpu import sha

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/data/candidates/new_swe_20261016/night_v2'
target_config = root / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml'
target_system = yaml.safe_load(target_config.read_text())['agent']['system_template']
source_system = 'You are a helpful assistant that can interact with a computer shell to solve programming tasks.'
old_submit = ('Step 3: Submit (EXACT command required)\nYou MUST use this EXACT command to submit:\n\n'
    '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt\n```\n\n'
    'If the command fails (nonzero exit status), it will not submit.\n')
new_submit = ('Step 3: Submit (EXACT command required)\nSubmit your changes and finish your work by issuing this command:\n\n'
    '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```\n\n'
    'Do not combine it with any other command. After this command, you cannot continue working on this task.\n')
allowed_final_commands = {
    'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt',
    'cd /testbed && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt',
    'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat /testbed/patch.txt',
}
final_command = 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


logs, counts, held = [], Counter(), []
for split in ['train', 'val']:
    input_path = out / f'{split}.cleaned.candidate.jsonl'
    output_path = out / f'{split}.target_contract.candidate.jsonl'
    with input_path.open() as source, output_path.open('w') as destination:
        for line in source:
            row = json.loads(line)
            adapted = copy.deepcopy(row)
            messages = adapted['messages']
            systems = [m for m in messages if m['role'] == 'system']
            user_positions = [i for i,m in enumerate(messages) if m['role'] == 'user' and old_submit in m['content']]
            cmd = messages[-1]['tool_calls'][0]['function']['arguments']['command']
            if len(systems) != 1 or systems[0]['content'] != source_system or len(user_positions) != 1 or cmd not in allowed_final_commands:
                held.append({'family_key': row['metadata']['family_key'], 'split': split, 'reason': 'not_exact_known_wrapper_or_final_command'})
                continue
            u = user_positions[0]
            assert messages[u]['content'].count(old_submit) == 1
            systems[0]['content'] = target_system
            messages[u]['content'] = messages[u]['content'].replace(old_submit, new_submit)
            messages[-1]['tool_calls'][0]['function']['arguments']['command'] = final_command
            action = parse_toolcall_actions([N(id=messages[-1]['tool_calls'][0]['id'], function=N(name='bash', arguments=json.dumps({'command': final_command})))], format_error_template='{{error}}')
            assert action[0]['command'] == final_command
            # Reverse only the authorized fixed-shell edits; equality proves every other field survives.
            reversed_messages = copy.deepcopy(messages)
            next(m for m in reversed_messages if m['role'] == 'system')['content'] = source_system
            reversed_messages[u]['content'] = reversed_messages[u]['content'].replace(new_submit, old_submit)
            reversed_messages[-1]['tool_calls'][0]['function']['arguments']['command'] = cmd
            assert reversed_messages == row['messages']
            assert adapted['tools'] == row['tools']
            log = {'family_key': row['metadata']['family_key'], 'split': split,
                'raw_parquet_file': row['metadata']['file'], 'raw_parquet_row': row['metadata']['row'],
                'source_export_line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                'source_messages_sha256': canonical_hash(row['messages']),
                'adapted_messages_sha256': canonical_hash(messages),
                'source_final_command': cmd, 'target_final_command': final_command,
                'source_system_sha256': hashlib.sha256(source_system.encode()).hexdigest(),
                'target_system_sha256': hashlib.sha256(target_system.encode()).hexdigest(),
                'submission_user_message_index': u,
                'source_submission_guidance_sha256': hashlib.sha256(old_submit.encode()).hexdigest(),
                'target_submission_guidance_sha256': hashlib.sha256(new_submit.encode()).hexdigest(),
                'all_tool_observations_unchanged': True, 'all_pre_final_commands_unchanged': True,
                'task_content_outside_fixed_submit_guidance_unchanged': True,
                'cwd_and_environment_claims_unchanged': True}
            adapted['metadata']['contract_adaptation'] = log
            adapted['metadata']['pre_adaptation_clean_total_tokens'] = adapted['metadata'].pop('clean_total_tokens')
            adapted['metadata']['adapted_token_lengths'] = 'see adapted_token_lengths.jsonl; no truncation or windows'
            adapted['metadata']['export_status'] = 'target_contract_adapted_candidate_not_training_released'
            adapted['metadata']['training_released'] = False
            destination.write(json.dumps(adapted, ensure_ascii=False) + '\n')
            logs.append(log)
            counts[split] += 1
            counts['source_final_command:' + cmd] += 1

# Actual harmless shell execution is restricted to a synthetic temporary task, never source commands.
with tempfile.TemporaryDirectory(prefix='apex-mini-submit-') as d:
    work = Path(d)
    (work / 'tracked.txt').write_text('synthetic unchanged state\n')
    before = sha(work / 'tracked.txt')
    env = LocalEnvironment(cwd=d)
    try:
        env.execute({'command': final_command})
    except Submitted as e:
        assert e.messages[0]['extra']['exit_status'] == 'Submitted'
        assert e.messages[0]['extra']['submission'] == ''
    else:
        raise AssertionError('native_local_did_not_terminate')
    assert sha(work / 'tracked.txt') == before
    assert list(work.iterdir()) == [work / 'tracked.txt']

for output, should_submit in [
    ({'output': 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n', 'returncode': 0}, True),
    ({'output': 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n', 'returncode': 1}, False),
    ({'output': 'OTHER\nCOMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n', 'returncode': 0}, False),
]:
    try:
        DockerEnvironment._check_finished(None, output)
    except Submitted:
        assert should_submit
    else:
        assert not should_submit

(out / 'contract_adaptation_ledger.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in logs))
(out / 'contract_adaptation_held.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in held))
report = {'counts': dict(counts), 'adapted': len(logs), 'held': len(held), 'target_config_sha256': sha(target_config),
    'changes': ['fixed generic system replaced with exact target system', 'exact Step 3 submission guidance replaced with standalone echo instruction', 'only known final echo+cat variants replaced with standalone echo'],
    'preserved': ['all task content outside fixed Step 3', 'all prior repository commands', 'all observations byte-for-byte', 'tool schema and IDs', 'source /testbed and other environment statements', 'source patch-file creation/inspection guidance and demonstrated actions'],
    'fixture': {'native_final_call_parser': True, 'native_local_actual_echo_raises_Submitted': True,
        'synthetic_filesystem_unchanged': True, 'native_docker_termination_check': True,
        'nonzero_exit_not_submitted': True, 'marker_not_first_line_not_submitted': True,
        'source_trajectory_commands_executed': False, 'docker_container_started': False},
    'output_sha256': {p.name: sha(p) for p in [out / 'train.target_contract.candidate.jsonl', out / 'val.target_contract.candidate.jsonl', out / 'contract_adaptation_ledger.jsonl']},
    'training_released': False,
    'remaining': ['source full prompt differs from target instance wrapper', 'source patch-file preparation remains and may add an unneeded patch.txt artifact under target capture', '/testbed mapping, dependency image and independent grader not runtime-verified', 'source multi-call ordering not independently proven', 'long histories need explicit window policy; one val teacher turn exceeds 8K output'],
    'scope': 'Mechanical protocol-shell adaptation with reversible equality checks. No fabricated observations, deletion of prior commands, invented cwd/dependencies, model inference, formal evaluation, GPU or training. Actual shell fixture executes only the constant echo in a synthetic temporary directory.'}
(out / 'contract_adaptation_summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2))
