#!/usr/bin/env python3
"""Inspect one fixed import failure/cache and optionally run import-only RED/GREEN.

Never evaluates a task, executes candidate code, sends HTTP, changes production
runtime, or writes a score/marker. Output is metadata only.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


CONDITION = 'electrical_engineering.cmos_opamp_design__seed31415__b1'


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def inspect(project):
    original = project / 'artifacts/eval/asi128_asi240_20261017'
    scoring = original / 'scoring'
    result = original / 'electrical_engineering.cmos_opamp_design' / (CONDITION + '.json')
    raw = json.loads(result.read_text())
    saved = raw['agent_output']['persisted_outputs']
    outputs = []
    for expected in saved['files']:
        row = identity(result.parent / saved['dir'] / expected['path'])
        assert row['sha256'] == expected['sha256'] and row['bytes'] == expected['bytes']
        row['matches_generation_recorded_bytes'] = True
        outputs.append(row)
    cache = scoring / 'judge_calls' / (CONDITION + '.grading1')
    requests = sorted(cache.glob('*.request.json'))
    cached = []
    for request in requests:
        key = request.name.removesuffix('.request.json')
        request_hash, occurrence = key.rsplit('.', 1)
        body = json.loads(request.read_text())
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        assert digest == request_hash
        response = cache / (key + '.response.json')
        assert response.is_file()
        cached.append({'request_key': key, 'occurrence': int(occurrence),
            'request_file': identity(request), 'response_file': identity(response)})
    assert len(cached) == 9
    row = next(x for x in json.loads((scoring / 'local_score_seed31415.json').read_text())['results']
               if x['condition'] == CONDITION)
    assert row['evaluation_status'] == 'evaluation_invalid'
    return {'condition': CONDITION, 'source_result': identity(result), 'persisted_outputs': outputs,
        'original_frozen_input_hashes': row['frozen_inputs'],
        'parameter_metadata': identity(project / 'artifacts/asi/instances_seed31415/electrical_engineering.cmos_opamp_design__seed31415/framework_task_info.json'),
        'original_condition_record': identity(scoring / 'conditions' / (CONDITION + '.json')),
        'original_journal': identity(scoring / 'judge_calls.jsonl'),
        'cache_namespace': CONDITION + '.grading1', 'verified_cache': cached,
        'preparation_http_calls': 0,
        'original_status_and_outputs_must_not_be_rewritten': True}


def probe_imports(project):
    runtime = project / 'artifacts/eval/asi128_asi240_20261017/scoring/runtime'
    repo = project / 'artifacts/benchmarks/asi'
    target = repo / 'tasks/electrical_engineering/cmos_opamp_design/cmos_eval_runtime.py'
    # Prevent any accidental network call during imports, before importing task code.
    code = ("import socket,json; "
        "socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('network forbidden')); "
        "from tasks.electrical_engineering.cmos_opamp_design import cmos_eval_runtime; "
        "print(json.dumps({'module_file':cmos_eval_runtime.__file__}))")
    rows = []
    with (project / 'artifacts/eval/direct_asi_grader_cpu92_95.lock').open('r') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='apex-asi-import-only-') as temporary:
            shim = Path(temporary) / 'sitecustomize.py'
            shim.write_text('import sys\nsys.path.append(' + repr(str(repo)) + ')\n')
            cases = [('red', str(runtime)), ('green', str(runtime) + os.pathsep + str(repo)),
                     ('future_shim_green', temporary + os.pathsep + str(runtime))]
            for name, pythonpath in cases:
                env = dict(os.environ, PYTHONPATH=pythonpath, PYTHONDONTWRITEBYTECODE='1',
                    OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
                result = subprocess.run(['taskset', '-c', '92',
                    str(project / 'artifacts/envs/asi-py312/bin/python'), '-c', code],
                    cwd=project, env=env, capture_output=True, text=True, timeout=30)
                if name == 'red':
                    assert result.returncode != 0 and "No module named 'tasks'" in result.stderr
                else:
                    assert result.returncode == 0, result.stderr
                    assert Path(json.loads(result.stdout)['module_file']) == target
                rows.append({'case': name, 'returncode': result.returncode,
                    'expected_verdict': 'ModuleNotFoundError: tasks' if name == 'red' else 'correct frozen module path'})
    return {'passed': True, 'cpu': 92, 'temporary_grader_lease_released': True,
        'network_forbidden': True, 'candidate_executions': 0, 'evaluations': 0,
        'cases': rows, 'production_runtime_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--probe-imports', action='store_true')
    args = parser.parse_args()
    project = args.project.resolve()
    data = inspect(project)
    if args.probe_imports:
        data['import_probe'] = probe_imports(project)
    data['collected_at_utc'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(data, indent=2))
