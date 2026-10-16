"""Verifier-only dependency repair for the six archived answers from October 17."""
import asyncio
import json
from pathlib import Path
import subprocess

from terminal_repair_environment_v2 import TerminalRepairEnvironment

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
REPAIR = ROOT / 'artifacts/recovery/terminal-v2/native-gaps-20261017'
TOOLS = ROOT / 'artifacts/tools/terminal_verifier_offline_20261016'


class TerminalNativeGapEnvironment(TerminalRepairEnvironment):
    async def _prepare_verifier(self):
        await super()._prepare_verifier()
        task = self.environment_dir.parent.name
        target = self._staging / 'verifier_assets'

        def tree(source, destination):
            destination.mkdir(parents=True, exist_ok=True)
            subprocess.run(['cp', '-a', '--reflink=auto', str(source) + '/.', str(destination)], check=True)

        def prepare():
            if task in ['train-fasttext', 'sam-cell-seg']:
                python = TOOLS / 'python/cpython-3.11.14-linux-x86_64-gnu'
                tree(python, target / 'python' / python.name)
            if task == 'sam-cell-seg':
                receipt = json.loads((REPAIR / 'sam-cache/receipt.json').read_text())
                if not receipt['ready']:
                    raise RuntimeError('Exact native sam-cell-seg dependency cache is not ready')
                tree(Path(receipt['uv_cache_dir']), target / 'uv-cache')
                urls = json.loads((target / 'url-cache/url_map.json').read_text())
                source = Path(receipt['url_cache_dir'])
                tree(source, target / 'url-cache')
                urls.update(json.loads((source / 'url_map.json').read_text()))
                (target / 'url-cache/url_map.json').write_text(json.dumps(urls) + '\n')
        await asyncio.to_thread(prepare)
        if task in ['train-fasttext', 'sam-cell-seg']:
            self._repair_verifier_env.update(UV_PYTHON_DOWNLOADS='never', UV_OFFLINE='1')
        if task == 'make-doom-for-mips':
            receipt = json.loads((REPAIR / 'doom-apt/receipt.json').read_text())
            if not receipt['ready']:
                raise RuntimeError('Original dated snapshot apt cache is not ready')
            for name in ['lists', 'archives']:
                source = REPAIR / 'doom-apt' / name
                destination = target / ('apt-' + name)
                await asyncio.to_thread(tree, source, destination)
            # The image's docker-clean update hook deletes /var/cache/apt/*.deb.
            # Point apt at the private exact-byte cache so update cannot erase it.
            (target / 'apt-archives.conf').write_text(
                'Dir::Cache::archives "/staging/verifier_assets/apt-archives";\n')
            self._repair_verifier_env['APT_CONFIG'] = '/staging/verifier_assets/apt-archives.conf'
            # These are the original snapshot index and exact .deb payloads.
            # The candidate's apt sources, hosts and answer remain unchanged.
            command = ('cp -a /staging/verifier_assets/apt-lists/. /var/lib/apt/lists/ && '
                       'cp -a /staging/verifier_assets/apt-archives/. /var/cache/apt/archives/')
            result = await self.exec(command, timeout_sec=60)
            if result.return_code:
                raise RuntimeError('Failed to stage original snapshot apt cache')
