"""Native glibc runtime; the Go cache is exposed only by the replay class."""
import json
from pathlib import Path
import time

from swe_score_bootstrap_runtime import SweScoreBootstrapRuntimeEnvironment
from swe_score_go_preseed import preseed_go_score_cache
from swe_score_go_runtime import apply_go_score_cache


class SweCleanGlibcRuntimeEnvironment(SweScoreBootstrapRuntimeEnvironment):
    pass


class SweCleanGlibcGoRuntimeEnvironment(SweCleanGlibcRuntimeEnvironment):
    async def _start_server(self):
        apply_go_score_cache(self)
        await super()._start_server()
        receipt = await preseed_go_score_cache(self)
        logs = Path(next(mount['source'] for mount in self._mounts
                         if mount['target'] == '/logs/agent'))
        (logs / 'native-go-cache.json').write_text(json.dumps(receipt, indent=2) + '\n')

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command and not getattr(self, '_workspace_prepared', False):
            self._workspace_prepared = True
            started = time.monotonic()
            # Same preparation already used by the production Flipt replay.
            preparation = ('cd /app 2>/dev/null || cd /testbed; '
                'export GOPROXY=file:///opt/apex-swe-score-go/gopath/pkg/mod/cache/download,https://goproxy.cn,direct; '
                'export GOSUMDB=sum.golang.org GOTOOLCHAIN=local; '
                'if [ -f go.work ]; then go work sync; fi; go mod download all')
            result = await super().exec(preparation, cwd=cwd, timeout_sec=1800)
            logs = Path(next(mount['source'] for mount in self._mounts
                             if mount['target'] == '/logs/agent'))
            (logs / 'native-go-workspace-preparation.json').write_text(json.dumps({
                'command': preparation, 'return_code': result.return_code,
                'elapsed_seconds': time.monotonic() - started,
                'stdout': result.stdout, 'stderr': result.stderr,
                'original_test_command_unchanged': True}, indent=2) + '\n')
        return await super().exec(command, cwd=cwd, env=env,
                                  timeout_sec=timeout_sec, user=user)
