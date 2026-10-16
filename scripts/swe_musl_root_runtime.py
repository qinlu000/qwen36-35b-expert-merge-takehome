"""The musl root-map process is already UID0; avoid an unnecessary su/setgroups."""
from musl_runtime_environment import MuslRuntimeEnvironment


class MuslRootRuntimeEnvironment(MuslRuntimeEnvironment):
    def _resolve_user(self, user):
        resolved = super()._resolve_user(user)
        return None if resolved in ('root', 0) else resolved
