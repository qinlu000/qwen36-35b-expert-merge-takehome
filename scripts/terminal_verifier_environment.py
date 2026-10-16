"""Official verifier downloads from exact cached upstream artifacts, after solver ends."""
import asyncio,json,shutil
from pathlib import Path
from terminal_native_environment import TerminalNativeEnvironment,ROOT

TOOLS=ROOT/'artifacts/tools/terminal_verifier_offline_20261016'


class TerminalVerifierEnvironment(TerminalNativeEnvironment):
    async def _prepare_verifier(self):
        await super()._prepare_verifier()
        target=self._staging/'verifier_assets'
        def copy():
            mapping=TOOLS/'task_cache_map.json'
            if mapping.exists():
                data=json.loads(mapping.read_text())
                rows=data.get('tasks',data)
                item=rows.get(self.environment_name,{}) if isinstance(rows,dict) else {}
                cache=item.get('uv_cache_dir') or item.get('cache') or item.get('cache_dir')
                if item.get('ready') and cache:
                    shutil.copytree(cache,target/'uv-cache',dirs_exist_ok=True)
            official=TOOLS/'uv-installer'
            if official.exists():
                shutil.copytree(official,target/'url-cache',dirs_exist_ok=True)
            shim=Path(__file__).with_name('terminal_verifier_curl.py')
            shutil.copy2(shim,target/'verifier-bin/curl')
            (target/'verifier-bin/curl').chmod(0o755)
        await asyncio.to_thread(copy)
