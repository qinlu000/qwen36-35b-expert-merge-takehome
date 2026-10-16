"""Execute one SAB solution/checker with the existing CPU/memory sandbox."""
import argparse
import json
from pathlib import Path
import subprocess

from asi_baseline_limits import affinity_filter, verify_memory_limit
from asi_bwrap import namespace_prefix, program_env


def main(args):
    memory = verify_memory_limit(8 * 1024**3)
    cpus = [int(value) for value in args.cpu_list.split(',')]
    bpf, selected = affinity_filter(4, cpus)
    prefix, mounts, _ = namespace_prefix(args.workspace, args.env_dir)
    for source, target in [(args.datasets, '/workspace/benchmark/datasets')]:
        prefix += ['--ro-bind', str(source), target]
        mounts.append({'source': str(source), 'target': target, 'readonly': True})
    if args.gold_results:
        target = '/workspace/benchmark/eval_programs/gold_results'
        prefix += ['--ro-bind', str(args.gold_results), target]
        mounts.append({'source': str(args.gold_results), 'target': target, 'readonly': True})
    command = prefix + ['--seccomp', str(bpf.fileno()), '--chdir', '/workspace', '--',
                        str(args.env_dir / 'bin/python'), args.code]
    args.receipt.write_text(json.dumps(dict(memory, allowed_cpus=selected, mounts=mounts,
        network='bwrap unshare-all; no controller credentials', task_gpu=False), indent=2) + '\n')
    environment = program_env(args.env_dir)
    environment.update(OPENBLAS_NUM_THREADS='4', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
    with bpf:
        result = subprocess.run(command, env=environment, pass_fds=(bpf.fileno(),))
    return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--env-dir', type=Path, required=True)
    parser.add_argument('--datasets', type=Path, required=True)
    parser.add_argument('--gold-results', type=Path)
    parser.add_argument('--code', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--cpu-list', default='112,113,114,115')
    raise SystemExit(main(parser.parse_args()))
