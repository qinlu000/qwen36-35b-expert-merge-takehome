"""Prepare the actual native Go workspace before running unchanged test.sh."""
import json
from pathlib import Path
import time

from swe_score_go_preseed_environments import SweScoreGoGlibcPreseed


class SweScoreGoPrefetchGlibc(SweScoreGoGlibcPreseed):
    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command and not getattr(self, '_workspace_prepared', False):
            self._workspace_prepared = True
            started = time.monotonic()
            preparation = ('cd /app 2>/dev/null || cd /testbed; '
                'export GOPROXY=file:///opt/apex-swe-score-go/gopath/pkg/mod/cache/download,https://goproxy.cn,direct; '
                'export GOSUMDB=sum.golang.org GOTOOLCHAIN=local; '
                'if [ -f go.work ]; then go work sync; fi; go mod download all')
            result = await super().exec(preparation, cwd=cwd, timeout_sec=1800)
            logs = Path(next(m['source'] for m in self._mounts if m['target'] == '/logs/agent'))
            (logs / 'native-go-workspace-preparation.json').write_text(json.dumps({
                'command': preparation, 'return_code': result.return_code,
                'elapsed_seconds': time.monotonic() - started,
                'stdout': result.stdout, 'stderr': result.stderr,
                'original_test_command_unchanged': True}, indent=2) + '\n')
        if '/tests/test.sh' in command and timeout_sec is None:
            # The outer verifier budget is3000s; the HTTP adapter otherwise
            # silently applies its600s default when no exec limit was passed.
            timeout_sec = 3000
        return await super().exec(command, cwd=cwd, env=env,
                                  timeout_sec=timeout_sec, user=user)
