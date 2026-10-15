"""Cache pinned SWE/TB image layers as SIFs without executing image contents."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    root = args.root
    source = root / 'configs/envs/swe_tb_image_digests.json'
    items = json.loads(source.read_text())
    # Prepare all TB images first; small images provide an early real pull check.
    items.sort(key=lambda x: (x['image'].startswith('ghcr.io/'), x['compressed_layer_bytes']))
    dest = root / 'artifacts/benchmarks/sif'
    logs = root / 'artifacts/preflight/swe_tb/image-pulls'
    dest.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    tool = root / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin/apptainer'
    env = os.environ | {'APPTAINER_CACHEDIR': str(root / 'artifacts/cache/apptainer'),
                        'APPTAINER_TMPDIR': str(root / 'artifacts/cache/apptainer-tmp'),
                        'GOMAXPROCS': '2', 'OMP_NUM_THREADS': '2'}
    env['NO_PROXY'] = env.get('NO_PROXY', '') + ',ghcr.io,pkg-containers.githubusercontent.com'
    env['no_proxy'] = env['NO_PROXY']
    Path(env['APPTAINER_CACHEDIR']).mkdir(parents=True, exist_ok=True)
    Path(env['APPTAINER_TMPDIR']).mkdir(parents=True, exist_ok=True)
    results = []

    def pull(item):
        digest = item.get('linux_amd64_manifest_digest', item['digest'])
        key = digest.replace(':', '-')
        output = dest / (key + '.sif')
        log = logs / (key + '.log')
        ref = item['image'].rsplit(':', 1)[0] + '@' + digest
        result = {'image': item['image'], 'linux_amd64_digest': digest, 'started_at': now(),
                  'log_path': str(log.relative_to(root))}
        if not output.exists():
            partial = dest / (key + '.partial.sif')
            with log.open('ab') as stream:
                for attempt in range(1, 3):
                    partial.unlink(missing_ok=True)
                    command = [str(tool), 'pull', '--arch', 'amd64', str(partial), 'docker://' + ref]
                    code = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
                    result['attempts'] = attempt
                    if code == 0:
                        partial.replace(output)
                        break
                else:
                    result.update(status='failed', return_code=code, finished_at=now())
                    return result
        # Check the SIF partition table only; no image file contents are opened.
        subprocess.run([str(tool), 'sif', 'list', str(output)], env=env,
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with output.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        alias = dest / (item['image'].replace('/', '_').replace(':', '_') + '.sif')
        if not alias.exists():
            alias.symlink_to(output.name)
        result.update(status='cached', sif_file=output.name, harbor_cache_name=alias.name,
                      sif_bytes=output.stat().st_size, sif_sha256=checksum, finished_at=now())
        return result

    report = {'manifest_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'total': len(items), 'workers': args.workers, 'started_at': now(),
              'scope': 'Image download/conversion only; no task or image commands executed'}

    def save(status):
        report.update(status=status, updated_at=now(), completed=sum(r['status'] == 'cached' for r in results),
                      failed=sum(r['status'] == 'failed' for r in results), results=results)
        temporary = dest / '_prefetch_progress.partial.json'
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(dest / '_prefetch_progress.json')

    save('running')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(pull, item): item for item in items}
        for future in as_completed(pending):
            result = future.result()
            results.append(result)
            save('running')
            print(json.dumps({k: result[k] for k in ('image', 'status')}), flush=True)
    save('finished' if any(r['status'] == 'failed' for r in results) else 'complete')
    print(json.dumps({k: report[k] for k in ('status', 'total', 'completed', 'failed')}), flush=True)


if __name__ == '__main__':
    main()
