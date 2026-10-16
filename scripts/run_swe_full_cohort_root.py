#!/usr/bin/env python3
"""Run the pending fixed-scope SWE cohort in two disjoint eight-slot groups."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

from swe_baseline_v2 import ROOT, save_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--admit-task-ids', type=Path, required=True)
    p.add_argument('--endpoint', required=True)
    p.add_argument('--engine-max-seqs', type=int, default=4)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / '.full-controller.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ids = json.loads(args.admit_task_ids.read_text())
    glibc_ids = set(json.loads((ROOT / 'artifacts/preflight/swe_v2/admit_glibc41_20261016.json').read_text()))
    glibc, musl = [n for n in ids if n in glibc_ids], [n for n in ids if n not in glibc_ids]
    if glibc and musl:
        groups = [('glibc', glibc, 64, False), ('musl', musl, 76, True)]
    else:
        only = glibc or musl
        groups = [('group0', only[::2], 64, bool(musl)), ('group1', only[1::2], 76, bool(musl))]
    assets = ROOT / 'artifacts/preflight/swe_v2/musl_compat'
    children = []
    for label, selected, offset, is_musl in groups:
        if not selected:
            continue
        out = args.output / label
        out.mkdir(exist_ok=True)
        manifest = out / 'admission_ids.json'
        save_json(manifest, selected)
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts'))
        prefix = (str(ROOT / 'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin') + ':' +
                  str(ROOT / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin'))
        runtime = 'swe_runtime_environment:SweRuntimeEnvironment'
        if is_musl:
            env['PYTHONPATH'] = str(assets) + ':' + env['PYTHONPATH']
            prefix = str(assets / 'shim') + ':' + prefix
            runtime = 'swe_musl_root_runtime:MuslRootRuntimeEnvironment'
        env['PATH'] = prefix + ':' + env['PATH']
        command = [str(ROOT / 'artifacts/envs/harbor/bin/python'), '-u',
            str(ROOT / 'scripts/run_swe_baseline_v2_next.py'), '--endpoint', args.endpoint,
            '--key-path', str(ROOT / 'artifacts/private/base_smoke_api_key'), '--output', str(out),
            '--admit-task-ids', str(manifest), '--concurrency', str(min(8, len(selected))),
            '--cpu-offset', str(offset), '--environment-import-path', runtime,
            '--engine-max-seqs', str(args.engine_max_seqs), '--acceptance-receipt',
            str(ROOT / 'artifacts/preflight/swe_v2/acceptance_glibc41_20261016.json'),
            '--model-finished-marker', str(out / 'model-consumer-finished.json')]
        with (out / 'controller.log').open('ab') as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, env=env, start_new_session=True)
        children.append((child, out, selected))
    save_json(args.output / 'controller.json', {'pid': os.getpid(), 'endpoint': args.endpoint,
        'task_ids': ids, 'scope': 51, 'max_solver_admissions': 16,
        'cpu_ids': list(range(64, 72)) + list(range(76, 84)),
        'model_max_num_seqs': args.engine_max_seqs,
        'children': [{'pid': c.pid, 'output': str(o), 'task_ids': s} for c, o, s in children]})
    while True:
        active, pending, terminal, states = [], [], [], []
        for child, out, selected in children:
            if (args.output / 'STOP_ADMISSION').exists():
                (out / 'STOP_ADMISSION').touch()
            cp = out / 'admission_checkpoint.json'
            if cp.exists():
                data = json.loads(cp.read_text())
                active.extend(data.get('active', []))
                pending.extend(data.get('pending', []))
                terminal.extend(data.get('terminal', []))
                states.append({'output': str(out), 'state': data.get('state'), 'returncode': child.poll()})
            else:
                pending.extend(selected)
        save_json(args.output / 'checkpoint.json', {'scope': 51, 'cohort_task_ids': ids,
            'active': active, 'pending': pending, 'terminal': terminal, 'children': states,
            'endpoint': args.endpoint, 'model_max_num_seqs': args.engine_max_seqs,
            'updated_unix': time.time()})
        if all(c.poll() is not None for c, _, _ in children):
            save_json(args.output / 'cohort-finished.json', {'controller_finished': True,
                'returncodes': [c.returncode for c, _, _ in children], 'pending': pending,
                'scope': 51, 'task_ids': ids})
            return
        time.sleep(2)


if __name__ == '__main__':
    main()
