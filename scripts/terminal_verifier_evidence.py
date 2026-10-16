"""Do not accept a zero from a pytest wrapper that never executed any tests."""
import json,re
from pathlib import Path


def verifier_infra_reason(result):
    config=result.get('config') or {}
    directory=Path(config.get('trials_dir','.'))/config.get('trial_name','')/'verifier'
    log=directory/'test-stdout.txt'
    text=log.read_text(errors='replace') if log.exists() else ''
    for token in ('curl: command not found','uvx: command not found','uv: command not found'):
        if token in text:return token
    reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    task=result.get('task_id') or {}
    script=Path(task.get('path','.'))/'tests/test.sh'
    if reward!=0 or not script.exists() or 'pytest' not in script.read_text(errors='replace'):return None
    for path in directory.glob('*.json'):
        try:data=json.loads(path.read_text())
        except (ValueError,OSError):continue
        summary=(data.get('results') or {}).get('summary') or {}
        if summary.get('tests',0)>0 and summary.get('passed',0)+summary.get('failed',0)>0:return None
    if re.search(r'\b[1-9]\d* (?:passed|failed)\b',text):return None
    return 'pytest wrapper returned zero reward without evidence that tests executed'
