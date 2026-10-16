"""Supply already-downloaded official3.11 only to train-fasttext's verifier assets."""
from datetime import datetime,timezone
import json,shutil,time
from pathlib import Path

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
SOURCE=ROOT/'artifacts/tools/terminal_verifier_offline_20261016/python/cpython-3.11.14-linux-x86_64-gnu'


def main():
    while not (RUN/'followon/full445.COMPLETE.json').exists():
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:args=p.joinpath('cmdline').read_bytes().decode().split('\0')
            except (OSError,ValueError):continue
            staging=next((a.split(':')[0] for a in args if a.endswith(':/staging')),None)
            logs=next((a.split(':')[0] for a in args if a.endswith(':/logs/verifier') and str(OUT) in a),None)
            if not staging or not logs or not Path(logs).parent.name.startswith('train-fasttext__'):continue
            assets=Path(staging)/'verifier_assets/python'
            if not assets.is_dir():continue
            target=assets/SOURCE.name
            if target.exists():continue
            temp=assets/('.'+SOURCE.name+'.staging')
            shutil.copytree(SOURCE,temp,symlinks=True,dirs_exist_ok=True)
            temp.rename(target)
            value={'at_utc':datetime.now(timezone.utc).isoformat(),'trial':str(Path(logs).parent),
                'source':str(SOURCE),'target':str(target),'phase':'verifier only','model_calls_or_tests_added':0}
            with (RUN/'verifier-python311-staged.jsonl').open('a') as stream:stream.write(json.dumps(value)+'\n')
            print(json.dumps(value),flush=True)
        time.sleep(5)


if __name__=='__main__':main()
