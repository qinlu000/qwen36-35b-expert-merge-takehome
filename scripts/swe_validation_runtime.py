"""Fresh replay for source dev; preserve the source evaluator's exact apply flags."""
import json
from pathlib import Path

from harbor.agents.base import BaseAgent


class SweValidationReplayAgent(BaseAgent):
    def __init__(self, *args, patch_path, **kwargs):
        super().__init__(*args, **kwargs)
        self.patch_path = Path(patch_path)

    @staticmethod
    def name():
        return 'source-dev-patch-replay'

    def version(self):
        return '1.0.0'

    async def setup(self, environment):
        pass

    async def run(self, instruction, environment, context):
        command = 'git reset --hard HEAD'
        if self.patch_path.is_file() and self.patch_path.stat().st_size:
            await environment.upload_file(self.patch_path, '/tmp/replay.patch')
            command += (' && git apply -v --3way --recount --ignore-space-change '
                        '--whitespace=nowarn /tmp/replay.patch')
        result = await environment.exec(command=command, timeout_sec=300)
        (self.logs_dir / 'replay.json').write_text(json.dumps({
            'patch': str(self.patch_path), 'apply_rc': result.return_code,
            'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
