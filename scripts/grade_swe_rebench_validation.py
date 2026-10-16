"""Score a held-out patch with the pinned SWE-rebench parser and test command."""
import json
from pathlib import Path
import runpy
import subprocess


def main():
    tests = Path('/tests')
    output = Path('/logs/verifier')
    output.mkdir(parents=True, exist_ok=True)
    official = runpy.run_path(str(tests / 'source/scripts/eval.py'))
    spec = json.loads((tests / 'spec.json').read_text())
    commands = official['normalize_command_list'](
        spec['install_config']['test_cmd'], 'install_config.test_cmd', spec['instance_id'])
    script = '\n'.join(['set -e',
        'git apply -v --3way --recount --ignore-space-change --whitespace=nowarn /tests/test_patch.diff',
        *commands])
    result = subprocess.run(['/bin/bash', '-c', script], cwd=spec['workdir'],
                            capture_output=True, text=True)
    raw = (result.stdout or '') + (result.stderr or '')
    (output / 'test_output.txt').write_text(raw)
    parser = official['get_parser'](spec['install_config']['log_parser'])
    normalize = official['_normalize_test_name']
    parsed = {normalize(k): v for k, v in parser(raw).items()}
    if not raw.strip() or not parsed:
        (output / 'grading_invalid.json').write_text(json.dumps({
            'reason': 'empty test log or no parsed tests; requires environment/model-failure audit',
            'test_exit_code': result.returncode, 'log_characters': len(raw)}, indent=2) + '\n')
        raise RuntimeError('No parsed test results; retained for audit without an invented reward')
    passed = sorted(k for k, v in parsed.items() if v == 'PASSED')
    expected = sorted(normalize(k) for k in spec['PASS_TO_PASS'] + spec['FAIL_TO_PASS'])
    replay = json.loads(Path('/logs/agent/replay.json').read_text())
    reward = int(passed == expected and replay['apply_rc'] == 0)
    (output / 'rebench_score.json').write_text(json.dumps({
        'instance_id': spec['instance_id'], 'reward': reward,
        'exit_code': result.returncode, 'passed_match': passed == expected,
        'passed_actual': passed, 'passed_expected': expected,
        'failed_actual': sorted(k for k, v in parsed.items() if v == 'FAILED'),
        'replay_apply_rc': replay['apply_rc'],
        'official_revision': 'c71902a8cf8d2b725f63d51f199f4d3e56f68d2d',
        'runtime_adapter': 'Apptainer fresh sandbox; original tests/parser/commands'}, indent=2) + '\n')
    (output / 'reward.txt').write_text(str(reward) + '\n')


if __name__ == '__main__':
    main()
