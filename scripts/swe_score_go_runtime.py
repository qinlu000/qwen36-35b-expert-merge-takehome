"""Scoring-only Go dependency source; preserve the image's existing module cache."""
from pathlib import Path

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
CACHE=ROOT/'artifacts/cache/swe-score-go'
MOUNT={'type':'bind','source':str(CACHE),'target':'/opt/apex-swe-score-go','read_only':True}
ENV={
    'GOPROXY':'file:///opt/apex-swe-score-go/gopath/pkg/mod/cache/download,https://goproxy.cn,direct',
    'GOSUMDB':'sum.golang.org',
}


def apply_go_score_cache(environment):
    """Call once before starting a fresh native replay environment."""
    environment._mounts.append(dict(MOUNT))
    environment._persistent_env.update(ENV)
