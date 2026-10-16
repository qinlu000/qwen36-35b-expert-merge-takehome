"""Allow the configured3000s native verifier through the HTTP exec adapter."""
from swe_score_runtime import SweNativeRuntimeEnvironment


class SweScoreFinalRuntimeEnvironment(SweNativeRuntimeEnvironment):
    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if '/tests/test.sh' in command and timeout_sec is None:
            timeout_sec = 3000
        return await super().exec(command, cwd=cwd, env=env,
                                  timeout_sec=timeout_sec, user=user)
