"""Use the cached official Go modules only for frozen-patch replay."""
from swe_score_go_runtime import apply_go_score_cache
from swe_score_runtime import SweNativeRuntimeEnvironment


class SweScoreGoGlibc(SweNativeRuntimeEnvironment):
    async def _start_server(self):
        apply_go_score_cache(self)
        await super()._start_server()


# This class is imported only by the musl replay controller, whose PATH and
# PYTHONPATH select the already-frozen musl compatibility helper.
def __getattr__(name):
    if name != 'SweScoreGoMusl':
        raise AttributeError(name)
    from swe_musl_root_runtime import MuslRootRuntimeEnvironment

    class SweScoreGoMusl(MuslRootRuntimeEnvironment):
        async def _start_server(self):
            apply_go_score_cache(self)
            await super()._start_server()

    return SweScoreGoMusl
