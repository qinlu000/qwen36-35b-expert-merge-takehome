import json
from pathlib import Path
from types import SimpleNamespace
import yaml
from minisweagent.exceptions import FormatError, Submitted
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.utils.actions_toolcall import parse_toolcall_actions, format_toolcall_observation_messages
ROOT = Path('/data/caoqinlu/projects/apex-takehome')
cfg = yaml.safe_load((ROOT/'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml').read_text())
checks = {}
def call(name='bash', args='{"command":"printf fixture"}'):
    return SimpleNamespace(id='fixture_call_1', function=SimpleNamespace(name=name, arguments=args))
checks['valid_bash_parses_command_and_id'] = parse_toolcall_actions([call()], format_error_template=cfg['model']['format_error_template']) == [{'command':'printf fixture', 'tool_call_id':'fixture_call_1'}]
for key, calls in [('empty_calls', []), ('unknown_tool', [call(name='not_bash')]), ('invalid_json', [call(args='{')]), ('missing_command', [call(args='{}')])]:
    try:
        parse_toolcall_actions(calls, format_error_template=cfg['model']['format_error_template'])
        checks[key+'_rejected'] = False
    except FormatError:
        checks[key+'_rejected'] = True
# Native parser checks name and presence of command, but not command's value type.
checks['nonstring_command_not_rejected_by_native_parser'] = parse_toolcall_actions([call(args='{"command":7}')], format_error_template=cfg['model']['format_error_template'])[0]['command'] == 7
for key, output in [('short', {'output':'fixture\n', 'returncode':0, 'exception_info':''}), ('long', {'output':'x'*10001,'returncode':0,'exception_info':''}), ('timeout', {'output':'partial\n','returncode':-1,'exception_info':'fixture TimeoutExpired'})]:
    msg = format_toolcall_observation_messages(actions=[{'command':'printf fixture','tool_call_id':'fixture_call_1'}], outputs=[output], observation_template=cfg['model']['observation_template'])[0]
    content = json.loads(msg['content'])
    checks[key+'_tool_role_and_call_id_preserved'] = msg['role']=='tool' and msg['tool_call_id']=='fixture_call_1'
    checks[key+'_returncode_preserved'] = content['returncode']==output['returncode']
    if key=='short': checks['short_output_exact'] = content['output']==output['output']
    elif key=='long': checks['long_output_head_tail_5000_elided_1'] = len(content['output_head'])==len(content['output_tail'])==5000 and content['elided_chars']==1
    else: checks['timeout_exception_preserved'] = content['exception_info']==output['exception_info']

env = LocalEnvironment()
# Only pure completion detector is called; execute/_run/subprocess are never invoked.
for key, output, expected in [('marker', {'output':'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n','returncode':0}, True), ('marker_plus_payload', {'output':'\n COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\nfixture payload','returncode':0}, True), ('nonzero_marker', {'output':'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n','returncode':1},False), ('not_first_line', {'output':'fixture\nCOMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n','returncode':0},False)]:
    try:
        env._check_finished(output)
        submitted = False
    except Submitted:
        submitted = True
    checks[key+'_completion_correct'] = submitted==expected
report = {'mini_version':'2.4.6', 'scope':'Synthetic parsing/observation/completion checks; no model/API/container requests, subprocesses, benchmark tasks or trajectory commands executed.', 'checks':checks, 'passed':sum(checks.values()),'total':len(checks)}
(ROOT/'artifacts/data/audits/swe_native_fixture_20261016.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
