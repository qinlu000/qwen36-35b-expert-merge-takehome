"""Observe actual staged cache metadata and supply one cached verifier runtime."""
from datetime import datetime,timezone
import json,shlex,shutil,time
from pathlib import Path
import httpx
from harbor.models.task.config import TaskConfig

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
TOOLS=ROOT/'artifacts/tools/terminal_verifier_offline_20261016'
SOURCE=TOOLS/'python/cpython-3.11.14-linux-x86_64-gnu'
QUERY="""import json,os,pathlib
print(json.dumps({'ready':pathlib.Path('/staging/verifier_assets').exists() and pathlib.Path('/logs/artifacts/final-task-state.tar').exists(),'stage_inode':os.stat('/staging').st_ino,'verifier_inode':os.stat('/logs/verifier').st_ino}))"""


def main():
    receipt_path=RUN/'native8-verifier-cache-hit.json'
    while Path('/proc/2571204').exists():
        staging={p.stat().st_ino:p for p in Path('/tmp').glob('apex_baseline_staging_*') if p.is_dir()}
        trials={p.stat().st_ino:p.parent for p in (OUT/'trials').glob('*/verifier') if p.is_dir()}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                args=p.joinpath('cmdline').read_bytes().decode().split('\0')
                parent=int(p.joinpath('stat').read_text().rsplit(')',1)[1].split()[1])
            except (OSError,ValueError):continue
            if '--namespace-relays' not in args or parent!=2571204:continue
            socket=args[args.index('--control-socket')+1]
            try:
                with httpx.Client(transport=httpx.HTTPTransport(uds=socket),timeout=5,trust_env=False) as client:
                    response=client.post('http://localhost/exec',json={'command':'/opt/harbor-server/bin/python3 -c '+shlex.quote(QUERY),'timeout_sec':3})
                    state=json.loads(response.json()['stdout'])
                if not state['ready']:continue
                host=staging[state['stage_inode']];trial=trials[state['verifier_inode']]
                config=json.loads((trial/'config.json').read_text());task=Path(config['task']['path'])
                task_config=TaskConfig.model_validate_toml((task/'task.toml').read_text())
                name=task_config.task.short_name if task_config.task else task.name
                actual=host/'verifier_assets/uv-cache/snapshot_receipt.json'
                if not receipt_path.exists() and actual.exists():
                    item=json.loads((TOOLS/'task_cache_map.json').read_text()).get(name,{})
                    copied=json.loads(actual.read_text())
                    value={'at_utc':datetime.now(timezone.utc).isoformat(),'trial':str(trial),'environment_name':name,
                        'environment_name_evidence':'Pinned Task.short_name on actual trial metadata; live namespace log inode matched host trial',
                        'selected_task_key':name if item else None,'task_directory_name':task.name,'ready':item.get('ready',False),
                        'cache_path':item.get('uv_cache_dir'),'actual_staged_receipt':str(actual),
                        'actual_staged_group':copied.get('group'),'selected_group':item.get('group'),
                        'actual_group_matches':copied.get('group')==item.get('group'),'model_calls_or_tests_added':0}
                    receipt_path.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value),flush=True)
                assets=host/'verifier_assets/python'
                if task.name=='train-fasttext' and assets.is_dir() and not (assets/SOURCE.name).exists():
                    temp=assets/('.'+SOURCE.name+'.staging')
                    shutil.copytree(SOURCE,temp,symlinks=True,dirs_exist_ok=True);temp.rename(assets/SOURCE.name)
                    with (RUN/'verifier-python311-staged.jsonl').open('a') as log:
                        log.write(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),'trial':str(trial),
                            'source':str(SOURCE),'target':str(assets/SOURCE.name),'phase':'verifier only'})+'\n')
            except (OSError,ValueError,KeyError,httpx.HTTPError):continue
        time.sleep(5 if receipt_path.exists() else 1)


if __name__=='__main__':main()
