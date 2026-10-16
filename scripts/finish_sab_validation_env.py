"""Complete the dedicated SAB CPU dependencies, preserving every shared environment."""
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
environment = root / 'artifacts/envs/sab-validation-py310'
while subprocess.run(['kill', '-0', '538007'], capture_output=True).returncode == 0:
    time.sleep(15)
# uv originally selected a parent venv interpreter. Point this independent venv
# directly to the same system Python so its isolated mount has no parent-venv alias.
python = environment / 'bin/python'
python.unlink()
python.symlink_to('/usr/bin/python3.10')
config = environment / 'pyvenv.cfg'
config.write_text(config.read_text().replace('home = /data/caoqinlu/envs/datamind-sft/bin', 'home = /usr/bin'))
settings = dict(os.environ, HTTPS_PROXY='http://127.0.0.1:38080', HTTP_PROXY='http://127.0.0.1:38080',
                UV_CONCURRENT_DOWNLOADS='2', UV_CONCURRENT_BUILDS='1')
subprocess.run([str(root / 'artifacts/tools/uv/uv'), 'pip', 'install', '--python', str(python),
                '--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.3.0+cpu'],
               env=settings, check=True)
code = ('import importlib.metadata as m, json; '
        'packages=["numpy","pandas","scipy","matplotlib","scikit-learn","rdkit","geopandas",'
        '"rasterio","mlxtend","oggm","torch"]; print(json.dumps({p:m.version(p) for p in packages}))')
versions = json.loads(subprocess.check_output([str(python), '-c', code], text=True))
(root / 'artifacts/eval/validation_direct_20261016/sab_env_ready.json').write_text(
    json.dumps({'ready': True, 'versions': versions, 'environment': str(environment)}, indent=2) + '\n')
print(json.dumps(versions), flush=True)
