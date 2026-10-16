#!/usr/bin/env python3
"""Cache transitive official Go dependencies with the task image's native Go."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    cache = ROOT / 'artifacts/cache/swe-score-go'
    work = cache / 'required-module-graph'
    work.mkdir(exist_ok=True)
    (work / 'go.mod').write_text('module apex_score_dependency_cache\n\ngo 1.24\n\nrequire (\n'
        ' github.com/aws/aws-sdk-go-v2/service/ecr v1.38.0\n'
        ' github.com/mdlayher/netlink v1.6.0\n)\n')
    images = json.loads((ROOT / 'artifacts/eval/base_swe_v2_20261016_full/glibc/image_readiness.json').read_text())
    image = next(v['sif'] for k, v in images.items() if 'flipt-c188284' in k)
    command = ['singularity', 'exec', '--cleanenv', '--containall', '--no-mount',
        'home,tmp,bind-paths,hostfs,cwd', '--bind', str(cache) + ':/cache', '--pwd',
        '/cache/required-module-graph', image, 'env', 'GOPATH=/cache/gopath',
        'GOCACHE=/cache/build', 'GOPROXY=https://goproxy.cn,direct',
        'GOSUMDB=sum.golang.org', 'GOTOOLCHAIN=local', 'go', 'mod', 'download', 'all']
    with (work / 'download.stdout').open('wb') as stdout, (work / 'download.stderr').open('wb') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr)
    (work / 'receipt.json').write_text(json.dumps({'returncode': result.returncode,
        'command': command, 'model_calls': 0, 'tests_executed': 0,
        'only_dependency_cache_preparation': True}, indent=2) + '\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
