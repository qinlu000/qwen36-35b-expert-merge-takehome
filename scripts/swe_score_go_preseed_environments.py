"""Populate the image's own Go download cache before unchanged verification."""
import json
from pathlib import Path

from swe_score_go_environments import SweScoreGoGlibc
from swe_score_go_preseed import preseed_go_score_cache


class Preseed:
    async def _start_server(self):
        await super()._start_server()
        receipt = await preseed_go_score_cache(self)
        logs = Path(next(m['source'] for m in self._mounts if m['target'] == '/logs/agent'))
        (logs / 'native-go-cache.json').write_text(json.dumps(receipt, indent=2) + '\n')


class SweScoreGoGlibcPreseed(Preseed, SweScoreGoGlibc):
    pass


def __getattr__(name):
    if name != 'SweScoreGoMuslPreseed':
        raise AttributeError(name)
    from swe_score_go_environments import SweScoreGoMusl

    class SweScoreGoMuslPreseed(Preseed, SweScoreGoMusl):
        pass

    return SweScoreGoMuslPreseed
