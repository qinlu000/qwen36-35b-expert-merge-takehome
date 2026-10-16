"""Record one real verifier's selected task cache; no fixture or cache mutation."""
from datetime import datetime,timezone
import json,time
from pathlib import Path
from harbor.models.task.config import TaskConfig

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
TOOLS=ROOT/'artifacts/tools/terminal_verifier_offline_20261016'


def main():
    while not (RUN/'followon/full445.COMPLETE.json').exists():
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:args=p.joinpath('cmdline').read_bytes().decode().split('\0')
            except (OSError,ValueError):continue
            staging=next((a.split(':')[0] for a in args if a.endswith(':/staging')),None)
            logs=next((a.split(':')[0] for a in args if a.endswith(':/logs/verifier') and str(OUT/'trials') in a),None)
            if not staging or not logs:continue
            trial=Path(logs).parent
            cache=Path(staging)/'verifier_assets/uv-cache'
            receipt=cache/'snapshot_receipt.json'
            if not receipt.exists() or not (trial/'config.json').exists():continue
            config=json.loads((trial/'config.json').read_text())
            task=Path(config['task']['path'])
            task_config=TaskConfig.model_validate_toml((task/'task.toml').read_text())
            name=task_config.task.short_name if task_config.task else task.name
            mapping=json.loads((TOOLS/'task_cache_map.json').read_text())
            item=mapping.get(name,{})
            copied=json.loads(receipt.read_text())
            value={'at_utc':datetime.now(timezone.utc).isoformat(),'trial':str(trial),
                'environment_name':name,'environment_name_evidence':'Pinned Task.short_name definition applied to this actual Trial task.toml',
                'task_directory_name':task.name,'selected_task_key':name if name in mapping else None,
                'ready':item.get('ready',False),'cache_path':item.get('uv_cache_dir'),
                'actual_staged_receipt':str(receipt),'actual_staged_group':copied.get('group'),
                'selected_group':item.get('group'),'actual_group_matches':copied.get('group')==item.get('group'),
                'model_calls_or_tests_added':0}
            (RUN/'native8-verifier-cache-hit.json').write_text(json.dumps(value,indent=2)+'\n')
            print(json.dumps(value));return
        time.sleep(5)


if __name__=='__main__':main()
