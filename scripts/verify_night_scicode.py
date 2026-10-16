"""Numerical calibration in the frozen ASI offline 4CPU/8GiB namespace.

Generated code never runs in the controller. Only numeric NPZ files cross out.
HDF reference values remain outside the candidate workspace.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import h5py
import numpy as np

HDF_SHA256 = '8fb6e575b7b6dda5e48b04dea338fc6af4fe185774b8f19221c96945df9b4142'
HDF_MD5 = '2b41a7df40ddc23ce651ec05b8ecb6f8'


def trusted_test_capture(test, number):
    """Preserve published test setup; replace its final assertion with actual-only export."""
    tree = ast.parse(test)
    assert isinstance(tree.body[-1], ast.Assert)
    check = tree.body[-1].test
    if isinstance(check, ast.Call):
        assert len(check.args) == 2 and isinstance(check.args[1], ast.Name) and check.args[1].id == 'target'
        value = check.args[0]
    else:
        assert isinstance(check, ast.Compare) and isinstance(check.comparators[0], ast.Name)
        assert check.comparators[0].id == 'target'
        value = check.left
    tree.body = [node for node in tree.body[:-1]
                 if not (isinstance(node, ast.ImportFrom) and node.module == 'scicode.compare.cmp')]
    tree.body.append(ast.Expr(ast.Call(ast.Name('_capture', ast.Load()), [value, ast.Constant(number)], [])))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


CAPTURE = '''
from pathlib import Path as _Path
import json as _json
import numpy as _np
_Path('outputs').mkdir(exist_ok=True)
def _capture(value, number):
    sequence = isinstance(value, (tuple, list))
    values = list(value) if sequence else [value]
    _np.savez('outputs/test_'+str(number)+'.npz', **{'var'+str(i): _np.asarray(v) for i,v in enumerate(values)})
    _Path('outputs/test_'+str(number)+'.json').write_text(_json.dumps({'sequence':sequence,'count':len(values)}))
'''


def read_target(group):
    # Same released HDF order as upstream process_hdf5_to_tuple for these array-only tasks.
    values = []
    for key in group.keys():
        obj = group[key]
        if isinstance(obj, h5py.Dataset):
            values.append(obj[()])
        elif 'list' in obj:
            values.append([obj['list'][item][()] for item in obj['list'].keys()])
        else:
            raise ValueError('Unsupported calibration HDF schema: '+obj.name)
    return values if len(values) > 1 else values[0]


def compare(actual_file, metadata_file, target):
    metadata = json.loads(metadata_file.read_text())
    with np.load(actual_file, allow_pickle=False) as saved:
        actual = [saved['var'+str(i)] for i in range(metadata['count'])]
    expected = list(target) if metadata['sequence'] else [target]
    if len(actual) != len(expected):
        return {'passed': False, 'reason': 'output_count'}
    comparisons = []
    for value, reference in zip(actual, expected):
        reference = np.asarray(reference)
        match_shape = value.shape == reference.shape
        match_value = bool(match_shape and np.allclose(value, reference, rtol=1e-5, atol=1e-8))
        comparisons.append({'actual_shape': list(value.shape), 'reference_shape': list(reference.shape),
            'allclose': match_value, 'max_abs_error': float(np.max(np.abs(value.astype(complex)-reference.astype(complex)))) if match_shape and value.size else None})
    return {'passed': all(r['allclose'] for r in comparisons), 'arrays': comparisons,
            'rtol': 1e-5, 'atol': 1e-8}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--hdf', type=Path, required=True)
    parser.add_argument('--env-dir', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    root = args.root.resolve()
    assert 0 < args.timeout <= 180
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with args.hdf.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            sha.update(chunk); md5.update(chunk)
    assert sha.hexdigest() == HDF_SHA256 and md5.hexdigest() == HDF_MD5
    (root/'hdf_integrity.json').write_text(json.dumps({'bytes': args.hdf.stat().st_size,
        'sha256':sha.hexdigest(), 'md5':md5.hexdigest()}, indent=2)+'\n')
    rows = [json.loads(line) for line in (root/'two_task_candidates.jsonl').read_text().splitlines()]
    cpus = sorted(os.sched_getaffinity(0))[-4:]
    assert len(cpus) == 4
    helper = Path(__file__).resolve().with_name('asi_baseline_limits.py')
    helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
    controller_env = {key: os.environ[key] for key in ('HOME','PATH','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS') if key in os.environ}
    results = []
    for record in rows:
        pid = record['problem_id']
        code_file = root/('teacher_'+pid+'.py')
        if not code_file.exists():
            results.append({'problem_id':pid, 'passed':False, 'reason':'no_valid_teacher_code'})
            continue
        workspace = root/'workspaces'/pid
        workspace.mkdir(parents=True, exist_ok=True)
        assert not (workspace/'outputs').exists(), 'Numerical execution already occurred; retain previous receipts'
        (workspace/'generated.py').write_bytes(code_file.read_bytes())
        (workspace/'prompt.md').write_text(record['prompt'])
        step = record['row']['sub_steps'][0]
        assert len(record['row']['sub_steps']) == 1
        body = [CAPTURE, record['row']['required_dependencies'],
                "exec(compile(_Path('generated.py').read_text(), 'generated.py', 'exec'), globals())"]
        body += [trusted_test_capture(test, i) for i,test in enumerate(step['test_cases'])]
        (workspace/'runner.py').write_text('\n\n'.join(body)+'\n')
        receipt = root/('limits_'+pid+'.json')
        unit = 'apex-scicode-'+uuid.uuid4().hex+'.scope'
        command = ['systemd-run','--user','--scope','--quiet','--unit',unit,
            '-p','MemoryMax=8589934592','-p','MemorySwapMax=0','--',sys.executable,str(helper),
            '--workspace',str(workspace),'--env-dir',str(args.env_dir.resolve()),'--code','runner.py',
            '--receipt',str(receipt),'--cpus','4','--cpu-list',','.join(map(str,cpus))]
        begin = time.time()
        process = subprocess.Popen(command, env=controller_env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, errors='replace', start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(['systemctl','--user','kill','--signal=KILL',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL)
            stdout,stderr = process.communicate()
        finally:
            subprocess.run(['systemctl','--user','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        elapsed = time.time()-begin
        (root/('execution_'+pid+'.stdout.txt')).write_text(stdout)
        (root/('execution_'+pid+'.stderr.txt')).write_text(stderr)
        checks = []
        with h5py.File(args.hdf,'r') as references:
            for i in range(len(step['test_cases'])):
                actual = workspace/'outputs'/('test_'+str(i)+'.npz')
                metadata = actual.with_suffix('.json')
                if not actual.is_file() or not metadata.is_file():
                    checks.append({'test':i+1,'passed':False,'reason':'missing_numeric_output'})
                    continue
                target = read_target(references[step['step_number']+'/test'+str(i+1)])
                checks.append({'test':i+1, **compare(actual, metadata, target)})
        result = {'problem_id':pid,'problem_name':record['problem_name'],'main_family':record['main_family'],
            'passed':process.returncode==0 and not timed_out and all(t['passed'] for t in checks),
            'returncode':process.returncode,'timeout':timed_out,'execution_seconds':round(elapsed,3),
            'test_results':checks,'limits_receipt':str(receipt),'cpu_list':cpus,
            'frozen_helper_sha256':helper_sha,'reference_visible_to_generated_code':False,
            'source_main_family_counted_as':1,'official_scicode_score':False,
            'protocol_deviation':'Complete one-shot program with imports; 180s single-current-env cap and stricter equal-shape check; official uses cumulative substeps, 1800s and 2024/2025 OR environments.'}
        results.append(result)
        (root/('verification_'+pid+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    summary = {'results':results,'accepted_main_families':sum(r['passed'] for r in results),
        'attempted_main_families':len(results),'unchanged_frozen_helper_sha256':helper_sha,
        'generated_programs_executed_on_host':False,'formal_asi_gold_read':False,
        'memory_bytes':8589934592,'cpu_list':cpus,'network':'unshare-all/offline',
        'not_full_scientific_train_val_ready':True}
    (root/'verification_summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':
    main()
