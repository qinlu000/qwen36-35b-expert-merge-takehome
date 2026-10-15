"""Run Harbor's unmodified Singularity bootstrap on a synthetic local task; no model/GPU calls."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import socket
import time

from apex_singularity import ApexSingularityEnvironment
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    args = parser.parse_args()
    scratch = args.root / 'artifacts/preflight/swe_tb/synthetic-harbor'
    environment_dir = scratch / 'environment'
    environment_dir.mkdir(parents=True, exist_ok=True)
    image_name = 'apex-synthetic/slime-ubuntu24:local'
    (environment_dir / 'Dockerfile').write_text(f'FROM {image_name}\nWORKDIR /tmp\n')
    cache = scratch / 'cache'
    cache.mkdir(exist_ok=True)
    cached_image = cache / 'apex-synthetic_slime-ubuntu24_local.sif'
    cached_image.unlink(missing_ok=True)
    cached_image.symlink_to(args.image.resolve())
    paths = TrialPaths(scratch / 'trial')
    paths.mkdir()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('apex.synthetic-harbor').setLevel(logging.DEBUG)
    env = ApexSingularityEnvironment(
        environment_dir=environment_dir,
        environment_name='apex-synthetic-harbor',
        session_id='bootstrap-smoke',
        trial_paths=paths,
        task_env_config=EnvironmentConfig(docker_image=image_name, cpus=1, memory_mb=4096, gpus=0),
        singularity_image_cache_dir=cache,
        logger=logging.getLogger('apex.synthetic-harbor'),
    )
    report = {'image_path': str(args.image), 'task_scope': 'Synthetic only; no benchmark instruction, solution, or tests',
              'scope': 'Native Harbor with project bootstrap/cleanup adaptations; no model or GPU computation'}
    started = time.monotonic()
    try:
        await env.start(force_build=False)
        report['start_seconds'] = time.monotonic() - started
        result = await env.exec(
            "id -u; printf 'APEX_HARBOR_SYNTHETIC_OK\\n' > /tmp/apex-harbor-synthetic.txt; "
            "cat /tmp/apex-harbor-synthetic.txt; "
            "/opt/harbor-server/bin/python3 -c 'import fastapi,uvicorn; print(fastapi.__version__,uvicorn.__version__)'",
            timeout_sec=30,
        )
        report['exec'] = result.model_dump()
        assert result.return_code == 0 and 'APEX_HARBOR_SYNTHETIC_OK' in result.stdout
        check = await env.exec('cat /tmp/apex-harbor-synthetic.txt', timeout_sec=10)
        assert check.return_code == 0 and check.stdout.strip() == 'APEX_HARBOR_SYNTHETIC_OK'
        report['persistent_exec'] = check.model_dump()
        terminal = await env.exec(
            "set -e; tmux -V; asciinema --version; "
            "tmux -S /tmp/apex-harbor-smoke.sock new-session -d -s synthetic 'bash --noprofile --norc'; "
            "tmux -S /tmp/apex-harbor-smoke.sock send-keys -t synthetic "
            "\"printf 'APEX_TMUX_SYNTHETIC_OK\\n' > /tmp/apex-tmux-smoke.txt\" Enter; "
            "timeout 5 bash -c 'until test -s /tmp/apex-tmux-smoke.txt; do sleep 0.1; done'; "
            "cat /tmp/apex-tmux-smoke.txt; "
            "tmux -S /tmp/apex-harbor-smoke.sock capture-pane -p -t synthetic; "
            "tmux -S /tmp/apex-harbor-smoke.sock kill-server; "
            "asciinema rec --command 'printf APEX_CAST_SYNTHETIC_OK' --overwrite /tmp/apex-synthetic.cast; "
            "test -s /tmp/apex-synthetic.cast",
            timeout_sec=30,
        )
        report['terminal'] = terminal.model_dump()
        assert terminal.return_code == 0 and 'APEX_TMUX_SYNTHETIC_OK' in terminal.stdout
        report['status'] = 'passed'
    except Exception as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        port = env._server_port
        await env.stop(delete=True)
        if port:
            with socket.socket() as probe:
                probe.settimeout(1)
                report['server_port_closed'] = probe.connect_ex(('127.0.0.1', port)) != 0
            if not report['server_port_closed']:
                report.update(status='failed', error='Harbor stop left the synthetic server running')
        report['total_seconds'] = time.monotonic() - started
        (scratch / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
        assert report.get('server_port_closed', True), 'Harbor stop left the synthetic server running'


if __name__ == '__main__':
    asyncio.run(main())
